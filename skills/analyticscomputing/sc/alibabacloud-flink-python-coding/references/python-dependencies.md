# Python Dependencies

Use for third-party imports and Python callbacks. The [Python job guide](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-a-pyflink-job) lists pre-installed packages; the [dependency guide](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/use-python-dependencies) describes deployment and compatible builds.

## Determine what to package

Follow imports through the entry point, helpers, UDFs, row/batch callbacks, and bootstrap code. Match import names to distributions and the APIs actually used. Classify both direct and transitive dependencies against the selected runtime before writing requirements or downloading packages.

- **Runtime-provided:** with VVR's built-in Python environment, reuse pre-installed packages whose versions satisfy the required APIs and dependency constraints. Record the reused packages, versions, and evidence in the README; exclude them from deployment `requirements.txt` and the bundle.
- **Job-provided:** pin only packages absent from the runtime or requiring a verified override. Prefer versions compatible with the runtime-provided packages; explain any necessary override and check compatibility with the affected runtime stack.
- **Local development:** keep inspection and test tools separate from deployment requirements.

VVR provides `pyflink`. Deployment requirements exclude `ververica-flink`, `pyflink`, `flink`, and `apache-flink`. A local package installation does not establish what the VVR worker has.

The pre-installed list includes AI/multimodal packages such as `torch`, `torchvision`, `transformers`, and `Pillow`, as well as `numpy`, `pandas`, and `pyarrow`. Check the target VVR/Python list and operator requirements before adding an AI stack. If all required packages are supplied compatibly by VVR, omit `requirements.txt`, the dependency build script, `deps.zip`, and its Python Libraries entry.

## Exclude runtime packages before downloading

A manylinux build environment does not represent VVR's installed packages. Removing `torch` from top-level requirements alone is insufficient: pip can still download it as another package's dependency.

Inspect package dependency metadata, including the selected extras and target Python/platform markers. Put the complete set of **job-provided direct and transitive dependencies** in pinned `requirements.txt`; each required dependency must be satisfied by either this list or a verified runtime-provided version. Use package metadata to make this split before fetching large wheels.

Install that complete list with [`pip install --no-deps`](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-no-deps). Apply the same exclusion to any separate download step. `--no-deps` is safe here because missing transitive dependencies have already been listed explicitly. Constraints only restrict versions; downloading everything and removing runtime packages during ZIP creation still wastes the download.

For example, a library depending on VVR's compatible `torch` needs only that library and its other missing dependencies packaged. If the job uses only compatible pre-installed `torch`, `transformers`, and `Pillow`, no dependency build is needed.

## Build for the target

A native dependency must match the worker's CPU, CPython ABI, and Linux/glibc compatibility. A macOS or Windows environment is useful for development but is not the source of deployable native libraries.

For packages requiring a dependency bundle, write pinned `requirements.txt` and a reproducible `scripts/build_dependencies.sh` (or use the project's existing build). The documented manylinux images include:

| Target CPU | Build image |
|---|---|
| x86-64 | `quay.io/pypa/manylinux_2_28_x86_64` |
| ARM64 | `quay.io/pypa/manylinux_2_28_aarch64` |

Confirm the target glibc compatibility and choose the matching interpreter, such as `/opt/python/cp311-cp311/bin/python` for CPython 3.11. Start with an empty staging directory. The manylinux image has no `zip` command; use Python's standard-library `zipfile` to package the staging directory's **contents** at the ZIP root. For example, inside the build container after resolving the complete job-provided requirements:

```bash
python_bin=/opt/python/cp311-cp311/bin/python
"$python_bin" -m pip install --no-deps -r requirements.txt --target __pypackages__
"$python_bin" - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path("__pypackages__")
with ZipFile("deps.zip", "w", ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(root))
PY
```

Syntax-check the build script and run it when Docker and a compatible build environment are available. Check the archive's integrity, root layout, and package list against the job-provided requirements. Record an unavailable environment or failed build as an unbuilt artifact, with the script needed to finish it.

Deploy third-party packages through **Python Libraries**. Use [runtime files](runtime-files.md) for models/configuration and [platform runtime](platform-runtime.md) for a complete custom Python environment. Keep those distinct from the Python package bundle.
