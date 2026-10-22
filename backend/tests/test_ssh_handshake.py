import datetime as dt

import pytest
from pydantic import ValidationError

from sshd import (
    MAX_IDENT_STRING_LENGTH,
    make_handshake_event,
    parse_ssh_handshake,
)

UTC = dt.timezone.utc
TS = dt.datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)


def test_parses_openssh_banner():
    parsed = parse_ssh_handshake("SSH-2.0-OpenSSH_8.9p1")
    assert parsed["ok"] is True
    assert parsed["protocol"] == "2.0"
    assert parsed["software"] == "OpenSSH_8.9p1"
    assert parsed["comments"] is None
    assert parsed["reason"] is None


def test_parses_banner_with_comments():
    parsed = parse_ssh_handshake("SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1")
    assert parsed["software"] == "OpenSSH_8.9p1"
    assert parsed["comments"] == "Ubuntu-3ubuntu0.1"


def test_keeps_hyphenated_software_version():
    parsed = parse_ssh_handshake("SSH-2.0-libssh-0.9.6")
    assert parsed["ok"] is True
    assert parsed["software"] == "libssh-0.9.6"


def test_accepts_legacy_protocol_version():
    parsed = parse_ssh_handshake("SSH-1.99-OpenSSH_5.3p1")
    assert parsed["ok"] is True
    assert parsed["protocol"] == "1.99"


def test_strips_trailing_crlf():
    parsed = parse_ssh_handshake("SSH-2.0-OpenSSH_8.9\r\n")
    assert parsed["ok"] is True
    assert parsed["raw"] == "SSH-2.0-OpenSSH_8.9"


def test_rejects_empty_line():
    parsed = parse_ssh_handshake("")
    assert parsed["ok"] is False
    assert parsed["reason"] == "empty"


@pytest.mark.parametrize(
    "line", ["DROPBEAR_0.8", "GET / HTTP/1.1", "\x00\x00\x00\x00"]
)
def test_rejects_non_ssh_banner(line):
    parsed = parse_ssh_handshake(line)
    assert parsed["ok"] is False
    assert parsed["reason"] == "missing prefix"


@pytest.mark.parametrize("line", ["SSH-foo-bar", "SSH-2-x", "SSH-2.0"])
def test_rejects_malformed_protocol(line):
    parsed = parse_ssh_handshake(line)
    assert parsed["ok"] is False
    assert parsed["reason"] == "malformed protocol"


def test_rejects_overlong_identification_string():
    line = "SSH-2.0-" + "a" * (MAX_IDENT_STRING_LENGTH - 7)
    assert len(line) == MAX_IDENT_STRING_LENGTH + 1
    parsed = parse_ssh_handshake(line)
    assert parsed["ok"] is False
    assert parsed["reason"] == "too long"


def test_accepts_identification_string_at_size_limit():
    line = "SSH-2.0-" + "a" * (MAX_IDENT_STRING_LENGTH - 8)
    assert len(line) == MAX_IDENT_STRING_LENGTH
    assert parse_ssh_handshake(line)["ok"] is True


def test_accepts_empty_software_version():
    parsed = parse_ssh_handshake("SSH-2.0-")
    assert parsed["ok"] is True
    assert parsed["software"] == ""
    assert parsed["comments"] is None


def test_multiple_spaces_collapse_in_comments():
    parsed = parse_ssh_handshake("SSH-2.0-OpenSSH_8.9   extra words")
    assert parsed["software"] == "OpenSSH_8.9"
    assert parsed["comments"] == "extra words"


def test_prefix_is_case_sensitive():
    parsed = parse_ssh_handshake("ssh-2.0-OpenSSH_8.9")
    assert parsed["ok"] is False
    assert parsed["reason"] == "missing prefix"


def handshake_event(line="SSH-2.0-OpenSSH_8.9p1", timestamp=TS):
    return make_handshake_event(
        source_ip="203.0.113.7",
        source_port=54321,
        destination_ip="10.0.0.2",
        destination_port=22,
        timestamp=timestamp,
        line=line,
    )


def test_make_handshake_event_builds_valid_raw_event():
    event = handshake_event()
    assert event.service.value == "ssh"
    assert event.login_info is None
    assert event.timestamp == TS
    info = event.additional_info
    assert info is not None
    assert info["event_kind"] == "ssh_handshake"
    assert info["client_version"] == "OpenSSH_8.9p1"
    assert info["protocol"] == "2.0"


def test_make_handshake_event_marks_malformed_banner():
    event = handshake_event(line="DROPBEAR_0.8")
    info = event.additional_info
    assert info is not None
    assert info["malformed"] == "missing prefix"
    assert "client_version" not in info


def test_make_handshake_event_requires_aware_timestamp():
    with pytest.raises(ValidationError):
        handshake_event(timestamp=dt.datetime(2026, 6, 6, 12, 0, 0))
