# cadt-deploy-on-aliyun

Qoder Operation dispatch CLI — the executable for the `alibabacloud-cadt-deploy-on-aliyun` Skill.

> **Usage documentation** (user/Skill perspective): see the project references/ directory
> This README only covers **directory structure** and **developer entry points**.

## Directory Structure

| Path | Purpose |
|------|------|
| [`cadt_deploy_on_aliyun.py`](./cadt_deploy_on_aliyun.py) | CLI main entry (`cadt-deploy-on-aliyun = "cadt_deploy_on_aliyun:main"`, exposed by pyproject) |
| [`cadt-deploy-on-aliyun.sh`](./cadt-deploy-on-aliyun.sh) | Bootstrap script: self-check venv → pip install → symlink → exec |
| [`pyproject.toml`](./pyproject.toml) | Package metadata; version sourced from `../../VERSION` |
| `lib/` | Internal modules (attrs / envelope / errors / hooks / identity / manifest / poller / runner / validator) |
| `../../ops/` | Operation contract definitions (`*.json` + `_manifest.json`); located at project root |
| `hooks/` | Op pre-/post- hooks (10 total) |
| `tests/` | pytest suite (`tests/test_smoke.py` / `test_hooks.py`) |

## Parameter Format

All `-run` operations accept parameters as a **single JSON object** string or `@file` reference:

```bash
cadt-deploy-on-aliyun -run <Op> '{"key":"value"}'
cadt-deploy-on-aliyun -run <Op> @input.json
```

Do NOT use `--key value` flag style for operation inputs — only operation-level flags (`--timeout`, `--command-file`) are supported. The `-d` output describes JSON Schema properties, not CLI flags.

## Developer Entry Points

```bash
# Local development install (editable)
pip install -e .

# Run tests
pytest

# Execute directly via bootstrap (auto-creates venv on first run)
bash cadt-deploy-on-aliyun.sh -version
```

## Op Contracts

Each `ops/*.json` (at project root) describes the input/output parameters and async semantics of a Qoder Operation. To add a new Op: place it in `ops/` + register in `_manifest.json`. See [`../../references/cli/knowledge/op-naming-rules.md`](../../references/cli/knowledge/op-naming-rules.md) for details.

## License

Apache-2.0
