from __future__ import annotations

from collections import Counter
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from open_data_intelligence.models import Procurement, RiskSignal


def rebuild_risk_signals(db: Session) -> int:
    db.execute(delete(RiskSignal))
    procurements = list(db.scalars(select(Procurement)).all())
    created = 0

    for item in procurements:
        tender_days = (item.deadline_at - item.announced_at).total_seconds() / 86_400
        if tender_days <= 3:
            db.add(
                RiskSignal(
                    fingerprint=f"short-deadline:{item.external_id}",
                    signal_type="short_deadline",
                    severity="medium",
                    description=(
                        f"Procurement {item.external_id} accepted bids for only "
                        f"{tender_days:.1f} days."
                    ),
                    organization_id=item.buyer_id,
                    procurement_id=item.id,
                )
            )
            created += 1

        if item.amount >= Decimal("1000000"):
            high_value_description = f"Procurement {item.external_id} exceeds 1,000,000 "
            high_value_description += f"{item.currency}."
            db.add(
                RiskSignal(
                    fingerprint=f"high-value:{item.external_id}",
                    signal_type="high_value_contract",
                    severity="low",
                    description=high_value_description,
                    organization_id=item.buyer_id,
                    procurement_id=item.id,
                )
            )
            created += 1

    by_buyer: dict[int, list[Procurement]] = {}
    for item in procurements:
        by_buyer.setdefault(item.buyer_id, []).append(item)

    for buyer_id, items in by_buyer.items():
        if len(items) < 3:
            continue
        supplier_counts = Counter(item.supplier_id for item in items)
        supplier_id, count = supplier_counts.most_common(1)[0]
        share = count / len(items)
        if share >= 0.60:
            db.add(
                RiskSignal(
                    fingerprint=f"supplier-concentration:{buyer_id}:{supplier_id}",
                    signal_type="supplier_concentration",
                    severity="medium",
                    description=(
                        f"One supplier received {count} of {len(items)} procurements "
                        f"from organization {buyer_id} ({share:.0%})."
                    ),
                    organization_id=buyer_id,
                )
            )
            created += 1

    db.flush()
    return created
