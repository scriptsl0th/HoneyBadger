"""aiohttp HTTP honeypot server (internet-facing edge).

Listens on port 8081, serves bait responses, captures all interactions,
and publishes raw events to the event bus.
"""

import hashlib
import logging
import time
from typing import Optional

import aiohttp
from aiohttp import web
from aiohttp.web_request import Request

from bus import EventBus
from config import Settings
from http_routes import BAIT_ROUTES, is_bait_path, select_bait
from metrics import (
    record_credential_attempt,
    record_http_bait_hit,
    record_http_latency,
    record_http_request,
)
from schemas import LoginInfo, RawEvent, Service

logger = logging.getLogger(__name__)


class HttpHoneypot:
    """HTTP honeypot server with bait routes and request capture."""

    def __init__(
        self,
        settings: Settings,
        raw_bus: EventBus[RawEvent],
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self._settings = settings
        self._raw_bus = raw_bus
        self._app = web.Application(middlewares=[self._capture_middleware])
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up catch-all route for bait responses."""
        # Catch-all for any path/method
        self._app.router.add_route("*", "/{tail:.*}", self._handle_request)

    @web.middleware
    async def _capture_middleware(self, request: Request, handler):
        """Middleware to capture request info before handling."""
        # Store start time for latency
        request["hb_start_time"] = time.time()
        # Read body for credential capture (if POST to login)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                request["hb_body"] = await request.read()
            except Exception:
                request["hb_body"] = b""
        else:
            request["hb_body"] = b""
        return await handler(request)

    async def _handle_request(self, request: Request) -> web.Response:
        """Handle incoming HTTP request with bait response."""
        path = request.path
        method = request.method
        start_time = request.get("hb_start_time", time.time())
        body = request.get("hb_body", b"")

        # Select bait response
        bait_handler = select_bait(path, method)

        if bait_handler:
            # Known bait path - serve the fake response
            response = bait_handler(request)
            bait_hit = True
            # Record bait hit metric
            record_http_bait_hit(path)
        else:
            # Unknown path - return 404 but still log
            response = web.Response(
                text="<html><body><h1>404 Not Found</h1></body></html>",
                status=404,
                content_type="text/html",
            )
            bait_hit = False

        # Capture credentials from login POSTs
        login_info = None
        if method == "POST" and path in ("/login", "/wp-login.php", "/phpmyadmin", "/admin"):
            login_info = self._extract_credentials(path, body)
            if login_info:
                record_credential_attempt("http", login_info.username)

        # Record HTTP request metric
        record_http_request(method, path, response.status)
        record_http_latency(time.time() - start_time)

        # Publish raw event
        await self._publish_event(
            request=request,
            response=response,
            path=path,
            method=method,
            login_info=login_info,
            bait_hit=bait_hit,
            latency=time.time() - start_time,
        )

        return response

    def _extract_credentials(self, path: str, body: bytes) -> Optional[LoginInfo]:
        """Extract and hash credentials from login POST body."""
        if not body:
            return None

        try:
            content_type = "application/x-www-form-urlencoded"
            # Parse form data
            from urllib.parse import parse_qs

            parsed = parse_qs(body.decode("utf-8", errors="replace"))

            username = None
            password = None

            if path == "/wp-login.php":
                username = parsed.get("log", [None])[0]
                password = parsed.get("pwd", [None])[0]
            elif path == "/phpmyadmin":
                username = parsed.get("pma_username", [None])[0]
                password = parsed.get("pma_password", [None])[0]
            else:
                username = parsed.get("username", [None])[0]
                password = parsed.get("password", [None])[0]

            if username and password:
                password_hash = "sha256:" + hashlib.sha256(password.encode("utf-8")).hexdigest()
                return LoginInfo(username=username, password_hash=password_hash)

        except Exception as e:
            logger.debug("Failed to extract credentials from %s: %s", path, e)

        return None

    async def _publish_event(
        self,
        request: Request,
        response: web.Response,
        path: str,
        method: str,
        login_info: Optional[LoginInfo],
        bait_hit: bool,
        latency: float,
    ) -> None:
        """Publish raw event to the bus."""
        # Get client IP (handle proxies)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.remote or "0.0.0.0"

        # Get destination IP (server) - use settings HTTP host if request.host is a hostname
        host = request.host.split(":")[0] if request.host else "0.0.0.0"
        # If host is a hostname (not IP), use the configured HTTP host
        import ipaddress
        try:
            ipaddress.ip_address(host)
            dest_ip = host
        except ValueError:
            dest_ip = self._settings.http_host or "0.0.0.0"

        # User agent
        user_agent = request.headers.get("User-Agent")

        # Determine ports
        try:
            source_port = int(request.headers.get("X-Forwarded-Port", "0")) or 0
        except ValueError:
            source_port = 0
        dest_port = self._settings.http_port

        event = RawEvent(
            service=Service.HTTP,
            source_ip=client_ip,
            destination_ip=dest_ip,
            timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source_port=source_port,
            destination_port=dest_port,
            login_info=login_info,
            user_agent=user_agent,
            http_method=method,
            http_path=path,
            http_status_code=response.status,
            additional_info={
                "event_kind": "http_request",
                "bait_hit": bait_hit,
                "latency_ms": round(latency * 1000, 2),
            },
        )

        self._raw_bus.publish(event)
        logger.debug("HTTP event: %s %s from %s -> %d", method, path, client_ip, response.status)

    async def start(self) -> None:
        """Start the HTTP server."""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._settings.http_host, self._settings.http_port)
        await self._site.start()
        logger.info("HTTP honeypot listening on %s:%s", self._settings.http_host, self._settings.http_port)

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        logger.info("HTTP honeypot stopped")