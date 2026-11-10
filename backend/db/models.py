"""SQLAlchemy models for HoneyBadger.

Defines the database schema for events, credential counts, payloads, and GeoIP cache.
Uses SQLAlchemy 2.0 declarative style with asyncpg.
"""

import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Event(Base):
    """One row per captured interaction (SSH or HTTP)."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Service identification
    service: Mapped[str] = mapped_column(String(16), nullable=False)  # "ssh" | "http"

    # Network info
    source_ip: Mapped[str] = mapped_column(INET, nullable=False)
    destination_ip: Mapped[str] = mapped_column(INET, nullable=False)
    source_port: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_port: Mapped[int] = mapped_column(Integer, nullable=False)

    # Authentication (hashed only)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # HTTP-specific
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    http_method: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    http_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    http_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Command / payload
    command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Enrichment
    technique_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # GeoIP
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    asn: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Raw additional info (JSONB)
    additional_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_events_source_ip_ts", "source_ip", "ts"),
        Index("ix_events_service_ts", "service", "ts"),
        Index("ix_events_technique_ts", "technique_id", "ts"),
        Index("ix_events_severity_ts", "severity", "ts"),
        Index("ix_events_payload_url", "payload_url"),
    )


class CredentialCount(Base):
    """Aggregate counters for top-N credential pairs (dashboard)."""

    __tablename__ = "credential_counts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("username", "password_hash", name="uq_credential_pair"),
        Index("ix_credential_counts_count", "count"),
        Index("ix_credential_counts_last_seen", "last_seen"),
    )


class Payload(Base):
    """Payload metadata captured from wget/curl commands."""

    __tablename__ = "payloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    quarantined: Mapped[bool] = mapped_column(nullable=False, default=False)
    quarantine_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_seen: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_payloads_first_seen", "first_seen"),
        Index("ix_payloads_quarantined", "quarantined"),
    )


class GeoIPCache(Base):
    """Cached GeoIP lookups with TTL."""

    __tablename__ = "geoip_cache"

    ip: Mapped[str] = mapped_column(INET, primary_key=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    asn: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("ix_geoip_cache_expires_at", "expires_at"),
    )