#!/usr/bin/env python3
"""FrameAI MCP server — exposes skills/ as MCP tools.

Lets Claude Desktop, Cursor, or any MCP client discover and invoke FrameAI
skills via the standard MCP tool-calling pathway (LLM auto-matches user
intent → tool call → skill instructions returned → LLM executes).

Design:
  - Each `skills/<slug>/SKILL.md` becomes one MCP tool.
  - The tool's `description` is the SKILL.md YAML frontmatter `description`.
  - When invoked, the server returns the full SKILL body as text content with
    a preamble telling the LLM to execute the instructions step-by-step
    using its file / Bash / edit access.
  - The skills/ directory is re-scanned on every list_tools() call, so new
    skills built via `./frame add` appear without restarting this server
    (the client may still cache the tool list until its next refresh).

Why tools (not prompts)? Claude Desktop's Connectors UI only surfaces tools.
Prompts are technically delivered but invisible. Tools also enable
natural-language auto-matching ("회의록 정리해줘" → meeting-summarizer tool)
without explicit user picker interaction.

Transport: stdio (default for Claude Desktop / Cursor / etc.).

Install:
    pip install mcp pyyaml

Run (usually launched by the client, not by hand):
    python3 scripts/frameai_mcp_server.py
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "frameai-mcp-server: pyyaml not installed. Run: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    print(
        "frameai-mcp-server: mcp SDK not installed. Run: pip install mcp",
        file=sys.stderr,
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

# Build-pipeline skills are exposed but flagged in description so clients
# (and users) know they orchestrate multi-agent Task chains best run in
# Claude Code, not standalone in Desktop.
BUILD_PIPELINE_SKILLS = {
    "prd",
    "kickoff",
    "sprint",
    "implement",
    "spec",
    "ship",
    "review",
    "diagnose",
}

# Deterministic skills the MCP server runs directly (subprocess) instead of
# returning SKILL instructions for the calling LLM. This lets Claude Desktop
# (which has no Bash) actually execute the operation end-to-end. Each entry
# hardcodes the command — no user input flows in, so injection surface is
# zero. Add new entries only for genuinely deterministic skills.
EXECUTABLE_SKILLS: dict[str, dict[str, Any]] = {
    "frameai-update": {
        "argv": ["./frame", "update"],
        "timeout_sec": 120,
        "summary": (
            "Pull the latest FrameAI skills and agents from upstream, "
            "restore executable bits, and report what changed."
        ),
    },
}

logger = logging.getLogger("frameai-mcp")
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)

server: Server = Server("frameai")


def parse_skill_md(skill_md_path: Path) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body_text). Empty dict if parse fails."""
    raw = skill_md_path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    try:
        fm = yaml.safe_load(m.group(1)) or {}
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group(2)


def discover_skill_files() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    # Intentionally empty: skills are exposed via tools (below). The prompts
    # handler stays registered so MCP clients that probe prompts/list don't
    # see a "method not found" error — they just get zero prompts.
    return []


# ---------------------------------------------------------------------------
# Tools — every SKILL.md becomes one MCP tool. This is the primary (and
# now only) interface: Claude Desktop's Connectors UI surfaces tools but
# hides prompts, and natural-language auto-matching ("회의록 정리해줘") is
# tool-only. The tool implementation returns the skill body as
# instructions; the calling LLM executes them using its own file / Bash /
# edit access.
# ---------------------------------------------------------------------------

TOOL_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "input": {
            "type": "string",
            "description": (
                "Free-form user input. Can be a file path, raw text, a "
                "question, or empty if the skill needs no arguments."
            ),
        }
    },
    "additionalProperties": False,
}


def build_tool(skill_md: Path) -> types.Tool | None:
    fm, _ = parse_skill_md(skill_md)
    name = (fm.get("name") or skill_md.parent.name).strip()
    if not name:
        return None

    desc = (fm.get("description") or "").strip()
    if not desc:
        desc = f"FrameAI skill: {name}"
    if name in BUILD_PIPELINE_SKILLS:
        desc = f"[build pipeline — best run in Claude Code] {desc}"

    arg_hint = str(fm.get("argument-hint") or "").strip()
    schema = dict(TOOL_INPUT_SCHEMA)
    schema["properties"] = dict(schema["properties"])
    if arg_hint:
        schema["properties"]["input"] = dict(schema["properties"]["input"])
        schema["properties"]["input"]["description"] = arg_hint.strip("[]")

    return types.Tool(name=name, description=desc, inputSchema=schema)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    tools: list[types.Tool] = []
    for skill_md in discover_skill_files():
        try:
            t = build_tool(skill_md)
        except Exception as exc:  # noqa: BLE001 — log + skip one bad skill
            logger.warning("skip tool %s: %s", skill_md, exc)
            continue
        if t:
            tools.append(t)
    logger.info("list_tools → %d skills", len(tools))
    return tools


def _run_executable_skill(name: str, spec: dict[str, Any]) -> types.TextContent:
    """Run a deterministic skill directly via subprocess and format the result.

    Used for skills that have no LLM-driven planning step (e.g. frameai-update
    is just `git pull --ff-only`). Lets Claude Desktop — which has no Bash —
    actually complete the operation end-to-end through the MCP tool call,
    instead of receiving instructions it can't execute.
    """
    try:
        proc = subprocess.run(
            spec["argv"],
            capture_output=True,
            text=True,
            timeout=spec.get("timeout_sec", 120),
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return types.TextContent(
            type="text",
            text=(
                f"# FrameAI skill: {name}\n\n"
                f"Timed out after {spec.get('timeout_sec', 120)}s. "
                "Re-run from a terminal to investigate."
            ),
        )
    except FileNotFoundError as exc:
        return types.TextContent(
            type="text",
            text=(
                f"# FrameAI skill: {name}\n\n"
                f"Command not found: {exc}. The FrameAI install may be "
                "missing or its `frame` script is not executable."
            ),
        )

    status = "✓ success" if proc.returncode == 0 else f"✘ exit code {proc.returncode}"
    return types.TextContent(
        type="text",
        text=(
            f"# FrameAI skill: {name}\n\n"
            f"{spec.get('summary', '').strip()}\n\n"
            f"**Status**: {status}\n\n"
            f"## stdout\n```\n{proc.stdout or '(empty)'}\n```\n\n"
            f"## stderr\n```\n{proc.stderr or '(empty)'}\n```"
        ),
    )


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any] | None,
) -> list[types.TextContent]:
    # Deterministic skill — server runs it directly (works in Desktop too,
    # which has no Bash). User input is intentionally ignored: these skills
    # are hardcoded, no injection surface.
    if name in EXECUTABLE_SKILLS:
        logger.info("call_tool %s (executable, direct subprocess)", name)
        return [_run_executable_skill(name, EXECUTABLE_SKILLS[name])]

    skill_md = SKILLS_DIR / name / "SKILL.md"
    if not skill_md.is_file():
        return [
            types.TextContent(
                type="text",
                text=f"Unknown FrameAI skill: {name!r}",
            )
        ]

    body = parse_skill_md(skill_md)[1]
    user_input = ""
    if isinstance(arguments, dict):
        raw = arguments.get("input")
        if isinstance(raw, str):
            user_input = raw.strip()

    preamble = (
        f"# FrameAI skill: {name}\n\n"
        "You have invoked a FrameAI skill. The skill instructions are "
        "below — execute them step by step using your available file, "
        "Bash, and editing tools. Write all outputs to the location the "
        "skill specifies (typically under "
        "`automations/<slug>/runs/<UTC-timestamp>/outputs/`).\n\n"
        "---\n"
    )
    parts = [preamble, body.strip()]
    if user_input:
        parts.append(f"---\n\n## User input\n\n{user_input}")
    text = "\n\n".join(parts)

    logger.info("call_tool %s (input=%d chars)", name, len(user_input))
    return [types.TextContent(type="text", text=text)]


async def main() -> None:
    logger.info("frameai-mcp-server starting (root=%s)", ROOT)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
