---
name: lhm-batch-check
version: 1.0.0
description: Creates and triggers an LHM batch-mode validation task, corresponding to run_batch_check() in the outer common.py.
---

# lhm-batch-check

Creates and triggers an LHM (Lakehouse Migration Center) batch-mode validation task. Automatically completes: task creation (batch mode) → matching rule configuration → batch saving → immediate execution.

## Steps

1. Confirm that the aliyun CLI + aliyun-cli-lhm plugin and `pyyaml` are installed (see "Environment Preparation" in the root README).
2. Determine `--check-type`: `0` for count check, `1` for metric check.
3. Construct the `--match-rule` batch matching rule string (see `batch_match_rules.md` for the rule format).
4. For metric checks, specify the template via `--check-template-id`; it is not needed for count checks.
5. Invoke this script, passing all required parameters via the command line.
   Data sources support alias mode: use `--src-alias` and `--dst-alias` to resolve from data_validation_config.yaml, in which case `--src-ds-id/name/type` do not need to be passed.
6. The script calls `run_batch_check()` in the outer `scripts/common.py` to create the task and trigger execution.
7. On success, stdout outputs JSON: `{"ok": true, "task_id": ..., "batch_id": ...}`.

## Pitfalls

- `--threshold` defaults to `None`, meaning it is not passed to the SDK; passing `none` also means `None`.
- Passing `0.0` for metric checks causes all numeric metrics to be falsely judged PASSED; only pass it when explicitly required.
- `--check-template-id` only takes effect when `--check-type=1`; it is not needed for count checks.
- MaxCompute partitioned tables usually require setting `--source-global-params` / `--target-global-params` to `odps.sql.allow.fullscan=true`; in batch mode the source and target partition conditions must also be specified explicitly in `--match-rule`, e.g., `dt='2026-01-01';dt='2026-01-01'`, otherwise a full-scan error or inconsistent results may occur.
- The table-name field of `--match-rule` is parsed as a regex: `lhm_*` matches `lhm` followed by zero or more underscores; to match all tables starting with `lhm_`, write `lhm_.*`; to match all tables, write `*`.
- Credential precedence: command-line arguments > data_validation_config.yaml (~/.lhm/data_validation_config.yaml) > environment variables.

## Verification

- After running the script, check whether the stdout output is `{"ok": true, "task_id": <int>, "batch_id": <int>}`.
- Use `lhm-poll-status` or the LHM console to check the execution status of the corresponding task_id / batch_id.

## Input/Output Examples

Input (command line, batch count check):

```bash
python atomic-skills/lhm-batch-check/scripts/run.py \
  --task-name "批量数据量校验" \
  --src-ds-id ds-src-001 \
  --src-ds-name "源端MySQL" \
  --src-ds-type MySQL \
  --dst-ds-id ds-dst-001 \
  --dst-ds-name "目标端Hive" \
  --dst-ds-type Hive \
  --check-type 0 \
  --match-rule "src_db|dst_db|*" \
  --region hangzhou
```

Input (command line, batch metric check):

```bash
python atomic-skills/lhm-batch-check/scripts/run.py \
  --task-name "批量指标校验" \
  --src-ds-id ds-src-001 \
  --src-ds-name "源端MySQL" \
  --src-ds-type MySQL \
  --dst-ds-id ds-dst-001 \
  --dst-ds-name "目标端Hive" \
  --dst-ds-type Hive \
  --check-type 1 \
  --match-rule "src_db|dst_db|*" \
  --check-template-id 1001 \
  --region hangzhou
```

Output (stdout):

```json
{"ok": true, "task_id": 12345, "batch_id": 67890}
```

Using alias mode (data sources resolved from data_validation_config.yaml):

```bash
python atomic-skills/lhm-batch-check/scripts/run.py \
  --task-name "批量数据量校验" \
  --src-alias mc_source \
  --dst-alias sr_target \
  --check-type 0 \
  --match-rule "src_db|dst_db|*" \
  --region hangzhou
```
