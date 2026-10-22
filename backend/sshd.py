import asyncio
import datetime as dt
import hashlib
import ipaddress as ipa
import logging
import re
import typing as t

import asyncssh

from bus import EventBus
from config import Settings
from fakeshell import FakeShell
from schemas import SSH_HANDSHAKE_KIND, LoginInfo, RawEvent, Service

logger = logging.getLogger(__name__)

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


SERVER_VERSION = "SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.5"
_SERVER_SOFTWARE_VERSION = SERVER_VERSION.removeprefix("SSH-2.0-")

_HANDSHAKE_POLL_INTERVAL = 0.05
_HANDSHAKE_POLL_ATTEMPTS = 40


def hash_password(password: str) -> str:
    """Hash a captured password at the edge; plaintext never leaves this call."""
    return "sha256:" + hashlib.sha256(password.encode("utf-8")).hexdigest()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class SshHoneypotServer(asyncssh.SSHServer):
    """One instance per TCP connection: accept any credentials, fake the rest."""

    def __init__(self, bus: EventBus[RawEvent]) -> None:
        self._bus = bus
        self._conn: t.Any = None
        self._handshake_emitted = False
        self._handshake_task: asyncio.Task[None] | None = None
        self._credentials: LoginInfo | None = None
        self._peer_ip = "0.0.0.0"
        self._peer_port = 0
        self._destination_ip = "0.0.0.0"
        self._destination_port = 0

    # -- connection lifecycle --------------------------------------------

    def connection_made(self, conn: t.Any) -> None:
        self._conn = conn
        peername = conn.get_extra_info("peername")
        if peername:
            self._peer_ip, self._peer_port = peername[0], peername[1]
        sockname = conn.get_extra_info("sockname")
        if sockname:
            self._destination_ip = sockname[0]
            self._destination_port = sockname[1]

        # The client identification string is only known after the version
        # exchange, which asyncssh performs *after* connection_made().
        self._handshake_task = asyncio.create_task(
            self._capture_handshake(), name="hb-ssh-handshake"
        )

    async def _capture_handshake(self) -> None:
        for _ in range(_HANDSHAKE_POLL_ATTEMPTS):
            if self._conn is None:
                return
            version = self._conn.get_extra_info("client_version")
            if version:
                self._publish_handshake(str(version))
                return
            await asyncio.sleep(_HANDSHAKE_POLL_INTERVAL)

    def connection_lost(self, exc: t.Any) -> None:
        if self._handshake_task is not None:
            self._handshake_task.cancel()
            self._handshake_task = None
        self._conn = None

    # -- authentication ---------------------------------------------------

    def begin_auth(self, username: str) -> bool:
        self._publish_handshake_if_known()
        return True

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        self._publish_handshake_if_known()
        credentials = LoginInfo(
            username=username, password_hash=hash_password(password)
        )
        self._credentials = credentials
        self._bus.publish(
            RawEvent(
                service=Service.SSH,
                source_ip=ipa.ip_address(self._peer_ip),
                destination_ip=ipa.ip_address(self._destination_ip),
                timestamp=_now(),
                source_port=self._peer_port,
                destination_port=self._destination_port,
                login_info=credentials,
                additional_info={"event_kind": "auth"},
            )
        )
        return True

    def session_requested(self) -> "FakeSession":
        return FakeSession(self)

    # -- event helpers ----------------------------------------------------

    def _publish_handshake_if_known(self) -> None:
        if self._handshake_emitted or self._conn is None:
            return
        version = self._conn.get_extra_info("client_version")
        if version:
            self._publish_handshake(str(version))

    def _publish_handshake(self, line: str) -> None:
        if self._handshake_emitted:
            return
        self._handshake_emitted = True
        try:
            event = make_handshake_event(
                source_ip=self._peer_ip,
                source_port=self._peer_port,
                destination_ip=self._destination_ip,
                destination_port=self._destination_port,
                timestamp=_now(),
                line=line,
            )
        except ValueError:
            logger.warning("could not build handshake event for %r", line)
            return
        self._bus.publish(event)

    def publish_command(self, command: str, payload_url: str | None = None) -> None:
        if self._credentials is None:
            return
        self._bus.publish(
            RawEvent(
                service=Service.SSH,
                source_ip=ipa.ip_address(self._peer_ip),
                destination_ip=ipa.ip_address(self._destination_ip),
                timestamp=_now(),
                source_port=self._peer_port,
                destination_port=self._destination_port,
                login_info=self._credentials,
                command=command,
                payload_url=payload_url,
                additional_info={"event_kind": "command"},
            )
        )


class FakeSession(asyncssh.SSHServerSession):
    """Interactive fake shell attached to a single SSH session."""

    def __init__(self, server: SshHoneypotServer) -> None:
        self._server = server
        self._chan: t.Any = None
        self._shell = FakeShell()
        self._buffer = ""
        self._closed = False
        self._interactive = False
        self._line_mode = False

    def connection_made(self, chan: t.Any) -> None:
        self._chan = chan

    def connection_lost(self, exc: t.Any) -> None:
        self._closed = True

    def pty_requested(
        self, term_type: str, term_size: t.Any, term_modes: t.Any
    ) -> bool:
        # Accepting a PTY makes asyncssh enable its own line editor, which
        # echoes keystrokes and hands us one complete line at a time.
        self._line_mode = True
        return True

    def shell_requested(self) -> bool:
        self._interactive = True
        return True

    def session_started(self) -> None:
        if self._interactive:
            self._write(self._shell.prompt())

    def exec_requested(self, command: str) -> bool:
        result = self._shell.dispatch(command)
        self._server.publish_command(command, result.payload_url)
        if result.output:
            self._write(result.output)
            if not result.output.endswith("\n"):
                self._write("\n")
        # Closing the channel before asyncssh has answered the exec request
        # makes some clients hang, so let the request round-trip first.
        asyncio.get_running_loop().call_soon(self._exit, 0)
        return True

    def data_received(self, data: bytes | str, datatype: int | None = None) -> None:
        if isinstance(data, str):
            text = data
        else:
            text = data.decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        if self._line_mode:
            lines = text.split("\n")
            complete, self._buffer = lines[:-1], lines[-1]
            for line in complete:
                if self._closed:
                    return
                self._handle_line(line)
            return

        for char in text:
            if self._closed:
                return
            if char == "\n":
                self._write("\n")
                line, self._buffer = self._buffer, ""
                self._handle_line(line)
            elif char in ("\x7f", "\b"):
                if self._buffer:
                    self._buffer = self._buffer[:-1]
                    self._write("\b \b")
            elif char == "\x03":
                self._buffer = ""
                self._write("^C\n")
                self._write(self._shell.prompt())
            elif char.isprintable():
                self._buffer += char
                self._write(char)

    def _handle_line(self, line: str) -> None:
        if not line.strip():
            self._write(self._shell.prompt())
            return

        result = self._shell.dispatch(line)
        self._server.publish_command(line, result.payload_url)
        if result.output:
            self._write(result.output)
            if not result.output.endswith("\n"):
                self._write("\n")
        if result.exit_requested:
            self._exit(0)
            return
        self._write(self._shell.prompt())

    def _write(self, text: str) -> None:
        if self._chan is None or self._closed:
            return
        self._chan.write(text.replace("\n", "\r\n"))

    def _exit(self, status: int) -> None:
        if self._chan is None or self._closed:
            return
        self._closed = True
        self._chan.exit(status)


async def start_ssh_server(
    settings: Settings,
    bus: EventBus[RawEvent],
    *,
    host: str | None = None,
    port: int | None = None,
) -> asyncssh.SSHAcceptor:
    """Start the SSH honeypot listener with an ephemeral ed25519 host key."""
    return await asyncssh.create_server(
        lambda: SshHoneypotServer(bus),
        host if host is not None else settings.ssh_host,
        port if port is not None else settings.ssh_port,
        server_host_keys=[asyncssh.generate_private_key("ssh-ed25519")],
        server_version=_SERVER_SOFTWARE_VERSION,
    )
