---
name: alibabacloud-dts-job-manager
description: Create, query, and manage database synchronization jobs in Alibaba Cloud Data Transmission Service (DTS), covering synchronization link creation, job status and progress visibility, job renaming, starting, suspending, or resuming jobs, and instance class and hourly price lookup. Use when the user mentions DTS, a DTS job/instance/link, data synchronization, or database synchronization; asks what synchronization jobs exist, how far a job has progressed, or what its incremental latency is; asks how much a synchronization costs, what the small instance class costs, or what unit it is billed by; needs full or incremental synchronization for a data migration or cross-region disaster recovery; or says “sync data from one database to another.” Supports database synchronization among RDS MySQL, PolarDB MySQL, and PolarDB-X 2.0; between RDS PostgreSQL and PolarDB PostgreSQL; and between ApsaraDB for MongoDB replica sets.
---

# Alibaba Cloud DTS Job Manager

## Core scope

Create and manage only same-account, one-way cloud-database synchronization jobs whose source and destination databases belong to the [supported synchronization links](references/supported-links.md#directed-link-groups). Apply the [source and destination database configuration](references/database-instance-configuration.md) for database instances or clusters, access methods, and regions; apply [DbList](references/db-list.md) and [Reserve](references/reserve.md) for synchronized objects and parameters.

Bidirectional or reverse synchronization, cross-account jobs, migration, subscription, data validation, and unregistered engines are outside management scope. Read-only queries may report these jobs, but stop before any write.

## Runtime

Every operation runs through `dtscli`, which must be on `PATH`. macOS, Linux, and Windows are supported. When the shell reports `dtscli: command not found`, read [platform installation and command execution](references/runtime-platforms.md) to select the installer, paths, and shell syntax for the actual host. When the current message already authorizes installation, run the documented non-interactive installer and continue; only stop and tell the user when that authorization is absent. Never fall back to another way of calling DTS.

When a `dtscli` command fails because the Alibaba Cloud CLI or the DTS plugin is missing — including `Plugin 'aliyun-cli-dts' is required ... but not installed`, even when `error_class` is `remote` — run this once and then continue the same command. Do not ask the user to authorize it, and do not add `--update`:

```bash
dtscli job deps install --yes
```

That install is not a plan change. If `execute` failed with `resource_effect` `NONE` only because the component was missing, retry `execute` once on the same `attempt_id` under the approval already given.

Do not add `--update`, and do not run `aliyun` yourself: this includes plugin installation, version queries, and API calls for products such as DDS, MongoDB, or DTS. Do not replace the `aliyun` binary. Stop the current task only when a command's JSON output carries an `error_class` whose `message` contains `ERROR: unchecked version`: preserve and report that error, and run no further `dtscli job` command or any `aliyun` command. A successful `dtscli doctor` check that merely mentions those words is not that error; continue. When reporting the CLI version, quote the `version` field from `dtscli job deps install`. Do not run `aliyun version`. Do not upgrade the Alibaba Cloud CLI and do not read the same data through another interface. See [setup](references/setup.md#install-or-update-the-cli-and-plugin).

In the current user session, run `dtscli version --json` only the first time this Skill is used. Confirm that capabilities contains `skills.ensure`, then run:

```bash
dtscli skills ensure --agent <agent>
```

Later steps and sub-agents in the same session run business commands directly. Continue when `ready=true`, including `action=busy`. Stop and reload Skill files when `reload_required=true`. When `ready=false` without reload, read [automatic Skills updates](references/skills-updates.md). `--agent` names the current host's stable lowercase identifier and must match `[a-z][a-z0-9_-]{0,31}`. Common hosts: `codex`, `claude`, `cursor`, `zcode`, `qoder`, `qoderwork`, `qwencode`, `qwenworkcn`, `opencode`, or `kimi`.

Results are written as JSON on standard output and progress on standard error. On failure, the exit code is non-zero. Standard output may contain a generic error with `error_class`, or retain the command-specific status or execution summary. Interpret the JSON under the relevant workflow; do not determine success from the exit code or one field alone.

## Request identity

Before any cloud API invocation, read this skill's [package identity manifest](references/manifest.json). Use only its top-level non-empty string `name` as `{skill-name}` and only its top-level non-empty string `version` as `{skill-version}`. The `name` must match this Skill's frontmatter `name` and the skill directory name. If missing, invalid, or inconsistent, STOP. NEVER invent, guess, or reuse a name or version from another skill. On a skill switch or return, reread that skill's package identity manifest. Read [request identity](references/request-identity.md) before constructing the request identifier.

Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder.

Attach `--user-agent` only to `dtscli` commands that call an OpenAPI and accept it: `dtscli job instances`, `job price`, `job get`, `job list`, `job precheck`, `job start`, `job pause`, `job rename`, `job create test`, and `job create execute`. Do not attach it to any other command, including `version`, `skills ensure`, `skills install`, `upgrade`, `doctor`, `job auth login`, `job auth status`, `job deps install`, `job credentials collect`, and the locally completed `job create scenarios`, `job create init`, and `job create review`. Exact user-agent with skill version propagation across CLI/SDK/Terraform:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dts-job-manager/{session-id} skill-version/{skill-version}"
```

## Core Security Requirements

- Never accept or handle a secret, credential, token, or authorization code in chat. Follow [setup](references/setup.md) for authentication and [database credentials and connection tests](references/credentials-and-security.md) for database credentials.
- Before every management operation, show the redacted target, key parameters, action, and billing or lifecycle impact, then obtain explicit confirmation. A change to the plan, parameters, or action requires new confirmation.
- When the same user message names the instances, databases or tables, and job name, and explicitly approves purchasing that unchanged plan, run `dtscli job create execute --attempt-id <attempt-id> --yes` once. Do not copy `confirmation_sha256` to the user. A changed plan requires a new confirmation.
- When the same user message names the job region and the job name (or job ID) and explicitly approves suspending, starting, or renaming that unchanged target, show the review and run that one operation once without asking again. That authorization covers only that job and that operation: a change to the target, direction, or operation requires new confirmation, and it never carries over to another job or another operation.
- Do not retry a management operation before verifying the previous outcome. When a purchase result is ambiguous, stop, ask the user to check the console, and never retry `execute`.
- Execute only a call that matches the user's request and appears in the [API allowlist](references/api-allowlist.md).

## Create

Sub-agents run only `dtscli`. The path below does not require reading references first; read the matching document from the table at the end only when the user must choose the class, stage combination, or existing-destination policy, or after a command fails or a required field is missing. Never read credential files.

Creation does not query existing jobs for a duplicate name. Use the job name the user supplied and create a new job. Do not wait for `delay_seconds` to become 0.

The instance class, the stage combination, and the existing-destination-object policy are the user's decisions and must not be filled in from a template: keep a valid choice the user already made, and when a choice is missing or invalid, obtain it under the three rules below before compiling the plan. After the required choices exist, follow the numbered sequence below exactly. Do not skip or reorder a step except when `next_step` requires credential collection followed by another `review`.

- Class: when the user has not chosen one, run `dtscli job price` first, show every reviewed class with its complete quotation, and require the user to select one; preserve a valid class the user already gave. Once a class is selected, query it once with `--instance-class` after loading the scenario and resolving both endpoints but before `create init`. Never preselect from RPS or price.
- Stage combination: follow [creation choice elicitation](references/job-creation.md#creation-choice-elicitation), show the available combinations, and require the user to select one; keep a valid combination the user already chose. Incremental synchronization is always on and cannot be disabled.
- Existing-destination-object policy: follow the [existing destination object policy](references/reserve.md#existing-destination-object-policy) and let the user choose between failing the precheck when destination objects exist and ignoring that precheck. Ignoring applies to that one precheck only; it never clears or rebuilds the destination, and a full-load primary-key conflict keeps the destination row. Any other precheck failure must stop.

1. Load the scenario template. If the scenario is unknown, run the same command without `--name` and pick only a returned name. When both sides are RDS PostgreSQL, the scenario is `rds-postgresql-to-rds-postgresql`; resolve both instance names with `--type RDS --engine POSTGRESQL --page-size 20` (`src` then `dest`). Do not use the PolarDB PostgreSQL flags for an RDS PostgreSQL instance.

```bash
dtscli job create scenarios --name <scenario>
```

2. Resolve the source and destination endpoints in order, then query the quotation. When the user gave only an instance name, run the source `job instances` query once under [resolve an instance ID from a name](references/database-instance-configuration.md#list-cloud-database-instances); run the destination query only after one exact source match. Skip the query for an endpoint that already has a complete instance ID. Stop immediately when either endpoint has zero or several matches or is unusable; do not continue to the other endpoint, quotation, or plan compilation. After both endpoints are known, run `dtscli job price --instance-class <instance-class>` once, with no region or link argument.

3. Write public JSON. Do not include usernames, passwords, `engine`, `instance_type`, or the profile. Angle brackets mark placeholders to replace with the user's actual choices. PostgreSQL and MongoDB endpoints need `database`; for MongoDB that field is the authentication database, such as `admin`, and synchronized objects belong in `objects`. Never put the authentication database into `objects`, and never use the database being synchronized as `database`. PolarDB MySQL destinations need `destination_storage_engine`.

```json
{
  "scenario": "<scenario>",
  "job_name": "<job-name>",
  "source": {
    "region": "<region-id>",
    "instance_id": "<source-instance-id>",
    "database": "<postgresql-database-or-mongodb-auth-database>"
  },
  "destination": {
    "region": "<region-id>",
    "instance_id": "<destination-instance-id>",
    "database": "<postgresql-database-or-mongodb-auth-database>"
  },
  "stages": { "structure": true, "full": true },
  "objects": [{ "source": "<namespace>", "objects": [{ "source": "<object>" }] }],
  "existing_destination_policy": "<existing-destination-policy>",
  "instance_class": "<instance-class>",
  "destination_storage_engine": "<polardb-mysql-only>"
}
```

Fill `stages` with the combination the user selected; the example is the standard structure-plus-full combination, and an incremental-only combination sets both to `false`. `existing_destination_policy` and `instance_class` must carry the user's selected values: do not submit the placeholders and do not substitute a default for the user's choice. Omit both `database` fields for the MySQL family; that family rejects them. For PostgreSQL set them to the databases that hold the synchronized objects. Different instances may use the same database name, such as `dtstest` on both sides. For MongoDB set them to the authentication database, such as `admin`, and keep the synchronized database in `objects`. Omit `destination_storage_engine` unless the destination is PolarDB MySQL; then set the engine the user named, such as `innodb`.

4. Compile the plan:

```bash
dtscli job create init --input <plan.json>
```

5. Follow the returned `next_step`: `review` reports credentials and the plan summary, then `test` reports connectivity and issues the confirmation hash. When `outcome` is `credentials_required`, run `dtscli job credentials collect --attempt-id <attempt-id>` once, return to `review`, then run `test`. Do not rebuild the public input and do not skip `review`; `test` accepts only an attempt that has been reviewed. The credential page is English by default; add `--language zh` for Chinese. Neither the page address nor credential values enter the conversation.

6. After `test` returns `ready_for_confirmation`, show the complete plan from `review`, this run's `connection_test`, the class and quotation obtained in step 2, and the billing impact, and obtain explicit confirmation. An approval already given in the current user message satisfies this confirmation; do not ask again. Re-query the same class only when that quotation's cache lifetime has expired. Once the user has approved the unchanged plan, run execute once. Do not stop after the connection test:

```bash
dtscli job create execute --attempt-id <attempt-id> --yes
```

Do not copy `confirmation_sha256`. When `outcome` is `indeterminate`, or `failed` with `resource_effect` `UNKNOWN`, stop and never retry `execute`; if a job ID is present, run `dtscli job get --job-id <job-id> --region <region-id>`, otherwise ask the user to check the console. When `outcome` is `failed` with `resource_effect` `NONE` (nothing was created) or `INSTANCE_PURCHASED` (the instance exists and is billing), determine the cause. If the only cause is a missing Alibaba Cloud CLI or DTS plugin, install it as described under Runtime and execute once more on the same `attempt_id` without asking again. For any other cause, obtain the user's confirmation again, and then execute once more on the same `attempt_id`: the purchased instance is reused for configuration and start, and a second instance is never bought.

7. After a successful create, follow `next_step` for the precheck, then `job get`. Do not wait for delay 0; a `CHECKING` precheck is not a failure — query it again as described in [job status · precheck](references/job-status.md#precheck).

`job price` quotes by class only and does not accept `--region`; the price does not vary with link or region.

## Query

When the user asks to list synchronization jobs in a region, follow [list jobs](references/job-status.md#list-jobs) and run `dtscli job list --region <region-id> --page 1 --page-size 10`. Show this page's job IDs, instance IDs, names, and raw statuses, plus the returned count and total count. If more pages exist, report how many jobs remain and let the user decide whether to continue.

If a job ID is known, run `dtscli job get --job-id <job-id> --region <region-id>`. When only a name is known, run `dtscli job list --region <region-id> --job-name <job-name>` and compare complete names case-sensitively on this page. Stop when there are zero or multiple exact matches. After one match, run `job get` or `dtscli job precheck --job-id <job-id> --region <region-id>`. Add `--with-db-list` when the user asks for the synchronized objects, and report the structured `db_list` mapping and counts. Interpret the raw `status`. Report an unknown value as-is and stop before any write.

When configuring a job and only an instance name is known, use `dtscli job instances` to resolve the instance ID; do not treat it as `job list`. First confirm that the `capabilities` from this session's `dtscli version --json` include `job.instances`. When they do not and the current user message already authorizes installing or upgrading the runtime dependencies, run `dtscli upgrade` once, rerun `dtscli version --json`, and continue once the capability appears; do not ask the user about it. Stop and tell the user to upgrade dtscli only when the capability is still missing after the upgrade or that authorization is absent. Pass the user-given instance name as `--instance-id`. Search the source and destination separately: use `--usage-type src` to resolve the source and `--usage-type dest` to resolve the destination. The same product can appear on either side, so do not follow the examples into one fixed side. Use these flags exactly; do not guess another `--type`, `--engine`, or `--page-size`:

```bash
dtscli job instances --region <region-id> --type RDS --engine MYSQL --usage-type <src|dest> --instance-id <instance-name> --page 1 --page-size 100
dtscli job instances --region <region-id> --type RDS --engine POSTGRESQL --usage-type <src|dest> --instance-id <instance-name> --page 1 --page-size 20
dtscli job instances --region <region-id> --type POLARDB --engine POLARDB --usage-type <src|dest> --instance-id <instance-name> --page 1 --page-size 30
dtscli job instances --region <region-id> --type POLARDB --engine POLARDB_PG --usage-type <src|dest> --instance-id <instance-name> --page 1 --page-size 30
dtscli job instances --region <region-id> --type POLARDBX20 --engine POLARDBX20 --usage-type <src|dest> --instance-id <instance-name> --page 1 --page-size 100
dtscli job instances --region <region-id> --type MONGODB --engine MONGODB --usage-type <src|dest> --instance-id <instance-name> --page 1 --page-size 100
```

| Product | `--type` | `--engine` | `--page-size` |
| --- | --- | --- | --- |
| RDS MySQL | `RDS` | `MYSQL` | `100` |
| RDS PostgreSQL | `RDS` | `POSTGRESQL` | `20` |
| PolarDB MySQL | `POLARDB` | `POLARDB` | `30` |
| PolarDB PostgreSQL | `POLARDB` | `POLARDB_PG` | `30` |
| PolarDB-X 2.0 | `POLARDBX20` | `POLARDBX20` | `100` |
| MongoDB replica set | `MONGODB` | `MONGODB` | `100` |

Further match rules are in [resolve an instance ID from a name](references/database-instance-configuration.md#list-cloud-database-instances). In user-facing text, use product names, instance names, and the resolved instance IDs; never show API enums such as `--type` or `--engine`. After a unique exact name match, write `instance_id` into the plan; stop when there are zero or several matches.

Stop when resolving an instance name returns zero or several matches, when the instance is unusable, or when either side does not satisfy the link requirements. Never pick the first row, reuse an older instance ID, or continue with a different instance.

## Price

A request that only asks for a price is read-only: run `dtscli job price --instance-class <class>` and report the unit price, the currency, and the billing unit, say whether the quote came from this run's live query or from a local cache (valid for 24 hours), and note that the purchase page and the final order remain official. Do not compile a plan, collect credentials, test connectivity, or run any `create`, `start`, `pause`, or `rename` for it. `job price` quotes by class only and accepts no `--region`, source, destination, or link parameter; do not pick a class the user did not choose, do not recommend other classes, and do not re-query for a fresher price. See [instance classes and pricing](references/instance-classes-and-pricing.md).

## Lifecycle

After locating the job, run `job get` and show the review before the first `dtscli job start`, `dtscli job pause`, or `dtscli job rename`. For a rename, that `job get` must happen before the first `rename`; a later `job get` that only reads the new name back does not replace it. Run the operation once when the same message already approved that job and that operation; otherwise obtain explicit confirmation first. A create-flow purchase approval does not authorize pause or rename, and one lifecycle authorization never carries over to another job or operation.

## Task-based reference loading

Read these only after a command fails, a field is missing, a user choice is needed for the class, stage combination, or existing-destination policy, or the user asks for pricing or link details. Do not load every creation reference at once.

| User intent | Read |
| --- | --- |
| Validate installation, profile, authentication, or service access | [Setup](references/setup.md) |
| Ask only for a price, a class quotation, or a billing unit, or compare classes | [Instance classes and pricing](references/instance-classes-and-pricing.md); read [setup](references/setup.md) first when installation or authentication needs validating |
| Create a job: scenario or field error | [Supported synchronization links](references/supported-links.md), [job creation](references/job-creation.md) |
| Create a job: stage combination or existing-destination policy | [Job creation](references/job-creation.md), [Reserve](references/reserve.md) |
| Create a job: endpoint, object, or Reserve error | Read the [source and destination database configuration](references/database-instance-configuration.md), [DbList](references/db-list.md), [Reserve](references/reserve.md), and [database credentials and connection tests](references/credentials-and-security.md) only as needed |
| Resolve an instance ID from a name to configure a job | [Source and destination database configuration · resolve an instance ID from a name](references/database-instance-configuration.md#list-cloud-database-instances) |
| List jobs, interpret status, or view precheck results | [Job status](references/job-status.md) |
| Rename or manage lifecycle | [Job lifecycle](references/job-lifecycle.md), with [job status](references/job-status.md) for current-state verification |
| Call a DTS API | Read the [API allowlist](references/api-allowlist.md) before calling it |
| Access denied, or which RAM actions this Skill requires | [RAM permissions](references/ram-policies.md) |
