import enum
from datetime import datetime

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OrderStatus(str, enum.Enum):
    COMPLETADA = "completada"
    PENDIENTE = "pendiente"
    FALLIDA = "fallida"
    CANCELADA = "cancelada"
    EN_PROGRESO = "en_progreso"
    COMPLETADA_PARCIAL = "completada_parcial"
    SIN_CAMBIO = "sin_cambio"
    REQUIERE_REVISION = "requiere_revision"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    whatsapp_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    group_jid: Mapped[str] = mapped_column(String(255), index=True)
    sender_jid: Mapped[str] = mapped_column(String(255), index=True)
    quoted_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    group_jid: Mapped[str] = mapped_column(String(255), index=True)
    scheduled_date: Mapped[datetime] = mapped_column(Date, index=True)
    operation_type: Mapped[str] = mapped_column(String(64))
    locality: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_document: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phones: Mapped[list] = mapped_column(JSON, default=list)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[str | None] = mapped_column(String(128), nullable=True)
    installation_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDIENTE)
    availability_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_customer_confirmation: Mapped[bool] = mapped_column(default=False)
    safety_risk: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OperationEvent(Base):
    __tablename__ = "operation_events"
    __table_args__ = (UniqueConstraint("order_id", "whatsapp_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    whatsapp_message_id: Mapped[str] = mapped_column(String(255))
    author_jid: Mapped[str] = mapped_column(String(255))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(default=1.0)
    source: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrderAssignment(Base):
    __tablename__ = "order_assignments"
    __table_args__ = (UniqueConstraint("order_id", "technician_name", "source_message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    technician_name: Mapped[str] = mapped_column(String(128))
    source_message_id: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[float] = mapped_column(default=1.0)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReportRun(Base):
    __tablename__ = "report_runs"
    __table_args__ = (UniqueConstraint("report_date", "scheduled"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    report_date: Mapped[datetime] = mapped_column(Date, index=True)
    scheduled: Mapped[bool] = mapped_column(default=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content: Mapped[str] = mapped_column(Text)
