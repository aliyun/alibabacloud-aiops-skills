# Alerting Module

> Global conventions (credentials, output, error codes) — see [../SKILL.md](../SKILL.md).
> Run `aliyun cms2 alert <subcommand> --help` for full flag lists; this doc focuses on **business knowledge** not in `--help`.
> Notification targets (contacts / robots / webhooks) are now under the top-level `notification-channel` command — not under `alert`.
> APM metric catalog → [apm-metrics.md](apm-metrics.md). UModel metric catalog → [umodel-metrics.md](umodel-metrics.md).

## Command Tree (sub-resource layout)

```
aliyun cms2 alert
├── rule          create | update | patch | delete | enable | disable | list | get
├── template      list | get | create | update | delete | apply
└── history       list
```

> ⚠️ **Hard rules (user preference)**:
> 1. To modify an existing rule, **always prefer** `alert rule patch --use-patch-api`. **Avoid `update`** (it requires the full body and risks accidental overwrites).
> 2. After a successful `alert rule create`, you **must** immediately run `alert rule get --alert-rule-id <id>` and show the full rule to the user. Do not skip.

### Query Alert Rule

```bash
aliyun cms2 alert rule get  --alert-rule-id <uuid>
aliyun cms2 alert rule list --workspace <ws>
```

#### Client-side Guards (alert rule get / list / delete)

These are **client-side fail-fast checks** added after the v0.9.2-6 QA pass
(CMS-CLI-NEW-1 / CMS-CLI-NEW-7 / silent-filter-acceptance). Treat them as
hard constraints when generating commands; the server would otherwise
silently return surprising rows or success-with-zero-effect envelopes.

| Command | Guard | Why |
|---------|-------|-----|
| `alert rule get` | `--alert-rule-id` rejects empty / whitespace-only values (`InvalidArgument`). | Was a P0 information-disclosure: empty ID degraded into a `Uuid.Eq=""` filter and dumped the entire account's rules. |
| `alert rule delete` | When `deletedCount == 0` (no UUID matched), the envelope is `{success:false, error:{code:"ResourceNotFound"}}`. | Earlier behaviour was `success=true, deletedCount=0` + a stderr warning, which masks typos in scripted teardown. |
| `alert rule list` | `--alert-rule-id`, when explicitly set, must not be empty / whitespace-only. | Otherwise the UUID filter was silently dropped and the query degraded to a workspace-wide list-all. |
| `alert rule list` | `--page-size`, `--page-number`, `--max-results` must be `>= 1` when explicitly set. | `--page-size 0` used to be silently forwarded and the server returned 0 rows. |
| `alert rule list` | `--page-size` and `--max-results` are capped at **1000** client-side. | The backend echoes any size into the envelope but truncates the actual rows; large values look like "0 rows returned". |

> If you need a true list-all, omit the filter flag entirely. Do **not**
> pass `--alert-rule-id ""` thinking it means "any".

### Alert Rule Template Filter Guards

| Command | Guard | Why |
|---------|-------|-----|
| `alert template list` | `--alert-type` is whitelisted to `PROMETHEUS_SINGLE_QUERY` / `PROMETHEUS_MULTI_QUERY` / `APM_METRIC_QUERY` / `APM_MULTI_QUERY` / `SLS_MULTI_QUERY` / `UMODEL_METRICSET_QUERY`. | The list endpoint silently returns 0 rows for unknown values, which masks typos like `Prometheus` (CamelCase, used by `create`/`update`) being pasted into list. |
| `alert template list` | `--alert-type` rejects empty / whitespace-only values when explicitly set. | Same reason as above. Omit the flag to query without an alert-type filter. |
| `alert template list` | `--page-size` capped at **1000** client-side; `--page-number` / `--page-size` must be `>= 1` when explicitly set. | The backend echoes the requested size in the envelope while truncating real rows, hiding paging bugs. |

> **CamelCase vs SCREAMING_SNAKE**: `alert template list --alert-type` uses
> the **inner ruleConfigs query type** (`PROMETHEUS_SINGLE_QUERY` etc.).
> The `alert template create / update` payload's top-level `alertType`
> uses the **CamelCase server-canonical form** (`Prometheus` / `APM` /
> `UModel`). They are different fields with different vocabularies; do
> not cross them.

### Patch vs Update Decision

| Scenario | Choose |
|----------|--------|
| Phase 2 supplement of `level` / `message` / `send` / `sendToArms` / `alertMetricInput` | ✅ `patch --use-patch-api` |
| Add/remove/modify notification targets, threshold, severity, active time, displayName, labels, annotations | ✅ `patch --use-patch-api` |
| Full rebuild of `queryConfig` (switch metric / switch PromQL) | ⚠️ `update` (or delete + create) |
| Switch `datasourceConfig.type` | ⚠️ `delete` + `create` (cannot patch) |

---

## ManageAlertRules Type System

Three rule types. `datasourceConfig.type` ↔ `queryConfig.type` ↔ `conditionConfig.type` must match strictly:

| datasource | queryConfig.type | conditionConfig.type | Use case |
|-----------|------------------|----------------------|----------|
| `PROMETHEUS` | `PROMETHEUS_SINGLE_QUERY` | `PROMETHEUS_SIMPLE_CONDITION` | PromQL alerts |
| `APM` | `APM_MULTI_QUERY` | `APM_SIMPLE_CONDITION` (multi-threshold) | APM single-condition |
| `APM` | `APM_MULTI_QUERY` | `APM_COMPOSITE_CONDITION` | APM multi-condition single-threshold |
| `UMODEL` | `UMODEL_METRICSET_QUERY` | `UMODEL_METRICSET_CONDITION` | CloudMonitor (ECS / RDS / K8s) |

### Common Config (all types)

```json
{
  "action": "CREATE",
  "workspace": "<workspace>",
  "displayName": "<rule-name>",
  "enabled": true,
  "scheduleConfig": {"type": "FIXED", "intervalSecs": 60},
  "notifyConfig": {
    "type": "DIRECT_NOTIFY",
    "channels": [{"type": "CONTACT", "identifiers": ["<contactId>"]}],
    "silenceTimeSecs": 300,
    "activeDays": [1,2,3,4,5,6,7],
    "activeStartTime": "00:00", "activeEndTime": "23:59",
    "utcOffset": "+08:00"
  }
}
```

`channels[].type`: `CONTACT` | `GROUP` | `DINGTALK` | `FEISHU` | `SLACK` | `WEIXIN` | `WEBHOOK`
`severity`: `INFO` | `WARN` | `ERROR` | `CRITICAL`

---

## Type 1: Prometheus

**Required user input** (AskUser): `workspace` + `instanceId` (Prometheus instance / cluster_id).

```json
"datasourceConfig": {"type": "PROMETHEUS", "instanceId": "<id>", "regionId": "<region>"},
"queryConfig":      {"type": "PROMETHEUS_SINGLE_QUERY", "promQl": "<expr>", "expr": "<expr>", "enableDataCompleteCheck": true},
"conditionConfig":  {"type": "PROMETHEUS_SIMPLE_CONDITION", "durationSecs": 300, "severity": "WARN"}
```

> ⚠️ **POP gateway requires `expr`**: the SDK field is `promQl`, but POP validation also requires `expr`. **Send both fields with the same value.**

### Message & Annotations (must be generated on CREATE)

Otherwise the console "detection statement" / notification body will be empty. Prometheus uses the Prometheus template syntax:

| Variable | Prom template | APM template |
|----------|---------------|--------------|
| Label | `{{$labels.<dim>}}` | `$tags.<dim>` |
| Current value | `{{ printf "%.2f" $value }}` | `$formatted_values.val_0` |

Severity zh-CN mapping (used inside `message`): `CRITICAL` → 严重 / `ERROR` → 错误 / `WARN` → 警告 / `INFO` → 普通.

**Default templates** (Chinese is intentional — these strings render in the alert console / IM messages):
- `message`: `<监控对象> {{$labels.<主维度>}} <指标中文> 最近 <durationSecs/60> 分钟持续<operator中文> <threshold> <unit>触发<severity中文>告警，当前值 {{ printf "%.2f" $value }}<unit>`
- `annotations._cms_rule_display_statement`: `<监控对象描述> <指标中文> 最近 <durationSecs/60> 分钟持续<operator中文> <threshold> <unit>触发<severity中文>告警。`

**Primary label inference**: nodes use `instance`; cAdvisor containers use `pod` / `container`; JVM uses `application`; cloud products use `instanceId` etc. When uncertain, use `{{ $labels | toJSON }}` as a debugging placeholder.

### Full Example (Prometheus)

```json
{
  "action": "CREATE",
  "workspace": "default-cms-<userId>-cn-hangzhou",
  "displayName": "CPU 使用率告警",
  "enabled": true,
  "annotations": {"_cms_rule_display_statement": "节点机 CPU 使用率最近 5 分钟持续大于 90% 触发警告告警。"},
  "message": "节点机 {{$labels.instance}} CPU 使用率最近 5 分钟持续大于 90% 触发警告告警，当前值 {{ printf \"%.2f\" $value }}%",
  "datasourceConfig": {"type": "PROMETHEUS", "instanceId": "prom-abc", "regionId": "cn-hangzhou"},
  "queryConfig": {
    "type": "PROMETHEUS_SINGLE_QUERY",
    "promQl": "avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) by (instance) > 90",
    "expr":   "avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) by (instance) > 90"
  },
  "conditionConfig": {"type": "PROMETHEUS_SIMPLE_CONDITION", "durationSecs": 300, "severity": "WARN"},
  "scheduleConfig": {"type": "FIXED", "intervalSecs": 60},
  "notifyConfig": {"type": "DIRECT_NOTIFY", "channels": [{"type": "CONTACT", "identifiers": ["ops-user"]}], "silenceTimeSecs": 300, "activeDays": [1,2,3,4,5], "activeStartTime": "09:00", "activeEndTime": "18:00", "utcOffset": "+08:00"}
}
```

---

## Type 2: APM

**Required user input** (AskUser): `workspace` + `serviceId` (APM service ID).

`datasourceConfig` does not carry `instanceId`; `regionId` is optional:

```json
"datasourceConfig": {"type": "APM", "regionId": "cn-hangzhou"},
"queryConfig": {
  "type": "APM_MULTI_QUERY",
  "serviceIdList": ["<service-id>"],
  "filterList":  [{"key": "<dim>", "type": "ALL"}],
  "measureList": [{"measureCode": "<key>", "windowSecs": 60, "groupBy": ["<dim>"]}]
}
```

> 📖 **measureCode / group / filter / unit mapping** → see [apm-metrics.md](apm-metrics.md). **Always look up the table before creating** — the console fails silently otherwise.

### ConditionConfig

```json
// Simple — single condition, multi-threshold
{"type": "APM_SIMPLE_CONDITION", "aggregate": "AVG", "operator": "GT",
 "thresholdList": [{"severity": "WARN", "threshold": 80}, {"severity": "CRITICAL", "threshold": 95}]}

// Composite — multi-condition, single-threshold
{"type": "APM_COMPOSITE_CONDITION", "relation": "OR", "severity": "CRITICAL",
 "compareList": [{"aggregate": "AVG", "operator": "GT", "threshold": 50}]}
```

`aggregate`: `AVG` | `SUM` | `COUNT` | `MAX` | `MIN` | `P50` | `P75` | `P90` | `P99` | `CONTINUES`
`operator`:  `GT` | `GE` | `LT` | `LE` | `EQ` | `NE`
`relation`:  `OR` | `AND`

### Console Display Required Fields (CRITICAL — must be set on CREATE)

| Field | Purpose |
|-------|---------|
| `annotations._cms_rule_display_statement` | Console "detection statement" |
| `annotations._cms_domain` | Entity domain — APM uses `"apm"` |
| `annotations._cms_entity_type` | Entity type template |
| `annotations._cms_entity_id` | Entity ID template |
| `annotations._cms_entity_prop_service_id` | `"$labels.acs_arms_service_id"` |
| `annotations._cms_entity_prop_ip` | `"$labels.rootIp"` (host metrics) |
| `message` | Notification body (see template) |
| `labels._cms_metric_key` / `_cms_metric_group_key` | Metric identifiers |
| `alertMetricInput` | Console metric-picker metadata (CREATE does not support; supplement via PATCH) |

**Display statement template** (Chinese — renders in console):
`"<groupDisplayName> <metricDisplayName> 最近 <windowSecs/60> 分钟的<aggregate>大于 <threshold> 触发<severity>告警。"`

**Message template** (Chinese — renders in notifications):
`"<groupDisplayName> <dimension>: $tags.<dim> <metricDisplayName>最近 <windowSecs/60> 分钟的<aggregate> 大于 <threshold> <unit>触发<severity>告警，当前值 $formatted_values.val_0"`

### Full Example (Host CPU)

```json
{
  "action": "CREATE",
  "workspace": "default-cms-<userId>-cn-hangzhou",
  "displayName": "arms-pop-cpu-high",
  "enabled": true,
  "labels": {"_cms_app_name":"application_insights","_cms_metric_key":"appstat.jvm.SystemCpuUsage","_cms_metric_group_key":"appstat.jvm.SystemCpuUsage"},
  "annotations": {
    "_cms_rule_display_statement": "主机监控 节点机CPU利用率 最近 1 分钟的平均值大于 80 触发警告告警。",
    "_cms_domain": "apm",
    "_cms_entity_type": " if $labels.rootIp apm.instance else apm.service end",
    "_cms_entity_id":   " if $labels.rootIpprintf \"%s$%s\" $labels.acs_arms_service_id $labels.rootIp | md5elseprintf \"%s\" $labels.acs_arms_service_id | md5end",
    "_cms_entity_prop_service_id": "$labels.acs_arms_service_id",
    "_cms_entity_prop_ip": "$labels.rootIp"
  },
  "message": "主机监控 节点机IP: $tags.rootIp 节点机CPU利用率最近 1 分钟的平均值 大于 80 %触发警告告警，当前值 $formatted_values.val_0",
  "alertMetricInput": {"metricId":"appstat.jvm.SystemCpuUsage","groupId":"apm.host","filterValues":[{"opt":"ALL","dim":"rootIp"}]},
  "datasourceConfig": {"type":"APM","regionId":"cn-hangzhou"},
  "queryConfig": {"type":"APM_MULTI_QUERY","serviceIdList":["aokcdqn3ly@xxx"],"filterList":[{"key":"rootIp","type":"ALL"}],
                   "measureList":[{"measureCode":"appstat.jvm.SystemCpuUsage","windowSecs":60,"groupBy":["rootIp"]}]},
  "conditionConfig": {"type":"APM_SIMPLE_CONDITION","aggregate":"AVG","operator":"GT","thresholdList":[{"severity":"WARN","threshold":80}]},
  "scheduleConfig": {"type":"FIXED","intervalSecs":60},
  "notifyConfig": {"type":"DIRECT_NOTIFY","channels":[{"type":"CONTACT","identifiers":["ops-user"]}],"silenceTimeSecs":900,"activeDays":[1,2,3,4,5,6,7],"activeStartTime":"00:00","activeEndTime":"23:59","utcOffset":"+08:00"}
}
```

### APM PATCH-Required Fields (CREATE does not accept them)

| Field | Reason |
|-------|--------|
| `level` | CREATE defaults to `INFO`; not derived from `thresholdList` |
| `alertMetricInput` | Required for console metric-picker rendering |
| `condition.compareList[].baseUnit/displayUnit` | Console unit display |
| `send.notification.notifyTime` | `notifyConfig.activeDays` is stored under the wrong field `effect_time` on CREATE |
| `send.sendToArms` | ARMS integration flag |

**Patch field mapping** (CREATE → patch body):

- `level` ← highest severity in `thresholdList` (CRITICAL > ERROR > WARN > INFO)
- `alertMetricInput.metricId/groupId` ← apm-metrics.md `key` / `group`
- `alertMetricInput.filterValues` ← group filters (default `opt: ALL`)
- `condition.compareList[].baseUnit/displayUnit` ← apm-metrics.md baseUnit / displayUnit map
- `condition.compareList[].valueLevelList[].value` ← `conditionConfig.thresholdList[].threshold` (**raw number, no conversion**)
- `condition.compareList[].aggregate` ← `conditionConfig.aggregate.toLowerCase()`
- `condition.compareList[].oper` ← `conditionConfig.operator`
- `send.notification.contacts/dingWebhooks/fsWebhooks/wxWebhooks/slackWebhooks/customWebhooks/groups` ← results from `notification-channel contact/robot/webhook list`
- `send.notification.notifyTime.dayOfWeek` ← active days (1=Mon..7=Sun)
- `send.notification.notifyTime.startTime/endTime` ← `HH:MM`
- `send.notification.notifyTime.gmtOffset` ← `+0800` (**no colon**, unlike CREATE's `+08:00`)
- `send.notification.silenceTime` ← `notifyConfig.silenceTimeSecs`
- `send.sendToArms` ← default `false`

> CREATE-stage `notifyConfig.activeDays/active*Time` may carry a placeholder full week. **The effective window is the one written by PATCH `send.notification.notifyTime`.**

---

## Type 3: UModel

**Required user input** (AskUser): `workspace` + entity info (domain / type / cluster_id).

```json
"datasourceConfig": {"type": "UMODEL"},
"queryConfig": {
  "type": "UMODEL_METRICSET_QUERY",
  "entityDomain": "k8s",
  "entityType":   "k8s.pod",
  "metricSet":    "k8s.metric.high_level_metric_pod",
  "metric":       "pod_restart_count",
  "entityFilters": [{"field":"namespace","operator":"=","value":"kube-system"}],
  "entityFields":  [{"field":"cluster_id","value":"<cluster-id>"}]
},
"conditionConfig": {"type":"UMODEL_METRICSET_CONDITION","durationSecs":60,"severity":"INFO","operator":"GT","threshold":1}
```

> 📖 **metricSet / metric ID lookup table** → [umodel-metrics.md](umodel-metrics.md). **Always look up before creating**; on a miss, call `ask_user_question` to confirm.

### Full Example (UModel — Pod restart)

```json
{
  "action": "CREATE",
  "workspace": "o11y-integration-cn-hongkong",
  "displayName": "Pod 重启次数 > 1",
  "enabled": true,
  "labels": {"_cms_app_name":"cloudlens_for_container","_cms_cluster_id":"c65359xxx","_cms_region":"cn-hongkong"},
  "datasourceConfig": {"type":"UMODEL"},
  "queryConfig": {"type":"UMODEL_METRICSET_QUERY","entityDomain":"k8s","entityType":"k8s.pod",
                  "metricSet":"k8s.metric.high_level_metric_pod","metric":"pod_restart_count",
                  "entityFilters":[{"field":"namespace","operator":"=","value":"kube-system"}],
                  "entityFields":[{"field":"cluster_id","value":"c65359xxx"}]},
  "conditionConfig": {"type":"UMODEL_METRICSET_CONDITION","durationSecs":60,"severity":"INFO","operator":"GT","threshold":1},
  "scheduleConfig": {"type":"FIXED","intervalSecs":60},
  "notifyConfig": {"type":"DIRECT_NOTIFY","channels":[{"type":"CONTACT","identifiers":["ops-user"]}],"silenceTimeSecs":60,"activeDays":[1,2,3,4,5,6,7],"activeStartTime":"00:00","activeEndTime":"23:59","utcOffset":"+08:00"}
}
```

---

## Creation Workflow (CREATE → PATCH → VERIFY)

### Step 1 — Lock context

| Type | Required params (must AskUser) |
|------|-------------------------------|
| Prometheus | `workspace` + `instanceId` |
| APM | `workspace` + `serviceId` |
| UModel | `workspace` + entity (domain / type / cluster_id) |

### Step 2 — Build query

- Prom: PromQL (send `promQl` and `expr` with the same value)
- APM: look up measureCode + group in [apm-metrics.md](apm-metrics.md), then derive filterList / groupBy
- UModel: look up metricSet + metric in [umodel-metrics.md](umodel-metrics.md)

### Step 3 — Build condition

severity / threshold / operator / aggregate (APM) / duration.

### Step 4 — Query notification targets (MANDATORY)

```bash
aliyun cms2 notification-channel contact list
aliyun cms2 notification-channel robot list
aliyun cms2 notification-channel webhook list
```

> **Skipping this** leaves `notifyConfig.channels[].identifiers` pointing at non-existent resources.

### Step 5 — Pre-check + summary + execute (CREATE)

```bash
# Duplicate-name pre-check
aliyun cms2 alert rule list --workspace <workspace>
```

Show the **Configuration Summary** (Type / Metric / Threshold / Severity / Notification / Active Time) to the user, wait for confirmation, then:

```bash
UUID=$(aliyun cms2 alert rule create --body @rule.json -o json | jq -r '.alertRuleId')
```

### Step 6 — PATCH supplement (MANDATORY for APM)

CREATE only writes a subset of fields; APM rules **must** be supplemented via PATCH (see APM patch field map above).

```bash
aliyun cms2 alert rule patch --alert-rule-id $UUID --body @patch.json
```

> Routing (defaults of `alert rule patch`):
> - `--body` mode + `--use-patch-api=true` (**default**) → `PatchAlertRule` (HTTP `PATCH /alertRules/{id}`, true incremental). This is what you want for APM phase-2 supplements.
> - `--body` mode + `--use-patch-api=false` → `ManageAlertRules UPDATE` (full replacement, PUT semantics). Partial bodies are typically rejected by the backend with `"X is required"`. The CLI prints a stderr warning when this branch is taken.
> - `--set key=value` mode → forced to `ManageAlertRules UPDATE` regardless of the flag, because `--set` paths (e.g. `conditionConfig.threshold`, `notifyConfig.channels`) are UPDATE-style and not compatible with the `PatchAlertRule` schema (`condition` / `query` / `send` / `labels` / ...). The CLI prints a stderr warning here as well.

**patch.json template**:

```json
{
  "level": "CRITICAL",
  "alertMetricInput": {"metricId":"<key>","groupId":"<group>","filterValues":[{"opt":"ALL","dim":"<dim>"}]},
  "condition": {"type":"APM_CONDITION","compareList":[{
    "oper":"GT","aggregate":"avg","baseUnit":"<baseUnit>","displayUnit":"<unitCn>",
    "valueLevelList":[{"level":"CRITICAL","value":<raw-number>}]
  }]},
  "send": {"sendToArms": false, "notification": {
    "contacts":["<contact-id>"],
    "notifyTime":{"dayOfWeek":[1,2],"startTime":"00:00","endTime":"23:59","gmtOffset":"+0800"},
    "silenceTime": 900
  }}
}
```

### Step 7 — Final verify (MANDATORY)

```bash
aliyun cms2 alert rule get --alert-rule-id $UUID -o json
```

Show the full JSON to the user. Verify: `level`, `alertMetricInput.metricId/groupId`, `condition.compareList[].baseUnit/displayUnit`, `send.notification.notifyTime.dayOfWeek`, `send.notification.contacts`.

---

## Critical Rules

### API Enforcement

CMS 2.0 only uses `ManageAlertRules` (create / update / delete) + `QueryAlertRules` (query) + `PatchAlertRule` (incremental supplement).

**Forbidden** — never fall back to: `PutResourceMetricRule` / `DescribeMetricRuleList` (CMS 1.0), `CreateOrUpdateAlertRule` / `CreatePrometheusAlertRule` (ARMS). On failure: STOP. Do not retry with a different API.

### Required AskUser Params

`workspace` / `instanceId` (Prom) / `serviceId` (APM) must come from AskUser. Do not auto-construct or guess.

### POP Gateway Known Limit

POP validates the `type` field. Currently registered: `PROMETHEUS` ✓ + 4 `conditionConfig.type` values ✓. If `APM` / `UMODEL` `datasourceConfig.type` returns `"type is mandatory for this action"`, you may degrade to `PROMETHEUS` + `PROMETHEUS_SINGLE_QUERY` and translate the APM expression into PromQL (loses filterList / multi-threshold APM features).

---

## Other Workflows

### Modify a Rule

```bash
# ✅ Preferred — incremental (PatchAlertRule, the default routing of --body mode)
aliyun cms2 alert rule patch --alert-rule-id <uuid> --body @patch.json
aliyun cms2 alert rule get   --alert-rule-id <uuid> -o json    # mandatory display

# ⚠️ --set is forced to ManageAlertRules UPDATE (full-replacement). Backend
# usually rejects a partial --set body with "X is required". Use --body for
# true incremental updates instead.
aliyun cms2 alert rule patch --alert-rule-id <uuid> --set displayName="New Name"

# ⚠️ Full replace — only when rebuilding queryConfig
aliyun cms2 alert rule get --alert-rule-id <uuid> -o json > rule.json
# Edit rule.json: set action=UPDATE, add the uuid field
aliyun cms2 alert rule update --alert-rule-id <uuid> --body @rule.json
aliyun cms2 alert rule get    --alert-rule-id <uuid> -o json
```

### Enable / Disable / Delete

```bash
aliyun cms2 alert rule enable  --alert-rule-id <uuid1>,<uuid2>
aliyun cms2 alert rule disable --alert-rule-id <uuid>
aliyun cms2 alert rule delete  --alert-rule-id <uuid>          # irreversible — confirm first
```

### Query Alert History

```bash
aliyun cms2 alert history list --workspace <workspace>
aliyun cms2 alert history list --workspace <workspace> --alert-rule-name "CPU使用率过高"
```

> ⚠️ **Pagination flags differ from rule / template**: `alert history list` only supports token-based pagination — `--max-results <N>` + `--next-token <token>` (read `nextToken` from the response). It does **not** support `--page-number` / `--page-size`.
>
> Output: `-o text` (default) and `-o json` both render full rows. The first stderr line in `-o text` is `# data returned=<n> total=<t> truncated=<bool>` followed by CSV rows. The previous regression where `-o text` returned an empty body (forcing `-o json`) has been fixed; you do not need `-o json` to see the rows.

#### Known Caveats (alert history list)

These are deliberate, currently-unsupported behaviours. Treat them as constraints when generating commands or `--body` payloads; do not silently "fix" them by retrying with different inputs.

| # | Caveat | Why it matters | Recommended workaround |
|---|--------|----------------|------------------------|
| 1 | **Inside `--body`, only `pageSize` is honoured by the server**; `maxResults` is silently ignored. | The `--max-results` flag path mirrors the value into both `MaxResults` and `PageSize` (see [list.go `buildAlertHistoryListRequestFromFlags`](file:///Users/hym/aliyun-cms-cli/pkg/command/alerthistory/list.go)). The `--body` path does **not** apply this rewrite — it forwards the JSON verbatim. A body that only sets `"maxResults":N` will fall back to the server default page size. | In `--body`, always write `"pageSize": N` (and optionally also `"maxResults": N` for forward compatibility). Reserve `--max-results` for the flag path. |
| 2 | **`--workspace` is not auto-trimmed**. Leading/trailing whitespace is sent verbatim and the server matches it as a literal string — you will see `data: []` with no error. | Client-side validation only rejects control characters and over-length; spaces are valid characters. | Trim the workspace identifier yourself (`echo "$WS" | xargs`) before passing it. Quote it with `"..."` to make accidental trailing spaces visible. |
| 3 | **No `--page-number` flag**. The SDK request model carries `pageNumber`, but the CLI deliberately exposes only token-based pagination. | Token pagination is stable across server-side re-shards; offset pagination is not. Mixing them produces non-deterministic skips. | Always paginate via `--max-results` + `--next-token`. If you genuinely need offset pagination, fall back to `--body '{"pageSize":N,"pageNumber":M}'` — you accept the stability caveat. |
| 4 | **`--max-results` upper bound is not documented in `--help`**. The server enforces an internal cap (observed: requests with `pageSize > ~1000` are quietly clamped). | Large page sizes silently degrade to the server cap, breaking client-side `len(data) == max-results` assumptions. | Keep `--max-results` ≤ **100** for normal querying. For full-table scans, loop with `--next-token` instead of trying to bump `--max-results` higher. |
| 5 | **Severity / status enums are case-sensitive on the client**. `--severity critical` is rejected as `InvalidArgument` even though the server itself would accept it. | The CLI runs an enum guard (`CRITICAL` / `WARNING` / `INFO` and `Ok` / `Alerting`) before the API call to surface typos early. | Use the canonical case shown in `--help`. Inside `--body`, also use `"latestLevel":"CRITICAL"` (or the alias `"severity":"CRITICAL"`); lowercase forms reach the server but the CLI flag path will not. |
| 6 | **`--body` accepts `severity` as an alias for `latestLevel`, but not the other pagination/filter aliases.** | The alias rewrite is intentionally narrow — only `severity → latestLevel` is implemented (see [`rewriteSeverityAlias`](file:///Users/hym/aliyun-cms-cli/pkg/command/alerthistory/list.go)). Other server-side names (`alertRuleId`, `startTimeFrom`, `startTimeTo`, `pageSize`) must be used verbatim. | When porting console JSON into `--body`, keep the SDK canonical key names. Setting **both** `severity` and `latestLevel` is rejected (`InvalidArgument`) on purpose. |

> If any of the above limitations becomes blocking for a real workflow, file a CLI feature request — do not paper over it with retries or shell post-processing in the SKILL output.

### Discoverability / Dry-run

```bash
aliyun cms2 alert rule create --show-schema
aliyun cms2 alert rule create --show-example-body
aliyun cms2 alert rule create --body @rule.json --dry-run    # server-side validation, not persisted
```

---

## Alert Rule Templates (`alert template`)

A template encapsulates a reusable alert rule definition; `apply` materializes it into one or more `alert rule` records — equivalent to the console "Apply Template" action.

### Schema (key fields)

| Field | Type | Description |
|-------|------|-------------|
| `id` | int64 | Numeric primary key (CLI: `--template-id`) |
| `uuid` | string | String alias (CLI: `--template-uuid`) |
| `templateName` / `description` / `alertType` / `subType` | string | Metadata |
| `isSystem` | int32 | 0 = custom, 1 = system built-in (read-only, applyable) |
| `applyCount` / `status` | int / int | Apply count / status |
| `ruleConfigs` | **string** | **Serialized alert rule JSON** (one or many) |

`alertType` (CamelCase, server-canonical — the create/update endpoint rejects underscored forms): `Prometheus` / `APM` / `UModel`.

> The CLI auto-serializes `ruleConfigs` (object/array) to a string on create/update; on apply it deserializes and substitutes placeholders `${key}` / `{{key}}` / `{{ key }}` / `{{.key}}` / `{{ .key }}` (placeholders without a matching `--var` are left intact for dry-run debugging).
>
> **`ruleConfigs` inner shape** — the create/update endpoint expects a **flat** object inside the stringified JSON, not a wrapper. Required keys: `level` / `displayName` / `query` / `message` / `labels`. Do **not** put `queryConfig` / `conditionConfig` / `datasourceConfig` / `rules` at the top level inside the string — those are the apply-time three-section schema. Run `alert template create --show-example-body` for the canonical create-time skeleton.

### Apply Workflow

| Step | Action |
|------|--------|
| 1 | `apply --template-id N --workspace W` |
| 2 | Resolve template: try `GetAlertRuleTemplate` first; on failure (the upstream `/alertRuleTemplate/detail` endpoint is not always deployed in every region) the CLI **auto-falls back** to `ListAlertRuleTemplate` and matches by `id` / `uuid` |
| 3 | Substitute placeholders with `--var key=value` — supports `${key}` / `{{key}}` / `{{ key }}` / `{{.key}}` / `{{ .key }}`. Placeholders without a matching `--var` are left intact for dry-run debugging |
| 4 | Decode `ruleConfigs` (single rule / `{rules:[...]}` wrapper / array of rules) |
| 5 | **Dialect translation** — if the rule body is in alertmanager-style (`alert` / `expr` / `for` / `labels.severity`), the CLI auto-translates to the three-section CMS schema (`queryConfig` / `conditionConfig` / `notifyConfig`). The PromQL is written into `queryConfig.expr` (the canonical wire field on the apply path; `promQl` returns `400 expr is required in queryConfig` here, even though `alert rule create` still accepts both) |
| 6 | **Inject overrides + required-field defaults** — `action=CREATE` / `workspace` / `displayName` / channel block; if missing, the CLI fills `enabled=true` and `scheduleConfig={type:FIXED, intervalSecs:60}` so the request passes the `ManageAlertRules` validator |
| 7a | `--dry-run` → print the assembled body without calling the backend |
| 7b | Otherwise call `ManageAlertRules` per rule body |
| 8 | Collect `uuid` + `displayName` + `requestId`. On mid-batch failure the error response carries `failedAt` + `createdRules` (no rollback) |
| 9 | `alert rule get --alert-rule-id <uuid>` (mandatory display) |

### Typical Examples

```bash
# Browse candidate templates
aliyun cms2 alert template list --alert-type PROMETHEUS_SINGLE_QUERY --is-system 1

# --is-system -1 fans out to two backend calls (custom + system) and merges results;
# pagination is intentionally rejected in this mode (semantics not well-defined).
aliyun cms2 alert template list --is-system -1

# Get a template (resolved via GetAlertRuleTemplate; auto-fallback to list-scan on endpoint miss)
aliyun cms2 alert template get --template-id 12345
aliyun cms2 alert template get --template-uuid tpl-xyz

# List notification identifiers BEFORE apply — needed for --contact-group-id / channel-type.
aliyun cms2 notification-channel contact list   # contact ids (use --channel-type CONTACT)
# (group ids come from your contact-group catalog in the console)

# Apply a template — default channel type is GROUP
aliyun cms2 alert template apply --template-id 12345 --workspace ws-xxx \
  --var namespace=prod --var prometheusInstanceId=prom-xxx \
  --contact-group-id <group-id-1> --contact-group-id <group-id-2>

# Apply with a single contact instead of a contact group
aliyun cms2 alert template apply --template-id 12345 --workspace ws-xxx \
  --var namespace=prod \
  --display-name "Pod-Restart-Prod" \
  --prometheus-instance-id <prom-instance-id> \
  --contact-group-id <contact-id> \
  --channel-type CONTACT     # GROUP (default) | CONTACT | DINGTALK | FEISHU | WEIXIN | SLACK | WEBHOOK

# Dry-run preview of the assembled alert rule body (no backend call)
aliyun cms2 alert template apply --template-id 12345 --workspace ws-xxx --dry-run

# Manage custom templates
aliyun cms2 alert template create --body @./template.json
aliyun cms2 alert template update --template-id 12345 --body '{"description":"new desc"}'
aliyun cms2 alert template delete --template-id 12345
```

### Limits

- `isSystem=1` system templates are read-only (cannot update/delete; can apply)
- `--workspace` is required outside dry-run mode
- Mid-batch failures of `apply` **do not auto-rollback** (avoids deleting production rules); the error response carries `failedAt` + `createdRules`
- The internal structure of `ruleConfigs` is not strictly validated by `apply`; an illegal body is rejected by `ManageAlertRules`
- **Resolution fallback**: when `GetAlertRuleTemplate` returns `data:null` or the detail endpoint is not deployed, the CLI silently retries via `ListAlertRuleTemplate`. Only after that miss does it surface a structured `ResourceNotFound` (the message mentions `data:null` for diagnosability)
- **Apply-path field name**: PromQL must be sent as `queryConfig.expr`; the apply path rejects `promQl` with `400 expr is required in queryConfig` (this differs from `alert rule create`, which still accepts both)
- **Channel-type default**: `--contact-group-id` values default to `notifyConfig.channels[0].type=GROUP`; pass `--channel-type CONTACT|DINGTALK|FEISHU|WEIXIN|SLACK|WEBHOOK` to override. The CLI also injects `enabled=true` and `scheduleConfig={type:FIXED, intervalSecs:60}` when the template body omits them, so apply does not fail with `"X is required"` 400s

---

## Related

- Alert events → SLS event store → [event-hub.md](event-hub.md)
- APM metric catalog → [apm-metrics.md](apm-metrics.md)
- UModel metric catalog → [umodel-metrics.md](umodel-metrics.md)
