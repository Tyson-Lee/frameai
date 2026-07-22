"""Claude Code process adapter.

This module owns only the existing Claude Code CLI process boundary. Prompt
construction, run archives, logging, and user-facing output remain in
``frame`` so extracting the adapter does not change the public CLI contract.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import IO, Mapping


class ClaudeAdapter:
    """Locate and invoke Claude Code using FrameAI's established contract."""

    name = "claude"
    executable = "claude"
    display_name = "Claude Code"
    invocation_label = "claude --print stdout"

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
        kwargs: dict[str, object] = {"cwd": cwd}
        if stdout is not None:
            kwargs["stdout"] = stdout
        if stderr is not None:
            kwargs["stderr"] = stderr
        if env is not None:
            kwargs["env"] = env
        if timeout is not None:
            kwargs["timeout"] = timeout
        return subprocess.run(
            [self.executable, "--print", prompt],
            **kwargs,
        )
