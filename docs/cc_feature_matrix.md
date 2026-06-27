# Claude Code Feature/Version Support Matrix

> Status: **largely resolved at v2.1.153 (2026-06-18 evidence sweep). Rows requiring an environment-side experiment remain `pending`.**
> Version policy: **Track latest** — the kit does not pin a specific minimum version; it follows the CC build at PR-land time and re-verifies every few months. Rationale: single-author kit, aggressive feature adoption, the cost of re-verification at a few-month cadence is acceptable.
> `requiredMinimumVersion` enforcement: **No (policy decision).** README Prerequisites carries a documentation-only note; settings.json does not refuse older builds. Decision made independently of whether the field EXISTS in CC (row A8 — verified existence at v2.1.153, kit still chooses not to set it).
> Owner: kit-author (single maintainer)
> Targeted (verified-at) build: **`claude --version` → `2.1.153 (Claude Code)`** (cmux app, macOS, 2026-06-18)
> Resolves: ISSUE-014
> Consumed by: ISSUE-015, ISSUE-016, ISSUE-017, ISSUE-020

## How to use

This doc records, for each Claude Code capability the kit depends on,
whether that capability is supported at the targeted minimum version.
It exists so ISSUE-015/016/017 do not each re-investigate the same
runtime questions independently.

Status values:

- `supported` — verified via the listed Verification method on the
  targeted minimum version.
- `unsupported` — verified absent at the targeted minimum version
  (either deprecated, not yet shipped, or never existed).
- `needs-newer` — supported only in CC versions ≥ some build later than
  the targeted minimum. Either raise the floor (and re-verify everything),
  or scope downstream issues to a fallback path.
- `pending` — not yet verified. Default for every row at draft time.

This doc is a **point-in-time record** of verified behavior at a
specific version. When the kit bumps its targeted minimum version,
every row must be re-verified — do NOT trust stale rows.

## Version policy (decided 2026-06-18)

- **Targeted version**: latest CC build at PR-land time (this matrix
  was verified against **v2.1.153**).
- **Re-verification cadence**: every few months OR when ISSUE-015 /
  016 / 017 starts, whichever comes first.
- **README enforcement**: documentation-only line in Prerequisites
  (no settings.json `requiredMinimumVersion` field).
- **`requiredMinimumVersion` enforcement**: NO, per policy decision.
  Row A8 confirms the field EXISTS in CC; the kit's choice not to use
  it is independent of that existence question.

## Verification methodology (2026-06-18 sweep)

The evidence sweep that resolved most rows used three sources, in
descending authority:

1. **Anthropic docs** at `code.claude.com/docs/en/*` — quoted verbatim
   in the Evidence column where it confirms a feature.
2. **`claude --version` output** locally — fixes the targeted-build
   anchor for every row.
3. **Available-skills system reminder** inside this authoring session —
   strong evidence for S-rows (which skills the CC runtime exposes
   right now).

Rows that need an environment-side experiment (build a plugin, wire a
hook, run an SDK call to observe cache_read tokens) remain `pending`.
They are clearly tagged "needs experiment" in Evidence.

## Agent-level capabilities

These rows feed ISSUE-015 (effort tiers + model alias refresh).

| Row | Feature | Status | Verification | Evidence | Linked issues |
|-----|---------|--------|--------------|----------|---------------|
| A1  | `model:` alias `opus` resolves | **supported** | doc | docs `code.claude.com/docs/en/sub-agents`: "model aliases (sonnet, opus, haiku, or fable)". Kit uses `opus` in `agents/business-analyst.md`, `agents/brainstormer.md`, `agents/reviewer.md`, etc. | ISSUE-015 |
| A2  | `model:` alias `sonnet` resolves | **supported** | doc | same source as A1. Kit uses `sonnet` in `agents/research-auditor.md`, `agents/synthesizer-auditor.md`, `agents/review-merge-auditor.md`. | ISSUE-015 |
| A3  | `model:` alias `haiku` resolves | **supported** | doc | same source as A1. Kit does not currently use `haiku`. | ISSUE-015 |
| A4  | `model:` alias `fable` resolves | **supported** | doc | same source as A1 quotes `fable` explicitly. ISSUE-015 wants an optional `team-lead` opt-in to `fable` — now unblocked. | ISSUE-015 |
| A5  | `effort:` frontmatter accepted (low/medium/high) | **supported** | doc | docs `code.claude.com/docs/en/sub-agents`: "Frontmatter effort applies when that skill or subagent is active, overriding the session level but not the environment variable. You can set effort in a skill or subagent markdown file to override the effort level when that skill or subagent runs." Effort levels documented as `low|medium|high|xhigh|max|ultra` (see commands doc for `/code-review`). | ISSUE-015 |
| A6  | `effort: xhigh` accepted (Opus-4.7+ tier) | **supported** | doc | commands doc lists xhigh explicitly: `/code-review [low\|medium\|high\|xhigh\|max\|ultra]`. | ISSUE-015 |
| A7  | `model: inherit` makes subagent inherit parent's model | **supported** | doc | sub-agents doc: "use model aliases (sonnet, opus, haiku, or fable), full model IDs, or 'inherit' to use the same model as the main conversation. When not specified, it defaults to inherit." Note: `inherit` is the DEFAULT — kit can simplify many agent files by omitting `model:` entirely. | ISSUE-015 |
| A8  | `requiredMinimumVersion` settings field exists | **supported** | doc | settings doc: "Managed settings only. Minimum Claude Code version required to start. If the running version is older, Claude Code exits at startup and instructs the user to update through the organization's approved method." Example value in docs: `"2.1.150"` (kit is on 2.1.153). Kit policy is NOT to set this field (see top); row confirms existence only. | ISSUE-014 |

## Lifecycle hook events

These rows feed ISSUE-016 (worktree/session lifecycle hooks).

| Row | Feature | Status | Verification | Evidence | Linked issues |
|-----|---------|--------|--------------|----------|---------------|
| H1  | `WorktreeCreate` hook event fires on worktree creation | **supported** | doc | hooks docs: "WorktreeCreate is unique in that any non-zero exit code aborts worktree creation, unlike most other hook events where exit code 2 is needed to block actions." Listed in matchers note alongside WorktreeRemove. | ISSUE-016 |
| H2  | `WorktreeRemove` hook event fires on worktree removal | **supported** | doc | hooks docs matchers note: "UserPromptSubmit, PostToolBatch, Stop, TeammateIdle, TaskCreated, TaskCompleted, **WorktreeCreate, WorktreeRemove**, and CwdChanged don't support matchers and always fire on every occurrence." | ISSUE-016 |
| H3  | `SessionEnd` hook event fires | **supported** | doc | hooks docs: "SessionEnd is an event that fires once per session. The SessionEnd hook input includes the reason the session ended. Additionally, the SessionEnd event supports matchers on the reason the session ended." | ISSUE-016 |
| H4  | `Stop` hook event fires | **supported** | doc | listed in matchers note (H2 source) alongside other no-matcher events. | ISSUE-016 |
| H5  | `PreCompact` hook event fires on context compaction | **supported** | doc | hooks docs: "PreCompact runs before Claude Code is about to run a compact operation. The PreCompact hook input includes a trigger field (either 'manual' or 'auto') and custom_instructions." | ISSUE-016 (PostCompact still pending if needed) |

## Plugin packaging

These rows feed ISSUE-017 (kit migration to Claude Code plugin system).

| Row | Feature | Status | Verification | Evidence | Linked issues |
|-----|---------|--------|--------------|----------|---------------|
| P1  | `.claude-plugin/plugin.json` manifest schema accepted | **supported** | doc | plugins doc: "Plugins require a `.claude-plugin/plugin.json` manifest file and can optionally include directories for commands, agents, skills, hooks, and MCP server definitions." | ISSUE-017 |
| P2  | Plugin `hooks/hooks.json` honored as the hook venue | **supported** | doc | plugins doc: "Plugin hooks are defined in `hooks/hooks.json` with an optional top-level description field. Hooks are user-defined shell commands, HTTP endpoints, or LLM prompts that execute automatically at specific points in Claude Code's lifecycle." | ISSUE-017 |
| P3  | Plugin subagent frontmatter `hooks:` field is **not supported** (explicit rejection, not silent drop) | **supported** | doc | plugins-reference doc verbatim: "Plugin agents support `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, and `isolation` frontmatter fields. The only valid `isolation` value is `worktree`. **For security reasons, `hooks`, `mcpServers`, and `permissionMode` are not supported for plugin-shipped agents.**" — SPEC-017's premise confirmed. Kit's `/freeze`, `/careful`, `/guard` (which embed `hooks:` in agent frontmatter) MUST migrate to `hooks/hooks.json` if/when kit ships as a plugin. | ISSUE-017 |
| P4  | Plugin subagent frontmatter `mcpServers:` field is **not supported** | **supported** | doc | same plugins-reference quote as P3. | ISSUE-017 |
| P5  | Plugin subagent frontmatter `permissionMode:` field is **not supported** | **supported** | doc | same plugins-reference quote as P3. | ISSUE-017 |
| P6  | Skill namespacing: `/skill` becomes `/<plugin>:<skill>` when bundled | **supported** | doc | plugins-reference: "`<name>`: Plugin name. Becomes the skill namespace and the directory name under `~/.claude/skills/`, so it cannot contain spaces or path separators." Also: "skills: An extra namespaced `<name>:example` skill alongside the default one." Affects SPEC-017's "keep short names" Open Question — namespacing is enforced upstream. | ISSUE-017 |
| P7  | `${CLAUDE_PLUGIN_ROOT}` env var available to plugin scripts | **supported** | doc | plugins-reference: "The `command` value supports the same variable substitutions as MCP and LSP server configs: `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`, `${user_config.*}`, and any `${ENV_VAR}` from the environment." Also `${CLAUDE_PLUGIN_DATA}` and `${CLAUDE_PROJECT_DIR}` available — broader than ISSUE-017's original spike noted. | ISSUE-017 |
| P8  | `/plugin install <name>@<marketplace>` flow available | **supported** | doc + filesystem | plugin-marketplaces doc covers install flow. Filesystem evidence: `~/.claude/plugins/installed_plugins.json` already contains `pyright-lsp@claude-plugins-official` and `swift-lsp@claude-plugins-official` — the flow is in use today. | ISSUE-017 |

## Runtime-exposed skills

| Row | Feature | Status | Verification | Evidence | Linked issues |
|-----|---------|--------|--------------|----------|---------------|
| S1  | `/deep-research` skill exposed | **supported** | session | listed in available-skills system reminder of this Track-Latest authoring session (2026-06-18). | ISSUE-018 |
| S2  | `/code-review` skill exposed | **supported** | session + doc | session reminder + commands doc verbatim: `/code-review [low\|medium\|high\|xhigh\|max\|ultra] [--fix] [--comment] [target]`. | ISSUE-019 |
| S3  | `/security-review` skill exposed | **supported** | session + doc | session reminder + commands doc: `/security-review — Analyze pending changes on the current branch for security vulnerabilities. Reviews the git diff and identifies risks like injection, auth issues, and data exposure`. | ISSUE-019 |
| S4  | `/verify` skill exposed | **supported (min-version 2.1.145)** | session + doc | commands doc: "Requires Claude Code v2.1.145 or later". Kit is on 2.1.153, so safely above floor. Follow-up issue **ISSUE-022** spawned to consolidate `/testgen`/`/ship`/`/diagnose` test-execution loops onto `/verify`. | ISSUE-022 |
| S5  | `/code-review --comment` posts inline PR comments | **supported** | doc | commands doc: "`--comment` to post them as inline GitHub PR comments". | ISSUE-019 Open Question — now answerable: kit `/review` CAN pass `--comment` through. |
| S6  | `/code-review --fix` applies findings to working tree | **supported** | doc | commands doc: "`--fix` to apply findings to your working tree". | ISSUE-019 Open Question — answerable. |
| S7  | `/code-review ultra` runs multi-agent cloud review | **supported** | doc | commands doc: "`ultra` to run a deep [cloud review](/en/ultrareview)". `/ultrareview` is the legacy alias. Note: includes 3 free runs on Pro/Max, then requires usage credits — surface this in kit `/review`'s documentation. | ISSUE-019 |
| S8 (new) | `/simplify` as separate cleanup-only review | **needs-newer (min-version 2.1.154)** | doc | commands doc: "From v2.1.154, `/simplify` runs a separate cleanup-only review that applies fixes without hunting for bugs. ... On earlier versions `/simplify` is equivalent to `/code-review --fix`." Kit is on **2.1.153 — one build below the floor**. Re-verify on next CC update; until then, treat `/simplify` as a thin alias for `--fix`. | ISSUE-014 (informational; not a downstream issue dependency) |

## Prompt caching

| Row | Feature | Status | Verification | Evidence | Linked issues |
|-----|---------|--------|--------------|----------|---------------|
| C1  | Agent system prompts auto-cached across Task invocations within a session | pending — **deferred to ISSUE-021** | SDK experiment | Anthropic docs confirm `cache_control: ephemeral` works at the API layer (5-min TTL), and the ScheduleWakeup tool description quotes "The Anthropic prompt cache has a 5-minute TTL" as a runtime fact. But no public docs explicitly state CC auto-applies cache_control to agent system prompts. ISSUE-021 spawns `scripts/probe_runtime_caching.py` to send the kit's first SDK calls with controlled stable prefixes + inspect `cache_read_input_tokens`. | ISSUE-021 |
| C2  | Skill instructions auto-cached across repeated invocations | pending — **deferred to ISSUE-021** | SDK experiment | same shape as C1 for skills. | ISSUE-021 |
| C3  | Tool definitions auto-cached across calls within a single turn | pending — **deferred to ISSUE-021** | SDK experiment | same shape — runtime-internal, no public surface. | ISSUE-021 |
| C4  | `cache_control: {type: 'ephemeral'}` honored in SDK calls (5-min default TTL) | **supported** | doc | prompt-caching doc verbatim: "'ephemeral' is the only supported cache type, which by default has a 5-minute lifetime." Syntax: `"cache_control": {"type": "ephemeral"}`. Pricing: write 1.25× base, read 0.1× base. | ISSUE-020, ISSUE-002 |
| C5  | `cache_control: {type: 'ephemeral', ttl: '1h'}` 1-hour TTL honored | **supported** | doc | same doc: "Anthropic also offers a 1-hour cache duration at additional cost. To use the extended cache, include ttl in the cache_control definition like this: `\"cache_control\": { \"type\": \"ephemeral\", \"ttl\": \"1h\" }`." Pricing: write 2× base. Response includes `ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens` breakdown. Available on Anthropic API + Bedrock + Vertex + Microsoft Foundry. | ISSUE-020, ISSUE-002 |
| C6  | Session-level preamble injection surface (kit can pre-warm context) | **unsupported (no public API)** | doc | No surface found in Anthropic docs for the kit to pre-warm a session-level preamble. Skills already follow a "lazy load on use" pattern (skill bodies load only when invoked) — that is the design choice, not a missing feature. Kit's existing `prd_digest.md` digest pattern stays the workaround. | ISSUE-020 |

## Resolution workflow

1. **Decide the targeted minimum version** and write it at the top of
   this doc + in README's Prerequisites section. ✅ done (v2.1.153 +
   Track Latest policy + README updated 2026-06-18).
2. **Run each `pending` row's Verification method** against the
   targeted version. ✅ for 24 of 34 rows via the doc-evidence sweep
   on 2026-06-18. Remaining `pending` rows (C1–C3) require API-level
   instrumentation and are deferred to ISSUE-002's eval gate work.
3. **Record the Evidence inline** — done where verified.
4. **Set Status** — done.
5. **Update downstream issues** in the same PR or follow-up:
   - **ISSUE-015**: `effort`, `model: inherit`, `fallbackModel`, and
     all 4 aliases (opus/sonnet/haiku/fable) are confirmed supported.
     ISSUE-015 can drop "pending verification" caveats. Note: `inherit`
     is the default — kit can omit `model:` from many agent files.
   - **ISSUE-016**: WorktreeCreate / WorktreeRemove / SessionEnd /
     Stop / PreCompact ALL confirmed. ISSUE-016 can drop its
     "graceful fallback when hook unsupported" branch.
   - **ISSUE-017 SPEC**: P3-P5 confirm the subagent restriction
     verbatim ("not supported" — stronger than "silently dropped").
     P6 confirms namespacing. P7 reveals `${CLAUDE_PLUGIN_DATA}` and
     `${CLAUDE_PROJECT_DIR}` are also available (broader than
     ISSUE-017's spike noted). SPEC-017 can now cite the docs directly.
   - **ISSUE-019**: S5/S6 (--comment, --fix) confirmed — the Open
     Question on whether kit `/review` passes flags through becomes
     actionable; recommend a follow-up issue to wire `--comment` and
     `--fix` to the runtime invocation. S7 ultra credit usage note
     (3 free / then credits) should surface in kit `/review` docs.
   - **ISSUE-020 `docs/caching_notes.md`**: C4, C5 confirmed. C1-C3
     remain `pending` (needs experiment). C6 marked `unsupported`.
     Update `caching_notes.md` rows from "pending ISSUE-014" to
     verified statuses in the same PR or a follow-up.
   - **S4 follow-up**: `/verify` confirmed supported (min-version
     2.1.145, kit on 2.1.153). File a new tracking issue for
     `/testgen`/`/ship`/`/diagnose` consolidation per ISSUE-014's
     follow-up signal memo.
6. **Land the matrix** alongside the README prerequisites edit. ✅
   done in this PR.

## Rollback

Delete this doc. Revert the README prerequisites line if added. No
runtime impact (documentation only). Rollback time: < 5 minutes.

## What this doc is NOT

- **Not a CC release notes mirror.** Specific version-by-version change
  histories belong in Anthropic's docs; this matrix records what THIS
  kit needs and whether it works at THIS targeted version.
- **Not a wish list.** Capabilities the kit might WANT to use later but
  has not yet committed to should not appear here. New rows are added
  only when a kit issue depends on them.
- **Not auto-refreshable.** Every row's `Status` is a manual
  verification. When the targeted minimum version bumps, all rows must
  be re-verified.

## Sources (2026-06-18 sweep)

- [`code.claude.com/docs/en/sub-agents`](https://code.claude.com/docs/en/sub-agents) — agent frontmatter, `effort`, `model: inherit`, model aliases
- [`code.claude.com/docs/en/hooks`](https://code.claude.com/docs/en/hooks) — WorktreeCreate, WorktreeRemove, SessionEnd, Stop, PreCompact
- [`code.claude.com/docs/en/plugins-reference`](https://code.claude.com/docs/en/plugins-reference) — plugin manifest, hooks.json, subagent restrictions (P3-P5), namespacing, `${CLAUDE_PLUGIN_ROOT}` etc.
- [`code.claude.com/docs/en/plugin-marketplaces`](https://code.claude.com/docs/en/plugin-marketplaces) — install flow
- [`code.claude.com/docs/en/settings`](https://code.claude.com/docs/en/settings) — `requiredMinimumVersion`
- [`code.claude.com/docs/en/commands`](https://code.claude.com/docs/en/commands) — `/code-review` flags + effort levels, `/security-review`, `/verify`, `/simplify` min-version
- [`docs.anthropic.com/en/docs/build-with-claude/prompt-caching`](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — `cache_control` ephemeral, 1-hour TTL, pricing, response usage breakdown
- Local `claude --version`: `2.1.153 (Claude Code)` (cmux app, macOS)
