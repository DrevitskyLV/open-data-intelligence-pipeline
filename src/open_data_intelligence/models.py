from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from open_data_intelligence.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class SyncStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255), index=True)

    purchases: Mapped[list[Procurement]] = relationship(
        back_populates="buyer", foreign_keys="Procurement.buyer_id"
    )
    sales: Mapped[list[Procurement]] = relationship(
        back_populates="supplier", foreign_keys="Procurement.supplier_id"
    )


class Procurement(TimestampMixin, Base):
    __tablename__ = "procurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    buyer_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    currency: Mapped[str] = mapped_column(String(3), default="UAH")
    announced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    buyer: Mapped[Organization] = relationship(back_populates="purchases", foreign_keys=[buyer_id])
    supplier: Mapped[Organization] = relationship(
        back_populates="sales", foreign_keys=[supplier_id]
    )


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[SyncStatus] = mapped_column(
        SAEnum(SyncStatus, native_enum=False, length=16), default=SyncStatus.RUNNING
    )
    records_seen: Mapped[int] = mapped_column(default=0)
    records_created: Mapped[int] = mapped_column(default=0)
    records_updated: Mapped[int] = mapped_column(default=0)
    signals_created: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(255), unique=True)
    signal_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    description: Mapped[str] = mapped_column(Text)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    procurement_id: Mapped[int | None] = mapped_column(ForeignKey("procurements.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Organization | None] = relationship()
    procurement: Mapped[Procurement | None] = relationship()
