# Independent Review — FrameAI Multi-Provider Runtime Architecture

> Reviewed artifact: `docs/provider-architecture.md`  
> Review basis: PER-19 requirements, PER-17 audit, PER-18 findings, and current `frame` execution paths  
> Method: refute-first static design review; no implementation or provider invocation

## Verdict

**Approve with conditions.** The design establishes the requested provider boundary without claiming false semantic parity, keeps Claude as the backward-compatible default, forbids unsafe automatic fallback, and directly incorporates all three PER-18 remediation themes. It is suitable as the implementation-planning baseline after the two Medium findings below are resolved in the implementation specification. No production-code implementation should start until the open routing/environment and pinned Codex CLI decisions receive operator approval.

Confidence: **High** for repository and Claude-compatibility findings; **Medium** for Codex feasibility because the Codex CLI version/contract has intentionally not yet been pinned or exercised.

## Findings

### Finding 1 — Medium: Supporting interface types are named but not contracted

- **Evidence:** Architecture §3.2 makes `EnvironmentReport`, `ParsedProviderOutput`, and `CancellationToken` part of the public `Provider` protocol, but §3.1 and §4 define no fields or invariants for those types.
- **Impact:** Two adapters can satisfy the method signatures while returning incompatible capability/routing diagnostics or parsed evidence. Cancellation ownership and thread/process safety could also diverge, weakening contract tests.
- **Required remediation:** Before implementation, define immutable schemas for all three types. At minimum, `EnvironmentReport` must carry provider/version, executable resolution, routing mode, redacted variable-name/source inventory, capability statuses and blocking violations; `ParsedProviderOutput` must separate advisory summary from structured evidence; `CancellationToken` must define monotonic state and process-group termination semantics.

### Finding 2 — Medium: Pre-execution mutation boundary is internally ambiguous

- **Evidence:** Architecture §3.1 says `ExecutionRequest` is created after current run-directory creation, while §6 requires invalid provider selection to fail “before scaffolding or provider execution.” Current `frame add` scaffolds `automations/<slug>/input.md` before checking for the Claude executable, and `frame run` creates its run archive before provider validation.
- **Impact:** An implementation could accidentally change existing `--dry-run`, missing-binary, invalid-provider, or failed-preflight side effects. Tests would then encode whichever interpretation an implementer chose rather than an approved compatibility decision.
- **Required remediation:** Add a per-operation lifecycle table specifying the exact order of local validation, provider selection, scaffolding/archive creation, dry-run rendering, environment validation, execution and normalization. Explicitly decide whether only an invalid provider fails before mutation while missing executable/routing validation preserves or changes current artifact creation. Snapshot these side effects in acceptance tests.

## Requirement coverage

| Review area | Result | Evidence |
|---|---|---|
| Requested module boundary | Pass | §2 defines `providers/base`, `claude`, `codex` and `runtime/normalized_result` plus supporting runtime modules |
| Common provider interface | Pass with condition | §3.2 includes all five requested methods; Finding 1 covers missing auxiliary schemas |
| Normalized result/error | Pass | §4 defines typed statuses, errors and cross-field invariants, including `partial` |
| `add/run/refine` compatibility | Pass with condition | §5 preserves prompt/archive behavior; Finding 2 requires exact lifecycle ordering |
| Provider selection/fallback | Pass | §6 defaults to Claude, requires explicit Codex selection and prohibits automatic fallback |
| Process safety and logging | Pass | §8 specifies argv, `shell=False`, cwd, explicit env, process groups, redaction, timeout/cancellation and partial artifacts |
| Claude enterprise routing | Pass | §7 includes Bedrock/Vertex/AWS credential-chain sources and routing fail-closed without value logging |
| Codex auth/config boundary | Pass | §7 defers credentials to Codex CLI and gates exact names/argv on a pinned approved version |
| PER-18 capability detail | Pass | §9 explicitly covers hook payload/exit semantics, allowed-tools patterns, WebSearch, SlashCommand, PDF/image and parallel subagents |
| Safety parity | Pass | §9 rejects unsupported required safety capability and makes functional degradation explicit |
| Completion/partial failure | Pass | §§4, 5, 11 distinguish filesystem evidence, completion contract and partial results |
| Testability | Pass | §13 provides fake executable, selection, environment/routing, schema/path and behavioral fixtures |
| Rollback | Pass | §14 keeps default Claude, uses explicit selection/revert, preserves archives and avoids destructive cleanup |
| Design-only scope | Pass | Header and §12 explicitly defer implementation to another task |

## Refute-first checks

1. **Could a command-name swap still pass this design?** No. Capability gates, provider-specific rendering, security parity and structured contract tests prevent treating `codex` as a renamed `claude`.
2. **Could an environment allowlist silently bypass Seoul Bedrock routing?** The design explicitly forbids this and requires routing conflicts/missing metadata to fail closed. The exact credential-chain inventory remains an approval gate, appropriately.
3. **Could provider prose create false success?** No for the target contract: filesystem/process evidence is authoritative and structured provider output is only supplementary. Legacy zero-output behavior is isolated behind a compatibility decision.
4. **Could timeout/fallback duplicate writes?** Timeout retains partial artifacts and automatic provider fallback/retry is prohibited.
5. **Does the base interface overpromise semantic parity?** No. §10 keeps Claude discovery/hooks and Codex-specific semantics within adapters and exposes capability degradation separately.

## Residual risks and approval gates

- The exact Codex non-interactive command, structured output, authentication/configuration names and supported version remain unknown by design. They must be verified against the pinned official CLI contract before the Codex adapter is enabled.
- AWS/Google credential chains can depend on files, SSO, instance roles or external processes. The approved pass-through/source policy and trusted endpoint/region verification must be decided before replacing full environment inheritance.
- Stable timeout values, new exit codes, archive retention and acceptable functional degradation per operation require operator approval.
- Prompt/archive redaction cannot protect existing historical archives; the design correctly avoids rewriting or deleting them, so operational access/retention remains a separate risk.

## Review conclusion

The architecture is a sound, reversible design baseline and addresses the blocking PER-18 routing concern. Resolve Findings 1 and 2 as explicit contract/lifecycle tables, obtain the listed operator decisions, and then create a separate implementation issue with staged acceptance gates. No code change is approved by this review.
