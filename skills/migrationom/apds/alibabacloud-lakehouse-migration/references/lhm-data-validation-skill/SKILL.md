---
name: lhm-data-validation-skill
version: 0.1.1
description: Validates data consistency across heterogeneous data sources based on the Alibaba Cloud Lakehouse Migration Center (LHM) product.
---

# LHM Data Validation Service (aliyun CLI)

Drives the entire data validation workflow through the aliyun CLI (`aliyun-cli-lhm` plugin). This Skill is **execution-first**: once the user specifies the data sources, tables, and check type, match the function directly and trigger execution; load reference documents on demand only for complex diagnosis and design scenarios.

> **Network layer**: all API calls are uniformly wrapped by `scripts/aliyun_cli.py` as `aliyun lhm <command>` subprocess invocations, keeping the same call shape as the original Python SDK (`client.xxx(request)` → `resp.body.data`). The request models are provided by the lightweight local module `scripts/lhm_models.py` (the former `alibabacloud_lhm20250116` SDK is deprecated and no longer installed). The aliyun CLI and the aliyun-cli-lhm plugin must be installed before running (see README).
>
> ⚠️ **Sandbox environment compatibility**: in the evaluation system's sandbox environment, the `aliyun` CLI may be wrapped as a proxy, and actual calls require using `aliyun_real`. The `find_aliyun_binary()` function in `scripts/aliyun_cli.py` already includes this detection logic (it prefers `aliyun_real`). But if you invoke the `aliyun` command directly through Bash, detect it first:
> ```bash
> if command -v aliyun_real >/dev/null 2>&1; then ALIYUN_CMD="aliyun_real"; else ALIYUN_CMD="aliyun"; fi
> ${ALIYUN_CMD} lhm <command> ...
> ```

> ⛔ **Plugin prerequisite — hard stop (mirrors the LHM dispatcher's Step 2.1 Hard Stop Gate)**: every atomic skill in this package reaches the service through `aliyun lhm <command>`, so the `aliyun-cli-lhm` plugin (>= 0.1.1, i.e. `~/.aliyun/plugins/aliyun-cli-lhm/manifest.json` must exist) is a hard prerequisite for *all* checks — count / metric / batch / template / report. Verify it before anything else; when this Skill is entered directly rather than through the dispatcher, run the dispatcher's `scripts/install_lhm_plugin.sh` and treat a non-zero exit as fatal.
>
> If the plugin is unavailable, **stop immediately**: report the environment error verbatim and terminate. Do **not** ask the user for `ds_id`, aliases, database/table names, check type, or sampling rate; do **not** run `run.py check`, any validation script, or any dependency install; and **never output a row count, consistency ratio, or pass/fail verdict that did not come from a real call**. Successfully installed local Python dependencies are never proof that the cloud path works.

## Quick Execution Path

0. **Pre-check** (on first run or after environment changes):
   ```bash
   python atomic-skills/lhm-common/scripts/run.py check --profile data-validation
   ```
   Continue only when `ready=true`; when `ready=false`, guide the user to fix things per the `fix_guide` entries in `blocking_items`. On first use, run `setup` for guided configuration.
1. **Read configuration**: credentials and data sources are read preferentially from `~/.lhm/data_validation_config.yaml`. Users may reference data sources by alias (e.g., `mc_source`, `sr_target`) without memorizing ds_ids.
2. **Build the client**: `build_client()`. Every `aliyun lhm` call carries the fixed parameters `--endpoint` / `--region`, read from the `lhm` section of `~/.lhm/credentials.json` (`lhm.endpoint` / `lhm.region_id`); an explicit `build_client(region='singapore')` overrides the region, and the environment variables (`LHM_ENDPOINT` / `REGION_ID`) then built-in defaults are fallbacks. Credentials are resolved by the aliyun CLI default credential chain — never read from any config file.
3. **Prepare data sources**: `src_ds = (ds_id, ds_name, ds_type)` / `dst_ds = (ds_id, ds_name, ds_type)`, where `ds_id` is the only SDK input. When aliases are used, resolve them from the `data_sources` section of data_validation_config.yaml.
4. **Invoke by intent** (prefer the wrapper functions in `scripts/common.py`):
   - **Template selection** (before metric checks): use 1001(MIX) by default. For custom rules, list available templates with `list_templates()`, or load `knowledge/patterns/template-guide.md` for guided configuration. Templates can also be CRUD-managed directly via `atomic-skills/lhm-template-manage`. For manual console configuration, see `knowledge/patterns/template-manual-setup.md`
   - Count check → `run_count_check()` or `run_batch_check(check_type=0)`
   - Metric check → `run_metric_check()` or `run_batch_check(check_type=1)`
   - View/download reports → `summarize_batch()` / `download_report()`
   - Rerun failures → `rerun_failed()`
   - If the raw SDK APIs are needed (scenarios not covered by the wrapper functions), search `references/api-integration.md`
5. **Poll until completion**: `poll_exec_status(client, task_id, batch_id)`, targeting `exec_status=4`.

## Core Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `region` | Center node | `hangzhou` (default), `singapore` |
| `src_ds` / `dst_ds` | Data source triple `(ds_id, ds_name, ds_type)` | `('ds-001', '源端MySQL', 'MySQL')` |
| `check_type` | Check type | `0` count / `1` metric / `2` weak content |
| `task_mode` | Creation mode | `0` per-table / `1` batch |
| `match_rule` | Batch matching rule | `src_db|dst_db|*`; full syntax in `references/batch_match_rules.md` |
| `check_template_id` | Check template ID. Built-in: 1001(MIX)/1002(NUM)/1003(LEN); custom: a user-provided UUID | `1001` (default) |

## User Intent Quick Reference

| User intent | Corresponding capability |
|-------------|--------------------------|
| Run a count check | `run_count_check()` / `run_batch_check(check_type=0)` |
| Run a metric check | `run_metric_check()` / `run_batch_check(check_type=1)` |
| View results / download reports | `summarize_batch()` / `download_report()` |
| Diagnose the root cause of differences | `diagnose_failed()`; load `knowledge/patterns/difference-patterns.md` on demand |
| Recommend a validation strategy | Load `knowledge/patterns/validation-strategies.md` on demand |
| Rerun failed tables | `rerun_failed()` |
| Custom check rules / template configuration | Load `knowledge/patterns/template-guide.md` for selection; create with `create_template()` or guide the user to create it in the console |
| Manage templates (CRUD) | `list_templates()` / `get_template_detail()` / `create_template()` / `update_template()` / `delete_templates()`, or CLI: `atomic-skills/lhm-template-manage/scripts/run.py --action <op>` |

## Key Pitfalls

- **Passing `threshold=0.0` for metric checks**: `0.0` means consistency ≥ 0% passes, causing all numeric metrics to be falsely judged PASSED. Pass `None` (omit it) by default.
- **Calling run / stop / rerun / download with `task_id`**: these interfaces must use `batch_id`.
- **Passing only `batch_id` to `poll_exec_status`**: both `task_id` and `batch_id` must be passed.
- **MaxCompute partitioned tables**: `source_global_params='odps.sql.allow.fullscan=true'` must be set, and `match_rule` must include partition conditions for both sides, e.g., `dt='2026-01-01';dt='2026-01-01'`.
- **Special characters in task names**: `task_name` only allows English letters, Chinese characters, and digits; otherwise `E500R103` is reported.
- **Use `metric_rules` when updating templates**: the backend `UpdateCmd.getMetricRules()` clears `metricRules`; you must use `basic_metric_rules` (dataTypeClassify=0) / `complex_metric_rules` (dataTypeClassify=1), otherwise `E501R104` is reported. Create is not subject to this restriction. `update_template()` splits them automatically internally.
- **Backend required fields on update**: the backend requires `checkType`, `dsEngineRels`, and the rules to be present (even when only renaming), otherwise `E500R100` / `E500R102` / `E501R104` is reported. When not provided, `update_template()` back-fills them automatically from the existing template, transparently to the caller.

See `docs/user-pitfalls.md` for more troubleshooting and misconceptions.

## When to Use

- The user needs to run cross-database data consistency checks via Python or write automation scripts.
- The user mentions the `alibabacloud_lhm` SDK, post-migration comparison, or whole-database/partitioned-table validation.
- The user needs to download reports, diagnose differences, or rerun failed tables.

**When NOT to use:**
- Data migration itself (table creation, data movement).
- Data source management (creating/deleting data source connections).

## More References

- Shared foundation (configuration/checks/guidance): `atomic-skills/lhm-common/SKILL.md`
- Atomic Skill CLI entry points: `atomic-skills/README.md`
- common.py functions and standalone scripts: `references/workflow-functions.md`
- Batch matching rules: `references/batch_match_rules.md`
- Complete scenario examples: `references/examples.md`
- Common misconceptions and troubleshooting: `docs/user-pitfalls.md`
- Template selection and configuration guide: `knowledge/patterns/template-guide.md`
- Manual template setup guide: `knowledge/patterns/template-manual-setup.md`
- Template API SDK specification: `references/template-sdk-api-spec.md`
