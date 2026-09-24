# VVR Versions and API Source

Use this reference to establish the target runtime and prepare API inspection.

## Version selection

User-provided versions and clear repository configuration count as confirmation.

| Scenario | VVR | Python |
|---|---|---|
| New job | If missing, propose the newest formal release from the live [Chinese release notes](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/release-notes) and confirm with the user | Confirm one of 3.9, 3.10, or 3.11 |
| Modify, review, or debug an existing job | Use its configured version; ask if missing | Use its configured version; ask if missing |
| General API inquiry | If missing, use the latest formal release and state that assumption; ask for the target when compatibility matters | Ask only when it affects the answer |
| Resolve dependencies or prepare deployment | Derive from the job; clarify missing values that affect compatibility or deployment | Match the target interpreter |

VVR below 11.8 is outside this skill's baseline; discuss upgrading before developing or repairing it. Preserve an existing supported target. Preview releases require an explicit user choice.

**Preview-to-GA availability:** features introduced in a VVR preview are included in the corresponding GA release. For example, a feature introduced in `11.8.0.preview.2` is available in GA `11.8`. A connector's "public beta" label describes its maturity, not a requirement to use a preview engine.

Use the Chinese release notes for release availability; an online API page labeled `latest` may describe a different or Preview build. When the current formal release cannot be verified, explain the uncertainty and ask for a target rather than guessing.

## Version identities

| Identity | Role |
|---|---|
| VVR release | Managed runtime and feature availability |
| Full engine version | Exact deployment selector, including its Flink/JDK lineage |
| Community Flink version | Upstream lineage, not a substitute for the VVR version |
| Python version | Interpreter and dependency ABI |
| `ververica-flink` version | Local API distribution matched to the VVR target |
| Documentation build | Version of the API evidence being read |

For example, the [DataFrame quickstart](https://help.aliyun.com/zh/flink/realtime-flink/quickstart) pairs VVR 11.8 with `ververica-flink==11.8.0`. Resolve other mappings from the product documentation and package metadata rather than mechanically constructing version strings.

## Obtain API source

For writing, modifying/reviewing, or debugging a job, reuse matching local `ververica-flink` source if available, whether installed or extracted. Otherwise download only its wheel and extract it into a versioned cache. The goal is readable `pyflink` source and docstrings; importing the package or resolving its dependencies is unnecessary.

For example, for VVR 11.8 and target Python 3.11, use an existing Python with pip to fetch the universal wheel:

```bash
python3 -m pip download --no-deps --only-binary=:all: \
  --platform any --python-version 3.11 \
  --dest .cache/vvr-api/11.8.0 "ververica-flink==11.8.0"
python3 -m zipfile -e \
  .cache/vvr-api/11.8.0/ververica_flink-11.8.0-py3-none-any.whl \
  .cache/vvr-api/11.8.0/source
```

Use the selected target's package version and downloaded filename. These [download options](https://pip.pypa.io/en/stable/cli/pip_download/) skip dependencies and source builds; the target Python need not be installed just to read source. Search the extracted `source/pyflink/` files directly to establish signatures, parameters, types, and feature scope. Keep this cache outside deployment artifacts.

For API inquiry, reuse matching local source or go directly to [online API documentation and source](official-docs.md). If a matching wheel is unavailable or downloading fails, use that online fallback for development too and state any unresolved version compatibility.

Prepare a target-compatible Python environment when needed for helper tests or dependency builds, using only their required packages. See [local checks](verification-method.md) and [Python dependencies](python-dependencies.md).

The package is API-only. DataFrame planning/execution, connector behavior, and AI/multimodal execution are verified on VVR.
