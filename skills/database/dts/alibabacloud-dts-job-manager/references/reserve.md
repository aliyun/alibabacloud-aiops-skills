# Synchronization Job `Reserve` Parameters

## Contents

- [Common parameters](#common-parameters)
- [Source database parameters](#source-database-parameters)
- [Destination database parameters](#destination-database-parameters)
- [Compilation and validation](#compilation-and-validation)

DTS describes source and destination database capabilities independently. `Reserve` parameters likewise depend on the source or destination role and database type, not on repeated source-to-destination combinations. Do not accept `Reserve` JSON supplied directly by the user. Use only the keys defined here, and reject duplicate and unknown keys.

<a id="common-parameters"></a>
## Common parameters

Every synchronization job must contain the following parameters, and every value is a string:

| Parameter | Compiled value | Value source | Requirement |
| --- | --- | --- | --- |
| `targetTableMode` | `"0"` or `"2"` | User-confirmed existing-destination policy | No default; confirm before compilation |
| `autoStartModulesAfterConfig` | `"none"` | Fixed value | Configuration must not auto-start modules |
| `syncArchitecture` | `"oneway"` | Fixed value | Support one-way synchronization only |

<a id="existing-destination-object-policy"></a>
### Existing destination object policy

This section is the official documentation for user-visible behavior and internal mapping. Keep a supplied choice when it clearly maps to one behavior below; do not ask for it again. Otherwise, present both behaviors and require a selection before compilation. Terms such as “overwrite,” “replace,” or “rebuild” are ambiguous and cannot select a behavior.

When `existing_destination_policy` is omitted, the CLI compiles the safer `fail_if_exists`. That is only a field default, not the user's choice: obtain an explicit selection under this section before compiling and write the result into the public input.

| User-facing choice | Planner public input | `targetTableMode` | Behavior |
| --- | --- | --- | --- |
| **Fail the precheck when the destination table or collection exists** | `"fail_if_exists"` | `"0"` | Stop during precheck so the destination object can be inspected or cleaned up |
| **Ignore the existing-object precheck error and continue** | `"ignore_precheck_and_continue"` | `"2"` | Continue after ignoring that precheck error; this does not clear, truncate, or drop and recreate the destination object |

Conflict handling for mode `2` depends on the destination database family:

| Destination database family | During full initialization | During incremental synchronization | Other limitation |
| --- | --- | --- | --- |
| RDS MySQL, PolarDB MySQL, and PolarDB-X 2.0 | A primary- or unique-key conflict retains the existing destination row and skips the corresponding source row | A conflicting source change overwrites the destination row | Applies to these three MySQL-compatible destination databases |
| RDS PostgreSQL and PolarDB PostgreSQL | A primary- or unique-key conflict retains the destination record and skips the corresponding source record | The source change overwrites the conflicting destination record | Structure differences can prevent initialization, synchronize only some columns, or fail the job |
| MongoDB replica set | When a destination document has the same primary or unique key, retain it and do not synchronize the corresponding source document | Follow the observed DTS job behavior; do not infer overwrite semantics | Mode `2` does not clear an existing collection |

Never describe mode `2` as unconditional “overwrite.” If an empty destination is required, the user must clean it outside this Skill and select the fail-if-present behavior so precheck verifies that the object is absent. Show the user-facing behavior and limitation, not the field name or numeric value.

**State this explicitly whenever structure initialization is also enabled**: the policy skips only that one *precheck*. Structure initialization still tries to create the objects on the destination. When a destination object of the same name already exists, the precheck passes and the job can still fail during structure initialization — especially on PostgreSQL, per the "structure differences" note above. Users choosing this policy usually expect "the job will run"; what they may get is a passed precheck followed by a failed initialization whose cause comes from the database and is usually withheld. Explain that difference before asking for confirmation, and when the destination really does hold objects of the same name and the user wants one clean synchronization, recommend clearing the destination first and switching to the fail-if-present policy.

The behavior is defined by Alibaba Cloud's [Reserve parameter documentation](https://help.aliyun.com/en/dts/developer-reference/reserve-parameter-description), [RDS PostgreSQL synchronization guide](https://help.aliyun.com/en/dts/user-guide/configure-one-way-synchronization-between-apsaradb-rds-for-postgresql-instances), [PolarDB PostgreSQL synchronization guide](https://help.aliyun.com/en/dts/user-guide/synchronize-data-between-polardb-for-postgresql-clusters), and [MongoDB replica-set synchronization guide](https://help.aliyun.com/en/dts/user-guide/synchronize-data-from-an-apsaradb-for-mongodb-instance-to-another-apsaradb-for-mongodb-instance). Planner public input accepts only the two policy names in this table and maps them internally to `"0"` or `"2"`.

### Configuration, start, and synchronization direction

| Parameter | Fixed value | Execution requirement |
| --- | --- | --- |
| `autoStartModulesAfterConfig` | `"none"` | After `ConfigureDtsJob` succeeds, call `StartDtsJob` explicitly under the combined creation confirmation |
| `syncArchitecture` | `"oneway"` | Use the reviewed one-way/`Forward` arguments for purchase and configuration; reject bidirectional and reverse requests |

<a id="source-database-parameters"></a>
## Source database parameters

Add parameters according to the source database type. Only a MongoDB replica-set source requires a source-specific parameter:

| Source database | Parameter | Compiled value | Requirement |
| --- | --- | --- | --- |
| MongoDB replica set | `srcEngineArchType` | `"1"` | Fixed to identify a replica set; stop when the source is a sharded cluster |

RDS MySQL, PolarDB MySQL, PolarDB-X 2.0, RDS PostgreSQL, and PolarDB PostgreSQL sources add no source-specific `Reserve` parameter.

<a id="destination-database-parameters"></a>
## Destination database parameters

Add parameters according to the destination database type:

| Destination database | Parameter | Compilation rule |
| --- | --- | --- |
| RDS MySQL | `triggerMode` | Default to `"manual"`; use `"auto"` only when the user explicitly requests it and the Planner schema accepts it |
| PolarDB MySQL | `triggerMode`, `anySinkTableEngineType` | Compile from the trigger-handling behavior and the user's storage-engine choice |
| PolarDB-X 2.0 | None | Use common parameters only; never emit `triggerMode` |
| RDS PostgreSQL and PolarDB PostgreSQL | None | Use common parameters only |
| MongoDB replica set | `destEngineArchType` | Fix to `"1"` to identify a replica set; stop when the destination is a sharded cluster |

### Trigger handling for MySQL-compatible destinations

For an RDS MySQL or PolarDB MySQL destination with table-level selection, default to `triggerMode="manual"`, which means DTS does not copy source triggers automatically. Use `"auto"` only when the user explicitly requests it and the Planner schema accepts it. Do not ask about trigger handling when the default satisfies the request. Show the applied behavior in the review before execution, not the internal key or value.

### PolarDB MySQL destination storage engine

When the destination is PolarDB MySQL, compile `anySinkTableEngineType` as follows:

| User-facing choice | Plan compilation input | `Reserve` value |
| --- | --- | --- |
| InnoDB | `destination_storage_engine="innodb"` | `anySinkTableEngineType="innodb"` |
| X-Engine | `destination_storage_engine="xengine"` | `anySinkTableEngineType="xengine"` |

Do not infer the value from an instance ID, omit it, or apply a default. Include the destination storage engine in the review before execution, but do not show the internal `Reserve` key.

<a id="compilation-and-validation"></a>
## Compilation and validation

The Planner must combine the common parameters, parameters for the source database, and parameters for the destination database; serialize the object once as compact JSON; and pass it as one `--reserve` argument. Require the final object to contain exactly the three common keys and the dedicated keys required by the current source and destination databases. Do not add parameters for another database type.

Print the current schema from the Planner:

```bash
dtscli job create scenarios --name <registered-scenario>
```

The Planner is the executable source of truth. Stop before any cloud write when a database type is unsupported, a user choice is unresolved, a parameter is missing or duplicated, or an unknown parameter is present.
