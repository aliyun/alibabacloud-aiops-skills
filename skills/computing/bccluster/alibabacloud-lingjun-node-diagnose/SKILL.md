---
name: alibabacloud-lingjun-node-diagnose
description: |
  bash prefix: export LJ_SKILL_DIR="${LJ_SKILL_DIR:-$HOME/.qoder/skills/alibabacloud-lingjun-node-diagnose}" && source "$LJ_SKILL_DIR/lib/lj_init.sh"
  i18n: detect language each turn (CJK ratio ≥ 0.30 → LJ_LANG=zh, else en); inject LJ_LANG=zh|en prefix before source.
  Intelligent diagnosis for Alibaba Cloud Lingjun (regular & hyper) compute nodes: submit diagnostic tasks (BasicCheck / NodeHardwareCheck / CheckByAiJobLogs), produce structured diagnostic reports, propose repair plans (reboot / reimage / stop / report-node-status), track fault reports (list-fault-reports / describe-fault-report / stop-node-diagnostic). Read-only: list-clusters / list-cluster-nodes / list-cluster-hyper-nodes / describe-node / describe-hyper-node / list-syslogs / list-diagnostic-results.
  Triggers: "lingjun diagnose", "灵骏诊断", "灵骏排障", "GPU 故障", "硬件故障", "节点异常", "诊断节点", "重启节点", "重装节点", "灵骏修复", "报障", "终止报障", "syslog", "NodeHardwareCheck", "CheckByAiJobLogs", "BasicCheck", "fault report", "stop fault diagnosis"
---

# Alibaba Cloud Lingjun Node Diagnose & Repair

## Scenario Description

Alibaba Cloud Lingjun runs AI workloads on rack-level GPU bare-metal nodes. Failures (GPU/HBM ECC, NIC link flap, NCCL hang, kernel panic, RDMA degradation, AI-job log anomalies) require a closed-loop "diagnose → report → repair" workflow. This skill covers exactly that closed loop using the **eflo-controller (v2022-12-15)** OpenAPI namespace shared with the `alibabacloud-lingjun-cluster-scaling` skill — three diagnostic CLIs + four repair CLIs + three fault-report CLIs + supporting read-only helpers — across **8 features**:

1. **Resource Locator** — `list-clusters` / `describe-cluster` / `list-cluster-nodes` / `list-cluster-hyper-nodes` / `describe-node` / `describe-hyper-node` to anchor the target Cluster + (Hyper)Node before any diagnostic submission.
2. **Submit Diagnostic Task** — `create-diagnostic-task` with one of three `DiagnosticType` values (`BasicCheck` / `NodeHardwareCheck` / `CheckByAiJobLogs`) — enum re-verified server-side 2026-08-19 (`NetConfigCheck` / `NetRuntimeCheck` deprecated, never submit).
3. **Query Diagnostic Result (single)** — `describe-diagnostic-result` returns the per-node check items + verdict + remediation hints.
4. **List Diagnostic History** — `list-diagnostic-results` browses prior diagnostic tasks (paginated, optional `--diag-type` filter).
5. **Produce Diagnostic Report** — Render a Markdown report combining (1) target identity, (2) diagnostic verdict, (3) per-check-item table, (4) supporting evidence (syslog excerpts, hardware counters).
6. **Produce Repair Plan** — Map the diagnostic verdict to one of `reboot-nodes` / `reimage-nodes` / `stop-nodes` / `report-node-status` (or escalate to the cluster-scaling skill's `shrink-cluster`/`delete-node` for permanent removal); output a `safe_mutate`-compatible HITL plan.
7. **Auxiliary Telemetry** — `list-syslogs` (kernel/system log excerpts), per-node hardware counters from `describe-node` / `describe-hyper-node` to enrich the report.
8. **Fault Report Tracking** — after `report-node-status` (fault declaration), track the deep-diagnosis lifecycle via `list-fault-reports` / `describe-fault-report`, stop an in-progress fault diagnosis via `stop-node-diagnostic`, and approve a platform-raised maintenance proposal via `approve-operation` (both mutating, `safe_mutate` two-phase).

**Key Resources**: Cluster → (Node Groups) → Compute Nodes — regular `NodeId` (e.g., `e01-cn-...`) or rack-level `HyperNodeId` (e.g., `hn-cn-...`). Diagnostic tasks operate on `NodeId` or `HyperNodeId`.

**Supported Regions**: Use `safe_aliyun aliyun eflo-controller describe-regions --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou` (`describe-regions` is the discovery seed; see [endpoint-routing.md](references/endpoint-routing.md) §2 sole exception) or fall back to [supported-regions.md](references/supported-regions.md).

---

## Installation

Verify `aliyun version >= 3.3.3`; otherwise:

```bash
curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash
aliyun version
```

This skill uses **one** Alibaba Cloud OpenAPI namespace — only `eflo-controller` plugin is required:

| Plugin | CLI Namespace | Used For |
|---|---|---|
| `eflo-controller` | `aliyun eflo-controller ...` | Diagnostic submit/query/list, repair (reboot/reimage/stop/report-node-status), fault-report tracking (list/describe/stop-node-diagnostic), and all read-only locators |

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install --name eflo-controller
aliyun plugin update
```

See [cli-installation-guide.md](references/cli-installation-guide.md) for detailed instructions and verification.

---

## Authentication

Verify credentials via `aliyun configure list` only. **Never** run `aliyun configure get` / `configure show` (they print plaintext secrets) and **never** echo or display AccessKey values; mask any credential-bearing output (e.g. `aliyun configure list | sed -E 's/(LTAI[A-Za-z0-9]{4})[A-Za-z0-9]+/\1****/g'`). If missing, guide users to the [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak) outside this session.

---

## RAM Permissions

Namespace coverage: `eflo:*` (read-only diagnostic + node-state mutating). Split into 4 permission sets:

- **Read-Only Locator (8)**: `eflo:ListClusters` / `eflo:DescribeCluster` / `eflo:ListClusterNodes` / `eflo:ListClusterHyperNodes` / `eflo:DescribeNode` / `eflo:DescribeHyperNode` / `eflo:DescribeRegions` / `eflo:ListSyslogs`.
- **Diagnostic Read+Submit (3)**: `eflo:CreateDiagnosticTask` / `eflo:DescribeDiagnosticResult` / `eflo:ListDiagnosticResults`.
- **Repair Mutating (4)**: `eflo:RebootNodes` / `eflo:ReimageNodes` / `eflo:StopNodes` / `eflo:ReportNodeStatus`.
- **Fault Report Tracking (4)**: `eflo:DescribeFaultReport` / `eflo:ListFaultReports` (read-only) + `eflo:StopNodeDiagnostic` / `eflo:ApproveOperation` (mutating).

Full policies in [ram-policies.md](references/ram-policies.md); on a permission failure, consult that file first and then route to the `ram-permission-diagnose` skill.

---

## Parameter Confirmation

> 🛑 **BLOCKING GATE — Two-Phase Commit (MANDATORY)**: All mutating CLIs (`reboot-nodes` / `reimage-nodes` / `stop-nodes` / `report-node-status` / `stop-node-diagnostic`, plus `create-diagnostic-task` because it physically attaches a long-running task to the node) **must** be issued via the [`safe_mutate` two-phase flow](references/scripts.md#safe_mutate-two-phase-commit-mandatory) — **including in dry-run mode**: when the user asks for a `--cli-dry-run` validation, keep *both* phases and merely append `--cli-dry-run` to the command inside `safe_mutate`, then always run Phase 2 (`safe_mutate_confirm <hash>`) so that the flag actually reaches the CLI and the request body is echoed back. Phase 1 on its own never touches the CLI — it only writes a dump under `/tmp/lingjun-diag-mutate/` and prints a hash, which validates nothing and leaves no evidence (see §Command Quick Reference → “Dry-run mode”). Phase 1 produces a dry-run dump of all parameters + a confirmation table ending with a prompt to review the parameters and reply the language-matched confirmation word (zh session: `「确认」`; en session: "confirm"); Phase 2 only commits after the user replies **`「确认」`** (zh) / **"confirm"** (en) — the single unified confirmation word, matched to session language (the agent then invokes `safe_mutate_confirm <hash>` internally; the hash is captured silently from stdout for audit only and internal terms — hash / token / Phase 1 / Phase 2 — must **never** appear in user-facing output). Region / ClusterId / NodeId|HyperNodeId / Hostname / DiagnosticType / DiagnosisType / Description / ImageId / LoginPassword(`******`) / ReportId **must all** appear in the confirmation table; in zh sessions every parameter name in the confirmation table renders as its **pure Chinese name** per [parameter-confirmation.md §parameter-name Chinese mapping table](references/parameter-confirmation.md) — Chinese name only, **no** English original in parentheses; values never translated (sole exception: `OperatingState` values render in Chinese per [node-state-i18n.md](references/node-state-i18n.md)); derived parameters (`Endpoint` — derived from Region, shown only inside the full-CLI line) and default-valued optionals (e.g. `IgnoreFailedNodeTasks=false`) must **NOT** appear as table rows; `ImageId` / `LoginPassword` (used by `reimage-nodes`) are flagged `forbidden_inference` — the LLM is **strictly forbidden** from auto-filling values after a `MissingParameter` error or silently inheriting prior session values. Per-action schemas live in [`mutating-schemas/`](references/mutating-schemas/); full confirmation-table templates in [parameter-confirmation.md](references/parameter-confirmation.md).

---

**`forbidden_inference` Parameter Hard Rule (MANDATORY)** — In mutating-call schemas, fields flagged `forbidden_inference` (typically: `ImageId` / `Hostname` / `LoginPassword` / `Description` / `IssueCategory` / `Reason` / `ReportId`) are **strictly forbidden** from being auto-filled by the LLM from conversational context / `describe-node` responses / historical commands / other resources, or silently inherited. After a `MissingParameter` error, the Agent **must** route through HITL: invoke `list-images` for `ImageId` and explicit user picker for `Hostname` / `LoginPassword` / `Description` / `IssueCategory` / `Reason` (no default inference / context reuse / "looks reasonable" fills allowed). Any LLM auto-fill of a `forbidden_inference` field constitutes [edge-cases.md §4.5 V3](references/edge-cases.md#45-skill-self-violation-not-retryable) — **non-retryable, non-pardonable**: stop immediately, retract all auto-filled values, discard the pending parameter set, disclose to the user in the format `⚠️ Skill violation (V3): <specific facts>, <obtained results> have been discarded; restarting from the list-* HITL`, then restart from the list-* HITL. Per-action `forbidden_inference` field lists live in [`mutating-schemas/`](references/mutating-schemas/).

---

## Interaction Rules

**Interactive selection** is used to collect input (fixed options / common defaults + custom). **Sensitive Information** (passwords / AK/SK / certificates) is **strictly forbidden** to appear in plaintext in responses / commands / summaries / logs / files; always render as `******`, with the real value used only inside CLI single quotes internally.

---

## Core Workflow

> Observability: `lib/lj_init.sh` generates a session-id and exports the skill User-Agent automatically (see §Observability). No manual setup needed.

### Endpoint Routing & Region Hard Rules (MANDATORY)

> 🔗 The full text, counter-examples, and execution details of these three hard rules are consolidated in [endpoint-routing.md](references/endpoint-routing.md); the section below is only an index summary. The Agent **must** satisfy all three before issuing any `aliyun eflo-controller *` CLI.

1. **Endpoint and Region must match**: Every `aliyun eflo-controller` command must explicitly carry `--endpoint eflo-controller.<region>.aliyuncs.com`, and `<region>` must be **exactly identical** to `--region`; mismatches trigger `InvalidRegionId`.
2. **Region is required**: When the user has not explicitly specified a Region, the Agent is **strictly forbidden** to use placeholders, **strictly forbidden** to silently default to `cn-hangzhou` / `cn-wulanchabu`, and **strictly forbidden** to reuse a value left over from a previous session; the Agent must first run HITL and let the user explicitly pick a Region from the `describe-regions` list (or [supported-regions.md](references/supported-regions.md)). The sole exception: `describe-regions` itself may use `cn-hangzhou` once as a discovery-style seed.
3. **Multi-Region Enumeration intent**: When the user's intent is "global inventory / cross-region listing" (e.g., "diagnose all nodes", "list all clusters"), the Agent is **strictly forbidden** from answering after querying a single Region only, and must first run a HITL two-way pick (A. iterate all Regions and aggregate by Region / B. specify a single Region). Under choice A, a single-region failure does not interrupt the overall iteration; the final answer must explicitly note "iterated N / succeeded M / failed K", and **strictly must not** conflate "successfully iterated 0 records" with "iteration did not succeed".

### Pagination Exhaustion (MANDATORY)

> 🔗 Full rules, pseudocode, and safety-valve thresholds are in [edge-cases.md §7](references/edge-cases.md#7-pagination-exhaustion-327). All paginated `list-*` calls (`list-clusters` / `list-cluster-nodes` / `list-cluster-hyper-nodes` / `list-diagnostic-results` / `list-syslogs`) must follow pagination through to the **true last page** before answering: if the response body's `NextToken` is non-empty → automatically continue with `--next-token <previous page's raw value>` until `NextToken` is empty; `--max-results` stays at the first-page value, and `--next-token` must **never** be concatenated / truncated / re-encoded. Safety valve: per-query soft cap 50 pages / 1000 records; if the threshold is hit and a token still remains → HITL two-way choice (continue paging / answer with cumulative results and explicitly note "not exhausted"); silent truncation is forbidden.

### Pre-Execution Self-Check (MANDATORY)

> **Session-scoped one-time hard rule** — on par with the `safe_aliyun` wrapper and the `safe_mutate` two-phase commit; issuing any CLI before this self-check passes is treated as a **severe Skill violation**, handled per [edge-cases.md §4.5](references/edge-cases.md#45-skill-self-violation-not-retryable).

1. **Before** the first invocation of any `aliyun ...` (including read-only, `xargs -P` / `&` parallel, `describe-diagnostic-result` polling, dry-run probes) **in the session**, the Agent must execute:
   ```bash
   export LJ_SKILL_DIR="${LJ_SKILL_DIR:-$HOME/.qoder/skills/alibabacloud-lingjun-node-diagnose}"
   source "$LJ_SKILL_DIR/lib/lj_init.sh"
   type safe_aliyun >/dev/null 2>&1 || { echo "❌ safe_aliyun not loaded; refusing to issue any CLI"; exit 2; }
   ```
   **Any** CLI invocation made before the `type` self-check passes is treated as **fabricated execution** — even if it returns real JSON, the result **must be discarded and the call re-run**, and **must not** be incorporated into user output / completion reports / `pending-tasks.json`.
2. **No exemption for parallel calls**: **Each** subcommand issued via batch `xargs -P` / `&` background / multiple Bash tools in parallel must still go through the `safe_aliyun` wrapper; raw `aliyun ...` calls are **forbidden** "for parallel-query efficiency".
3. **Bare invocation = violation (V1)**: A discovered raw `aliyun *` invocation constitutes [edge-cases.md §4.5 V1 Skill self-violation](references/edge-cases.md#45-skill-self-violation-not-retryable) — **non-retryable, non-pardonable**: stop immediately, discard any obtained response, disclose to the user in the format `⚠️ Skill violation (V1): <specific facts>, <obtained results> have been discarded; restarting from the Pre-Execution Self-Check`, and restart the self-check.

### Transient Failure Retry (MANDATORY)

> 🔗 Full whitelist / blacklist / backoff algorithm / `safe_aliyun` skeleton are in [edge-cases.md §4 + Appendix B](references/edge-cases.md#4-exception-classification--retry-324); this section is an index summary, with the single source of truth in edge-cases.md.

**Every** CLI executed by this Skill (`aliyun eflo-controller *`, including read-only, submit, and `describe-diagnostic-result` polling) **must** be issued uniformly as `safe_aliyun aliyun ...`; raw invocation is **strictly forbidden** (self-check rules in the previous section).

- **Whitelist (silent retry, up to 3 times)**: Network-layer failures (connection refused / timeout / TLS / DNS / EOF), HTTP 5xx (502/503/504), transient API codes (`ServiceUnavailable` / `InternalError` / `RequestTimeout` / `SystemBusy`) → exponential backoff `2s/4s/8s + jitter`; throttling (`Throttling*` / HTTP 429) → fixed 60s wait.
- **Blacklist (fail immediately, no retry)**: Authentication (`InvalidAccessKeyId` / `SignatureDoesNotMatch`), authorization (`NoPermission` / `Forbidden` / 403), business 4xx (`InvalidParameter` / `NotFound` / `DiagnosticNotFound` / `OperationConflict` / `NodeNotInCluster`).
- **Silent-retry log**: Each retry prints one line `retry #N after <err> sleeping <s>s` to the Agent's own execution log; on 3 full failures → must emit a unified failure report per [Edge Cases §6](references/edge-cases.md), and **must not** fabricate a successful return.

---

## Authenticity & Anti-Fabrication Constraints (NON-NEGOTIABLE)

> **Hard red line**, taking precedence over all Feature flows and output formats; any conflict is treated as a **severe Skill violation**.

1. All diagnostic reports & repair plans **must** be strictly generated from real CLI-returned JSON. Critical fields like `DiagnosticId` / `RequestId` / `NodeId` / `HyperNodeId` / `ReportId` / `ServiceName` / `CheckItem` / `Status` / `ErrorCode` / `ErrorMessage` must come from real API response bodies and **must not** be stitched together, guessed, or reused from historical context.
2. When a core API (`CreateDiagnosticTask` / `DescribeDiagnosticResult` / `RebootNodes` / `ReimageNodes` / `StopNodes` / `ReportNodeStatus` / `StopNodeDiagnostic`) was not successfully called or returned failure, the report **must** mark "not executed" or "execution failed" and emit a complete failure analysis per [Edge Cases §6](references/edge-cases.md).
3. **Strictly forbidden**: using mocks / placeholders to impersonate real return values; hard-coding `DiagnosticId`/`RequestId`/`NodeId`; fabricating diagnostic check-item states / repair-plan progress / verdict transitions; producing "polling logs / progress bars / monitoring scripts / timestamps" that lack real API backing; claiming "node restored" / "diagnostic passed" without a valid response.

**Execution-state annotation**: Each report must be tagged with one of: ✅ **Executed successfully** (CLI 2xx + key-field verification passed → `RequestId` + `DiagnosticId` + verdict summary) / ⏳ **Submitted, pending poll** (valid `DiagnosticId` obtained but verdict still `Running`/`InProgress` → `DiagnosticId` + current state + next-poll plan) / ❌ **Execution failed** (CLI 4xx/5xx or core fields missing → strict Edge Cases §6 output) / ⏸ **Not executed** (user cancelled / preconditions unmet / HITL not passed → explicitly state "no diagnostic / repair API was called; cloud resources are unchanged"). If the current session executed no real APIs, the response **must** explicitly state "no cloud-side changes were made in this session", and must not stitch together a fake success report for "conversational continuity".

---

## Command Quick Reference (one page — self-sufficient)

> **This table alone is enough to issue every command in this Skill.** Open a file under [`references/`](references/) only for deep dives that the table explicitly points to (per-field elicitation phrasing, error-code handling, confirmation-box templates) — never to look up a sub-command name or its required params.

**Universal shape** — every call carries a matched endpoint/region pair and goes through the wrapper:

```bash
# read-only  (R)
safe_aliyun aliyun eflo-controller <sub> --endpoint eflo-controller.<region>.aliyuncs.com --region <region> <params>
# mutating   (W) — safe_mutate two-phase HITL: Phase 1 dumps the params to /tmp and prints a 12-char hash,
#                  Phase 2 (safe_mutate_confirm <hash>) commits after the user replies 「确认」
safe_mutate <sub> aliyun eflo-controller <sub> --endpoint eflo-controller.<region>.aliyuncs.com --region <region> <params>
# mutating, dry-run (W) — the user asked to validate only: SAME two phases, just append --cli-dry-run.
#                  Phase 1 echoes the 12-char hash; Phase 2 replays the identical argument vector
#                  (--cli-dry-run included) and is what actually prints the request body.
safe_mutate <sub> aliyun eflo-controller <sub> --endpoint eflo-controller.<region>.aliyuncs.com --region <region> <params> --cli-dry-run
```

The `<region>` inside `--endpoint` must be **byte-identical** to `--region`. Sub-commands, required params and hard rules:

| # | Sub-command | R/W | Required params (besides `--endpoint` / `--region`) | Optional | Hard rules (violations are non-retryable) |
|---|---|---|---|---|---|
| 1 | `describe-regions` | R | — | — | Discovery seed; the **sole** command allowed to use `cn-hangzhou` once without a user-specified Region |
| 2 | `list-clusters` | R | — | `--max-results` `--next-token` | Paginate `--next-token` to the true last page |
| 3 | `describe-cluster` | R | `--cluster-id` | — | — |
| 4 | `list-cluster-nodes` | R | `--cluster-id` | `--max-results` `--next-token` | Paginate to exhaustion |
| 5 | `list-cluster-hyper-nodes` | R | `--cluster-id` | `--max-results` `--next-token` | Not registered on every Region gateway (e.g. `me-east-1` returns 400 `InvalidParameter … ACTION_MODDULE_MAP ListClusterHyperNodes is not found`) → report the real error code + `RequestId` as measured; never switch to another sub-command, never retry other Regions, never fabricate a `HyperNodeId` |
| 6 | `describe-node` | R | `--node-id` | — | Yields `OperatingState` / `Hostname` / `MachineType` / `Disks[]` / `NetworkCards[]`; mandatory pre-check before any repair and the source of `approve-operation` pending states |
| 7 | `describe-hyper-node` | R | `--hyper-node-id` | — | Rack-level counterpart of #6 |
| 8 | `list-images` | R | — | `--max-results` `--next-token` | The **only** legitimate source of `ImageId` for `reimage-nodes` (`forbidden_inference`) |
| 9 | `create-diagnostic-task` | W | `--cluster-id` `--diagnostic-type`, plus `--node-ids` and/or `--ai-job-log-info` | — | `--diagnostic-type` ∈ `BasicCheck` \| `NodeHardwareCheck` \| `CheckByAiJobLogs` (`NetConfigCheck` / `NetRuntimeCheck` deprecated 2026-08-19, never submit); `--node-ids` is **space-separated** (`--node-ids n1 n2` — an array literal gets word-split and fails with "These nodes do not exist"); `--ai-job-log-info` mandatory only for `CheckByAiJobLogs` |
| 10 | `describe-diagnostic-result` | R | `--diagnostic-id` | — | Polling; `DiagnosticId` must come from a real submit response, never guessed |
| 11 | `list-diagnostic-results` | R | `--diag-type` | `--max-results` (≤100) `--next-token` `--resource-group-id` | **Enum split**: this read endpoint accepts only the legacy `NetDiag` \| `ServerDiag` \| `BasicCheck` (the new enum fails with `Invalid parameter DiagType`); iterate all three and merge to browse full history |
| 12 | `list-syslogs` | R | `--node-id` `--from-time` `--to-time` | `--query` `--reverse` `--next-token` | `--from-time` / `--to-time` are **epoch-second integers** (ISO8601 fails validation — convert first); `--query` uses SLS syntax with `OR` (`'error OR fail OR panic'`; pipe-separated fails); both bounds explicit, never silently default to "the last hour"; window > 24h → HITL warning |
| 13 | `reboot-nodes` | W | `--cluster-id` `--nodes` | `--ignore-failed-node-tasks` | `--nodes` is a space-separated list; reversible |
| 14 | `reimage-nodes` | W | `--cluster-id` `--nodes` (structured) | `--user-data` `--ignore-failed-node-tasks` | `--nodes` is a **structured list**: `Hostname=<h> ImageId=<i> LoginPassword='<pw>' NodeId=<n>` (plain `NodeId` form is rejected); `Hostname` / `ImageId` / `LoginPassword` are all `forbidden_inference` → HITL + `list-images`; ⚠ wipes the system disk |
| 15 | `stop-nodes` | W | `--nodes` | `--ignore-failed-node-tasks` | ⚠ **Takes NO `--cluster-id`** — adding it "for consistency" triggers `unknown flag` (V6 default-value hallucination) |
| 16 | `report-node-status` | W | `--node-id` (single) `--diagnosis-type` `--description` | — | `--diagnosis-type` accepts **only** `COMPREHENSIVE` (`QUICK` → 400 "Only COMPREHENSIVE diagnosis type is supported"); `--description` is the user's own fault wording verbatim (`forbidden_inference`); node must be `OperatingState=Using`; success returns `ReportId` + `RequestId`; legacy `report-nodes-status` is deprecated — do not use it |
| 17 | `list-fault-reports` | R | — | `--nodes` `--status` `--max-results` `--next-token` | `--status` ∈ `Processing` \| `DiagnosisTerminating` \| `DiagnosisTerminated` \| `DiagnosisPassed` \| `FaultConfirmed` \| `FaultFinish`; paginate to exhaustion |
| 18 | `describe-fault-report` | R | `--report-id` | — | `ReportId` must come from a same-session `list-fault-reports` response or the user's explicit input (`forbidden_inference`) |
| 19 | `stop-node-diagnostic` | W | `--report-id` | — | Prove stoppable first via `describe-fault-report` (`Status` ∈ `Processing` \| `DiagnosisTerminating`); the deep diagnosis stops **and cannot be resumed**; post-commit re-check shows `DiagnosisTerminating` / `DiagnosisTerminated` |
| 20 | `approve-operation` | W | `--node-id` `--operation-type` | — | Closed enum `RepairMachine` \| `RebootMachine` \| `UpgradeMachine` (`TerminateWindow` is internal-only, forbidden here); must match the measured pending state from `describe-node`: `RepairMachine` ← `ClusterNodeRepairPendingApproval`, `RebootMachine` ← `ClusterNodeRebootPendingApproval`, `UpgradeMachine` ← `ClusterNodeUpgradePendingApproval` |

**`--ai-job-log-info` JSON shape** (only for `DiagnosticType=CheckByAiJobLogs`; passed as one single-quoted JSON string; `StartTime` / `EndTime` are ISO8601 **with timezone**; every field is `forbidden_inference` — collect via HITL, never auto-fill):

```bash
--ai-job-log-info '{"StartTime":"2026-05-16T08:00:00+0800","EndTime":"2026-05-16T09:00:00+0800","AiJobLogs":[{"NodeId":"<nid>","AiInstance":"job-worker-0","Logs":["NCCL WARN Call to connect returned Connection timed out"]}]}'
```

**Every mutating command (W) additionally requires** the prominent warning box + `参数确认表` / "parameter confirmation table" and a fresh user reply of the language-matched confirmation word before Phase 2 — see §Parameter Confirmation and Feature 6.

**Dry-run mode — the user explicitly asked for a `--cli-dry-run` validation**: the warning box + `参数确认表` **and both phases** stay mandatory; simply append `--cli-dry-run` to the command inside `safe_mutate`. Phase 1 never reaches the CLI — it only writes a base64 dump under `/tmp/lingjun-diag-mutate/` and echoes a 12-char hash — so the agent **must** immediately follow it with Phase 2 `safe_mutate_confirm <hash>`, which replays that identical argument vector (`--cli-dry-run` included) through `safe_aliyun` and therefore prints, on stdout, `DRY-RUN MODE: Request Details (No actual API call)`, `API Action: <PascalCase>`, the `Body:` payload and `Request NOT sent (dry-run mode)`, with exit code 0. **Stopping after Phase 1 validates nothing and leaves no evidence to judge by.** Because `--cli-dry-run` guarantees the request is *not* submitted, Phase 2 is safe to run as soon as the confirmation table has been shown. Verified on aliyun CLI 3.3.10.

---

## Features

> 📎 OpenAPI required / optional parameter inventories, default values, and prompt phrasing are consolidated in [api-parameters.md](references/api-parameters.md). Each Feature below lists only the highlights; per-field elicitation is performed by the Agent at runtime following api-parameters.md.

### Feature 1: Resource Locator (Read-Only)

Anchor the diagnostic target before any submission. Six read-only operations:

```bash
aliyun eflo-controller list-clusters             --endpoint eflo-controller.<region>.aliyuncs.com --region <region>
aliyun eflo-controller describe-cluster          --endpoint eflo-controller.<region>.aliyuncs.com --region <region> --cluster-id <cid>
aliyun eflo-controller list-cluster-nodes        --endpoint eflo-controller.<region>.aliyuncs.com --region <region> --cluster-id <cid>
aliyun eflo-controller list-cluster-hyper-nodes  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> --cluster-id <cid>
aliyun eflo-controller describe-node             --endpoint eflo-controller.<region>.aliyuncs.com --region <region> --node-id <nid>
aliyun eflo-controller describe-hyper-node       --endpoint eflo-controller.<region>.aliyuncs.com --region <region> --hyper-node-id <hnid>
```

**Picker hard rule (MANDATORY)**: When the user provides only a partial identifier (e.g., "the GPU node that hung last night", "node-007"), the Agent **must** walk through HITL:
1. Confirm Region.
2. Run `list-clusters` and let the user pick.
3. Run `list-cluster-nodes` + `list-cluster-hyper-nodes` (paginated to exhaustion) and present a numbered table with `NodeId|HyperNodeId` + `Hostname` + `MachineType` + `OperatingState`. In zh sessions the `OperatingState` column values render in Chinese per [node-state-i18n.md](references/node-state-i18n.md).
4. Auto-select is **forbidden**; the user must explicitly pick.

`describe-node` / `describe-hyper-node` returns include `OperatingState`, `Disks[]`, `NetworkCards[]`, `MachineType`, etc., used as supporting evidence for the diagnostic report. 📖 [diagnose-operations.md #f1](references/diagnose-operations.md) · [api-parameters.md #1-#6](references/api-parameters.md).

---

### Feature 2: Submit Diagnostic Task (Async)

Submit a diagnostic task on one or more nodes / hyper nodes within a Cluster.

**Workflow (8 stages)**: ① locate Cluster + target Nodes (Feature 1) → ② confirm `DiagnosticType` (three-way pick) → ③ for `CheckByAiJobLogs`, additionally collect `AiJobLogInfo` JSON via HITL → ④ HITL summary + `safe_mutate` Phase 1 dump → ⑤ user replies `「确认」` (zh) / "confirm" (en) → ⑥ submit `create-diagnostic-task` → ⑦ **MANDATORY submission receipt echo** (see below) → ⑧ enter Feature 3 polling.

**Submission receipt (MANDATORY, before ANY polling; V7 violation if skipped)**: right after Phase 2 returns, the agent MUST echo this block to the user verbatim-style — polling must never start silently:

```
✅ Diagnostic task submitted
  DiagnosticId : <did>
  RequestId    : <reqid>
  Region / Type: <region> / <DiagnosticType>
  Nodes        : <NodeId list>
  Polling      : Foreground burst rounds — one round every 10s, progress line relayed in the reply body (all three DiagnosticType)  |  Background + resume_command (only if user explicitly opts out of waiting)
```

**Required (CLI truth)**: `--region` + `--cluster-id` + `--diagnostic-type` + at least one of `--node-ids` / `--ai-job-log-info`. **`--node-ids` two-layer format (2026-08-19 probe-verified)**: OpenAPI layer `NodeIds` is a string array (official example `["mock-sn-200101"]`); the aliyun CLI encodes that array as space-separated `--node-ids value1 value2 value3` — passing the array literal verbatim (JSON or Python style) word-splits / bracket-corrupts the IDs and makes even real nodes fail with "These nodes do not exist".

**`DiagnosticType` three-way guided pick (MANDATORY; enum re-verified server-side 2026-08-19; `NetConfigCheck`/`NetRuntimeCheck` deprecated)** — Never ask the user for a raw enum; present a three-way picker:

| User-facing | DiagnosticType | Scope | Required Inputs |
|---|---|---|---|
| 1. Server basic health diagnosis | `BasicCheck` | Per-node OS/driver/runtime | `--node-ids` |
| 2. Hardware sanity check | `NodeHardwareCheck` | Per-node hardware (GPU/HBM/NIC/disk) | `--node-ids` |
| 3. AI job log analysis | `CheckByAiJobLogs` | Multi-node, log-driven | `--ai-job-log-info` (JSON), `--node-ids` |

Picking `3. CheckByAiJobLogs` triggers a sub-flow that collects `AiJobLogs[].{NodeId,AiInstance,Logs[]}` + `StartTime` + `EndTime` (ISO8601 with timezone, e.g., `2026-05-16T08:00:00+0800`). Auto-filling any of these is forbidden — they all carry `forbidden_inference` semantics.

**Optional**: None at the CLI top level. `--ai-job-log-info` is required only when `DiagnosticType=CheckByAiJobLogs`; for other types, omit it.

**HyperNode handling**: `--node-ids` accepts both regular `NodeId` (e.g., `e01-cn-...`) and rack-level `HyperNodeId` (e.g., `hn-cn-...`); the API treats them uniformly. When the user picks a hyper node, the Agent **must** display this fact in the confirmation table (column "Resource Type: HyperNode (rack-level)") so the user understands the diagnostic spans all sub-nodes.

```bash
aliyun eflo-controller create-diagnostic-task --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --cluster-id <cid> --diagnostic-type <BasicCheck|NodeHardwareCheck|CheckByAiJobLogs> \
  --node-ids <NodeId1> <NodeId2>
```

📖 [diagnose-operations.md #f2](references/diagnose-operations.md) · [api-parameters.md #7](references/api-parameters.md) · [mutating-schemas/create-diagnostic-task.yaml](references/mutating-schemas/create-diagnostic-task.yaml).

---

### Feature 3: Query Diagnostic Result (Polling)

Poll a single diagnostic task to terminal state and produce the structured report.

**Required** (`describe-diagnostic-result`): `--region`, `--diagnostic-id`. **No optional parameters.**

**Polling rule (MANDATORY)**: After `create-diagnostic-task` returns a non-empty `DiagnosticId` (response field is `DiagId` per 2026-08-16 real-response calibration), poll until the response body's diagnostic-state field reaches a terminal state (terminal verdicts observed: `Finished`/`Failed` in `Status`, verdict in `DiagResult` — the Agent **must not** hard-code one specific terminal string, instead checking "state ∉ {InProgress, Running, Pending, Diagnosing}"). **Progress-report rule (MANDATORY, all three DiagnosticType, aligned with node-ops)**: foreground polling runs in **10s rounds, each round an independent Bash call** (`sleep 10 && poll_diagnostic_burst <region> <did> 10 10 <t0>`); each round emits one progress line (`⏳ [HH:MM:SS] poll #N — diagnostic <did> state=<state> elapsed <elapsed>`, localized per session language) which the Agent **must** relay verbatim in the reply body so the user sees live progress in the frontend. **Strictly forbidden**: packing the polling loop into one long-running blocking command (e.g. `poll_diagnostic` to terminal state, `for i in $(seq ...)`) in an interactive session — the frontend then shows zero progress for the whole task; blocking `poll_diagnostic` is test/non-interactive only. **Hard cap**: 30min for `BasicCheck`, 60min for `NodeHardwareCheck` / `CheckByAiJobLogs`; foreground rounds cap at 20min then HITL (continue / stop with self-check command). On exceeding the hard cap → stop polling and offer "continue waiting / re-submit / file a ticket" three-way choice (no silent continuation).

**TaskId/DiagnosticId Strict Validation (MANDATORY, before polling)**: HTTP 2xx + non-empty `DiagnosticId` → enter polling; HTTP 4xx/5xx or empty `DiagnosticId` → **abort immediately** and produce classified output per [Edge Cases §4 / §6](references/edge-cases.md). It is **strictly forbidden** to call `describe-diagnostic-result` without a valid `DiagnosticId`, or to fabricate state-transition logs.

📖 [diagnose-operations.md #f3](references/diagnose-operations.md) · [api-parameters.md #8](references/api-parameters.md).

---

### Feature 4: List Diagnostic History (Read-Only)

Browse historical diagnostic tasks to compare a recurring failure pattern or pick up a previously-suspended task.

**Required** (`list-diagnostic-results`): `--region` **and `--diag-type`** (server-side enforced, verified 2026-08-16: omitting `--diag-type` returns `field required` validation error). **Enum split (server-side API migration in progress)**: this READ endpoint only accepts the legacy enum `NetDiag`/`ServerDiag`/`BasicCheck` (verified); the new enum used by `create-diagnostic-task` is rejected with `Invalid parameter DiagType<enum>`. To browse full history, iterate the three legacy values and merge results. **Optional** (one by one): `--resource-group-id`, `--max-results` (≤100, default 20), `--next-token`.

**Response field names (real-response calibrated)**: items live in `DiagnosticResults[]` with fields `DiagId` / `DiagResult` (`Success`|`Failed`) / `Status` (`Finished`|`Failed`) / `ResourceId` (singular, one row per node) / `ServerName` / `CreationTime` / `FinishedTime` / `ClusterId` / `ClusterName` / `DiagContent`.

**Pagination exhaustion** is mandatory; never stop mid-pagination. 📖 [diagnose-operations.md #f4](references/diagnose-operations.md) · [api-parameters.md #9](references/api-parameters.md).

---

### Feature 5: Produce Diagnostic Report

After Feature 3 reaches terminal verdict, render a Markdown report combining real API JSON. **No fabrication** (see Authenticity §1–§3).

**Report layout (MANDATORY 6-section template)** — full template in [diagnose-operations.md #report-template](references/diagnose-operations.md):

1. **Header** — Region, ClusterId, DiagnosticId, DiagnosticType, submit time, terminal time, total duration. All six fields **must** come from real `describe-diagnostic-result` response (or, for fields the API doesn't expose, leave as `-` and explicitly note "API response did not include").
2. **Target Identity Table** — One row per node: `NodeId|HyperNodeId` + `Hostname` + `MachineType` + `OperatingState` + `ClusterId`. Sourced from `list-cluster-nodes` / `list-cluster-hyper-nodes` / `describe-node` / `describe-hyper-node`. **Resource-listing field-source hard rule** (see below) applies.
3. **Diagnostic Verdict** — Top-level verdict (PASS / FAIL / WARNING) sourced from response body. If multiple sub-checks present, render a table of `(CheckItem, Status, ErrorCode, ErrorMessage)`.
4. **Per-Item Detail** — Failed items expanded with full `ErrorMessage`, related counters (e.g., HBM ECC count, NIC error count) read from `describe-node` / `describe-hyper-node` `Disks[]` / `NetworkCards[]` / `Hardware*` fields.
5. **Supporting Evidence** — On hardware/server failure, attach a 200-line `list-syslogs` excerpt around the failure window (`--from-time` ≈ `submit_time - 30min`, `--to-time` ≈ `terminal_time + 5min`), filtered by `--query` for `error|fail|panic|oom|nccl|nvidia|nic|ib0|rdma`.
6. **Recommended Repair Plan** — Cross-link to Feature 6 for the actionable plan.

**Field-name i18n (MANDATORY, all user-facing result displays)**: in zh sessions (`LJ_LANG=zh`), every field name and table column header in the report — and in **all** other user-facing result displays (submission receipts, poll progress, error reports) — renders as "Chinese name (OriginalParam)" per [parameter-confirmation.md §parameter-name Chinese mapping table](references/parameter-confirmation.md); field **values** (IDs / enums / timestamps) are never translated, **with one exception**: node status values (`OperatingState`) **must** be rendered in Chinese per the authoritative mapping table [node-state-i18n.md](references/node-state-i18n.md) (e.g., `Using` → `使用中 / In Use`, `ClusterNodeRepairing` → `集群节点维修中 / Cluster node repairing`; states not in the table stay English; scripts/jq comparisons still use the raw English value — translation happens only at the rendering layer). Mixing untranslated field names into a zh display is a rendering violation — regenerate the output.

**Resource-listing field-source hard rule (MANDATORY)** — Each row in §2 / §3 / §4 tables' `NodeId` / `HyperNodeId` / `Hostname` **must** be sourced field-by-field from **the current** `list-cluster-nodes` / `list-cluster-hyper-nodes` / `describe-node` / `describe-hyper-node` real response body (response field names are fixed as `NodeId` / `HyperNodeId` / `Hostname`); it is **strictly forbidden** to impersonate node identity using `MachineType` / `NodeGroupName` / `HpnZone` / `Zone` / `OperatingState` — these aggregate / dictionary / machine-type fields share the same value across **multiple nodes** and do not constitute a recognizable identity for the user; if any row is missing `NodeId|HyperNodeId` or `Hostname`, or impersonates identity using a field like `MachineType` → terminate the report immediately and emit a ⏸ Not Executed report, handled per the V5(c) field-impersonation violation (same tier: **non-retryable, non-pardonable**).

📖 [diagnose-operations.md #f5](references/diagnose-operations.md) · [verification-method.md](references/verification-method.md).

---

### Feature 6: Produce Repair Plan

Map the diagnostic verdict to a concrete repair CLI. The Agent **proposes** one of the four options below as default and **always** runs HITL — **auto-execution is strictly forbidden**, even on identical recurring failures.

**Verdict → Default Repair Mapping (MANDATORY default; user may override)**:

| Verdict / Symptom | Default Action | CLI | Reversible? |
|---|---|---|---|
| `BasicCheck` SOFT errors / kernel hang / NCCL hang | **Reboot** | `reboot-nodes` | ✅ |
| Driver/firmware/kernel severely degraded (reboot ineffective) | **Reimage** | `reimage-nodes` | ⚠️ wipes system disk |
| `NodeHardwareCheck` HARDWARE error (CPU/GPU/MEM/PSU/disk/NIC/fan/cable) | **Report hardware fault** | `report-node-status` | ✅ |
| User-explicit "shut it down" (offline maintenance) | **Stop** | `stop-nodes` | ✅ |
| Permanent removal needed (disk-corrupted hyper node, etc.) | **Escalate** | (`alibabacloud-lingjun-cluster-scaling` skill: `shrink-cluster` → `delete-node`/`delete-hyper-node`) | ❌ irreversible |

**Repair CLI parameters (CLI truth, verified on aliyun 3.3.10)**:

```bash
# Reboot — required: --cluster-id + --nodes (list)
aliyun eflo-controller reboot-nodes --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --cluster-id <cid> --nodes <NodeId1> <NodeId2> [--ignore-failed-node-tasks false]

# Reimage — required: --cluster-id + --nodes (structured list with Hostname/ImageId/LoginPassword/NodeId)
aliyun eflo-controller reimage-nodes --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --cluster-id <cid> \
  --nodes Hostname=<h1> ImageId=<imgid> LoginPassword='<pw>' NodeId=<nid1> \
          Hostname=<h2> ImageId=<imgid> LoginPassword='<pw>' NodeId=<nid2> \
  [--user-data <base64>] [--ignore-failed-node-tasks false]

# Stop — required: --nodes (list); ⚠ NO --cluster-id
aliyun eflo-controller stop-nodes --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --nodes <NodeId1> <NodeId2> [--ignore-failed-node-tasks false]

# Report-node-status — required: --node-id (single) + --diagnosis-type + --description
#   (every hard rule — COMPREHENSIVE-only, Using-state precondition, ReportId+RequestId on
#   success, the deprecated legacy report-nodes-status alias — is spelled out below this block)
aliyun eflo-controller report-node-status --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId> --diagnosis-type COMPREHENSIVE \
  --description '<user-provided fault description>'
```

**`stop-nodes` cluster-id absence hard rule (MANDATORY)**: Unlike `reboot-nodes` / `reimage-nodes`, `stop-nodes` does **not** accept `--cluster-id` (verified by `aliyun eflo-controller stop-nodes --help` on 3.3.10). The Agent **must not** add a `--cluster-id` flag for `stop-nodes` "for consistency"; doing so triggers `unknown flag` and is treated as [edge-cases.md §4.5 V6 default-value hallucination](references/edge-cases.md#45-skill-self-violation-not-retryable) — non-retryable, non-pardonable.

**`reimage-nodes` `--nodes` structured-list hard rule (MANDATORY)**: `--nodes` for `reimage-nodes` is **structured list**, not a string list. CLI format: `--nodes Hostname=<h> ImageId=<i> LoginPassword=<p> NodeId=<n>` per item, multiple items separated by another `--nodes` block (per `aliyun eflo-controller reimage-nodes --help` example). Passing only `NodeId` (string-list form like `reboot-nodes`) is rejected by the CLI. `Hostname` / `ImageId` / `LoginPassword` are **all** flagged `forbidden_inference` — must be collected via HITL with `list-images` / explicit user typing.

**`report-node-status` parameter hard rules (MANDATORY)**: `--node-id` takes a **single NodeId** (not a list); `--diagnosis-type` currently accepts **only `COMPREHENSIVE`** — `QUICK` is a reserved enum but the current implementation rejects it with 400 "Only COMPREHENSIVE diagnosis type is supported"; `--description` is `forbidden_inference` — it must be the user's own fault description verbatim. Preconditions: the node's state must be `Using`; daily quota (default 10% of account machines) applies; a duplicate report for the same account+node is rejected. The legacy PAI-only `report-nodes-status` (`--nodes` / `--reason` / `--issue-category` / `--start-time`) is deprecated and **must no longer be used**.

**Strong-confirmation hard rule (MANDATORY)** — Before submitting **any** of `reboot-nodes` / `reimage-nodes` / `stop-nodes` / `report-node-status`, in addition to `safe_mutate` Phase 1 dump, the Agent **must** display the "prominent repair warning box" per [parameter-confirmation.md](references/parameter-confirmation.md) showing:
- Full resource list (`ClusterId` + `NodeId|HyperNodeId` + `Hostname` + `MachineType`)
- Action (`Reboot`/`Reimage`/`Stop`/`ReportStatus`) and reversibility (especially flag `Reimage` as ⚠️ "wipes system disk; user data on system disk will be lost")
- Expected impact (workload interruption, billing implications)
- Require the user to reply the **language-matched confirmation word** — zh session: `「确认」`; en session: "confirm" (`yes` / `OK` / spelling variants / blank Enter / added or removed punctuation / the other language's word NOT accepted as approximate matches).

Any input that does not exactly match the session-language confirmation word (zh: `「确认」`; en: "confirm") → terminate the flow immediately and emit a ⏸ Not Executed report. Upon receiving it the agent invokes `safe_mutate_confirm <hash>` internally (the hash/TTL check is still enforced: missing or expired token → refuse). Committing Phase 2 without the user's confirmation word, or accepting an approximate reply, falls under [edge-cases.md §4.5 V5](references/edge-cases.md#45-skill-self-violation-not-retryable) — **non-retryable, non-pardonable**. The turn then **ends at the interception report**: simulating or fabricating any subsequent user reply within the same turn (e.g. self-authoring a "the user replied 「确认」" message), or issuing any Phase 1 / Phase 2 command after the report, is the same V5 violation (see V5(d)); only a genuine new user message arriving in a later turn may resume the flow.

**The original task/request text NEVER counts as confirmation (MANDATORY)**: even when the user's task statement pre-specifies every parameter and explicitly demands immediate execution (e.g., `直接帮我上报` / "just do it"), the Agent **must** still display the warning box and then **wait** for a fresh user reply of the confirmation word sent **after** the box is displayed. Treating the task statement as "confirmation intent", self-authoring the confirmation, or auto-committing Phase 2 on the user's behalf is the **same V5 violation** — there is no "pre-authorized" path.

**For `reimage-nodes` (especially destructive)**: the confirmation table **must** carry a prominent ⚠️ "system disk wiped, irreversible" warning line (with the full data-loss impact statement); the user's single confirmation word (`「确认」` / "confirm") then acknowledges that data loss. No extra typed English phrases are required.

📖 [diagnose-operations.md #f6](references/diagnose-operations.md) · [repair-plan-templates.md](references/repair-plan-templates.md) · [parameter-confirmation.md](references/parameter-confirmation.md) · [mutating-schemas/](references/mutating-schemas/).

**Post-report tracking**: after `report-node-status` commits, the platform creates the fault report (`Status=Processing`) and the node enters the fault-report deep diagnosis — track its progress or stop it via **Feature 8** (`list-fault-reports` / `describe-fault-report` / `stop-node-diagnostic`).

---

### Feature 7: Auxiliary Telemetry (Read-Only)

Enrich the diagnostic report with kernel-level evidence.

**Required** (`list-syslogs`): `--region` (global flag), `--node-id`, `--from-time`, `--to-time` (all three explicitly marked `(required)` by the CLI). **Time format (CLI truth, server-verified 2026-08-20)**: `--from-time` / `--to-time` are **epoch-second integers** — passing ISO8601 strings fails validation (`value is not a valid integer`); the Agent converts ISO→epoch before issuing. **`--query` uses SLS syntax with `OR` connectors** (pipe-separated keywords fail with `parse search query error`). **Optional**: `--reverse` (default `false`), `--next-token` (pagination).

**Time-window hard rule (MANDATORY)**: Both must be explicit; the Agent is **strictly forbidden** from defaulting to "the last hour" or any silent value. Window > 24h → HITL warning ("syslog window too wide; consider narrowing").

**Pagination exhaustion** mandatory. 📖 [diagnose-operations.md #f7](references/diagnose-operations.md) · [api-parameters.md #10](references/api-parameters.md).

---

### Feature 8: Fault Report Tracking (Read + Stop)

After `report-node-status` submits a fault declaration, the node enters a deep-diagnosis round (typically 3–5 hours: system info / environment / PCIe / CPU / memory / GPU / network performance / high-speed links / logs / local storage). Feature 8 tracks that lifecycle and can stop it.

```bash
# Historical fault report list (filter by node / status; paginate to exhaustion)
safe_aliyun aliyun eflo-controller list-fault-reports \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  [--nodes <nid1> <nid2>] [--status <Processing|DiagnosisTerminating|DiagnosisTerminated|DiagnosisPassed|FaultConfirmed|FaultFinish>] \
  [--max-results 20] [--next-token <tok>]

# Fault report detail (--report-id required)
safe_aliyun aliyun eflo-controller describe-fault-report \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --report-id <rid>

# Stop an in-progress fault diagnosis (mutating; must go through the safe_mutate two-phase flow)
safe_mutate stop-node-diagnostic aliyun eflo-controller stop-node-diagnostic \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --report-id <rid>

# Approve a platform-raised maintenance proposal (mutating; safe_mutate two-phase)
# --operation-type from the closed enum RepairMachine / RebootMachine / UpgradeMachine
safe_mutate approve-operation aliyun eflo-controller approve-operation \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId> --operation-type <RepairMachine|RebootMachine|UpgradeMachine>
```

**Fault-report state machine (CLI truth, verified 2026-08-23)**: `Processing` (deep diagnosis in progress) → one of `DiagnosisTerminating` / `DiagnosisTerminated` (user stopped) | `DiagnosisPassed` (no fault found) | `FaultConfirmed` (fault confirmed) → `FaultFinish` (fault handling completed). In zh sessions `Status` renders in Chinese via `_lj_fault_state_t` (`faultstate.*` entries in `lib/core/i18n.sh`; unknown values pass through unchanged); en sessions pass through verbatim.

**`stop-node-diagnostic` hard rules (MANDATORY)**:
- `ReportId` is `forbidden_inference` — it **must** come from a same-session `list-fault-reports` / `describe-fault-report` response or the user's explicit input; never fabricate or reuse from historical context.
- Before Phase 1, `describe-fault-report` **must** confirm the report is stoppable (`Status` ∈ {`Processing`, `DiagnosisTerminating`}); terminal states (`DiagnosisTerminated` / `DiagnosisPassed` / `FaultConfirmed` / `FaultFinish`) cannot and need not be stopped → terminate the flow and explain with the real measured Status.
- The impact statement **must** be shown verbatim in the confirmation table: the deep diagnosis stops immediately **and cannot be resumed**; the node becomes available again; diagnosing again requires a fresh fault report (`report-node-status`).
- Post-commit verification: `describe-fault-report` re-check shows `Status` ∈ {`DiagnosisTerminating`, `DiagnosisTerminated`}.

**Billing/SLA note**: reports ending in `DiagnosisTerminated` / `DiagnosisPassed` do not count toward node unavailable time; a `FaultConfirmed` report counts unavailable time from the report moment to `FaultFinish`. The Agent relays this only as informational context, never as a billing promise.

**`approve-operation` hard rules (MANDATORY)**:
- Closed enum: `--operation-type` only accepts `RepairMachine` / `RebootMachine` / `UpgradeMachine`; `TerminateWindow` is internal-only and **forbidden** through this public CLI; out-of-enum values hit the server default dispatch branch and fail confusingly.
- `OperationType` must match the measured pending state from `describe-node`: `RepairMachine` ← `ClusterNodeRepairPendingApproval`, `RebootMachine` ← `ClusterNodeRebootPendingApproval`, `UpgradeMachine` ← `ClusterNodeUpgradePendingApproval`; mismatch → terminate the flow and re-present the picker.
- `NodeId` / `OperationType` come from measured state + explicit HITL picker, never LLM invention; submission goes through the `safe_mutate` two-phase flow; post-commit verification: `describe-node` re-check shows the node leaving the `*PendingApproval` state.

📖 [fault-report-tracking.md](references/fault-report-tracking.md) · [api-parameters.md #15–#17](references/api-parameters.md) · [mutating-schemas/stop-node-diagnostic.yaml](references/mutating-schemas/stop-node-diagnostic.yaml) · [mutating-schemas/approve-operation.yaml](references/mutating-schemas/approve-operation.yaml).

---

## Diagnostic Task Monitoring

**Dual-mode UX for polling the async `create-diagnostic-task` → `describe-diagnostic-result` (decided by the Normal upper bound; the poll goes through `safe_aliyun` and is also subject to the Transient Failure Retry hard rule; see [edge-cases.md §1.5](references/edge-cases.md#15-long-running-async-task-ux-client-experience))**:

- **A. Foreground burst polling (DEFAULT for all three DiagnosticType)** — 10s rounds, each round an **independent Bash call** (`sleep 10 && poll_diagnostic_burst …`); after each round the Agent relays the progress line (`poll # + state + elapsed`) in the reply body. Packing the loop into one long blocking command is forbidden (frontend shows nothing). If elapsed ≥ 20min or the user says "I won't wait anymore" → downgrade to B.
- **B. Return immediately + suspend (ONLY on explicit user opt-out or A-downgrade)** — on HTTP 2xx + non-empty `DiagnosticId`, register to `$HOME/.lingjun/diag-pending-tasks.json`, emit a `resume_command`, and end the current session round. The submission receipt (DiagnosticId + RequestId) must still be echoed first.

**Anti-fabrication red line**: Under mode B, the `last_state_snapshot` is used only as resume input / display fallback and **must not** impersonate real-time state; all ✅ / ❌ terminal conclusions must come from a fresh `describe-diagnostic-result` response. Hard caps: BasicCheck 30min, NodeHardwareCheck/CheckByAiJobLogs 60min; on exceeding the hard cap, follow [edge-cases.md §1.2](references/edge-cases.md#12-decision-tree) and offer "continue waiting / re-submit / file a ticket" three-way choice.

---

## Edge Cases and Error Handling

Full decision tree / retry wrapper / failure samples → [edge-cases.md](references/edge-cases.md); per-`ErrorCode` handling → [error-codes.md](references/error-codes.md). Seven-class index:

1. **Timeout** — 10s burst rounds with a per-round user-facing progress line (diagnostic tasks); hard caps BasicCheck 30min, NodeHardwareCheck/CheckByAiJobLogs 60min, repair (reboot/reimage/stop) 30min, report-node-status / stop-node-diagnostic 5min. On exceeding, stop polling and give the user a "continue waiting / re-submit / file a ticket (with `RegionId` + `DiagnosticId`)" three-way choice.
2. **Error-code lookup** — Look up [error-codes.md](references/error-codes.md) first; on miss, fall back to `ErrorCode + Message`; for parameter errors, "auto-fix if possible, otherwise interactively re-pick".
3. **Reentrancy** — Retries must not produce side effects: before submit-diagnostic, check whether an active `DiagnosticId` for the same node exists in `list-diagnostic-results`; before reboot/reimage/stop, query `describe-node.OperatingState`.
4. **Exception classification & retry** — Transient/Throttling ✅ retry; Auth/Permission/NotFound/Business ❌; `DiagnosticConflict` (already in progress) ✅ join existing rather than re-submit; Partial failure (multi-node) ✅ only the failed subset → report. See [edge-cases.md §4](references/edge-cases.md).
5. **Rollback** — Diagnostic tasks are read-only on the node and need no rollback. `reboot-nodes` is reversible (node returns to `Using` once boot completes); `reimage-nodes` is **destructive** (system disk wiped) — for stuck async stages, guide the user to file a ticket; `stop-nodes` is reversible via `start-nodes` (not in this skill — escalate to console).
6. **Unified error output** — Failures must include `❌` summary + `ErrorCode` + impact + suggestion + `RequestId` / `DiagnosticId`; template in [edge-cases.md §6](references/edge-cases.md).
7. **Pagination exhaustion** — Non-empty `NextToken` must auto-paginate to exhaustion; after a soft cap of 50 pages / 1000 records, run HITL; **strictly forbidden** to stop mid-pagination to answer or to silently truncate.

**Success Verification**: diagnose → terminal-state in `describe-diagnostic-result`; reboot → `describe-node.OperatingState` returns to `Using`; reimage → `describe-node.OperatingState=Using` AND `ImageId` matches the new one; stop → `describe-node.OperatingState=Stopped`; report-node-status → 2xx + `ReportId` + `RequestId` AND `list-fault-reports` shows the new report with `Status=Processing`; stop-node-diagnostic → 2xx + `RequestId` AND `describe-fault-report.Status` ∈ {`DiagnosisTerminating`, `DiagnosisTerminated`}. See [verification-method.md](references/verification-method.md).

---

## Observability (MUST follow for every aliyun command)

> Upon loading this skill, `lib/lj_init.sh` generates a random session ID (32-char lowercase hex string) once for the entire session and exports it as `LJ_SESSION_ID`. Use it as `{session-id}` below.
>
> **Rule: Every `aliyun` CLI command that calls a cloud API MUST carry the following User-Agent.** `lib/lj_init.sh` injects it automatically via the `ALIBABA_CLOUD_USER_AGENT` environment variable; when issuing an `aliyun` API command outside the wrapper, pass the flag explicitly.
> Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.
>
> ```
> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-lingjun-node-diagnose/{session-id}
> ```
>
> Do not skip, alter the format, or omit the User-Agent on any `aliyun` API command invocation. Legacy configure-based User-Agent mechanisms are deprecated and must NOT be used.

---

## Troubleshooting

**Common Issues**: Plugin not found → install plugin. Auth failed → check `aliyun configure list`. Permission denied → check [ram-policies.md](references/ram-policies.md). **API**: Eflo-Controller (v2022-12-15); plugin `eflo-controller`; docs <https://api.aliyun.com/api/eflo-controller/2022-12-15>.

---

## Reference Links

See the [`references/`](references/) directory: parameters and hard rules (`api-parameters` / `endpoint-routing` / `parameter-confirmation` / `mutating-schemas/` / `ram-policies`); exceptions and retries (`edge-cases` / `error-codes`); Feature flows (`diagnose-operations` / `repair-plan-templates` / `fault-report-tracking`); quick references and verification (`command-quick-reference` — extended skeletons with worked examples, the companion to the one-page table in §Command Quick Reference above — / `verification-method` / `supported-regions` / `scripts` / `cli-installation-guide`).
