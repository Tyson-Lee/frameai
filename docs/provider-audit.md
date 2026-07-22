# FrameAI Claude Code Provider Audit

> Issue: PER-17  
> Audit date: 2026-07-21  
> Scope: repository snapshot only; no production code or external service was modified  
> Method: static inspection of tracked source, configuration, tests, and documentation. Runtime archives under `.claude/run/` and `automations/*/runs/` were excluded because they are generated evidence, not provider contracts, and may contain user data.

## Executive summary

FrameAI does not currently have a provider boundary. The `frame` executable directly locates and launches the `claude` binary, while the orchestration layer is authored around Claude Code's repository discovery, skills, agents, Task tool, slash commands, hooks, model aliases, and settings schema. Replacing only the three `subprocess.run(["claude", "--print", prompt], ...)` calls would therefore not provide behavioral compatibility.

The direct executable dependency is concentrated in one file and three commands: `frame add`, `frame run`, and `frame refine`. The wider runtime dependency spans `.claude/`, `project/.claude/`, every `agents/*.md` definition, most `skills/*/SKILL.md(.tmpl)` orchestration, setup/install scripts, and Claude-specific documentation. There is no Anthropic SDK import in application code and no explicit API-key handling in `frame`; authentication is delegated completely to the installed Claude Code CLI/session.

Confidence: **high** for repository-visible dependencies; **medium** for runtime behavior because this audit intentionally did not authenticate, invoke a model, or inspect external Claude Code state.

## System map

```text
user / CI
   |
   v
./frame (Python, provider-hardcoded)
   |-- add/refine: prompt as final argv value
   |-- run: prompt as final argv value + FRAMEAI_RUN_* environment
   v
claude --print <prompt>                 [authentication owned by Claude Code]
   |
   |-- discovers CLAUDE.md
   |-- discovers .claude/skills -> skills/
   |-- discovers .claude/agents -> agents/
   |-- loads .claude/settings.json and hooks
   |-- interprets /prd, /kickoff, /sprint, Task, Read/Write/Bash, etc.
   v
working-tree artifacts / automations/<slug>/runs/<timestamp>/outputs/

Claude Desktop / other MCP client
   -> scripts/frameai_mcp_server.py
   -> exposes skill instructions as MCP tools
   -> client runtime executes the instructions (not the `frame` headless path)
```

## 1. CLI invocation points

| Location | Command | Exact invocation | Working directory | Process I/O |
|---|---|---|---|---|
| `frame:258` | `frame add` | `["claude", "--print", prompt]` | repository root | inherited stdin/stdout/stderr; returns child exit code |
| `frame:392` | `frame run` | `["claude", "--print", prompt]` | repository root | stdout and stderr merged into run `log.txt`; returns child exit code |
| `frame:445` | `frame refine` | `["claude", "--print", prompt]` | repository root | inherited stdin/stdout/stderr; returns child exit code |

All three paths first call `find_claude()` (`shutil.which("claude")`, `frame:197-198`). There is no executable path option, provider selector, command factory, protocol adapter, version check, timeout, retry, or process cancellation policy.

Additional CLI assumptions:

- `setup.sh` and `install.sh` require `claude` on `PATH`; `setup.ps1` and `install.ps1` do the same with PowerShell command discovery.
- `setup.sh` and `setup.ps1` run `claude --version` only to report the installed version.
- Setup documentation instructs users to enter the repository and run `claude`, or probe commands with `claude --print "/help"`.
- `frame.cmd` only forwards to Python and does not abstract the provider.

## 2. Prompt passing

### `frame add`

`ADD_PROMPT` is a large static Python format string (`frame:44-181`). It interpolates the generated `slug` and repository-relative `automations/<slug>/input.md` path, then passes the complete prompt as one command-line argument. The prompt assumes Claude Code can:

- resolve and execute `/prd`, `/kickoff`, and `/sprint`;
- understand Claude Code skill layout and frontmatter;
- use Bash, Read, Write, git worktrees, and repository-relative paths;
- generate and invoke `SKILL.md` files through Claude Code discovery;
- leave working-tree changes for later review.

`--dry-run` prints the exact prompt and skips the CLI invocation, but scaffolding (`automations/<slug>/input.md`) has already occurred.

### `frame run`

The prompt is assembled line-by-line (`frame:340-357`) and includes the skill name, copied input paths, raw joined free-form text, output directory, and execution instructions. It is passed both:

- in-band as the final `claude --print` argument; and
- partly out-of-band through inherited environment plus `FRAMEAI_RUN_INPUTS`, `FRAMEAI_RUN_OUTPUTS`, `FRAMEAI_RUN_TEXT`, and `FRAMEAI_RUN_MODE=cli` (`frame:375-380`).

The exact prompt is persisted to `prompt.txt`. The four environment values, including the unredacted free-form `FRAMEAI_RUN_TEXT`, are persisted to `log.txt` before execution. This is a data-retention/security concern rather than a provider feature, but any adapter must preserve or deliberately revise this contract.

### `frame refine`

`REFINE_PROMPT` (`frame:183-195`) interpolates `slug` and the user's refinement text, instructs the runtime to edit repository artifacts, run generation and tests, and preserve the public skill/archive contract. It is also passed as one command-line argument.

### Chat and MCP paths

- Claude Code chat invocation depends on native `/<slug>` or natural-language skill dispatch and the absence of `FRAMEAI_RUN_MODE` to select self-bootstrap behavior.
- `scripts/frameai_mcp_server.py` reads skill instructions and exposes them as MCP tools for Claude Desktop/Cursor. This is a separate client-driven execution path; it does not invoke `claude --print` and cannot be treated as proof of Codex CLI compatibility.

## 3. Output parsing and completion semantics

There is effectively **no model-output parser**.

- `frame add` and `frame refine` stream the provider's text directly to the terminal and use only the process return code.
- `frame run` merges stdout and stderr into `log.txt`; it does not parse text, JSON, tool events, or provider-specific result envelopes.
- `frame run` determines delivered outputs by recursively listing regular files under the pre-created `outputs/` directory after the process exits. The provider's printed file list is advisory and ignored.
- A zero exit with no output files is reported as a warning message but still returns zero. A non-zero exit may still leave partial output files, which are listed before the non-zero status is returned.
- No `--output-format` is supplied, so behavior depends on Claude Code's default `--print` rendering remaining human-readable.

This filesystem-based output contract is the strongest reusable seam for another provider. Terminal prose is not a stable API today.

## 4. Authentication assumptions

Facts:

- `frame` does not read or validate `ANTHROPIC_API_KEY`, credentials files, subscription state, login state, Bedrock settings, or provider endpoints.
- The complete parent environment is inherited by `claude` (`os.environ`; explicitly copied in `frame run`, implicitly inherited in `add`/`refine`).
- Install/setup checks prove only that a binary named `claude` exists; `claude --version` does not prove an authenticated end-to-end model call.
- There is no preflight such as a harmless authenticated prompt, and no classification of login, quota, network, policy, or billing errors.
- README authentication guidance concerns GitHub push (`GH_TOKEN`/SSH), not Claude/Anthropic authentication.

Inference: FrameAI assumes the operator has already completed whatever authentication and provider routing the local Claude Code installation requires. An adapter must not translate that into a new secret requirement without an approval decision and approved secret binding.

## 5. Error handling

| Condition | Current behavior | Provider coupling / gap |
|---|---|---|
| Empty description/refinement, missing skill/input | local message, exit `2` | provider-neutral validation |
| `claude` absent from `PATH` | exact error `FrameAI: \`claude\` CLI not found on PATH. Install Claude Code first.`, exit `3` | hardcoded provider and remediation |
| CLI exits non-zero | return the same exit code | no normalized error taxonomy or user guidance |
| CLI hangs | waits indefinitely | no timeout/cancellation policy |
| CLI emits stderr | terminal for add/refine; merged into `log.txt` for run | no structured distinction between diagnostics and result |
| CLI writes partial files | files remain and are listed | no transaction/rollback or completion marker |
| CLI exits zero but writes no files | warning only, exit remains `0` | false-success possible |
| setup script fails | shell/PowerShell-specific checks and messages | checks installation, not authenticated capability |

There are no retries. This is appropriate for avoiding duplicate agent actions, but the absence of idempotency/completion markers means a future adapter must not add automatic retry casually.

## 6. Configuration and runtime contracts

### Repository discovery

`setup.sh` creates symlinks and `setup.ps1` creates junctions:

- `.claude/skills -> ../skills`
- `.claude/agents -> ../agents`
- `.claude/hooks -> ../project/.claude/hooks`
- `.claude/settings.json`, initially copied from `project/.claude/settings.snippet.json`

This is a Claude Code-native loading mechanism. There is no equivalent neutral registry consumed by `frame`.

### Settings and hooks

`project/.claude/settings.snippet.json` is the distributable source for:

- Claude model fallback IDs (`fallbackModel`);
- Claude-specific `statusLine` command location;
- hook event names/matchers including `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `PreToolUse`, `PostToolUse`, and `PostToolUseFailure`;
- Claude tool names such as `Write`, `Edit`, `Bash`, `Task`, and `Agent`;
- shell commands that locate `.claude/hooks/*.py`.

The checked-in `.claude/settings.json` is runtime-local/generated configuration and currently differs from the snippet's first fallback model. Consumers should treat the snippet as distribution intent and detect drift explicitly.

### Skills and agents

- Every `agents/*.md` file uses Claude Code subagent frontmatter, including `model:` aliases (`opus`/`sonnet`) and `effort:` levels.
- Skills use Claude Code frontmatter such as `disable-model-invocation` and assume slash-command arguments/runtime behavior.
- Orchestration skills explicitly invoke the Claude Code `Task` tool with `subagent_type`, including parallel calls and retry rules.
- Several skills delegate to runtime slash commands such as `/deep-research`, `/code-review`, `/security-review`, and `/verify`, probed through `scripts/has_skill.py` against Claude skill/plugin locations.
- Generated automation skills use the `FRAMEAI_RUN_*` dual-mode contract but still direct the model to use Claude Code tools and Task subagents.

### Other Claude-specific paths

- `CLAUDE.md` is automatically injected by Claude Code and contains the repository operating contract.
- `scripts/has_skill.py` searches `~/.claude/skills`, project `.claude/skills`, and `~/.claude/plugins/installed_plugins.json`.
- `scripts/kit_config.py`, `scripts/kit_update_check.py`, and contributor reporting use the historical `~/.claude-kit/` state namespace.
- `pyproject.toml` package name/description remain `claude-dev-kit`; this is naming/metadata coupling, not an invocation dependency.
- The MCP server and Desktop registration are Claude Desktop-oriented but use the provider-neutral MCP protocol at their boundary.

## 7. Tests

Existing tests cover parts of the Claude runtime contract:

- `tests/test_agent_effort_and_model_refs.py`: validates agent `model:`/`effort:` metadata and `fallbackModel` shape/retired IDs.
- `tests/test_agent_state.py`, `tests/test_hook_runner.py`: validate `.claude/run` state and worktree hook resolution.
- `tests/test_autotest.py`, `tests/test_dangerous_command_guard.py`: validate hook implementations wired through Claude settings.
- `tests/test_has_skill.py`: validates discovery through Claude user/project/plugin locations.
- `tests/test_review_delegation_guard.py`: asserts runtime delegation/subagent contract markers.
- `tests/test_gen_skills.py` and lint/guard tests indirectly preserve generated Claude skill structure.

Critical coverage gaps:

- no unit test for `frame` command dispatch;
- no fake executable test asserting argv, cwd, environment, stdout/stderr handling, or exit-code propagation;
- no test for missing CLI (`exit 3`) or authenticated/unavailable runtime errors;
- no end-to-end `claude --print` smoke test;
- no contract test proving zero-exit/no-output behavior;
- no provider-neutral fixtures against which Claude Code and Codex CLI could be compared;
- no check that `.claude/settings.json` matches the distributable snippet.

## 8. Documentation inventory

| Document | Direct dependency documented |
|---|---|
| `README.md` | Product is presented primarily as a Claude Code skill builder; installation, chat UX, headless CLI, `.claude` discovery, Desktop MCP, models, hooks, and limitations |
| `CLAUDE.md` | Auto-loaded Claude project context; `claude --print`, dual-mode variables, Task/runtime delegation, model/fallback assumptions |
| `CONCEPT.md` | Current reliance on Claude Code skills/agents/hooks/headless mode and planned plugin/MCP direction |
| `docs/cc_feature_matrix.md` | Versioned Claude Code feature assumptions for agents, hooks, plugins, runtime skills, and caching |
| `docs/cache_friendly_authoring.md`, `docs/caching_notes.md` | Anthropic/Claude prompt-cache assumptions and authoring rules |
| `docs/security.md`, `docs/telemetry_schema.md` | Claude hook enforcement and Claude runtime event/tool schema assumptions |
| `automations/*/README.md`, `before_after.md` | User-facing examples and runtime claims centered on `frame run`/Claude behavior |
| `setup.*`, `install.*` messages | Claude installation, version, repository launch, Desktop configuration |

No document currently defines a provider interface or behavioral equivalence criteria for Claude Code versus Codex CLI.

## Prioritized risk register

| Priority | Risk | Evidence | Impact | Confidence |
|---|---|---|---|---|
| P0 | No provider abstraction despite wide runtime semantics | direct `claude --print`; Task/slash command/hooks throughout skills | a command-name swap can silently lose orchestration, safety hooks, and output guarantees | high |
| P0 | Hook-based safety controls are runtime-specific | `.claude/settings*` wires secret/dangerous-command guards to Claude events/tools | another runtime may execute edits/commands without equivalent guard coverage | high |
| P1 | Success is only process exit status; no completion contract | no parser/manifest; zero exit with empty outputs remains success | false success and partial deliverables | high |
| P1 | No authenticated CLI preflight or normalized errors | PATH/version checks only | login/quota/network failures are opaque to operators | high |
| P1 | Prompt and free-form input are persisted unredacted | `prompt.txt`; `FRAMEAI_RUN_TEXT` in `log.txt` | sensitive operator input can enter archives | high |
| P1 | Runtime has unrestricted inherited environment | child inherits all environment variables | provider process can receive unrelated secrets; behavior differs by shell | high |
| P2 | No timeout/cancellation behavior | blocking `subprocess.run` without timeout | hung automation blocks indefinitely | high |
| P2 | Distribution/runtime settings can drift | snippet copied only if local settings absent; current files differ | inconsistent model/hook behavior across installations | high |
| P2 | No CLI dispatch tests | test inventory contains no `frame` process harness | regressions in argv/env/error handling are likely | high |
| P2 | Provider-specific product language and paths are pervasive | docs, package metadata, `.claude*` paths | migration scope and operator expectations can be underestimated | high |

## Proposed acceptance checks for a future provider boundary

These are proposals only; adopting the provider contract is an explicit approval gate.

1. **Executable contract:** inject provider executable/config; assert exact argv, cwd, environment allowlist, and missing-binary error with a fake CLI.
2. **Prompt contract:** snapshot provider-neutral task intent separately from provider rendering for `add`, `run`, and `refine`; ensure hostile/free-form text cannot alter argument structure.
3. **Filesystem result contract:** require an explicit completion manifest or define exact rules for zero outputs, partial outputs, and non-zero exits.
4. **Error contract:** normalize at least `not_installed`, `not_authenticated`, `permission_denied`, `rate_limited`, `network_error`, `timeout`, `provider_failed`, and `contract_violation`, while retaining the exact redacted provider error.
5. **Safety parity:** prove secret guard, dangerous-command guard, write-scope restriction, review checkpoint, and worktree isolation on each provider. Unsupported controls must fail closed or be explicitly accepted as residual risk.
6. **Capability contract:** inventory required operations (read/write/shell, skills, subagents, parallel tasks, slash/runtime skills, hooks) and provide a supported/degraded/unsupported matrix per provider.
7. **Authentication check:** use only the provider's approved existing credential binding; run a minimal non-mutating prompt and record version, expected/actual result, redacted error, and exit code.
8. **Behavioral fixtures:** run one deterministic fixture for each of `add`, `run`, and `refine`; compare created paths, content schema, exit status, and prohibited writes rather than natural-language prose.
9. **Regression gate:** run current focused tests plus new provider-contract tests with Claude Code as the baseline; preserve current Claude behavior before enabling Codex CLI.
10. **Operator documentation:** document setup, authentication ownership, evidence locations, cleanup, rollback, known degraded features, and provider selection.

## Rollback and recovery observations

This audit changed only `docs/provider-audit.md`; rollback is removal or revert of that single documentation file. No runtime, infrastructure, credential, generated automation, or production state was changed.

For a future implementation, the smallest reversible shape is an opt-in provider selector defaulting to the current Claude Code path. Keep all existing prompt construction and archive paths initially, add a fake-provider test harness, and make fallback explicit rather than automatic. Rollback should be a configuration change back to `claude` plus removal/revert of the adapter commit; existing `runs/` archives must not be rewritten or deleted.

## Blocking issues and recommendations

Blocking issue for implementation: the minimum provider contract and acceptable safety degradation have not been approved. In particular, Claude Code Task/hooks/slash-command capabilities cannot be assumed to exist in Codex CLI under the same names or lifecycle.

Recommendation: approve a narrowly scoped provider contract only after the capability and safety-parity checks above are reviewed independently. Do not begin by changing the hardcoded executable alone.

## Audit limitations

- No model invocation, authentication test, network call, production access, or infrastructure inspection was performed.
- External Claude Code documentation was not re-fetched; this report describes the repository's declared assumptions, with `docs/cc_feature_matrix.md` as existing evidence.
- Generated run logs were excluded from dependency enumeration except to confirm that their paths exist; their contents are not required to establish the source-level provider contract.
- “Every direct dependency” means every dependency visible in this repository snapshot. User-level Claude configuration, plugins, managed settings, and shell wrappers may add dependencies outside the repository.
