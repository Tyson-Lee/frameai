# FrameAI Codex Adapter — Operator Notes

> Issue: PER-23
> Scope: non-production implementation and smoke-test preparation

## Contract

- Claude remains the default: `frame ...` continues to dispatch `claude --print <prompt>`.
- Select Codex explicitly with `--provider codex` or `FRAMEAI_PROVIDER=codex`.
- CLI selection takes precedence over `FRAMEAI_PROVIDER`; unknown environment values fail with exit `2` and never fall back.
- Codex dispatch is `codex exec --ephemeral --dangerously-bypass-approvals-and-sandbox --cd <resolved-repository-root> <prompt>`, with the prompt kept as one argv element. The same resolved repository root is also the process `cwd`, making that directory the explicit Codex primary workspace.
- Codex selection always passes `--dangerously-bypass-approvals-and-sandbox` because the approved FrameAI runtime supplies the external isolation boundary and nested Codex sandbox initialization fails with exact error `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. FrameAI prints a warning on every Codex selection. Never use Codex through FrameAI for an untrusted checkout or production target.
- `add`, `run`, and `refine` preserve their existing prompts, archive paths, stream handling, exit-code propagation, and no-retry behavior.
- FrameAI does not add, read, print, or persist provider credentials. Codex CLI owns authentication and configuration.
- No FrameAI timeout is enabled by default. This deliberately preserves the Claude baseline. Both adapters accept an opt-in process timeout; `subprocess.TimeoutExpired` is propagated unchanged and is not retried; selecting a stable CLI timeout/exit code remains a separate approval decision.

## Redacted preflight

The implementation host exposed `codex-cli 0.144.6` on `PATH` on 2026-07-21. Recheck on the smoke-test host without printing environment or auth files:

```bash
codex --version
python3 frame add --help
PYTHONPATH=. python3 tests/test_codex_adapter.py
PYTHONPATH=. python3 tests/test_frame_provider_integration.py
python3 -m pytest -q tests/test_claude_adapter.py tests/test_codex_adapter.py tests/test_frame_provider_integration.py
git diff --check
```

The `pytest` command requires the repository's `dev` dependencies. Do not install them globally or introduce credentials merely for this check.

## Non-mutating CLI checks

`frame add --dry-run` intentionally creates its existing scaffold before printing the prompt, so do not use it as a zero-write preflight. The following checks only parse CLI arguments:

```bash
python3 frame add --help
python3 frame run --help
python3 frame refine --help
```

## Live smoke checklist (operator approval required)

A live `codex exec` can consume account quota and modify the non-production checkout. Before running it, confirm the exact checkout, authentication binding, expected spend, allowed write scope, and rollback owner. Never paste tokens into commands or evidence.

Use a disposable automation fixture whose expected writes are restricted to its own `automations/<slug>/runs/<timestamp>/outputs/`. Capture only:

1. `codex --version` and FrameAI command with sensitive text replaced by `<redacted>`.
2. Expected versus actual exit code.
3. Created repository-relative paths and output schema, not file contents if sensitive.
4. Redacted `log.txt` excerpts, checking first that no credential or private input is present.
5. `git status --short` before and after, confirming no prohibited writes.

Run the same fixture once with default Claude and once with explicit Codex, then compare paths, archive structure, output schema, non-zero failure propagation, and prohibited writes. Do not compare natural-language wording as an equality signal.

## Rollback and recovery

Operational rollback is immediate: omit `--provider codex`, unset `FRAMEAI_PROVIDER`, or set it to `claude`. Code rollback is the revert of the PER-23 adapter/selection changes. Existing run archives are additive and must not be deleted automatically. Review partial files manually after a non-zero exit or interrupted process; there is no automatic retry or cross-provider fallback.

For the PER-27 workspace-root hardening specifically, rollback removes the `--cd <resolved-repository-root>` argument and restores the original `cwd` value in `frameai/providers/codex.py`. This does not remove files created by a prior run; inspect `git status --short` and recover or discard them through the normal review workflow.

## Known risks

- Codex does not consume Claude-specific `.claude/` skills, agents, hooks, or model aliases as equivalent native contracts. This adapter proves process and FrameAI archive compatibility, not semantic safety-feature parity.
- `frame run` retains the existing inherited environment and logs `FRAMEAI_RUN_TEXT`; changing redaction or environment pass-through would alter the Claude baseline and remains a separate approval-gated decision.
- A stable timeout, normalized result JSON, completion manifest, and capability-degradation policy are not introduced by PER-23.


To roll back the automatic bypass, restore `CodexAdapter` dispatch to `--sandbox workspace-write`. This will restore the earlier nested-sandbox failure on hosts where `bwrap` cannot initialize networking.
