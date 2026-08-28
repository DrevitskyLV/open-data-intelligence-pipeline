from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from open_data_intelligence.models import Organization, Procurement
from open_data_intelligence.schemas import OrganizationInput, ProcurementInput
from open_data_intelligence.services.normalization import (
    normalize_organization_name,
    normalize_registration_code,
)
from open_data_intelligence.services.signals import rebuild_risk_signals


@dataclass(frozen=True, slots=True)
class IngestionResult:
    seen: int
    created: int
    updated: int
    signals_created: int


def default_fixture_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "sample_procurements.json"


def load_fixture_records(path: Path | None = None) -> list[ProcurementInput]:
    fixture_path = path or default_fixture_path()
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    return [ProcurementInput.model_validate(item) for item in raw]


def _upsert_organization(db: Session, payload: OrganizationInput) -> Organization:
    registration_code = normalize_registration_code(payload.registration_code)
    organization = db.scalar(
        select(Organization).where(Organization.registration_code == registration_code)
    )
    normalized_name = normalize_organization_name(payload.name)
    if organization is None:
        organization = Organization(
            registration_code=registration_code,
            name=payload.name.strip(),
            normalized_name=normalized_name,
        )
        db.add(organization)
        db.flush()
    else:
        organization.name = payload.name.strip()
        organization.normalized_name = normalized_name
    return organization


def ingest_fixture(db: Session, path: Path | None = None) -> IngestionResult:
    records = load_fixture_records(path)
    return ingest_records(db, records)


def ingest_records(db: Session, records: list[ProcurementInput]) -> IngestionResult:
    created = 0
    updated = 0

    for payload in records:
        buyer = _upsert_organization(db, payload.buyer)
        supplier = _upsert_organization(db, payload.supplier)
        procurement = db.scalar(
            select(Procurement).where(Procurement.external_id == payload.external_id)
        )
        if procurement is None:
            procurement = Procurement(external_id=payload.external_id)
            db.add(procurement)
            created += 1
        else:
            updated += 1

        procurement.title = payload.title.strip()
        procurement.buyer_id = buyer.id
        procurement.supplier_id = supplier.id
        procurement.amount = payload.amount
        procurement.currency = payload.currency.upper()
        procurement.announced_at = payload.announced_at
        procurement.deadline_at = payload.deadline_at

    db.flush()
    signals_created = rebuild_risk_signals(db)
    return IngestionResult(
        seen=len(records),
        created=created,
        updated=updated,
        signals_created=signals_created,
    )
