# FrameAI Multi-Provider Runtime Architecture

> Issue: PER-19  
> Status: design only; implementation is intentionally deferred to a separate task  
> Inputs: `docs/provider-audit.md` (PER-17) and independent review PER-18

## 1. Decision summary

FrameAI remains a Python modular monolith. A narrow provider boundary is inserted between the existing `frame add/run/refine` orchestration and CLI processes. `claude` remains the default, so existing commands and archives remain compatible. `codex` is selected only through explicit configuration. There is no automatic cross-provider fallback because retrying an agent with another provider can duplicate writes and can change data-routing policy.

The provider layer owns process mechanics and provider-specific rendering/parsing. The runtime layer owns provider-neutral requests, normalized results, completion rules, redaction, and policy gates. Provider adapters do not interpret business workflows or rewrite skills.

```text
frame (argument validation, scaffolding, run archive)
  -> runtime/service.py (selection, policy, lifecycle)
     -> providers/base.py (contract)
        |-> providers/claude.py
        `-> providers/codex.py
     -> runtime/normalized_result.py
     -> runtime/capabilities.py
     -> runtime/redaction.py
```

## 2. Proposed module tree

```text
frameai/
├── providers/
│   ├── __init__.py          # registry; no side effects
│   ├── base.py              # Provider protocol and immutable request/process types
│   ├── claude.py            # Claude Code argv, routing environment, output/error mapping
│   └── codex.py             # Codex CLI argv, environment, output/error mapping
└── runtime/
    ├── __init__.py
    ├── service.py           # provider lifecycle and compatibility facade
    ├── normalized_result.py # result/error schemas and invariants
    ├── capabilities.py      # required capability and safety-policy evaluation
    └── redaction.py         # log/environment redaction
```

The top-level directory is named `frameai/` to avoid colliding with the executable `frame`. Packaging changes, if required, belong to the implementation task.

## 3. Provider-neutral contracts

### 3.1 Request and process types

```python
ProviderName = Literal["claude", "codex"]
Operation = Literal["add", "run", "refine"]

@dataclass(frozen=True)
class ExecutionRequest:
    operation: Operation
    prompt: str
    cwd: Path
    run_dir: Path | None
    inputs_dir: Path | None
    outputs_dir: Path | None
    text_argument: str | None
    timeout_seconds: float | None
    required_capabilities: frozenset[str]

@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]       # never a shell command string
    cwd: Path
    env: Mapping[str, str]
    stdout_mode: Literal["inherit", "capture_to_log"]
    stderr_mode: Literal["inherit", "merge_to_log", "capture_separately"]

@dataclass(frozen=True)
class ProcessOutcome:
    returncode: int | None
    stdout: str | None
    stderr: str | None
    started_at: datetime
    finished_at: datetime
    timed_out: bool = False
    cancelled: bool = False
```

`ExecutionRequest` is built only after current local validation and run-directory creation. User text is always one argv element through the provider renderer; `shell=True` is forbidden. `cwd` must resolve to the repository root. Input/output paths must resolve inside the run archive for `run`.

### 3.2 Provider interface

```python
class Provider(Protocol):
    name: ProviderName

    def build_command(self, request: ExecutionRequest, env: Mapping[str, str]) -> CommandSpec: ...
    def validate_environment(self, request: ExecutionRequest, env: Mapping[str, str]) -> EnvironmentReport: ...
    def execute(self, command: CommandSpec, *, cancel: CancellationToken | None) -> ProcessOutcome: ...
    def parse_output(self, request: ExecutionRequest, outcome: ProcessOutcome) -> ParsedProviderOutput: ...
    def normalize_error(self, request: ExecutionRequest, outcome: ProcessOutcome,
                        parsed: ParsedProviderOutput | None) -> NormalizedError | None: ...
```

Method invariants:

- `validate_environment()` is non-mutating. It checks executable presence/version, required configuration names, routing conflicts and declared capabilities; it never logs credential values or performs a model call by default.
- `build_command()` is deterministic for the same request/config, returns an argv tuple, and cannot weaken validation decisions.
- `execute()` is the only subprocess boundary. It applies timeout, cancellation, process-group cleanup, I/O policy and redacted logging. It does not retry.
- `parse_output()` treats terminal prose as advisory. It may parse a provider-supported structured envelope, but filesystem evidence remains authoritative for `run` until a completion manifest is implemented.
- `normalize_error()` maps known evidence conservatively. Unknown non-zero failures become `provider_failed`; ambiguous zero-exit contract failures become `contract_violation`, never a guessed auth/network category.

## 4. Normalized result and error

```python
ResultStatus = Literal["success", "failed", "partial", "cancelled", "timed_out"]
ErrorCode = Literal[
    "not_installed", "not_authenticated", "permission_denied",
    "rate_limited", "network_error", "timeout", "cancelled",
    "provider_failed", "contract_violation", "unsupported_capability",
    "routing_policy_violation",
]

@dataclass(frozen=True)
class NormalizedError:
    code: ErrorCode
    message: str                 # safe operator-facing summary
    retryable: bool              # advice only; runtime never auto-retries
    provider_exit_code: int | None
    redacted_detail: str | None

@dataclass(frozen=True)
class NormalizedResult:
    provider: ProviderName
    operation: Operation
    status: ResultStatus
    summary: str
    files_changed: tuple[str, ...]
    tests_run: tuple[str, ...]
    raw_log_path: str | None
    error: NormalizedError | None
    started_at: str
    finished_at: str
```

Invariants:

- `success` requires exit code 0 and satisfaction of the operation completion contract; `error` is `None`.
- `failed`, `cancelled`, and `timed_out` require a non-null error.
- `partial` means useful filesystem changes exist but the process or completion contract failed; it also requires an error and never converts to exit 0.
- Paths are repository-relative, normalized, and cannot contain paths outside the repository. `raw_log_path` points to a redacted local archive.
- `files_changed` comes from a before/after filesystem inventory (restricted to the expected scope), not provider prose. `tests_run` is empty unless backed by structured or independently captured execution evidence.

For backward compatibility, the CLI initially returns the provider exit code when non-zero; FrameAI-local validation remains exit 2 and missing executable remains exit 3. New timeout/cancellation/contract statuses receive documented stable exit codes during implementation rather than being invented in this design.

## 5. Execution flows

### `frame add` and `frame refine`

Existing prompt construction and inherited terminal streaming remain unchanged in migration stage 1. The runtime validates the chosen provider, builds the command and normalizes its exit. Changed files are inventoried only within approved repository scopes. Because these operations intentionally edit repository artifacts, a non-zero exit with changes is `partial`.

### `frame run`

The existing archive layout (`inputs/`, `outputs/`, `prompt.txt`, `log.txt`) is preserved. The runtime adds a machine-readable `result.json`. `FRAMEAI_RUN_INPUTS`, `FRAMEAI_RUN_OUTPUTS`, `FRAMEAI_RUN_TEXT`, and `FRAMEAI_RUN_MODE=cli` remain available to both adapters. Sensitive free-form text must no longer be copied verbatim into the log header; `prompt.txt` retention is documented as sensitive and follows existing archive access controls.

Stage 1 completion is exit 0 plus output-directory inventory, preserving current zero-output behavior only behind an explicit compatibility flag. The target contract is a FrameAI-owned atomic `completion.json` written after process exit from independently observed evidence. Providers must not be trusted to self-declare paths outside `outputs/`. Non-zero exit, timeout or cancellation with output files is `partial`.

## 6. Selection and fallback

Selection precedence is proposed as `--provider` > `FRAMEAI_PROVIDER` > repository configuration > `claude`. Allowed values are an exact registry key. Unknown values fail before scaffolding or provider execution.

There is no automatic Claude-to-Codex or Codex-to-Claude fallback. A fallback may only be an explicit second user invocation after reviewing partial changes. This preserves idempotency, billing expectations, authentication boundaries and data residency. Provider model selection remains adapter-owned and must not reinterpret existing Claude model aliases as Codex models.

## 7. Environment, authentication, and routing

The runtime starts from a minimal provider-specific pass-through policy plus FrameAI variables. It records only variable names, sources and validation outcomes, never values.

Claude policy must account for:

- direct Claude Code session/authentication owned by the installed CLI;
- `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_PROFILE`, and the approved AWS/Google credential-chain mechanisms;
- mutually exclusive Bedrock/Vertex routing flags;
- required region/profile policy supplied by the operator.

When a routing mode is configured, missing or conflicting required routing metadata is `routing_policy_violation` and fails closed before execution. The adapter must not silently fall back to Anthropic infrastructure. Exact credential-chain pass-through is an implementation approval decision: broad parent-environment inheritance is insecure, but a simplistic allowlist can break instance-role, profile-file, SSO or external-process authentication. Tests inventory names and source types; values are always redacted. Endpoint/region verification for production requires trusted external evidence, not model self-report.

Codex authentication and configuration are likewise owned by Codex CLI. The adapter validates binary/version and mutually conflicting supported config names without reading, copying or committing credential files. Repository code must not introduce a new API-key requirement. Exact Codex argv and environment names must be pinned from the approved CLI version's official contract in the implementation task.

## 8. Process and log policy

- Use `subprocess` with argv, fixed repository `cwd`, `shell=False`, an explicit environment map, and a new process group/session.
- Default timeout remains disabled in the first compatibility stage; the implementation must add an opt-in timeout before selecting a global default. On timeout/cancel, terminate the process group, wait a bounded grace period, then kill; retain partial artifacts.
- `add/refine` keep inherited I/O initially. `run` merges provider output into the archive as today, with an explicit marker containing provider/version but no secret values or raw `FRAMEAI_RUN_TEXT`.
- Redaction covers known token/key patterns, configured sensitive environment values, authorization headers and provider credential paths. Redaction happens before persistent writes; failure to initialize the redactor fails closed for captured logs.
- Raw unredacted provider output is not persisted elsewhere by FrameAI. Archive access and retention remain an operator responsibility until a separate retention feature is approved.

## 9. Capability and safety contract

Every operation declares required capabilities. Provider enablement is denied if a required safety capability is `unsupported`; functional degradation requires an explicit operator-approved policy.

| Capability | Claude baseline evidence | Codex gate | Policy |
|---|---|---|---|
| Read/write/shell and scoped writes | Claude tools + prompts/hooks | deterministic fixture | required; writes outside scope fail |
| Hook input schema | `tool_name`, `tool_input.file_path/content/new_string/command`, `hook_event_name`, `agent_id`, `agent_type` | native equivalent or wrapper evidence | safety hooks must fail closed |
| Hook exit semantics | Claude event/exit behavior | mapped and contract-tested | required for guard parity |
| `allowed-tools` command patterns | Claude frontmatter enforcement | equivalent enforcement | required where skill declares it |
| secret and dangerous-command guards | current Claude hooks | pre-execution equivalent | required for protected operations |
| `Task`, parallel subagents, identity fields | Claude runtime | supported/degraded fixture | explicit degradation allowed only for non-safety workflows |
| `SlashCommand` and runtime skills | `/review`, `/verify`, etc. | provider renderer/alternative workflow | no silent name substitution |
| `WebSearch` | Claude tool contract | provider-native evidence | operation-specific |
| PDF/image native read | documented Claude Read behavior | deterministic PDF/image fixture | degraded mode must be visible |
| worktree isolation/concurrency | current skills/hooks | provider-independent wrapper | required for parallel writes |

Capability status is `supported`, `degraded`, or `unsupported`, with repository evidence, provider/version and last verification date. Marketing or model self-report is not evidence.

## 10. Provider responsibilities

`ClaudeProvider` preserves `claude --print <prompt>` in the first stage, supports current stdout modes, and maps only verified Claude diagnostics. It does not move Claude skill, agent or hook discovery into the base interface.

`CodexProvider` renders the same provider-neutral request into the pinned Codex non-interactive command contract. It must not assume Claude slash commands, Task names, hook events, model aliases or settings discovery. Unsupported required capabilities stop execution. Codex-specific structured output may enrich `summary` and errors but cannot override filesystem or policy evidence.

The base interface contains only mechanics common to both. Provider-specific capability implementations remain in their adapters; this avoids pretending semantic parity exists where it does not.

## 11. Failure handling

| Failure | Result | Required behavior |
|---|---|---|
| binary absent | `failed/not_installed` | no subprocess; preserve legacy exit 3 |
| authentication evidence recognized | `failed/not_authenticated` | redact detail; never print credentials |
| routing conflict/missing required region | `failed/routing_policy_violation` | fail before execution; no fallback |
| timeout/cancel | `timed_out`/`cancelled` | stop process group; inventory partial files |
| non-zero with files | `partial/provider_failed` (or verified specific code) | retain artifacts and log; no retry |
| zero exit, required output absent | `failed/contract_violation` | compatibility flag only for legacy behavior |
| output outside allowed scope | `failed/contract_violation` | report paths; do not auto-delete user data |
| parser cannot understand prose | exit-based result unless structured output required | preserve redacted raw log |

## 12. Implementation stages (separate task)

1. Add immutable schemas, provider registry, fake provider/process harness and contract tests without changing CLI behavior.
2. Route existing Claude calls through `ClaudeProvider`; default remains Claude and golden tests prove argv/cwd/env/I/O/exit compatibility.
3. Add normalized `result.json`, redaction and completion rules behind compatibility controls.
4. Implement `CodexProvider` against one pinned, documented CLI version; keep selection opt-in.
5. Run capability/safety fixtures and approved non-production authentication/routing smoke tests; enable only operations whose required gates pass.
6. Update installation, selection, fallback, archive sensitivity, degraded-feature and rollback documentation.

Each stage is independently revertible. Existing `runs/` archives are never migrated or deleted.

## 13. Verification and acceptance criteria

- Fake executables assert exact argv element boundaries, repository cwd, I/O, timeout/cancel cleanup and exit propagation for all three operations and both providers.
- Selection tests prove default Claude, explicit Codex, invalid-provider rejection and absence of automatic fallback.
- Environment tests prove approved variable-name pass-through, redaction, routing conflict failure and no unintended credential-variable propagation. Separate approved Bedrock/Vertex tests verify endpoint/region using trusted external evidence.
- Result-schema tests cover success, failure, partial, timeout, cancellation, zero-output and path-escape cases; JSON serialization is stable.
- Behavioral fixtures compare created paths/content schema/prohibited writes, not natural-language output.
- Hook payload and exit fixtures cover every field listed in the capability matrix. Dedicated fixtures cover allowed-tool patterns, WebSearch/SlashCommand behavior, PDF/image read and parallel subagent identity/isolation.
- Current focused Claude tests remain green before Codex is enabled. Security parity gates cannot be waived by a provider adapter.
- No auth file, environment value, prompt secret or unredacted provider diagnostic is newly committed or logged.

## 14. Rollback

Operational rollback is explicit selection of `claude` followed, if necessary, by reverting the adapter/runtime commits. Because the default stays Claude and archives are additive, rollback does not rewrite user artifacts. If routing validation fails, operators fix the approved routing configuration; they must not bypass it by automatic direct-provider fallback. Partial working-tree changes require human review rather than automated deletion.

## 15. Open approval decisions

1. Exact supported Codex CLI version, non-interactive argv, structured-output mode and authentication/config names.
2. Exact Claude and Codex environment pass-through sets, including AWS/Google credential-chain source types and enterprise routing policies.
3. Stable new CLI exit codes and the deprecation window for legacy zero-exit/no-output behavior.
4. Which functional capability degradations are acceptable per `add`, `run`, and `refine`; safety capability degradation is not accepted by default.
5. Default timeout/cancellation grace period and log/archive retention policy.
6. Whether `completion.json` is runtime-generated only or includes a separately namespaced provider assertion.

These decisions gate implementation and provider enablement, not this architecture document.

## 16. Tradeoffs and self-review

| Decision | Chosen | Rejected | Rationale |
|---|---|---|---|
| architecture | modular monolith | service/plugin process | lowest operational cost and reversible extraction |
| result truth | process + filesystem evidence | terminal prose | current stable seam; avoids provider wording dependency |
| fallback | explicit reinvocation | automatic provider fallback | avoids duplicate writes and routing-policy bypass |
| environment | provider policy with approved credential-chain sources | full inheritance or naive universal allowlist | balances secret minimization with enterprise auth compatibility |
| capability parity | explicit matrix and fail-closed safety gates | common interface implying semantic parity | makes degradation observable |

Self-review: The design preserves existing Claude defaults, separates mechanics from provider semantics, covers non-zero/partial/timeout/routing failures, and does not add infrastructure or implementation code. The strongest unresolved risk is the exact credential pass-through and Codex CLI contract; both are deliberately approval-gated. Confidence is **high** for the repository-derived boundary and migration shape, and **medium** for Codex command/auth details until pinned official-version verification occurs.
