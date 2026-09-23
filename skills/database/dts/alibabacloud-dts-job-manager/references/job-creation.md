# DTS Synchronization Job Creation

## Contents

- [Creation inputs and user choices](#creation-inputs-and-user-choices)
- [Source, destination, and link prerequisites](#link-prerequisites)
- [Purchase, configuration, and start workflow](#purchase-configure-start-workflow)
- [Pre-execution review](#customer-facing-creation-output-requirements)
- [Result reporting](#result-reporting)

<a id="creation-inputs-and-user-choices"></a>
## Creation inputs and user choices

Apply the [database instance access boundary](database-instance-configuration.md#database-instance-access-boundary) before collecting credentials or link information. Resolve the source and destination database instances or clusters from the [source and destination database configuration](database-instance-configuration.md), and apply the [source, destination, and job region rules](database-instance-configuration.md#destination-region-requirements); require the synchronization direction to match one [supported synchronization link](supported-links.md#directed-link-groups).

<a id="creation-choice-elicitation"></a>
### Confirm required choices

Treat a documented value or plain statement as supplied when it clearly maps to one valid value for the selected link. Validate and keep every supplied value; do not ask the user to select it again. Ask only for an applicable value that is missing, invalid, or ambiguous, and present the supported choices for that field. Do not substitute a Planner example or recommendation for a required user decision. A request to use defaults applies only to values explicitly documented as defaults; it does not resolve a required decision that has no default.

While a required decision remains unresolved, show only each missing, invalid, or ambiguous field, its valid choices, and any important difference in the synchronized data among those choices. Do not list successful CLI or profile checks, internal scenario names or engine enums, raw `DbList` or `Reserve`, script status codes, or a full repetition of values already resolved.

Resolve every required decision that does not depend on the current price before inspecting profile metadata, requesting a quotation, compiling a plan, initializing credentials, testing whether the source and destination databases can be reached, or calling a service. Instance class is the only decision that depends on the current price: keep and quote a supplied class, or quote all reviewed classes and then require a selection. The later combined confirmation displays the resolved values and authorizes the sequence of management operations; it does not ask the user to select them again.

Collect:

- the job name, IDs and regions of the source and destination database instances or clusters; when the user gave only an instance name, first resolve it to an ID under [resolve an instance ID from a name](database-instance-configuration.md#list-cloud-database-instances), and when they already gave a complete instance ID, use it; when there are zero or several exact name matches, require a choice and never pick one yourself;
- a selectable class and validated quotation from [instance classes and pricing](instance-classes-and-pricing.md);
- object databases required by the PostgreSQL source and destination, and authentication databases required by the MongoDB source and destination;
- synchronization objects and destination names established under the [object selection boundary](db-list.md#object-selection-boundary);
- applicable source and destination settings from [Reserve](reserve.md), including the existing-destination policy;
- structure and full initialization choices; incremental synchronization is mandatory.

Support these phase combinations:

| Structure | Full data | Incremental | Requirement |
| --- | --- | --- | --- |
| Enabled | Enabled | Enabled | Standard initialization |
| Disabled | Enabled | Enabled | Compatible destination structure exists |
| Enabled | Disabled | Enabled | Existing rows are not copied |
| Disabled | Disabled | Enabled | A compatible baseline is verified |

Retain a valid phase combination supplied by the user. Otherwise, present the four combinations above and require one selection before compilation.

When structure initialization is disabled, require the user to confirm that compatible destination objects already exist. When full initialization is disabled, require confirmation that the required initial-data baseline already exists. This Skill does not inspect or verify either condition; the user confirmation and subsequent DTS precheck remain official.

Display object mappings according to the [object pre-execution review](db-list.md#object-selection-review).

For a PolarDB MySQL destination, retain a supplied InnoDB or X-Engine value. If it is missing, invalid, or ambiguous, require the user to select one before compilation. Follow [Reserve destination-database parameters](reserve.md#destination-database-parameters) for trigger-handling applicability, defaults, and compilation rules.

<a id="link-prerequisites"></a>
## Source, destination, and link prerequisites

Apply the common requirements once, the source row for the selected source product, and the destination row for the selected destination product. Do not restate the same database requirement for every compatible link. Treat every prerequisite as information that the user must review. Do not inspect or change database parameters, permissions, constraints, topology, storage, or database load. A failed server precheck is decisive and stops further management operations.

Common requirements:

- Require selected tables to have a primary key or unique constraint whose fields are unique.
- Require destination capacity to exceed occupied source storage.
- Warn that initialization increases database load and may increase destination storage use.
- Warn that writes outside DTS to synchronized destination objects can cause inconsistency.

| Database role and product | Additional requirements |
| --- | --- |
| Source: PolarDB MySQL | Require `loose_polar_log_bin=ON`, prefer seven days of Binlog retention, and require at least three days. Apply no PolarDB parameter name to RDS MySQL. |
| Source: PolarDB-X 2.0 | Support Standard Edition and Enterprise Edition without asking the user for an edition. Require a writable source, binary logging, and `binlog_row_image=full`; require more than 24 hours of source logs for incremental-only or at least seven days for full plus incremental. Warn that table-group and locality metadata is not synchronized. |
| Source: RDS PostgreSQL | Require the selected source database and every selected Schema, Logical Replication Slot Failover, and documented WAL retention. Support only a non-encrypted database connection. |
| Destination: RDS PostgreSQL | Require the destination database that holds the synchronized objects as `database`. Resolve that instance with `--type RDS --engine POSTGRESQL --page-size 20` and `--usage-type dest`. When the source is also RDS PostgreSQL, the scenario is `rds-postgresql-to-rds-postgresql`. Do not treat this destination as a PolarDB PostgreSQL cluster. |
| Source: PolarDB PostgreSQL | Require the selected source database and every selected Schema, Logical Replication Slot Failover, and every parent and child partition when selecting a partitioned table. Exclude Oracle-compatible and distributed PolarDB PostgreSQL. Support only a non-encrypted database connection. |
| Source: MongoDB replica set | Require replica-set architecture, the authentication database, `read` on the synchronized database plus `config`, `admin`, and `local`, a non-encrypted connection, and acknowledgment of the documented incremental-operation limits. |
| Destination: MongoDB replica set | Require replica-set architecture, the authentication database, `dbAdminAnyDatabase`, `readWrite` on the destination database, `read` on `local`, and a non-encrypted connection. |

If either MongoDB database instance is a sharded cluster, stop before compiling the plan. Collect the source and destination authentication databases independently.

For every PostgreSQL link, include one source-side confirmation in the combined confirmation:

- the source account is the owner of the selected source database;
- source WAL uses `wal_level=logical`;
- DTS creates a `dts_sync_` replication slot and auxiliary/heartbeat tables and may execute `ALTER TABLE ... REPLICA IDENTITY FULL` when the related precheck is skipped;
- long transactions or an uncleared replication slot can retain WAL and consume source storage.

Do not copy the source database-owner or source `wal_level` confirmation to the destination, and do not turn either statement into a Planner field. Keep documented destination permissions or parameters separate. For an RDS PostgreSQL source, require each selected table to have a primary key or unique constraint; when structure initialization is disabled, require the same primary key or non-null unique constraint at the destination. For a PolarDB PostgreSQL source, require a primary key or non-null unique index.

For a PolarDB-X 2.0 destination, state that PolarDB-X 2.0 does not support database triggers. DTS cannot copy a source trigger to that destination, and there is no supported destination trigger for DTS writes to fire. Explain that trigger-dependent effects are not preserved. Apply the exact compilation rule from [Reserve destination database parameters](reserve.md#destination-database-parameters). Reject a requirement to create, copy, or fire a trigger unless the user removes it and accepts the limitation.

Use the official [existing-destination object policy](reserve.md#existing-destination-object-policy). For MongoDB, state that mode `2` does not overwrite or clear an existing collection.

<a id="purchase-configure-start-workflow"></a>
## Creation workflow: purchase, configure, and start

### 1. Collect and validate inputs

Apply [creation inputs and user choices](#creation-inputs-and-user-choices), [link prerequisites](#link-prerequisites), and [instance classes and pricing](instance-classes-and-pricing.md). Require the actual regions of the source and destination database instances and a complete current quote for the selected class. Instance price does not depend on the link or region. Derive the DTS instance/business-request region from the destination region; do not ask the user to choose it separately.

Run the read-only preparation steps in this fixed order: load the registered scenario with `job create scenarios --name <scenario>`, resolve the source instance, resolve the destination only after one exact source match, query the user-selected class with `job price --instance-class <instance-class>` only after both endpoints are unique and usable, and only then run `job create init`. Stop immediately if either instance query returns zero matches, several matches, an unusable instance, or an error; do not continue to the other endpoint, quotation, or plan compilation.

Derive the calling application identifier from trusted information provided by the host application. Creation does not query existing DTS jobs for duplicate names or overlapping scopes.

<a id="review-and-safe-resume"></a>
### 2. Review the plan and complete read-only checks

Apply the [database instance configuration completeness check](database-instance-configuration.md#required-field-completeness-check), [DbList rules](db-list.md), and [Reserve rules](reserve.md). The quotation has already been obtained separately in step 1 under [instance classes and pricing](instance-classes-and-pricing.md). Then compile the plan and create a local attempt:

```bash
dtscli job create init --input <input-json>
```

Each step's JSON reports a copy-pasteable `next_step` when the caller can continue; branches that need a human to judge the cause first (a connection failure, for example) report none. Follow it for `review`, then `test`:

```bash
dtscli job create review --attempt-id <attempt-id>
dtscli job create test --attempt-id <attempt-id>
```

`test` accepts only an attempt that has been reviewed. The summary is produced by `review` alone, so skipping it leaves nothing to show the user and the command fails with a usage error.

The commands use the Alibaba Cloud CLI's current profile. Quotations come from the cache; run `dtscli job price --refresh-cache` separately only for a live-verification case allowed under [query current prices](instance-classes-and-pricing.md#service-access-evidence).

`init` saves the plan and attempt state. `review` only checks locally stored credentials and writes the plan summary; `test` runs the connection test. A storage failure stops the flow without an executable confirmation. Storage errors use `error_class="config"`; do not depend on the legacy `storage_failure_category` or classify local storage errors as cloud-service failures.

`init` generates an `attempt_id` shaped as `a<timestamp>-<16 hex digits>` and creates `.aliyun-dts/job-manager/creation-plans/<attempt-id>/` under the current user's home directory. Each attempt directory uses only the fixed names `plan.json`, `state.json`, and `execute.lock`; uniqueness comes from the parent `attempt_id`. Never put a job name, instance ID, or database name in the path. Never use a system temporary directory, a directory automatically removed when a child agent or task ends, or a repository path.

After missing credentials are corrected, rerun `review` using only the internal `attempt_id` returned by `init`, then run `test`; on `outcome=stored`, `job credentials collect` reports that `review` command as its `next_step`. After a recoverable pre-purchase connection failure is corrected, rerun only `test` with the same `attempt_id`. Both commands load and fully validate the retained `plan.json` and `state.json` from the fixed attempt directory. They never purchase, configure, or start a resource. Never resupply, reconstruct, copy, or edit the original public input. Stop on a plan-hash or state mismatch.

For parallel creation of multiple jobs, run `init` once per job so each call creates an independent directory. The `attempt_id`, directory path, and filenames are internal orchestration data and must not appear in the user-facing review.

The input JSON must contain `scenario`, but `source` and `destination` must not repeat the `engine` or `instance_type` derived from that scenario. Profile and host-application identity are compiler context and must not appear in public input. Tables and collections share `existing_destination_policy`; its valid values are defined by the [existing-destination object policy](reserve.md#existing-destination-object-policy).

The profile in the compiler context comes from the CLI's current profile. Never ask the user to put it in the input JSON or show it in the user-facing review. Plan compilation is handled by `dtscli job create init`: submit the public input, keep the `attempt_id`, use `review` for credential requirements or the plan summary, and use `test` for connectivity and the confirmation hash.

Creation commands have no `--timeout` flag. `ConfigureDtsJob` times out after 60 seconds; every other OpenAPI call times out after 10 seconds. These limits apply to a single call, not the entire creation workflow.

The profile comes from the compilation context. The compiled plan and attempt state use `schema_version=1`. Later calls load the saved plan by `attempt_id`; never rewrite its JSON or add credentials. Pre-purchase resume applies only to attempts with no cloud write. After `execute`, follow the resource-effect matrix in [resuming after a failure](#resuming-after-failure); never reset a finished or uncertain attempt through `review`.

#### Pending-plan lifecycle

The `outcome` values from `review` and `test` return `attempt_id`, and the plan is retained until the attempt is resolved. The caller must retain the `attempt_id`. The `confirmation_sha256` issued by `test` is stored on the local attempt; `execute --yes` uses it by default, so the hash does not need to be copied onto the command line. Keep the attempt until one of these terminal conditions occurs:

`credentials_required` authorizes only completing the local credential page and resuming pre-purchase checks; it never authorizes a management operation.

- `execute` produces a final result that has been recorded;
- the user cancels this creation attempt;
- the user changes the plan or an applicable prerequisite, which ends the old attempt and requires a new preparation.

Never remove a pending plan while waiting for user confirmation, handing off the task, or ending a child agent. If the plan file, attempt state, or binding is lost, stop before any write operation. Only a new `init` attempt, a new review, and a new explicit confirmation can continue.

`state.json` atomically records `PREPARED`, `AWAITING_CREDENTIALS`, `READY_FOR_CONFIRMATION`, `EXECUTING`, `PURCHASED`, `CONFIGURED`, `STARTED`, `INDETERMINATE`, `FINISHED`, `CANCELLED`, or `FAILED`. Before any cloud write API, `execute` must obtain exclusive ownership of the attempt by atomically creating `execute.lock` and transition from `READY_FOR_CONFIRMATION` to `EXECUTING`. An existing lock, a finished or cancelled attempt, or an attempt whose result is unclear must never purchase again. A definitely failed attempt may run once more only when the [resource-effect matrix](#resuming-after-failure) allows it and the user has confirmed again, and it never purchases a second instance. A lock left after a crash, or an `EXECUTING`, `CONFIGURED`, `STARTED`, or `INDETERMINATE` state, must stop further writes; never delete the lock or retry automatically.

When the user cancels or changes a pending plan, stop this attempt and start a new `init`; do not rerun `execute` on the old attempt. An instance that was already purchased keeps billing; ask the user to handle it in the console.

Normal and handled-error paths remove only the `execute.lock` obtained by the current process. Same-directory random `.tmp` staging files used for atomic writes are cleaned after a successful replacement or write failure. Never scan or delete other attempt directories, locks, or staging files with a glob. Preserve the plan, state, and known IDs when the result is ambiguous. Preserve a crash-left lock as evidence that the result is unclear instead of deleting it by age. Cleanup must never delete or inspect credential storage.

`dtscli` validates the compiled job name, stage booleans, serialized `DbList` and `Reserve`, and IDs returned after purchase. It then injects only the two username/password pairs referenced by the plan. Do not construct the `ConfigureDtsJob` command containing database credentials directly.

### 3. Handle missing credentials

When `review` returns `outcome="credentials_required"`, first explain that credentials are stored as Base64 text in local files under the current user's home directory, then run `dtscli job credentials collect --attempt-id <attempt-id>` once under [credentials and security](credentials-and-security.md). The attempt directory is derived internally from `attempt_id`; never accept an arbitrary user-provided path or expose it in the user-facing review. After the user completes the local page, follow [plan review and safe resume](#review-and-safe-resume) and rerun `review` using only the same `attempt_id`, then run `test` after `ready_for_test`; on `outcome=stored`, the collect command reports that `review` command as its `next_step`. Never request credentials, screenshots, browser URLs, terminal transcripts, or credential files in the conversation.

### 4. Review and authorize

`test` runs the connection test under the [database connection test requirements](credentials-and-security.md#database-connection-test-request-and-response-requirements). Present the combined create-flow review only when `test` returns `outcome` `ready_for_confirmation`; also inspect `connection_test`: only `passed` confirms connectivity. For `skipped_by_request`, follow [database connection tests](credentials-and-security.md#database-connection-tests). Show the plan from `review`'s `summary`, the connectivity result from `test`, and the class quotation obtained separately from `job price`. The tables below select what to tell the user, by scenario and chosen policy. The command does not return these codes: decide which entries apply from the tables and render them as natural language, never as raw codes. Stop before purchase on test failure; an unverified result is allowed only under that explicitly authorized exception. Allow credential re-entry only for the source or destination explicitly identified by the redacted result, then safely resume `review` and `test` under this section.

<a id="customer-facing-creation-output-requirements"></a>
#### Pre-execution combined confirmation

Use two short groups so facts, user assertions, and impacts are not repeated in one list.

**Job configuration**:

- Job name and DTS region.
- Source and destination product names, database instance or cluster IDs, regions, and applicable PostgreSQL object databases or MongoDB authentication databases.
- Every fully qualified source → destination object mapping.
- Enabled structure initialization, full initialization, and ongoing incremental synchronization phases.
- Selected behavior and limitation from the [existing-destination object policy](reserve.md#existing-destination-object-policy).
- Selected class, RPS reference, current quote, billing start condition, and applicable warnings required by the [billing and quotation requirements](instance-classes-and-pricing.md#billing-and-quote-requirements).
- The source and destination databases can both be reached.

**Required confirmations and impacts**:

- Applicable conditions from [link prerequisites](#link-prerequisites) that the user must assert and this Skill does not inspect.
- Applicable initialization load, writes outside DTS, WAL, or trigger impacts.
- Confirmation will purchase a DTS instance, configure the job as reviewed, and start it; purchase creates a resource that may become billable.

Only when applicable, include the destination storage engine, PostgreSQL source requirements and WAL impact, the PolarDB-X 2.0 trigger limitation, MongoDB replica-set and collection-conflict behavior, and managed MySQL destination trigger behavior.

Do not include plan paths or hashes, profile names, `RequestId`, CLI arguments, internal scenario or engine enums, raw `DbList` or `Reserve`, credential-set IDs, script status codes, or the calling application identifier. For a cached or mixed quotation, show only the source and oldest cache-write time needed to judge freshness; omit other internal cache fields. Do not repeat successful setup checks.

Require one explicit outcome: confirm creation and start for the unchanged plan, modify without writing, or cancel. Modification or cancellation ends this attempt. One explicit confirmation authorizes only the unchanged purchase → configure → start sequence.

### 5. Execute the confirmed plan

After explicit confirmation, purchase once. Never show `confirmation_sha256` to the user or require the user to copy it. When `--confirmation` is omitted, the command uses the hash stored on the local attempt by `test`. That hash binds the plan, job name, region, profile, billing impact, and connectivity evidence. An explicit `--confirmation` that does not match the local hash is rejected:

```bash
dtscli job create execute --attempt-id <attempt-id> --yes
```

`execute` does not test connections. It runs no precheck observation; query the precheck from the returned `next_step` or under [job status · precheck](job-status.md#precheck).

<a id="resuming-after-failure"></a>
#### Resuming after a failure

When `outcome="failed"`, `resource_effect` decides whether the same `attempt_id` may run once more. The three values do not overlap, and a second instance is never purchased:

| `resource_effect` | What remains in the cloud | Handling |
| --- | --- | --- |
| `NONE` | The purchase definitely failed; no instance exists | After finding the cause and obtaining the user's confirmation again, run once more; nothing is reused |
| `INSTANCE_PURCHASED` | The instance exists and is billing | After finding the cause and obtaining the user's confirmation again, run once more to reuse that instance for configuration and start; report its `instance_id` to the user |
| `UNKNOWN` | The purchase request went out and the result is unknown | Stop and never retry; verify with the [readback order for an unclear purchase](#purchase-readback-order) |

An `outcome="indeterminate"` (including an uncertain start) always stops the flow: never retry and never purchase again. A resume still requires one explicit user confirmation per execution and is never automatic.

<a id="purchase-readback-order"></a>
#### Readback order when a purchase or start is unclear

When any creation step ends unclear, verify in this order: never purchase again and never re-run `execute`.

1. The output carries a `job_id`: read that job with `dtscli job get --job-id <job-id> --region <region-id>`.
2. Only an `instance_id` is known: resolve the single job in that region as described in [locate a job by DTS instance ID](job-status.md#query-one-job-by-dts-instance-id-for-purchase-verification), then run `job get`.
3. Neither is available, or no single resource can be identified: keep the outcome ambiguous and ask the user to check the DTS console for a billed instance.

This section defines that readback order once; other sections summarise it and link here. `INSTANCE_PURCHASED` and `UNKNOWN` may both already be billing. Report only confirmed identifiers and never infer an ID from `RequestId`.

#### The `outcome` of review

| `outcome` | Handling |
| --- | --- |
| `credentials_required` | Explain local Base64 storage, run the credential page once, then resume `review` using only the same `attempt_id` |
| `ready_for_test` | Keep `summary`, then immediately follow `next_step` and run `dtscli job create test --attempt-id <attempt-id>` |

#### The `outcome` of test

| `outcome` | Handling |
| --- | --- |
| `credentials_required` | Collect credentials (follow `next_step`), then run `review` and `test` again |
| `connection_failed` | Act on `connection_error`; once corrected, resume `test` using only the same `attempt_id`. No confirmation hash is returned, so the flow cannot reach a purchase |
| `ready_for_confirmation` | Render the pre-execution review from `review`'s `summary` and this `connection_test`; when the user has approved the unchanged plan, follow `next_step` and run `execute --yes`. `confirmation_sha256` is an internal binding value and must never be displayed |

#### The `outcome` of execute

| `outcome` | Handling |
| --- | --- |
| `created` | Report successful creation and start, then query the precheck verdict under [job status · precheck](job-status.md#precheck) |
| `indeterminate` | A management operation may have taken effect; stop and never run `review`, `execute`, or another purchase. Verify with the [readback order for an unclear purchase](#purchase-readback-order) |
| `failed` | Handle from `error_class` and `resource_effect`; only the two `resource_effect` values allowed by [resuming after a failure](#resuming-after-failure) may run once more after a new user confirmation, and never automatically |

A failed `execute` may still return the complete execution summary with a non-zero exit code. Inspect `outcome`, `resource_effect`, and `steps` before using `error_class`; absence of a generic error object is not success.

- `outcome="created"` means purchase, configuration, and startup completed; query precheck separately.
- `steps` lists purchase, configuration, and startup in order. `succeeded`, `failed`, `indeterminate`, and `not_reached` mean success, definite failure, unknown result, and not executed. Read how far configuration and start progressed from here.
- `resource_effect` of `INSTANCE_PURCHASED` or `UNKNOWN` means billing has or may have started. Tell the user even when the overall operation failed.
- With `outcome="indeterminate"`, stop writes and never retry. Missing summary fields do not prove that no resource exists.

#### Stop when the result is unclear

When `execute` returns `outcome="indeterminate"`, stop further writes. Never retry `execute`, `review`, or another purchase; verify with the [readback order for an unclear purchase](#purchase-readback-order). The lock is never broken automatically: taking it over risks purchasing a second billed instance.

`summary` carries the fields below. Build the pre-execution review only from them, and never add internal plan fields outside `summary` to the user confirmation:

| Field | Meaning |
| --- | --- |
| `job_name`, `scenario` | Job name and link scenario |
| `source_region`, `source_instance`, `destination_region`, `destination_instance` | Both endpoints' regions and instances or clusters |
| `source_database`, `destination_database` | Present only for PostgreSQL and MongoDB. For PostgreSQL it is the database holding the synchronized objects; for MongoDB it is the **authentication** database and must never be described as the database being synchronized |
| `mappings` | One `source.object -> destination.object` entry per selection, or `source.* -> destination.*` for a whole namespace. **The review must show these**; never report counts alone |
| `namespace_count`, `object_count`, `whole_namespace_count` | Counts, useful only to cross-check `mappings` |
| `structure_stage`, `full_stage`, `incremental_stage` | Which phases are enabled |
| `existing_destination_policy` | Existing-destination policy; see [Reserve](reserve.md#existing-destination-object-policy) for its semantics |
| `instance_class`, `pay_type`, `billing_impact` | Class, payment type, and billing impact |

The price is not in `summary`. Obtain it with `dtscli job price` and present it alongside. Prerequisites, impact warnings, and similar guidance come from the rules in this document and in [Reserve](reserve.md), selected by scenario and chosen policy and rendered as natural language.

The table below lists the prerequisites to state. The complete requirements remain authoritative under [source, destination, and link prerequisites](#link-prerequisites):

| Code | Selected rule |
| --- | --- |
| `SELECTED_TABLES_HAVE_UNIQUE_KEY` | Primary-key or unique-constraint requirement for selected MySQL-compatible tables |
| `DESTINATION_CAPACITY_EXCEEDS_SOURCE_USED_STORAGE` | Destination-capacity requirement |
| `SOURCE_POLARDB_MYSQL_LOOSE_POLAR_LOG_BIN_ON` | Source PolarDB MySQL `loose_polar_log_bin` requirement |
| `SOURCE_POLARDB_MYSQL_BINLOG_RETENTION_AT_LEAST_3_DAYS` | Minimum source PolarDB MySQL Binlog retention |
| `SOURCE_POLARDBX_WRITABLE` | Writable PolarDB-X 2.0 source |
| `SOURCE_POLARDBX_BINARY_LOGGING_ENABLED` | Binary logging enabled at the PolarDB-X 2.0 source |
| `SOURCE_POLARDBX_BINLOG_ROW_IMAGE_FULL` | Source PolarDB-X 2.0 `binlog_row_image=full` |
| `SOURCE_POLARDBX_LOG_RETENTION_OVER_24_HOURS` | PolarDB-X 2.0 log retention for incremental-only synchronization |
| `SOURCE_POLARDBX_LOG_RETENTION_AT_LEAST_7_DAYS` | PolarDB-X 2.0 log retention for full plus incremental synchronization |
| `SOURCE_POSTGRESQL_DATABASE_OWNER` | PostgreSQL source account owns the source database |
| `SOURCE_POSTGRESQL_WAL_LEVEL_LOGICAL` | Source PostgreSQL `wal_level=logical` |
| `SOURCE_POSTGRESQL_LOGICAL_REPLICATION_SLOT_FAILOVER` | Source PostgreSQL replication-slot failover |
| `SOURCE_POSTGRESQL_WAL_RETENTION_CONFIGURED` | Source PostgreSQL WAL retention |
| `SOURCE_POSTGRESQL_CONNECTION_UNENCRYPTED` | PostgreSQL source non-encrypted connection restriction |
| `SOURCE_RDS_POSTGRESQL_SELECTED_TABLES_HAVE_PRIMARY_OR_UNIQUE_KEY` | RDS PostgreSQL source-table key requirement |
| `SOURCE_POLARDB_POSTGRESQL_SELECTED_TABLES_HAVE_PRIMARY_OR_NON_NULL_UNIQUE_INDEX` | PolarDB PostgreSQL source-table key requirement |
| `SOURCE_POLARDB_POSTGRESQL_PARTITION_SELECTION_COMPLETE` | Complete parent/child partition selection for PolarDB PostgreSQL |
| `SOURCE_POLARDB_POSTGRESQL_STANDARD_NON_DISTRIBUTED` | PolarDB PostgreSQL product-compatibility boundary |
| `SOURCE_MONGODB_REPLICA_SET`, `DESTINATION_MONGODB_REPLICA_SET` | MongoDB replica-set topology for the source and destination database instances |
| `SOURCE_MONGODB_PERMISSIONS_AND_INCREMENTAL_LIMITS` | MongoDB source permissions and incremental-operation limits |
| `DESTINATION_MONGODB_PERMISSIONS` | MongoDB destination permissions |
| `SOURCE_MONGODB_CONNECTION_UNENCRYPTED`, `DESTINATION_MONGODB_CONNECTION_UNENCRYPTED` | MongoDB non-encrypted connection restriction for the source and destination databases |

The table below lists the impact warnings to state:

| Code | Selected impact |
| --- | --- |
| `INITIALIZATION_INCREASES_DATABASE_LOAD` | Initialization load |
| `INITIALIZATION_MAY_INCREASE_DESTINATION_STORAGE` | Destination storage growth |
| `EXTERNAL_DESTINATION_WRITES_MAY_CAUSE_INCONSISTENCY` | Inconsistency risk from destination writes outside DTS |
| `SOURCE_POLARDB_MYSQL_BINLOG_RETENTION_7_DAYS_RECOMMENDED` | Seven-day source PolarDB MySQL Binlog retention recommendation |
| `POLARDBX_TABLE_GROUP_AND_LOCALITY_NOT_SYNCHRONIZED` | PolarDB-X 2.0 table-group and locality metadata are not synchronized |
| `DESTINATION_POLARDBX_TRIGGERS_UNSUPPORTED` | PolarDB-X 2.0 destination trigger limitation |
| `POSTGRESQL_DTS_CREATES_REPLICATION_SLOT_AND_AUXILIARY_TABLES` | PostgreSQL replication-slot and auxiliary-table impact |
| `POSTGRESQL_REPLICA_IDENTITY_FULL_MAY_BE_APPLIED` | PostgreSQL `REPLICA IDENTITY` may be changed |
| `POSTGRESQL_LONG_TRANSACTIONS_OR_STALE_SLOTS_RETAIN_WAL` | PostgreSQL WAL-storage impact |

Existing-destination behavior is stated from the [existing-destination object policy](reserve.md#existing-destination-object-policy), covering: `EXISTING_DESTINATION_OBJECT_CAUSES_PRECHECK_FAILURE`, `EXISTING_DESTINATION_OBJECT_PRECHECK_IGNORED`, `EXISTING_DESTINATION_OBJECTS_NOT_CLEARED_OR_REBUILT`, `FULL_CONFLICT_KEEPS_DESTINATION_ROW`, `INCREMENTAL_CONFLICT_APPLIES_SOURCE_CHANGE`, `POSTGRESQL_STRUCTURE_DIFFERENCE_MAY_FAIL_OR_PARTIALLY_SYNC`, `FULL_CONFLICT_KEEPS_DESTINATION_DOCUMENT`, `MONGODB_INCREMENTAL_CONFLICT_BEHAVIOR_NOT_INFERRED`, and `MONGODB_EXISTING_COLLECTION_NOT_CLEARED`.

On failure, decide what to do from the `error_class` on standard output:

| `error_class` | Meaning and handling |
| --- | --- |
| `usage` | The input, attempt ID, plan hash, or confirmation hash is invalid; correct it and start over, never skip it |
| `config` | The profile or the credentials are unusable; see [setup](setup.md) and [database credentials](credentials-and-security.md) |
| `dependency` | The Alibaba Cloud CLI or the DTS plugin is missing. Run `dtscli job deps install --yes` once without asking, then retry the same command once. Do not add `--update`. Stop only when the command's JSON output carries an `error_class` whose `message` contains `ERROR: unchecked version`; a successful `dtscli doctor` check that mentions those words is not that error. Do not replace `aliyun`, do not run `aliyun version`, and do not fetch the same data through another interface |
| `transport` | The network failed and the service provably did not act; retry once |
| `remote` | The service rejected the call; report the message and stop. A missing local plugin is not this case: when the message says the DTS plugin or Alibaba Cloud CLI is not installed, handle it as `dependency` |
| `indeterminate` | The write was sent but whether the service acted cannot be determined; never retry, check the console |

After `indeterminate`, stop; never delete the lock or retry. An attempt that definitely failed after a cloud write follows [resuming after a failure](#resuming-after-failure): only recorded resources may be reused and a purchase is never repeated. A finished or cancelled attempt is never executed again: that is an idempotent terminal state, not permission to execute again.

`STARTED` states that purchase, configuration, and Start were verified, but it does not mean that precheck passed. When a purchase effect exists, retain the returned IDs and `resource_effect`. Never forward raw child stdout or stderr.

If `job create test` fails, stop and do not run `execute`. If `execute` has no recorded connection evidence, stop and report that nothing was purchased. After configuration is accepted, proceed directly to Start without a routine detail query.

Each step of `execute` carries its own limit: 60 seconds for `ConfigureDtsJob`, and 10 seconds for every other OpenAPI call, including purchase and read-only verification. The connection test is a separate `job create test` call with the same 10-second limit. There is no countdown spanning the steps; the operation stops as soon as one of them is exceeded. These limits are safety bounds, not estimates of service duration.

After each step, `execute` atomically writes the result into the attempt's `state.json` before starting the next one: the instance ID lands as soon as the purchase succeeds, the job ID as soon as configuration succeeds. **Interrupted recovery reads that state file, not standard error** — stderr carries human-readable progress and must not be parsed.

However `execute` is interrupted, never re-run `execute`; verify with the [readback order for an unclear purchase](#purchase-readback-order). Never infer success from the progress text.

On success, read the outcome from the stdout JSON: `outcome` (`created`), `instance_id`, and `job_id`.

#### Resource effects

Use `resource_effect` to decide whether a resource may remain and whether its current state must be verified:

`resource_effect` answers one question: **is anything billing**. It deliberately has only three values; how far configuration and start progressed is expressed by `steps`, and the two should not be read together.

| `resource_effect` | Meaning |
| --- | --- |
| `NONE` | No evidence that an instance was purchased |
| `INSTANCE_PURCHASED` | An instance was purchased and is billing |
| `UNKNOWN` | The purchase request was sent and its outcome cannot be determined. Never retry the purchase; ask the user to check the console |

`UNKNOWN` is the one to watch: an instance may be billing without the local record knowing it. Never retry creation; ask the user to confirm in the console before releasing anything.

When the purchase outcome is ambiguous, `execute` fails with `error_class` `indeterminate` and exit code 7. The purchase request went out, but nothing local can establish what the service created. Three situations produce it:

| Situation | How the message reads |
| --- | --- |
| The purchase call timed out or the connection broke | the request was sent and the outcome is unknown |
| The purchase response could not be read | returned output that could not be read |
| The purchase reported success without an instance ID | returned no instance id |

All three mean the same thing to the caller and need no separate handling. On any `indeterminate` result:

1. Stop before configuration and Start. Treat the DTS instance as possibly created and billable.
2. Never retry `execute` automatically, and never reissue the purchase directly.
3. Verify with the [readback order for an unclear purchase](#purchase-readback-order); do not infer an ID from `RequestId`.
4. If one resource can be uniquely identified and verified, report its IDs, state, and possible billing impact. Attempting another purchase requires a separate review and explicit confirmation.
5. If no resource can be uniquely identified and verified, keep the outcome ambiguous, report the possible billing impact, and direct the user to the DTS console or support. Absence from one query is not proof that no resource was created.

<a id="6-start-evaluate-precheck-and-finish"></a>
### 6. Start, evaluate precheck, and finish

Once configuration succeeds, `dtscli job create execute` calls `StartDtsJob` once with the verified job ID, instance ID, and the DTS region from the unchanged plan, in the `Forward` direction. This happens inside the command; never issue the call by hand.

When Start fails or its result is ambiguous, the command retains the verified IDs and records `INDETERMINATE`. Stop further management operations, report that the purchased, configured instance remains, inspect it with `job get` if a job ID is known, and never retry `execute`.

Then observe precheck according to [job status](job-status.md#precheck). Start acceptance may allow DTS to advance while observation continues.

- On passed precheck, report the redacted content of every Warning entry in `warnings`, observe the current job state once, and follow the successful-creation reporting requirements.
- On failed precheck, stop further management operations and use the failure requirements.
- Report each Warning entry with the same redacted fields as a failed item; a Warning is not a failed item and never stops further management operations.

Any later suspend or rename action requires its own review and confirmation.

<a id="result-reporting"></a>
## Result reporting

### Successful creation

Report:

- that the job was created and started;
- the DTS region, DTS job ID, and DTS instance ID;
- that precheck passed; report the redacted content of each non-blocking Warning entry;
- the current observed state in plain terms;
- the official [DTS console](https://dtsnew.console.aliyun.com/) entry.

Do not repeat the full review or the internal fields excluded from it. The console URL is only a generic entry, not evidence of job state; do not invent region, job, or instance query parameters. Keep the region and both IDs next to the link so the user can locate the job in the console.

After precheck passes, the job is typically `Initializing`. This is the normal transition state immediately after start; **creation is complete at this point** — do not block waiting for the next phase to begin, and do not repeatedly recheck. Ongoing incremental synchronization has no finite completion milestone. Describe current health from [job status](job-status.md#delay-semantics).

### Failed or ambiguous creation

Report the failed operation or stage, allocated job and instance IDs, redacted error or failed precheck items, whether an instance remains retained and potentially billable, the current state, and one concrete next action.

Do not repeat the full review. `RequestId` is not a success indicator; omit it from routine output and include it only when the user requests support metadata or when it is needed to verify an ambiguous result. Follow [credentials and security](credentials-and-security.md) for redaction. Do not retry an operation with an ambiguous outcome.
