"""Initial schema for HoneyBadger.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-11-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create events table
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("service", sa.String(length=16), nullable=False),
        sa.Column("source_ip", postgresql.INET(), nullable=False),
        sa.Column("destination_ip", postgresql.INET(), nullable=False),
        sa.Column("source_port", sa.Integer(), nullable=False),
        sa.Column("destination_port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("http_method", sa.String(length=16), nullable=True),
        sa.Column("http_path", sa.Text(), nullable=True),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("payload_url", sa.Text(), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.Column("payload_size", sa.BigInteger(), nullable=True),
        sa.Column("technique_id", sa.String(length=32), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("asn", sa.String(length=128), nullable=True),
        sa.Column("additional_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_events_source_ip_ts", "events", ["source_ip", "ts"], unique=False
    )
    op.create_index("ix_events_service_ts", "events", ["service", "ts"], unique=False)
    op.create_index(
        "ix_events_technique_ts", "events", ["technique_id", "ts"], unique=False
    )
    op.create_index(
        "ix_events_severity_ts", "events", ["severity", "ts"], unique=False
    )
    op.create_index("ix_events_payload_url", "events", ["payload_url"], unique=False)

    # Create credential_counts table
    op.create_table(
        "credential_counts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", "password_hash", name="uq_credential_pair"),
    )
    op.create_index(
        "ix_credential_counts_count", "credential_counts", ["count"], unique=False
    )
    op.create_index(
        "ix_credential_counts_last_seen",
        "credential_counts",
        ["last_seen"],
        unique=False,
    )

    # Create payloads table
    op.create_table(
        "payloads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("quarantined", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("quarantine_path", sa.Text(), nullable=True),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(
        "ix_payloads_first_seen", "payloads", ["first_seen"], unique=False
    )
    op.create_index(
        "ix_payloads_quarantined", "payloads", ["quarantined"], unique=False
    )

    # Create geoip_cache table
    op.create_table(
        "geoip_cache",
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("asn", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("ip"),
    )
    op.create_index(
        "ix_geoip_cache_expires_at", "geoip_cache", ["expires_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_geoip_cache_expires_at", table_name="geoip_cache")
    op.drop_table("geoip_cache")

    op.drop_index("ix_payloads_quarantined", table_name="payloads")
    op.drop_index("ix_payloads_first_seen", table_name="payloads")
    op.drop_table("payloads")

    op.drop_index("ix_credential_counts_last_seen", table_name="credential_counts")
    op.drop_index("ix_credential_counts_count", table_name="credential_counts")
    op.drop_table("credential_counts")

    op.drop_index("ix_events_payload_url", table_name="events")
    op.drop_index("ix_events_severity_ts", table_name="events")
    op.drop_index("ix_events_technique_ts", table_name="events")
    op.drop_index("ix_events_service_ts", table_name="events")
    op.drop_index("ix_events_source_ip_ts", table_name="events")
    op.drop_table("events")