from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, Message, OperationEvent, Order, OrderAssignment, OrderStatus
from app.processing import assigned_names, availability, classify, classify_with_openrouter, extract_customer_details, extract_order, individual_record


def assign_prior_team(db: Session, order: Order, before: datetime) -> None:
    if not order.locality:
        return
    messages = db.scalars(select(Message).where(
        Message.group_jid == order.group_jid,
        Message.occurred_at <= before,
        Message.text.ilike(f"%{order.locality}%"),
    )).all()
    for assignment_message in messages:
        for technician_name in assigned_names(assignment_message.text):
            db.add(OrderAssignment(order_id=order.id, technician_name=technician_name,
                                   source_message_id=assignment_message.whatsapp_id,
                                   assigned_at=assignment_message.occurred_at))


def operation_date(occurred_at: datetime) -> object:
    return occurred_at.astimezone(ZoneInfo(settings().timezone)).date()


def process_message(db: Session, message: Message) -> None:
    config = settings()
    if message.sender_jid in config.authorized_creators and individual_record(message.text):
        if not db.scalar(select(Order).where(Order.source_message_id == message.whatsapp_id)):
            operation, locality, customer = extract_order(message.text)
            details = extract_customer_details(message.text)
            order = Order(source_message_id=message.whatsapp_id, group_jid=message.group_jid,
                          scheduled_date=operation_date(message.occurred_at), operation_type=operation,
                          locality=locality, customer_name=customer, **details)
            db.add(order)
            db.flush()
            assign_prior_team(db, order, message.occurred_at)
    elif message.quoted_message_id:
        order = resolve_order(db, message.quoted_message_id)
        if order:
            note, confirmation = availability(message.text)
            if note:
                order.availability_note = note
                order.requires_customer_confirmation = confirmation
                return mark_processed(message)
            for technician_name in assigned_names(message.text):
                db.add(OrderAssignment(order_id=order.id, technician_name=technician_name,
                                       source_message_id=message.whatsapp_id, assigned_at=message.occurred_at))
            result = classify(message.text)
            if result.status == OrderStatus.REQUIERE_REVISION:
                result = classify_with_openrouter(message.text)
            db.add(OperationEvent(order_id=order.id, whatsapp_message_id=message.whatsapp_id,
                                  author_jid=message.sender_jid, status=result.status,
                                  reason_code=result.reason_code, reason_text=result.reason_text,
                                  confidence=result.confidence, source=result.source,
                                  occurred_at=message.occurred_at))
            if result.status not in {OrderStatus.SIN_CAMBIO, OrderStatus.REQUIERE_REVISION}:
                order.current_status = result.status
            if result.reason_code == "RIESGO_SEGURIDAD":
                order.safety_risk = True
    else:
        technicians = assigned_names(message.text)
        if technicians:
            normalized_text = message.text.lower()
            orders = db.scalars(select(Order).where(Order.group_jid == message.group_jid,
                                                    Order.scheduled_date == message.occurred_at.date())).all()
            for order in orders:
                if order.locality and order.locality.lower() in normalized_text:
                    for technician_name in technicians:
                        db.add(OrderAssignment(order_id=order.id, technician_name=technician_name,
                                               source_message_id=message.whatsapp_id, assigned_at=message.occurred_at))
    mark_processed(message)


def mark_processed(message: Message) -> None:
    message.processed_at = datetime.now(UTC)


def resolve_order(db: Session, message_id: str) -> Order | None:
    seen: set[str] = set()
    current = message_id
    while current and current not in seen:
        seen.add(current)
        order = db.scalar(select(Order).where(Order.source_message_id == current))
        if order:
            return order
        parent = db.scalar(select(Message).where(Message.whatsapp_id == current))
        current = parent.quoted_message_id if parent else None
    return None


def claim_job(db: Session) -> Job | None:
    return db.scalar(select(Job).where(Job.status == "pending").order_by(Job.id).with_for_update(skip_locked=True).limit(1))
