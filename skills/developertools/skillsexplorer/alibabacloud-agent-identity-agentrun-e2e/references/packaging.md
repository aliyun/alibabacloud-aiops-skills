# Packaging: Cross-Platform Dependency Vendoring (Field-Verified)

The AgentRun runtime is linux/amd64, Python 3.12. Building the deployment zip
on macOS requires vendoring Linux wheels. A naive one-liner fails in four
different ways; this document explains the verified pipeline (implemented by
`scripts/03_build.sh`) and why each part exists.

## The Verified Pipeline

```bash
pip install -r requirements.txt -t . \
  --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 \
  --platform manylinux_2_28_x86_64 \
  --python-version 3.12 --only-binary=:all: \
  --find-links "$WHEELS" -c "$CONSTRAINTS"
```

## Why Each Part Exists (all four failures were hit in the field)

### 1. Multi platform tags (not just manylinux2014)

Modern wheels (tiktoken, etc.) are tagged `manylinux_2_17` / `manylinux_2_28`,
NOT `manylinux2014`. With a single `--platform manylinux2014_x86_64`, pip
reports "no matching distribution" for them and the resolver fails.

**Rule:** always pass all three tags.

### 2. Constraints file (resolver explosion)

Several sample requirements are unpinned (`fastapi`, `starlette`, `uvicorn`,
...). With `--only-binary` + platform tags the resolver's search space
explodes and pip dies with `ResolutionImpossible: resolution too deep`.

**Fix:** pin the known-good set (the constraint list embedded in
`03_build.sh`, captured from a working build). Also pin the two SDKs in
`requirements.txt` itself (`agentrun-sdk[...]==0.0.52`,
`agent-identity-python-sdk==0.1.5`) — both had breaking changes across
versions.

### 3. Local wheels for sdist-only dependencies

`--only-binary=:all:` refuses sdist-only packages. Verified offenders in the
sample's tree:

| Package | Why it gets pulled | Wheel strategy |
|---|---|---|
| `utils` | agent-identity-python-sdk dep | pure Python — `pip wheel` locally works |
| `oss2`, `alibabacloud-tea*`, `alibabacloud-credentials*`, `darabonba-core`, `aliyun-python-sdk-core` | transitive deps | pure Python — `pip wheel` locally works |
| `crcmod` | agentrun-sdk dep | **C extension, PyPI ships sdist only** — see below |

`03_build.sh` builds the pure-Python ones into a temp `--find-links` dir.

### 4. crcmod (the hard one)

crcmod needs a **Linux** compiled `.so`; building it on macOS produces a
macOS wheel — wrong platform. Field-verified fallback: take the compiled
`crcmod/` + `crcmod-1.7.dist-info/` directories from any prior Linux build
(e.g. an earlier deployment zip), zip them as
`crcmod-1.7-cp312-cp312-manylinux2014_x86_64.whl`, and drop the file into the
`--find-links` directory. A wheel is just a zip with the package + dist-info
at the root, so the repack is byte-faithful.

If no prior build exists, alternatives: build once on any Linux box
(`pip wheel crcmod==1.7`) or via `cibuildwheel`, then cache the wheel.

## Result Size

Expect ~590 MB unpacked / ~130 MB zipped (the langchain ecosystem pulled by
`agentrun-sdk[langchain]` dominates). The console accepts this size.

## Post-Build Checklist

- `py_compile main.py` and every tool `.py` (syntax sanity)
- zip with `-x "*__pycache__*"`
- Confirm the sample's own files (README, tool files) survived the vendoring
  (pip warns "Target directory README.md already exists" — harmless, pip
  does not overwrite existing files)
