"""Create core intelligence tables.

Revision ID: 20260808_0001
Revises:
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("registration_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("registration_code"),
    )
    op.create_index("ix_organizations_registration_code", "organizations", ["registration_code"])
    op.create_index("ix_organizations_normalized_name", "organizations", ["normalized_name"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("records_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "procurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_procurements_external_id", "procurements", ["external_id"])
    op.create_index("ix_procurements_buyer_id", "procurements", ["buyer_id"])
    op.create_index("ix_procurements_supplier_id", "procurements", ["supplier_id"])

    op.create_table(
        "risk_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fingerprint", sa.String(length=255), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True
        ),
        sa.Column("procurement_id", sa.Integer(), sa.ForeignKey("procurements.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_index("ix_risk_signals_signal_type", "risk_signals", ["signal_type"])
    op.create_index("ix_risk_signals_severity", "risk_signals", ["severity"])


def downgrade() -> None:
    op.drop_table("risk_signals")
    op.drop_table("procurements")
    op.drop_table("sync_runs")
    op.drop_table("organizations")
