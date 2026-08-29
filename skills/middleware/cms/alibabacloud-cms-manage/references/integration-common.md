# Integration Common Rules

> This file builds on the global conventions in [SKILL.md](../SKILL.md) — output format, pagination, error handling, write confirmation, output language, and the glossary. They are not repeated here. Flag lists, body envelopes, tag `op` enums, status derivation, and delete target priority come from `aliyun cms2 <command> --help` / `--show-schema` / `--show-example-body` (read once per subcommand per session). A named subcommand's help is the authority for that command's flags, body envelope, response fields, and environment behaviour — do not search other skill files for a copy of those fields. This file is the authority where help is silent or wrong: gates, `--env-type`, fan-out, and writes that contradict `--help`.

> **Every command in this document is a `aliyun cms2` subcommand.** Commands are always written with their full `aliyun cms2 ...` form; never invoke a bare `integration`, `entity`, `policy`, `addon`, `addon-release`, `collector`, `workspace`, `resource-group`, `tag`, `meta`, `metric`, or `aliyun-service` command, and never substitute another CLI.

> Answer from this file instead of keyword-searching other files for a definition: terms here have look-alikes elsewhere, such as the tag match `op` of [Tag Match Modes](#tag-match-modes) versus the APM alert `filterList[].type` owned by [alerting.md](alerting.md).

## General Conventions

- **When `-o json` is required** (refining [Prefer `-o text`](../SKILL.md#global-conventions)): use `-o json` whenever the output is parsed field by field instead of read — addon schemas (`defaultValue`/`fieldPath`), and any `aliyun cms2 entity query` whose `instance_id`/`instance_name`/`region_id`/`status` feed a later command. Column-parsing a text table costs more turns than the JSON costs tokens.
- **Onboarding exceptions to [Uncertain parameters](../SKILL.md#global-conventions)**: (1) region scope for `aliyun cms2 entity query --source CloudResource` follows [CloudResource Query Region Handling](#cloudresource-query-region-handling); (2) addon selection follows [Addon Selection Gate](#addon-selection-gate-hard-requirement); (3) policy name follows [Policy Name Defaulting](#policy-name-defaulting-hard-requirement). Never fabricate or guess values outside these exceptions.
- **Workspace must be explicitly selected** before policy or addon-release creation, per [Workspace Selection Gate](#workspace-selection-gate-hard-requirement).
- **Before onboarding concrete resource IDs**, verify them per [Resource Identity Verification](#resource-identity-verification).
- **`aliyun cms2 entity query` time range**: always pass `--from`/`--to` (Unix seconds); default last 7 days when the user does not specify. Compute the pair once per task with `date` and reuse it.
- **`--sql` region injection, columnar `header`/`data` JSON, no `stats`, and `project` before `limit`**: `aliyun cms2 entity query --help`. Under `--sql`, write `where region_id = '<region>'` yourself — do not rely on `--region`. `--entity-type` mode still uses the flag as a filter.
- **Map columns by header** after every `--source CloudResource` call. `__entity_id__` vs `instance_id` disambiguation is in `aliyun cms2 entity query --help`. Use `instance_id` as the cloud resource ID.

## Metadata Query Mapping

| What You Need | How to Get It |
|--------------|---------------|
| Resource metadata & instance details | `aliyun cms2 entity query --source CloudResource` |
| Entity data ingested into a workspace (proves ingestion, not current onboarding) | `aliyun cms2 entity query --source EntityStore` |
| Authoritative addon onboarding status | [Determining Onboarding & Monitoring Status](#determining-onboarding--monitoring-status) |
| Policy-scoped Kubernetes resources | `aliyun cms2 integration resource list --policy-id <policyId> --kind <Kind>`; never `aliyun cms2 entity query --source CloudResource --entity-type acs.k8s.namespace`. No policy → report the missing `policyId`, do not fabricate one |
| Existing tag keys on a resource type | Distinct keys from CloudResource `tags` JSON on sampled rows of that entity type. Do not use `aliyun cms2 tag list` here: it tags CMS product resources (`--resource-type` / `--resource-id`, flags from `--help`) and does not list ECS/cloud-product ARNs |
| Prometheus instance for addon release | `aliyun cms2 integration storage list --policy-id --addon-release-name --storage-type Prometheus` |

---

## Determining Onboarding & Monitoring Status

Do NOT treat the following as proof of onboarding:

- CloudResource exists → only proves the cloud resource exists.
- EntityStore has an entity → only proves that data was once ingested.
- Policy exists → only proves a resource scope is bound.

A policy with a healthy release still does not prove a given resource is covered — judge coverage from that release's scope.

| Step | Action |
|------|--------|
| 1. Identify addons | Resource type → `aliyun cms2 integration addon list --entity-type <entityType>`; instance ID → `aliyun cms2 entity query --source CloudResource` to resolve the type first. This is Step 0 of the [Addon Selection Gate](#addon-selection-gate-hard-requirement) — run the whole gate before using any `addonName`. |
| 2. Find candidate policies | `aliyun cms2 integration policy list --addon-name <addonName>`. ACK/CS: `--policy-type CS --bind-resource-id <clusterId>` (see [Policy Lookup Rules](#policy-lookup-rules)). Cloud sub-types: `--addon-name` is primary; verify each policy with a target release before counting as evidence. |
| 3. Check addon releases | `aliyun cms2 integration addon-release list --policy-id <policyId>` per policy, **without** `--addon-name`: an entry addon fans out one release per enabled child, and filtering by the entry name leaves every child unverified. Group by `parentAddonReleaseId` — one group per entry release, since a policy can hold several with different scopes — and evaluate the entry addon together with its children. CS/ACK children leave that field empty; there the children are every non-entry release under the policy. Cloud children also leave it empty even while the entry exists, so that field cannot split generations after an entry update: previous children stay listed, and a leftover of a closed child is not present — isolate per [Addon Release Config Update](#addon-release-config-update-hard-requirement). |
| 4. Collector status | CS/ECS: `aliyun cms2 integration collector list --policy-id --collector-type ClusterCollector`. ECS additionally: NodeCollector when the addon requires node-level collection. Cloud: skip. |

**Step 3 scope.** The monitored scope lives on the release, not on the policy. A policy's `entityGroup` is populated only for CS cluster binding (`clusterId`) and cross-account (`entityUserId`) — on ECS and Cloud it is normally `{}`. Its `resourceGroupId` and `acs:rm:rgId` tag describe where the policy object sits in Resource Management; reading either as the monitored scope narrows an audit to the wrong set.

| Condition | Scope Logic |
|-----------|-------------|
| `policyType == Default` | Release status directly reflects onboarding status |
| Non-Default, has `parentAddonReleaseId` | A child covers what its own `entityRules` says, same as its entry release. Collect siblings by grouping the unfiltered list on `parentAddonReleaseId`: `aliyun cms2 integration addon-release list --parent-addon-release-id <id>` comes back empty for ECS and Cloud fan-outs, and that empty result is not evidence of zero coverage |
| Non-Default, no parent | Scope comes from the release's `entityRules.entityRules` (`regionIds`, `instanceIds`, `resourceGroupId`, `tags`) and `entityRules.entityQueries[].spl`. Cloud: healthy release + scope is primary evidence; CS: the bound cluster is the scope. A release can carry no `entityRules` at all (CS/ACK, some Cloud log addons) — never read that as covering everything; fall back to the policy's bound resource and the release's children. |

**Collector health:** judge `state` and `workloads[]` against the Health state normalization table in `aliyun cms2 integration collector list --help`. CS always requires ≥1 healthy ClusterCollector. ECS requires ClusterCollector only after ≥1 release exists (no releases → `NO_RELEASE`, not missing collector). Either query can return several collectors, so judge each on its own and read the instances it covers from its `workloads[]`. ECS NodeCollector unhealthy → corresponding VPC (`{vpcId}-{policyId}`) is unhealthy.

Evaluate release status per [Rules for Determining Addon Release Status](#rules-for-determining-addon-release-status). Onboarded = required addon healthy release (Success) + required collectors healthy. Report the release status together with every collector the type requires. `-umodel` suffix addons do not count as base CloudMonitor onboarding evidence.

| Type | Verification Criteria |
|------|----------------------|
| **CS (ACK/ACS/ASI)** | Policy with `policyType=CS` + correct cluster binding; release `Success`; ≥1 healthy ClusterCollector |
| **ECS** | Policy with `policyType=ECS`; release `Success` with the intended scope in its `entityRules`; ClusterCollector healthy; NodeCollector healthy when the release set requires node-level collection |
| **Cloud (RDS/SLB/ALB etc.)** | Policy with correct `policyType`; release `Success` with the intended scope in its `entityRules`; no collectors |

### Unonboarded Resource Follow-up

When a status check identifies active resource(s) not onboarded:

- Ask whether to onboard (concrete active resources not covered by any healthy release). Do not ask for `Unknown`/`InventoryUnavailable`, historical/deleted, or audit-only requests.
- If agreed, run [Standard Onboarding](#standard-onboarding) applying all gates, then the type-specific workflow. An audit result is not a confirmed scope: run [Resource Scope Selection Gate](#resource-scope-selection-gate-hard-requirement) first, then onboard exactly that scope.

**Optional metric data-plane check** (when the user asks about queryable metrics): `aliyun cms2 integration storage list --policy-id --addon-release-name --storage-type Prometheus`, then `aliyun cms2 metric promql labels`/`series`/`query` with `--prometheus-id` from `status.instanceId`. Missing samples may indicate lag but do not override control-plane status.

### CloudResource Query Region Handling

Before any `aliyun cms2 entity query --source CloudResource`, determine the region scope in this order:

1. **User explicitly limited regions** → use exactly those regions.
2. **Onboarding task** → use the regions confirmed in [Resource Scope Selection Gate](#resource-scope-selection-gate-hard-requirement). Before that confirmation the only permitted query is that gate's region discovery query.
3. **A task-specific reference declares a narrower default** for a non-onboarding task (e.g. CS fleet audit defaults to a single region, recommended from the workspace's region) → that declaration wins over the all-regions default below.
4. **Otherwise** (status check, audit, ad-hoc lookup) → omit the region parameter (query all regions), and do not derive regions from workspace/policy/release/prior commands.

Always state the final region coverage.

### CloudResource Aggregation (Hard Requirement)

`aliyun cms2 entity query --source CloudResource` returns rows and has no `stats` stage: `stats <alias> = count() by <field>`, `stats count() as <alias> by <field>`, `summarize`, and `dc()` all fail. Do not spend turns hunting for a working aggregate form.

For a count or a distribution, pull the rows inside the narrowest `where` the task allows and aggregate locally. Keep the row cap explicit (`limit 0, <N>`) and paginate when the result reaches it.

**`project` before `limit`** — the order matters — drops the response to those columns, turning default `-o text` into a small CSV that `sort`/`uniq -c` can consume without `jq`. An unprojected row carries the type's full column set (34 for `acs.ack.cluster`, 44 for `acs.ecs.instance`), so a 500-row probe is roughly 50x a one-column probe.

**A truncated aggregate drops whole categories silently, so never read one as complete.** Surviving rows are whatever the backend returned first; an unfiltered `.entity with(domain='acs')` is dominated by `acs.sls.project`, `acs.ecs.eni`, and `acs.ecs.securitygroup`. Low-count categories then vanish from the distribution instead of showing a low count, which reads as "the account owns none of these". Paginate to completion or probe the category directly (`--entity-type <type>`, or `where <field> like '<prefix>%'`). If a broad distribution is unavoidable, exclude the dominant categories in `where` until the result stops reaching the cap, and state that the coverage was built that way.

---

## Onboarding Workflow

### Addon Selection Gate (Hard Requirement)

Apply after addon discovery, before any command using `addonName`. Step 0 always runs.

**Step 0 — scope the candidate set.** Rules 3 and 4 count `groupMode` candidates, and that count only means something over a scoped set: a large share of the catalog carries `GroupMode:true`, each addon for its own resource type. Build the set by entity type, then keep only the addons whose `scene` and `environments[].policyType` match the onboarding type at hand:

```bash
aliyun cms2 integration addon list --entity-type <entityType> -o json \
  | jq -r '.data.addons[] | [.name, .alias, (.scene//"-"),
      ((.keywords//[])|join("|")),
      ((.environments//[])|map("\(.name//"-"):\(.policyType//"-")")|join("/")),
      ((.weight//0)|tostring)] | @tsv'
```

Keep every projected field: `keywords` carries the `GroupMode:true` verdict, `scene` and `policyType` do the narrowing, `weight` separates an entry addon from the narrower ones beside it. Each environment prints as `name:policyType`; the `name` half is `--env-type` later. Project out of `-o json` — a text row inlines `dashboards` and `environments`, pushing `keywords` deep into a multi-KB line.

`--search <word>` is not a scope: it both misses addons whose name and keywords omit the word and admits addons bound to unrelated types. Use it only when no entity type can be resolved, and drop candidates bound elsewhere before the rules below count anything.

`--entity-type` is a catalog filter, not a complete index: an addon can declare a type in `environments[].policies.bindEntity.entityType` yet surface under neither that flag nor a `--search`. A scoped set holding exactly one addon is weak evidence — check it against the onboarding type before auto-selecting under rule 3.

Then, on the scoped set:

1. User explicitly specified → verify it is among candidates, use it.
2. Another deterministic rule uniquely identifies → use it, state evidence.
3. Exactly one candidate has `groupMode: true`, or the scoped set holds exactly one addon → auto-select, state the reason and the scope that produced it.
4. Several candidates with multiple or zero `groupMode: true` → ask user to choose.

`groupMode` is the keyword `GroupMode:true` in `addon.keywords`. There is no `groupMode` field. Do not confuse with `entityGroupMode`/`entityGroup`.

**The `groupMode` check is mandatory.** Read `keywords` for every candidate, then `aliyun cms2 integration addon get` on each `groupMode` candidate to confirm the keyword along with description, environments, and capabilities. Do not use candidate templates or run writes until the gate completes.

**Semantic fit is not a deterministic rule.** An entry addon is often categorised by the cloud service it fronts rather than by the workload it monitors, so the candidate whose `alias` and `keywords` read most on-topic can be a child of the one that should be selected. Never let it stand in for rule 2, and never let it override rule 4.

### Addon Values Defaults (Hard Requirement)

Build nested JSON for `values` from the live `aliyun cms2 integration addon get` schema. Do not fill remembered defaults for fields the user did not name. Do not describe a subset as the console's full draft.

**`--env-type` is `environments[].name`, not `policyType`.** `aliyun cms2 integration addon get --help` / `aliyun cms2 integration addon-release create --help` listing CS/ECS/Cloud is wrong. Select the `environments[]` object whose `policyType` matches the policy being created (ask if that leaves more than one). Then pass **that object's `name`** as `--env-type` and as the body's `envType`. An ECS **entry** addon is often `{name: Cloud, policyType: ECS}` (`cloud-acs-ecs`) — the flag is `Cloud`. That mapping is not global: probe `metric-agent` is `{name: ECS, policyType: ECS}` and `{name: Cloud, policyType: System}`. When updating an existing `metric-agent` release that still needs `aliyun cms2 integration addon get`, `--env-type` is the live `release.envType` (CS / ECS / Cloud), never `policyType` (`--env-type System` returns empty `.fields`) and never the entry-addon "ECS → Cloud" shortcut (that loads the System schema onto an ECS probe). Create still uses `environments[].name` — there is no `release.envType` yet. Metric drop does not run catalog `aliyun cms2 integration addon get` — `dropMetrics` type and the draft come from `aliyun cms2 integration addon-release get` per [Metric Drop](integration-management.md#metric-drop). Omitting the flag resolves as `CS` and commonly returns a `schema` holding nothing but `requestId`. Passing `policyType` often still exits 0 with a non-empty catalog that omits the `name` schema's switches. The flag scopes `schema` only; `addon.keywords`, `environments`, and `dependencies` are unaffected. Match `.data.schema.fields`; a user-named capability that hits nothing is this mistake, not "the addon has no such switch". Skill markdown does not enumerate field catalogs; grepping this repository for a key is not evidence the schema lacks it.

Read the **full** `aliyun cms2 integration addon get -o json` payload (`data.addon` beside `data.schema`; `environments[].commonSchemaRefs` already merged). Fields live in `.data.schema`. `.data.addon.schema` is null — do not parse it. An empty `.data.schema.fields` is not "the addon has no switches": typical causes are omitted `--env-type` (resolves as `CS`) or reading only `data.addon`. Two empty catalogs are genuine: a composition entry whose `schema` is only `guide` (`cloud-batch-metrics` — child fields live on each child's own get), and a true-zero-fields child (`cs-event` — `values` is `{}`). Re-run with `environments[].name` before concluding a named switch is absent.

A write key is the field's `fieldPath` expanded on its dots — `x.y.z` is `{"x":{"y":{"z":<value>}}}`, never the dotted string as one literal key, and never the sibling `name`. `obj[fieldPath] = v` copies that dotted string as one key. The JSON type of each value is that row's `defaultValue` (a quoted `"30"` stays a string; a JSON `30` stays a number). The same `fieldPath` can differ in type across addons — there is no global type table.

Create may send a field-level subset. Omitted keys are **not** filled into stored `config`. Runtime may still provision (a default LogStore name) but is **not** bitwise `defaultValue`. A user-named switch must appear explicitly in the object that is submitted. A required field's `defaultValue: null` → ask. An optional free-form field the user did not name may be omitted.

Each child is an `element: addon` field; `enable` lives inside `defaultValue` and is not a `fieldPath` ending in `.enable`. Skip `element: addon` rows when matching settings. `aliyun cms2 integration addon get` each child with that child's `--env-type`. Do not use a live release `config` as the create body.

**Right — nested `fieldPath`, entry create.** Named fields on the monitor child, and an explicit close of a default-enabled sibling (omitting `cloud-acs-ecs-audit` would still fan it out):

```json
{"addons":{"cloud-acs-ecs-monitor":{"enable":true,"values":{"hermes":{"enable":false},"scrapeInterval":"60"}},"cloud-acs-ecs-audit":{"enable":false,"values":{}}}}
```

**Wrong — dotted string as one key** (stored and never read; the nested path is not written):

```json
{"hermes.enable": false}
```

**Child update** — no `addons.<child>.values` prefix; draft and wholesale replace: [Addon Release Config Update](#addon-release-config-update-hard-requirement).

A key the schema does not declare is stored as sent and never read — see [Addon Release Config Update](#addon-release-config-update-hard-requirement). Dotted keys in `config` are unread; the nested path is not written.

**Fan-out.** Parent `addons.<child>` is only `{enable, values}`; child fields live on each child's own catalog. A child left out of `values.addons` is created from the entry schema's `defaultValue.enable`, not withheld: `values: "{}"` and a map that names only some children both fan out every child whose `defaultValue.enable` is `true`. An entry with no `element: addon` fields fans out nothing without an explicit `addons` map. Suppressing a default-enabled child takes `{"enable": false, "values": {}}` under its name — that omits it from the next fan-out; child `config` has no `enable`. The previous child release stays in the unfiltered list and is not proof the child is still on. `once: true` does not cap a child at one release per account/workspace.

**Resolve each user setting against that child's `.fields` before writing `enable` or any field.** A request that names only a setting adds those named keys; unnamed fields stay **unsent**. That is not an instruction to drop the rest, and not permission to copy remembered `defaultValue`s into the body. Never rewrite a setting as `entityRules`, and never copy `entityRules` into `values`: the two objects share names (`tags` is the usual collision) and nothing else. A selector array on a string field was written to the wrong object, not a type to ask about.

1. **Scan set.** Every child the entry schema will fan out (`defaultValue.enable`, plus any the user explicitly enabled). Inventory, instance type, and alias resemblance do not shrink this set. `aliyun cms2 integration addon get` each with its `--env-type` (`environments[].name`) and read `.data.schema.fields`.
2. **Match** against `.fields` (`label` and `name`; `fieldPath` is the write key only). Skip `element: addon` rows. A phrase that names a scope mode from [Resource Scope Selection Gate](#resource-scope-selection-gate-hard-requirement) occupies `entityRules` — do not test it against field `label`s.
    - Strip 开启 / 关闭 / 只要 / 不要 (and equivalents) from the request, then match the remainder against `label` / `name` by containment. The request need not quote the full `label`. Do not match from remembered field names; the live `.fields` catalog is the only match surface.
    - Several children with the same hitting `label` → broadcast the override to every hitting child. Same `name` but different `label`s → keep the child whose `label` uniquely contains the request; if none or several still match, ask.
    - A `.fields` hit is a field override — leave that child's `enable` at its default. A request that names a child's `name` or full `alias` and hits no field sets that child's `enable` only.
    - Named collection capabilities plus "the rest stay off" → those overrides, then `false` on every remaining `element: switch` whose `label` / `name` denotes a collection capability. Leave non-collection fields unsent. If a remaining switch's role is unclear from its `label` / `name` / `element`, ask.
    - No field hit and no child-enable hit → emit that child's `.fields[] | [.label, .name, .fieldPath]` and ask. Do not invent a key. Do not claim the schema has no such switch.
    - A non-empty catalog that still misses a user-named collection capability is `--env-type` set to `policyType`: re-run `aliyun cms2 integration addon get` with `environments[].name` before concluding the switch is absent. A non-empty catalog does not skip this step.
3. **Coerce** from the hit row's `element` / `type` and that row's `defaultValue` JSON type, not a remembered `fieldPath`. Switch / checkbox / boolean radio → bool. `numberPicker` or `type: number` → peel units to digits (`60s` → `60`); if `defaultValue` is a quoted numeric string, send a string; if it is a JSON number, send a number. `input` / `textArea` → string. `select` → array. No value on a non-switch → ask. Expand each hitting `fieldPath` into the child's `values` object. `{}` on a child that had a field hit is "keep defaults", not "the override landed".
4. **Verify** each child's `config`, not the parent. Landed means every child that had a field hit is present and stores the coerced value at the expanded path. Emit a child's `config` only as `jq -c` over its `fromjson` parse; pretty-printing, retyping, dropping keys the parse had, or copying the entry's `addons.<child>.values` is reconstructing. Dotted keys are not landed. An array on a string field is the `entityRules` homonym, not landed. A hitting child's `config` that is `{}` or omits the key is not landed — `aliyun cms2 integration addon-release update` that child's `releaseName` with its `values`, not the entry `addons` map. An absent child after a field hit is a mis-built `values` object, not proof the field is off. A child written `enable: false` is absent from the current fan-out; a leftover earlier release of that name is not present. After an update, a still-enabled child whose `config` still holds the pre-update value is also not landed — that path is [Addon Release Config Update](#addon-release-config-update-hard-requirement), not a resend of the entry `addons` map.

After create, group the policy's releases by `parentAddonReleaseId` and judge the group by which expected children are present rather than by its size: a fan-out also carries releases no `addons` map named — companion collectors that the entry's children require. If a child you enabled is missing, the create `values.addons` map was wrong — delete that failed entry release if it exists, rebuild the map, and recreate, or ask; do not `aliyun cms2 integration addon-release update` a gated parent to add the child. A name written `enable: false` on this create is absent from the current fan-out; a leftover release of that name from an earlier entry on the same policy is not present.

Do not ask the user to confirm defaults; apply overrides only when explicitly requested. Required field with no usable default, no derivable value, or type conflict → ask. Serialize as escaped JSON string; validate the outer body with `jq`. Then `fromjson` `.values` and reject if any key **at any depth** contains `.`.

Does not bypass Scope/Workspace/Policy Reuse gates or write confirmation.

### Addon Release Dependency Pre-Check (Hard Requirement)

Before `aliyun cms2 integration addon-release create`, inspect `dependencies.services` from `aliyun cms2 integration addon get`:

1. `aliyun cms2 aliyun-service status --service-name <name>`.
2. If not activated: `aliyun cms2 aliyun-service open --service-name <name>` → ask the user to activate.
3. **Skip** services containing `role` (case-insensitive) — these are SLRs, not cloud services.

Supported: `prometheus`, `cmee`, `ackpro`, `grafana`, `resource-center`, `resource-directory`. Others (non-role): report unrecognized.

### Standard Onboarding

The type file is the runbook: [cs-onboarding.md](cs-onboarding.md), [ecs-onboarding.md](ecs-onboarding.md), [cloud-onboarding.md](cloud-onboarding.md), [batch-onboarding-workflow.md](batch-onboarding-workflow.md). Commands live there; **this order is the rule** and applies even when common is loaded without a type file. Each step's pre-check is in the corresponding Gate section.

1. Discover addon candidates (`aliyun cms2 integration addon list --entity-type`).
2. [Addon Selection Gate](#addon-selection-gate-hard-requirement) (Step 0 scoping first, then rules 1–4).
3. Fetch the selected addon (`aliyun cms2 integration addon get --env-type <environments[].name>`), plus each enabled child its schema declares.
4. [Resource Scope Selection Gate](#resource-scope-selection-gate-hard-requirement): confirm regions + entity scope **before** any inventory query.
5. Scoped discovery inside that confirmed scope; [Resource Identity Verification](#resource-identity-verification) for concrete IDs.
6. [Multi-Region Grouping Gate](#multi-region-resource-grouping-gate-hard-requirement) if the confirmed scope spans regions (each group runs 7–13 independently).
7. [Workspace Selection Gate](#workspace-selection-gate-hard-requirement).
8. [Existing Policy Reuse Gate](#existing-policy-reuse-gate-hard-requirement).
9. [Policy Name Defaulting](#policy-name-defaulting-hard-requirement) if new policy.
10. Build `values` per [Addon Values Defaults](#addon-values-defaults-hard-requirement).
11–13. Execute: reuse/create policy → create release → verify. Before create/update: [Addon Release Region Requirement](#addon-release-region-requirement-hard-pre-check).

### Choosing an Onboarding Method

Cloud sessions use the canonical copy in [cloud-onboarding.md](cloud-onboarding.md#choosing-an-onboarding-method). Keep this stub here: a common-only or batch session does not load that file unless it follows the link.

- **Batch onboarding for multiple cloud services** — addon `cloud-batch-metrics` (`aliyun cms2 integration addon list --search "BatchCloud:CloudMetric"`). When creating/updating a release, validate `entityRules.entityTypes` against those products' `environments[].policies.bindEntity.entityType`; `aliyun cms2 integration addon get --addon-name cloud-batch-metrics` returns no `entityTypes` of its own. Products actually onboarded come from `values.addons`, not from `entityRules`.
- **Single service or custom scope** — product-specific addon via `aliyun cms2 integration addon list --entity-type <entityType>`.

## Key Business Constraints

### Resource Scope Selection Gate (Hard Requirement)

**Runs before inventory discovery, not only before writes.** For every onboarding task, ask Steps 1 and 2 in one prompt and wait for the user's answer before Step 4's scoped discovery — never issue that query alongside addon discovery to save a round trip, and never report an un-onboarded list produced outside a confirmed scope.

**A recommended default is not a confirmed value**: "all regions" when `Feature:CrossRegion` is present, the runtime context workspace's region, the region holding the most resources, and "all entities" still require the user's answer. State the confirmed region(s), scope mode, and scope value when you run the discovery.

**Step 1 — regions.** User named regions → use exactly those. Otherwise build the candidates by pulling the entity type's rows and counting `region_id` locally, per [CloudResource Aggregation](#cloudresource-aggregation-hard-requirement):

```bash
aliyun cms2 entity query --source CloudResource --from <from> --to <to> \
  --sql ".entity with(domain='acs', type='<entityType>') | limit 0, 1000"
```

Present each candidate with its resource count, and shape the options by the selected addon's `keywords` (already retrieved by `aliyun cms2 integration addon get`):

| `Feature:CrossRegion` | Region options |
|-----------------------|----------------|
| present | **"all regions" is required and is the recommended default** (first option, pre-selected) — a single workspace/policy/release can cover them. Keep every discovered region on the list so the user can narrow. "all regions" means every region in the presented distribution, not an unscoped sweep of empty regions. Still wait for the answer. |
| absent | **single region by default**, recommending the runtime context workspace's region (or the region with the most resources when there is none), plus an explicit "multiple regions" option stating that each region becomes an independent onboarding group with its own workspace, policy, and addon release |

If the query fails or returns nothing, ask the user to name the regions — never fall back to an unscoped full listing.

**Step 2 — entity scope mode.** Ask for the **mode first**, never a concrete value and never a broad scope inferred from an omitted field. Modes: all entities, resource group (`resourceGroupId`), tag filter (`tags`, itself carrying a match mode), entity ID list (`instanceIds`), plus bound cluster for CS (`--bind-resource-id`/`entityGroup.clusterId`). Region scope (`regionIds`) is already settled in Step 1. `entityQueries`/`spl` is the server-derived read shape on `aliyun cms2 integration addon-release list`, not a fifth write mode — see [Addon Release Create Body Shape](#addon-release-create-body-shape).

**Step 3 — concrete values**, collected only after the mode is chosen. Do not pre-fill them from inventory.

| Mode | How to collect |
|------|----------------|
| resource group | `aliyun cms2 resource-group list` (account-wide, `--region` not required, paginate) → user picks the `rg-` ID |
| tag | one question collects the key, the match mode, and the value(s) together per [Tag Match Modes](#tag-match-modes). Never default the mode when the user gave only a key and a value |
| entity ID list | user supplies the IDs → verify per [Resource Identity Verification](#resource-identity-verification) |

**Step 4 — scoped discovery.** Only now query the inventory, pushing the confirmed region and scope into the query, and compute the un-onboarded set inside that scope only:

```bash
aliyun cms2 entity query --source CloudResource --from <from> --to <to> \
  --sql ".entity with(domain='acs', type='<entityType>') | where region_id in ('<r1>','<r2>') and <scope predicate> | limit 0, 1000"
```

The scope predicate comes from the confirmed mode — one mode, one predicate:

| Mode | Predicate |
|------|-----------|
| all entities | omit (region filter only) |
| resource group | `resource_group_id = '<rg-id>'` |
| tag | `json_extract_scalar(tags, '$["<key>"]')` plus the operator of the confirmed mode: `equals` → `= '<v>'`, `in` → `in ('<v1>','<v2>')`, `notIn` → `not in ('<v1>','<v2>')`, `startWith` → `like '<v>%'`, `endWith` → `like '%<v>'`, `inAll` → `is not null`. A resource without the key never matches, not even under `notIn`, so `in` and `notIn` do not partition the resource set |
| entity ID list | `instance_id in ('<id1>','<id2>')` |

`--sql` and `--entity-type` are mutually exclusive: use `--entity-type` only for the unfiltered all-entities case, otherwise express every filter in `--sql` — including the region, as `region_id = '<region>'`, because `--region` is unreliable under `--sql` per [General Conventions](#general-conventions).

Tag mode writes as `entityRules.tags[] = {tagKey, op, tagValues[]}` with the confirmed `op`, elements AND-ed, and `tagKey`/`tagValues` non-empty in every element (`inAll` ignores the values but still needs `["*"]`). Keep the selector in `tags` — never expand it into `instanceIds`. When the addon provisions an SLS collection policy, `notIn` is rejected and `in`/`inAll` degrade to substring matching, so the collected scope can be wider than the scanned one; `equals`/`startWith`/`endWith` translate consistently and are safer when the two must match.

Report the un-onboarded list with the confirmed regions and scope stated alongside it. Those confirmed values are also the policy/addon release write scope (`entityRules`) — do not re-ask at write time; restate them plus resource type/addon, tag match mode, and workspace in the write confirmation.

#### Tag Match Modes

Ask as one question carrying all six modes below, returning the tag key, the match mode, and the tag value(s) together. Prefill the key only when the user already named one; the mode is always the user's answer, even when their wording hints at one. A dropped option lets the user silently settle for a wider or narrower scope.

The question queries nothing: the key and the values are typed in. Discover existing keys from CloudResource rows' `tags` JSON (object keys) for that entity type, then list them in the question body so the user can copy one. Do not call `aliyun cms2 tag list` for this: that command tags CMS product resources (`--resource-type` / `--resource-id`, flags from `--help`) and does not list ECS/cloud-product tag keys. Keys are case-sensitive; one absent from that list matches nothing.

When the structured input form cannot render all six modes, ask as plain text with every mode spelled out per [One choice, one question](../SKILL.md#global-conventions). Single-select: exactly one `op` reaches `entityRules.tags[]`. Show labels in the answer language per [Output Language and Terminology](../SKILL.md#output-language-and-terminology).

| `op` | Label (中文) | Label (English) | Values to collect |
|------|-------------|-----------------|-------------------|
| `equals` | 等于 — 标签值精确等于指定值 | Equals — tag value is exactly the given value | single value |
| `in` | 包含 — 标签值在指定列表中 | In — tag value is one of the listed values | value list |
| `notIn` | 不包含 — 标签值不在指定列表中 | Not in — tag value is none of the listed values | value list |
| `startWith` | 前缀 — 标签值以指定内容开头 | Starts with — tag value begins with the given text | single value |
| `endWith` | 后缀 — 标签值以指定内容结尾 | Ends with — tag value ends with the given text | single value |
| `inAll` | 全部 — 只要存在该标签 Key 即可（不限值） | Any — the tag key exists, whatever its value | none — never ask for values; the write still sends `["*"]` |

`in`/`notIn` are list membership, not substring matching. The single-value modes silently ignore extra values, so switch to `in` when the user lists several. `inAll` still writes `tagValues: ["*"]` and never asks for values. Step 4 above holds the query predicate and the `entityRules.tags[]` payload each `op` translates into.

The answer carries `matchMode` as the `op` verbatim and `tagValues` as comma- or newline-separated text, which the form does not check against the mode: split it, drop empty entries, and re-ask when a value-requiring mode came back empty.

### Multi-Region Resource Grouping Gate (Hard Requirement)

Applies before Workspace Selection when the scope confirmed in [Resource Scope Selection Gate](#resource-scope-selection-gate-hard-requirement) spans several regions; skip it for a single-region scope. Without `Feature:CrossRegion` such a scope only exists because the user explicitly chose it in that gate.

1. Collect distinct `region_id` from the verified resources.
2. `Feature:CrossRegion` **absent**: group by region. Each group is an independent unit with its own workspace/policy/release in that region, and the runtime context workspace applies only to its own region.
3. `Feature:CrossRegion` **present**: one workspace may cover all regions; proceed without grouping.

Present the grouping plan before proceeding.

### Workspace Selection Gate (Hard Requirement)

Module-specific steps for the global [Workspace Confirmation Gate](../SKILL.md#workspace-confirmation-gate-hard-requirement). Before creating policy or addon release without an explicit workspace:

1. Determine the target region from resource metadata.
2. `aliyun cms2 workspace list --region <targetRegion> -o json` paginated to completion.
3. Present candidates; recommend when evidence supports (user-provided > same-region with relevant policies > `default-cms-{userId}-{regionId}` as a discovery hint only). If the list is empty, ask for the exact workspace.
4. Wait for an explicit choice, including when step 2 returned a single candidate — present it as the recommended option instead of adopting it.

If the user provided a workspace, verify it exists in the target region. Stop pagination early only on exact `workspaceName` match. No match → report and ask.

### Existing Policy Reuse Gate (Hard Requirement)

Before `aliyun cms2 integration policy create` or `aliyun cms2 integration addon-release create`, check for reusable policies via `aliyun cms2 integration policy list` (paginate to completion):

- User-provided: `--policy-id` or resolve `--policy-name` to one `policyId`.
- CS: `--policy-type CS --bind-resource-id <clusterId>`.
- ECS: `--policy-type ECS --workspace <ws> --filter-region-ids <region>`; cross-check with `--addon-name`.
- Cloud: `--addon-name <addonName>`; cross-check with `--policy-type`.

Verify each candidate: `policyType`, workspace/region, scope, existing target releases. Reuse only after confirmed compatible; existing healthy release covering scope → do not duplicate unless the user confirms; both paths possible → ask; no reusable → create after write confirmation. Confirmation must state path, policyId (if reuse), workspace, region, addon, scope.

### Policy Name Defaulting (Hard Requirement)

`policyName` is required for `aliyun cms2 integration policy create`. If the user provides one, use it. If omitted and the new-policy path is chosen, generate deterministically (`date -u +%Y%m%d%H%M%S` once): **CS** `ACK:{clusterName}`; **Cloud** `{Cloud}-{regionId}-Policy-{UTC timestamp}`; **ECS** `ECS-{regionId}-Policy-{UTC timestamp}`; **BatchMetric** `BatchMetric-{regionId}-Policy-{UTC timestamp}`. Freeze before confirmation; reuse on retry. API rejection → stop, ask the user. Does not permit defaulting other parameters. Sub-types (RDS/SLB etc.) are under Cloud, declared per addon (`environments[].policyType`).

### Policy Type Classification

Top-level categories: **Default**, **System**, **CS**, **ECS**, **Cloud**, **Flink**, **BatchMetric**. Sub-types (RDS/SLB etc.) are under Cloud, declared per addon (`environments[].policyType`).

- **Default policy**: addons with no bound entity (`integrate-metric-store`, `security-actiontrail`, etc.)
- **System policy**: cloud-service probes (`metric-agent`), etc.

### Policy Lookup Rules

`--bind-resource-id` requires `--policy-type CS` (ACK/container only). ECS and Cloud: `--addon-name` or `--policy-type`, then verify by target release and scope. Full flags: `aliyun cms2 integration policy list --help`.

### Resource Identity Verification

Before onboarding or creating/updating policy/release for concrete IDs, verify them with `aliyun cms2 entity query --source CloudResource`; never rely on ID shape alone. For ACK/CS: a 32-char hex is only a format hint — confirm K8s identity from the query result.

### Cross-Account Onboarding

If CloudResource `user_id` ≠ the current account (from workspace name `default-cms-{userId}-{regionId}`, or ask), check only `addon.keywords` for `Feature:CrossAccount`.

- **Supported** → set `entityUserId` on the policy's `entityGroup` and continue. CS requires `feePackage=CS_Pro` on that path (`CS_Basic` fails creation); where the field lives is in [cs-onboarding.md](cs-onboarding.md). `aliyun cms2 integration addon-release create --help` has the same rule.
- **Unsupported** → do not abort immediately. Search other addons bound to the same entity type (`aliyun cms2 integration addon list --entity-type`) and check only `addon.keywords` for `Feature:CrossAccount`. Found → apply [Addon Selection Gate](#addon-selection-gate-hard-requirement) to select the target. None → ask the user to switch credentials.

### Addon Release Create Body Shape

Flags and the body envelope: `aliyun cms2 integration addon-release create --help`. `--addon-name` is not a flag (`unknown flag: --addon-name`); the name goes in the body as `addonName`, alongside `version`, `envType`, `workspace`, and `values`. `envType` is `environments[].name` per [Addon Values Defaults](#addon-values-defaults-hard-requirement), not the help's CS/ECS/Cloud — that `name` can be `Cloud` on an ECS policy. `values` is that section's expanded object, escaped. `--show-example-body` / `--help` flat `name`s are envelope samples only.

`entityRules` is a single object beside `addonName` — not an array, and not nested under `entityGroup` (a policy field). Sub-fields are flat: `entityTypes` (required, no wildcards), `regionIds`, and **at most one** of `resourceGroupId` / `tags` / `instanceIds`. Cloud and ECS take it; some CS addons reject it, so read the type workflow first. Homonymous keys are not shared with `values`. A tag scope writes only to `entityRules.tags` **whether or not the scope gate already ran**; the schema field named `tags` stays unsent unless the user named that field's `label`.

**The write shape and the read shape differ.** `aliyun cms2 integration addon-release list` wraps the rules one level deeper — `entityRules.entityRules` — beside the server-derived `entityRules.entityQueries[]`, one `{entityType, spl}` per entity type. Validate a request body against the flat shape; resolve an existing release's scope from the nested one.

### Addon Release Config Update (Hard Requirement)

Applies to every change of an existing release's settings. Read `aliyun cms2 integration addon-release update --help` for flags and the body envelope; the behaviour below governs the write. Dropping scrape metrics (`dropMetrics`) on probe `metric-agent` is not a child-addon field change — follow [Metric Drop](integration-management.md#metric-drop): discover it via `aliyun cms2 integration collector list` (`HideReleaseName:true` hides it from `aliyun cms2 integration addon-release list`), send live `release.version` as `addonVersion` plus wholesale `values`, and do not use the "values by itself" bullet below.

**Do not `aliyun cms2 integration addon-release update` the target if either check hits; change child configuration instead.** Judge the **target** release as follows:

1. **Grouping mode:** `aliyun cms2 integration addon get --addon-name <that release's addonName>` → `.data.addon.keywords` contains the token `GroupMode:true`. There is no `groupMode` field. Do not confuse with `entityGroupMode` / `entityGroup`. Judge every target by **that addon's** keywords. A hit is not an update target even if no children have appeared yet, including the entry's own fields (ACK `store.storageTarget` / `store.project`). Ask; do not update the parent.
2. **Already has children:** unfiltered `aliyun cms2 integration addon-release list --policy-id`. This target has children only when other rows' `parentAddonReleaseId` equals this row's `releaseId`. Read that pointer from **list**, not from `aliyun cms2 integration addon-release get`. Do not use `--parent-addon-release-id` (an empty result is not zero children; Cloud/ECS/CS children often leave the field empty — see step 3 of [Determining Onboarding & Monitoring Status](#determining-onboarding--monitoring-status)). An empty pointer on this row means this check does not hit — do not treat "the policy has other releases" as this target having children, and do not reuse step 3's CS rule ("every non-entry under the policy") here: that would block updating a CS child. A CS/ACK entry is already blocked by check 1.

This gate does not apply to `aliyun cms2 integration addon-release create`. Do not also update the parent so its `config` "stops contradicting" the child. `addons.<child>.enable` belongs on the **entry's** create body (below). After that entry exists, close a child with `aliyun cms2 integration addon-release delete` on that child's `releaseName`; open a child with `aliyun cms2 integration addon-release create` using the **child's** `addonName` on the same policy.

Envelope vs wholesale `values`: `aliyun cms2 integration addon-release update --help`. A settings change sends `values` by itself and leaves `addonVersion` and `entityRules` untouched. Inside `values` the wholesale rule below governs instead. **Exception — metric-agent metric drop:** send `addonVersion` (pinned to `release.version` from `aliyun cms2 integration addon-release get`, not catalog latest) and `values` together per [Metric Drop](integration-management.md#metric-drop). Every update is a final write — the command has no dry-run field.

**Composing the body.** `values` replaces the stored config wholesale. `fromjson` the child's current `config` from `aliyun cms2 integration addon-release list --policy-id <policyId> -o json` (rows are `.data.releases[]`), expand each hitting `fieldPath` into that object per [Addon Values Defaults](#addon-values-defaults-hard-requirement), and `jq -c` the **whole** object into `values`. The draft is the live `config`, not schema defaults: a subset that names only the new keys drops every omitted key from stored `config` — it does not keep them and does not restore schema `defaultValue`. `--show-example-body` names are envelope samples. Nothing validates the keys and the write reports success either way — the stored `config` is the only landing evidence. A release rendering at its defaults after a successful write is holding keys the addon does not read.

**A fan-out child's existing release does not follow its entry release**, and most settings live in a child. Writing `values.addons.<childName>.values` on the entry changed the entry's config alone (measured on Cloud and ECS). A field change takes effect when the child release is updated directly — that is the only write. A broadcast field hit needs that child-release write on every hitting child. Identify children per step 3 of [Determining Onboarding & Monitoring Status](#determining-onboarding--monitoring-status). Do not wait for the child to pick up an entry write, and do not send one: `Loaded` with the pre-update `config` on the same `releaseName` is the measured outcome of an entry-only attempt. `Loaded` / `Success` is not evidence the field landed. The child's update body is `fromjson` of its own `config`, never the entry `addons` map. Child `config` has no `enable`; do not write `enable: false` there to close a child.

**Closing or opening a child is not a child `config` field and not an entry `update`.** On the **entry's** `aliyun cms2 integration addon-release create`, suppressing a default-enabled child takes an explicit `{"enable": false, "values": {}}` under its name in `values.addons` — omitting the name still fans it out from `defaultValue.enable` (see [Fan-out](#addon-values-defaults-hard-requirement) above). That object keeps the name out of this create's fan-out. A leftover release of that name from an earlier entry on the same policy stays listed and is not present.

After that entry exists, do not rewrite a gated entry's `addons` map:

- **Close** a child: `aliyun cms2 integration addon-release delete --release-name` on that child's existing release ([Teardown](#teardown)). Do not write `enable: false` on the child `config`.
- **Open** a child that is not in the current fan-out: `aliyun cms2 integration addon-release create --policy-id` with **that child's** `addonName` (child `values` and `--env-type` from its own schema per [Addon Values Defaults](#addon-values-defaults-hard-requirement) and [Addon Release Create Body Shape](#addon-release-create-body-shape); Cloud/ECS still send `entityRules` matching the entry's scope). This is not initial onboarding — do not treat the child as a replacement for the entry. Do not `aliyun cms2 integration addon-release update` the gated parent to add it.

Field changes on names that stay enabled land only by `aliyun cms2 integration addon-release update` on that child's existing `releaseName` — do not wait for a replacement mint.

**Verifying afterwards** — on the config, never on the status: re-read every release **without** `--addon-name`. The current fan-out is the entry plus each still-enabled child, one release per `addonName`: the existing child `releaseName` you updated in place if you did, otherwise the non-entry release minted by this write (`createTime` at this write's `updateTime`). A mint of the same `addonName` beside that in-place update is not a second present. Do not use Cloud `parentAddonReleaseId` (empty) or latest `updateTime` per `addonName` — the latter reports a leftover closed child as present. A name written `enable: false` at create is absent even when the leftover release is still listed and `Loaded`. Then check each remaining child's `config` at the expanded path. A still-enabled hitting child whose parsed `config` still holds the pre-update value is not landed — update that child's `releaseName` and re-read; do not wait for Installing, and do not report the entry `config` or that stale parse as the post-update child config. Three outcomes are expected rather than regressions:

- An update reinstalls the release, so `Ready` may sit at `Unknown` while `Loaded`/`Installed` stay `True` — a pending metric check.
- A re-run of the onboarding check reports today's data plane, not the config you sent. A release whose scope has since gone empty settles at `Ready=False, The addon metrics is not ready` with a byte-identical config, because its `Ready=True` had been frozen at install time. Check current inventory before calling it a regression.
- A disabled capability keeps its aliyun cms2 integration collector listed with `state: Success` long afterwards; judge `workloads[].status`, not collector existence. The uninstall trails the config write by many minutes.

### Addon Release Region Requirement (Hard Pre-Check)

Mandatory before `aliyun cms2 integration addon-release create` or `aliyun cms2 integration addon-release update`, regardless of scope mode. Probe `metric-agent` has no `Feature:CrossRegion` — `--region` equals the policy's `regionId`; do not run catalog `aliyun cms2 integration addon get` to learn that. See [Metric Drop](integration-management.md#metric-drop).

1. `aliyun cms2 integration policy get --policy-id` → `.data.policy.regionId`. There is no `policyRegion` field; do not parse the workspace name.
2. `aliyun cms2 integration addon get --addon-name <name> -o json` → `addon.keywords`. For `metric-agent`, skip this get — treat as Absent and apply step 4.
3. `Feature:CrossRegion` present → proceed (release region may differ).
4. Absent → CLI `--region` must equal that `regionId`; `entityRules.regionIds` must only contain that `regionId`.

**On violation** — stop and report: workspace/policy in `{policy.regionId}`, resources in `{targetRegion}`, addon lacks `Feature:CrossRegion`. **Fallback**: `aliyun cms2 integration addon list --entity-type <entityType>` for a `Feature:CrossRegion` alternative → [Addon Selection Gate](#addon-selection-gate-hard-requirement). None → suggest a workspace in the target region.

## Rules for Determining Addon Release Status

Three labels — `Success`, `Installing`, `Failed` — derived from the release's `conditions` array, never from the top-level `.status`. Mapping: `aliyun cms2 integration addon-release list --help` for the current session.

A parent at `Ready`/`Success` is not enough when the addon fans out children: judge the group per [Addon Values Defaults](#addon-values-defaults-hard-requirement). An empty `values` can still reach `Ready=True` while enabling nothing.

## Teardown

Read `aliyun cms2 integration policy delete --help` and `aliyun cms2 integration addon-release delete --help` before deleting in the current session. Follow write confirmation before any delete.

### Scenario Selection

**Whole-resource teardown** — one matching integration policy → delete the policy (`aliyun cms2 integration policy delete`; the CLI cascades to addon releases).

**Single-addon teardown** — delete the target addon release (`aliyun cms2 integration addon-release delete --release-name`), or batch-delete all releases of one addon (`--addon-name`) when the user explicitly wants that. There is no `--force` flag. Closing one fan-out child after the entry exists is this path: `--release-name` of that child, not an entry `update` ([Addon Release Config Update](#addon-release-config-update-hard-requirement)). Target-flag priority (`--addon-name` vs `--release-name`): `aliyun cms2 integration addon-release delete --help`. Use only one target flag.

### Post-Delete Verification

1. **CS policy deletion**: `aliyun cms2 integration policy list --policy-type CS --bind-resource-id <clusterId>` and expect zero matching policies.
2. **ECS or Cloud sub-types**: re-run the same candidate-policy lookup used before deletion, then inspect remaining target addon releases and their scopes. Deletion is verified when no remaining healthy release covers the original target; do not expect zero policies for the addon globally.
3. **Cross-check**: `aliyun cms2 integration policy get --policy-id <policyId>` rejected with `400` is positive deletion evidence (wording varies).
4. **Release check**: `aliyun cms2 integration addon-release list --policy-id <policyId>` is positive evidence that releases/environment were removed when it is **rejected**. Judge on the `400` status, not on the message text (see [Policy identity gate](integration-diagnosis.md#policy-identity-gate)). A `200` with an empty list means the policy still exists and merely holds no releases.
5. **Eventually consistent**: if delete succeeded but the first list still returns the old policy, wait briefly and retry 2–3 times before reporting failure.
6. Distinguish confirmed control-plane deletion from cluster-side cleanup lag or residual collectors.
