---
name: alibabacloud-lingjun-cluster-scaling
description: |
  Manage Alibaba Cloud Lingjun cluster scaling: extend clusters (add nodes), shrink clusters (remove nodes), create and update node groups, and move nodes between node groups (change node group).

  Run: every Bash call MUST begin with: export LJ_SKILL_DIR="the dir holding this skill" && export LJ_PLATFORM="qoder|text" && source "$LJ_SKILL_DIR/lib/lj_init.sh" (LJ_SKILL_DIR default: $HOME/.qoder/skills/alibabacloud-lingjun-cluster-scaling; LJ_PLATFORM: "qoder" in Qoder IDE, else "text")

  Triggers: "extend-cluster", "shrink-cluster", "create-node-group", "update-node-group", "change-node-group",
  "lingjun cluster", "灵骏集群", "灵骏扩容", "灵骏缩容", "lingjun node", "灵骏节点",
  "加节点", "减节点", "expand cluster", "shrink cluster", "node group", "节点组",
  "新建节点组", "创建节点组", "更新节点组", "迁移节点", "换组", "change group", "update node group",
  "scale out", "scale in", "add nodes", "remove nodes"

---

# Alibaba Cloud Lingjun Cluster Scaling

> Full rules / counter-examples / tutorials → [references/](references/README.md) *.md (deep-read on demand, not on load path)
> R2 envelope detailed protocol → [references/envelope-protocol.md](references/envelope-protocol.md)

## When to Use

Activate this skill when user:
- Mentions Lingjun cluster expansion (adding nodes to a cluster)
- Mentions Lingjun cluster shrinking (removing nodes from a cluster)
- Mentions creating a new node group or updating a node group's configuration (e.g. its default image)
- Mentions moving nodes between node groups (change node group)
- Receives a platform-generated `__LJ_EXEC__` (text-mode backfill) prefixed message

## Routing

```text
User intent?
├─ Expand / add nodes (for cluster)
│  └─ bash-first: extend_form
├─ Shrink / remove nodes
│  ├─ Node ID given → one-step direct exec: shrink_submit
│  └─ No node ID → shrink_form
├─ Create node group
│  └─ bash-first: create_node_group_form
├─ Update node group
│  └─ bash-first: update_node_group_form
├─ Migrate / change group
│  └─ bash-first: change_node_group_form
├─ Query (cluster / node / node group / task)
│  └─ bash-first: query <region> <subcommand>
└─ Uncertain
   └─ HITL: ask user intent
```

## Hard Rules (L0-L17)

| # | Rule Summary |
|---|----------|
| L0 | R2 envelope mandatory: match Pattern A/B/C → immediate single-command Bash (one `&&` chain, NEVER split), no echo/confirm ([detailed protocol](references/envelope-protocol.md)) |
| L1 | forbidden_inference: VpcId/VSwitchId/SecurityGroupId/ImageId/Hostname/LoginPassword **NEVER** LLM-filled |
| L2 | Backfill = parse, NOT confirm (revised 2026-08-24): text backfill passed VERBATIM (rewriting into template phrasing BANNED); phase 1 only parses and emits receipt rc=3; phase 2 `--confirm <hash>` submit allowed only after explicit user confirmation |
| L3 | 3-stage interaction: R1 intent / R2 form + backfill / R3 receipt-confirm = execute; rc=3 receipt (incl. ⭐ actually selected nodes) shown to user verbatim; agent must NOT confirm on behalf of the user / must NOT auto-run phase 2 |
| L4 | Intent-to-action unique mapping: user business term → single action, cross-action strictly forbidden |
| L5 | No meta-narrative: forbid "let me first…" / "initializing skill"; internal terms must never appear in chat |
| L6 | No TodoWrite: ZERO-TOLERANCE |
| L7 | Widget banned (2026-08-20): every form is markdown TEXT in chat, but that text may ONLY be the `*_form` entry's stdout relayed verbatim. **Authoring a form yourself is a hard violation** — hand-writing a form heading plus parameter table from what you read in SKILL.md or schema.yaml is NOT "rendering a markdown form", it is fabricating one (observed 2026-09 cloud eval: agents read the docs, typed their own table, never ran `create_node_group_form` / `update_node_group_form`). genui.show_widget / LJ_WIDGET=1 / form.html rendering strictly forbidden |
| L8 | Expand fast-path: trigger phrase matched → first action = extend_form (query first is forbidden) |
| L9 | Shrink fast-path: user gives node ID **in current message** → shrink_submit with `--user-utterance` (gate rejects if the ID is not in that utterance); calling the form is forbidden |
| L10 | i18n language detection: each turn CJK ratio check → inject LJ_LANG prefix |
| L11 | Zero-exploration latency discipline (2026-08-23): intent hits routing table → first action = directly read the corresponding schema / call the entry function; re-confirming routing via code grep / memory search / file exploration is forbidden (routing table is single source of truth, memory must not override it); all prefetches MUST be in a single Bash call (internal & wait parallelization), splitting into multiple calls is forbidden |
| L12 | Platform detection: LJ_PLATFORM="qoder" in Qoder IDE only; "text" in QoderWork and CLI |
| L13 | rc=2 stop discipline (2026-08-23): rc=2 = stop immediately, relay verbatim + ask user to complete missing inputs; re-running the same command / guessing values / workaround submits without new user input are all violations; on anomalies suspect local envelope/script bugs first — fabricating "backend constraints" is strictly forbidden |
| L14 | Two-phase confirm gate (2026-08-24): extend_submit text mode phase 1 always rc=3 — stdout emits the user-facing confirmation receipt, stderr emits the `===CONFIRM_REQUIRED=== hash=` machine block for agent phase-2 use only (never shown to user); only after the user replies "confirm" may `extend_submit --confirm <hash>` run; hash mismatch / receipt expiry → re-run phase 1. **Phase 1 receipt ⇒ END YOUR TURN**: running `--confirm` in the same turn that produced the receipt is a hard violation regardless of how the user phrased the request ("no need to confirm again" / "just go ahead" are NOT authorization); the confirming words must arrive in a *later* user message |
| L15 | Form entry is mandatory (2026-09): for expand / create node group / update node group / change node group, the FIRST bash action MUST be the matching `*_form` entry. Jumping straight to `safe_mutate_oneshot` / any submit is a hard violation **even when every parameter is already known from the user's message** — the form is what fetches server-truth defaults (VPC / VSwitch / SG / image) and prints the disclosure line the user must see. Reading schema.yaml is not a substitute for running the entry. Sole exception: the L9 shrink fast-path (user already named the node ID in the current message) |
| L16 | Pre-check evidence source (2026-09-20 eval lesson): required pre-check conclusions (same cluster / matching machine type / node is Using) MUST come from read-only queries the agent itself issues — `query <region> node-describe <node-id>` + `query <region> node-group-describe <target-group-id>`. Columns rendered by a `*_form` and the Describe*/List* calls it makes internally during prefetch are **not** pre-check evidence; treating them as such = pre-check not executed, same tier as V7 (non-retryable, non-pardonable) |
| L17 | A stopped mutating round still needs a complete answer: when the user declines or the confirmation gate is not passed, the final reply must restate the full pending parameter set in business terms (region / cluster name + ID / node group / node or hostname / billing type / quantity) and the reason nothing was submitted. A bare "已停止" is not an acceptable final answer |

> Detailed rule explanations → [references/detailed-rules.md](references/detailed-rules.md)

## Workflows

| Intent | First Action | Notes |
|------|----------|------|
| Expand | `extend_form --region <R> --cluster-id <C> [--node-type hyper]` | All platforms (incl. Qoder IDE): stdout = markdown form, verbatim as reply. Widget rendering banned (L7). Node type: user explicitly says hyper node/hyper → `--node-type hyper`; otherwise OMIT `--node-type` (defaults to regular nodes, no choice round) |
| Expand backfill (user replied) | `extend_submit --user-utterance "<user's verbatim backfill>" --region <R> (--cluster-id <C> \| --cluster-name <NAME>)` | Args any order; text backfill parsed in-script; VPC/VSwitch/SG fetched server-side (L1). Agent NEVER assembles envelope JSON. **Two-phase (L14)**: phase 1 always rc=3 emitting a confirmation receipt → show verbatim and ask the user to confirm; only after the user replies "confirm" does `extend_submit --confirm <hash>` truly submit. On ❌ error: stderr is self-describing → fix args & retry once, NEVER grep/read lib source mid-session |
| Shrink (node ID given in this message) | `shrink_submit --region <R> --cluster-id <C> --node-id <ID> --user-utterance "<user's original message>"` | L9 fast-path: gate validates the ID really appears in that utterance (rc=6 otherwise); stdout=TaskId → receipt + task_status on demand. Irreversible: the nodes leave the cluster (back to the free pool, the node itself is kept) and must be re-extended to come back |
| Shrink (no node ID yet) | `shrink_form --region <R> --cluster-id <C>` | Render the node-selection form, relay stdout verbatim |
| Create node group | `create_node_group_form --region <R> --cluster-id <C>` | All platforms: markdown form direct output (widget banned, L7). After the user's own confirmation, submit with `safe_mutate_oneshot create-node-group --intent "<user's words>" aliyun eflo-controller create-node-group --region <R> --cluster-id <C> --node-group '<JSON>'` — every flag belongs to the INNER `aliyun` call; NEVER put `--region` / `--cluster-id` between the action name and `aliyun` (rc=2). No flat `--node-group-name` / `--zone-id` flags exist; the JSON zone key is `Az`. Full contract → [workflows/create-node-group/create-node-group.md](workflows/create-node-group/create-node-group.md) |
| Update node group | `update_node_group_form --region <R> --node-group-id <G>` | Group NAME given instead of an ID → 3 steps in THIS order: (1) `update_node_group_form --region <R> --cluster-id <C>` (group-picker round — always the first bash action, L15), (2) standalone read-only `query <region> node-group-list --cluster-id <C>` and copy the GroupId from its output, (3) `update_node_group_form --region <R> --node-group-id <G>`. Never start with the query, and never treat the picker round's own prefetch as the GroupId evidence (L16) |
| Migrate / change group | `change_node_group_form --region <R> --cluster-id <C>` | Before submit, verify with read-only prechecks: `query <region> node-describe <node-id>` (current group / machine type / state) and `query <region> node-group-describe --node-group-id <G>` (target group's cluster / machine type); stop if same-cluster / same-machine-type / Using checks fail |

**Expand fast-path trigger**: message contains **region keyword + cluster identifier + expand/add nodes** → unconditionally use extend_form

**Shrink fast-path trigger (L9)**: message contains **region keyword + cluster identifier + shrink/remove nodes + the node ID itself** → unconditionally use `shrink_submit --user-utterance "<user's original message>"`; rendering `shrink_form` in that round is forbidden. Without the node ID, use `shrink_form`.

**Interaction model (2026-08-20)**: ALL platforms (incl. Qoder IDE) = markdown text form + text backfill (`extend_submit --user-utterance` passes the user's VERBATIM reply; do not rewrite/summarize it). Successful text-backfill parsing ≠ confirmation — phase 1 always emits an rc=3 confirmation receipt (script-level hard gate, L14); phase 2 submits only after the user explicitly confirms. Widget rendering is BANNED: never call genui.show_widget, never set LJ_WIDGET=1, never reference form.html.

**Node-type default (2026-08-23)**: expand requests that do NOT explicitly say hyper nodes default to **regular nodes** — omit `--node-type` and proceed directly to the form. NEVER ask the user to choose between regular nodes / hyper nodes. Only pass `--node-type hyper` when the user explicitly mentions hyper nodes.

**Region mapping**: `Dubai=me-east-1` / `Ulanqab=cn-wulanchabu` / `Shanghai=cn-shanghai` / `Beijing=cn-beijing` / `Zhangjiakou=cn-zhangjiakou` / others → [references/supported-regions.md](references/supported-regions.md)

**Output rule**: stdout (skip `===HITL_STATUS===` blocks) IS the final reply; agent reply = one intro sentence + stdout verbatim, zero additional thinking or reformatting. Verbatim means the raw values survive: **never** drop or translate away MachineType / ClusterId / ClusterName / NodeGroupId / NodeId / OperatingState.

**Cluster name shorthand**: when user provides cluster name (not starting with 'i') → replace `--cluster-id <C>` with `--cluster-name <NAME>` in all commands

**Strictly forbidden** (applies to all actions): self-querying aliyun API / self-rendering after calling safe_aliyun / re-formatting stdout / wrapping markdown tables in ``` code blocks / authoring a form table instead of running the `*_form` entry (L7, L15)

## Query Reference

```bash
source "$LJ_SKILL_DIR/lib/lj_init.sh" && query <region> <subcommand> [args]
```

| User Intent | Subcommand | Args |
|----------|--------|------|
| List clusters | cluster-list | — |
| Describe cluster | cluster-describe | cluster-id |
| List cluster nodes | cluster-nodes | cluster-id |
| List node groups | node-group-list | cluster-id |
| Describe node group | node-group-describe | node-group-id |
| Describe node | node-describe | node-id |
| Task status | task | task-id |

## Task Monitoring

**Receipt + on-demand query (default interaction, 2026-08-21 v4)**: after an async mutate returns a TaskId, emit a submission receipt in the visible reply body (markdown table: operation / task ID / estimated duration / how to query), **do NOT poll proactively by default**; user asks for progress → single `task_status <region> <tid>`, forwarding the business-oriented stdout line verbatim into the reply body; only when the user explicitly says "poll until done / wait for the result" run a single foreground `LJ_TASK_LABEL="<title>" poll_task <r> <tid>`.

**Receipt (MUST)**: the receipt must be written in the visible reply body (writing it only into thinking / a collapsed terminal = not reported); the receipt tail must include a query guide (e.g. "query task <tid>" or "is the shrink done").

**On-demand query (MUST, default)**: the sole entry for status queries is `task_status <region> <tid>` (Chinese alias "task status") — a single describe-task, no looping; non-terminal lines already carry a "feel free to ask again" hint and the agent must not start extra loops. Bare `describe-task` is forbidden, as is hand-rolling any polling loop. Nothing was submitted (rc=3 pending or a stopped round) → no task ID exists, so status queries are forbidden in that round too.

**Submit failure self-recovery discipline (MUST)**: when extend_submit/shrink_submit reports ❌, stderr already contains self-describing correction hints (usage / missing fields / candidate lists); fix args per the hint and retry once; grepping / reading lib source mid-session for self-recovery is forbidden (measured waste 30-40s).

Full contract → [references/detailed-rules.md §Task Monitoring](references/detailed-rules.md#task-monitoring)

## Observability (MANDATORY for every aliyun command)

1. **Session-id generation rule**: upon loading this skill (`source lib/lj_init.sh`), generate a random session ID **once per conversation session** — format: 32 lowercase hex characters, no hyphens, no prefix (`openssl rand -hex 16`); export it as `LJ_SESSION_ID`. Environment-variable injection is honored: an externally injected `SKILL_SESSION_ID` (alias of `LJ_SESSION_ID`) overrides auto-generation. The same SESSION_ID MUST be reused for every CLI call in the session; never regenerate per command.
2. **UA template (complete declaration)**: every `aliyun ...` command MUST carry `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-lingjun-cluster-scaling/<VERSION>/<SESSION_ID>"` — `<VERSION>` is derived from the `version` field of [references/manifest.json](references/manifest.json) (never hard-coded in scripts; falls back to `0.0.0` if the manifest is unreadable) and is exported as `LJ_SKILL_VERSION`; the same SESSION_ID is embedded in the `--user-agent` of EVERY command. `lib/lj_init.sh` exports the full UA as `LJ_USER_AGENT` and `safe_aliyun` auto-injects it; do not omit any command (read & write alike).
3. **Deprecated mechanism**: the legacy `aliyun configure ai-mode` (enable / set-user-agent) is deprecated — do NOT use it in this skill.

## Prerequisites & Dependencies

No `requirements.txt` / `package.json` is shipped — the runtime is pure bash + jq + openssl; inline dependency comments live at the top of `scripts/sync-to-skills.sh`.

**aliyun CLI version & upgrade (MANDATORY)**: this skill requires aliyun CLI >= 3.3.3 (plugin subsystem). Verify with `aliyun version`; upgrade the CLI via `brew upgrade aliyun-cli` (macOS) or the platform installer in [references/cli-installation-guide.md](references/cli-installation-guide.md); keep plugins current via `aliyun plugin upgrade --name <plugin>` (eflo-controller / vpc / ecs / bssopenapi / ram / sts).

Required by `lib/` runtime and `scripts/`:

| Dependency | Purpose |
|---|---|
| bash ≥ 4 | all `lib/` and `workflows/*/lib/` scripts |
| aliyun CLI >= 3.3.3 (plugin mode) with plugins: eflo-controller, vpc, ecs, bssopenapi, ram, sts | API calls |
| jq ≥ 1.6 | envelope / response parsing |
| openssl (uuidgen fallback) | Observability session-id generation |
| rsync | `scripts/sync-to-skills.sh` (dev-time sync to skill install dirs) |

## References

| Document | Content |
|------|------|
| [envelope-protocol.md](references/envelope-protocol.md) | R2 envelope pass-through full protocol |
| [detailed-rules.md](references/detailed-rules.md) | Hard rules detailed explanation with counter-examples |
| [error-codes.md](references/error-codes.md) | eflo-controller error codes |
| [edge-cases.md](references/edge-cases.md) | Edge case handling |
| [supported-regions.md](references/supported-regions.md) | Region code full table |
| [workflows/README.md](workflows/README.md) | extend-cluster / shrink-cluster / create-node-group / update-node-group / change-node-group schema index |
