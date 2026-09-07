---
name: alibabacloud-lingjun-cluster-manage
description: |
  What it does: manages Alibaba Cloud Lingjun cluster lifecycle via eflo-controller CLI — create / list / describe / delete clusters, list nodes, query machine types & images, tag / untag / list tags, change resource group.
  When to use it: when the user asks to create, query or delete a Lingjun cluster, list clusters or nodes, look up machine types or images, manage cluster tags, or change its resource group.
  Run: bash prefix: export LJ_SKILL_DIR="${LJ_SKILL_DIR:-$HOME/.qoder/skills/alibabacloud-lingjun-cluster-manage}" && source "$LJ_SKILL_DIR/lib/lj_init.sh"; i18n: CJK ratio 0.30+ → LJ_LANG=zh else en; stdout (skip ===...=== envelope blocks) is final reply; __LJ_EXEC__ or [Widget interaction] prefix → confirmed → one && chain.
  Triggers: "lingjun cluster", "灵骏集群", "create cluster", "创建集群", "delete cluster", "删集群", "list clusters", "describe cluster", "查集群", "machine type", "机型", "image", "镜像", "tag", "打标", "untag", "解标", "查标", "resource group", "资源组", "移资源组", "改资源组", "GPU", "CUDA", "集群管理", "cluster lifecycle"
---

# Alibaba Cloud Lingjun Cluster Manage

> Full rules / counter-examples / tutorials → [references/](references/) *.md (deep-read on demand, not on load path)

## When to Use

Activate this skill when user:
- Creates, queries, or deletes Lingjun clusters
- Queries machine types or OS images
- Tags / untags / lists tags for cluster resources
- Migrates cluster to a different resource group
- Queries async task status

Scope boundary: cluster-level lifecycle only. Node group management (create / query / update / delete node group), cluster scaling, node purchase/release, and hyper-node management belong to `alibabacloud-lingjun-cluster-scaling` (see [Out of Scope](#out-of-scope)).

## Routing

```text
User intent?
├─ Create cluster (3-round flow)
│  ├─ R1: cluster_create_form --region <R> → markdown form: name/HPN/VPC/machine-type/image/keypair/disk/switches in ONE user reply
│  ├─ R2: cluster_create_form --region <R> --step 2 --vpc-id <V> → vSwitch + security group pick
│  └─ R3: cluster_create_submit <all params> → confirmation table → user replies 确认 → safe_mutate_confirm <hash from ===MUTATE_HASH=== block> → receipt, then query task on demand
│     (widget ONLY on explicit visual-form request → cluster_create_form_widget → MCP genui.show_widget; legacy fields)
├─ Query (cluster / node / machine type / image / tag / task)
│  └─ bash-first: query <region> <subcommand>
├─ Delete cluster
│  └─ bash-first: safe_mutate_oneshot delete-cluster
├─ Tag resources
│  └─ bash-first: safe_mutate_oneshot tag-resources
├─ Untag resources
│  └─ bash-first: safe_mutate_oneshot untag-resources
├─ Change resource group
│  └─ bash-first: safe_mutate_oneshot change-resource-group
└─ Uncertain
   └─ HITL: ask user intent
```

## Hard Rules (L0-L11)

| # | Rule Summary |
|---|----------|
| L0 | forbidden_inference: VpcId/VSwitchId/SecurityGroupId/ImageId/KeyPairName/Hostname/LoginPassword **NEVER** LLM-guessed — user picks from prefetched dropdown lists (create form) or provides the value explicitly |
| L1 | Backfill = confirm: user backfills params → treat as confirmed, execute directly |
| L2 | Intent-to-action unique mapping: user business term → single action, cross-action strictly forbidden |
| L3 | No meta-narrative: forbid "let me first…" / "initializing skill"; internal terms must never appear in chat |
| L4 | No TodoWrite: ZERO-TOLERANCE |
| L5 | i18n language detection: each turn CJK ratio check → inject LJ_LANG prefix |
| L6 | Region must be user-specified: **NEVER** default to cn-hangzhou / cn-beijing. Conversely there is **no client-side region whitelist and no region lock** — pass through whatever region the user names (incl. overseas / newly launched ones) and let the API answer; switching region mid-conversation is always allowed. A region named in words (`迪拜`, `Dubai`, `新加坡`…) **counts as user-specified**: resolve it via the Region mapping line below and proceed — do **not** ask the user to restate it as a region id (they already named it), and do **not** invent an id by pattern-guessing (`迪拜` → `me-central-1` is a real, observed mis-guess; the correct id is `me-east-1`) |
| L7 | Zero narrative around widget: no preamble before MCP call; only one sentence reply after |
| L8 | Pagination exhaustion: all `list-*` must page until NextToken empty (soft cap 50 pages) |
| L9 | Mutating operations require explicit user confirmation before execution |
| L10 | No self-rescue on failure: if a skill command errors (e.g. command not found / non-zero rc), report the stderr to the user verbatim and stop — NEVER grep/read/source lib internals in-session to reverse-engineer a workaround; retry at most once only when stderr itself instructs a parameter fix |
| L11 | Never ask for create-cluster params empty-handed: the moment a create-cluster intent lands without the full flag set, run `cluster_create_form --region <R>` (then `--step 2 --vpc-id <V>` once the VPC is chosen) FIRST and ask on top of the candidate lists it prints. Listing the missing field names from memory — without the form call — violates L0, because the user has no ids to pick from |

## Workflows

| Intent | First Action | Notes |
|------|----------|------|
| Query | `query <region> <subcommand> [args]` | stdout is markdown table direct output |
| Create cluster | R1 `cluster_create_form --region <R>` → R2 `cluster_create_form --region <R> --step 2 --vpc-id <V>` → R3 `cluster_create_submit …` (full flag list below) | Each stdout is the reply verbatim. R3 prints confirmation table + hash in skip block; after user replies `确认` → `safe_mutate_confirm <hash>` → reply receipt (see Task Monitoring), NO auto polling. Platform defaults (Lite/cloud_essd/ipv4/CloudLinkCidr/IgnoreFailedNodeTasks) are hardcoded in submit — never pass them manually. Empty VPC/vSwitch/SG/KeyPair → form prints console guidance, stop. R1 is not skippable when params are incomplete (L11); it *is* skipped only when the user already handed over every flag in the list below — then go straight to R3 (L1) |
| Delete cluster | `safe_mutate_oneshot delete-cluster aliyun eflo-controller delete-cluster --region <R> --cluster-id <C>` | Sync — no polling; verify with cluster-list / describe-cluster (expect RESOURCE_NOT_FOUND) |
| Tag resources | `safe_mutate_oneshot tag-resources aliyun eflo-controller tag-resources --region <R> --biz-region-id <R> --resource-id <C> --resource-type Cluster --tag Key=<K> Value=<V>` | Sync |
| Untag resources | `safe_mutate_oneshot untag-resources aliyun eflo-controller untag-resources --region <R> --biz-region-id <R> --resource-id <C> --resource-type Cluster --tag-key <K>` | Sync; `--tag-key` and `--all` are mutually exclusive. Removing every tag needs an explicit boolean value — `--all true`, never a bare `--all` (the CLI would swallow the next flag as its value) |
| Change resource group | `safe_mutate_oneshot change-resource-group aliyun eflo-controller change-resource-group --region <R> --resource-region-id <R> --resource-id <C> --resource-type Cluster --resource-group-id <G>` | Sync; `--resource-type` must be `Cluster` (capital C) — lowercase `cluster` returns generic HTTP 400 `SystemError` |

**Region mapping** (translation aid only — *not* a supported-region list; any region id the user gives is passed through as-is): `乌兰察布=cn-wulanchabu` / `上海=cn-shanghai` / `北京=cn-beijing` / `杭州=cn-hangzhou` / `深圳=cn-shenzhen` / `张家口=cn-zhangjiakou` / `宁夏=cn-ningxia` / `香港=cn-hongkong` / `新加坡=ap-southeast-1` / `东京=ap-northeast-1` / `法兰克福=eu-central-1` / **`迪拜=阿联酋=me-east-1`** (NOT `me-central-1` — that id does not exist here) / more pairs → [references/endpoint-and-regions.md](references/endpoint-and-regions.md). Overseas names are listed inline on purpose: guessing an id the user never typed is worse than a wrong lookup, and this line has to be enough on its own.

**`cluster_create_submit` full flag list** — copy flag names exactly; every flag is `--kebab-case`, no abbreviations:

```bash
cluster_create_submit \
  --region <R> \
  --cluster-name <N> \
  --hpn-zone <H> \
  --vpc-id <V> \
  --vswitch-id <VSW> \
  --security-group-id <SG> \
  --machine-type <MT> \
  --image-id <IMG> \
  --key-pair-name <KP> \
  --node-group-name <NG> \
  --disk-size <GB>
# optional: --disk-pl PL0|PL1  --open-eni-jumbo-frame  --fs-mount  --vgpu true
# optional: --cli-dry-run  (validation only, see Dry-run mode)
```

**Strictly forbidden** (applies to all actions): self-querying aliyun API / self-rendering after calling safe_aliyun / re-formatting stdout / wrapping markdown tables in ``` code blocks

## Query Reference

```bash
source "$LJ_SKILL_DIR/lib/lj_init.sh" && query <region> <subcommand> [args]
```

| User Intent | Subcommand | Args |
|----------|--------|------|
| List clusters | cluster-list | — |
| Describe cluster | cluster-describe | cluster-id |
| List cluster nodes | cluster-nodes | cluster-id |
| Machine types | machine-types | — |
| Images | images | — |
| List tags | tag-list | [--resource-type type] [--resource-id id] |
| Task status | task | task-id |

## Mutating Reference

All mutating operations use `safe_mutate_oneshot`:

```bash
source "$LJ_SKILL_DIR/lib/lj_init.sh" && safe_mutate_oneshot <action> [--intent "<user words>"] aliyun eflo-controller <action> --region <R> [args]
```

| Action | CLI Action | Async | Notes |
|--------|-----------|-------|-------|
| Create cluster | `create-cluster` | Yes | 3-round markdown form (see Workflows) → `cluster_create_submit` builds JSON with hardcoded platform defaults → user replies `确认` → `safe_mutate_confirm <hash>` → receipt + on-demand query. Widget entry `cluster_create_form_widget` is legacy, explicit request only |
| Delete cluster | `delete-cluster` | No | ⚠️ Irreversible. Sync — returns RequestId, deletion effective immediately; verify via describe-cluster → RESOURCE_NOT_FOUND |
| Tag resources | `tag-resources` | No | `--biz-region-id <R> --resource-type Cluster --tag Key=<K> Value=<V>` |
| Untag resources | `untag-resources` | No | `--biz-region-id <R>` required; `--tag-key` and `--all` mutually exclusive; `--all` must carry an explicit value (`--all true`) |
| Change resource group | `change-resource-group` | No | `--resource-region-id <R> --resource-type Cluster --resource-group-id G` (capital-C `Cluster`; lowercase `cluster` returns SystemError) |

**Dry-run mode** — only when the user explicitly asks for a `--cli-dry-run` validation: keep the exact same path and confirmation gate, just append `--cli-dry-run` at the end of the command. `safe_mutate_oneshot <action> aliyun eflo-controller <action> … --cli-dry-run` for the four sync actions; `cluster_create_submit … --cli-dry-run` for create (the flag is passed straight through to the CLI, so the following `safe_mutate_confirm <hash>` is what actually prints the request body). The CLI then prints `DRY-RUN MODE: Request Details`, `API Action: <PascalCase>`, the `Body:`/`Query Parameters:` payload and `Request NOT sent (dry-run mode)` with exit code 0 — nothing is created / deleted / tagged / moved. Verified on aliyun CLI 3.3.10.

## Task Monitoring (receipt + on-demand query)

Async mutating (create-cluster only) returns TaskId. **NO automatic polling** — simple & reliable:

1. **Receipt first**: right after submit succeeds, reply with a markdown receipt table — Operation / ClusterId (if any) / TaskId / RequestId / estimated duration (~1 min without nodes, a few minutes with nodes) — plus one closing line (zh-session canonical wording, render verbatim): `可随时对我说“查一下任务进度”。`
2. **On-demand query**: when user asks progress → `query <region> task <tid>` (stdout verbatim; after terminal state, optionally run `query <region> cluster-describe <cid>` to verify OperatingState).
3. `poll_task <region> <tid>` is **opt-in only**: use solely when user explicitly asks to wait/watch until the task finishes.

## Observability

All `aliyun` API calls issued through `safe_aliyun` (and therefore `query` / `safe_mutate_*` / `poll_task`) automatically append a unified User-Agent flag:

`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-lingjun-cluster-manage/{session-id}`

session-id rules (generated by `lib/lj_init.sh` as `LJ_SESSION_ID`, consumed via `LJ_USER_AGENT`):
- Format: `lj-<UTC yyyymmddHHMMSS>-<pid>-<4-hex random>` (e.g. `lj-20260825073000-12345-a1b2`); generated once per conversation session on first `source` of `lj_init.sh`.
- All CLI calls within one session share the same session-id so backend audit logs can correlate the whole operation chain.
- Never hardcode or reuse a stale value; a fresh `source` regenerates it when unset.
- The legacy persistent UA configuration mechanism (ai-mode) is deprecated and no longer used.

## Prerequisites

- bash 3.2+ with coreutils (`date`, `stat`, `shasum`/`sha256sum`)
- aliyun CLI 3.3.3+ — the `eflo-controller` plugin is installed automatically by `lib/lj_init.sh` on first source (non-interactive; the CLI's own prompt would hang in a no-tty sandbox). See [cli-installation.md](references/cli-installation.md)
- eflo-controller API version is **not** pinned — the CLI default is used. Where a CLI build's parameter schema disagrees with the request body (`unknown field: X` on `--networks` / `--node-groups`, raised during *local* validation, so nothing is sent), `safe_aliyun` strips that field and replays automatically; the fields in question are platform defaults, so dropping them does not change semantics
- `jq` 1.6+ (JSON parsing in lib / workflows). `python3` is an optional second engine for the schema-strip fallback above — either one suffices
- `rsync` (only for the dev-only utility `scripts/sync-to-skills.sh`)
- Credentials configured and RAM policies attached per [ram-policies.md](references/ram-policies.md)

## References

| Document | Content |
|------|------|
| [cli-installation.md](references/cli-installation.md) | CLI installation & authentication |
| [endpoint-and-regions.md](references/endpoint-and-regions.md) | Endpoint routing + region id reference |
| [ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [async-task-monitoring.md](references/async-task-monitoring.md) | Async task polling contract |
| [error-codes.md](references/error-codes.md) | eflo-controller error codes |

## Out of Scope

This skill does **not** cover:
- Cluster scaling (`extend-cluster` / `shrink-cluster`)
- Node purchase / release / migration (`CreateInstance` / `DeleteNode` / `ChangeNodeGroup`)
- Node group management (`create-node-group` / `list-node-groups` / `update-node-group` / `delete-node-group`)
- Hyper-node management (HyperNode)

These belong to `alibabacloud-lingjun-cluster-scaling` skill.
