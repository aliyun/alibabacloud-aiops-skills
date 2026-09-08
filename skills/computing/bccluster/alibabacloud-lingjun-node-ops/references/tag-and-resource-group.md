# Feature 9 - Tag & Resource Group

Lingjun node metadata management: 4 synchronous APIs, all returning `RequestId`, **no TaskId**, **no async polling**, but single-step confirmation is still **mandatory** (parameter confirmation table + user replies the confirmation word - see `render.confirm_word` in `lib/core/i18n.sh` - within the same message).

| Sub-capability | API | Category |
|---|---|---|
| 9.1 Add tags | `tag-resources` | synchronous |
| 9.2 Remove tags | `untag-resources` | synchronous |
| 9.3 List tags | `list-tag-resources` | synchronous read-only |
| 9.4 Move resource group | `change-resource-group` | synchronous |

`ResourceType` values (**case-sensitive**, determined by the server-side contract):

| Resource | ResourceType |
|---|---|
| regular node | `node` |
| cluster | `cluster` |
| hyper node | `Hypernode` |

> Any spelling deviation (e.g. `Node` / `HyperNode` / `hypernode`) is rejected by the server; the Agent must pass values strictly per this table.
>
> [WARN] **Exception: the ResourceType contract of 9.4 `change-resource-group` differs from the tag APIs** - regular nodes must pass `Node` (capitalized); passing `node` / `instance` yields a generic HTTP 400 `SystemError`, and omitting it yields `ResourceNotFound`. Verified on me-east-1 (2026-08-24).

---

## 9.1 `tag-resources` - add tags to nodes

### Required

- `--region` / `--endpoint`
- `--biz-region-id <region>` - **business-side region**, must equal `--region`
- `--resource-type <node|cluster|Hypernode>`
- `--resource-id <id1> [<id2> ...]` - at least 1, at most 50
- `--tag Key=<k> Value=<v>` - at least 1 pair; repeat `--tag` for multiple pairs

### Workflow

1. HITL pick the target nodes / clusters / hyper nodes
2. HITL collect K-V pairs (`Key` length 1-128, `Value` length 0-128, both case-sensitive)
3. Parameter confirmation table + user replies the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`, same step); after confirmation, submit via `safe_mutate_oneshot`
4. Submit -> record `RequestId`
5. Verify: `list-tag-resources --resource-id <ids>` returns `Tags[]` containing all new K-V pairs

### Example invocation

```bash
safe_aliyun aliyun eflo-controller tag-resources \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --biz-region-id <region> \
  --resource-type node \
  --resource-id e01-cn-xxxx e01-cn-yyyy \
  --tag Key=env Value=prod --tag Key=team Value=ai
```

---

## 9.2 `untag-resources` - remove tags from nodes

### Required

- `--region` / `--endpoint`
- `--biz-region-id <region>`
- `--resource-type <node|cluster|Hypernode>`
- `--resource-id <id1> [<id2> ...]`
- `--tag-key <k1> [<k2> ...]` or `--all true` (mutually exclusive)

### Mutual-exclusion rule (hard)

- Pick **exactly one**: either explicit `--tag-key` list, or `--all=true`
- `--all=true` only takes effect when `--tag-key` is **completely omitted**; passing both -> the server ignores `--all`
- To prevent accidents, this Skill defaults to `--tag-key`; `--all=true` must be explicitly chosen by the user in HITL with an extra second warning

### Example invocation

```bash
safe_aliyun aliyun eflo-controller untag-resources \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --biz-region-id <region> \
  --resource-type node --resource-id e01-cn-xxxx \
  --tag-key env team
```

---

## 9.3 `list-tag-resources` - list tags (read-only)

### Required

- `--region` / `--endpoint`
- `--biz-region-id <region>`
- `--resource-type <node|cluster|Hypernode>`

### Optional

- `--resource-id <id1> ...` - filter by resource
- `--tag Key=<k> Value=<v>` - filter by K-V
- `--max-results <int>` / `--next-token <str>` - pagination

### Purpose

The **only trustworthy verification means** after submitting `tag-resources` / `untag-resources`. Do not use the `Tags` field of other APIs (e.g. `describe-node`) for verification - their response structures may not refresh in sync.

---

## 9.4 `change-resource-group` - move resource group (RAM scope)

### Required

- `--region` / `--endpoint`
- `--resource-region-id <region>` - must equal `--region`
- `--resource-type <Node|cluster|Hypernode>` - **note: for this API, regular nodes take `Node` (capitalized), unlike the tag APIs' `node`**
- `--resource-id <id>`
- `--resource-group-id <new-rgid>` - `forbidden_inference`; **must** go through HITL and **must** be obtained from `aliyun resourcemanager list-resource-groups`

### Workflow

1. `aliyun resourcemanager list-resource-groups` (note: this is the central ResourceManager API, not eflo-controller) -> list every RG under the current account
2. HITL: user picks `--resource-group-id` from the real list
3. Parameter confirmation table + user replies the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`, same step); after confirmation, submit via `safe_mutate_oneshot`
4. Submit -> record `RequestId`
5. Verify: `describe-node --node-id <id>` returns `ResourceGroupId == the new rgid`

### Example invocation

```bash
safe_aliyun aliyun eflo-controller change-resource-group \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --resource-region-id <region> \
  --resource-type Node \
  --resource-id e01-cn-xxxx \
  --resource-group-id rg-aekzxxxxxxx
```

### `ResourceGroupId` `forbidden_inference` hard rule

The LLM is **strictly forbidden** to:
- reuse the previous turn's `describe-node.ResourceGroupId` (the user may want exactly to move away from it)
- auto-reuse a cluster / node-group ResourceGroupId
- compose / fabricate an `rg-aek...` string

Any auto-fill = Skill self-violation V3; abort immediately and discard all collected parameters.

---

## Verification Cheat Sheet

| Sub-capability | Verification API | Pass criteria |
|---|---|---|
| 9.1 tag-resources | `list-tag-resources` | `Tags[]` contains all new K-V pairs |
| 9.2 untag-resources | `list-tag-resources` | `Tags[]` no longer contains the removed Keys |
| 9.3 list-tag-resources | (self-verifying) | exhaust pagination until `NextToken` is empty |
| 9.4 change-resource-group | `describe-node` | `ResourceGroupId == target rgid` |
