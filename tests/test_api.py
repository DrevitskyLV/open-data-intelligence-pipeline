import pytest
from fastapi.testclient import TestClient

import open_data_intelligence.api as api_module
from open_data_intelligence.schemas import ProcurementInput
from open_data_intelligence.services.ingestion import load_fixture_records


def run_sync(client: TestClient) -> dict:
    response = client.post("/api/v1/sync-runs", json={"source": "fixtures"})
    assert response.status_code == 201
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_is_available(client: TestClient) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Open Data Intelligence" in response.text
    assert "Load demo dataset" in response.text
    assert "Load live Prozorro" in response.text


def test_live_prozorro_sync_uses_connector(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_record = load_fixture_records()[0]
    live_record = ProcurementInput.model_validate(
        {**source_record.model_dump(), "external_id": "UA-LIVE-001:award-001"}
    )

    async def fake_fetch(limit: int) -> list[ProcurementInput]:
        assert limit == 1
        return [live_record]

    monkeypatch.setattr(api_module, "fetch_prozorro_records", fake_fetch)
    response = client.post("/api/v1/sync-runs", json={"source": "prozorro", "limit": 1})

    assert response.status_code == 201
    assert response.json()["source"] == "prozorro"
    assert response.json()["records_created"] == 1


def test_sync_run_can_be_polled(client: TestClient) -> None:
    created = run_sync(client)
    response = client.get(f"/api/v1/sync-runs/{created['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_unknown_sync_run_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/sync-runs/unknown")
    assert response.status_code == 404


def test_organizations_can_be_searched(client: TestClient) -> None:
    run_sync(client)
    response = client.get("/api/v1/organizations", params={"query": "energy"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_procurements_include_buyer_and_supplier(client: TestClient) -> None:
    run_sync(client)
    response = client.get("/api/v1/procurements")
    assert response.status_code == 200
    assert len(response.json()) == 6
    assert "buyer" in response.json()[0]
    assert "supplier" in response.json()[0]


def test_relationships_are_aggregated(client: TestClient) -> None:
    run_sync(client)
    organization = client.get("/api/v1/organizations", params={"query": "energy"}).json()[0]
    response = client.get(f"/api/v1/organizations/{organization['id']}/relationships")
    assert response.status_code == 200
    assert any(item["relation_type"] == "buys_from" for item in response.json())


def test_signals_can_be_filtered(client: TestClient) -> None:
    run_sync(client)
    response = client.get("/api/v1/risk-signals", params={"signal_type": "short_deadline"})
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(item["signal_type"] == "short_deadline" for item in response.json())
