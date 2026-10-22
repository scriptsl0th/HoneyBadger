"""In-memory fake shell used by the SSH honeypot.

Every command is simulated: no real path is ever opened, written, or executed,
and no network request is ever made. ``wget``/``curl`` only record the
requested URL so it can be attached to the event as payload metadata.
"""

import shlex
from dataclasses import dataclass

HOSTNAME = "honeybadger"
HOME = "/root"

_DIRECTORIES = {
    "/",
    "/root",
    "/tmp",
    "/etc",
    "/var",
    "/var/log",
    "/home",
    "/home/user",
}

_FILES: dict[str, str] = {
    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
        "ubuntu:x:1000:1000:Ubuntu:/home/user:/bin/bash\n"
    ),
    "/etc/hostname": HOSTNAME + "\n",
    "/etc/issue": "Ubuntu 22.04.4 LTS \\n \\l\n\n",
    "/etc/hosts": "127.0.0.1\tlocalhost\n127.0.1.1\t" + HOSTNAME + "\n",
    "/root/.bashrc": "# ~/.bashrc\nexport PATH=$PATH:/usr/local/bin\n",
    "/root/notes.txt": (
        "TODO: migrate the billing service.\n"
        "staging credentials rotated last week.\n"
    ),
    "/var/log/auth.log": (
        "Jul 12 03:14:15 honeybadger sshd[1122]: "
        "Failed password for root from 203.0.113.7 port 51234 ssh2\n"
    ),
    "/var/log/syslog": (
        "Jul 12 03:14:15 honeybadger systemd[1]: Started Daily apt upgrade.\n"
    ),
}

_COMMANDS = (
    "cat",
    "cd",
    "curl",
    "echo",
    "exit",
    "help",
    "history",
    "id",
    "logout",
    "ls",
    "pwd",
    "uname",
    "wget",
    "whoami",
)


@dataclass
class ShellResult:
    """Outcome of one fake-shell command."""

    output: str
    cwd: str
    exit_requested: bool = False
    payload_url: str | None = None


class FakeShell:
    """A tiny, stateful, entirely in-memory shell."""

    def __init__(self, hostname: str = HOSTNAME, username: str = "root") -> None:
        self.hostname = hostname
        self.username = username
        self.cwd = HOME
        self.history: list[str] = []

    def prompt(self) -> str:
        location = "~" if self.cwd == HOME else self.cwd
        return f"{self.username}@{self.hostname}:{location}# "

    def dispatch(self, line: str) -> ShellResult:
        command = line.strip()
        if not command:
            return ShellResult("", self.cwd)

        self.history.append(command)
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        if not parts:
            return ShellResult("", self.cwd)

        name, args = parts[0], parts[1:]
        handler = getattr(self, f"_cmd_{name}", None)
        if handler is None:
            return ShellResult(f"bash: {name}: command not found", self.cwd)
        return handler(args)

    # -- builtins ---------------------------------------------------------

    def _cmd_pwd(self, args: list[str]) -> ShellResult:
        return ShellResult(self.cwd, self.cwd)

    def _cmd_whoami(self, args: list[str]) -> ShellResult:
        return ShellResult(self.username, self.cwd)

    def _cmd_id(self, args: list[str]) -> ShellResult:
        return ShellResult("uid=0(root) gid=0(root) groups=0(root)", self.cwd)

    def _cmd_uname(self, args: list[str]) -> ShellResult:
        if "-a" in args:
            text = (
                f"Linux {self.hostname} 5.15.0-91-generic #101-Ubuntu SMP "
                "Tue Nov 14 13:30:08 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux"
            )
        else:
            text = "Linux"
        return ShellResult(text, self.cwd)

    def _cmd_ls(self, args: list[str]) -> ShellResult:
        show_hidden = any("a" in arg for arg in args if arg.startswith("-"))
        targets = [arg for arg in args if not arg.startswith("-")]
        path = self._resolve(targets[0]) if targets else self.cwd

        if path in _FILES:
            entries = [path.rsplit("/", 1)[-1]]
        elif path in _DIRECTORIES:
            entries = self._entries(path)
        else:
            target = targets[0] if targets else path
            return ShellResult(
                f"ls: cannot access '{target}': No such file or directory", self.cwd
            )

        if not show_hidden:
            entries = [entry for entry in entries if not entry.startswith(".")]
        return ShellResult("  ".join(entries), self.cwd)

    def _cmd_cd(self, args: list[str]) -> ShellResult:
        target = args[0] if args else HOME
        path = self._resolve(target)
        if path in _DIRECTORIES:
            self.cwd = path
            return ShellResult("", self.cwd)
        if path in _FILES:
            return ShellResult(f"bash: cd: {target}: Not a directory", self.cwd)
        return ShellResult(
            f"bash: cd: {target}: No such file or directory", self.cwd
        )

    def _cmd_cat(self, args: list[str]) -> ShellResult:
        if not args:
            return ShellResult("cat: missing operand", self.cwd)

        outputs: list[str] = []
        for target in args:
            path = self._resolve(target)
            if path in _FILES:
                outputs.append(_FILES[path].rstrip("\n"))
            elif path in _DIRECTORIES:
                outputs.append(f"cat: {target}: Is a directory")
            else:
                outputs.append(f"cat: {target}: No such file or directory")
        return ShellResult("\n".join(outputs), self.cwd)

    def _cmd_echo(self, args: list[str]) -> ShellResult:
        return ShellResult(" ".join(args), self.cwd)

    def _cmd_history(self, args: list[str]) -> ShellResult:
        lines = [
            f"{index:5d}  {command}"
            for index, command in enumerate(self.history, start=1)
        ]
        return ShellResult("\n".join(lines), self.cwd)

    def _cmd_help(self, args: list[str]) -> ShellResult:
        return ShellResult("Built-in commands: " + ", ".join(_COMMANDS), self.cwd)

    def _cmd_exit(self, args: list[str]) -> ShellResult:
        return ShellResult("", self.cwd, exit_requested=True)

    def _cmd_logout(self, args: list[str]) -> ShellResult:
        return ShellResult("", self.cwd, exit_requested=True)

    def _cmd_wget(self, args: list[str]) -> ShellResult:
        url = self._url(args)
        if url is None:
            return ShellResult("wget: missing URL", self.cwd)

        name = self._download_name(url)
        output = (
            f"--2026-10-22 12:00:00--  {url}\n"
            "Resolving host... 93.184.216.34\n"
            "Connecting to host|93.184.216.34|:80... connected.\n"
            "HTTP request sent, awaiting response... 200 OK\n"
            "Length: 2048 (2.0K) [application/octet-stream]\n"
            f"Saving to: '{name}'\n\n"
            f"'{name}' saved [2048/2048]"
        )
        return ShellResult(output, self.cwd, payload_url=url)

    def _cmd_curl(self, args: list[str]) -> ShellResult:
        url = self._url(args)
        if url is None:
            return ShellResult(
                "curl: try 'curl --help' for more information", self.cwd
            )

        output = (
            "  % Total    % Received % Xferd  Average Speed   Time    Time     "
            "Time  Current\n"
            "                                 Dload  Upload   Total   Spent    "
            "Left  Speed\n"
            "100  2048  100  2048    0     0  20480      0 --:--:-- --:--:-- "
            "--:--:-- 20480"
        )
        return ShellResult(output, self.cwd, payload_url=url)

    # -- helpers ----------------------------------------------------------

    def _resolve(self, path: str) -> str:
        if not path or path == "~":
            return HOME
        if path.startswith("~/"):
            path = HOME + path[1:]
        if not path.startswith("/"):
            path = f"{self.cwd.rstrip('/')}/{path}"

        parts: list[str] = []
        for segment in path.split("/"):
            if segment in ("", "."):
                continue
            if segment == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(segment)
        return "/" + "/".join(parts)

    @staticmethod
    def _entries(path: str) -> list[str]:
        prefix = "/" if path == "/" else path + "/"
        names = {
            candidate[len(prefix) :]
            for candidate in (*_DIRECTORIES, *_FILES)
            if candidate != path and candidate.startswith(prefix)
        }
        return sorted(name for name in names if name and "/" not in name)

    @staticmethod
    def _url(args: list[str]) -> str | None:
        for arg in args:
            if arg.startswith(("http://", "https://")):
                return arg
        return None

    @staticmethod
    def _download_name(url: str) -> str:
        name = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        return name or "index.html"
