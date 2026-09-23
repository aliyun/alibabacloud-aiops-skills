# Source and Destination Database Configuration

## Contents

- [Access-method boundary](#database-instance-access-boundary)
- [Database instance input fields](#database-instance-input-fields)
- [Source, destination, and job regions](#destination-region-requirements)
- [Resolve an instance ID from a name](#list-cloud-database-instances)
- [Required field completeness check](#required-field-completeness-check)
- [CLI configuration argument mapping](#cli-configuration-argument-mapping)
- [Database instance configuration and plan validation](#database-instance-configuration-and-plan-validation)

> API specification: DTS `2020-01-01`.
>
> Scope: define the source and destination database fields, cloud-database access methods, and region rules used by registered one-way synchronization links.
>
> Specification sources: [ConfigureDtsJob](https://help.aliyun.com/en/dts/developer-reference/api-configuredtsjob), the [synchronization matrix](https://help.aliyun.com/en/dts/user-guide/data-synchronization-scenarios), and the [PolarDB-X 2.0 synchronization guide](https://help.aliyun.com/en/dts/user-guide/synchronize-data-between-polardb-x-2-0-instances). The reviewed `CreateDtsInstance` specification uses `POLARDBX20` for both the source and destination engines of PolarDB-X 2.0.

<a id="database-instance-access-boundary"></a>
## Access-method boundary

Use only cloud-instance access for the source and destination databases. Internal `instance_type` is limited to the registered `RDS`, `POLARDB`, `POLARDBX20`, and `MONGODB` values. The wider DTS API also defines `EXPRESS`, `OTHER`, `DG`, `ECS`, and `CEN`, but this Skill does not support those access methods. Reject them for either side and stop before collecting credentials, testing connections, quoting, or writing. Do not collect a database IP, port, Oracle SID, vSwitch, gateway, or CEN parameter as a fallback.

<a id="database-instance-input-fields"></a>
<a id="database-instance-fields"></a>
## Database instance input fields

The source and destination databases both use this Planner structure:

```json
{
  "instance_id": "<cloud-instance-id>",
  "region": "<database-instance-region>",
  "database": "<required-for-postgresql-and-mongodb-only>"
}
```

The field is `database`, not `database_name`. For PostgreSQL it holds the database containing the synchronized objects. For MongoDB it holds the account's **authentication** database, such as `admin`, which is unrelated to the database being synchronized: that one goes in `objects`. The MySQL family does not accept this field.

| Product | Scenario product identifier | Internal `engine` | Internal `instance_type` | Public-input `database` |
| --- | --- | --- | --- | --- |
| RDS MySQL | `rds-mysql` | `MYSQL` | `RDS` | Omit |
| RDS PostgreSQL | `rds-postgresql` | `POSTGRESQL` | `RDS` | Database containing the synchronized objects |
| PolarDB MySQL | `polardb-mysql` | `POLARDB` | `POLARDB` | Omit |
| PolarDB PostgreSQL | `polardb-postgresql` | `POLARDB_PG` | `POLARDB` | Database containing the synchronized objects |
| PolarDB-X 2.0 | `polardbx20` | `POLARDBX20` | `POLARDBX20` | Omit |
| MongoDB replica set | `mongodb-replica-set` | `MONGODB` | `MONGODB` | Authentication database |

The Planner must derive the table's `engine` and `instance_type` from the registered `scenario`; public input must not repeat either field. The plan must reuse the derived values in `CreateDtsInstance` purchase requests, `DescribeDtsInstancePrice` requests, the Endpoint engine arguments of `ConfigureDtsJob`, and `RunEndpointLinkTest` calls made from the compiled plan. In particular, PolarDB MySQL uses `POLARDB`, and PolarDB PostgreSQL uses `POLARDB_PG`. PolarDB-X 2.0 uses `POLARDBX20` as both its engine and instance type; do not use the legacy `DRDS` label shown by `CreateDtsInstance --help`. In user-facing text, use product names and database instances or clusters; never expose API enums or refer to all database resources as endpoints.

Rules:

- Require the non-empty database instance or cluster ID defined by the selected product for both the source and destination. When the user gave only an instance name, first resolve it under [resolve an instance ID from a name](#list-cloud-database-instances) and then write the ID; when they already gave a complete instance ID, use it. Never infer an ID from a prefix, and never pick one yourself when there are zero or several exact name matches.
- For PolarDB-X 2.0, support Standard Edition and Enterprise Edition; do not add edition metadata to the plan or review.
- PolarDB PostgreSQL means the standard PostgreSQL-compatible product. Exclude PolarDB for PostgreSQL (Compatible with Oracle) and distributed PolarDB PostgreSQL.
- For both the PostgreSQL source and destination, require the database containing the synchronized objects as `database`. One task synchronizes one source database to one destination database; collect Schema names separately in each object mapping.
- An RDS PostgreSQL destination uses the same product row as an RDS PostgreSQL source: `--type RDS --engine POSTGRESQL --page-size 20` and `--usage-type dest`. Two RDS PostgreSQL instances use the scenario `rds-postgresql-to-rds-postgresql`. Do not resolve that destination with the PolarDB PostgreSQL flags.
- For MongoDB, require the source and destination authentication databases as `database`. Do not infer either from a selected synchronization database; `admin` is common but is not a safe default.
- For MongoDB, require explicit confirmation that the source and destination database instances are replica sets. If either side is a sharded cluster, stop before compilation or database connection testing. This Skill does not support MongoDB sharded clusters.
- Require both database instances or clusters to belong to the active Alibaba Cloud profile. Do not submit Endpoint owner IDs or RAM role fields.
- Omit Endpoint IP, port, Oracle SID, vSwitch, and self-managed network fields. Omit database-name fields for managed MySQL and require them for every PostgreSQL link and MongoDB.
- Keep database usernames and passwords out of the plan compilation input. `dtscli` injects them only into the database connection test and configuration call performed with the compiled plan.
- Reject every extra key in the source or destination database object. Do not infer support from an instance-ID prefix or from values accepted by the wider DTS product.

<a id="destination-region-requirements"></a>
### Source, destination, and job regions

Preserve the actual regions of the source and destination database instances; source and destination regions may differ. Derive the compiled plan's top-level `region` from `destination.region`. This top-level value is the DTS instance and business-request region. Do not collect a third region or replace the source database region.

<a id="list-cloud-database-instances"></a>
<a id="resolve-instance-id-by-name"></a>
### Resolve an instance ID from a name

Configuring a synchronization job needs a cloud database instance ID. Users usually give an instance name. Use `dtscli job instances` and pass that name as `--instance-id`: the service fuzzy-matches instance names or instance IDs. Do not use `job list` (that matches DTS job names). This command is the only way to look up an instance: never call a product or generic API directly, and never substitute another product's equivalent. When the command fails because a component is missing, install it as described in [setup](setup.md#install-or-update-the-cli-and-plugin) and run the same command once more. Stop only when that command's JSON output carries an `error_class` whose `message` contains `ERROR: unchecked version`: preserve and report it, and run no further `dtscli job` command or any `aliyun` command. A successful `dtscli doctor` check that mentions the same words is not that error; continue. Quote the CLI version from `dtscli job deps install` and do not run `aliyun version`. Do not replace `aliyun`, reuse an older instance ID, take the first hit, or continue with a different instance.

Before the call, confirm that the `capabilities` from this session's `dtscli version --json` include `job.instances`. When they do not and the current user message already authorizes installing or upgrading the runtime dependencies, run `dtscli upgrade` once, rerun `dtscli version --json`, and continue once the capability appears; do not ask the user about it and do not guess another command. Stop and tell the user to upgrade dtscli only when the capability is still missing after the upgrade or that authorization is absent. Search the source and destination separately: `--usage-type` is `src` or `dest`. `--region` is that cloud database instance's region; if the region is unknown, ask the user first and do not retry other regions. Fill `--type`, `--engine`, and `--page-size` from the selected product. `ModName` is fixed to `SYNC` by the command; do not pass it. MongoDB listings are replica sets only: omitting `--engine-arch-type` still sends `1`; stop for a sharded cluster (`2`). PolarDB-X 2.0 uses `POLARDBX20`; do not use `DRDS`.

When the user already gave a complete instance ID, write it into the plan and do not search. Keep passing `--instance-id` with the user-given name or ID; do not omit it yourself. PolarDB-X 2.0 does not support service-side fuzzy search on `InstanceId`: dtscli pages the full PolarDB-X list and keeps only entries whose `instance_name` or `instance_id` equals the keyword exactly (case-sensitive). Other products first send `--instance-id` for a service-side fuzzy search; if that page is empty, they use the same exact match against an unfiltered listing. Omit `--instance-id` only when the user explicitly asks to browse that region's candidates, or when even the exact match is empty and the user agrees to browse.

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

PolarDB listings must use `--page-size 30`; a smaller page size may be rejected. On this page, compare `instance_name` values case-sensitively and in full: after a unique exact match, write that `instance_id` into the plan and repeat the instance name and ID to the user; when there is no exact match, show any fuzzy hits on this page as name-and-ID pairs and require a choice, or ask for another name or the instance ID if there are none; when several names match exactly, show them and require a choice. Never pick one yourself or infer an ID from a prefix. `count` is this page only: when it equals this run's `--page-size`, say there may be another page. In user-facing text, use product names, instance names, and instance IDs; never show the table's API enums, and never emit VPC, address, or account fields.

<a id="required-field-completeness-check"></a>
## Required-field completeness check

Before compilation, verify in order that the link is registered in [supported synchronization links](supported-links.md), both sides satisfy the [access-method boundary](#database-instance-access-boundary), the [database instance input fields](#database-instance-input-fields) are complete, and the regions satisfy the [source, destination, and job region](#destination-region-requirements) requirements.

Treat null, empty, whitespace-only, example, or unresolved placeholder values as missing. Report only the missing non-secret inputs; never build a partial request or infer missing values.

<a id="cli-configuration-argument-mapping"></a>
## CLI configuration argument mapping

After the source and destination database configurations pass the completeness check, the Planner emits these common arguments:

| Public input or derived value | Source argument | Destination argument |
| --- | --- | --- |
| `instance_type` derived from `scenario` | `--source-endpoint-instance-type <type>` | `--destination-endpoint-instance-type <type>` |
| `engine` derived from `scenario` | `--source-endpoint-engine-name <engine>` | `--destination-endpoint-engine-name <engine>` |
| `instance_id` | `--source-endpoint-instance-id <id>` | `--destination-endpoint-instance-id <id>` |
| `region` | `--source-endpoint-region <region>` | `--destination-endpoint-region <region>` |
| `database`, when required | `--source-endpoint-database-name <database>` | `--destination-endpoint-data-base-name <database>` |

Use the engine and exact instance type from the product table. The Planner copies `destination.region` to the compiled plan's top-level `region` and uses it both for the DTS job region and for service access. These values do not replace the region of either the source or destination database.

<a id="database-instance-configuration-and-plan-validation"></a>
## Database instance configuration and plan validation

Obtain the current database-instance configuration schema with:

```bash
dtscli job create scenarios --name <registered-scenario>
```

The creation flow uses `dtscli job create init` to compile once and uses that exact file for credential checks, database connection testing, purchase, and configuration. A repeated call may reuse only a fully validated, byte-identical plan; stop when the input or compiler context changes. Stop if plan compilation rejects the source or destination database configuration, a required region is missing, or an extra field is present.
