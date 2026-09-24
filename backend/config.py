from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="HB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ssh_host: str = "0.0.0.0"
    ssh_port: int = Field(8022, ge=1, le=65535)
    http_host: str = "0.0.0.0"
    http_port: int = Field(8081, ge=1, le=65535)
    metrics_port: int = Field(8000, ge=1, le=65535)
    api_host: str = "0.0.0.0"
    api_port: int = Field(8090, ge=1, le=65535)

    database_url: str = (
        "postgresql+asyncpg://honeybadger:honeybadger@postgres:5432/honeybadger"
    )

    geoip_provider: Literal["ip-api", "maxmind"] = "ip-api"
    geoip_cache_ttl_days: int = Field(30, ge=1)
    maxmind_db_path: Path | None = None
    maxmind_license_key: SecretStr | None = None

    capture_payloads: bool = False
    quarantine_dir: Path = Path("/opt/hb-quarantine")

    enable_simulator: bool = False
    retention_days: int = Field(180, ge=1)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use the asyncpg driver")
        return value

@lru_cache
def get_settings() -> Settings:
    """Get the application settings, cached for performance."""
    return Settings() #type: ignore