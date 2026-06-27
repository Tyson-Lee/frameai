# Cache-Friendly Authoring Guide

> Audience: contributors writing or editing skill templates, agent files, and any
> kit script that calls the Anthropic SDK directly.
> Companion: see [`caching_notes.md`](./caching_notes.md) for the runtime-behavior
> cheat-sheet (what is auto-cached, what requires explicit `cache_control`).

## The rule (one line)

**Stable content first. Dynamic content last. Tool-result-loaded context
pre-summarized into a digest.**

That's it. Three patterns below show what it looks like in practice; two
anti-patterns show what to avoid. The lint in
`scripts/lint_skill_cache_order.py` enforces the structural piece of this
rule on every `SKILL.md.tmpl` (the first non-frontmatter, non-blank,
non-comment line must be `{{PREAMBLE}}`).

## Why this matters

Anthropic's prompt cache keys on the **longest common prefix** of the
request. Within a single skill invocation, the model is called many times
(one call per turn / tool result). If the prefix is stable across those
calls — same system prompt, same kit preamble, same boilerplate — the
cache hit rate is high and the per-call cost drops dramatically. If a
contributor accidentally interleaves dynamic content (a fresh `git log`,
a per-turn date stamp, a user-supplied path) **before** the stable
preamble, the prefix changes every turn and the cache resets cold.

The default cache TTL is 5 minutes; with `cache_control: {type:
"ephemeral", ttl: "1h"}` it's 1 hour. So even a moderately long skill
session benefits substantially from this rule.

**Honest framing.** The kit's `scripts/preambles.py` dedupes preamble
content across 25 skill templates (20 core under `skills/` + 5 under
`packs/sales/skills/` — count verified 2026-06-18). This is a
**code-maintenance win** — contributors edit one constant, not 25 copies.
It is NOT a **cross-skill cache win** — each skill is a distinct file
loaded as instructions, so the runtime does not see "the same preamble
across skills" as a shared prefix. The cache win is **within a single
skill's multi-turn execution**, and that win depends on the preamble
being placed first.

## Pattern 1 — Skill preamble immediately after frontmatter

Every `skills/*/SKILL.md.tmpl` opens with this shape:

```markdown
---
name: <skill>
description: …
allowed-tools: …
---

{{PREAMBLE}}
Steps:
1) …
```

`{{PREAMBLE}}` expands (via `scripts/preambles.py`) to the kit's tiered
boilerplate (Kit Update Check, Project Context Detection, Behavioral
Rules, Contributor Mode, and for Tier 2/3 also Checkpoint / Worktree /
Registry / Self-Review / Parallel Management blocks). It is a 30–80-line
stable prefix that the model sees on every turn within the skill.

Lint enforcement: `scripts/lint_skill_cache_order.py` fails if
`{{PREAMBLE}}` is missing or placed after any non-blank, non-comment
content line.

## Pattern 2 — Digest-file pre-summarization

When a skill needs context from a long-lived state file (e.g. PRD,
review_lessons, sprint_state, architecture), have the skill `Read` a
**stable digest** rather than the raw file. The digest changes much less
often than the live file, so the cache prefix stays warm across multiple
skill invocations within the same session.

Concrete kit examples:

- `docs/prd_digest.md` is the digest of the full PRD. Pipeline skills
  read the digest, not the raw `docs/prd.md`.
- `docs/sprint_state.md` is itself a digest (status table), not the full
  per-issue history.

Authoring rule: if you find yourself instructing a skill to `Read` a file
that grows monotonically, write the digest pattern instead.

## Pattern 3 — Agent system prompt stability

`agents/*.md` files are the runtime's system prompt for the corresponding
subagent. Within a single session, multiple Task invocations of the same
agent reuse the agent file as the system prompt — the runtime caches this
automatically (per ISSUE-014's probe; pending confirmation for the
targeted runtime version).

Authoring rule for agent files:

- Keep the agent body stable. Avoid embedding per-invocation data
  (timestamps, run IDs, current issue numbers) in the system prompt.
  Pass those as user-message context instead.
- If you need conditional behavior, branch on tool-loaded files inside
  the agent prompt's instructions — the file content arrives as a tool
  result, not as part of the cached prefix.

## Anti-pattern 1 — Interleaving stable + dynamic

❌ Bad:

```markdown
---
name: ship
---
**Current run ID**: <generated at invocation time>
{{PREAMBLE}}
Steps:
…
```

The "Current run ID" line is dynamic and sits before the stable
`{{PREAMBLE}}`. Every invocation produces a different prefix, defeating
the cache. The lint catches this shape.

✅ Good: emit the run ID inside the Steps body or as a tool result,
after the stable prefix. The dynamic content lives in cache-cold
territory where it belongs.

## Anti-pattern 2 — Recomputing the same context per turn

❌ Bad: a skill that runs `git log` or `gh pr view` at the start of
every Step (because the contributor copy-pasted the boilerplate) — each
call returns slightly different output (timestamps, ephemeral PR
metadata), and the tool-result lines become part of the prompt's tail.
By itself this is fine (tail churn is cheap), but if the skill then
**includes those outputs in later prompt text** (e.g., "Based on the
git log above, …"), the included text varies per turn and pushes
unrelated dynamic content into the prefix of later turns.

✅ Good: compute the dynamic context **once** at the start, write it to
a digest file, and have later steps reference the digest. The digest
content is stable for the rest of the session, so subsequent turns get
prefix hits.

## Runtime vs. kit responsibility split

Caching is a two-layer concern. The kit owns the structural pieces; the
runtime owns the mechanical caching itself.

**Runtime owns (kit cannot override)**:

- Whether agent system prompts are auto-cached across Task invocations
  within a session. (Pending ISSUE-014 probe row (a).)
- Whether skill instructions (SKILL.md content) are auto-cached when
  the same skill is invoked repeatedly. (Pending row (b).)
- The default 5-min TTL and the 1-hour `cache_control` option.

**Kit owns**:

- **Structural placement** — preamble first, digest before raw file,
  agent prompt stable. The lint enforces the easiest of these.
- **Explicit `cache_control`** when a kit script calls the Anthropic
  SDK directly (today: zero scripts; tomorrow: ISSUE-002 eval gate is
  the first candidate, and its DoD now mandates `cache_control` on the
  rubric + diff per ISSUE-020).
- **Documentation** that prevents future contributors from over-claiming
  the caching benefit (e.g. "kit preamble dedup gives cross-skill cache
  hits" — it does NOT).

For the matrix of runtime auto-caching behavior, see
[`caching_notes.md`](./caching_notes.md).

## When kit code calls the Anthropic SDK directly

Today: no kit script imports `anthropic` or uses `cache_control`. (Verified
2026-06-18 audit.) The first scheduled candidate is ISSUE-002 (eval
gate, currently deferred). ISSUE-020 added a hard acceptance criterion
to ISSUE-002 that the rubric + diff inputs MUST be wrapped in
`cache_control: {type: "ephemeral"}` blocks before the eval gate can
ship.

Future scripts should follow the same rule:

- Wrap stable inputs (rubrics, schemas, system prompts, frequently-reused
  reference docs) in `cache_control` blocks.
- Use the 1-hour TTL (`ttl: "1h"`) for inputs that survive across many
  invocations within a session (e.g., a rubric used to review every PR
  in a sprint).
- Use the default 5-min TTL for inputs that survive only within a single
  multi-turn run.
- Measure the cache-hit token reduction in a determinism run and report
  it in the script's output. If the reduction is below ~50% for an
  input that should be cache-hot, something is wrong with the placement.

## How to verify your changes

- Run `python3 scripts/lint_skill_cache_order.py` after editing any
  `SKILL.md.tmpl`. Exit code 0 = pass.
- Run `python3 -m pytest tests/test_lint_skill_cache_order.py -v` after
  changing the lint or adding a new skill template.
- For new SDK-calling scripts, write a regression test that asserts
  `cache_control` is present in the request payload for the inputs you
  intended to cache.
