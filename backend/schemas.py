import pydantic as pydantic
import ipaddress as ipa
import typing as t
import re
import datetime as dt
from enum import Enum


class Service(Enum):
    """Enum for the different services."""
    SSH = "ssh"
    HTTP = "http"


class Severity(Enum):
    """Enum for the different severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LoginInfo(pydantic.BaseModel):
    """Schema for login information."""
    username: str | None = None
    password_hash: str | None = None

    @pydantic.field_validator("password_hash")
    @classmethod
    def validate_password_hash(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", value, re.IGNORECASE):
            raise ValueError('password_hash must be "sha256:<64 hex digits>"')
        return value.lower()


class GeoInfo(pydantic.BaseModel):
    """Schema for geographical information."""
    country: str | None = None
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    asn: str | None = None


class RawEvent(pydantic.BaseModel):
    """Schema for raw event data."""
    service: Service
    source_ip: ipa.IPv4Address | ipa.IPv6Address
    destination_ip: ipa.IPv4Address | ipa.IPv6Address
    timestamp: dt.datetime
    login_info: LoginInfo | None = None
    user_agent: str | None = None
    http_method: str | None = None
    http_path: str | None = None
    http_status_code: int | None = None
    command: str | None = None
    payload_url: str | None = None
    payload_hash: str | None = None
    payload_size: int | None = None
    source_port: int
    destination_port: int
    additional_info: t.Dict[str, t.Any] | None = None

    @pydantic.field_validator("timestamp")
    @classmethod
    def validate_timestamp_aware(cls, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @pydantic.model_validator(mode="after")
    def validate_login_requirement(self) -> "RawEvent":
        if self.service is Service.SSH:
            if (
                self.login_info is None
                or not self.login_info.username
                or not self.login_info.password_hash
            ):
                raise ValueError(
                    "SSH events require login_info with username and password_hash"
                )
        return self


class EnrichedEvent(RawEvent):
    """Schema for enriched event data."""
    geo_info: GeoInfo | None = None
    technique_id: t.Literal[
        "T1110", "T1110.004", "T1595", "T1190", "T1105", "T1059", "T1078"
    ] | None = None
    severity: Severity | None = None


class EventOut(pydantic.BaseModel):
    """Schema for event output to the dashboard."""
    model_config = pydantic.ConfigDict(from_attributes=True)

    service: Service
    source_ip: ipa.IPv4Address | ipa.IPv6Address
    timestamp: dt.datetime
    login_info: LoginInfo | None = None
    user_agent: str | None = None
    http_method: str | None = None
    http_path: str | None = None
    http_status_code: int | None = None
    command: str | None = None
    payload_url: str | None = None
    payload_hash: str | None = None
    payload_size: int | None = None
    geo_info: GeoInfo | None = None
    technique_id: str | None = None
    severity: Severity | None = None