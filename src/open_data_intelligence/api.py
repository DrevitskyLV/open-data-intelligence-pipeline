from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from open_data_intelligence.config import settings
from open_data_intelligence.connectors.prozorro import ProzorroClient
from open_data_intelligence.db import get_db
from open_data_intelligence.models import Organization, Procurement, RiskSignal, SyncRun, SyncStatus
from open_data_intelligence.schemas import (
    HealthRead,
    OrganizationDetail,
    OrganizationRead,
    ProcurementInput,
    ProcurementRead,
    RelationshipRead,
    RiskSignalRead,
    SyncRunCreate,
    SyncRunRead,
)
from open_data_intelligence.services.ingestion import ingest_fixture, ingest_records

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_db)]


async def fetch_prozorro_records(limit: int) -> list[ProcurementInput]:
    async with ProzorroClient() as client:
        return await client.fetch_awarded_procurements(limit=limit)


@router.get("/health", response_model=HealthRead, tags=["system"])
def health() -> HealthRead:
    return HealthRead(status="ok", environment=settings.app_env)


@router.post(
    "/sync-runs",
    response_model=SyncRunRead,
    status_code=status.HTTP_201_CREATED,
    tags=["ingestion"],
)
async def create_sync_run(payload: SyncRunCreate, db: DbSession) -> SyncRun:
    run = SyncRun(id=str(uuid4()), source=payload.source, status=SyncStatus.RUNNING)
    db.add(run)
    db.commit()

    try:
        if payload.source == "prozorro":
            records = await fetch_prozorro_records(payload.limit)
            result = ingest_records(db, records)
        else:
            result = ingest_fixture(db)
        completed_run = db.get(SyncRun, run.id)
        if completed_run is None:
            raise RuntimeError("Sync run disappeared during processing")
        completed_run.status = SyncStatus.COMPLETED
        completed_run.records_seen = result.seen
        completed_run.records_created = result.created
        completed_run.records_updated = result.updated
        completed_run.signals_created = result.signals_created
        completed_run.finished_at = datetime.now(UTC)
        db.commit()
        db.refresh(completed_run)
        return completed_run
    except Exception as exc:
        db.rollback()
        failed_run = db.get(SyncRun, run.id)
        if failed_run is not None:
            failed_run.status = SyncStatus.FAILED
            failed_run.error_message = str(exc)[:1000]
            failed_run.finished_at = datetime.now(UTC)
            db.commit()
        raise HTTPException(status_code=500, detail="Synchronization failed") from exc


@router.get("/sync-runs/{run_id}", response_model=SyncRunRead, tags=["ingestion"])
def get_sync_run(run_id: str, db: DbSession) -> SyncRun:
    run = db.get(SyncRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Sync run not found")
    return run


@router.get("/organizations", response_model=list[OrganizationRead], tags=["organizations"])
def list_organizations(
    db: DbSession,
    query: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Organization]:
    statement = select(Organization).order_by(Organization.name).limit(limit).offset(offset)
    if query:
        term = f"%{query.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(Organization.name).like(term),
                func.lower(Organization.normalized_name).like(term),
                func.lower(Organization.registration_code).like(term),
            )
        )
    return list(db.scalars(statement).all())


@router.get(
    "/organizations/{organization_id}", response_model=OrganizationDetail, tags=["organizations"]
)
def get_organization(organization_id: int, db: DbSession) -> OrganizationDetail:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    purchases_count = db.scalar(
        select(func.count()).select_from(Procurement).where(Procurement.buyer_id == organization_id)
    )
    sales_count = db.scalar(
        select(func.count())
        .select_from(Procurement)
        .where(Procurement.supplier_id == organization_id)
    )
    return OrganizationDetail(
        id=organization.id,
        registration_code=organization.registration_code,
        name=organization.name,
        normalized_name=organization.normalized_name,
        purchases_count=purchases_count or 0,
        sales_count=sales_count or 0,
    )


@router.get(
    "/organizations/{organization_id}/relationships",
    response_model=list[RelationshipRead],
    tags=["organizations"],
)
def get_relationships(organization_id: int, db: DbSession) -> list[RelationshipRead]:
    if db.get(Organization, organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    relationships: list[RelationshipRead] = []
    purchase_rows = db.execute(
        select(
            Organization.id,
            Organization.name,
            func.count(Procurement.id),
            func.sum(Procurement.amount),
        )
        .join(Procurement, Procurement.supplier_id == Organization.id)
        .where(Procurement.buyer_id == organization_id)
        .group_by(Organization.id, Organization.name)
    ).all()
    for counterparty_id, name, count, total in purchase_rows:
        relationships.append(
            RelationshipRead(
                counterparty_id=counterparty_id,
                counterparty_name=name,
                relation_type="buys_from",
                procurements_count=count,
                total_amount=Decimal(total),
            )
        )

    sales_rows = db.execute(
        select(
            Organization.id,
            Organization.name,
            func.count(Procurement.id),
            func.sum(Procurement.amount),
        )
        .join(Procurement, Procurement.buyer_id == Organization.id)
        .where(Procurement.supplier_id == organization_id)
        .group_by(Organization.id, Organization.name)
    ).all()
    for counterparty_id, name, count, total in sales_rows:
        relationships.append(
            RelationshipRead(
                counterparty_id=counterparty_id,
                counterparty_name=name,
                relation_type="sells_to",
                procurements_count=count,
                total_amount=Decimal(total),
            )
        )
    return relationships


@router.get("/procurements", response_model=list[ProcurementRead], tags=["procurements"])
def list_procurements(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Procurement]:
    statement = (
        select(Procurement)
        .options(joinedload(Procurement.buyer), joinedload(Procurement.supplier))
        .order_by(Procurement.announced_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


@router.get("/risk-signals", response_model=list[RiskSignalRead], tags=["analytics"])
def list_risk_signals(
    db: DbSession,
    signal_type: str | None = None,
    severity: str | None = None,
) -> list[RiskSignal]:
    statement = select(RiskSignal).order_by(RiskSignal.created_at.desc())
    if signal_type:
        statement = statement.where(RiskSignal.signal_type == signal_type)
    if severity:
        statement = statement.where(RiskSignal.severity == severity)
    return list(db.scalars(statement).all())
