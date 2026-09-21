---
name: lhm-engine-bind
description: Queries available validation engines and binds an engine to a validation task. Tasks created via API/CLI carry no validation engine; types such as MaxCompute/Hive without an engine fail at runtime with [RuntimeException]No default project specified. Use this skill to query candidates, bind engines, or read back to confirm.
version: 1.0.0
---

# lhm-engine-bind — Validation Engine Query and Binding

## Positioning

`add-data-check-task` (POP/CLI) **has no engine parameter**; for tasks created via the API,
`srcEngineId`/`dstEngineId` are always empty. The backend then falls back to "using the data source itself
as the engine"; in MaxCompute scenarios a `[RuntimeException]No default project specified.` is thrown at
the worker stage, and it is only visible in the job/step's `err_message`.

`update-data-check-task` supports engine parameters; this skill uses it to fill the gap.

## Steps

### 1. Query Available Engines

```bash
python scripts/run.py list --ds-type MaxCompute
python scripts/run.py list --ds-type MaxCompute --check-type 1   # filter by the engine types allowed by the template
```

### 2. Bind Engines to an Existing Task

```bash
python scripts/run.py bind --task-id 10001 \
  --src-engine-id 456 --src-engine-name mc_engine --src-engine-type MaxCompute \
  --dst-engine-id 456 --dst-engine-name mc_engine --dst-engine-type MaxCompute
```

After binding, `exec-data-check-save-task` **must be rerun** to generate a new batch before executing:
both the batch and the table configuration copy the engine fields from the task record as it stood at that time.

### 3. Read Back to Confirm

```bash
python scripts/run.py show --task-id 10001
```

The binding is successful only when `src_engine_id` / `dst_engine_id` are non-empty.

## Pitfalls

- **Ordering**: for new tasks, the engine must be bound before `add-data-check-config` (the `run_*` functions
  already do this internally); when fixing an existing task, save again after binding.
- **`list` uses the 2022-11-15 version API** (`list-meta-data-component-engine`);
  `aliyun_cli` has the version preset built in, no manual specification needed.
- **When the engine id equals the data source id**, binding does not change execution behavior; if
  `No default project specified.` is still reported, the data source itself lacks a default project —
  it must be completed in the console; binding an engine is ineffective.
- **Outdated plugin**: if `update-data-check-task` does not recognize the engine flags, `aliyun_cli`
  explicitly reports `CLI_PARAM_UNSUPPORTED` instead of silently dropping the parameters; upgrade the plugin in that case.

## Verification

```bash
python scripts/run.py list --ds-type MaxCompute     # candidates can be listed
python scripts/run.py show --task-id <id>           # engine fields are non-empty
```
