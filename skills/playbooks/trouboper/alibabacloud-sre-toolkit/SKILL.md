---
name: alibabacloud-sre-toolkit
description: |
  Alibaba Cloud SRE skill for cloud infrastructure diagnosis, health inspection, capacity planning, incident response, and security audit, including scenarios where STAROps is unavailable and CLI fallback diagnosis is required. When users ask about ECS, ACK clusters, Pod issues, resource utilization, or fault troubleshooting, load this skill. Provides actionable SRE analysis reports and remediation recommendations via STAROps digital employees.
  Triggers: "sre-init", "sre-observability", "sre-incident", "sre-capacity", "sre-architecture", "sre-security", "巡检", "诊断", "容量规划", "故障排查", "安全审计", "健康巡检", "CrashLoopBackOff", "扩缩容", "资源利用率"
  Keywords: SRE operations, intelligent diagnostics, observability, monitoring, performance optimization, HA architecture, STAROps, Alibaba Cloud, ECS, ACK, Pod diagnostics, resource utilization, root cause analysis, scaling recommendations
---

## ⛔ CRITICAL RULES — Zero Tolerance

**Before ANY `aliyun` CLI or `starops_manager.py` command, verify ALL steps completed:**
1. ✅ `env-check` executed?
2. ✅ `list-accounts` executed?
3. ✅ `init` executed?

**If ANY answer is NO → STOP. Execute missing step(s) first.** Applies universally — single-account mode, multi-account mode, CLI fallback, even when environment "looks ready".

**EXECUTION LOCK**: Before executing ANY diagnostic, planning, or `aliyun` CLI command, you MUST verify that `.aliyun-sre/execution-trace.jsonl` contains valid records for `env-check`, `list-accounts`, AND `init`. If any record is missing, STOP immediately and execute the missing step(s). Do NOT proceed to `aliyun` CLI or `starops_manager.py` until all three steps are logged. Violation of this lock invalidates the entire session.

**Additional absolute prohibitions:**
- Never use `aliyun` CLI as primary diagnosis when STAROps is available
- Never skip `list-accounts` because "only one account" or "environment looks ready"
- Never generate session IDs manually (`openssl rand`, `uuidgen`, etc.) — only `session_manager.py init` generates valid session IDs
- Never enter Smart Discovery before calling `list-accounts`
- Never fall back to CLI without exhausting retry protocol (see Step 6)
- Never include raw AK/SK, secret tokens, or unmasked credential strings in ANY output file (diagnostic-report.md, inspection-report.md, or any .md/.json/.txt artifact). All credential references in reports MUST be masked (e.g., `LT****`) or replaced with `[REDACTED]`
- **NEVER execute cloud resource write operations via `aliyun` CLI.** The ONLY permitted `aliyun` CLI API patterns are read-only queries:
  - ALLOWED: `Describe*`, `List*`, `Get*`, `get-caller-identity`
  - FORBIDDEN (zero tolerance): `Create*`, `Delete*`, `Modify*`, `Add*`, `Remove*`, `Set*`, `Update*`, `Stop*`, `Start*`, `Restart*`, `Attach*`, `Detach*`, `Allocate*`, `Release*`, `Put*`, `PUT` (HTTP method), `POST` (HTTP method to cloud product endpoints), `Apply*`, `Bind*`, `Unbind*`, `Grant*`, `Revoke*`
  - This includes RESTful calls like `aliyun cs PUT /api/v2/clusters/...` and RPC calls like `aliyun slb add-access-control-list-entry`
  - Remediation commands MUST appear ONLY as text in reports (marked "requires manual user execution"), NEVER as executed commands

**Eval Validation Mapping** (direct causes of skill validation failure):
- Skipping `env-check` / `list-accounts` / `init` → **Step pass rate fails**
- Using `aliyun` CLI as primary diagnosis when STAROps available → **Forbidden action detected**
- Falling back to CLI without meeting trigger conditions → **Step pass rate fails**
- Not generating report file before final answer → **TestCase pass rate fails**
- Executing any cloud resource write operation (Create/Delete/Modify/Add/Stop/Restart/Set/Update via `aliyun` CLI) → **Forbidden action detected (read-only violation)**

---

# alibabacloud-sre-toolkit

Alibaba Cloud SRE intelligent operations skill. Completes the full workflow via STAROps digital employees: `env-check → [uid-select] → init → triage → diagnose → plan → self-validate → report`.

**Supported Environments**: LLM frameworks (Eino / LangChain / LlamaIndex) and Agent runtimes (Qoder / Claude Code / Codex / Cursor, etc.).

The **diagnostic/inspection workflow** is **read-only**. No cloud resource write operations during diagnosis. Onboarding configuration (first-time setup) includes user-triggered `CreateDigitalEmployee`/`DeleteDigitalEmployee` actions. All remediation requires manual user execution.

## Mandatory Command Sequence

> ⚠️ **WARNING**: These 5 steps are NON-NEGOTIABLE and MUST be executed in exact order. Substituting any step with direct `aliyun` CLI calls or skipping to Step 4/5 without completing Steps 1-3 is a critical workflow violation that invalidates the entire session.

For ANY SRE query, execute in exact order BEFORE any other action:

```bash
# Step 1: Environment check (always first)
python3 <skill-root>/scripts/session_manager.py env-check --cwd "$PWD"

# Step 2: List accounts (MUST — even single-account mode)
python3 <skill-root>/scripts/session_manager.py list-accounts --cwd "$PWD"

# Step 3: Initialize session
python3 <skill-root>/scripts/session_manager.py init --cwd "$PWD" --uid "<selected-UID>"

# Step 4: Create STAROps Thread (when STAROps available)
python3 <skill-root>/scripts/starops_manager.py create-thread --employee-id "<id>" --config "<config.json>" --uid "<uid>"

# Step 5: Send diagnostic query (SSE streaming)
python3 <skill-root>/scripts/starops_manager.py chat "<thread-id>" "<diagnostic-prompt>" --config "<config.json>" --uid "<uid>" --stream
```

These are NON-NEGOTIABLE. Do not substitute with direct `aliyun` CLI calls.

## CLI Fallback Decision Tree

Default path is always STAROps. CLI fallback is ONLY permitted when:

| # | Condition | Action |
|---|-----------|--------|
| 1 | User explicitly states STAROps unavailable | Skip STAROps → CLI fallback |
| 2a | `env-check` starops.available=false AND Smart Discovery fails due to **network errors** (Connection Refused / TCP Timeout) | Skip STAROps → CLI fallback |
| 2b | `env-check` starops.available=false due to **configuration missing** only | MUST enter Smart Discovery — CLI fallback FORBIDDEN |
| 3 | User explicitly requests CLI diagnosis | Skip STAROps → CLI fallback |
| 4 | 2 consecutive network-level failures after retry (Step 6) | CLI fallback |

**NOT CLI fallback triggers** (require retry, not fallback): SSE timeout, HTTP 409, HTTP 5xx, HTTP 401/403.

CLI fallback STILL requires: `env-check` → `list-accounts` → `init` → `update --status triaged` before any `aliyun` CLI call.

> **Hard Rule**: CLI fallback is ONLY permitted after Steps 1–3 are completed AND STAROps retry protocol (Step 6) is fully exhausted. Direct CLI usage without prior STAROps attempt is strictly forbidden.

## Installation

**Pre-checks:**
- Aliyun CLI >= 3.3.3: `aliyun version`. Install: download, review, then run the official setup script per [references/cli-installation-guide.md](references/cli-installation-guide.md). Update (>=3.3.5): `aliyun upgrade`.
- Python deps: `pip3 install -r scripts/requirements.txt`

### Runtime Dependencies

All API calls via aliyun CLI or `starops_manager.py`:
- **STAROps API** (CreateThread / CreateChat / ListDigitalEmployees etc.): via `starops_manager.py` (ACS3-HMAC-SHA256 signing, read-only credential resolution by profile).
- **STS / Cloud product read-only API** (get-caller-identity / describe-* / list-*): via `aliyun` CLI.

> **Safety**: STAROps `CreateThread`/`CreateChat` create diagnostic sessions only (not cloud resource changes). `CreateDigitalEmployee`/`DeleteDigitalEmployee` are onboarding-only operations.

## Authentication

> **Security Rules:** NEVER read/echo/print AK/SK values. NEVER ask user to input AK/SK. NEVER use `aliyun configure set` with literal credentials. ONLY use `aliyun configure list` to check status.
>
> **No telemetry or external tracing:** This skill does NOT send session data, diagnostics, or cloud resource information to any external service. No telemetry, tracing plugins, or data collection is included. STAROps diagnostic queries stay within the STAROps service endpoint (`*.aliyuncs.com`). Any agent runtime configuration (e.g., `.claude/settings.json`, `.qwen/settings.json`) that enables external tracing plugins must be disclosed and is NOT part of this skill. Specifically, `langfuse-tracing@Aliyun-Security-Scan-Market` found in `.claude/settings.json` is injected by the security scanning infrastructure during audit runs and is NOT authored, shipped, or controlled by this skill.

```bash
aliyun configure list
```

If no valid profile exists → STOP. Guide user to obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak) and configure outside this session.

**Credential source matches selected profile**: "single session, single UID, single digital employee" model. `starops_manager.py` resolves credentials read-only by `--uid`. Env var fallback: `ALIBABA_CLOUD_ACCESS_KEY_ID`/`ALIBABA_CLOUD_ACCESS_KEY_SECRET` (profiles take priority).

## RAM Policy

Diagnostic workflow is read-only. Requires STAROps CreateThread/CreateChat + read-only Describe\*/List\*/Get\* permissions. Onboarding additionally requires `CreateDigitalEmployee`/`DeleteDigitalEmployee` (user-triggered only). See [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** On any permission error: 1) Read `references/ram-policies.md` for required permissions, 2) Use `ram-permission-diagnose` skill to guide user, 3) Wait for user confirmation before continuing.

## Parameter Confirmation

ALL user-customizable parameters (RegionId, instance names, CIDR blocks, etc.) MUST be confirmed with user. Do NOT assume default values.

## Observability

**User-Agent**: Every `aliyun` CLI API command MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sre-toolkit/{session-id}`. Local utility commands (configure, plugin, version) excluded. Session ID comes from `init` output — never generate manually.

**Execution Trace**: Every `session_manager.py`/`starops_manager.py` call appends a JSONL record to `.aliyun-sre/execution-trace.jsonl` (timestamp, script, subcommand, args, session ID, exit code).

## Core Workflow

### Onboarding (sre-init)

Triggered when `env-check` shows failures or via `sre-init`. Wizard steps:

| Step | Check | Action |
|------|-------|--------|
| 1 | aliyun CLI >= 3.3.3 | Install via [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| 2 | Valid credentials | Guide `aliyun configure` (no AK/SK echo/input) |
| 3 | Python deps | `pip3 install -r <skill-root>/scripts/requirements.txt` |
| 4 | STAROps setup | Smart Discovery or manual `account-add`/`configure-set` |

Credential management (user-triggered): configure credentials via `aliyun configure` first, then `account-add` + `create-employee` (add), `delete-employee` + `account-delete` (remove). Completion: re-run `env-check` until `pass`. See [references/initialization-guide.md](references/initialization-guide.md).

### Supported Scenarios

| Scenario | Trigger | Output |
|----------|---------|--------|
| `observability-monitoring` | Metric analysis, log query, health inspection, alert insight | Inspection report + monitoring recommendations |
| `incident-response` | Root cause analysis, emergency remediation, rollback | Diagnostic report + emergency plan |
| `capacity-planning` | Resource utilization, capacity assessment, performance bottleneck | Capacity report + optimization recommendations |
| `architecture-reliability` | HA assessment, architecture review, reliability improvement | Architecture review + improvement plan |
| `security-audit` | Operation audit, risk identification, compliance check | Audit report + remediation recommendations |

Routing: fault/exception/Pod error → `incident-response`; metrics/logs/health → `observability-monitoring`; utilization/capacity → `capacity-planning`; HA/reliability → `architecture-reliability`; audit/compliance → `security-audit`; ambiguous → default `observability-monitoring`.

### Built-in Scripts

Located in `<skill-root>/scripts/`:
- `session_manager.py` — Session lifecycle and Profile management ([references/session-management.md](references/session-management.md))
- `starops_manager.py` — STAROps API CLI: CreateChat (SSE), CreateThread, ListDigitalEmployees, etc. ([references/starops-api.md](references/starops-api.md))
- `requirements.txt` — Python dependencies

> Shell state is not preserved across calls — each Bash invocation must use full absolute paths.

### Configuration

STAROps config at `<project-root>/.starops/config.json`. Uses `accounts` array (`uid -> profile -> employeeId`, workspace optional). **Credentials never persisted** (managed by aliyun CLI, resolved read-only). See [references/starops-config.md](references/starops-config.md).

### Step 1: Environment Pre-check

```bash
python3 <skill-root>/scripts/session_manager.py env-check --cwd "$PWD"
```

Checks CLI/credentials, STAROps config, accounts cross-validation, Python deps.
- `"status": "pass"` → proceed to Step 2
- `"status": "fail"` → **stop**. Display `remediation`, fix, re-run `env-check`. **Do not proceed until passed.**

> **Hard Block**: `env-check` is the only acceptable environment verification. Do NOT substitute with `which aliyun`, `pip list`, etc.

### Step 2: UID Selection

> `list-accounts` MUST be called unconditionally regardless of `credential_mode` (single/multi/none).

**Single-account mode** (`credential_mode: "single"`):
1. Call `list-accounts` (MUST for visibility and session context)
2. Auto-select the only credential, proceed to Step 3

**Multi-account mode** (`credential_mode: "multi"`):
1. Call `list-accounts` — display UID/profile/employeeId/workspace
2. User confirms selection or requests new account → onboarding → re-run `list-accounts`
3. If empty → Smart Discovery flow (only when `list-accounts` returns no registered UIDs)

#### Smart Discovery (when profile credentials exist but STAROps config missing)

1. **Select profile** from `env-check` profiles[] — user confirms selection
2. **Auto-resolve UID**: `aliyun sts get-caller-identity --profile "<selected>"` → extract `AccountId`
3. **Enumerate digital employees**: `starops_manager.py list-employees --profile "<selected>"` → parse `digitalEmployees[]`
4. **User selects** employee (`name` → `employeeId`)
5. **workspace** (optional): omit if not needed
6. **Write config**: `session_manager.py account-add --cwd "$PWD" --uid "<UID>" --employee-id "<id>" --profile "<profile>"`
7. **Re-run `env-check`** → proceed after `pass`

### Step 3: Initialize Session

```bash
python3 <skill-root>/scripts/session_manager.py init --cwd "$PWD" --uid "<selected UID>"
```

Resolves profile/employeeId/workspace from config, writes status.json. Record returned `session` ID and `sre_dir` path.

> **Hard Block**: Session IDs MUST come from `init`. Never use `openssl rand`/`uuidgen`/`date`/hardcoded values. Pre-init ID generation is strictly prohibited — any `--user-agent` with a pre-init ID is a workflow violation.

### Step 4: STAROps Capability Discovery

Query digital employee capabilities when STAROps is configured.

**1. Check cache** (key = `uid|employeeId|workspace`, TTL=86400s):
```bash
python3 <skill-root>/scripts/session_manager.py starops-cap-cache-get \
  --uid "<uid>" --employee-id "<employeeId>" [--workspace "<ws>"] --cwd "$PWD"
```
- Hit + not expired → use cached `capabilities_text`, proceed to Step 5
- Miss or expired → step 2

**2. Query capabilities** (only on cache miss):
1. Create thread via `starops_manager.py create-thread` (idempotencyKey per [references/starops-api.md](references/starops-api.md))
2. **Persist threadId immediately**: `session_manager.py update --session "<id>" --cwd "$PWD" --status "<status>" --thread-id "<threadId>"`
3. Send capability query:
   ```bash
   python3 <skill-root>/scripts/starops_manager.py chat "<thread-id>" "Please list all your currently available diagnostic skills" --config "<config.json>" --uid "<uid>" --stream
   ```
4. Extract capability list from stdout
5. Write to cache:
   ```bash
   echo "<capabilities_text>" | python3 <skill-root>/scripts/session_manager.py starops-cap-cache-set \
     --uid "<uid>" --employee-id "<employeeId>" [--workspace "<ws>"] \
     --capabilities-text-stdin --skills-count <N> --skills-list '<JSON_ARRAY>' --cwd "$PWD"
   ```

> **Streaming**: Add `--stream` for real-time thinking (stderr). Add `--json` for `{thinking, answer}`. Agent runtimes should use background execution + polling (3-5s intervals via `GetTerminalOutput`). Frameworks can import `stream_chat()` with `on_event` callback.

If STAROps completely unavailable (network error, not permission error) → mark `Available: false`, skip. Permission errors (401/403) → follow Permission Failure Handling.

### Step 5: Scenario Routing and Triage

Determine scenario (see table above). Collect context → identify affected resources → list symptoms → form hypothesis. Generate `triage-summary.md`.

```bash
python3 <skill-root>/scripts/session_manager.py update \
  --session "<session-id>" --cwd "$PWD" --status "triaged"
```

### Step 6: Diagnose

Delegates diagnostic tasks to STAROps via prompts — does not directly call cloud product APIs.

**1. Send diagnostic task to STAROps**:
1. **Reuse Thread (MUST)**: Check `status.json` for existing `threadId` before creating new one. Reuse if present.
2. **Build and send prompt**:
   ```bash
   python3 <skill-root>/scripts/starops_manager.py chat "<thread-id>" "<diagnostic prompt>" --config "<config.json>" --uid "<uid>" --stream
   ```
   Include: objective, scope (cluster/Region/time/resources), focus dimensions, expected output format.
3. **Follow-up queries**: Reuse same `threadId` and `--uid`.

**2. STAROps retry protocol** (MUST exhaust before CLI fallback):

| Failure Type | Action |
|-------------|--------|
| SSE timeout (>120s) / empty response / "exited with no output" | Wait 30s, retry same threadId (max 2 retries). Do NOT create new threadId. |
| HTTP 409 Conflict | Create new threadId, retry `chat` (max 2 retries) |
| HTTP 401/403 | Follow Permission Failure Handling. Never fall back to CLI. |
| HTTP 500/502/503 | Wait 30s, retry same threadId (max 2 retries) |
| Connection Refused / TCP Timeout | Retry once after 30s. If still fails → CLI fallback |

**Retry procedure** (strict order):
1. Wait 30s → retry `chat` with same threadId
2. If fails with non-empty error → create new threadId → retry once
3. If step 2 fails with network error → CLI fallback
4. If step 2 fails with SSE/HTTP error → do NOT fallback, repeat from step 1 (max 2 full cycles)

> **Hard Block**: SSE timeout, HTTP 409/5xx are NOT "unavailable". Falling back to CLI without exhausting retries is a workflow violation.

**3. CLI fallback** (only after STAROps verified unavailable):
- `env-check`, `list-accounts`, `init` MUST already be executed
- Status MUST be `triaged` before CLI calls
- All CLI calls MUST be read-only queries (`Describe*`/`List*`/`Get*` only) with `--user-agent`. ANY write operation (`Create*`/`Delete*`/`Modify*`/`Add*`/`Set*`/`Update*`/`Stop*`/`Restart*`/`PUT`/`POST`) is a ZERO-TOLERANCE violation — output remediation as text only
- Report file MUST still be generated

**4. Record results**: Write to `.aliyun-sre/<session>/observations/` (step/tool/expected/actual/hypothesis_match/key_findings/unanswered_questions).

### Step 7: Solution Generation (incident-response only)

> Every remediation step MUST include `Safety: "requires manual user execution"`.

Generate `plan/solution.md`: Basic Information table, Technical Design (mermaid diagrams, impact/observation/loss-stop plans), Remediation Steps (reasoning/purpose/safety/command/expected result/verification), Verification Plan, Emergency Plan (rollback), Success Criteria.

```bash
python3 <skill-root>/scripts/session_manager.py update \
  --session "<session-id>" --cwd "$PWD" --status "planned"
```

### Step 8: Solution Self-Validation

Check: security compliance (read-only/manual), coverage completeness (every symptom has diagnostic result), solution quality (diagrams, plans, actionable verification). Auto-correct max 1 iteration.

```bash
python3 <skill-root>/scripts/session_manager.py update \
  --session "<session-id>" --cwd "$PWD" --status "validated"
```

### Step 9: Report Output

Written to `.aliyun-sre/<session>/` (bound to one UID):
- `diagnostic-report.md` (incident-response): problem overview, diagnostic process, root cause, solution
- `inspection-report.md` (inspection-governance): scope, results table, findings, summary

> **Pre-output Checklist**: 1) Report file exists, 2) All remediation steps have "requires manual user execution", 3) Status advanced via `update --status`, 4) Scan all report content for unmasked credentials (AK/SK, tokens, secrets); if found, replace with `[REDACTED]` before finalizing. Fix any failures BEFORE outputting.

### Step 10: Complete

```bash
python3 <skill-root>/scripts/session_manager.py update \
  --session "<session-id>" --cwd "$PWD" --status "executed"
```

Output: report path, solution path, key findings, follow-up recommendations.

> Session MUST reach `executed` status. `triaged` = report skipped; `planned` = self-validation skipped.

### Session State Machine

```
pending → triaged → planned → validated → executed
```

`inspection-governance` skips `planned`/`validated` (triaged → executed directly). See [references/session-management.md](references/session-management.md).

## Success Verification

Confirm by scenario: report generated, state machine at `executed`, conclusions based on actual data. See [references/verification-method.md](references/verification-method.md).

## Cleanup

```bash
python3 <skill-root>/scripts/session_manager.py cleanup --cwd "$PWD"
```

Remove expired sessions (TTL=300s default).

## Best Practices

1. **Diagnostic workflow is fully read-only**: `aliyun` CLI is restricted to `Describe*`/`List*`/`Get*` queries ONLY. Write operations (`Create*`/`Delete*`/`Modify*`/`Add*`/`Set*`/`Update*`/`Stop*`/`Restart*`/`PUT`/`POST` to cloud endpoints) are NEVER executed — remediation is output as text marked "requires manual user execution". Onboarding has user-triggered write actions (`CreateDigitalEmployee`/`DeleteDigitalEmployee`) via `starops_manager.py` only.
2. **STAROps primary**: Delegate via `create-thread` + `chat`. CLI fallback only when completely unavailable (network error). Permission errors → Permission Failure Handling.
3. **Thread reuse**: Follow-up queries reuse same thread within a session.
4. **Single session, single UID**: One UID → one profile → one digital employee per session.
5. **Credential source matches profile**: All API calls use the profile bound to session UID.
6. **Profile management is explicit**: Diagnostic workflow is read-only; profile changes are user-triggered.

## References

| Reference | Description |
|-----------|-------------|
| references/starops-config.md | STAROps configuration and Profile management |
| references/session-management.md | Session lifecycle management |
| references/starops-api.md | STAROps API specification |
| references/cli-installation-guide.md | Aliyun CLI installation guide |
| references/ram-policies.md | RAM permission list |
| references/related-commands.md | Command quick reference |
| references/acceptance-criteria.md | Acceptance criteria |
| references/verification-method.md | Verification method |
| references/initialization-guide.md | Initialization guide (Onboarding) |
