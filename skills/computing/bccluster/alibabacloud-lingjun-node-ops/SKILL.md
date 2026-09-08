---
name: alibabacloud-lingjun-node-ops
description: |
  Manage Alibaba Cloud Lingjun (hyper-)node full-lifecycle ops: stop/reboot/reimage,
  subscription renewal (bssopenapi renew-instance), spec change (change-node-types),
  repair (report-node-status/approve-operation), run-command, node-group default
  update, tag/untag, change-resource-group, plus read-only inventory prerequisite
  (list-cluster-nodes/describe-node/list-cluster-hyper-nodes). change-node-group &
  send-file out of scope (see alibabacloud-lingjun-cluster-scaling).
  Triggers: "lingjun node ops", "灵骏节点运维", "节点停机", "stop nodes", "节点重启",
  "reboot nodes", "节点重装", "reimage nodes", "节点续费", "renew lingjun node",
  "节点规格修改", "change node types", "节点维修", "report node status",
  "节点执行命令", "run command", "节点分组更新", "update node group",
  "节点打标", "tag node", "节点资源转组", "change node resource group".
---

# Alibaba Cloud Lingjun Node Operations (Full Lifecycle)

## Scenario Description

Cover the **post-provisioning** day-to-day operations of Lingjun regular nodes (`NodeId`) and rack-level hyper-nodes (`HyperNodeId`). Provisioning/expansion/shrink/release is **out of scope** here - see the sister skill `alibabacloud-lingjun-cluster-scaling`. This skill focuses on 9 capability areas / 22 use cases (node-to-group move `change-node-group` and file delivery `send-file` are out of scope):

| # | Capability | Mutating CLI | Sync/Async | Reversible |
|---|---|---|---|---|
| F1 | Node Stop | `stop-nodes` | Async (TaskId) | Yes (start later via reboot) |
| F2 | Node Reboot | `reboot-nodes` | Async (TaskId) | N/A |
| F3 | Node Reimage | `reimage-nodes` | Async (TaskId) | **No** (data loss) |
| F4 | Node Renew | `bssopenapi renew-instance` | Sync (OrderId) | No (paid) |
| F5 | Node Spec Change | `change-node-types` | Async (TaskId) | Yes (re-issue) |
| F6 | Repair | `report-node-status` + `approve-operation` | Sync | N/A |
| F7 | Run Command | `run-command` (+ `describe-invocations` / `stop-invocation`) | Async (InvokeId) | N/A |
| F8 | Node Group Update | `update-node-group` (group default) | Sync | Yes |
| F9 | Tag & Resource Group | `tag-resources` / `untag-resources` / `change-resource-group` | Sync | Yes |

> **Canonical Chinese feature names (MANDATORY in zh sessions)** - the authoritative zh rendering strings live in `lib/core/i18n.sh` (`render.feat.F1`..`render.feat.F9` keys, rendered via `_lj_t`); the agent must use them verbatim and never free-translate (e.g. F5 must never be rendered with a non-canonical synonym). The `F1`-`F9` codes themselves are **internal documentation indices** - never show them in **any user-facing output** (confirmation-table titles, operation names, submission receipts, progress lines, final reports): write the canonical feature name plus the CLI name in parentheses, never the F-code; they may appear only in capability-overview tables that enumerate all features.

**Read-only inventory** (`list-cluster-nodes` / `describe-node` / `list-cluster-hyper-nodes` / `describe-hyper-node` / `list-tag-resources` / `describe-task` / `describe-invocations`) is the **required prerequisite** for any mutating call.

**Supported Regions**: `safe_aliyun aliyun eflo-controller describe-regions --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou` (the discovery seed) or `cn-wulanchabu` / `cn-shanghai` / `cn-beijing` / `cn-hangzhou` / international gateways. Test region: `cn-wulanchabu-test-6` (auto-injects `--insecure`).

---

## Installation

Verify `aliyun version >= 3.3.3`; otherwise:

```bash
curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash
aliyun version
```

This skill orchestrates **two** Alibaba Cloud OpenAPI namespaces (plugin mode, lowercase-hyphenated commands):

| Plugin | CLI Namespace | Used For |
|---|---|---|
| `eflo-controller` | `aliyun eflo-controller ...` | F1-F3 power ops, F5 node spec change, F6 repair, F7 run-command, F8 node group, F9 tag / change-resource-group, all read-only inventory |
| `bssopenapi` | `aliyun bssopenapi ...` | F4 subscription renewal (`renew-instance`) and order verification (`query-orders`) |

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install --name eflo-controller
aliyun plugin install --name bssopenapi
aliyun plugin update
```

Verification: `aliyun eflo-controller version && aliyun bssopenapi version`. See [cli-installation-guide.md](references/cli-installation-guide.md).

---

## Authentication

Verify credentials via `aliyun configure list`. **Never** echo or display AccessKey values; render as `***` when discussing them. Missing -> guide users to the [Alibaba Cloud RAM Console](https://ram.console.aliyun.com/manage/ak) outside this session.

---

## RAM Permissions

Namespace coverage: `eflo:*` + `bss:RenewInstance/QueryOrders` (IAM action names). Split into 4 permission sets for least-privilege:

| Set | Actions | API Coverage |
|---|---|---|
| **Read-Only** | `eflo:DescribeRegions/ListClusters/ListClusterNodes/ListClusterHyperNodes/DescribeNode/DescribeHyperNode/ListNodeGroups/DescribeNodeGroup/DescribeTask/ListTagResources/DescribeInvocations` | Inventory & verification |
| **Power** (F1-F3) | `eflo:StopNodes/RebootNodes/ReimageNodes/DescribeTask` | Power state mutation |
| **Lifecycle** (F4-F8) | `eflo:ChangeNodeTypes/ReportNodeStatus/ApproveOperation/RunCommand/StopInvocation/UpdateNodeGroup` + `bss:RenewInstance/QueryOrders` | Renewal / node spec change / repair / exec / group update |
| **Tag & RG** (F9) | `eflo:TagResources/UntagResources/ListTagResources/ChangeResourceGroup` | Metadata mutation |

Full policies in [ram-policies.md](references/ram-policies.md). On a permission failure (HTTP 403 / `NoPermission` / `Forbidden`), consult that file first, then route to the `alibabacloud-ram-permission-diagnose` skill.

---

## Observability (MANDATORY for every aliyun command)

1. **Session-id generation rule**: upon loading this skill (`source lib/lj_init.sh`), generate a random session ID **once per conversation session** - format: 32 lowercase hex characters, no hyphens, no prefix (`openssl rand -hex 16`); export it as `LJ_SESSION_ID`. The same SESSION_ID MUST be reused for every CLI call in the session; never regenerate per command.
2. **UA template (complete declaration)**: every `aliyun ...` command MUST carry `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-lingjun-node-ops/<SESSION_ID>"` - the same SESSION_ID embedded in the `--user-agent` of EVERY command. `lib/lj_init.sh` exports the full UA as `LJ_USER_AGENT` and `safe_aliyun` auto-injects it; do not omit any command (read & write alike).
3. **Deprecated mechanism**: the legacy configure-level user-agent switch (the deprecated `aliyun configure` subcommand form for UA injection) MUST NOT be used in this skill; only the per-command `--user-agent` flag with the template above is accepted.

---

## Parameter Confirmation

> [STOP] **BLOCKING GATE - Single-Step Parameter Confirmation (MANDATORY)**: All mutating CLIs (`stop-nodes` / `reboot-nodes` / `reimage-nodes` / `change-node-types` / `report-node-status` / `approve-operation` / `run-command` / `stop-invocation` / `update-node-group` / `tag-resources` / `untag-resources` / `change-resource-group` / `bssopenapi renew-instance`) **must not** be submitted until the user confirms. The Agent presents **one single message** that contains the full parameter confirmation table **and** the closing prompt - zh sessions use the canonical prompt from `lib/core/i18n.sh` key `render.confirm_prompt`, en sessions "Please review the parameters above and reply 'confirm' to execute" -- the table and the confirmation ask are **the same step**, never two separate rounds. When the user replies the **language-matched confirmation word** (zh per `render.confirm_word`, en `confirm`, case-insensitive; the other language's word is not accepted), the Agent submits via [`safe_mutate_oneshot`](references/scripts.md); any other reply -> [paused] Not Executed. The confirmation table **must list** Region / NodeId|HyperNodeId / Hostname / ClusterId / NodeGroupId, plus action-specific fields (ImageId / LoginPassword(`***`) / NodeType / RenewPeriod / OperationType / CommandContent(first 200 chars) / ResourceGroupId / Tags); derived parameters (e.g. `Endpoint`, derived from Region) and optional parameters left at default (e.g. `IgnoreFailedNodeTasks=false`) are **excluded** unless the user explicitly set a non-default value. Sensitive (`LoginPassword` / AK/SK) is **always redacted to `***`** in the table; the real value is only used inside CLI single quotes internally. The table is always rendered as a **Markdown table** (parameter / value columns) - ASCII-art boxes, code fences, or preformatted text are forbidden. Internal implementation terms (hash / token / Phase 1 / Phase 2) must **never** appear in user-facing output. Per-action schemas in [`mutating-schemas/`](references/mutating-schemas/); full table templates in [parameter-confirmation.md](references/parameter-confirmation.md).

**Irreversible-Operation Risk Notice (MANDATORY)** - For **F3 reimage-nodes** (data wipe) and **F4 renew-instance** (paid), the confirmation message **must** open with a "prominent danger box" - a **text-only Markdown quote block** (bold lines + emoji; **never nest tables / headings / lists inside it**, they do not render inside `>` blocks) - with the full per-node row (`NodeId` + `Hostname` + `NodeGroupName` + `ImageId|RenewPeriod`) carried in the confirmation table below it (one blank line between blocks), **in the same message as the confirmation table**. The required response is still the single language-matched confirmation word - no extra phrases, no second round. The canonical zh danger wording lives in `lib/core/i18n.sh` (`render.danger_reimage` / `render.danger_reimage_tail` / `render.danger_renew_tail`).

**Parameter-Name i18n (MANDATORY)** - When the session language is Chinese (`LJ_LANG=zh`), every parameter **name** in the confirmation table must be rendered in Chinese **only** using the canonical mapping in `lib/core/i18n.sh` (`pname.*` keys, e.g. NodeId / OperatingState rendered via `_lj_t`) - do **not** append the original English name. Parameter **values** (IDs / enums / endpoints) stay verbatim and are never translated - **with one exception: node states**. `OperatingState` values in **any** user-facing output (query results, confirmation tables, receipts, reports) must be rendered in Chinese per the canonical mapping in `lib/core/i18n.sh` (`state.*` keys, rendered via `_lj_state_t`; see [node-state-i18n.md](references/node-state-i18n.md) for the rendering rules); states not in the table stay in English. Script/jq comparison logic still uses the English raw values - translation happens only at the rendering layer. In English sessions keep original names and states. Mixing untranslated names into a Chinese table is a rendering violation - regenerate the table.

**Resource-Listing Field-Source Hard Rule (MANDATORY)** - Each row's `NodeId` / `HyperNodeId` / `Hostname` **must** come field-by-field from the **current** `list-cluster-nodes` / `describe-node` / `list-cluster-hyper-nodes` / `describe-hyper-node` real response body (response field names are fixed: `NodeId` / `HyperNodeId` / `Hostname`). Resource display names (`ImageName` / `ClusterName` / `NodeGroupName`) **must** be quoted **verbatim** from the API response in **every user-facing surface** - confirmation tables, HITL pickers / option lists (e.g. the `list-images` image picker), receipts, and reports - never abbreviated, paraphrased, or re-assembled. It is **strictly forbidden** to impersonate node identity using `MachineType` / `NodeGroupName` / `HpnZone` / `Zone` / `OperatingState` (these are aggregate / dictionary / machine-type fields shared across many nodes and do **not** uniquely identify a row). Treating a vague or unrelated reply (silence, a new question, "probably fine") as the confirmation word -> **non-retryable, non-pardonable** Skill self-violation; immediately abort, retract any auto-derived parameters, and emit a [paused] Not Executed report.

**`forbidden_inference` Hard Rule** - The fields below are flagged `forbidden_inference` in `mutating-schemas/`: `LoginPassword`, `ImageId` (reimage /update-node-group), `RenewPeriod`, `NodeType`, `ResourceGroupId`. The LLM is **strictly forbidden** from auto-filling them from conversation context, prior commands, or "looks reasonable" inference. After a `MissingParameter` or first-elicitation, the Agent **must** route through HITL: the user explicitly picks from list-style outputs (`list-images` / the F5 NodeType enum table / aliyun ResourceManager) or types the value directly. Auto-fill = Skill self-violation V3 - non-retryable, non-pardonable.

**Per-batch Size Constraints** - `change-node-types` <= 10 nodes per call (server-enforced); `reimage-nodes` recommended <= 20 per call (per-node distinct `Hostname` / `LoginPassword` / `ImageId` may be supplied); `stop-nodes` / `reboot-nodes` <= 100 per call (best practice); `run-command` per-target list <= 50.

---

## Interaction Rules

**Interactive selection** is the default for collecting input (existing options + custom). Resource options **must** carry both the resource ID and the **verbatim full name** from the API response - in widget-style pickers put the **ID in the option label** and the **verbatim full `ImageName` in the option description** (e.g. label `i194640731762741076447`, description `Alinux3_x86_5.10.134-16.3_NV_RunC_D3_E3C7_570.133.20_V1.3_251027`); if the picker has no description field, the label itself is "<Id> (<full verbatim name>)". Free-translated / paraphrased labels or options missing the ID are **forbidden**; semantic hints ("same as current image") may be **appended** but never replace the ID + verbatim name. Never merge multiple resources into one option. **Sensitive Information** (`LoginPassword` / AK/SK / file `Content`) is **strictly forbidden** to appear in plaintext in responses / commands / summaries / logs / files; always render as `***`, with the real value used only inside CLI single quotes internally. **Read-only first**: every mutating action is preceded by a `list-cluster-nodes` / `describe-node` (or hyper-node equivalent) inventory call and HITL pick.

---

## Core Workflow

### Endpoint Routing & Region Hard Rules (MANDATORY)

> [link] Full text in [endpoint-routing.md](references/endpoint-routing.md). The Agent **must** satisfy all four before any `aliyun eflo-controller` CLI.

1. **Endpoint matches Region**: every `aliyun eflo-controller` command must explicitly carry `--endpoint eflo-controller.<region>.aliyuncs.com`, and `<region>` must be **exactly identical** to `--region`. Mismatch -> `InvalidRegionId`. (BssOpenApi / ECS are exempt - they use central gateway.)
2. **Region is required**: when the user has not explicitly specified a Region, the Agent is **strictly forbidden** to use placeholders, **strictly forbidden** to silently default to `cn-hangzhou` / `cn-wulanchabu`, and **strictly forbidden** to reuse a value left over from a previous turn - must HITL the user first. Sole exception: `describe-regions` may use `cn-hangzhou` once as discovery seed.
3. **Multi-Region Enumeration**: when the user's intent is "what nodes do I have / list all nodes", the Agent **must** run a HITL two-way pick (A. iterate all regions and aggregate / B. specify a single region); single-region answers must explicitly note the scope.
4. **Test region `cn-wulanchabu-test-6`**: **all** `aliyun *` calls in this skill (read & write) **must** append `--insecure`. The test gateway uses a self-signed certificate. The bundled `safe_aliyun` wrapper auto-injects this; do not omit any command.

### Pagination Exhaustion (MANDATORY)

> [link] Full rules in [edge-cases.md Sec.7](references/edge-cases.md#7-pagination-exhaustion). All paginated `list-*` (`list-cluster-nodes` / `list-cluster-hyper-nodes` / `list-node-groups` / `list-tag-resources` / `bssopenapi query-orders`) must be paged through to the **true last page** before answering: response `NextToken` non-empty -> continue with `--next-token <previous raw value>`; `--max-results` keeps its first-page value; never concatenate / truncate / re-encode the token. Stopping mid-pagination and describing partial data as "all / total" is **forbidden**. Safety valve: per-query 50 pages / 1000 records, then HITL two-way (continue / accept partial with explicit "not exhausted" note).

### Pre-Execution Self-Check (MANDATORY)

> Session-scoped one-time hard rule, on par with `safe_mutate`. Before issuing **any** `aliyun ...` (incl. read-only / dry-run / `describe-task` polling) the Agent must execute:

```bash
source "$LJ_SKILL_DIR/lib/lj_init.sh"
```

This also performs the Observability bootstrap (session-id + UA export, see Sec.Observability). Any `aliyun ...` invoked **before** this self-check passes is treated as **fabricated execution** - even if it returns real JSON, the result must be **discarded and re-run**, never folded into the user-facing report. Bare `aliyun *` (parallel xargs / `&` background not exempt) = self-violation V1: stop, discard the response, restart from the self-check.

### Transient Failure Retry (MANDATORY)

**Every** CLI in this skill **must** be issued as `safe_aliyun aliyun ...`; raw invocation is forbidden.

- **Whitelist (silent retry, <= 3 times)**: network failure (connection refused / timeout / TLS / DNS / EOF), HTTP 5xx, transient codes (`ServiceUnavailable` / `InternalError` / `RequestTimeout` / `SystemBusy`) -> `2s/4s/8s` exponential backoff + jitter; throttling (`Throttling*` / 429) -> fixed 60s.
- **Blacklist (fail immediately)**: auth (`InvalidAccessKeyId` / `SignatureDoesNotMatch`), authz (`NoPermission` / `Forbidden` / 403), business 4xx (`InvalidParameter` / `*.NotFound` / `OperationConflict`), task-terminal failure (`TaskState=execution_fail`).
- **Mutating preconditions**: idempotency before retry - `bssopenapi renew-instance` requires a stable `ClientToken` (UUID, same across retries); once `TaskId` / `InvokeId` / `OrderId` is obtained, switch to async polling, do not retry the submit.

### Async Submission Receipt & Progress Reporting (MANDATORY)

1. **Submission receipt first**: the moment a mutating submit returns, the Agent **must** surface a receipt in the **visible reply body** - output produced inside thinking / reasoning blocks is invisible to the user and **counts as no report**. Receipt fields: action (canonical name per `render.feat.*` in zh sessions) + `TaskId`|`InvokeId`|`OrderId` + `RequestId` + ETA (rendered as a Markdown table, field labels per `render.receipt_action` / `render.receipt_eta` in zh sessions). Skipping or hiding the receipt = self-violation V7.
2. **Default: on-demand status checks, no continuous polling.** Continuous in-chat progress is structurally impossible in this IDE (mid-chain narration folds into thinking; per-round calls trip loop protection; the collapsed terminal block shows only the command echo). So after the receipt the Agent ends the turn with: estimated completion time + the on-demand progress prompt (zh per `render.progress_ondemand` in `lib/core/i18n.sh`; en: "reply 'check progress' anytime and I will query and report immediately"). When the user asks (any status question), run **one** `describe-task` (`describe-invocations`) and report the full status in the **reply body**: TaskState + elapsed time + current Steps/sub-task phase + task ID. On terminal state, run the feature's verification (`describe-node` etc.) and write the final report in the body.
3. **Optional: terminal watch mode - only when the user explicitly asks to watch/monitor continuously.** Run one short foreground command `bash "$LJ_SKILL_DIR/lib/lj_poll.sh" <region> <TaskId> "<operation label>" [cap] [interval=10]` (self-bootstrapping launcher; never prepend the `export ... && source ...` chain; the operation label is the canonical zh feature name in zh sessions). It streams a banner + one heartbeat per round to the live terminal; the reply must state that the live stream is in the expanded terminal block / bottom terminal panel, and the Agent snapshots the terminal (~ every 60s) to relay the latest heartbeat. Soft-timeout (rc=2) -> report latest state + HITL continue/stop.
4. **Forbidden in any mode**: per-round separate Bash calls every 10s (loop protection); backgrounding silently; `LJ_QUIET=1` in interactive sessions; fabricating progress lines without a real API response.

---

## Authenticity & Anti-Fabrication Constraints (NON-NEGOTIABLE)

1. All completion reports **must** be strictly generated from real CLI-returned JSON. Critical fields (`TaskId` / `RequestId` / `OrderId` / `InvokeId` / `NodeId` / `HyperNodeId` / `TaskState` / `InvocationStatus` / `OperatingState`) must come from real API response bodies - **must not** be stitched, guessed, or reused from historical context.
2. When a core API was not successfully called or returned failure, the report **must** mark "not executed / execution failed" and produce a complete failure analysis per [edge-cases.md Sec.6](references/edge-cases.md).
3. **Strictly forbidden**: mock / placeholder values impersonating real returns; hard-coding `TaskId`/`RequestId`/`OrderId`/`InvokeId`; fabricating `TaskState`/`InvocationStatus` transitions; producing "polling logs / progress bars / monitoring scripts / timestamps" that lack real API backing.

**Execution-state tags**: each mutating-action report must carry one of: [OK] **Executed successfully** / [waiting] **Submitted, pending poll** / [FAIL] **Execution failed** / [paused] **Not executed**. If no real APIs ran in a session, the response **must** explicitly state "no cloud-side changes were made in this session".

---

## Features

> [attach] Per-API parameter inventories, defaults, and prompt phrasings live in [api-parameters.md](references/api-parameters.md). Each Feature below lists only highlights.

### Feature 1: Node Stop (`stop-nodes`)

Halt one or more Lingjun nodes (regular `NodeId`). Returns `{ "TaskId": "...", "RequestId": "..." }`.

**Workflow**: (1) locate cluster -> (2) `list-cluster-nodes` -> HITL pick `NodeId[]` -> (3) pre-check current `OperatingState` (must be `Using` / `HealthyUsing`; reject `Stopped` / `Deleting` / `Failed`) -> (4) confirmation table + user replies the confirmation word (single step) -> (5) submit -> user-facing receipt (`TaskId`) -> (6) on-demand `describe-task` status checks (per Sec.Async Submission Receipt & Progress Reporting) until `TaskState=execution_success` -> (7) verify `describe-node` `OperatingState=Stopped`.

**Required**: `--region`, `--endpoint`, `--nodes <NodeId1> <NodeId2> ...`. **Optional**: `--ignore-failed-node-tasks` (default `false`). **Timeout**: 5-15 min.

```bash
safe_aliyun aliyun eflo-controller stop-nodes \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --nodes e01-cn-xxxx e01-cn-yyyy
```

[doc] [node-power-operations.md](references/node-power-operations.md) - [mutating-schemas/stop-nodes.yaml](references/mutating-schemas/stop-nodes.yaml).

---

### Feature 2: Node Reboot (`reboot-nodes`)

Reboot one or more nodes; OS reboot, **state and data preserved**.

**Workflow** (mirror F1): (1) cluster -> (2) list -> (3) pre-check (`Using` allowed; reject `Stopped` since it's a no-op) -> (4) confirmation table + user replies the confirmation word -> (5) submit -> (6) poll -> (7) `describe-node` confirms recent boot time advanced.

**Required**: `--region`, `--endpoint`, `--nodes <id1> <id2>`. **Optional**: `--cluster-id`, `--ignore-failed-node-tasks`.

```bash
safe_aliyun aliyun eflo-controller reboot-nodes \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --cluster-id <cid> --nodes e01-cn-xxxx
```

[doc] [node-power-operations.md](references/node-power-operations.md).

---

### Feature 3: Node Reimage (`reimage-nodes`) - IRREVERSIBLE

Re-install OS on one or more nodes. **System-disk data is destroyed** - the system disk is reformatted; **data disks are left untouched by default**. Canonical zh danger wording: `render.danger_reimage` in `lib/core/i18n.sh` (system disk reformatted and wiped; data disks kept by default) - do NOT claim "all data on the node will be wiped". Per-item required fields: `Hostname`, `ImageId`, `NodeId`; per-item optional: `LoginPassword` (omit -> node keeps its existing password; if supplied, rendered as `***`).

**Workflow**: (1) cluster -> (2) list -> (3) HITL pick + per-node fill `Hostname` / `ImageId` (must come from `list-images` HITL - `forbidden_inference`) / optional `LoginPassword` (`***`; omit when the user wants to keep the current password) -> (4) pre-check `OperatingState=Stopped` (preferred) or `Using` -> (5) **danger box + confirmation table in one message; user replies the confirmation word** -> (6) submit -> (7) poll -> (8) verify `describe-node` `ImageId` updated and `OperatingState=Using`.

**Required**: `--region`, `--endpoint`, `--nodes Hostname=<h> ImageId=<i> NodeId=<n>` (per-node `LoginPassword=<pwd>` optional - omit to keep existing password). **Optional**: `--cluster-id`, `--user-data`, `--ignore-failed-node-tasks`. **Timeout**: 30-60 min.

```bash
safe_aliyun aliyun eflo-controller reimage-nodes \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --cluster-id <cid> \
  --nodes Hostname=node-001 ImageId=m-xxx NodeId=e01-cn-xxxx [LoginPassword='***']
```

[doc] [node-power-operations.md](references/node-power-operations.md) - [mutating-schemas/reimage-nodes.yaml](references/mutating-schemas/reimage-nodes.yaml).

---

### Feature 4: Node Renew (`bssopenapi renew-instance`) - PAID

Extend the subscription period of a subscription Lingjun node. **Generates an order - irreversible payment**.

**Workflow**: (1) locate node -> (2) `describe-node` to confirm `BillingType=PrePaid` and read `ExpiredTime` -> (3) HITL pick `RenewPeriod` (allowed `1..9 / 12 / 24 / 36` months - `forbidden_inference`) -> (4) generate stable `ClientToken` (UUID) -> (5) **danger box (cost estimate by month x machine-type list-price) + confirmation table in one message; user replies the confirmation word** -> (6) submit `renew-instance` -> (7) verify via `bssopenapi query-orders --order-id <oid>` `Status=Success` -> (8) re-fetch `describe-node`, confirm `ExpiredTime` advanced.

**Required**: `--instance-id <NodeId>`, `--product-code bccluster`, `--renew-period <month>`. **Business required (CLI-Optional)**: `--product-type bccluster_eflocomputing_public_cn` (China) / `..._intl` (international). **Optional**: `--client-token <uuid>`. **Endpoint order (MANDATORY)**: try `--endpoint business.aliyuncs.com` first; if unreachable or site-mismatched (e.g. `Product code is invalid`), fall back to `--endpoint business.ap-southeast-1.aliyuncs.com` (+ `_intl` product type), keeping the same `ClientToken`.

```bash
safe_aliyun aliyun bssopenapi renew-instance \
  --endpoint business.aliyuncs.com \
  --instance-id e01-cn-xxxx \
  --product-code bccluster --product-type bccluster_eflocomputing_public_cn \
  --renew-period 1 --client-token <uuid>
```

`InstanceId` for Lingjun renewal = `NodeId` (the `e01-cn-xxx` form). On `Failure to check order` -> see [error-codes.md](references/error-codes.md).

[doc] [node-renew.md](references/node-renew.md) - [mutating-schemas/renew-instance.yaml](references/mutating-schemas/renew-instance.yaml).

---

### Feature 5: Node Spec Change (`change-node-types`)

Change a node's **NodeType** (DPU/storage mode) in-place. `--node-type` is **NOT** a machine type - it is one of 9 enum values: `cpfs-enhanced` / `ebs-enhanced` / `balanced` / `cpfs-enhanced-multi-tenant` / `ebs-enhanced-multi-tenant` / `balanced-multi-tenant` / `zeroLeni-cpfs` / `zeroLeni-ebs` / `zeroLeni-balanced`. Current value = `describe-node.NodeType`. Transitions are constrained by the cluster vdpu version and single/multi-tenant matrix (single<->multi and zeroLeni<->non-zeroLeni never interchangeable) - see node-spec-change.md. **Important**: task success != change success (per-node `RESOURCE_INSUFFICIENT` possible); always re-verify `describe-node.NodeType`.

**Workflow**: (1) cluster -> (2) `list-cluster-nodes` -> HITL pick `NodeIds[]` (<=10, same node group, `OperatingState=Using`) -> (3) HITL pick `--node-type` from the 9-value enum per current `NodeType` + transition matrix (`forbidden_inference`; never from `list-machine-types`) -> (4) warning box + confirmation table in one message; user replies the confirmation word -> (5) submit -> (6) poll task -> (7) for each node call `describe-node` and **compare `NodeType` against the requested target**; on mismatch emit [WARN] partial-success report.

**Required**: `--region`, `--endpoint`, `--node-ids <id1> <id2> ...` (<=10), `--node-type <NodeType enum value>`.

```bash
safe_aliyun aliyun eflo-controller change-node-types \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-ids e01-cn-xxxx e01-cn-yyyy --node-type ebs-enhanced
```

[doc] [node-spec-change.md](references/node-spec-change.md) - [mutating-schemas/change-node-types.yaml](references/mutating-schemas/change-node-types.yaml).

---

### Feature 6: Repair (`report-node-status` + `approve-operation`)

Two sub-features:

**6.1 Report node fault** (`report-node-status`, general-user API `ReportNodeStatus`): declare a fault on a single node; the platform immediately creates a fault report (`Status=Processing`, visible via `list-fault-reports`) and spawns the repair/deep-diagnosis workflow. Returns `ReportId` + `RequestId` (sync). Replaces the legacy PAI-only `report-nodes-status` — do not use it.

**Required**: `--node-id <NodeId>` (single), `--diagnosis-type COMPREHENSIVE` (only value accepted today), `--description <text written by the user>` (`forbidden_inference`). **Preconditions**: node state `Using`; daily quota (default 10% of account machines); no duplicate account+node report.

```bash
safe_aliyun aliyun eflo-controller report-node-status \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id e01-cn-xxxx --diagnosis-type COMPREHENSIVE \
  --description 'GPU 0 ECC error spike'
```

**6.2 Approve maintenance operation** (`approve-operation`): when service-side raises a maintenance proposal pending user approval (node in a `*PendingApproval` state), approve it by `(NodeId, OperationType)`. `OperationType` is a closed enum picked via a three-way HITL guided by the measured pending state: `RepairMachine` (`ClusterNodeRepairPendingApproval`) / `RebootMachine` (`ClusterNodeRebootPendingApproval`) / `UpgradeMachine` (`ClusterNodeUpgradePendingApproval`); `TerminateWindow` is internal-only and forbidden through this CLI.

**Required**: `--node-id <NodeId>`, `--operation-type <RepairMachine|RebootMachine|UpgradeMachine>`.

```bash
safe_aliyun aliyun eflo-controller approve-operation \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id e01-cn-xxxx --operation-type RepairMachine
```

Both sub-features are sync; verify by re-querying node status / inbox notifications.

[doc] [node-repair.md](references/node-repair.md) - [mutating-schemas/approve-operation.yaml](references/mutating-schemas/approve-operation.yaml).

---

### Feature 7: Run Command (Cloud Assistant)

**7.1 Run shell command** (`run-command`): execute Bash on one or more nodes. Returns `{ "InvokeId": "...", "RequestId": "..." }`.

**Required**: `--node-id-list <id1> <id2>`, `--command-content <bash-script>`. **Highly recommended**: `--client-token <uuid>` (idempotency), `--timeout <sec>` (default 60), `--name <human-readable>`, `--working-dir <path>`. **Optional**: `--enable-parameter true` + `--parameters '{"key":"val"}'` for `{{var}}` substitution; `--repeat-mode Once|Period|NextRebootOnly|EveryReboot` (+ `--frequency` for `Period`); `--username` (Linux default `root`). Encoding: `--content-encoding PlainText` (default) | `Base64`.

```bash
safe_aliyun aliyun eflo-controller run-command \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id-list e01-cn-xxxx --command-content 'nvidia-smi -L' \
  --timeout 30 --name 'check-gpu' --client-token <uuid>
```

**7.2 Poll execution** (`describe-invocations`): `--invoke-id <InvokeId>` (required) + `--node-id <NodeId>` + `--include-output true` + `--content-encoding PlainText`. Field of interest: `Invocations[0].InvokeNodes[*].InvocationStatus`  in  {`Pending`, `Scheduled`, `Running`, `Success`, `Failed`, `Stopped`, `Stopping`, `PartialFailed`, `Timeout`}.

**7.3 Stop in-flight** (`stop-invocation`): `--invoke-id <InvokeId>` (+ optional `--node-id-list`).

[WARN] Do not place secrets in `--command-content` plaintext - render as `***` in any user-facing summary; use `--enable-parameter` + a value-only Parameters JSON when secrets are unavoidable.

[doc] [node-exec-command.md](references/node-exec-command.md) - [mutating-schemas/run-command.yaml](references/mutating-schemas/run-command.yaml).

---

### Feature 8: Node Group Update (`update-node-group`)

> [BLOCK] **Scope boundary (MANDATORY)** - This feature only updates the **node group's default config**. Moving a node into another group (`change-node-group`) is a **different** concept and is **out of scope** here - route such requests to the sister skill `alibabacloud-lingjun-cluster-scaling`.

**Update node-group default config** - modifies the **node group's default** parameters used for **future** node provisioning; existing nodes are not affected.

> [WARN] **CLI --help doc-hallucination hard rule (MANDATORY)** - `aliyun eflo-controller update-node-group --help` marks `--new-node-group-name` as Optional, but server-side it is **mandatory**: even if the user only wants to change `--image-id` / `--login-password` / `--user-data` / `--biz-key-pair-name` / `--biz-ram-role-name` / `--file-system-mount-enabled`, omitting `--new-node-group-name` causes `MissingParameter`. The Agent **must** carry the existing name from `describe-node-group` if the user does not want to rename.

**Required**: `--node-group-id <gid>`, `--new-node-group-name <name>`. **Mutating optional fields** (>=1 of these must be provided to make a meaningful change): `--image-id` (`forbidden_inference`), `--login-password` (`***`), `--user-data`, `--biz-key-pair-name`, `--biz-ram-role-name`, `--file-system-mount-enabled true|false`, `--system-disk PerformanceLevel=<PL>` (system disk: **performance level only** - Category/Size have no parameters and cannot be changed; changing disk type/size requires delete+recreate via the scaling skill).

```bash
safe_aliyun aliyun eflo-controller update-node-group \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-group-id ng-xxx --new-node-group-name <existing-name> \
  --image-id m-xxx --login-password '***'
```

[doc] [node-group-update.md](references/node-group-update.md) - [mutating-schemas/update-node-group.yaml](references/mutating-schemas/update-node-group.yaml).

---

### Feature 9: Tag & Resource Group

**9.1 Tag node** (`tag-resources`):

**Required**: `--biz-region-id <region>`, `--resource-type node`, `--resource-id <id1> [<id2> ...]`, `--tag Key=<k> Value=<v> [--tag Key=<k2> Value=<v2>]`.

```bash
safe_aliyun aliyun eflo-controller tag-resources \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --biz-region-id <region> --resource-type node --resource-id e01-cn-xxxx \
  --tag Key=env Value=prod --tag Key=team Value=ai
```

**9.2 Untag node** (`untag-resources`): `--resource-type node`, `--resource-id <id>`, `--tag-key <k1> <k2>` *or* `--all=true` (only effective when `--tag-key` is empty).

**9.3 List tags** (`list-tag-resources`): `--biz-region-id`, `--resource-type node`, plus optional `--resource-id` / `--tag Key= Value=` filters.

**9.4 Change resource group** (`change-resource-group`): move node into another resource group (RAM scope).

**Required**: `--resource-region-id <region>`, `--resource-type node`, `--resource-id <NodeId>`, `--resource-group-id <new-rgid>` (`forbidden_inference` - must come from `aliyun resourcemanager list-resource-groups`).

```bash
safe_aliyun aliyun eflo-controller change-resource-group \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --resource-region-id <region> --resource-type node \
  --resource-id e01-cn-xxxx --resource-group-id rg-xxxx
```

All four return synchronously with `RequestId` only (no `TaskId`); verify with `list-tag-resources` / `describe-node`. Submission goes through the single-step confirmation gate (confirmation table + the user's confirmation word).

`ResourceType` accepted values: `node` for compute nodes, `cluster` for clusters, `Hypernode` for hyper nodes (case per service contract - see [api-parameters.md](references/api-parameters.md)).

[doc] [tag-and-resource-group.md](references/tag-and-resource-group.md) - [mutating-schemas/tag-resources.yaml](references/mutating-schemas/tag-resources.yaml).

---

## Success Verification

| Feature | Verification |
|---|---|
| F1 stop | `describe-task TaskState=execution_success` + `describe-node OperatingState=Stopped` |
| F2 reboot | `TaskState=execution_success` + `describe-node` boot time advanced (or `OperatingState=Using`) |
| F3 reimage | `TaskState=execution_success` + `describe-node ImageId` matches target + `OperatingState=Using` |
| F4 renew | `bssopenapi query-orders Status=Success` + `describe-node ExpiredTime` advanced by `RenewPeriod` |
| F5 node spec change | `TaskState=execution_success` **AND** `describe-node MachineType == requested NodeType` (otherwise [WARN] partial) |
| F6 repair | `report-node-status` returns `ReportId` + `RequestId` (sync); the new report shows `Status=Processing` in `list-fault-reports`; approval flow tracked via service-side notification |
| F7 run-command | `describe-invocations Invocations[0].InvokeNodes[*].InvocationStatus = Success` |
| F8 update-node-group | `describe-node-group` field equals new value |
| F9 tag | `list-tag-resources` Tags[] contains the new key/value |
| F9 untag | `list-tag-resources` Tags[] no longer contains the key |
| F9 change-resource-group | `describe-node ResourceGroupId` equals target |

---

## Edge Cases & Errors

See [edge-cases.md](references/edge-cases.md) (idempotency / orphan resource scan / partial failure / approximate-confirmation) and [error-codes.md](references/error-codes.md) (per-API code dictionary). The most frequent are:

- `OperationConflict` / `The cluster is not in Running state, not allowed to *` -> another mutating task is in-flight in this cluster; HITL the user (parallel submit / wait).
- `MissingParameter` / `InvalidParameter.*` -> re-elicit the field through HITL with a list-style picker; **must not** auto-fill.
- `Throttling` -> `safe_aliyun` waits 60s and retries automatically (<=3).
- `Failure to check order` (BssOpenApi) -> re-confirm `ProductCode=bccluster` + `ProductType=bccluster_eflocomputing_public_cn` + valid `RenewPeriod`.
- `InvalidNodeStatus` (stop on already-stopped / reboot on stopped) -> pre-check `OperatingState`, **must not** retry.

---

## File Index

- [references/cli-installation-guide.md](references/cli-installation-guide.md)
- [references/endpoint-routing.md](references/endpoint-routing.md)
- [references/parameter-confirmation.md](references/parameter-confirmation.md)
- [references/ram-policies.md](references/ram-policies.md)
- [references/api-parameters.md](references/api-parameters.md)
- [references/edge-cases.md](references/edge-cases.md)
- [references/error-codes.md](references/error-codes.md)
- [references/scripts.md](references/scripts.md)
- [references/node-power-operations.md](references/node-power-operations.md)
- [references/node-renew.md](references/node-renew.md)
- [references/node-spec-change.md](references/node-spec-change.md)
- [references/node-repair.md](references/node-repair.md)
- [references/node-exec-command.md](references/node-exec-command.md)
- [references/node-group-update.md](references/node-group-update.md)
- [references/tag-and-resource-group.md](references/tag-and-resource-group.md)
- [references/mutating-schemas/](references/mutating-schemas/) (per-action YAML schemas)
- [tests/](tests/) (00-bootstrap + per-feature test cases)
