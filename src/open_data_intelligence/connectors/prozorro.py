from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from open_data_intelligence.config import settings
from open_data_intelligence.schemas import OrganizationInput, ProcurementInput


class ProzorroConnectorError(RuntimeError):
    """Raised when the connector cannot produce usable procurement records."""


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _Identifier(_ApiModel):
    id: str
    legalName: str | None = None


class _Party(_ApiModel):
    name: str | None = None
    identifier: _Identifier | None = None


class _Money(_ApiModel):
    amount: Decimal
    currency: str = "UAH"


class _Period(_ApiModel):
    startDate: datetime | None = None
    endDate: datetime | None = None


class _Award(_ApiModel):
    id: str
    status: str | None = None
    suppliers: list[_Party] = Field(default_factory=list)
    value: _Money | None = None


class _Tender(_ApiModel):
    id: str
    tenderID: str | None = None
    title: str | None = None
    description: str | None = None
    dateCreated: datetime | None = None
    procuringEntity: _Party | None = None
    datePublished: datetime | None = None
    dateModified: datetime | None = None
    tenderPeriod: _Period | None = None
    awards: list[_Award] = Field(default_factory=list)


class _FeedItem(_ApiModel):
    id: str
    status: str | None = None


class _NextPage(_ApiModel):
    path: str | None = None
    uri: str | None = None


class _FeedPage(_ApiModel):
    data: list[_FeedItem] = Field(default_factory=list)
    next_page: _NextPage | None = None


class _TenderResponse(_ApiModel):
    data: _Tender


def _organization(party: _Party | None) -> OrganizationInput | None:
    if party is None or party.identifier is None:
        return None
    code = party.identifier.id.strip()
    name = (party.identifier.legalName or party.name or "").strip()
    if len(code) < 2 or len(name) < 2:
        return None
    return OrganizationInput(registration_code=code[:64], name=name[:255])


def map_tender_to_procurements(payload: object) -> list[ProcurementInput]:
    """Map one full Prozorro tender response to awarded procurement records."""
    tender = _TenderResponse.model_validate(payload).data
    buyer = _organization(tender.procuringEntity)
    period = tender.tenderPeriod
    deadline_at = period.endDate if period else None
    start_candidates = (
        period.startDate if period else None,
        tender.datePublished,
        tender.dateCreated,
        tender.dateModified,
    )
    announced_at = next(
        (
            candidate
            for candidate in start_candidates
            if candidate is not None and deadline_at is not None and candidate <= deadline_at
        ),
        None,
    )
    title = (tender.title or tender.description or tender.tenderID or tender.id).strip()
    if buyer is None or announced_at is None or deadline_at is None or len(title) < 2:
        return []

    records: list[ProcurementInput] = []
    for award in tender.awards:
        if (award.status or "").casefold() != "active" or award.value is None:
            continue
        if award.value.amount <= 0 or not award.suppliers:
            continue
        supplier = _organization(award.suppliers[0])
        if supplier is None:
            continue
        tender_key = tender.tenderID or tender.id
        external_id = f"{tender_key}:{award.id}"[:100]
        records.append(
            ProcurementInput(
                external_id=external_id,
                title=title[:500],
                buyer=buyer,
                supplier=supplier,
                amount=award.value.amount,
                currency=award.value.currency.upper(),
                announced_at=announced_at,
                deadline_at=deadline_at,
            )
        )
    return records


class ProzorroClient:
    """Small async client for the public OpenProcurement read API."""

    def __init__(
        self,
        *,
        base_url: str = settings.prozorro_api_url,
        timeout_seconds: float = settings.prozorro_timeout_seconds,
        max_retries: int = settings.prozorro_max_retries,
        max_concurrency: int = 5,
        retry_backoff_seconds: float = 0.35,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self.max_retries: int = max(0, max_retries)
        self.max_concurrency: int = max(1, max_concurrency)
        self.retry_backoff_seconds: float = max(0.0, retry_backoff_seconds)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": "open-data-intelligence-pipeline/0.1"},
        )

    async def __aenter__(self) -> ProzorroClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request_json(self, url: str, *, params: dict[str, str] | None = None) -> object:
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(url, params=params)
                retryable = response.status_code == 429 or response.status_code >= 500
                if retryable and attempt < self.max_retries:
                    await asyncio.sleep(self._retry_delay(response, attempt))
                    continue
                response.raise_for_status()
                payload: object = response.json()
                return payload
            except httpx.TransportError:
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_backoff_seconds * (2**attempt))
        raise ProzorroConnectorError("Prozorro request exhausted all retry attempts")

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), 10.0))
            except ValueError:
                pass
        return float(self.retry_backoff_seconds * (2**attempt))

    async def _fetch_tender_records(self, tender_id: str) -> list[ProcurementInput]:
        try:
            payload = await self._request_json(f"{self.base_url}/tenders/{tender_id}")
            return map_tender_to_procurements(payload)
        except (httpx.HTTPError, ValidationError):
            return []

    async def _fetch_page_records(self, tender_ids: list[str]) -> list[ProcurementInput]:
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def fetch(tender_id: str) -> list[ProcurementInput]:
            async with semaphore:
                return await self._fetch_tender_records(tender_id)

        batches = await asyncio.gather(*(fetch(tender_id) for tender_id in tender_ids))
        return [record for batch in batches for record in batch]

    def _next_page_url(self, next_page: _NextPage) -> str | None:
        target = next_page.path or next_page.uri
        if not target:
            return None
        candidate = urljoin(f"{self.base_url}/", target)
        base_parts = urlsplit(self.base_url)
        candidate_parts = urlsplit(candidate)
        if candidate_parts.netloc != base_parts.netloc:
            raise ProzorroConnectorError("Prozorro pagination changed the configured API host")
        return urlunsplit(
            (
                base_parts.scheme,
                base_parts.netloc,
                candidate_parts.path,
                candidate_parts.query,
                "",
            )
        )

    async def fetch_awarded_procurements(
        self,
        *,
        limit: int = 6,
        max_pages: int = 5,
    ) -> list[ProcurementInput]:
        """Fetch recent tenders until enough active awards have been mapped."""
        if limit < 1:
            return []
        page_size = min(max(limit * 3, 10), 50)
        page_url = f"{self.base_url}/tenders"
        params: dict[str, str] | None = {
            "limit": str(page_size),
            "descending": "1",
            "opt_fields": "status",
        }
        records: list[ProcurementInput] = []

        for _ in range(max(1, max_pages)):
            page = _FeedPage.model_validate(await self._request_json(page_url, params=params))
            params = None
            candidate_ids = [
                item.id
                for item in page.data
                if item.status is None or item.status in {"active.awarded", "complete"}
            ]
            page_records = await self._fetch_page_records(candidate_ids)
            records.extend(page_records)
            if len(records) >= limit:
                return records[:limit]

            next_url = self._next_page_url(page.next_page) if page.next_page else None
            if not next_url or not page.data:
                break
            page_url = next_url

        if not records:
            raise ProzorroConnectorError("No recent tenders with usable active awards were found")
        return records[:limit]
