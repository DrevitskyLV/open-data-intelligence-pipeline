from __future__ import annotations

import asyncio

import httpx

from open_data_intelligence.connectors.prozorro import (
    ProzorroClient,
    map_tender_to_procurements,
)


def tender_response(tender_id: str, *, award_status: str = "active") -> dict[str, object]:
    return {
        "data": {
            "id": tender_id,
            "tenderID": f"UA-TEST-{tender_id}",
            "title": "Cloud infrastructure services",
            "datePublished": "2026-08-20T10:00:00+03:00",
            "dateModified": "2026-08-25T10:00:00+03:00",
            "tenderPeriod": {
                "startDate": "2026-08-20T10:00:00+03:00",
                "endDate": "2026-08-24T10:00:00+03:00",
            },
            "procuringEntity": {
                "name": "Public Buyer",
                "identifier": {"id": "UA-BUYER-001", "legalName": "Public Buyer LLC"},
            },
            "awards": [
                {
                    "id": f"award-{tender_id}",
                    "status": award_status,
                    "value": {"amount": "245000.50", "currency": "UAH"},
                    "suppliers": [
                        {
                            "name": "Winning Supplier",
                            "identifier": {
                                "id": "UA-SUPPLIER-001",
                                "legalName": "Winning Supplier LLC",
                            },
                        }
                    ],
                }
            ],
        }
    }


def test_tender_mapper_keeps_only_active_awards() -> None:
    active = map_tender_to_procurements(tender_response("active"))
    unsuccessful = map_tender_to_procurements(
        tender_response("unsuccessful", award_status="unsuccessful")
    )

    assert len(active) == 1
    assert active[0].external_id == "UA-TEST-active:award-active"
    assert active[0].buyer.registration_code == "UA-BUYER-001"
    assert active[0].supplier.name == "Winning Supplier LLC"
    assert unsuccessful == []


def test_tender_mapper_prefers_tender_period_start() -> None:
    payload = tender_response("late-publication")
    data = payload["data"]
    assert isinstance(data, dict)
    data["datePublished"] = "2026-08-26T10:00:00+03:00"

    records = map_tender_to_procurements(payload)

    assert len(records) == 1
    assert records[0].announced_at.isoformat() == "2026-08-20T10:00:00+03:00"
    assert records[0].deadline_at > records[0].announced_at


def test_client_follows_next_page_until_it_finds_an_award() -> None:
    requested_offsets: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/tenders"):
            offset = request.url.params.get("offset")
            requested_offsets.append(offset)
            if offset is None:
                return httpx.Response(
                    200,
                    json={
                        "data": [{"id": "first", "status": "active.awarded"}],
                        "next_page": {"uri": "https://unit.test/api/2.5/tenders?offset=page-2"},
                    },
                )
            return httpx.Response(200, json={"data": [{"id": "second", "status": "complete"}]})
        if request.url.path.endswith("/tenders/first"):
            return httpx.Response(200, json=tender_response("first", award_status="pending"))
        return httpx.Response(200, json=tender_response("second"))

    async def scenario() -> list[str]:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            connector = ProzorroClient(
                base_url="https://unit.test/api/2.5",
                client=http_client,
                retry_backoff_seconds=0,
            )
            records = await connector.fetch_awarded_procurements(limit=1, max_pages=2)
            return [record.external_id for record in records]

    assert asyncio.run(scenario()) == ["UA-TEST-second:award-second"]
    assert requested_offsets == [None, "page-2"]


def test_client_retries_transient_feed_failure() -> None:
    feed_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal feed_attempts
        if request.url.path.endswith("/tenders"):
            feed_attempts += 1
            if feed_attempts == 1:
                return httpx.Response(503)
            return httpx.Response(200, json={"data": [{"id": "recovered", "status": "complete"}]})
        return httpx.Response(200, json=tender_response("recovered"))

    async def scenario() -> int:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            connector = ProzorroClient(
                base_url="https://unit.test/api/2.5",
                client=http_client,
                max_retries=1,
                retry_backoff_seconds=0,
            )
            records = await connector.fetch_awarded_procurements(limit=1, max_pages=1)
            return len(records)

    assert asyncio.run(scenario()) == 1
    assert feed_attempts == 2
