# DTS Synchronization Job Status

## Contents

- [Region parameter requirements](#region-parameter-mapping)
- [List jobs](#list-jobs)
- [Locate a job by name](#job-name-resolution)
- [Query one job](#query-one-job)
- [Status interpretation](#state-interpretation)
- [Stage mapping](#stage-mapping-table)
- [Incremental synchronization delay](#delay-semantics)
- [Precheck](#precheck)
- [Failure-state handling](#failure-state-query-sequence)

> API version: DTS `2020-01-01`. [DescribeDtsJobs](https://help.aliyun.com/en/dts/developer-reference/api-describedtsjobs), [DescribeDtsJobDetail](https://help.aliyun.com/en/dts/developer-reference/api-describedtsjobdetail), and [DescribePreCheckStatus](https://help.aliyun.com/en/dts/developer-reference/api-describeprecheckstatus) define the job-list, job-detail, and precheck facts used here.

<a id="region-parameter-mapping"></a>
## Job region requirements

Every job query and lifecycle command in this Skill takes the same business parameter, `--region <region-id>`, naming the DTS job's region. The CLI uses it to select the service entry point and to fill the DTS API region fields, so callers never handle those field names.

Obtain an explicit DTS job region before a query. If the user has not provided one, ask; never infer it from the CLI default region, the source or destination database region, or the job name. Whether or not the source and destination databases are cross-region, pass the confirmed DTS job region, which may differ from either database's region.

<a id="list-jobs"></a>
## List jobs

```bash
dtscli job list --region <region-id> --page 1 --page-size 10
```

The command always queries the synchronization job type and never expands synchronized objects internally, rather than relying on CLI defaults.

- Page numbers start at 1. `--page-size` accepts 1 to 30; this Skill queries page 1 with 10 records by default.
- To narrow by name, add `--job-name`. The service match is fuzzy; exact-match locally on this page as in [Locate a job by name](#job-name-resolution).
- Query one page by default. It returns `total_count` and the page's `jobs` array; report the page count and the total, and when the total exceeds this page, state how many records remain undisplayed and ask whether to retrieve the next page; never enumerate every job automatically.
- Group the **current page** by raw `status`. Each row carries only job ID, DTS instance ID, name, and status; the region is the one passed in and need not be repeated per row. Never present current-page counts as totals for all jobs, and never describe one page as the complete result.
- The listing contains no synchronized objects, endpoint objects, raw error text, `request_id`, or raw API JSON; never ask for or relay those.
- Treat the job name as non-unique. Locate a job only through the exact unique-match workflow below; never use the first record returned by the fuzzy search.

<a id="query-one-job-by-dts-instance-id-for-purchase-verification"></a>
### Locate a job by DTS instance ID (for purchase verification)

To verify an instance purchased by a creation attempt, use `dtscli job get --job-id <job-id> --region <region-id>` when a job ID is known.

With only an instance ID and no job ID, page through `dtscli job list --region <region-id> --page-size 30` in the confirmed DTS job region and compare `instance_id`. This is a named exception to the list rules: paging is allowed here because it verifies one instance the user already supplied, and it ends in exactly one of three ways:

- exactly one match: run `job get` with that row's `job_id`;
- more than one match: report that the instance ID maps to several jobs, stop before any write, and ask the user which one to use;
- no match after paging through `total_count`: report that the instance was not found in this region rather than that it does not exist, and ask the user to check the DTS console.

Never retry creation in any of the three cases. The default first page holds only 10 records and is not enough to conclude anything; this exception does not apply to routine [list jobs](#list-jobs) queries.

<a id="job-name-resolution"></a>
## Locate a job by name

`DescribeDtsJobs` uses fuzzy matching for `Type=name`. When a user identifies a target by job name, use `job list --job-name` to narrow the page, then exact-match locally:

```bash
dtscli job list --region <region-id> --job-name <job-name>
```

- Compare the complete job name case-sensitively; prefixes, substrings, and differently cased strings are not matches.
- The CLI returns one page. An empty `jobs` array with `total_count=0` means not found. If this page has no exact match and more pages remain, ask whether to retrieve the next page; never scan the entire result set automatically.
- Report not found when there is no exact match. Report an ambiguous name when more than one job has the exact name. Do not continue to a write in either case.
- Only one exact match may proceed. Use that row's `job_id` with `dtscli job get --job-id <job-id> --region <region-id>`. Later precheck and management use this ID only.
- Creation does not look up existing jobs by name and does not reuse a job because the name already exists.

<a id="query-one-job"></a>
## Query one job

```bash
dtscli job get --job-id <job-id> --region <region-id>
```

Use `job get` for routine detail queries and post-write verification. It calls `DescribeDtsJobDetail` once, verifies the returned job ID, converts detail `Delay` from milliseconds to seconds, and preserves the raw `job_type` and `status`. A missing type is never inferred as `SYNC`. Compare `SYNC` case-insensitively; `sync` is the same word and is not a missing type. Non-`SYNC` jobs remain available for read-only reporting and must not continue to a write.

`management` describes the management boundary: `eligible` indicates whether supported management metadata is available, `reasons` explains refusal, and `scope` supplies the direction and safe endpoint fields for review. The CLI compares job type, direction, engines, and access types after ASCII case folding and display-name aliases (`MySQL`/`MYSQL`, `PolarDB`/`POLARDB`); it does not rewrite the raw `scope` values. A blank `SynchronizationDirection` on a one-way job with no reverse or compound evidence is treated as Forward for eligibility only. Equal owner IDs with no cross-account roles are same-account. Both owner IDs absent and no roles are also same-account, with `account_inferred=true`. A role name or unequal owner IDs is cross-account and blocks writes. A single-sided owner ID remains unknown and blocks writes. MongoDB also requires replica-set architecture evidence on both sides. Follow [pre-execution review and confirmation](job-lifecycle.md#pre-execution-review-and-confirmation) when using these fields for lifecycle operations. The CLI checks scope again before writing. Use `eligible`; do not apply a second inference.

If the job's source or destination database does not satisfy the [database instance access boundary](database-instance-configuration.md#database-instance-access-boundary), report the read-only query result but do not continue to a management operation.

If a read-only query reveals a bidirectional job or reverse-direction sub-job, identify it as outside this Skill's management boundary and stop before a write.

Judge the job only from the raw `status`. When the value is not in the lifecycle table, report it as-is and stop before a write; never classify it yourself.

The three stage statuses (`structure_status`, `full_status`, `incremental_status`) are reported per stage. An empty string and `null` mean the same thing: this response carries no status for that stage. That empty value can mean either "not reached yet" or "already finished and no longer reported", so never present it as not started, running, or complete:

- Structure and full initialization are reported only while the job is initializing or when that stage failed. Once the job reaches `synchronizing`, these two fields usually disappear; at that point the top-level status supports saying the enabled structure and full stages have finished without failing, but never present that as a `Finished` value from the service.
- Which stages are enabled is decided by the creation-time stage selection (incremental is always on). Use the creation input or the console to establish what this job was supposed to run.
- Incremental status keeps being reported once incremental starts; interpret it per [incremental health](#incremental-synchronization-health-signal).

Trade-off between stage selection and top-level status: `Initializing` means the enabled stages are initializing or the job is moving into incremental; `synchronizing` means incremental has started. Any other top-level status follows [lifecycle states](#lifecycle-states).

For a routine status request, render only the user-relevant fields below; do not echo the command's JSON:

| Category | Fields |
| --- | --- |
| Identity | Job ID, instance ID, name, and region |
| State | Overall state and the active or failed stage |
| Stage | Structure initialization, full initialization, and incremental synchronization status |
| Synchronization | Latency converted to seconds after incremental synchronization starts |
| Failure | Redacted cause and one concrete next action when unhealthy |

For an explicit detail or scope-inspection request, use the allowlisted `DescribeDtsJobDetail` query to add source and destination products, database instance or cluster identities, database/table-or-collection counts and mapping summary, and all available phase progress. Synchronized objects come back only with `--with-db-list`: the resulting `db_list` is decoded structured JSON, so report it as database, schema, table or collection levels and never echo the service's raw `DbObject` string. Its type keys keep the service's engine-neutral naming (for example `Table`), which means collection under MongoDB; never read the key name as the engine's own term. `job get` returns only the forward sub-job and has no flag for historical sub-jobs. Never emit usernames, passwords, IPs, ports, complete `SourceEndpoint` or `DestinationEndpoint` objects, CLI arguments, script status codes, or raw API JSON. Omit `request_id` from routine output and report it only when the user asks for support metadata or an ambiguous result needs corroboration.

### When a job has failed

When the top-level `status` from `job get` is `PrecheckFailed`, `InitializeFailed`, or `Failed`, report the failure from the stage fields already on `job get`. For `PrecheckFailed`, use `dtscli job precheck` for redacted items. For other failures, ask the user to check the original step error in the DTS console. Never call `list-job-step` or treat error text as a confirmed root cause.

### Output and failure handling

On success, `job get` emits one object with `job_id`, `instance_id`, `job_name`, `job_type`, `status`, the three synchronization-stage statuses, `delay_seconds`, `management`, and optional `request_id`; `--with-db-list` adds the structured `db_list`.

On failure, standard output holds an object containing `error_class` and the exit code is non-zero. Decide what to do from `error_class` rather than the exit code:

| `error_class` | Meaning | Required action |
| --- | --- | --- |
| `usage` | A required argument is missing, arguments conflict, or request validation failed | Fix the call and start over; never skip it |
| `unsupported` | The command, flag, or platform does not exist in this build | Check the spelling, or run `dtscli version --json` to see what this build supports |
| `config` | The current profile or local credentials are unusable | See [setup](setup.md); never retry automatically |
| `dependency` | The Alibaba Cloud CLI or the DTS plugin is missing or unusable | See [setup](setup.md) |
| `transport` | The network failed and the service provably did not act | A read-only or idempotent call may be retried once |
| `remote` | The service explicitly rejected the business request, or the returned job does not match the request | Report the message and stop without a write |
| `indeterminate` | A write request was sent and its outcome cannot be determined; the read-only `CHECKING` from `job precheck` uses it too, meaning no terminal verdict yet | Never retry a write: verify with a read-only query or the console. `CHECKING` may be queried again for the same job |
| `interrupted` | The user interrupted execution | None |
| `internal` | Unclassified internal error | Report it as a defect; never retry |

This table is the complete shared taxonomy for every command; the lifecycle `indeterminate` case is described in [pre-execution review and confirmation](job-lifecycle.md#pre-execution-review-and-confirmation).

After a name lookup, if `job get` reports a different name from the requested name, treat the name as changed during resolution and stop before a write.

<a id="state-interpretation"></a>
## Status interpretation

<a id="status-namespaces-and-comparison"></a>
### Status namespaces and comparison

Keep the raw API value for display and failure-information queries. For comparison only, normalize ASCII letters to lowercase; do not rewrite the value shown to the user. The same word does not have the same namespace everywhere:

| Field namespace | Documented running values | Notes |
| --- | --- | --- |
| Top-level `Status`, `JobType=SYNC` | `synchronizing` | The running value documented for `DescribeDtsJobDetail`; other list responses may differ in capitalization, so compare ASCII letters case-insensitively |
| `DataSynchronizationStatus.Status` (incremental module) | `NotStarted`, `Migrating`, `Suspending`, `Checking`, `Failed`, `Finished`, `Catched` | Official incremental-module values; `Catched` means caught up. Keep this namespace distinct from top-level `Status`, including names such as `NotStarted`, `Failed`, and `Suspending` that appear in both |
| `StructureInitializationStatus.Status` and `DataInitializationStatus.Status` | `NotStarted`, `Migrating`, `Finished`, `Failed` | These values describe only the structure or full-initialization subtask; they are reported only while initializing or when that stage fails, and are usually absent once incremental starts |
| `JobProgress[].State` | Service values such as `Success`, `Warning`, and `Failed` | Classify an item only within its current subtask; never treat it as top-level job status |

Never infer `JobType` from a different word or from a subtask value. Compare `SYNC` case-insensitively and keep the raw value for display. An empty type is missing. When a value is unknown, report it unchanged and stop before a write; never force it into a known state.

<a id="lifecycle-states"></a>
### Lifecycle states

A job may move from `NotStarted` through `Prechecking`, `PreCheckPass`, and `Initializing` to `synchronizing`, or to `PrecheckFailed`. Not every job visits every state. The table combines synchronization-job top-level states documented for `DescribeDtsJobs` and `DescribeDtsJobDetail`; the official enums do not include `Suspended`. When a value is not listed, report it unchanged and stop before a write.

| `Status` | Meaning | Action |
| --- | --- | --- |
| `NotConfigured` | Created, not configured | Report as not configured; do not perform a lifecycle operation other than configuration |
| `NotStarted` | Configured, not started | Precheck or start only on request |
| `Prechecking` | Precheck in progress | Use the bounded [precheck](#precheck) query; never classify it as failure |
| `PreCheckPass` | Precheck passed, link not yet started | Report the pass; authorize any later operation separately under the active workflow |
| `PrecheckFailed` | Precheck found blocking issues | Report failed items through [precheck](#precheck) and stop further management operations |
| `Initializing` | Enabled Schema/full stages are running, or the job is transitioning to incremental | Report as in progress; never classify it as failure. See [field reliability](#field-reliability-during-initializing) |
| `InitializeFailed` | Synchronization initialization failed | Report through [failure-state handling](#failure-state-query-sequence) and send the user to the console |
| `synchronizing` | Synchronization link running | Report as running; incremental sync is ongoing, never "complete" |
| `Failed` | Synchronization failed | Report through [failure-state handling](#failure-state-query-sequence) and send the user to the console |
| `Suspending` | Suspension completed; DTS retains this top-level value | Preserve the raw value and report the job as suspended; never keep polling for `Suspended` |
| `Retrying` | Retrying | Report as in progress; do not initiate another write |
| `Upgrade` | Upgrading | Report as in progress |
| `Downgrade` | Downgrading | Report as in progress |
| `Locked` | Locked | Stop automatic operations and report the state |
| `Finished` | Finished terminal state | Report as terminal |

Never infer billing from `Status` alone. Apply the [billing requirements](instance-classes-and-pricing.md#billing-and-quote-requirements) to the observed `PayType` and incremental-module state.

<a id="field-reliability-during-initializing"></a>
### Field reliability during `Initializing`

During `Initializing`, `StructureInitializationStatus`, `DataInitializationStatus`, and incremental detail may be null or outdated. Preserve the unknown state; do not query initialization or synchronization modules through `DescribePreCheckStatus`. Top-level `Status` remains a valid but broad transition state. When the service returns `Delay=-1`, `delay_seconds` is `null`; this only means incremental mode has not started, is expected during initialization, and is not a query or synchronization failure. Do not assume a fixed duration or order in which fields are filled. After the job leaves `Initializing` for `synchronizing`, the structure and full sub-statuses usually disappear; that is not a missing field, and the rule above on the three stage statuses applies.

<a id="stage-mapping-table"></a>
### Standard stage mapping

This skill creates only data synchronization jobs (`SYNC`), not migration jobs. Keep precheck request parameters separate from execution-step codes:

| Purpose | API and CLI path | Code and calling boundary |
| --- | --- | --- |
| Precheck | `DescribePreCheckStatus`, through `dtscli job precheck` | `JobCode=01`, retaining the `--struct-type before` compatibility argument; no other stages |
| Incremental runtime state and lag | `DescribeDtsJobDetail`, through `dtscli job get` | Use `incremental_status` and `delay_seconds`; no stage-code argument |

Do not use `DescribePreCheckStatus` as a generic stage query in this workflow: never pass `02`, `03`, `04`, or `07` to it. Migration-stage descriptions in SDKs or general documentation do not justify changing the precheck JobCode.

Interpret precheck results under [precheck](#precheck). Do not apply precheck parameters or completion criteria to structure initialization, full load, or synchronization modules. When detail is missing, report insufficient information rather than infer completion.

<a id="incremental-synchronization-health-signal"></a>
#### Incremental synchronization health signal

For incremental health, use detail `DataSynchronizationStatus.Status`. The official values are `NotStarted`, `Migrating`, `Suspending`, `Checking`, `Failed`, `Finished`, and `Catched`. `Migrating` is running; `Catched` is caught up; `NotStarted` or absence means incremental mode has not started; report `Failed` through [failure-state handling](#failure-state-query-sequence); and report `Suspending`, `Checking`, and `Finished` unchanged. This is the incremental-module namespace, not top-level `Status`; the completed-suspension meaning of top-level `Status=Suspending` does not apply here. Never query this module through `DescribePreCheckStatus` or interpret a missing incremental status as synchronization completion.

<a id="delay-semantics"></a>
## Incremental synchronization delay

`Delay` is meaningful only in incremental mode. Interpret and report it with its field-specific unit:

| Field or value | Unit or meaning |
| --- | --- |
| `DescribeDtsJobDetail.Delay` | Milliseconds |
| `DescribeDtsJobs.Delay` | Seconds |
| `IncLatencySeconds` / `IncLatencyMilliseconds` | Seconds / milliseconds |
| `-1` | Incremental mode has not started; `delay_seconds` is `null`, not an error |
| `0` | Caught up |
| Positive | Current lag; a large or growing value requires investigation but is not a failure state |

Convert latency to seconds before reporting. `<5000` ms in job detail is only a near-zero reference, not a completion threshold. Reaching incremental mode requires only `Delay != -1`.

### Incremental synchronization health check

Confirm incremental health only when top-level status compares as `synchronizing`, incremental detail compares as `migrating` or `catched`, detail `Delay` is present and not `-1`, and no failed or retrying state exists. Preserve raw status values. Do not apply a delay threshold or run failure mode on every routine query.

<a id="precheck"></a>
## Precheck

`start-dts-job` triggers precheck. In the purchase-before-configuration workflow, observation occurs after Start and does not pause DTS; initialization or transfer may begin while status is being observed.

For a one-time query:

```bash
dtscli job precheck --job-id <job-id> --region <region-id>
```

Synchronization jobs supported by this skill have at most 20 precheck items. The default page covers all items, so pagination is unnecessary. The command passes code `01` and `--struct-type before` internally and does not use `--waiter`, `--page-no`, or `--page-size`. A default page size of 20 alone is not evidence of truncation and does not justify requesting another page. Determine the precheck outcome from its state and item results.

After Start, use one time-limited status query:

```bash
dtscli job precheck --job-id <job-id> --region <region-id> --wait-seconds 300
```

`--wait-seconds` defaults to 0 (return the current verdict immediately) and accepts 0 to 300. The command queries immediately and then every `--poll-interval-seconds` (default 5, accepts 1 to 300), bounded by a maximum of 60 precheck requests. It never retries on its own. The output object carries `result`, `state`, `item_count`, the redacted `issues` and `warnings`; `result="CHECKING"` is the non-terminal case. `FAILED` carries `error_class="remote"`; `CHECKING` carries `error_class="indeterminate"`. Both exit non-zero. `CHECKING` means this read-only wait has not completed: query the same job ID again, and do not proceed until precheck passes. It does not indicate an ambiguous write outcome. `can_skip` and `skipped` are fields of entries inside `issues[]` and `warnings[]`; an entry omits them when the API did not return them, and a missing value is never false.

| Result | Required action |
| --- | --- |
| `PASSED` | Report the redacted content of every Warning entry in `warnings`, then continue the confirmed creation workflow |
| `FAILED` | Stop further management operations; report `error_class` and the redacted failed items |
| `CHECKING` | Report the latest state and `state`; the timeout does not pause DTS and does not establish a DTS failure |
| `status=ERROR` | Report the fixed query error; do not classify it as precheck failure or retry Start |

The `warnings` field carries the redacted Warning entries one by one; report the entries, never just the count.

Apply these decision rules:

- Select details only for `JobProgress[].State=Failed` as failed items.
- Place `JobProgress[].State=Warning` items into `warnings` and report each with the same redacted fields as a failed item; a Warning is not a failed item and never stops management operations.
- Treat top-level `State=Failed` as failure even when no failed item is returned.
- Treat top-level `State=Finished` as passed when no failed item exists.
- Do not use `ErrorItem`, nested log severity, or `CanSkip` alone to classify an item as failed.
- Treat `CanSkip=true` as metadata only. The API allowlist excludes `skip-pre-check`.

For each failed or Warning item, retain only the check identity, `error`, `repair_method`, `detail_redacted`, `repair_redacted`, `can_skip`, existing skip flags, and affected objects from logs. State when the API returns no object details. Do not infer a cause or corrective operation from an error-code name. When further investigation is required, report the available redacted information and direct the user to current official DTS documentation or support; never claim that root-cause analysis was completed.

After the reported issues are fixed, query current state and obtain authorization for the required management action. Invoke Start again only when the observed state requires it and the API permits it.

The same API queries structure, full-load, and incremental stages. Use the [stage mapping](#stage-mapping-table). For finite stages, a sub-task `State` is the preferred value when top-level detail fields are null or outdated. Incremental health is the documented exception: use `DataSynchronizationStatus.Status` and `Delay`.

<a id="failure-state-query-sequence"></a>
## Failure-state handling

1. Run `dtscli job get --job-id <job-id> --region <region-id>` and confirm the current state.
2. If precheck failed, run `dtscli job precheck --job-id <job-id> --region <region-id>` and report the redacted items.
3. For other failures, report the stage fields already on `job get` and ask the user to check the original step error in the DTS console. Do not infer an unsupported root cause or automatically perform a management operation.
