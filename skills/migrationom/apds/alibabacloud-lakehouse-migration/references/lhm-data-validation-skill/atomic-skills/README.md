# Inner Atomic Skills

This directory contains the inner atomic skills split by responsibility. Each one can be invoked directly by an external workflow, bypassing the interaction layer of the outer skill.

## Directory conventions

```
atomic-skills/<skill-name>/
├── SKILL.md              # Atomic skill definition (Steps / Pitfalls / Verification)
└── scripts/
    └── run.py            # Standalone executable entry script
```

## Implementation conventions

1. **Reuse the outer `scripts/common.py`**:
   - At the top of `run.py`, add the `../../../scripts` directory to the path via `sys.path.insert`, then `from common import ...`.
   - Avoid copying shared functions to reduce maintenance cost.

2. **Use `argparse` for command-line arguments**:
   - All required parameters are passed via the command line; the script must never prompt the user interactively.
   - Output is uniformly JSON, so external systems can parse it easily.

3. **Runtime environment**:
   - Network layer: aliyun CLI + aliyun-cli-lhm plugin; the only Python dependency is `pyyaml` (the request models are provided by the local `scripts/lhm_models.py`; no LHM SDK needs to be installed)
   - Credentials: resolved through the Alibaba Cloud default credential chain (environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, RAM Role, or `~/.alibabacloud/credentials`); the scripts never accept AK/SK as command-line arguments

4. **Usage example**:

```bash
python atomic-skills/lhm-count-check/scripts/run.py \
  --task-name "Per-table count check" \
  --src-ds-id ds-src-001 --src-ds-name "source MySQL" --src-ds-type MySQL \
  --dst-ds-id ds-dst-001 --dst-ds-name "target Hive" --dst-ds-type Hive \
  --tables-json '["src_db.orders","dst_db.orders","dt=20240305","dt=20240305"]' \
  --threshold 0.0
```

## Atomic skill inventory

| Skill | Responsibility | Corresponding outer common.py function |
|-------|------|------------------------|
| `lhm-common` | **Shared foundation**: configuration management, pre-flight checks, guided setup, client construction | `load_config()` / `save_config()` / `check_resource_group_status()` / `check_agent_status()` / `build_client()` |
| `lhm-count-check` | Create and trigger a per-table count check | `run_count_check()` |
| `lhm-metric-check` | Create and trigger a per-table metric check | `run_metric_check()` |
| `lhm-batch-check` | Create and trigger a batch-mode check | `run_batch_check()` |
| `lhm-poll-status` | Query/poll the execution status | `poll_exec_status()` |
| `lhm-report-summary` | Get the batch overview | `summarize_batch()` + `format_batch_summary()` |
| `lhm-report-download` | Download the validation report | `download_report()` |
| `lhm-report-diagnose` | Diagnose the failure causes | `diagnose_failed()` + `format_diagnosis_report()` |
| `lhm-rerun-failed` | Rerun the failed tasks | `rerun_failed()` |
| `lhm-template-manage` | Template CRUD (list/detail/create/update/delete) | `list_templates()` / `get_template_detail()` / `create_template()` / `update_template()` / `delete_templates()` |

### Migrated

| Original skill | Migrated to |
|----------|--------|
| `lhm-client-builder` | `lhm-common` → `client` subcommand |
| `lhm-preflight-check` | `lhm-common` → `check` + `config` subcommands |
