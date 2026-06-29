#!/usr/bin/env python3
"""FrameAI MCP server — exposes skills/ as MCP prompts.

Lets Claude Desktop, Cursor, or any MCP client discover and invoke FrameAI
skills the same way Claude Code does via slash commands.

Design:
  - Each `skills/<slug>/SKILL.md` becomes one MCP prompt.
  - The prompt's `description` is the SKILL.md YAML frontmatter `description`.
  - When invoked, the server returns the full SKILL body as a user message so
    the client's LLM follows the skill instructions.
  - The skills/ directory is re-scanned on every list_prompts() call, so new
    skills built via `./frame add` appear without restarting this server
    (the client may still cache the prompt list until its next refresh).

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

AUTOGEN_HEADER_RE = re.compile(r"^<!--\s*AUTO-GENERATED.*?-->\s*\n", re.IGNORECASE)
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

logger = logging.getLogger("frameai-mcp")
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)

server: Server = Server("frameai")


def _strip_autogen_header(text: str) -> str:
    return AUTOGEN_HEADER_RE.sub("", text, count=1)


def parse_skill_md(skill_md_path: Path) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body_text). Empty dict if parse fails."""
    raw = skill_md_path.read_text(encoding="utf-8")
    raw = _strip_autogen_header(raw)
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


def build_prompt(skill_md: Path) -> types.Prompt | None:
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
    arguments: list[types.PromptArgument] = []
    if arg_hint:
        arguments.append(
            types.PromptArgument(
                name="input",
                description=arg_hint.strip("[]"),
                required=False,
            )
        )

    return types.Prompt(name=name, description=desc, arguments=arguments)


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    prompts: list[types.Prompt] = []
    for skill_md in discover_skill_files():
        try:
            p = build_prompt(skill_md)
        except Exception as exc:  # noqa: BLE001 — log + skip one bad skill
            logger.warning("skip %s: %s", skill_md, exc)
            continue
        if p:
            prompts.append(p)
    logger.info("list_prompts → %d skills", len(prompts))
    return prompts


@server.get_prompt()
async def handle_get_prompt(
    name: str,
    arguments: dict[str, str] | None,
) -> types.GetPromptResult:
    skill_md = SKILLS_DIR / name / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError(f"Unknown FrameAI skill: {name!r}")

    fm, body = parse_skill_md(skill_md)
    user_input = ((arguments or {}).get("input") or "").strip()

    parts = [body.strip()]
    if user_input:
        parts.append(f"## User input\n\n{user_input}")
    text = "\n\n".join(parts)

    desc = (fm.get("description") or f"FrameAI skill: {name}").strip()
    return types.GetPromptResult(
        description=desc,
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=text),
            )
        ],
    )


# ---------------------------------------------------------------------------
# Tools — same skills exposed as MCP tools so they appear in Claude Desktop's
# Connectors UI. Tools and prompts share the same source (SKILL.md). The tool
# implementation returns the skill body as instructions; the calling LLM
# executes them using its own file/Bash access.
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


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict[str, Any] | None,
) -> list[types.TextContent]:
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
