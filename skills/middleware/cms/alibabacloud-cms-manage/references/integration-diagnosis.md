# Integration Policy Diagnosis

> This file builds on the global conventions in [SKILL.md](../SKILL.md) and on the shared onboarding rules in [integration-common.md](integration-common.md) — policy / addon / addon release concepts, release status determination, and collector health.

Use this workflow to run a health check on an integration policy — or on one collection rule under it — and emit a structured diagnostic report.

## Scope

Trigger when the user asks to diagnose, health-check, or troubleshoot:

- **Whole-policy diagnosis** — a policy identified by `<policy-id>`; run all [Check Items](#check-items-whole-policy).
- **Targeted diagnosis** — one addon release / collection rule under a policy (a custom collection such as `custom-discover-<id>`, a ServiceMonitor, a PodMonitor, an Exporter probe), usually named together with the policy. Run [Targeted Collection Rule Diagnosis](#targeted-collection-rule-diagnosis) instead of the full sweep; do not expand it into a whole-policy report the user did not ask for.

## Tooling

Complete the diagnosis with `aliyun cms2` subcommands, under the help-first rule in [SKILL.md](../SKILL.md#global-conventions). The two collection-path checks below are where that help falls short: it names neither the fields to read nor every flag the API requires.

### Policy type gate (hard pre-check)

Not every collection-path command works on every `policyType`, and an unsupported pair is rejected with `status 400: the environment(policy) type is invalid`. Only `check-scrape-config --help` documents this, under *Environment behaviour* — the others say nothing, so read the matrix rather than take the 400 for a flag error:

| Command | `CS` | `ECS` | Others (`PAI`, `HOST`, `BatchMetric`, `BatchLog`, `BAILIAN`, `AWS` …) |
|---------|------|-------|-----------------------------------------------------------------------|
| `collector list` | yes | yes | accepted, but these types run no collector, so `collectors[]` is empty |
| `custom-job list` | yes | yes | **400** |
| `check-scrape-config` | yes | yes, `customjob` sources only | **400** |
| `job-target list` | yes | yes | no collector, hence no `collectorReleaseName` to pass |
| `service-monitor list` | yes | **400** | **400** |
| `pod-monitor list` | yes | **400** | **400** |

The line falls between running a collector and not, so `ECS` keeps most of the path and only ServiceMonitor / PodMonitor are truly CS-only. `check-collector-target` is unmeasured; being collector-scoped like `job-target list`, it is reachable wherever a collector release exists.

That 400 is a verdict on the policy type rather than on the collection path: no [Differential Diagnosis](#differential-diagnosis) branch applies to it, and it is a planning error, not evidence. So read `policyType` off the `policy list` / `policy get` result before planning the sweep, then drop the unsupported commands and mark them not applicable. `addon-release list`, `storage list`, datasources, dashboards, and probes are policy-type agnostic and always run.

Never substitute a policy of another type for the one the user asked about, and never invent a `policyId` when the workspace holds none of the required type — say no diagnostic object exists and stop.

### Policy identity gate

A `400` on a `--policy-id` command means either that the ID resolves to nothing — deleted, mistyped, invented — or that the [policy type gate](#policy-type-gate-hard-pre-check) was skipped, and the message only hints at which (currently `Environment is not exist` from `addon-release list`, `The integration policy is not exist` from `policy get` / `collector list` / `custom-job list` / `service-monitor list`). Settle it on the status code instead of on that wording: `policy get --policy-id <policyId>` answering `2xx` hands the original 400 back to the type gate, while a `400` on `policy get` itself means there is no **diagnostic object** at all — stop, re-establish the ID from a `policy list` result, and report that none exists when nothing matches. Do not read on: a nonexistent ID makes `storage list` return `200` with an empty body, indistinguishable from a policy that genuinely has no Prometheus storage. Teardown inverts the same test, taking that `400` as positive evidence the environment was removed — see [Teardown](integration-common.md#teardown).

### Collection-path checks (mandatory)

| Command | Answers | Read these fields |
|---------|---------|-------------------|
| `aliyun cms2 integration check-scrape-config` | Dry-run of the **deployed** config: does it parse into a loadable job, what does service discovery yield, and what do relabel rules drop? | `passed`, `results[].failedPhase`, `summary.discoveryTargets` / `relabelKept` / `finalTargets`, `targets[].scrapeUrl` — its `--help` names none of these |
| `aliyun cms2 integration check-collector-target` | **Live probe** of one target URL: reachable? which metric names and sample counts does it actually expose? | `result.metrics[]`, `.samples[]` |

**`check-collector-target` and `job-target list` require more than their `--help` admits.** Both mark every flag but `--policy-id` an optional filter, and `check-collector-target --help` even offers a bare `--policy-id` call as its basic example, yet the API rejects:

| Missing flag | `status 400` |
|--------------|--------------|
| `--collector-release-name` or `--collector-name`, on either command | `integrationPolicyId and collectorReleaseName or collectorName must be set` |
| `--scrape-url`, on `check-collector-target` | `scrapeUrl is required` |

Both values come from earlier steps: `collector list --collector-type ClusterCollector` returns `collectors[].releaseName` — a field its own `--help` does not list — and `check-scrape-config` returns `results[].targets[].scrapeUrl`. Never assemble a scrape URL from an `instance` label.

A policy usually returns several collectors, so pick by `collectorName`: the scraping one is `metric-agent`, not `entity-collector`. Its `releaseName` has no single shape — `collector:metric-agent:policy:<policyId>` and `metric-agent-<uuid>-<timestamp>` both occur on CS policies, and ECS uses `collector:metric-agent:vpc:<vpcId>`, one entry per VPC. Read the value out of the response; never reconstruct it from the policy ID.

- Both checks are read-only and change no CMS or cluster state, even though `check-scrape-config` maps to a `POST` API. They need no write confirmation; run them directly.
- `check-scrape-config` is the **arbiter of whether the config can load**: `passed: true` with a `results[]` entry for the job proves that the config *as this check renders it* parses and yields targets, which settles any doubt raised by the shape of the submitted YAML. It does not prove the collector is running that job, and it does not overrule an explicit rejection carried on the delivered rule — the check re-renders the config server-side, while the collector consumes what was actually delivered, so the two can disagree. `passed: false` → `failedPhase` names the phase that broke.
- Read `drops[]`, not just `targets[]` — it separates "job never loaded" from "job loaded but every target relabelled away".
- `status 400: The target url is insecure` is the probe service declining to fetch that URL — a plain `http://` or otherwise non-permitted endpoint. It is **not** a verdict on the target: record the reachability check as `QueryFailed`, keep `scheme: http` out of the root cause and out of the fix, and fall back to the [`up` series](#up-is-the-reachability-oracle).
- On any other failure (permission, 4xx/5xx, timeout), handle it as `QueryFailed` per [Pagination & Query Failure Handling](../SKILL.md#pagination--query-failure-handling) and report the verbatim error with its `requestId`. A failed check does not license a `kubectl` substitute.

### `up` is the reachability oracle

The collector synthesizes `up` for every target it actually scrapes, so **no `up{job="<jobName>"}` series at all** is a verdict on config load, not on the target: the running collector never scraped this job — it is not in the effective runtime config, whatever the dry-run says. That it is absent is settled; *why* — content the backend rejected, or a valid config that never reached the collector — is branch 2 versus branch 5. `0` and `1` carry their usual Prometheus meaning, and `1` moves anything still missing downstream to metric relabel or the query.

Only read `up` this way after confirming the instance with `storage list` and querying a recent range — a wrong `--prometheus-id` also yields an empty result. This is the fallback whenever `check-collector-target` came back `QueryFailed`.

### Evidence fidelity (hard requirement)

Report what each command returned, quoting `passed`, `summary`, `failedPhase`, and error strings verbatim. Never write that a check returned nothing when it returned a result: a plausible branch of the [Differential Diagnosis](#differential-diagnosis) is not a licence to restate the evidence so it fits. When two checks disagree — the dry-run shows a target while the runtime shows none — carry both into the report and resolve them through branches 2 and 5, instead of dropping the inconvenient one.

### Evidence sources — use these, not `kubectl`

| Evidence needed | Command (filter with `--addon-release-name` / `--job-name` as the task allows) |
|-----------------|--------------------------------------------------------------------------------|
| Release status and the **submitted** values (`config`, a JSON string holding `configMapYamlTxt` etc.) | `aliyun cms2 integration addon-release list --policy-id <policyId>` |
| **Delivered** custom collection config (`CustomScrapeJobRule` CRDs) | `aliyun cms2 integration custom-job list --policy-id <policyId> --addon-release-name <releaseName>` |
| Delivered ServiceMonitor / PodMonitor CRDs | `aliyun cms2 integration service-monitor list` / `aliyun cms2 integration pod-monitor list --policy-id <policyId>` |
| Targets the collector actually discovered, with state | `aliyun cms2 integration job-target list --policy-id <policyId> --collector-release-name <collectorReleaseName>` |
| Whether a job's config parses and would load | `aliyun cms2 integration check-scrape-config --policy-id <policyId>` |
| Collector health, including pod-level detail in `workloads` | `aliyun cms2 integration collector list --policy-id <policyId> --collector-type ClusterCollector` |
| Metric samples in storage | `aliyun cms2 integration storage list --policy-id --addon-release-name --storage-type Prometheus` → `aliyun cms2 metric promql query --prometheus-id <status.instanceId>` |

Two response quirks:

- Always filter `custom-job list` by `--addon-release-name` in a targeted diagnosis. Unfiltered it also returns every built-in `cs-default` job, and the response grows large enough to be spilled to a file and read as a preview — which is how the rule under diagnosis ends up unexamined.
- An empty `job-target list` omits `jobs`, `targets`, and `totalCount` entirely, leaving only `maxResults` and `requestId`. That is a genuine "no targets", not a failed query — but read it together with `check-scrape-config` and the delivered rule's `message` before calling it a finding, per branches 2 and 5.

**`kubectl` is not part of this workflow.** Every evidence type above has a CLI source, which makes cluster-side probing — ConfigMap and CRD dumps, the collector's `/api/v1/targets` and `/api/v1/status/config`, Pod listings, collector log greps — redundant. Use it only after the corresponding command returned `QueryFailed`, label it as unverified side evidence, and never rest a root cause or a fix recommendation on it.

## Input

- Policy ID: `<policy-id>` (confirm exact value with the user; name-to-ID lookup must match exactly), plus its `policyType` per the [policy type gate](#policy-type-gate-hard-pre-check); an ID that resolves to nothing is settled by the [policy identity gate](#policy-identity-gate) before any check item runs.
- For targeted diagnosis: addon release name and/or `job_name` (confirm exact value; do not infer one from the other).

## Check Items (whole policy)

1. Policy basics: name, ID, type, region, workspace, status.
2. Addon (integration component) deployment status.
3. Datasource status.
4. Monitoring dashboard readiness.
5. Probe status: cluster probe, host probe, Exporter probe.
6. ServiceMonitor configuration and status.
7. PodMonitor configuration and status.
8. Custom collection configuration and status.
9. [Collection Config Content Validation](#collection-config-content-validation) for every rule from items 6-8.
10. Scrape config load status across all config sources.
11. Discovered targets and their state, plus live target reachability.
12. Data-plane verification: `up` and one expected series per job.

## Targeted Collection Rule Diagnosis

Run these steps in order. Do not jump to a root cause before step 6 completes.

Every command below takes `--policy-id`, plus `--region` and `-o json`; the [Evidence sources](#evidence-sources--use-these-not-kubectl) table holds the full form, and the [policy type gate](#policy-type-gate-hard-pre-check) decides which of them apply.

1. **Collector identity and health** — `collector list --collector-type ClusterCollector`: judge `state` and `workloads[]` against the health table in its `--help`, and keep `collectors[].releaseName` for step 5. That is the *collector's* release name, distinct from the addon release name used in steps 2-4.
2. **Release status** — `addon-release list`: locate the release, read its `conditions` (Loaded / Installed / Ready), version, `message`, and the submitted `config`.
3. **Config content** — fetch the delivered rule with `custom-job list` / `service-monitor list` / `pod-monitor list --addon-release-name <releaseName>`, then validate its `configYaml` **and** its `message` per [Collection Config Content Validation](#collection-config-content-validation). A `Ready` release only proves the config was **rendered and delivered**, never that it is **valid**.
4. **Scrape config load** — `check-scrape-config --addon-release-name <releaseName> --job-name <jobName>`: read `passed`, `summary`, `targets[]`, and `drops[]` together, and note each `targets[].scrapeUrl` for step 5.
5. **Target status** — `job-target list --collector-release-name <collectorReleaseName> --job-name <jobName>` for what the collector discovered at runtime, then `check-collector-target --collector-release-name <collectorReleaseName> --scrape-url <scrapeUrl>` to live-probe it.
6. **Data plane** — `storage list --addon-release-name <releaseName> --storage-type Prometheus` for the instance, then `metric promql query --prometheus-id <status.instanceId> --query 'up{job="<jobName>"}'` plus one expected series, read per [`up` is the reachability oracle](#up-is-the-reachability-oracle).
7. **Root cause** — apply [Differential Diagnosis](#differential-diagnosis) to the combined results, then write the report.

## Collection Config Content Validation

Whenever a collection release is in scope, look at the config **content**, not just its status: a rule reports `Ready` as soon as it is rendered and delivered.

Two artefacts carry that content, and they are not the same document:

| Artefact | Where | What it is |
|----------|-------|------------|
| Submitted values | `addon-release list` → `config` (JSON string; the YAML sits in `configMapYamlTxt` / `serviceMonitorYamlTxt` / `podMonitorYamlTxt`) | what the user typed |
| Delivered rule | `custom-job list --addon-release-name <releaseName>` → `configYaml`, or `service-monitor list` / `pod-monitor list` | what the backend rendered into the cluster |

**Judge the delivered artefact, and judge it by reading it.** The two documents can differ, so neither one vouches for the other. For `discoverType: PrometheusYaml` the delivered `configYaml` has to be a complete Prometheus document under a `scrape_configs:` root key — the shape the built-in `cs-default` rule shows in the same `custom-job list` response. A delivered `configYaml` that is a bare job list (`- job_name: ...`) is a defect no matter how the submitted values read, and no assumed backend normalization excuses it.

**The rule's own `message` is the backend's verdict on the content it delivered.** A string such as `ScrapeConfigs Invalid: scrape_configs is empty` is the controller rejecting the rule, not a cosmetic warning. Do not recast it as a hint from the rendering layer, and do not discount it because `check-scrape-config` passed — the two read different documents, so only a check against the *same* artefact can overturn it.

Lint the delivered config as Prometheus would, and for ServiceMonitor/PodMonitor check the selector and `endpoints[].port` against real cluster objects. A lint finding that `check-scrape-config` contradicts — job present, `passed: true` — is a note rather than an anomaly; carry it and keep going down the branches. The two exceptions are a rejecting `message` and a missing `scrape_configs:` root key, which the dry-run does not get to overrule.

## Differential Diagnosis

Walk the branches in order against the step 3-6 results. The first match is the root cause; the ordering is what keeps a config defect from being misread as a sync failure, and a sync failure from being misread as a config defect.

1. **Job absent from `check-scrape-config` `results[]`, or `passed: false`** → read `failedPhase`, then check the delivered config content. Content invalid → the config is the root cause and the collector never loaded the job; fix by updating the release values, and do not propose a restart, since an invalid config survives every restart. Content valid → the config did not reach the collector; check collector health with `collector list`, then have it reload.
2. **`check-scrape-config` passed, yet the delivered rule carries a rejecting `message` or its `configYaml` lacks the `scrape_configs:` root key** — `job-target list` and `up` are then typically empty too → the backend rejected the content it delivered, so the collector has nothing to run. The content is the root cause: fix the release values so the delivered artefact is a valid document — for `PrometheusYaml`, an explicit `scrape_configs:` root key — and do not propose a restart, which an invalid document survives. Quote the `message` and the delivered `configYaml`, and say why the passing dry-run does not clear the rule.
3. **Job loaded, `summary.discoveryTargets: 0` / `targets[]` empty** → service discovery matched nothing; fix the selector, `namespaceSelector`, port name, or `static_configs` targets.
4. **Job loaded, but every discovered target sits in `drops[]` (`relabelKept: 0`)** → `relabel_configs` drops them all; correct the offending rule and quote it in the report.
5. **Job loaded with `finalTargets ≥ 1`, yet `up` has no series at all** — branch 2 has already cleared the content, and `job-target list` is usually empty too → the dry-run and the runtime disagree: the config is valid and would load, but the collector is not running it. This is a delivery or reload gap, not a content defect, so do not re-litigate the YAML. Report both results side by side, then check collector health and the `workloads[]` start times against the release `updateTime`, and have the collector pick the config up.
6. **Targets kept and `up == 0`, or the probe ran and reported a connection or scrape failure** → target-side problem (network path, port, exporter, auth). A `The target url is insecure` rejection is not this branch — that probe never ran.
7. **Targets kept, probe returns `result.metrics[]` empty while `up == 1`** → the target exposes nothing the job wants, or `metric_relabel_configs` drops every series; inspect the exposed metrics with `--include-raw-metrics`.
8. **Targets kept, probe returns metrics, yet the query is still empty** → the storage / remote-write path, or a query against the wrong Prometheus instance or time range; re-check the `storage list` result and re-query with the correct `--prometheus-id`.

**Anti-patterns — do not do these:**

- Declaring a config-content defect the root cause while `check-scrape-config` reports the job loaded, or restating that check as having returned nothing so the defect becomes the answer. Branches 1 and 2 are the only entry points for a content root cause: branch 1 needs the job absent or `passed: false`, branch 2 needs the backend's own rejection on the delivered rule.
- Blaming config sync, or recommending a collector restart, because the job is missing from the scrape config, **without** having read the delivered config content first — or, with branch 2's evidence in hand, calling it a reload gap anyway.
- Explaining away a backend error string as advisory. `message` is evidence about the delivered artefact; only another check against that same artefact overturns it.
- Reaching two verdicts on one finding — dismissing it as "not a defect on its own" where the evidence is presented, then listing it in the root-cause evidence chain. Decide once: in the chain means anomaly, cleared means out of the chain.
- Treating `Ready` / `Loaded` / `Installed` conditions, or the mere existence of the delivered config, as evidence that the config is valid.
- Reporting only the symptom (job not loaded, no active targets) when the delivered config is in hand and its defect is visible in it.
- Reading `targets[]` without `drops[]`, or reporting that a job has targets when every one of them was relabelled away.
- Turning a failed check into a finding: `The target url is insecure` and `scrapeUrl is required` describe the probe call, not the target. `the environment(policy) type is invalid` is narrower still — it means the [policy type gate](#policy-type-gate-hard-pre-check) was skipped and the check should never have run on this policy type.
- Carrying on down the steps with a `policyId` the [policy identity gate](#policy-identity-gate) has already shown to resolve to nothing, or reading the empty `200` that `storage list` then gives back as a finding — there is no diagnostic object left to report on.

## Report Sections

Whole-policy report, in order:

- Policy summary
- Addon status
- Datasource status
- Dashboard status
- Probe status (cluster / host / Exporter)
- ServiceMonitor
- PodMonitor
- Custom collection
- Config content validation result across all three rule types
- Scrape config load status and target status
- Data-plane verification
- Overall conclusion: health assessment + anomaly summary + suggested actions

Targeted report: a summary line (policy, release, job, addon version), then the seven steps of [Targeted Collection Rule Diagnosis](#targeted-collection-rule-diagnosis) in order, each carrying its evidence — quote the offending config snippet, the `check-scrape-config` `passed`/`summary` values, the dropping relabel rule, and any probe error verbatim, and mark a check that failed to run as `QueryFailed` rather than folding it into a finding. Close with the root cause and its evidence chain, then the fix, pending user confirmation per the write-confirmation rule in [SKILL.md](../SKILL.md#global-conventions).

For a fix that changes the release, give the exact command, and build its values per [Addon Release Config Update](integration-common.md#addon-release-config-update-hard-requirement) — that section carries the body shape, the key format, and the decision of whether the change belongs on a fan-out child rather than the entry release. State the re-verification too: `check-scrape-config`, then `up{job="<jobName>"}` once a scrape interval has passed. Propose only what the root cause calls for; do not append speculative edits (a `scheme` switch, a restart) that no branch produced.

## Report Delivery

- Deliver the report as the turn's final output, once, with no tool call in the same step.
- Complete every in-scope check item, and close out the task list if one is in use, before writing the report.
- Do not restate a delivered report in a later step unless the user asks.

## Anomaly Rules

- Policy / addon / probe status not `Running` → anomaly.
- Datasource missing instance ID, or status abnormal → anomaly.
- Dashboard list empty → warning.
- Monitor `enableStatus` is `disabled` → warning.
- Custom collection `message` non-empty → needs attention; a validation or parse failure in it (`ScrapeConfigs Invalid: ...`) → anomaly and a root-cause candidate, which a passing `check-scrape-config` does not clear.
- Delivered config fails content validation **and** `check-scrape-config` shows the job absent or `passed: false` → anomaly, and the root cause. A content finding that `check-scrape-config` contradicts → note only, never the root cause — except a rejecting `message` or a missing `scrape_configs:` root key, which the dry-run does not overrule.
- Job not loaded (`passed: false`, or absent from `results[]`), or all of its targets in `drops[]` → anomaly; classify it with [Differential Diagnosis](#differential-diagnosis) instead of reporting the symptom alone. A partially non-empty `drops[]` → needs attention.
- `check-collector-target` connects and fails, or returns `result.metrics[]` empty → anomaly, quoting the reported error verbatim. A call the probe service refused, or rejected for a missing flag → `QueryFailed`, not an anomaly.
- `job-target list` empty while `check-scrape-config` reports `finalTargets ≥ 1` → anomaly, never a normal state and, on its own, never evidence that the config is invalid; settle which branch it is against the `up` result and the delivered rule's `message` (branch 2 versus branch 5).
- `up{job=...}` empty while the control plane reports `Ready` → anomaly; never conclude from control-plane status alone.
