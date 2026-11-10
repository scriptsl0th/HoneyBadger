"""MITRE ATT&CK technique classifier for HoneyBadger events.

Rule-based classification matching SYSTEM_ARCHITECTURE.md §5:
- T1110 — Brute Force (password guessing)
- T1110.004 — Credential Stuffing (repeated same credentials)
- T1595 — Active Scanning (scanner/probe hits)
- T1190 — Exploit Public-Facing Application (exploit-shaped payloads)
- T1105 — Ingress Tool Transfer (wget/curl payload downloads)
- T1059 — Command and Scripting Interpreter (shell commands)
- T1078 — Valid Accounts (contextual, "successful" session)
"""

import re
from typing import Optional

from schemas import RawEvent, Severity, Service


# Known exploit patterns for T1190 detection
EXPLOIT_PATTERNS = [
    # SQL injection
    r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table|delete\s+from)",
    r"(?i)(\bor\s+1\s*=\s*1\b|\band\s+1\s*=\s*1\b)",
    r"(?i)(information_schema|sysobjects|syscolumns)",
    # Command injection
    r"(?i)(;\s*(cat|ls|id|whoami|wget|curl|nc|netcat|bash|sh)\b)",
    r"(?i)(\|\s*(cat|ls|id|whoami|wget|curl|nc|netcat|bash|sh)\b)",
    r"(?i)(`.*`|\$\(.*\))",
    # Path traversal
    r"(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/)",
    # LDAP injection
    r"(?i)(\*\)\(|\)\(|&\||\(\))",
    # XSS
    r"(?i)(<script|javascript:|onerror=|onload=)",
    # Shellshock
    r"(?i)\(\)\s*\{.*\}",
    # Log4Shell
    r"(?i)\$\{jndi:",
    # Spring4Shell
    r"(?i)class\.module\.classloader",
]

# Scanner/probe paths for T1595 detection
SCANNER_PATHS = [
    "/.env",
    "/.git",
    "/.svn",
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
    "/metrics",
    "/health",
    "/api/v1",
    "/api/v2",
    "/swagger",
    "/graphql",
    "/.well-known",
    "/robots.txt",
    "/sitemap.xml",
    "/crossdomain.xml",
    "/clientaccesspolicy.xml",
    "/phpmyadmin",
    "/pma",
    "/mysql",
    "/sqladmin",
    "/myadmin",
    "/webadmin",
]

# Common credential stuffing usernames
COMMON_USERNAMES = {
    "root",
    "admin",
    "administrator",
    "user",
    "test",
    "guest",
    "ubuntu",
    "ec2-user",
    "centos",
    "debian",
    "pi",
    "oracle",
    "postgres",
    "mysql",
    "redis",
    "nginx",
    "apache",
    "www-data",
    "docker",
    "kubernetes",
    "jenkins",
    "gitlab",
    "git",
    "ansible",
}


def classify(event: RawEvent) -> tuple[Optional[str], Optional[Severity]]:
    """Classify a raw event into MITRE ATT&CK technique and severity.

    Returns:
        Tuple of (technique_id, severity) or (None, None) if no match.
    """
    # T1105 - Ingress Tool Transfer (payload download via wget/curl)
    if event.command and _is_payload_download(event.command):
        return "T1105", Severity.HIGH

    # T1190 - Exploit Public-Facing Application (exploit patterns)
    if _has_exploit_pattern(event):
        return "T1190", Severity.HIGH

    # T1595 - Active Scanning (scanner/probe paths)
    if _is_scanner_probe(event):
        return "T1595", Severity.LOW

    # T1059 - Command and Scripting Interpreter (shell commands)
    if event.command and event.service == Service.SSH:
        return "T1059", Severity.MEDIUM

    # T1110 / T1110.004 - Brute Force / Credential Stuffing
    if event.login_info and event.login_info.username and event.login_info.password_hash:
        if _is_credential_stuffing(event):
            return "T1110.004", Severity.HIGH
        return "T1110", Severity.MEDIUM

    # T1078 - Valid Accounts (contextual, any accepted auth)
    if event.login_info and event.additional_info and event.additional_info.get("event_kind") == "auth":
        return "T1078", Severity.LOW

    return None, None


def _is_payload_download(command: str) -> bool:
    """Check if command is a payload download (wget/curl with URL)."""
    cmd_lower = command.lower().strip()
    return (
        cmd_lower.startswith("wget ") and ("http://" in cmd_lower or "https://" in cmd_lower)
    ) or (
        cmd_lower.startswith("curl ") and ("http://" in cmd_lower or "https://" in cmd_lower)
    )


def _has_exploit_pattern(event: RawEvent) -> bool:
    """Check if event contains exploit-shaped payloads."""
    # Check command for exploit patterns
    if event.command:
        for pattern in EXPLOIT_PATTERNS:
            if re.search(pattern, event.command):
                return True

    # Check HTTP path/body for exploit patterns
    if event.http_path:
        for pattern in EXPLOIT_PATTERNS:
            if re.search(pattern, event.http_path):
                return True

    # Check user agent for exploit patterns
    if event.user_agent:
        for pattern in EXPLOIT_PATTERNS:
            if re.search(pattern, event.user_agent):
                return True

    return False


def _is_scanner_probe(event: RawEvent) -> bool:
    """Check if event is a scanner/probe hit."""
    if event.service != Service.HTTP:
        return False

    if not event.http_path:
        return False

    path_lower = event.http_path.lower()

    # Check for known scanner paths
    for scanner_path in SCANNER_PATHS:
        if scanner_path.lower() in path_lower:
            return True

    # Check for common vulnerability scanner patterns
    scanner_patterns = [
        r"^/[a-z0-9_-]+$",  # Single path segment (common probe)
        r"\.(bak|backup|old|orig|save|swp|tmp)$",
        r"(?i)(scanner|bot|crawler|spider|nikto|dirb|gobuster|feroxbuster)",
    ]

    if event.user_agent:
        ua_lower = event.user_agent.lower()
        for pattern in scanner_patterns:
            if re.search(pattern, ua_lower):
                return True

    return False


def _is_credential_stuffing(event: RawEvent) -> bool:
    """Check if event looks like credential stuffing (repeated same credentials).

    This is a heuristic - in practice, the credential tracker in credentials.py
    would track repeated attempts and could signal this.
    """
    if not event.login_info or not event.login_info.username:
        return False

    username = event.login_info.username.lower()

    # Common usernames with multiple attempts = likely credential stuffing
    if username in COMMON_USERNAMES:
        return True

    # Email-like usernames often indicate credential stuffing
    if "@" in username:
        return True

    return False