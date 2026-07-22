"""Shared process contract for FrameAI CLI providers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import IO, Mapping, Protocol


class ProviderAdapter(Protocol):
    """Smallest provider boundary needed by the existing ``frame`` CLI."""

    name: str
    executable: str
    display_name: str
    invocation_label: str

    def is_available(self) -> bool: ...

    def run(
        self,
        prompt: str,
        *,
        cwd: Path,
        stdout: IO[str] | None = None,
        stderr: int | IO[str] | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess: ...
