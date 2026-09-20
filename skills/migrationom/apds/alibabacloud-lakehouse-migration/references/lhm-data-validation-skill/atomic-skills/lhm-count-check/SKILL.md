---
name: lhm-count-check
version: 1.0.0
description: Creates and triggers an LHM per-table count validation task, corresponding to run_count_check() in the outer common.py.
---

# lhm-count-check

Creates and triggers an LHM (Lakehouse Migration Center) per-table count validation task. Automatically completes: task creation → per-table configuration → batch saving → immediate execution.

## Steps

1. Confirm that the aliyun CLI + aliyun-cli-lhm plugin and `pyyaml` are installed (see "Environment Preparation" in the root README).
2. Construct the `--tables-json` argument: a JSON array where each element is a list of 4 strings `[source_table, target_table, source_partition, target_partition]`; an empty string for a partition means a whole-table check.
3. Invoke this script, passing all required parameters via the command line.
   Data sources support alias mode: use `--src-alias` and `--dst-alias` to resolve from data_validation_config.yaml, in which case `--src-ds-id/name/type` do not need to be passed.
4. The script calls `run_count_check()` in the outer `scripts/common.py` to create the task and trigger execution.
5. On success, stdout outputs JSON: `{"ok": true, "task_id": ..., "batch_id": ...}`.

## Pitfalls

- `--threshold` defaults to `0.0`, meaning exact match; passing `none` means `None`, letting the system use its default value.
- When a partition field is an empty string, common.py treats it as a whole-table check (`is_full_table_count=1`).
- MaxCompute partitioned tables usually require setting `--source-global-params` / `--target-global-params` to `odps.sql.allow.fullscan=true`.
- Credential precedence: command-line arguments > data_validation_config.yaml (~/.lhm/data_validation_config.yaml) > environment variables.

## Verification

- After running the script, check whether the stdout output is `{"ok": true, "task_id": <int>, "batch_id": <int>}`.
- Use `lhm-poll-status` or the LHM console to check the execution status of the corresponding task_id / batch_id.

## Input/Output Examples

Input (command line):

```bash
python atomic-skills/lhm-count-check/scripts/run.py \
  --task-name "逐表数据量校验" \
  --src-ds-id ds-src-001 \
  --src-ds-name "源端MySQL" \
  --src-ds-type MySQL \
  --dst-ds-id ds-dst-001 \
  --dst-ds-name "目标端Hive" \
  --dst-ds-type Hive \
  --tables-json '[
    ["src_db.orders", "dst_db.orders", "dt=20240305", "dt=20240305"],
    ["src_db.users", "dst_db.users", "", ""]
  ]' \
  --threshold 0.0 \
  --region hangzhou
```

Output (stdout):

```json
{"ok": true, "task_id": 12345, "batch_id": 67890}
```

Using alias mode (data sources resolved from data_validation_config.yaml):

```bash
python atomic-skills/lhm-count-check/scripts/run.py \
  --task-name "逐表数据量校验" \
  --src-alias mc_source \
  --dst-alias sr_target \
  --tables-json '[["src_db.orders", "dst_db.orders", "", ""]]' \
  --threshold 0.0
```
