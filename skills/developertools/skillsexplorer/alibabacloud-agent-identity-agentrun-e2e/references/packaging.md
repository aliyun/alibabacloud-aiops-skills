# Packaging: Cross-Platform Dependency Vendoring

This workflow targets Linux x86_64 with Python 3.12. Building the deployment zip
on macOS requires vendoring Linux wheels. This document explains the pipeline (implemented by
`scripts/03_build.sh`) and why each part exists.

## The Verified Pipeline

```bash
pip install --upgrade -r requirements.txt -t python \
  --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 \
  --platform manylinux_2_28_x86_64 \
  --python-version 3.12 --only-binary=:all: \
  --find-links "$WHEELS" -c "$CONS"
```

Dependencies are installed under `python/`, separate from the sample's own files.
The deployment configuration places `/code/python` first in `PYTHONPATH`.
If the sample root contains an earlier dependency installation, use a clean
checkout and save its absolute path with `save_project_dir` before building.

## Why Each Part Exists

### 1. Multi platform tags (not just manylinux2014)

The build lists `manylinux2014_x86_64`, `manylinux_2_17_x86_64`, and
`manylinux_2_28_x86_64` to resolve the sample's Linux wheels.

Keep the platform tags aligned with the deployment environment.

### 2. Constraints file (resolver backtracking)

Several sample requirements are unpinned (`fastapi`, `starlette`, `uvicorn`,
...). With `--only-binary` and platform tags, dependency resolution can
require extensive backtracking.

**Fix:** use the constraint list embedded in `03_build.sh`, including
`agentrun-sdk==0.0.52`,
`agent-identity-python-sdk==0.1.5` and `litellm==1.95.0`. Keep these versions in
the constraints and post-build checks; do not edit the official sample files.

### 3. Local wheels for sdist-only dependencies

`--only-binary=:all:` refuses sdist-only packages. Dependencies requiring local wheels:

| Package | Why it gets pulled | Wheel strategy |
|---|---|---|
| `utils` | agent-identity-python-sdk dep | pure Python — `pip wheel` locally works |
| `oss2`, `alibabacloud-tea*`, `alibabacloud-credentials*`, `darabonba-core`, `aliyun-python-sdk-core` | transitive deps | pure Python — `pip wheel` locally works |
| `crcmod` | agentrun-sdk dep | Optional C extension; build the pure-Python wheel below |

`03_build.sh` stores these wheels under the run state directory's `wheels/`
cache and passes that directory to `--find-links`.

### 4. crcmod

A compiled crcmod extension must be compatible with Python 3.12 on Linux
x86_64. Do not repackage unverified build directories as a compatible wheel.

`03_build.sh` removes earlier cached crcmod wheels and builds the official
`crcmod==1.7` pure Python wheel. It works across platforms without changing
the sample, but CRC computation is slower than with the Linux extension.

## Result Size

Package size varies with dependencies. Check the ZIP against the current
AgentRun upload limits.

## Post-Build Checklist

- `py_compile main.py` and every tool `.py` (syntax sanity)
- zip with `-x "*__pycache__*"`
- Compare the sample's own files (README, tool files) with the original checkout
  after vendoring; a pip warning alone does not verify that they are unchanged.
