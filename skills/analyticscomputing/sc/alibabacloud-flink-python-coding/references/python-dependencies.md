# Python Dependencies

Use this reference when reachable job code imports a third-party distribution or invokes a Python callback.

## Inventory reachable dependencies

Trace imports from UDFs, UDTFs, UDAFs, `map`, `map_batches`, one-to-many callbacks, project helpers, and job bootstrap code. For each import, record:

- import name and distribution name;
- consuming function and required API;
- local-only, VVR-only, or shared use;
- provider and exact version evidence.

## Check pre-installed packages

Use the **Pre-installed software packages** section of the [Python job development documentation](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-a-pyflink-job) for the exact target VVR and Python version.

Treat a dependency as pre-installed only when the documented distribution version provides every API the reachable code uses. Local installation and `ververica-flink` prove neither target availability nor target package version.

## Pin remaining distributions

Resolve each non-pre-installed distribution from an existing lockfile, dependency file, installed metadata, or primary package documentation. Preserve unrelated dependency entries and comments, and use exact pins in `requirements.txt`:

```text
distribution-name==confirmed.version
```

For every pinned distribution, record target CPU architecture, Python ABI, and documented glibc baseline. Pure-Python packages still belong in the dependency artifact unless the target documentation lists them as pre-installed.

## Generate the dependency build script

Generate `scripts/build_dependencies.sh` directly in the target project from this contract. The script must:

- require the exact Python version resolved through [official-docs.md](official-docs.md);
- accept only an x86-64 target with glibc 2.28 or later for the `quay.io/pypa/manylinux_2_28_x86_64` Docker image;
- map Python 3.9, 3.10, and 3.11 to their matching `/opt/python/cp*/bin` interpreters and reject other versions;
- install into `__pypackages__` and package its contents, without the wrapper directory, as `deps.zip`;
- call the system `zip` utility, avoid privilege escalation, and refuse an existing output path instead of overwriting it.

Syntax-check the generated script. Run it when Docker is available, the confirmed target is compatible, and local execution is safe. Upload a successfully built and verified `deps.zip` through **Python Libraries**. Record an unexecuted-build note when those run conditions are not met.

## Completion criterion

Complete dependency resolution when every reachable third-party import has a provider and exact version; local and VVR consumers are classified; CPU, ABI, and glibc compatibility are recorded; and the artifact set contains exact pins, a syntax-checked build script, and either a verified `deps.zip` or an unexecuted-build note.
