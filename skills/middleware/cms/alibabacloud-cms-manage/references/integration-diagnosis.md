# Integration Policy Diagnosis

Use this workflow to run a health check on an integration policy — or on one collection rule under it — and emit a structured diagnostic report.

## Scope

Trigger when the user asks to diagnose, health-check, or troubleshoot:

- **Whole-policy diagnosis** — a policy identified by `<policy-id>`; run all [Check Items](#check-items-whole-policy).
- **Targeted diagnosis** — one addon release / collection rule under a policy (`custom-discover-<id>` is a release name — read `discoverType` before treating it as a custom-job — plus ServiceMonitor, PodMonitor, Exporter probe), usually named together with the policy. Run [Targeted Collection Rule Diagnosis](#targeted-collection-rule-diagnosis) instead of the full sweep; do not expand it into a whole-policy report the user did not ask for.

## Tooling

Complete the diagnosis with `aliyun cms2` subcommands, under the help-first rule in [SKILL.md](../SKILL.md#global-conventions). Flags, response fields, and Environment behaviour come from each command's `--help` — do not copy them here.

### Policy type gate (hard pre-check)

Read `policyType` from `aliyun cms2 integration policy get`. Keep only the collection-path commands whose `--help` Environment behaviour accepts that type; drop the rest as not applicable.

A 400 `the environment(policy) type is invalid` is a planning error (the type gate was skipped), not collection-path evidence: no [Differential Diagnosis](#differential-diagnosis) branch applies. Do not substitute a policy of another type, and do not invent a `policyId` when the workspace holds none of the required type — say no diagnostic object exists and stop.

`aliyun cms2 integration addon-release list`, `aliyun cms2 integration storage list`, `aliyun cms2 integration dashboard list`, and `aliyun cms2 integration collector list` are type-agnostic (collector may return an empty `collectors[]`). There is no `datasource` or `probe` subcommand under `integration`; probes are collector-type queries per that `--help`.

### Policy identity gate

A `400` on a `--policy-id` command is either "this ID resolves to nothing" or a skipped [type gate](#policy-type-gate-hard-pre-check). Settle it on status code, not on the message text: `aliyun cms2 integration policy get --policy-id <policyId>` answering `2xx` hands the original 400 back to the type gate; a `400` on `policy get` itself means there is no diagnostic object — stop, re-establish the ID from `aliyun cms2 integration policy list`, and report that none exists when nothing matches.

Do not read on: a nonexistent ID makes `aliyun cms2 integration storage list` return `200` with an empty body, indistinguishable from a policy that genuinely has no Prometheus storage. Teardown inverts the same test — see [Teardown](integration-common.md#teardown).

### Collection-path corrections

Run only the collection-path commands the [type gate](#policy-type-gate-hard-pre-check) kept. Per-job fields and target-location combinations: that command's `--help`.

Three overrides `--help` does not settle:

- **scrapeUrl** comes from `aliyun cms2 integration check-scrape-config` `results[].targets[].scrapeUrl`, not from `job-target list` (even though that `--help` says to) and never assembled from an `instance` label.
- Collector identity is `aliyun cms2 integration collector list --collector-type ClusterCollector` `collectors[].releaseName`. Pick `collectorName: metric-agent`, not `entity-collector`. Read `releaseName` from the response; never reconstruct it from the policy ID.
- `aliyun cms2 integration check-scrape-config` re-renders the config server-side; the collector consumes what was **delivered**. `passed: true` with a matching `results[]` row proves the dry-run can load; it does not prove the collector is running that job, and it does not overrule a rejecting `message` on the delivered rule. `passed: false` → `failedPhase` from that `--help`.

`status 400: The target url is insecure` is the probe service declining the URL — record `QueryFailed`, keep `scheme: http` out of the root cause and the fix, and fall back to [`up`](#up-is-the-reachability-oracle). Any other failure: `QueryFailed` per [Pagination & Query Failure Handling](../SKILL.md#pagination--query-failure-handling). A failed check does not license `kubectl`.

### `up` is the reachability oracle

The collector synthesizes `up` for every target it **actually scrapes**. No `up{job="<resolvedJobName>"}` series means this job produced no scrape. That is **not** by itself a config-load verdict — read it against step 4:

- Step 4 shows the job in `results[]` and `relabelKept` omitted or `0`, or `discoveryTargets: 0` → empty `up` is the data-plane echo of branch 3 or 4. Do not reclassify it as "the job is not in the runtime config".
- Step 4 shows `finalTargets ≥ 1` and `up` is still empty → the dry-run kept targets the running collector never scraped (branch 5), once `--prometheus-id` is confirmed.
- Job absent from `results[]` and `up` empty → still branch 1 or 2; `up` does not add a third story.

Query with the **resolved scrape job name** from [Rule identity vs scrape job identity](#rule-identity-vs-scrape-job-identity-hard), never the user's collection-rule token and never a fuzzy `job=~".*<token>.*"`. Confirm the instance with `aliyun cms2 integration storage list` first — a wrong `--prometheus-id` also yields empty. This is the fallback whenever `check-collector-target` came back `QueryFailed`.

### Evidence fidelity (hard requirement)

Report what each command returned, quoting `passed`, `summary`, `failedPhase`, and error strings verbatim. Never write that a check returned nothing when it returned a result. When the dry-run and the runtime disagree, carry both and resolve them through branches 2 and 5.

### Evidence sources — use these, not `kubectl`

| Evidence needed | Command |
|-----------------|--------------------------------------------------------------------------------|
| Release status and the **submitted** values (`config`) | `aliyun cms2 integration addon-release list --policy-id <policyId>` |
| **Delivered** custom collection | `aliyun cms2 integration custom-job list --policy-id <policyId> --addon-release-name <releaseName>` |
| Delivered ServiceMonitor / PodMonitor | `aliyun cms2 integration service-monitor list` / `pod-monitor list --policy-id <policyId> --addon-release-name <releaseName>`. Named ServiceMonitor: `matchedServiceCount` and `endpoints[].matchedTargetCount` (not in that `--help`; omitted is 0). Named PodMonitor: `matchedPodCount` (omitted is 0); do not read the ServiceMonitor counts. What those counts mean: [branch 4](#differential-diagnosis) |
| Targets the collector discovered | `aliyun cms2 integration job-target list --policy-id <policyId> --collector-release-name <collectorReleaseName>` | 
| Whether a job would load | `aliyun cms2 integration check-scrape-config --policy-id <policyId>` |
| Collector health | `aliyun cms2 integration collector list --policy-id <policyId> --collector-type ClusterCollector` |
| Policy-scoped Service | `aliyun cms2 integration resource list --policy-id <policyId> --kind Service --namespace <ns>` once the rule's namespace is known. Without `--namespace`, an empty `200` with no `resources[]` matches an unsupported kind — inconclusive, not zero Services. Endpoints / Pod / Deployment: [branch 4](#differential-diagnosis). Not `aliyun cms2 entity query --source CloudResource`. |
| Metric samples | `aliyun cms2 integration storage list --policy-id --addon-release-name --storage-type Prometheus` → `aliyun cms2 metric promql query --prometheus-id <status.instanceId>` |
| Dashboards | `aliyun cms2 integration dashboard list --policy-id <policyId>` |

**Targeted filter lock.** Named-rule diagnosis: `--addon-release-name` is the owning release (`custom-job list --help` already requires this so `cs-default` stays out). `--job-name` is a **resolved scrape job name**. A miss, a 400, or `passed: true` with no matching `results[]` row → re-resolve; do not drop `--addon-release-name` or read other jobs (that is unfilter). Omitting `--job-name` while `--addon-release-name` already scopes the call is step 4, not unfilter. Ignore other `results[]` / target rows even if an unfiltered body happens to contain the job.

### `kubectl` is not the default path

`aliyun cms2 integration resource list` is the cluster-object check. A `job-target list` 400 does **not** unlock `kubectl`.

Use `kubectl` when any of these holds:

- the user explicitly asked, or
- the matching `resource list --kind` returned `QueryFailed`, or
- [branch 4](#differential-diagnosis) needs Endpoints / Pod / Deployment facts and `resource list` for those kinds is empty `200` / omitted `resources[]` (inconclusive, not zero).

Stay on the named rule's Service / Endpoints (or EndpointSlice) / Pods / owning Deployment. Do not list those kinds cluster-wide after the named object is in hand. `command not found` → the continuation is `QueryFailed`; keep the finding already classified. Label `kubectl` as side evidence when `resource list` did not confirm the same fact, and do not rest a CMS release-values fix on `kubectl` alone.

## Input

- Policy ID: `<policy-id>` (exact match), plus its `policyType` per the [type gate](#policy-type-gate-hard-pre-check); an ID that resolves to nothing is settled by the [identity gate](#policy-identity-gate) first.
- For targeted diagnosis: the collection-rule name the user spoke. Resolve it per [Rule identity vs scrape job identity](#rule-identity-vs-scrape-job-identity-hard) before any `--job-name` or PromQL `job=` call.

## Rule identity vs scrape job identity (hard)

The user names a **collection rule**. Prometheus scrape `job` labels — and `--job-name` on `check-scrape-config` / `job-target list` — are a different string.

| User names | Resolve from |
|------------|--------------|
| ServiceMonitor / PodMonitor name | `service-monitor list` / `pod-monitor list` → `name` + `namespace` |
| Custom collection name / embedded `job_name` | `custom-job list` → `scrapeConfigs[].jobName` or the `job_name:` in `configYaml` |
| Addon release name (`custom-discover-<id>` included) | `addon-release list` → that release's submitted `discoverType`, then the matching rule list. An empty `custom-job list` is expected when `discoverType` is `PodMonitor` / `ServiceMonitor` |

Operator-generated monitor jobs are typically `serviceMonitor/<namespace>/<name>/<endpointIndex>` and `podMonitor/<namespace>/<name>/<endpointIndex>`.

Resolve once, then lock:

1. Find the delivered rule. Token is a rule name → exact `name` (and namespace if given) in the three rule lists. Token is a release name → that release's `discoverType`, then the `--addon-release-name` row(s); do not require `name` to equal the release name. Diagnose that rule only.
2. Derive scrape job names: custom-job → each `scrapeConfigs[].jobName` / `job_name:`; ServiceMonitor / PodMonitor → every `check-scrape-config` `results[]` row whose job belongs to this rule (`serviceMonitor/<ns>/<name>/` or `podMonitor/<ns>/<name>/` prefix). Diagnose those rows only.
3. `--job-name <userToken>` with no matching `results[]` row, or `job-target list` 400 / empty: the token was the rule name — re-resolve from step 2, then apply the [filter lock](#evidence-sources--use-these-not-kubectl). A `passed: true` with no matching row is a **filter miss**, not proof the job loaded.

## Check Items (whole policy)

1. Policy basics: name, ID, type, region, workspace, status (`policy get`).
2. Addon release status (`addon-release list`; conditions per that `--help`).
3. Storage / datasource instance IDs (`storage list`).
4. Dashboards (`dashboard list`).
5. Collector / exporter health (`collector list --collector-type` values from that `--help`: ClusterCollector, NodeCollector, Exporter).
6. ServiceMonitor / PodMonitor / custom-job configuration and status.
7. [Collection Config Content Validation](#collection-config-content-validation) for every rule from item 6.
8. Scrape config load across all config sources.
9. Discovered targets, live reachability, and data-plane `up` plus one expected series per job.

## Targeted Collection Rule Diagnosis

Run these steps in order.

Commands take `--policy-id` and `-o json`; full forms sit in [Evidence sources](#evidence-sources--use-these-not-kubectl). The [type gate](#policy-type-gate-hard-pre-check) decides which apply.

Collector health (step 1) is policy-level. Steps 2–6 stay on the **one** rule [identity](#rule-identity-vs-scrape-job-identity-hard) resolved.

1. **Collector identity and health** — `collector list --collector-type ClusterCollector`: judge `state` / `workloads[]` per that `--help`, keep `collectors[].releaseName` for step 5 (the *collector's* release name, distinct from the addon release in steps 2-4).
2. **Release status** — `addon-release list`: the **one** release that owns the named rule. Read `conditions` per that `--help`, plus version, `message`, and submitted `config`.
3. **Config content** — fetch the matching rule type with `--addon-release-name` (`discoverType` picks the list; an empty `custom-job list` is not "no rule"). Token is a rule name → keep the row whose `name` equals it. Token is a release name → keep the row(s) that `--addon-release-name` returned; do not require `name` to equal the release name. Validate that rule's `configYaml` **and** `message` per [Collection Config Content Validation](#collection-config-content-validation). A `Ready` / `Success` condition only proves **rendered and delivered**, never **valid**.
4. **Scrape config load** — `check-scrape-config --addon-release-name <releaseName>` with `--job-name` set to each **resolved scrape job name**. If the CLI misses or 400s on the user's collection-rule token, omit `--job-name` **only** when `--addon-release-name` already scopes the call, then **client-keep** `results[]` rows that belong to this rule. Read `passed`, `summary`, `targets[]`, and `drops[]` on the kept rows only; note each kept `targets[].scrapeUrl` for step 5.
5. **Target status** — `job-target list --collector-release-name <collectorReleaseName> --job-name <resolvedJobName>`, then `check-collector-target --collector-release-name <collectorReleaseName> --scrape-url <scrapeUrl>` on a kept target of this rule. On 400 / empty after a name miss: retry with the resolved name, or mark `QueryFailed`.
6. **Data plane** — `storage list --addon-release-name <releaseName> --storage-type Prometheus`, then `promql query --prometheus-id <status.instanceId> --query 'up{job="<resolvedJobName>"}'` once per resolved job, plus one expected series, read per [`up`](#up-is-the-reachability-oracle).
7. **Root cause** — apply [Differential Diagnosis](#differential-diagnosis). Cluster-object evidence belongs here; do not replace step 5 with a cluster-object heading.

## Collection Config Content Validation

A rule reports `Ready` as soon as it is rendered and delivered. Two artefacts are not the same document:

| Artefact | Where | What it is |
|----------|-------|------------|
| Submitted values | `addon-release list` → `config` (`configMapYamlTxt` / `serviceMonitorYamlTxt` / `podMonitorYamlTxt`) | what the user typed |
| Delivered rule | `custom-job list` → `configYaml`, or `service-monitor list` / `pod-monitor list` | what the backend rendered |

**Judge the delivered artefact by reading it.** For `discoverType: PrometheusYaml`, a delivered `configYaml` that is a bare job list (`- job_name: ...`) is a defect — it needs a `scrape_configs:` root (the `cs-default` row in the same `custom-job list`). Submitted values do not excuse it.

**The rule's `message` is the backend's verdict on what it delivered.** `ScrapeConfigs Invalid: scrape_configs is empty` is a rejection, not a hint. A passing dry-run does not overrule it — the two read different documents. The same exception: a PrometheusYaml custom-job missing the `scrape_configs:` root key. Any other lint finding that the dry-run contradicts (job present, `passed: true`) is a note; keep going down the branches. ServiceMonitor/PodMonitor selectors: [branch 4](#differential-diagnosis) for **that** rule type — do not borrow the other type's counts.

## Differential Diagnosis

Walk the branches in order against the step 3-6 results. The first match is the root cause.

1. **Job absent from `check-scrape-config` `results[]`, or `passed: false` with `failedPhase` validation** → read `failedPhase`, then the delivered content. Content invalid → config is the root cause; fix release values, do not restart. Content valid → config did not reach the collector; check collector health, then reload. `failedPhase: relabel` / `ALL_DROPPED` with the job in `results[]` is branch 4, not this branch.
2. **Dry-run passed, yet the delivered rule carries a rejecting `message`, or a PrometheusYaml custom-job lacks the `scrape_configs:` root key** → the backend rejected what it delivered. Fix the release values so the delivered artefact is a valid document. Quote the `message` and `configYaml`; a passing dry-run does not clear the rule. A PodMonitor / ServiceMonitor has no `scrape_configs:` root — do not take its absence as this branch.
3. **Job loaded, `summary.discoveryTargets: 0` / `targets[]` empty** → service discovery matched nothing.
4. **Job loaded, every discovered target in `drops[]` (`relabelKept` omitted or `0`)** → quote the dropping rule. Then split **on the delivered rule type** (do not borrow another type's fields):
   - **ServiceMonitor** — the named row on `service-monitor list` (those fields are not in that `--help`):
     - `matchedServiceCount` is Endpoints objects matching the selector, not addresses. `≥ 1` is not scrapeable targets.
     - Read `endpoints[].matchedTargetCount` (omitted is 0; the count includes NotReady). Do not treat `discoveryTargets` or a generated port-name `keep` as that Service's endpoint count.
     - Then `resource list --kind Service --namespace <rule namespace>` for `ports[].name` / `spec.selector`. Do not call `--kind Service` without `--namespace`. Do not invent `--kind` values, and do not take empty `--kind Endpoints` / `--kind Pod` as zero objects.
     - `matchedTargetCount` omitted or `0` + port name does not match `endpoints[].port` → port-name miss. Same `0` + port name already matches → **this Service has no endpoints** (no addresses, including NotReady — do not call this "no ready backends"). Report that first; `spec.selector` is the Pod filter, not a cause — do not name a key from that map as the root cause from the Service object. Then quote, in order: Endpoints / EndpointSlice for that Service name; Pods matching `spec.selector`; the owning Deployment if a controller owns those labels. Prefer `resource list` for kinds `--help` lists; empty `200` → `kubectl` per [kubectl is not the default path](#kubectl-is-not-the-default-path). Missing Pods, a selector-key mismatch on live Pods, or not-Ready is the *why* after that finding, not instead of it.
     - If `drops[]` has per-target labels, keep rows whose `__meta_kubernetes_service_name` equals the matched Service and read `__meta_kubernetes_endpoint_port_name` on **that subset only**; empty subset → the Service never entered SD (no endpoints) — still not a port miss. ≠ `endpoints[].port` → port mismatch. Only `droppedCount` → do not infer the Service from the count. A user-written `relabel_configs` (not the generated port `keep`) that dropped the matched object → quote that rule.
   - **PodMonitor** — the named row on `pod-monitor list` (not in that `--help`):
     - `matchedPodCount` omitted or `0` is a selector miss. `discoveryTargets ≥ 1` with a generated `keep` whose `regex` equals a `matchLabels` value is that miss, not a port miss.
     - `endpoints[]` omitted when the endpoint is a numeric `targetPort` or `matchedPodCount` is 0 is not a port-name miss. `endpoints[].matchedTargetCount` omitted or `0` is a container port-name miss only after `matchedPodCount ≥ 1` and a named `port` is present.
     - Do not read `matchedServiceCount`. Do not call `--kind Service`. `--kind Pod` empty `200` is inconclusive — SD can still report `discoveryTargets ≥ 1`.
     - If `drops[]` has per-target labels, read `__meta_kubernetes_pod_*` on that subset, not `__meta_kubernetes_service_name`.
   - **Custom-job** — stop at the quoted drop rule. No `matched*` counts. `scrape_configs:` belongs to branch 2, not this branch.
5. **Job loaded with `finalTargets ≥ 1`, yet `up` has no series** — branch 2 has cleared the content → delivery or reload gap. Report both results; check collector `workloads[]` start times against the release `updateTime`.
6. **Targets kept and `up == 0`, or the probe ran and failed** → target-side. `The target url is insecure` is not this branch.
7. **Targets kept, probe `result.metrics[]` empty while `up == 1`** → inspect with `--include-raw-metrics`.
8. **Targets kept, probe returns metrics, query still empty** → re-check `storage list` `--prometheus-id`.

**Anti-patterns — do not do these:**

- Using the collection-rule token as `--job-name` or PromQL `job=`, or dropping `--addon-release-name` / reading `up{job=~"..."}` after a miss or 400. Resolve the scrape job name; do not widen.
- Treating `custom-discover-<id>` as a custom-job, or reading ServiceMonitor `matched*` / `--kind Service` on a PodMonitor (same-namespace Services can be unrelated).
- Calling port mismatch from a generated `keep` or from `matchedServiceCount ≥ 1` — classify from [branch 4](#differential-diagnosis) for **that** rule type.
- Using `job-target list` QueryFailed as a licence to `kubectl get` Services, Endpoints, or Pods, or listing those kinds cluster-wide after the named object is already in hand.
- Stopping on `resource list --kind Service` when [branch 4](#differential-diagnosis) still needs Endpoints / Pod facts.
- Turning `The target url is insecure` into a target finding, or carrying on after the [identity gate](#policy-identity-gate) has shown the `policyId` resolves to nothing.

## Report

Whole-policy report follows [Check Items](#check-items-whole-policy) in order, then a conclusion (health + anomalies + actions).

Targeted report — these headings, in this order; do not rename or swap:

- **Summary** — policy id / type / region, release, addon version, rule type / name / namespace, **resolved** scrape job names. Not one jammed line.
- The seven steps under their titles in [Targeted Collection Rule Diagnosis](#targeted-collection-rule-diagnosis). A `job-target list` 400 or ALL_DROPPED still keeps **Target status**; cluster-object evidence belongs in **Root cause**. Write the finding in product language; do not cite numbered items from [Differential Diagnosis](#differential-diagnosis).
- Close with the evidence chain and the fix pending confirmation per `integration-common.md`.

Each step carries this-rule evidence only. Mark a check that failed to run as `QueryFailed`. Workload scale and selectors belong on the addon release values when the schema exposes them; do not lead with a raw `kubectl patch`.

For a fix that changes the release, give the exact command and build its values per [Addon Release Config Update](integration-common.md#addon-release-config-update-hard-requirement). Re-verify with `check-scrape-config` scoped to the resolved scrape jobs, then `up{job="<resolvedJobName>"}` after one scrape interval. Propose only what the root cause calls for.

## Report Delivery

- Deliver the report as the turn's final output, once, with no tool call in the same step.
- Complete every in-scope check item, and close out the task list if one is in use, before writing the report.
- Do not restate a delivered report in a later step unless the user asks.

## Anomaly Rules

- Policy / addon / collector status not healthy per that command's `--help` → anomaly.
- `storage list` missing instance ID, or status abnormal → anomaly.
- `dashboard list` empty → warning.
- Monitor `enableStatus` is `disabled` → warning.
- Collection-path findings (job not loaded, all targets dropped, empty `up`, rejecting `message`, probe failure) → anomaly; classify with [Differential Diagnosis](#differential-diagnosis). `QueryFailed` is not an anomaly. A content lint that the dry-run contradicts is a note, except a rejecting `message` or a PrometheusYaml custom-job missing the `scrape_configs:` root key.
