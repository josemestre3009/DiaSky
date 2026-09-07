from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Order, OrderStatus, ReportRun


def build_report(db: Session, report_date: date) -> str:
    orders = list(db.scalars(select(Order).where(Order.scheduled_date == report_date)))
    groups = {"Completadas": [], "Pendientes": [], "Fallidas/Canceladas": [], "Sin reporte": []}
    for order in orders:
        detail = f" ({order.availability_note})" if order.availability_note else ""
        line = f"- {order.operation_type}: {order.locality or 'sin zona'}{detail}"
        if order.current_status == OrderStatus.COMPLETADA:
            groups["Completadas"].append(line)
        elif order.current_status in {OrderStatus.FALLIDA, OrderStatus.CANCELADA}:
            groups["Fallidas/Canceladas"].append(line)
        elif order.current_status in {OrderStatus.PENDIENTE, OrderStatus.COMPLETADA_PARCIAL, OrderStatus.EN_PROGRESO}:
            groups["Pendientes"].append(line)
        else:
            groups["Sin reporte"].append(line)
    sections = [f"Resumen operativo {report_date.isoformat()}"]
    for name, lines in groups.items():
        sections.extend((f"\n{name}: {len(lines)}", *(lines or ["- Ninguna"])))
    return "\n".join(sections)


def send_report(content: str) -> None:
    config = settings()
    if not config.evolution_api_key or not config.evolution_instance_name:
        raise RuntimeError("Evolution sending is not configured")
    path = config.evolution_send_text_path.format(instance=config.evolution_instance_name)
    response = httpx.post(f"{config.evolution_api_url.rstrip('/')}{path}", headers={"apikey": config.evolution_api_key},
                          json={"number": config.report_recipient_jid.split("@")[0], "text": content}, timeout=15)
    response.raise_for_status()


def scheduled_report(db: Session) -> bool:
    local_today = datetime.now(ZoneInfo(settings().timezone)).date()
    existing = db.scalar(select(ReportRun).where(ReportRun.report_date == local_today, ReportRun.scheduled.is_(True)))
    if existing:
        return False
    content = build_report(db, local_today)
    report = ReportRun(report_date=local_today, scheduled=True, content=content)
    db.add(report)
    db.flush()
    send_report(content)
    report.sent_at = datetime.now(UTC)
    return True
