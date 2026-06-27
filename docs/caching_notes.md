# Caching Notes — Runtime Behavior Cheat-Sheet

> Companion to [`cache_friendly_authoring.md`](./cache_friendly_authoring.md).
> This doc records what the Claude Code runtime caches automatically vs.
> what kit code must mark with explicit `cache_control`. Rows marked
> *pending ISSUE-014* will be filled in once that spike confirms behavior
> on the targeted runtime version. **Do not guess — leave rows pending
> until they are verified.**

## TL;DR

- **Within a single skill invocation** (multi-turn), the runtime caches
  the stable prefix. Kit's job: put stable content first. The lint
  (`scripts/lint_skill_cache_order.py`) enforces this for
  `SKILL.md.tmpl`.
- **Across skill invocations within a session**, runtime auto-caching of
  agent/skill system prompts is *pending verification* (ISSUE-014). Plan
  for it but do not depend on it.
- **For kit scripts that call the Anthropic SDK directly** (today: zero;
  tomorrow: ISSUE-002 eval gate), wrap stable inputs in `cache_control`
  blocks explicitly. The kit's authoring guide makes this a hard rule.

## What the runtime auto-caches

| Surface | Auto-cached? | TTL | Verified | Source |
|---|---|---|---|---|
| Agent system prompts across Task invocations within a session | *pending — ISSUE-021* | *pending* | ❌ | matrix row C1 — Anthropic docs confirm API-level prompt caching but do not publicly document whether CC auto-applies cache_control to agent prompts. ISSUE-021 spawns the SDK-probe script to resolve this. |
| Skill instructions (SKILL.md content) across repeated invocations | *pending — ISSUE-021* | *pending* | ❌ | matrix row C2 — same shape as C1 |
| Tool definitions across calls within a turn | *pending — ISSUE-021* | *pending* | ❌ | matrix row C3 — same shape |
| `cache_control: {type: "ephemeral"}` honored in SDK calls (5-min default) | **yes** | 5 min default | ✅ | matrix row C4 — Anthropic prompt-caching docs: "'ephemeral' is the only supported cache type, which by default has a 5-minute lifetime." |
| 1-hour TTL via `cache_control: {ttl: "1h"}` honored in SDK calls | **yes** | 1 h opt-in | ✅ | matrix row C5 — Anthropic prompt-caching docs: `"cache_control": { "type": "ephemeral", "ttl": "1h" }`. Pricing: 2× base on write. Available on Anthropic API + Bedrock + Vertex + Microsoft Foundry. Response carries `ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens` breakdown |
| Session-level preamble injection surface (kit can pre-warm context) | **no (no public API)** | n/a | ✅ | matrix row C6 — no documented surface for the kit to pre-warm. Skills' lazy-load-on-use is the design choice. `prd_digest.md` digest pattern remains the kit-side workaround |

Verified 2026-06-18 against CC v2.1.153. C1–C3 are runtime-internal
behavior — without an Anthropic-side instrumentation surface, the kit
must wait until a script (e.g. ISSUE-002's eval gate) actually calls
the SDK and inspects `cache_read_input_tokens` in the response to
resolve them.

## What kit code controls explicitly

| Concern | Mechanism | Owner | Status |
|---|---|---|---|
| `{{PREAMBLE}}` placement in skill templates | `scripts/lint_skill_cache_order.py` | kit | ✅ enforced |
| Stable preamble content deduped across templates | `scripts/preambles.py` (3-tier) | kit | ✅ done |
| Digest files pre-summarizing long-lived state | `docs/prd_digest.md`, `docs/sprint_state.md` | kit | ✅ partial |
| `cache_control` on stable inputs to SDK calls | per-script — see below | kit | ⏳ none today; ISSUE-002 DoD enforces on un-defer |
| Agent file stability (no per-invocation data in system prompt) | authoring discipline | kit | ⏳ guidance only; no lint |

## TTL choice — when to use 1h vs. 5min

- **Default 5-min ephemeral**: stable inputs that survive within a
  single skill's multi-turn run but not across runs. Most kit script
  candidates fall here. Lower miss cost on the first call; cache pays
  off across the turns of one run.
- **1-hour `ttl: "1h"`**: stable inputs that survive across many
  invocations within a session — a rubric used to review every PR in a
  sprint, a system prompt for a long-running agent panel, a reference
  doc consumed by multiple Task invocations. Higher miss cost on the
  first call; cache pays off across many subsequent calls.

Rule of thumb: if the input is reused fewer than ~3 times within an
hour, use 5-min; if more, use 1-hour.

## SDK-call scripts in the kit

Today (2026-06-18 audit): **none**. No `anthropic` SDK import, no
`cache_control` reference anywhere in the repo. The first scheduled
candidate is ISSUE-002 (eval gate, currently deferred). ISSUE-020 added
this hard acceptance criterion to ISSUE-002:

> Given `eval_review.py` sends the diff + rubric to the API, when the
> second run within the cache TTL executes, then both inputs are wrapped
> in `cache_control: {type: 'ephemeral'}` blocks and the report shows a
> measurable cache-hit token reduction (≥50%).

When ISSUE-002 un-defers, the implementer is required to satisfy this
criterion before merge. The DoD lives in `issues.md` ISSUE-002 entry.

Future SDK-call scripts (e.g. a future eval pass over UI prototypes, a
future memory-promotion ingest that uses an LLM to extract patterns)
follow the same rule. Add new rows to the table above when they land.

## Anti-claims to avoid

A handful of plausible-sounding statements about kit caching are
**wrong** and should not appear in skill docs or PR descriptions:

- ❌ "The kit's deduped preamble in `preambles.py` gives cross-skill
  cache hits."  
  *Why wrong*: each skill is a distinct file the runtime loads as
  instructions. The cache keys on the longest common prefix per request,
  not on text equality across different requests. Dedup is a code
  maintenance win, not a cache win.

- ❌ "Tool-loaded files (`Read` results) get prompt-cached."  
  *Why wrong*: tool results are appended to the conversation tail, not
  the cached prefix. They benefit from cache TTL only if they appear in
  the **same place** on subsequent calls — and the cache prefix is
  truncated at the first turn where text diverges.

- ❌ "1-hour cache is always better than 5-min."  
  *Why wrong*: 1-hour costs more on first miss. For inputs used only
  within a single skill run (typically < 5 min wall time), default
  5-min ephemeral is cheaper.

- ❌ "We don't need `cache_control` because the runtime caches
  automatically."  
  *Why wrong*: runtime auto-caching applies to system prompts and tool
  definitions managed by the runtime. When a kit script makes its own
  API call, the script's request payload is what the runtime sees —
  there is no kit-side wrapper to inject `cache_control` for you.

## Updating this doc

- When ISSUE-014 confirms a runtime caching capability, replace the
  *pending* row with the confirmed status and cite the verification
  source.
- When a new SDK-calling kit script lands, add a row under "SDK-call
  scripts in the kit" with the cached inputs and the TTL choice.
- When a new auto-caching surface is discovered (e.g., a future plugin
  preamble injection), add a row under "What the runtime auto-caches".
- Treat this doc as a **point-in-time record of verified behavior**. If
  the runtime changes, the doc must change in the same PR.
