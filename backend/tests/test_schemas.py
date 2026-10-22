import datetime as dt

import pytest
from pydantic import ValidationError

from schemas import EnrichedEvent, RawEvent, Service

UTC = dt.timezone.utc
TS = dt.datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)

SSH_LOGIN = {"username": "root", "password_hash": "sha256:" + "ab" * 32}


def make_raw(**overrides):
    base = {
        "service": Service.SSH,
        "source_ip": "1.2.3.4",
        "destination_ip": "5.6.7.8",
        "timestamp": TS,
        "source_port": 54321,
        "destination_port": 22,
        "login_info": SSH_LOGIN,
    }
    base.update(overrides)
    return RawEvent(**base)


def test_valid_ssh_event():
    event = make_raw()
    assert event.service is Service.SSH
    assert event.login_info.username == "root"
    assert event.source_port == 54321


def test_password_hash_normalized_to_lowercase():
    event = make_raw(
        login_info={"username": "root", "password_hash": "SHA256:" + "AB" * 32}
    )
    assert event.login_info.password_hash == "sha256:" + "ab" * 32


@pytest.mark.parametrize(
    "bad_hash",
    ["password123", "sha256:" + "ab" * 63, "sha256:" + "ab" * 32 + "ZZ"],
)
def test_invalid_password_hash_rejected(bad_hash):
    with pytest.raises(ValidationError):
        make_raw(login_info={"username": "root", "password_hash": bad_hash})


def test_ssh_event_without_login_rejected():
    with pytest.raises(ValidationError):
        make_raw(login_info=None)


def test_ssh_event_with_partial_login_rejected():
    with pytest.raises(ValidationError):
        make_raw(login_info={"username": "root"})


def test_http_event_without_login_accepted():
    event = make_raw(service=Service.HTTP, destination_port=80, login_info=None)
    assert event.login_info is None


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError):
        make_raw(timestamp=dt.datetime(2026, 6, 6, 12, 0, 0))


def test_enriched_event_with_optional_fields():
    event = EnrichedEvent(
        **make_raw().model_dump(),
        geo_info={"country": "FR", "city": "Paris"},
        technique_id="T1110",
        severity="high",
    )
    assert event.technique_id == "T1110"
    assert event.severity.value == "high"
    assert event.geo_info.country == "FR"


def test_enriched_event_invalid_technique_rejected():
    with pytest.raises(ValidationError):
        EnrichedEvent(**make_raw().model_dump(), technique_id="T9999")