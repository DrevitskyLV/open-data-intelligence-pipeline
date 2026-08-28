from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from open_data_intelligence.models import Organization, Procurement, RiskSignal
from open_data_intelligence.services.ingestion import (
    ingest_fixture,
    ingest_records,
    load_fixture_records,
)


def test_first_ingestion_creates_records(db_session: Session) -> None:
    result = ingest_fixture(db_session)
    db_session.commit()
    assert result.seen == 6
    assert result.created == 6
    assert result.updated == 0


def test_second_ingestion_is_idempotent(db_session: Session) -> None:
    ingest_fixture(db_session)
    db_session.commit()
    result = ingest_fixture(db_session)
    db_session.commit()
    assert result.created == 0
    assert result.updated == 6
    assert db_session.scalar(select(func.count()).select_from(Procurement)) == 6


def test_registration_code_variants_resolve_to_one_organization(db_session: Session) -> None:
    ingest_fixture(db_session)
    db_session.commit()
    count = db_session.scalar(
        select(func.count())
        .select_from(Organization)
        .where(Organization.registration_code == "UA500001")
    )
    assert count == 1


def test_ingestion_creates_explainable_signals(db_session: Session) -> None:
    result = ingest_fixture(db_session)
    db_session.commit()
    signal_types = set(db_session.scalars(select(RiskSignal.signal_type)).all())
    assert result.signals_created >= 3
    assert {"short_deadline", "high_value_contract", "supplier_concentration"} <= signal_types


def test_negative_duration_does_not_create_short_deadline_signal(db_session: Session) -> None:
    record = load_fixture_records()[0].model_copy(
        update={
            "external_id": "INVALID-DATE-ORDER",
            "announced_at": datetime(2026, 8, 20, tzinfo=UTC),
            "deadline_at": datetime(2026, 8, 10, tzinfo=UTC),
        }
    )
    ingest_records(db_session, [record])
    db_session.commit()

    fingerprints = set(db_session.scalars(select(RiskSignal.fingerprint)).all())
    assert "short-deadline:INVALID-DATE-ORDER" not in fingerprints
