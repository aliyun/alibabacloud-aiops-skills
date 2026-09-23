# Synchronization Object Selection and Renaming

## Contents

- [Selection boundary](#selection-boundary)
- [Job plan input](#job-plan-input)
- [Generated DbList](#generated-dblist)
- [Pre-execution review](#pre-execution-review)
- [Configuration validation](#configuration-validation)

This reference is the single definition of synchronization object selection, renaming, and `DbList` generation rules.

<a id="object-selection-boundary"></a>
<a id="selection-boundary"></a>
## Selection boundary

`DbList` supports two selection levels:

1. An entire database or Schema: select a database for MySQL-compatible databases and MongoDB, or a Schema within the source or destination database for PostgreSQL.
2. One or more tables or collections: select tables for MySQL-compatible databases and PostgreSQL, or collections for MongoDB.

Destination database, Schema, table, and collection names default to their corresponding source names; rename them only when the user explicitly requests it. Apply these rules:

- Selecting a table or collection synchronizes the whole object. Column-level selection, exclusion, mapping, and renaming are unsupported.
- Do not select an entire database or Schema together with individual tables or collections inside it.
- Select each source database, Schema, table, or collection only once.
- Map each source database or Schema to only one destination database or Schema.
- Do not map different source objects to the same destination table or collection.
- Whole-instance selection, document fields, row or document filters, DML or DDL subsets, wildcards, merge rules, and arbitrary object JSON are unsupported.

When a request exceeds this boundary, identify the unsupported part and stop before credential setup, database connection testing, quotations, or writes.

<a id="job-plan-input"></a>
## Job plan input

Require a non-empty `objects` array. Every database type uses the **same nested shape**; the field names do not change per engine:

```json
{
  "source": "<source namespace>",
  "target": "<destination namespace, only when renaming>",
  "objects": [
    { "source": "<source object>", "target": "<destination object, only when renaming>" }
  ]
}
```

The outer `source` is a namespace and the inner `objects[]` are objects inside it. What each layer means depends on the engine, but the field names do not:

| Database type | Outer `source` | Inner `objects[].source` |
| --- | --- | --- |
| MySQL family | database | table |
| PostgreSQL | schema (the database holding it goes in the endpoint's `database`) | table |
| MongoDB | database | collection |

Rules:

- **Omit the inner `objects` array to select the whole namespace.** That is the only way to express "synchronize an entire database or schema".
- `target` is only for renaming; omit it to keep the source name. Never supply a `target` without its `source`.
- Run `dtscli job create scenarios --name <scenario>` for the scenario's complete template and replace the placeholders. Its `notes.objects` states what the namespace and object layers mean for that engine.

MySQL family, synchronizing table `t1` in database `db1`:

```json
{ "source": "db1", "objects": [{ "source": "t1" }] }
```

MongoDB, synchronizing collection `test_data` in database `hongxian`. Note that the endpoint's `database` holds the **authentication** database, which is unrelated to the database selected here:

```json
{ "source": "hongxian", "objects": [{ "source": "test_data" }] }
```

PostgreSQL, synchronizing the whole `public` schema, inside the database named by the endpoint's `database`:

```json
{ "source": "public" }
```

Reject keys not defined above instead of accepting them without validation.

<a id="generated-dblist"></a>
## Generated `DbList`

When selecting an entire database or Schema, emit:

```json
{
  "<source-namespace>": {
    "name": "<target-namespace>",
    "all": true
  }
}
```

For selected tables or collections, emit:

```json
{
  "<source-namespace>": {
    "name": "<target-namespace>",
    "all": false,
    "Table": {
      "<source-object>": {
        "name": "<target-object>",
        "all": true
      }
    }
  }
}
```

Top-level keys are source databases for MySQL-compatible databases and MongoDB, or source Schemas for PostgreSQL. DTS uses the internal `Table` key for both tables and MongoDB collections. The OpenAPI field is `DbList`; serialize the structured object once as compact JSON and pass it as one `--db-list` argument.

Generation rules:

- An entire database or Schema item has exactly `name` and `all=true`; it has no `Table` member.
- When selecting tables or collections, their parent database or Schema has exactly `name`, `all=false`, and a non-empty `Table` member.
- `Table` keys are source object names; top-level and second-level `name` fields are destination names; each selected object has `all=true`.
- Reject `Column` and every other third-level member.
- Reject serialized UTF-8 output larger than 1 MiB.

<a id="object-selection-review"></a>
<a id="pre-execution-review"></a>
## Pre-execution review

Before authorization, show every fully qualified mapping:

| Selection | Example |
| --- | --- |
| MySQL-family or MongoDB database | `<source-database> → <destination-database>` |
| MySQL-family table or MongoDB collection | `<source-database>.<source-table> → <destination-database>.<destination-table>` |
| PostgreSQL Schema | `<source-database>.<source-schema> → <destination-database>.<destination-schema>` |
| PostgreSQL table | `<source-database>.<source-schema>.<source-table> → <destination-database>.<destination-schema>.<destination-table>` |

When destination names are omitted, show the same-name mapping instead of asking a redundant question. Review existing destination objects under the [Reserve policy](reserve.md#existing-destination-object-policy). Do not expose raw `DbList` JSON unless the user explicitly requests safe technical detail.

The official [DTS object definition](https://help.aliyun.com/en/dts/developer-reference/objects-of-dts-tasks) defines `DbList` and `all`. Related synchronization guides describe the selection rules for [PostgreSQL Schemas and tables](https://help.aliyun.com/en/dts/user-guide/configure-one-way-synchronization-between-apsaradb-rds-for-postgresql-instances), [MongoDB databases and collections](https://help.aliyun.com/en/dts/user-guide/synchronize-data-from-an-apsaradb-for-mongodb-instance-to-another-apsaradb-for-mongodb-instance), and [MySQL databases](https://help.aliyun.com/en/dts/user-guide/precautions-and-limits-for-synchronizing-data-from-a-mysql-database).

<a id="configuration-validation"></a>
## Configuration validation

Use `dtscli job create scenarios` to obtain the schema and build against it. Do not manually construct a broader object model:

```bash
dtscli job create scenarios --name <registered-scenario>
```

Before reading credentials or invoking a cloud API, `dtscli job create init` independently revalidates the generated `DbList` and rejects ambiguous or duplicate mappings. The `summary.mappings` that `review` then returns lists each mapping as `source-namespace.object -> destination-namespace.object`, or `source.* -> destination.*` for a whole namespace. The pre-execution review must show those entries; never report counts alone.
