import pytest
from pydantic import ValidationError

from config import Settings, get_settings


def test_defaults_match_spec():
    s = Settings()
    assert s.ssh_port == 8022
    assert s.http_port == 8081
    assert s.metrics_port == 8000
    assert s.api_port == 8090
    assert s.capture_payloads is False
    assert s.enable_simulator is False
    assert s.quarantine_dir.as_posix() == "/opt/hb-quarantine"
    assert s.retention_days == 180
    assert s.geoip_provider == "ip-api"
    assert s.database_url.startswith("postgresql+asyncpg://")


def test_env_override(monkeypatch):
    monkeypatch.setenv("HB_SSH_PORT", "2222")
    assert Settings().ssh_port == 2222


def test_port_bounds_rejected():
    with pytest.raises(ValidationError):
        Settings(ssh_port=70000)


def test_retention_days_rejected():
    with pytest.raises(ValidationError):
        Settings(retention_days=0)


def test_non_asyncpg_url_rejected():
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://user:pass@localhost/db")


def test_get_settings_is_cached():
    get_settings.cache_clear()
    assert get_settings() is get_settings()


def test_secret_key_hides_value(monkeypatch):
    monkeypatch.setenv("HB_MAXMIND_LICENSE_KEY", "supersecret")
    s = Settings()
    assert s.maxmind_license_key.get_secret_value() == "supersecret"
    assert "supersecret" not in repr(s.maxmind_license_key)