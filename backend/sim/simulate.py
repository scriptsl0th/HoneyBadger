"""Attack simulator for HoneyBadger.

Generates realistic attack traffic against both SSH and HTTP honeypots
for demos and integration testing.

Usage:
    python -m backend.sim.simulate [--duration SECONDS] [--scenario NAME]
"""

import argparse
import asyncio
import logging
import sys

from config import get_settings
from schemas import Service

logger = logging.getLogger(__name__)

SCENARIOS = [
    "credential_stuffing",      # T1110.004 - repeated creds
    "brute_force_ssh",          # T1110 - password spraying
    "web_scanner",              # T1595 - common path probes
    "exploit_attempts",         # T1190 - SQLi, RCE payloads
    "payload_download",         # T1105 - wget/curl in shell
    "post_exploitation",        # T1059, T1078 - commands after "success"
]


async def run_scenario(scenario: str, target_host: str, target_port: int, duration: int) -> None:
    """Run a single attack scenario."""
    logger.info("Running scenario: %s against %s:%d for %ds", scenario, target_host, target_port, duration)
    # TODO: Implement actual attack simulation
    await asyncio.sleep(duration)


async def run_all(target_host: str, ssh_port: int, http_port: int, duration: int) -> None:
    """Run all scenarios sequentially."""
    for scenario in SCENARIOS:
        if scenario in ("credential_stuffing", "brute_force_ssh", "payload_download", "post_exploitation"):
            await run_scenario(scenario, target_host, ssh_port, duration // len(SCENARIOS))
        else:
            await run_scenario(scenario, target_host, http_port, duration // len(SCENARIOS))


def main() -> None:
    parser = argparse.ArgumentParser(description="HoneyBadger attack simulator")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--scenario", choices=SCENARIOS + ["all"], default="all", help="Scenario to run")
    parser.add_argument("--host", default="127.0.0.1", help="Target host")
    parser.add_argument("--ssh-port", type=int, default=8022, help="SSH port")
    parser.add_argument("--http-port", type=int, default=8081, help="HTTP port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings = get_settings()

    if args.scenario == "all":
        asyncio.run(run_all(args.host, args.ssh_port, args.http_port, args.duration))
    else:
        port = args.ssh_port if args.scenario in ("credential_stuffing", "brute_force_ssh", "payload_download", "post_exploitation") else args.http_port
        asyncio.run(run_scenario(args.scenario, args.host, port, args.duration))


if __name__ == "__main__":
    main()