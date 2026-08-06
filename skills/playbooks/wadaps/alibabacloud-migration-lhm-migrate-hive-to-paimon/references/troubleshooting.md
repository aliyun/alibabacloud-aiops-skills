# migration-lhm-migrate-hive-to-paimon Troubleshooting

> Extracted from SKILL.md. Common issues encountered when running full migration (main.py) and incremental migration (incremental_migrate.py), with diagnostic directions.
> Last Updated: 2026-05-14

| Issue | Diagnostic direction |
|-------|----------------------|
| Preflight check fails | Check whether placeholder values in config.ini have been replaced with real values; use `--skip-preflight` to bypass |
| Spark connection fails | Check the [spark_thrift] config; confirm host/port/auth are correct |
| DDL execution error | Check the error logs under logs/; confirm the Paimon Catalog is configured |
| Database not found | Use `--auto-create-db` to auto-create the database |
| Table already exists | Use `--force` to force DROP + CREATE (**requires user confirmation before running**) |
| rclone sync fails | Check the rclone logs; confirm HDFS and OSS connectivity |
| INSERT row count mismatch | Use `--verify` to enable row-count checking; verify source data completeness |
| TextFile INSERT error | Confirm Spark version >= 3.5.2; lower versions do not support text format-table |
| TIMESTAMP type conflict | Already handled by setting `spark.sql.timestampType=TIMESTAMP_LTZ` |
| table_manifest.csv missing | Run Step 1 first, or check the --output-dir path |
| pyhive install fails | `pip install pyhive[hive]`; confirm thrift/sasl dependencies |
| DLS data unreachable by rclone | OSS-HDFS (DLS) and plain OSS are different storage layers; use `--direct-read` mode |
| EMR Spark Gateway 401 | Check auth settings; EMR Gateway usually uses `auth=NONE`, `scheme=https`, `port=443` |
| AK/SK leak risk | Never commit config.ini to version control; inject credentials via environment variables |

## Diagnostic Tips

1. **Check logs first**: stored per-step under `output/YYYYMMDDHHMMSS/logs/`.
2. **Start from the reports**: each step's `*_result.csv` records per-table success/failure status and an error summary.
3. **Rehearse with dry-run**: `--dry-run` does not execute and quickly validates config and filter results.
4. **Resumable runs**: after a failure, resume from any step with `--start-step N` to avoid redundant work.
5. **Credential security**: if AK/SK appear in failure messages, revoke and rotate them immediately.
