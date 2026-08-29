# Integration Management

> This file builds on [SKILL.md](../SKILL.md) and the shared onboarding rules in [integration-common.md](integration-common.md) — region confirmation, write confirmation, pagination, and error handling are not repeated. Flag lists and body envelopes come from `--help` (once per subcommand per session). `dropMetrics` is a string, one metric name per line — not a JSON array; draft names from `aliyun cms2 integration addon-release get` config. Catalog `aliyun cms2 integration addon get` is not required for this write — do not send its `addon.version` as `addonVersion`. **This file is the authority** for the metric-drop (`dropMetrics`) workflow on cluster probe `metric-agent` (discover via `aliyun cms2 integration collector list`, pin `addonVersion`, merge/replace/clear the list) and for CMS resource tags (`aliyun cms2 tag`: intent, system-tag policy, and landing checks).

Use this module for runtime operations that are not part of initial onboarding: metric drop on an **already-onboarded** integration policy; add / change / remove tags on specified CMS resources.

## Metric Drop

### Scope

Trigger when the user asks to drop, discard, or deprecate scrape metrics on an integration policy (指标废弃 / metric drop), to inspect the current drop list, or to set / change `dropMetrics`.

Supported when `aliyun cms2 integration collector list --collector-type ClusterCollector` has a `metric-agent` row: CS, ECS (one per VPC), and System (cloud-service probe). RDS / Cloud user policies typically have no collectors → not supported.

**Out-of-scope**: initial onboarding; changing other probe switches unless the user named those too; writing `dropMetrics` onto an entry addon or a fan-out child.

### Support gate (hard requirement)

Metric drop is configured **only** on the probe `metric-agent`.

1. Resolve the policy (id, exact name, CS `aliyun cms2 integration policy list --policy-type CS --bind-resource-id`, or ECS `aliyun cms2 integration policy list --policy-type ECS`). Uncertain → ask. User-stated **id**: `aliyun cms2 integration policy get` — do not require a workspace.
2. `aliyun cms2 integration policy get` → `.data.policy.regionId` is `--region` for every later call. 400 `The integration policy is not exist` → no policy; stop.
3. `aliyun cms2 integration collector list --collector-type ClusterCollector` for that policy (flags from `--help`).
4. Pick by `collectorName`: `metric-agent` only. CS ClusterCollector lists also `entity-collector` and `loongcollector` (the latter may have null `releaseName`). Read `releaseName` from the metric-agent row (fields from `aliyun cms2 integration collector list --help`). Never build it from policy id, vpc id, or workspace name.
5. **No `metric-agent` row** — zero rows, omitted `collectors`, or only other names (`entity-collector` / `loongcollector`) — → this policy does **not** support metric drop. Stop. That is not `QueryFailed`. A non-empty ClusterCollector list is not by itself support.
6. **Several** `metric-agent` rows (ECS: one per VPC) → present as a choice. If the user named a VPC, keep the row whose `releaseName` contains that `vpcId`.

This write targets that collector `releaseName`. Keywords are `HideReleaseName:true`, not `GroupMode:true` — do not refuse this update because the policy's **entry** addon is GroupMode, and do not put `dropMetrics` under `values.addons`. `--region` equals the policy's `regionId` (metric-agent has no `Feature:CrossRegion`). For the general rule see [Addon Release Region Requirement](integration-common.md#addon-release-region-requirement-hard-pre-check).

### Input

| Parameter | Required | How to obtain |
|-----------|----------|---------------|
| Region | Yes | [Region Confirmation Gate](../SKILL.md#region-confirmation-gate-hard-requirement), then policy `regionId` |
| Workspace | Only to resolve a policy by list | Skip when the user already gave a `policyId` |
| Policy | Yes | `aliyun cms2 integration policy get` / exact `aliyun cms2 integration policy list` name / CS bind / ECS type |
| Metric names | When setting or adding | User-named names. Never invent. Not required to inspect or to clear |

### `dropMetrics`

The value is a string (one name per line), not an array. Draft names from this release's config; never paste a body recorded for another `envType`.

- Trim each line; skip empty lines.
- Sent value is the **full** post-write list. Show the live list in the confirmation when config parsed to an object that has the key.
  - Bare list, or "drop only these" / 改为只丢弃 → replace.
  - Add / 再加上 → merge, unique, keep existing order then append.
  - Clear the drop list / 取消废弃 → `""`.
  - Inspect only → get, report, no write.
- Do not send a JSON array of names.

### 1. Live release

`aliyun cms2 integration addon-release get` that collector `releaseName` (flags from `--help`). Read `release.envType`, `release.version`, and `.data.config`.

- Body `addonVersion` is get's **`version`** (`release.version`), not a catalog `addon.version` from `aliyun cms2 integration addon get` (`--version` defaults to latest). Sending a newer catalog version **upgrades** the probe — do not unless the user asked.
- Draft `values` from `.data.config` (same string as `.release.config` when `haveConfig` is true): missing, `null`, or `""` → `{}` (`fromjson` of `""` fails). If it is a JSON object string, `fromjson` it. Do not fill schema `defaultValue`s into an empty draft.

### 2. Compose `values`

Set `dropMetrics` on the draft. Keep every other key already in that object. `jq -c` the **whole** object into `values` (wholesale: a subset that names only `dropMetrics` drops every omitted **stored** key). Reject dotted keys at any depth. Validate the outer body with `jq`.

This workflow **overrides** "settings change sends `values` by itself": `--body` is pinned `addonVersion` **and** `values`. Do not send `entityRules`.

### 3. Write

Write confirmation: policy id/name, `policyType`, `releaseName`, `envType`, pinned `release.version`, current vs proposed `dropMetrics`. Wait for a clear affirmative.

`aliyun cms2 integration addon-release update` that collector `releaseName` (flags from `--help`). `--body`:

```json
{
  "addonVersion": "<release.version>",
  "values": "<jq -c of draft with dropMetrics set>"
}
```

`values` is a JSON **string**, not an object (`--show-schema`).

### 4. Verify

Same `aliyun cms2 integration addon-release get`. Landed means `.data.config` `fromjson`s to an object whose `dropMetrics` equals the string you sent (line set after trim). `""` config after the write is **not** landed. `Loaded` / `Success` / `Ready` is not evidence. Emit config only as `jq -c` over the parse.

---

## CMS Resource Tags

### Scope

Trigger when the user asks to add / change / remove tags on a specified CMS resource ("打标签" / "修改标签" / "删除标签"), or to inspect tags on one.

**Out-of-scope**: onboarding tag filters ([Tag Match Modes](integration-common.md#tag-match-modes) / `entityRules.tags`); tagging non-CMS products; Prometheus cluster (`prometheuscluster`).

Flags, typical `resourceType` tokens, `--tag` JSON shape, and bind / unbind / list envelopes: this session's `aliyun cms2 tag --help` and the subcommand `--help`. `--region` is the target's `regionId` ([Region Confirmation Gate](../SKILL.md#region-confirmation-gate-hard-requirement)); do not pass `controlRegionId`.

### 1. Resolve

Map user wording onto a typical token from `--help`, then the matching get/list. User-stated **id** → get; do not require a workspace the command does not need. Missing → stop. Uncertain type → ask with the help typical list. `--resource-id` may repeat (cap from `--help`). Different type or region → separate calls.

Intent, if unclear → ask:

| Intent | Command |
|--------|---------|
| Inspect | `aliyun cms2 tag list` — no write. Pass `--resource-id` for that object. Paginate |
| Add, or change a key's **value** | `aliyun cms2 tag bind` — same key overwrites |
| Remove keys | `aliyun cms2 tag unbind --tag-key` |
| Rename a key | `aliyun cms2 tag unbind` the old key, then `aliyun cms2 tag bind` the new pair |

Do not treat "modify" as delete-all-and-rebind. Do not unbind keys the user did not name. Never invent keys.

System tags (`acs:rm:rgId` = this object's resource group; `acs:arms:prometheusName` on Prometheus instances): the Tag API rejects writes (`custom tag key pattern is invalid`). Even if the user named them → stop and say they cannot be changed. Exclude from any unbind set. Do not read them as onboarding / monitored scope. `acs:rm:rgId` is on resource get, not on `tag list`.

"Remove all tags" with no keys → `aliyun cms2 tag list` first, drop system keys, confirm, then `aliyun cms2 tag unbind --tag-key`. Do not use `--all` for that: with system tags present the API rejects it (`The specified tagKeys is not valid`) and custom tags stay.

### 2. Write

Confirm type, id, command, and the tag pairs or keys; wait for a clear affirmative. Compose `--tag` / `--tag-key` from `--help`. Reject system keys.

### 3. Verify

`success: true` / `requestId` is **not** landed. Re-read the same object with `aliyun cms2 tag list`. Bind landed = every sent pair is present. Unbind landed = those keys are absent. Remaining system tags are expected. Get/list success / omitting tags / a different object is **not** evidence.
