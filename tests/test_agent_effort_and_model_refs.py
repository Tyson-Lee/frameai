"""Guards for ISSUE-015 — agent effort tiers + model reference refresh.

Verifies:
- Every agent file under agents/ declares an `effort:` frontmatter field with
  a value from the runtime's effort vocabulary (per cc_feature_matrix.md
  rows A5-A6: low | medium | high | xhigh, plus max/ultra which the kit
  does not currently use but are valid).
- For sonnet-modeled agents, effort stays in {low, medium, high}. xhigh
  is opus-tier per the matrix and would fail or silently degrade on sonnet.
- No retired model identifier appears in the README outside of a clearly-
  historical section. The status-line example must use a current model id.
- project/.claude/settings.snippet.json carries a `fallbackModel` array of
  at most 3 entries (matrix row A8-adjacent: docs cap chains at 3).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = KIT_ROOT / "agents"

ALLOWED_EFFORT = {"low", "medium", "high", "xhigh", "max", "ultra"}
# Sonnet does NOT accept xhigh / max / ultra per ISSUE-014 matrix notes.
SONNET_SAFE_EFFORT = {"low", "medium", "high"}

# Stale model IDs we explicitly forbid from appearing as a CURRENT example.
RETIRED_MODEL_IDS = {
    "claude-opus-4-5",
    "claude-opus-4-6",
    "claude-sonnet-4-5",
    "claude-haiku-4-4",
}


def _frontmatter(path: Path) -> dict[str, str]:
    """Parse the simple key: value frontmatter block at the top of an md file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    block = text[4:end]
    result: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.+)$", line)
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


class TestAgentEffortFrontmatter:
    def test_every_agent_declares_effort(self):
        missing: list[str] = []
        for agent in sorted(AGENTS_DIR.glob("*.md")):
            fm = _frontmatter(agent)
            if not fm.get("effort"):
                missing.append(agent.name)
        assert not missing, (
            "Agents missing `effort:` frontmatter (ISSUE-015 contract):\n  "
            + "\n  ".join(missing)
        )

    def test_every_effort_value_is_allowed(self):
        violations: list[str] = []
        for agent in sorted(AGENTS_DIR.glob("*.md")):
            fm = _frontmatter(agent)
            effort = fm.get("effort")
            if effort and effort not in ALLOWED_EFFORT:
                violations.append(f"{agent.name}: effort={effort!r}")
        assert not violations, (
            "Agents with effort values outside the matrix vocabulary "
            f"{sorted(ALLOWED_EFFORT)}:\n  " + "\n  ".join(violations)
        )

    def test_sonnet_agents_do_not_request_xhigh_or_higher(self):
        # Matrix row A6 notes xhigh is opus-tier. Putting xhigh on a sonnet
        # agent is undefined behavior on the targeted runtime.
        violations: list[str] = []
        for agent in sorted(AGENTS_DIR.glob("*.md")):
            fm = _frontmatter(agent)
            if fm.get("model") == "sonnet" and fm.get("effort") not in SONNET_SAFE_EFFORT:
                violations.append(f"{agent.name}: model=sonnet effort={fm.get('effort')!r}")
        assert not violations, (
            "Sonnet agents requesting effort tiers outside "
            f"{sorted(SONNET_SAFE_EFFORT)}:\n  " + "\n  ".join(violations)
        )

    def test_at_least_one_agent_per_effort_tier(self):
        # Regression: if a bulk-edit accidentally collapses all agents to one
        # tier, this catches it.
        seen: set[str] = set()
        for agent in sorted(AGENTS_DIR.glob("*.md")):
            fm = _frontmatter(agent)
            if fm.get("effort") in ALLOWED_EFFORT:
                seen.add(fm["effort"])
        for tier in ("low", "medium", "high", "xhigh"):
            assert tier in seen, f"No agent assigned effort: {tier} — bulk edit may have flattened the split"


class TestNoRetiredModelIdsInReadme:
    def test_readme_does_not_advertise_retired_ids(self):
        readme = (KIT_ROOT / "README.md").read_text(encoding="utf-8")
        violations: list[str] = []
        for stale in RETIRED_MODEL_IDS:
            if stale in readme:
                # Pinpoint the line
                for i, line in enumerate(readme.splitlines(), start=1):
                    if stale in line:
                        violations.append(f"README.md:{i}: {stale} — {line.strip()[:80]}")
        assert not violations, (
            "Retired model IDs still appear in README (refresh per ISSUE-015):\n  "
            + "\n  ".join(violations)
        )


class TestFallbackModelInSettings:
    def test_fallback_model_present_and_well_formed(self):
        settings_path = KIT_ROOT / "project" / ".claude" / "settings.snippet.json"
        assert settings_path.is_file(), "missing project/.claude/settings.snippet.json"
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        chain = data.get("fallbackModel")
        assert isinstance(chain, list), (
            "fallbackModel must be a list (Anthropic docs: array of model identifiers)"
        )
        assert 1 <= len(chain) <= 3, (
            f"fallbackModel chain must be 1–3 entries (docs cap), got {len(chain)}"
        )
        for entry in chain:
            assert isinstance(entry, str) and entry, (
                f"fallbackModel entries must be non-empty strings, got {entry!r}"
            )
            # Allow "default" or real model IDs; reject retired IDs.
            assert entry not in RETIRED_MODEL_IDS, (
                f"fallbackModel references retired model {entry!r}"
            )
