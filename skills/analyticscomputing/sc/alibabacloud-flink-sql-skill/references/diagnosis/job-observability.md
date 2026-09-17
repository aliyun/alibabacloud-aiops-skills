# Querying Job Observability Data

Read after the [diagnosis entry point](README.md) identifies the required evidence, or when analysis requires additional evidence. This document defines query methods, authentication, and data semantics. It does not determine root causes or recommend optimizations.

## Contents

- [Query Preparation and Entry Points](#query-preparation-and-entry-points): authentication, identifiers, command templates, and availability.
- [Job Information and Execution Plan](#job-information-and-execution-plan): instances, SQL/configuration, topology, and TMs.
- [Metrics](#metrics): current snapshots, specified historical times, time ranges, and statistics.
- [Job Logs](#job-logs): runtime logs, startup logs, and exceptions.
- [Platform Events and Diagnosis](#platform-events-and-diagnosis), [Checkpoints and Savepoints](#checkpoints-and-savepoints).
- [Backpressure and Watermarks](#backpressure-and-watermarks), [Flame Graphs and Thread Dumps](#flame-graphs-and-thread-dumps).
- [Lineage](#lineage), [ResourcePlan](#resourceplan).

## Query Preparation and Entry Points

Run all commands from the project root through `python3 scripts/flink_sql_manager.py <command>`. See [command-reference.md](../command-reference.md) and the command's `--help` for complete arguments.

| Entry point | Scope | Authentication and boundary |
|-------------|-------|-----------------------------|
| Dedicated Ververica OpenAPI commands | Jobs, configuration, startup logs, events, lineage, resource plans, and similar data | Run `config_doctor` according to [configuration.md](../configuration.md) |
| `flink_api_proxy` | Current runtime information through an OpenAPI proxy to Flink REST | Uses the same OpenAPI authentication; available paths depend on the target engine |
| `get_metric_dashboard`, `get_metric_data` | VVP console historical Metrics | Uses independent Cookie authentication, without SDK credentials or `config_doctor` |

For OpenAPI queries, identify the target Job UUID with `list_jobs` and `get_job`, then confirm the corresponding Flink Job ID through proxied `/jobs`. Historical Metrics use the separate Cookie flow below.

### Identifiers and Incident Verification

| Identifier | Purpose | Source and verification |
|------------|---------|-------------------------|
| Region / Workspace / Namespace | Constrains the platform resource scope | Obtain from the actual URL, configuration, or user-confirmed information; do not copy values from another job |
| Deployment ID | Deployment configuration, instance list, events, and latest startup log | Does not identify one runtime instance |
| VVP Job UUID | Dedicated Job commands, proxy target, and historical Metric variables | Verify the owning Deployment and actual runtime |
| Flink Job ID | Job identifier in Flink REST paths | Obtain from a runtime response; do not reuse another Job's path |
| Vertex / Subtask / TM | Operator, concurrent instance, and process | Obtain from the target Job's runtime response; reconfirm after a restart |
| Checkpoint ID / Savepoint ID / ticket | Snapshot record, Savepoint, or asynchronous result | Obtain from the corresponding response; never interchange them |

Streaming-job restarts and repeated batch runs create distinct instances. When a list is paginated, read enough pages to cover the incident period. When only the current instance is needed, do not traverse unrelated history. A platform resource summary from the SDK or proxy is neither a real-time performance Metric nor a historical time series.

### Flink REST Proxy

The following is an invocation template. Resolve real IDs before requesting the required path:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '<flink-rest-path>'
```

Use the platform Job UUID for `resource_id` and the runtime ID for `<flink-job-id>` in a REST path. Obtain Vertex, Subtask, TM, and Checkpoint identifiers from actual responses. Parse proxy `data` first when it is a JSON string. This entry point does not proxy arbitrary VVP HTTP APIs and does not automatically provide historical data.

## Job Information and Execution Plan

| Data | Query method |
|------|--------------|
| Instance list and details | `list_jobs`, `get_job` |
| Deployment SQL, version, Flink configuration, and resource configuration | `get_deployment`; for a historical issue, compare against the corresponding Job rather than substituting the latest Deployment |
| Runtime topology, operator chains, parallelism, state, and upstream/downstream edges | Proxy `/jobs/<flink-job-id>` and extract Plan and vertices from the actual response |
| TaskManager list | Proxy `/taskmanagers` and retain real TM IDs for later queries |

From a Plan, extract `nodes[].description`, `parallelism`, `inputs[].ship_strategy`, and any actual exchange-mode field while preserving dependencies. Runtime topology, table/column lineage, and ResourcePlan describe different objects and do not substitute for one another.

### Deployment Configuration and Runtime Instances

Query Deployment SQL, engine version, Flink configuration, and resource configuration:

```bash
python3 scripts/flink_sql_manager.py get_deployment \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id>
```

List runtime instances for the Deployment, then retrieve the instance corresponding to the incident period:

```bash
python3 scripts/flink_sql_manager.py list_jobs \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id>
```

```bash
python3 scripts/flink_sql_manager.py get_job \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id> --job_id <job-uuid>
```

Use `--page_index` and `--page_size` to continue through paginated `list_jobs` results. Deployment configuration may have changed after the Job started and cannot automatically be treated as the effective configuration of a historical instance.

### Runtime Topology and Plan

First identify the Flink Job ID for the proxy target, then query the topology, Vertices, and Plan of that runtime instance:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>'
```

Use the runtime ID returned by `/jobs` for later paths; do not derive it from the platform Job UUID. Inspect the following content across Deployment, instance, and runtime responses:

| Object | Fields or content | Notes |
|--------|-------------------|-------|
| Deployment / Job | `deploymentId`, `jobId`, `engineVersion`, `executionMode`, state, and start/end time | Fields vary by response; distinguish platform state from runtime state |
| Artifact | `artifact.kind`, SQL script, or configuration for the corresponding kind | Do not assume JAR, Python, or CDC YAML Artifacts contain SQL scripts |
| Configuration | `flinkConf`, actual resource configuration, logging, and restore settings | Do not invent defaults for missing fields; redact before display |
| Vertices | ID, name, state, parallelism, and runtime summary | One Vertex may contain an entire operator chain |
| Plan | Node descriptions, input edges, and distribution strategies | Node order does not represent data-flow direction |
| TM | ID, address/heartbeat, Slots, or resource information when returned | Query CPU and memory performance from actual Metrics |

Example Plan fields (structure only, not an actual Job result):

```json
{
  "plan": {
    "type": "STREAMING",
    "nodes": [
      {
        "id": "<vertex-id>",
        "parallelism": 4,
        "description": "Calc",
        "inputs": [{"id": "<upstream-vertex-id>", "ship_strategy": "FORWARD"}]
      }
    ]
  }
}
```

Reconstruct upstream/downstream edges through `inputs`. For display, convert `<br/>` to line breaks and retain only relevant Plan fragments. Record configured parallelism, generated-plan parallelism, and actual runtime parallelism separately.

### TaskManager and Subtask Mapping

Enumerate current TaskManagers, retrieve the target Vertex's Subtask locations, and query the corresponding TM details:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>'
```

Build Subtask → TM mappings from actual fields. When no mapping field is returned, do not pair items by list order. TM details verify the process, Slots, and resource information; query CPU and memory usage through Metrics below. The current TM list does not represent a TM that exited during an earlier incident.

## Metrics

### Current Time

Choose the path for the target entity. First enumerate Metric IDs without `?get=`, then retrieve values with `?get=<metric-id>[,<metric-id>...]`. Determine meaning from the name, unit, entity attributes, and Job context; do not use the user's natural-language phrase directly as a physical Metric name.

| Entity | Flink REST path |
|--------|-----------------|
| Job | `/jobs/<flink-job-id>/metrics` |
| Vertex | `/jobs/<flink-job-id>/vertices/<vertex-id>/metrics` |
| One Subtask | `/jobs/<flink-job-id>/vertices/<vertex-id>/subtasks/<subtask-index>/metrics` |
| Subtask aggregate | `/jobs/<flink-job-id>/vertices/<vertex-id>/subtasks/metrics` |
| JobManager | `/jobmanager/metrics` |
| TaskManager | `/taskmanagers/<tm-id>/metrics` |

Record retrieval time, entity, Metric ID, value, and unit. The current API does not support arbitrary historical times, and multiple requests are not one atomic snapshot. A Subtask aggregate is not a per-instance breakdown; query individual Subtasks when distribution matters.

#### Metric Enumeration

The example below uses a Vertex. For another entity, use its path from the table above, also enumerating without `?get=` before putting returned IDs into a value query.

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>/metrics'
```

#### Job Metrics

Retrieve Job-level Metrics. Replace placeholders with IDs enumerated for that Job.

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/metrics?get=<metric-id-1>,<metric-id-2>'
```

#### Vertex Metrics

Retrieve Metrics for the target Vertex. One Vertex may contain several chained operators; use actual ID prefixes, names, and the Plan to identify ownership.

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>/metrics?get=<metric-id-1>,<metric-id-2>'
```

#### Subtask Metrics

To inspect one concurrent instance, use its actual Subtask index:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>/subtasks/<subtask-index>/metrics?get=<metric-id-1>,<metric-id-2>'
```

For an aggregate across the Vertex's Subtasks:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>/subtasks/metrics?get=<metric-id-1>,<metric-id-2>'
```

Parse aggregate responses according to their actual aggregate fields; do not reconstruct each Subtask value from them. Query relevant Subtasks individually to compare instance distributions.

#### JobManager Metrics

Query Metrics for the JM process, such as memory, GC, or CPU IDs found during enumeration.

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobmanager/metrics?get=<metric-id-1>,<metric-id-2>'
```

#### TaskManager Metrics

Use a confirmed TM ID to query that process. Query multiple TMs separately; do not treat one process's value as a Job total.

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>/metrics?get=<metric-id-1>,<metric-id-2>'
```

#### Data Types and Entity Semantics

| User concern | Confirm during the query |
|--------------|--------------------------|
| Input, output, throughput | Whether the value is a cumulative record count or a rate per unit time, and whether it belongs to a Source, Vertex, chained operator, or Sink |
| Busy, idle, backpressure | Units for time proportion or per-second rate and Subtask aggregation; do not interpret directly as CPU |
| CPU | Process or host, percentage or ratio, CPU time or utilization, and whether it is normalized by core count |
| Memory and GC | Heap, Non-Heap, Direct, Managed, and process total with units; GC count versus cumulative duration |
| State and Checkpoint | Full State, current bytes written, incremental upload, or repeated sampling of the latest Checkpoint |
| Watermark, latency, backlog | Timestamp, time difference, or record count, including actual meaning and owning input/entity |
| Connector Metric | Connector version, source partition, call/cache/retry/commit meaning, and whether it is actually reported |

When a Metric is missing, first verify enumeration, entity level, instance, and engine support. Do not silently substitute a similar name. This document does not maintain a fixed dictionary of business Metric names.

### Specified Historical Time and Time Range

For a specified historical time, query a nearby time window and report actual sample time and offset from the target. If there is no matching sample, do not substitute a current value or interpolate. For a time-range query, retain each series, label, and sample before computing the requested statistic.

#### Query Flow

1. Check whether the current conversation already contains a user-provided Cookie or the runtime has `VVP_COOKIE`; check existence only and do not echo the value.
2. If there is no Cookie, ask the user to **open the Job URL, press F12, select Network, choose a request to the same VVP host, open Headers, and copy the Cookie request-header value**. Then wait; do not extract browser credentials yourself.
3. Obtain region, Workspace, Namespace, and Deployment ID from the Job URL or confirmed configuration. Use `get_metric_dashboard` to retrieve the Job UUID, dashboard title, unit, and Target expression, then choose the `dashboard_id`, `panel_id`, and `ref_id` matching the user's intent. Do not hard-code a panel or Metric name; ask the user if ambiguity remains.
4. Fix the start and end times and call `get_metric_data` with the same Cookie. On success, compute the requested result from actual entities and samples. On failure, explain the reason; do not treat an empty result as zero.

Pass the Cookie only through in-process `VVP_COOKIE` or `--cookie_stdin`; TTY input is hidden. When an environment variable already exists, omit `--cookie_stdin`. For a value supplied in the conversation, pass it through hidden standard input. Never put the Cookie in command arguments, files, configuration, logs, or Git, and never output request headers. These commands validate their own scope and Cookie; they do not require SDK credentials or `config_doctor`.

#### CLI

```bash
python3 scripts/flink_sql_manager.py get_metric_dashboard \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id> --cookie_stdin

python3 scripts/flink_sql_manager.py get_metric_data \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id> --job_id <job-uuid> \
  --dashboard_id <dashboard-uid> --panel_id <panel-id> --ref_id <ref-id> \
  --start_time <unix-seconds> --end_time <unix-seconds> --step 5 --cookie_stdin
```

`get_metric_dashboard` discovers dashboards and query targets; `get_metric_data` returns the selected target's time series. `--start_time` and `--end_time` use Unix seconds; `--step` is the sampling step in seconds. Adjust the example value of 5 to the required precision.

The dashboard command uses the latest streaming Job by default; append `--job_id` for a specific runtime instance. If a time window spans a restart, identify each affected Job UUID, query it separately, and state coverage. Do not substitute an old Job for the current Job.

## Job Logs

### Runtime Logs

#### Log File List

First enumerate log files for the JM and target TMs. For multiple TMs, obtain every ID from the current Job's TM list.

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobmanager/logs'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>/logs'
```

#### Log File Content

Path-encode and read a filename returned by the list; do not guess a filename:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobmanager/logs/<filename>'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>/logs/<filename>'
```

#### stdout

Query the standard-output entry points provided by the target engine:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobmanager/stdout'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>/stdout'
```

`flink.log`, `flink.out`, and GC logs are only possible file types. Do not assume filenames, rotated files, or that every TM has every log. Record the owning process, file, and actual time coverage. For historical segments, distinguish log rotation, an exited instance, and API failure. The current proxy does not guarantee logs for an exited TM and is not a centralized log-search service.

#### Filtering Logs

For returned logs or local logs supplied by the user, use a read-only search to extract context, for example:

```bash
rg -n -C 20 -- 'OutOfMemoryError|CheckpointException|<user-keyword>' <log-file>
```

Keywords are examples. Select them from the user's issue and retain surrounding exception context rather than only one error line.

#### Completeness and Multi-Process Checks

1. Determine whether to inspect the JM, a specified TM, or every relevant TM, recording instance IDs and log coverage.
2. Distinguish stdout, application logs, and GC logs. Empty stdout does not prove that an application has no errors, and GC files do not have a guaranteed name.
3. Search a narrow window around an exception first, then inspect context and rotated files as needed. When REST returns a file's content, do not assume server-side time or keyword filtering.
4. Retain the full causal stack for multi-line exceptions. Distinguish the first failure from later retry, cancellation, or Failover effects.
5. When a response limit is reached, rotated files are missing, or a TM has exited, state that coverage is incomplete; do not call it “all logs.”
6. Organize multiple TM results by process and time. Do not mix logs from another Job or a replacement process into the same incident.

### Startup Logs

Use `get_start_log`. The current implementation invokes `GetLatestJobStartLog` to get the latest startup log by Deployment. Although the command requires a Job ID, that does not mean it can return the startup log for any historical Job. Verify response time and instance; report a historical coverage gap when they do not match.

```bash
python3 scripts/flink_sql_manager.py get_start_log \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id> --job_id <job-uuid>
```

Verify startup stage, first/last time, key error, and instance relationship. When it does not match the historical Job, stop correlating the log with the incident.

### Exceptions

Proxy `/jobs/<flink-job-id>/exceptions` for available exceptions, then read matching JM/TM log context as needed. Use time, component, and stack to distinguish the initial exception, later propagation, and retry exceptions. An empty response does not prove that no exception occurred during the incident period.

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/exceptions'
```

The response may contain structures such as `root-exception`, `all-exceptions`, or `exceptionHistory`. Parse actual results and retain time, task/host, exception type, and truncation flags. The exception list does not replace all runtime logs.

## Platform Events and Diagnosis

- `get_events`: query Deployment runtime events, checking event time and associated Job. Do not assume arbitrary time-range filters or complete history.
- `diagnose_job`: query the platform's diagnosis for a specific Job. Label it “platform-reported diagnosis”; do not treat it directly as an agent-verified root cause.

```bash
python3 scripts/flink_sql_manager.py get_events \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id>
```

```bash
python3 scripts/flink_sql_manager.py diagnose_job \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id> --job_id <job-uuid>
```

Retain event time, type, message, instance relationship, and the platform's original diagnosis.

## Checkpoints and Savepoints

- `get_checkpoints`: query summaries of completed, failed, and in-progress Checkpoints and records retained by the backend.
- Proxy `/jobs/<flink-job-id>/checkpoints/details/<checkpoint-id>`: query one Checkpoint and extract actual fields such as operator duration, State, or uploaded bytes.
- `list_savepoints`, `get_savepoint`: query existing Savepoints and their details; a query does not create, delete, or restore anything.

Distinguish Checkpoint bytes written, incremental upload, and full State size according to backend semantics. Retained Checkpoint records are not a historical Metric time series; a finite list is not complete history for an arbitrary interval.

### Checkpoint Summary

```bash
python3 scripts/flink_sql_manager.py get_checkpoints \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id> --job_id <job-uuid>
```

### Checkpoint Details

Obtain the Checkpoint ID from the target Job's summary response, then retrieve that record:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/checkpoints/details/<checkpoint-id>'
```

| Level | Extract |
|-------|---------|
| Summary | `counts`, `summary`, `latest`, and the actual retained history |
| One record | ID, state, trigger/completion time, end-to-end duration, and failure message |
| Operator details | Acknowledgments, duration, State, or snapshot volume by Vertex; interpret actual fields |
| Finer details | Subtask, alignment, synchronous, and asynchronous phase data actually provided by the backend; do not fill missing data |

Use Checkpoint IDs from the current target Job, not same-numbered records from another Job. In-progress values may be incomplete; a cumulative failure count is not necessarily the count during an incident period.

### Savepoint List and Details

First list Savepoints for the Deployment, then retrieve details by a returned Savepoint ID:

```bash
python3 scripts/flink_sql_manager.py list_savepoints \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id>
```

```bash
python3 scripts/flink_sql_manager.py get_savepoint \
  -w <workspace> -n <namespace> -r <region> \
  --savepoint_id <savepoint-id>
```

Record Savepoint state, creation time, location, and owning instance when returned. A path does not prove restore compatibility and does not trigger restore or deletion.

## Backpressure and Watermarks

### Backpressure Details

Query sampling state and per-Subtask backpressure for the target Vertex:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>/backpressure'
```

Engines may return sampling state, an overall level, per-Subtask levels, or ratios. Distinguish “not completed/no sample” from “low backpressure.” When sample time is present, verify freshness rather than treating an old sample as current.

### Watermarks

Query Watermarks for the target Vertex and Subtasks:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>/watermarks'
```

Distinguish input and output Watermarks and their owning Subtasks, and interpret actual fields. Convert ordinary Watermark timestamps using their units; mark sentinel values such as `Long.MIN_VALUE` as uninitialized rather than formatting them as normal business dates.

These APIs provide a sample or snapshot. Query reported historical Metrics when a trend is required; one value cannot prove persistent backpressure or a stalled Watermark.

## Flame Graphs and Thread Dumps

Use `flink_api_proxy` for the APIs below.

### Flame Graph APIs and Sampling Behavior

| Target | GET path | Parameters | Behavior |
|--------|----------|------------|----------|
| Vertex / Subtask | `/jobs/<flink-job-id>/vertices/<vertex-id>/flamegraph` | `type`, optional `subtaskindex` | Returns a thread-stack sample tree and may trigger sampling |
| JobManager | `/jobmanager/flame-graph` | `profilingEvent`, `profilingDurationSeconds` | Requests process profiling and returns a generated filename and start time |
| TaskManager | `/taskmanagers/<tm-id>/flame-graph` | Same as JM | Requests process profiling for the specified TM |

The operator path is `flamegraph`; JM/TM paths use `flame-graph`, and their parameters differ:

- Operator `type` supports `full`, `on_cpu`, and `off_cpu`, defaulting to `full`. `on_cpu` filters by RUNNABLE/NEW thread state and `off_cpu` by waiting or blocked state; neither is equivalent to precise hardware CPU sampling. `subtaskindex` selects a real Subtask index; omission selects the Vertex scope.
- In the inspected implementation, JM/TM `profilingEvent` supports `cpu`, `alloc`, `nativemem`, `lock`, `wall`, and `itimer`, defaulting to `cpu`. Whether an event works still depends on the runtime environment and profiling tool.
- `profilingDurationSeconds` is a positive integer in seconds and defaults to 10 in the inspected implementation. Use an explicitly confirmed duration rather than treating this local default as fixed across engine versions.

Although these APIs use GET, they can start sampling, add runtime overhead, and write output files. First define the target, type, duration or scope, and sampling impact. Execute when the user has authorized sampling of the current target; otherwise request confirmation. To inspect an existing result, prefer reading an already generated file and do not trigger new sampling by default. Do not profile every TM concurrently.

### Operator Flame Graph

This is a request template, not evidence that sampling was performed:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobs/<flink-job-id>/vertices/<vertex-id>/flamegraph?type=on_cpu'
```

Append `&subtaskindex=<subtask-index>` to inspect one Subtask. Operator-sampling duration/frequency comes from engine configuration and does not use the JM/TM duration parameter.

The response contains `endTimestamp` and `data`; tree-node `name`, `value`, and `children` represent stack location, sample hits, and child nodes. The inspected implementation uses these states:

| Response | Meaning and handling |
|----------|----------------------|
| Valid `data` and sample end time | A sample tree was obtained; record actual sample time rather than assuming request time |
| `endTimestamp=-3`, no tree | Awaiting the first sample; check back a limited number of times according to the target engine's sampling period, without high-frequency polling |
| `endTimestamp=-2`, no tree | Feature disabled; inspect `rest.flamegraph.enabled` without changing configuration or restarting automatically |
| `endTimestamp=-1`, no tree | Target execution ended; use existing results and do not restart automatically for evidence |

These sentinels are neither normal timestamps nor “CPU is zero.” The API may reuse an existing sample or refresh stale data; repeated calls are not guaranteed to read only cached data.

### JM/TM Flame Graphs

After obtaining explicit profiling authorization, request CPU profiling with these templates:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobmanager/flame-graph?profilingEvent=cpu&profilingDurationSeconds=<seconds>'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>/flame-graph?profilingEvent=cpu&profilingDurationSeconds=<seconds>'
```

Handling flow:

1. Preserve returned `generatedFileName` and `profilingStartTimestamp`. The inspected implementation returns after starting profiling, before the file necessarily exists.
2. Wait for the selected duration and necessary generation time, then read the returned filename through the same process's log-file entry point: `/jobmanager/logs/<generatedFileName>` for JM or `/taskmanagers/<tm-id>/logs/<generatedFileName>` for TM. Path-encode the filename.
3. If the file is temporarily unavailable, check the file entry point a limited number of times. Do not invoke `flame-graph` repeatedly and start new profiling sessions. A failure or timeout may occur after profiling has started; first inspect existing results and logs.
4. The inspected implementation writes SVG to the process log directory, and a later sample for the same event replaces the same-named result. Retrieve an old file before resampling if it must be retained; never present an old file with the same name as the current result.
5. Report successful flame-graph generation only after obtaining the actual SVG or another result returned by the target version. If the request succeeds but the file is absent, distinguish profiling in progress, generation failure, process exit, and unsupported proxy file access.

#### Read a Flame Graph Result

After profiling completes, read the returned `generatedFileName` from the same process:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobmanager/logs/<generatedFileName>'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>/logs/<generatedFileName>'
```

To inspect an existing flame graph, first enumerate files through the runtime-log flow and substitute an actual filename. Path-encode filenames. Reading a file and triggering profiling are distinct operations.

### Availability and Failure Handling

- API absent or rejected by proxy: verify target version, path, and permissions; do not conclude immediately that flame graphs are unsupported.
- Operator feature disabled, target ended, or sampling pending: report the actual state; do not collapse them into “no data.”
- JM/TM profiling failure: inspect the actual error and process logs. It may involve profiling scripts, native tools, event support, or system permissions; do not install tools or elevate permissions automatically.

### Thread Dumps

Read the current threads of the JM or a specified TM:

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/jobmanager/thread-dump'
```

```bash
python3 scripts/flink_sql_manager.py flink_api_proxy \
  -w <workspace> -n <namespace> -r <region> \
  --resource_type jobs --resource_id <job-uuid> \
  --flink_api_path '/taskmanagers/<tm-id>/thread-dump'
```

Extract thread names, states, and relevant frames, preserving waiting objects or lock information when returned. One WAITING/BLOCKED stack is not proof of a deadlock. Stacks from different times can support further analysis, but this query does not itself establish a root cause.

### Sampling Semantics

Verify the owning Job, process/TM, operator or thread scope, sample time, and effective sample count. Distinguish CPU, wall-clock, allocation, and other modes and their weight meanings. Do not interchange sample proportions, duration, and allocation volume. Check missing symbols, truncation, pre-restart instances, and other coverage limits.

Leave hotspot attribution to in-depth analysis. Heap Dumps, Arthas attach/watch, and changing log levels are outside flame-graph queries.

## Lineage

Use `get_lineage`, setting `--lineage_id` and `--lineage_id_type` from a real object, and select `--direction`, `--depth`, and `--is_column_level` as needed.

Distinguish table-level from column-level lineage. Upstream is the data-source direction, and downstream is the data-destination direction. The root node, direction, and depth determine coverage. An empty response does not prove no dependencies, and a lineage graph is not a runtime operator topology.

### Example

```bash
python3 scripts/flink_sql_manager.py get_lineage \
  -w <workspace> -n <namespace> -r <region> \
  --lineage_id <job-or-table-id> --lineage_id_type <JOB-or-TABLE> \
  --direction BOTH --depth <depth>
```

Append `--is_column_level` for column-level lineage and use `--is_temporary` for a temporary table when applicable. Root-node type, direction, and depth affect coverage; parse returned nodes and edges from the actual response.

Missing lineage may reflect absent metadata collection or API coverage. The query layer does not guess actual dependencies.

## ResourcePlan

- **Read an existing result:** when a real ticket is available, use `get_resource_plan_result --ticket_id <ticket-id>`.
- **Request generation:** when no result exists and the user requests one, use `generate_resource_plan --deployment_id <deployment-id>`, with a confirmed `--body_json` configuration when necessary; query the result after obtaining the real ticket.

Resource-plan generation is asynchronous. It is not a read of the running instance's resource snapshot and does not deploy the plan. Do not start generation by default for a data-only query. State the SQL/configuration version used, and do not present a newly generated plan as historical runtime resource configuration. Query actual resources and configuration through “Job Information and Execution Plan.”

### Example and Asynchronous Result

Read an existing result:

```bash
python3 scripts/flink_sql_manager.py get_resource_plan_result \
  -w <workspace> -n <namespace> -r <region> \
  --ticket_id <ticket-id>
```

Use only when the user asks to generate a plan:

```bash
python3 scripts/flink_sql_manager.py generate_resource_plan \
  -w <workspace> -n <namespace> -r <region> \
  --deployment_id <deployment-id>
```

To override Flink configuration, first verify the `--body_json` structure accepted by the command and backend; do not construct unknown fields from natural language. After generation returns a ticket, query only that ticket. Distinguish in-progress, failed, timed-out, and completed states; do not report “request accepted” as generation success.

Extract the actual operator/chain, parallelism, CPU, memory, or Slot groups returned in the result. Preserve the SQL/configuration and generation time on which the plan is based when available. When comparing it with runtime resources, state the difference in semantics.
