import datetime as dt
import ipaddress as ipa
import re
import typing as t

from schemas import SSH_HANDSHAKE_KIND, RawEvent, Service

MAX_IDENT_STRING_LENGTH = 255

_PROTOCOL_RE = re.compile(r"\d+\.\d+")


def _malformed(raw: str, reason: str) -> dict[str, t.Any]:
    return {
        "ok": False,
        "reason": reason,
        "protocol": None,
        "software": None,
        "comments": None,
        "raw": raw,
    }


def parse_ssh_handshake(line: str) -> dict[str, t.Any]:
    """Parse an RFC 4253 identification string without ever raising.

    Strict on size (255 characters) and on the ``SSH-<major>.<minor>-``
    prefix; permissive on the software tag so scanner banners are still
    recorded instead of dropped.
    """
    raw = line.rstrip("\r\n")
    if not raw:
        return _malformed(raw, "empty")
    if len(raw) > MAX_IDENT_STRING_LENGTH:
        return _malformed(raw, "too long")
    if not raw.startswith("SSH-"):
        return _malformed(raw, "missing prefix")

    protocol, separator, remainder = raw[4:].partition("-")
    if not separator or not _PROTOCOL_RE.fullmatch(protocol):
        return _malformed(raw, "malformed protocol")

    software, _, comments = remainder.partition(" ")
    return {
        "ok": True,
        "reason": None,
        "protocol": protocol,
        "software": software,
        "comments": comments.strip() or None,
        "raw": raw,
    }


def make_handshake_event(
    *,
    source_ip: str,
    source_port: int,
    destination_ip: str,
    destination_port: int,
    timestamp: dt.datetime,
    line: str,
) -> RawEvent:
    """Build the RawEvent emitted when a client opens an SSH connection."""
    parsed = parse_ssh_handshake(line)
    additional_info: dict[str, t.Any] = {
        "event_kind": SSH_HANDSHAKE_KIND,
        "banner": parsed["raw"],
    }
    if parsed["ok"]:
        additional_info["protocol"] = parsed["protocol"]
        additional_info["client_version"] = parsed["software"]
        if parsed["comments"]:
            additional_info["client_comments"] = parsed["comments"]
    else:
        additional_info["malformed"] = parsed["reason"]

    return RawEvent(
        service=Service.SSH,
        source_ip=ipa.ip_address(source_ip),
        destination_ip=ipa.ip_address(destination_ip),
        timestamp=timestamp,
        source_port=source_port,
        destination_port=destination_port,
        additional_info=additional_info,
    )
