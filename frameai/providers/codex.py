"""Codex CLI process adapter.

Codex's documented non-interactive entrypoint is ``codex exec``. FrameAI's
build, run, and refine operations require repository writes. The FrameAI host
already supplies the isolation boundary, so Codex's nested sandbox is disabled
to avoid unsupported ``bwrap`` initialization. Authentication and configuration
remain owned by the installed Codex CLI.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import IO, Mapping


class CodexAdapter:
    """Locate and invoke Codex while preserving FrameAI process semantics."""

    name = "codex"
    executable = "codex"
    display_name = "Codex CLI"
    invocation_label = "codex exec stdout"

    def is_available(self) -> bool:
        return shutil.which(self.executable) is not None

    def run(
        self,
        prompt: str,
        *,
        cwd: Path,
        stdout: IO[str] | None = None,
        stderr: int | IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess:
        workspace = cwd.resolve()
        kwargs: dict[str, object] = {"cwd": workspace}
        if stdout is not None:
            kwargs["stdout"] = stdout
        if stderr is not None:
            kwargs["stderr"] = stderr
        if env is not None:
            kwargs["env"] = env
        if timeout is not None:
            kwargs["timeout"] = timeout
        return subprocess.run(
            [
                self.executable,
                "exec",
                "--ephemeral",
                "--dangerously-bypass-approvals-and-sandbox",
                "--cd",
                str(workspace),
                prompt,
            ],
            **kwargs,
        )
