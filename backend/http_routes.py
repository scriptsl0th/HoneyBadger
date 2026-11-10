"""HTTP bait routes and responses for the honeypot.

Defines realistic responses for common attack targets:
- Fake login pages (generic, WordPress, phpMyAdmin, etc.)
- Common scanner probes (.env, .git, admin panels, etc.)
- API endpoints
- Server status pages
"""

import html
import random
from typing import Callable, Optional

from aiohttp import web

# Type for route handlers
Handler = Callable[[web.Request], web.Response]


def fake_landing_page() -> web.Response:
    """Generic landing page."""
    return web.Response(
        text=(
            "<!DOCTYPE html><html><head><title>Welcome</title></head>"
            "<body><h1>Welcome to Our Server</h1>"
            "<p>This is a default web server page.</p>"
            "<p><a href='/login'>Login</a> | <a href='/admin'>Admin</a></p>"
            "</body></html>"
        ),
        content_type="text/html",
    )


def fake_login_form() -> web.Response:
    """Generic login form."""
    return web.Response(
        text=(
            "<!DOCTYPE html><html><head><title>Login</title></head>"
            "<body><h2>Login</h2>"
            "<form method='POST' action='/login'>"
            "Username: <input type='text' name='username'><br>"
            "Password: <input type='password' name='password'><br>"
            "<input type='submit' value='Login'>"
            "</form></body></html>"
        ),
        content_type="text/html",
    )


def fake_login_handler(request: web.Request) -> web.Response:
    """Handle login POST - always 'succeeds' but logs credentials."""
    # Credentials are captured by middleware, not here
    return web.Response(
        text=(
            "<!DOCTYPE html><html><head><title>Welcome</title></head>"
            "<body><h2>Login Successful</h2>"
            "<p>Welcome back!</p>"
            "<p><a href='/dashboard'>Dashboard</a></p>"
            "</body></html>"
        ),
        content_type="text/html",
    )


def fake_wp_login() -> web.Response:
    """WordPress login page mimic."""
    return web.Response(
        text=(
            "<!DOCTYPE html><html><head><title>WordPress &rsaquo; Log In</title>"
            "<link rel='stylesheet' href='/wp-admin/css/login.min.css'></head>"
            "<body class='login'><div id='login'><h1><a href='#'>WordPress</a></h1>"
            "<form name='loginform' id='loginform' action='/wp-login.php' method='post'>"
            "<p><label for='user_login'>Username or Email Address</label>"
            "<input type='text' name='log' id='user_login' class='input' value='' size='20'></p>"
            "<p><label for='user_pass'>Password</label>"
            "<input type='password' name='pwd' id='user_pass' class='input' value='' size='20'></p>"
            "<p class='forgetmenot'><label for='rememberme'>"
            "<input name='rememberme' type='checkbox' id='rememberme' value='forever'> "
            "Remember Me</label></p>"
            "<p class='submit'><input type='submit' name='wp-submit' "
            "id='wp-submit' class='button button-primary button-large' value='Log In'></p>"
            "</form></div></body></html>"
        ),
        content_type="text/html",
    )


def fake_wp_login_handler(request: web.Request) -> web.Response:
    """WordPress login handler - sets auth cookie and redirects."""
    response = web.Response(
        text=(
            "<!DOCTYPE html><html><head><title>Dashboard &lsaquo; WordPress</title></head>"
            "<body><h1>Dashboard</h1><p>Welcome to WordPress!</p></body></html>"
        ),
        content_type="text/html",
    )
    response.set_cookie("wordpress_logged_in", "true", httponly=True)
    return response


def fake_admin_panel() -> web.Response:
    """Generic admin panel."""
    return web.Response(
        text=(
            "<!DOCTYPE html><html><head><title>Admin Panel</title></head>"
            "<body><h1>Administration Panel</h1>"
            "<ul><li><a href='/admin/users'>Users</a></li>"
            "<li><a href='/admin/settings'>Settings</a></li>"
            "<li><a href='/admin/logs'>Logs</a></li></ul>"
            "</body></html>"
        ),
        content_type="text/html",
    )


def fake_env_file() -> web.Response:
    """Fake .env file (common probe target)."""
    return web.Response(
        text=(
            "APP_ENV=production\n"
            "APP_DEBUG=false\n"
            "APP_KEY=base64:fakekeyfordeceptiononly\n"
            "DB_HOST=localhost\n"
            "DB_DATABASE=app\n"
            "DB_USERNAME=appuser\n"
            "DB_PASSWORD=supersecretpassword123\n"
            "REDIS_HOST=localhost\n"
            "MAIL_HOST=smtp.example.com\n"
            "AWS_ACCESS_KEY_ID=AKIAFAKEKEY\n"
            "AWS_SECRET_ACCESS_KEY=fakesecretkeyfordeception\n"
        ),
        content_type="text/plain",
    )


def fake_git_config() -> web.Response:
    """Fake .git/config."""
    return web.Response(
        text=(
            "[core]\n"
            "    repositoryformatversion = 0\n"
            "    filemode = true\n"
            "    bare = false\n"
            "    logallrefupdates = true\n"
            "[remote \"origin\"]\n"
            "    url = https://github.com/example/repo.git\n"
            "    fetch = +refs/heads/*:refs/remotes/origin/*\n"
            "[branch \"main\"]\n"
            "    remote = origin\n"
            "    merge = refs/heads/main\n"
        ),
        content_type="text/plain",
    )


def fake_phpmyadmin() -> web.Response:
    """phpMyAdmin login page."""
    return web.Response(
        text=(
            "<!DOCTYPE html><html><head><title>phpMyAdmin</title></head>"
            "<body><div id='page_content'><form method='post' action='/phpmyadmin'>"
            "<input type='hidden' name='token' value='faketoken'>"
            "<fieldset><legend>Login</legend>"
            "<label>Username: <input type='text' name='pma_username'></label><br>"
            "<label>Password: <input type='password' name='pma_password'></label><br>"
            "<input type='submit' value='Go'></fieldset></form></div></body></html>"
        ),
        content_type="text/html",
    )


def fake_api_endpoint() -> web.Response:
    """Generic API endpoint."""
    return web.json_response(
        {
            "status": "ok",
            "version": "1.0.0",
            "data": {"message": "API operational"},
        }
    )


def fake_server_status() -> web.Response:
    """Apache/server-status mimic."""
    return web.Response(
        text=(
            "Apache Server Status for localhost (via 127.0.0.1)\n\n"
            "Server Version: Apache/2.4.52 (Ubuntu)\n"
            "Server Built: 2022-03-08T16:38:45\n"
            "Current Time: 2026-11-10 12:00:00\n"
            "Restart Time: 2026-11-09 00:00:00\n"
            "Parent Server Config. Generation: 1\n"
            "Parent Server MPM Generation: 0\n"
            "Server uptime: 1 day 12 hours\n"
            "Server load: 0.15 0.10 0.05\n"
            "Total accesses: 12345 - Total Traffic: 12.3 MB\n"
            "CPU Usage: u.5 s.1 cu.0 cs.0 - 0.1% CPU load\n"
            "1.2 requests/sec - 1.0 KB/second - 850 B/request\n"
            "1 requests currently being processed, 5 idle workers\n\n"
            "Scoreboard Key:\n"
            '"_" Waiting for Connection, "S" Starting up, "R" Reading Request,\n'
            '"W" Sending Reply, "K" Keepalive (read), "D" DNS Lookup,\n'
            '"C" Closing connection, "L" Logging, "G" Gracefully finishing,\n'
            '"I" Idle cleanup of worker, "." Open slot with no current process\n\n'
            "PID   M   CPU   SS   Req   Conn   Child   Slot   Client   VHost   Request\n"
            "1234  0   0.00  0    1     0      0.0     0.00   192.168.1.1  localhost  GET / HTTP/1.1\n"
        ),
        content_type="text/plain",
    )


def fake_robots_txt() -> web.Response:
    """robots.txt"""
    return web.Response(
        text=(
            "User-agent: *\n"
            "Disallow: /admin/\n"
            "Disallow: /private/\n"
            "Disallow: /backup/\n"
            "Allow: /\n"
            "Sitemap: https://example.com/sitemap.xml\n"
        ),
        content_type="text/plain",
    )


# Bait route registry
BAIT_ROUTES: dict[str, dict[str, Handler]] = {
    "/": {"GET": lambda _: fake_landing_page()},
    "/login": {"GET": lambda _: fake_login_form(), "POST": fake_login_handler},
    "/wp-login.php": {"GET": lambda _: fake_wp_login(), "POST": fake_wp_login_handler},
    "/admin": {"GET": lambda _: fake_admin_panel()},
    "/.env": {"GET": lambda _: fake_env_file()},
    "/.git/config": {"GET": lambda _: fake_git_config()},
    "/phpmyadmin": {"GET": lambda _: fake_phpmyadmin(), "POST": fake_phpmyadmin},
    "/api": {"GET": lambda _: fake_api_endpoint()},
    "/api/v1": {"GET": lambda _: fake_api_endpoint()},
    "/api/v2": {"GET": lambda _: fake_api_endpoint()},
    "/server-status": {"GET": lambda _: fake_server_status()},
    "/server-info": {"GET": lambda _: fake_server_status()},
    "/robots.txt": {"GET": lambda _: fake_robots_txt()},
    "/.htaccess": {"GET": lambda _: fake_env_file()},  # Often probed together
    "/.htpasswd": {"GET": lambda _: fake_env_file()},
    "/backup": {"GET": lambda _: fake_env_file()},
    "/config": {"GET": lambda _: fake_env_file()},
    "/phpinfo.php": {"GET": lambda _: web.Response(text="<?php phpinfo(); ?>", content_type="text/html")},
    "/info.php": {"GET": lambda _: web.Response(text="<?php phpinfo(); ?>", content_type="text/html")},
    "/actuator": {"GET": lambda _: fake_api_endpoint()},
    "/actuator/health": {"GET": lambda _: web.json_response({"status": "UP"})},
    "/metrics": {"GET": lambda _: fake_server_status()},
    "/health": {"GET": lambda _: web.json_response({"status": "healthy"})},
    "/swagger": {"GET": lambda _: fake_api_endpoint()},
    "/graphql": {"GET": lambda _: web.json_response({"errors": [{"message": "GraphQL endpoint"}]} )},
    "/.well-known": {"GET": lambda _: web.Response(status=404)},
    "/sitemap.xml": {"GET": lambda _: web.Response(text='<?xml version="1.0"?><urlset></urlset>', content_type="application/xml")},
    "/crossdomain.xml": {"GET": lambda _: web.Response(text='<?xml version="1.0"?><cross-domain-policy></cross-domain-policy>', content_type="application/xml")},
    "/clientaccesspolicy.xml": {"GET": lambda _: web.Response(text='<?xml version="1.0"?><access-policy></access-policy>', content_type="application/xml")},
}


def select_bait(path: str, method: str) -> Optional[Handler]:
    """Select the appropriate bait handler for a path and method."""
    # Exact match first
    if path in BAIT_ROUTES:
        route = BAIT_ROUTES[path]
        if method in route:
            return route[method]
        # Fallback to GET for any method if defined
        if "GET" in route:
            return route["GET"]

    # Prefix match for dynamic paths (e.g., /api/v1/users)
    for bait_path, handlers in BAIT_ROUTES.items():
        if path.startswith(bait_path + "/") or path == bait_path:
            if method in handlers:
                return handlers[method]
            if "GET" in handlers:
                return handlers["GET"]

    return None


def is_bait_path(path: str) -> bool:
    """Check if a path is a known bait path."""
    if path in BAIT_ROUTES:
        return True
    for bait_path in BAIT_ROUTES:
        if path.startswith(bait_path + "/"):
            return True
    return False