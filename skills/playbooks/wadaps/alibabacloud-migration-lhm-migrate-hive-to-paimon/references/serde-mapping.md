# SERDE → DLF FORMAT Mapping

## Full Mapping

| Full Hive SERDE class | DLF FORMAT | Notes |
|---|---|---|
| `org.apache.hadoop.hive.ql.io.orc.OrcSerde` | `USING ORC` | Most common format; used by the vast majority of tables |
| `org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe` | `USING CSV` | Text format, corresponds to TextInputFormat |
| `org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe` | `USING PARQUET` | Columnar storage format |
| `org.apache.hadoop.hive.serde2.avro.AvroSerDe` | `USING AVRO` | Avro format (less common) |
| `org.apache.hadoop.hive.serde2.JsonSerDe` | `USING JSON` | JSON format (less common) |

## Quick Match Rules

No need to match the full class name; match by keyword substring:

| SERDE class name contains | DLF FORMAT |
|---|---|
| `OrcSerde` | `USING ORC` |
| `LazySimpleSerDe` | `USING CSV` |
| `ParquetHiveSerDe` | `USING PARQUET` |
| `AvroSerDe` | `USING AVRO` |
| `JsonSerDe` | `USING JSON` |

## INPUTFORMAT Fallback

When SERDE info is ambiguous, use INPUTFORMAT as a fallback:

| INPUTFORMAT class name contains | DLF FORMAT |
|---|---|
| `OrcInputFormat` | `USING ORC` |
| `TextInputFormat` | `USING CSV` |
| `MapredParquetInputFormat` | `USING PARQUET` |
| `AvroContainerInputFormat` | `USING AVRO` |

## CSV Format Notes

When the SERDE is `LazySimpleSerDe`, the Hive DDL may include `SERDEPROPERTIES`:

```sql
WITH SERDEPROPERTIES (
  'field.delim'=',',
  'serialization.format'=','
)
```

In the DLF external table, pass the delimiter config via OPTIONS (add as needed):

```sql
OPTIONS(
  'path'='oss://...',
  'delimiter'=','
)
```

The default delimiter is `\001` (Hive default); for standard comma-separated files it is `,`.

## Default Handling

If the Hive DDL has no `ROW FORMAT SERDE` info:
1. Check for `STORED AS` info (e.g. `STORED AS ORC`, `STORED AS PARQUET`).
2. If none, default to `USING ORC` and add a warning comment in the output.
