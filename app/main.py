import hmac
import logging
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Correction, Job, Message, OperationEvent, Order, OrderAssignment, OrderStatus
from app.reporting import build_report, send_report

app = FastAPI(title="DiaSky Operations API")
logger = logging.getLogger("diasky.webhook")


def db_session():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(db_session)]


def admin(authorization: Annotated[str | None, Header()] = None) -> None:
    expected = f"Bearer {settings().admin_token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(401, "Unauthorized")


Admin = Annotated[None, Depends(admin)]


class CorrectionInput(BaseModel):
    status: OrderStatus
    reason_code: str | None = None
    reason_text: str | None = None
    actor: str = "admin"


def text_from_message(message: dict) -> str:
    content = message.get("message", {})
    for key in ("conversation", "extendedTextMessage"):
        value = content.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("text", "")
    return ""


def quoted_id(message: dict) -> str | None:
    direct_context = message.get("contextInfo")
    if isinstance(direct_context, dict):
        return direct_context.get("stanzaId")
    content = message.get("message", {})
    extended = content.get("extendedTextMessage", {})
    return extended.get("contextInfo", {}).get("stanzaId") if isinstance(extended, dict) else None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/panel", include_in_schema=False)
def panel() -> FileResponse:
    return FileResponse("app/static/panel.html")


@app.post("/webhooks/evolution/{path_token}", status_code=200)
def evolution_webhook(path_token: str, payload: dict, db: DB, x_webhook_secret: Annotated[str | None, Header()] = None) -> dict[str, bool]:
    config = settings()
    if not hmac.compare_digest(path_token, config.webhook_path_token):
        raise HTTPException(404, "Not found")
    received_secret = x_webhook_secret or payload.get("secret") or ""
    if config.webhook_secret and not hmac.compare_digest(received_secret, config.webhook_secret):
        raise HTTPException(401, "Invalid webhook secret")
    data = payload.get("data", payload)
    messages = data if isinstance(data, list) else [data]
    for item in messages:
        key = item.get("key", {})
        group_jid = key.get("remoteJid", "")
        message_id = key.get("id")
        if group_jid not in config.operation_groups or not message_id:
            # Log routing metadata only. Payload text can contain customer PII.
            logger.info("Ignored webhook message event=%s group=%s has_message_id=%s", payload.get("event"), group_jid, bool(message_id))
            continue
        if db.scalar(select(Message.id).where(Message.whatsapp_id == message_id)):
            continue
        timestamp = item.get("messageTimestamp")
        occurred_at = datetime.fromtimestamp(int(timestamp), UTC) if timestamp else datetime.now(UTC)
        message = Message(whatsapp_id=message_id, group_jid=group_jid,
                          sender_jid=key.get("participant") or key.get("remoteJid", ""),
                          quoted_message_id=quoted_id(item), text=text_from_message(item),
                          occurred_at=occurred_at, payload=item)
        db.add(message)
        db.flush()
        db.add(Job(message_id=message.id))
    db.commit()
    return {"received": True}


@app.get("/orders", dependencies=[Depends(admin)])
def list_orders(db: DB, scheduled_date: date | None = None, status: OrderStatus | None = None, locality: str | None = None):
    query = select(Order).order_by(Order.id.desc())
    if scheduled_date:
        query = query.where(Order.scheduled_date == scheduled_date)
    if status:
        query = query.where(Order.current_status == status)
    if locality:
        query = query.where(Order.locality.ilike(f"%{locality}%"))
    return [{"id": o.id, "date": o.scheduled_date, "type": o.operation_type, "locality": o.locality,
             "customer_name": o.customer_name, "status": o.current_status, "availability_note": o.availability_note,
             "requires_customer_confirmation": o.requires_customer_confirmation, "safety_risk": o.safety_risk} for o in db.scalars(query)]


@app.get("/orders/{order_id}", dependencies=[Depends(admin)])
def get_order(order_id: int, db: DB):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    events = db.scalars(select(OperationEvent).where(OperationEvent.order_id == order_id).order_by(OperationEvent.occurred_at)).all()
    assignments = db.scalars(select(OrderAssignment).where(OrderAssignment.order_id == order_id).order_by(OrderAssignment.assigned_at)).all()
    event_messages = {
        message.whatsapp_id: message.text
        for message in db.scalars(select(Message).where(Message.whatsapp_id.in_([event.whatsapp_message_id for event in events])))
    }
    return {"id": order.id, "date": order.scheduled_date, "type": order.operation_type, "locality": order.locality,
            "customer_name": order.customer_name, "customer_document": order.customer_document, "address": order.address,
            "phones": order.phones, "email": order.email, "plan": order.plan, "installation_value": order.installation_value,
            "status": order.current_status,
            "availability_note": order.availability_note, "requires_customer_confirmation": order.requires_customer_confirmation,
            "safety_risk": order.safety_risk, "assignments": [{"technician": a.technician_name, "assigned_at": a.assigned_at} for a in assignments],
            "events": [{"status": e.status, "reason_code": e.reason_code, "reason_text": e.reason_text,
                        "report_text": event_messages.get(e.whatsapp_message_id, ""),
                        "confidence": e.confidence, "source": e.source, "occurred_at": e.occurred_at} for e in events]}


@app.patch("/orders/{order_id}", dependencies=[Depends(admin)])
def correct_order(order_id: int, body: CorrectionInput, db: DB):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    order.current_status = body.status
    db.add(Correction(order_id=order_id, actor=body.actor, status=body.status,
                      reason_code=body.reason_code, reason_text=body.reason_text))
    db.commit()
    return {"id": order.id, "status": order.current_status}


@app.delete("/orders/{order_id}", status_code=204, dependencies=[Depends(admin)])
def delete_order(order_id: int, db: DB):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    db.execute(delete(OperationEvent).where(OperationEvent.order_id == order_id))
    db.execute(delete(OrderAssignment).where(OrderAssignment.order_id == order_id))
    db.execute(delete(Correction).where(Correction.order_id == order_id))
    db.delete(order)
    db.commit()


@app.get("/reports/daily", dependencies=[Depends(admin)])
def daily_report(db: DB, report_date: date = Query(default_factory=date.today)):
    orders = list(db.scalars(select(Order).where(Order.scheduled_date == report_date)))
    groups: dict[str, list[Order]] = {"completadas": [], "pendientes": [], "fallidas_canceladas": [], "sin_reporte": []}
    for order in orders:
        if order.current_status == OrderStatus.COMPLETADA:
            groups["completadas"].append(order)
        elif order.current_status in {OrderStatus.FALLIDA, OrderStatus.CANCELADA}:
            groups["fallidas_canceladas"].append(order)
        elif order.current_status == OrderStatus.PENDIENTE and not db.scalar(select(OperationEvent.id).where(OperationEvent.order_id == order.id)):
            groups["sin_reporte"].append(order)
        else:
            groups["pendientes"].append(order)
    return {key: [{"id": order.id, "locality": order.locality, "type": order.operation_type} for order in value] for key, value in groups.items()}


@app.post("/reports/daily/{report_date}/send", dependencies=[Depends(admin)])
def send_daily_report(report_date: date, db: DB):
    content = build_report(db, report_date)
    send_report(content)
    return {"sent": True, "report_date": report_date}
