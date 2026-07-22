from __future__ import annotations

import subprocess
from pathlib import Path

from frameai.providers.claude import ClaudeAdapter


def test_availability_checks_claude_on_path(monkeypatch):
    seen = []
    monkeypatch.setattr("shutil.which", lambda executable: seen.append(executable) or "/bin/claude")

    assert ClaudeAdapter().is_available() is True
    assert seen == ["claude"]


def test_run_preserves_headless_command_cwd_and_exit_code(monkeypatch, tmp_path):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 17)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = ClaudeAdapter().run("prompt text", cwd=tmp_path)

    assert result.returncode == 17
    assert calls == [(["claude", "--print", "prompt text"], {"cwd": tmp_path})]


def test_run_preserves_archive_streams_and_environment(monkeypatch, tmp_path):
    calls = []
    log_path = tmp_path / "log.txt"
    env = {"FRAMEAI_RUN_MODE": "cli"}

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with log_path.open("w", encoding="utf-8") as log:
        ClaudeAdapter().run(
            "run prompt",
            cwd=Path("/repo"),
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )

    argv, kwargs = calls[0]
    assert argv == ["claude", "--print", "run prompt"]
    assert kwargs["cwd"] == Path("/repo")
    assert kwargs["stderr"] == subprocess.STDOUT
    assert kwargs["env"] is env
    assert kwargs["stdout"].name == str(log_path)
