# migration-lhm-migrate-hive-to-paimon Agent Execution Rules

> Extracted from SKILL.md. Defines the agent's interaction and confirmation policy when running the migration flow.
> Last Updated: 2026-05-14

## Direct-Read Mode Detection

When the user's source data is on OSS-HDFS (DLS), the agent should proactively suggest `--direct-read` mode. Detection criteria:

- The source HDFS location contains `oss-dls.aliyuncs.com` or `cn-*.oss-dls.aliyuncs.com`.
- The user explicitly states the source is DLS/OSS-HDFS.
- The user says "no rclone needed" or "skip the data copy".

## rclone Parameter Confirmation

Before running rclone-related steps (full-migration Step 4 or incremental Phase 2, and `--direct-read` is not used), the agent must confirm the following parameters with the user:

| Parameter | CLI flag | Must confirm | Notes |
|-----------|----------|--------------|-------|
| HDFS NameNode address | `--src-namenode` | Yes | host:port format |
| HDFS username | `--src-username` | No | default hadoop |
| OSS/S3 provider | `--tgt-provider` | No | default Alibaba |
| OSS endpoint | `--tgt-endpoint` | Yes | e.g. oss-cn-hangzhou-internal.aliyuncs.com |
| Access Key ID | `--tgt-ak` | Yes | |
| Secret Access Key | `--tgt-sk` | Yes | |
| Target bucket | `--tgt-bucket` | Yes | |
| Bandwidth limit | `--bwlimit` | No | e.g. 50M, 08:00,off 23:00,30M |
| Parallel transfers | `--transfers` | No | default 64 |
| Parallel checkers | `--checkers` | No | default 64 |
| Max parallel tables | `--max-parallel` | No | default 4 |

### Confirmation Rules

1. If the corresponding value in config.ini is a placeholder (starts with `$` or contains `YOUR_`), the agent must ask the user for the real value.
2. If config.ini has a real value, the agent shows the current value and asks whether it needs changing.
3. Sensitive info (AK/SK) is shown with only the last 4 characters (e.g. `****ABCD`).
4. After the user confirms, pass changed parameters to the script via the corresponding CLI flags.
5. Parameters the user did not change need no CLI flag (the config.ini value is used).

### Write-Operation Confirmation (PreToolUse-equivalent mechanism)

Because this skill drives write operations directly via the CLI, the agent must explicitly confirm with the user at these points:

| Operation | Trigger point | Confirmation focus |
|-----------|---------------|--------------------|
| `CREATE TABLE` (incl. `--auto-create-db`) | Step 3 / incremental Phase 1 | List the number of DBs/tables to create and the first batch of names |
| `DROP TABLE` (`--force` mode) | Step 3 with `--force` | Must list each table to drop and wait for the user to type `yes` |
| `INSERT OVERWRITE` | Step 5 / incremental Phase 3 | Warn that this **overwrites** all data in the target table |
| `rclone copy` | Step 4 / incremental Phase 2 | Confirm source/target paths and bandwidth limit |

Preview any write operation with `--dry-run` before running it.

### Example Interaction

```
Agent: Before running the rclone data sync, please confirm the following parameters:

Current config:
  HDFS NameNode:   10.0.0.1:8020
  OSS endpoint:    oss-cn-hangzhou-internal.aliyuncs.com
  Access Key:      ****WXYZ
  Secret Key:      ****ABCD
  Target bucket:   my-data-bucket
  Bandwidth limit: 08:00,off 23:00,30M
  Parallel transfers: 64
  Parallel checkers:  64
  Max parallel tables: 4

Do you need to change anything? If so, tell me the specific parameter and new value.
```
