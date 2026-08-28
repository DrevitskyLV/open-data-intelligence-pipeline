from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from open_data_intelligence.models import SyncStatus


class OrganizationInput(BaseModel):
    registration_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=255)


class ProcurementInput(BaseModel):
    external_id: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=2, max_length=500)
    buyer: OrganizationInput
    supplier: OrganizationInput
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="UAH", min_length=3, max_length=3)
    announced_at: datetime
    deadline_at: datetime


class SyncRunCreate(BaseModel):
    source: Literal["fixtures", "prozorro"] = "fixtures"
    limit: int = Field(default=6, ge=1, le=20)


class SyncRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    status: SyncStatus
    records_seen: int
    records_created: int
    records_updated: int
    signals_created: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_code: str
    name: str
    normalized_name: str


class ProcurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    title: str
    amount: Decimal
    currency: str
    announced_at: datetime
    deadline_at: datetime
    buyer: OrganizationRead
    supplier: OrganizationRead


class OrganizationDetail(OrganizationRead):
    purchases_count: int
    sales_count: int


class RelationshipRead(BaseModel):
    counterparty_id: int
    counterparty_name: str
    relation_type: str
    procurements_count: int
    total_amount: Decimal


class RiskSignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    signal_type: str
    severity: str
    description: str
    organization_id: int | None
    procurement_id: int | None
    created_at: datetime


class HealthRead(BaseModel):
    status: str
    environment: str
