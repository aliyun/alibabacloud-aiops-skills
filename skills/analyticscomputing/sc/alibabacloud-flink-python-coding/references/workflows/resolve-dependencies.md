# Resolve Dependencies

Resolve what a job needs beyond its source: Python packages, runtime files, model assets, and connector JARs.

Use the job's VVR/Python versions and existing dependency configuration. Clarify missing target details when they affect package compatibility or runtime paths; see [version selection](../product-contract.md).

## Select the relevant dependency path

| Dependency | Reference |
|---|---|
| Imports in helpers, UDFs, row/batch callbacks, or bootstrap code | [Python dependencies](../python-dependencies.md): reuse target-preinstalled packages and build only missing direct/transitive dependencies |
| Data, models, dictionaries, configuration, certificates, or archives | [Runtime files](../runtime-files.md): consumer, upload field, and runtime path |
| Custom/non-built-in connector or Java extension | [Runtime files and JARs](../runtime-files.md), plus the specific [connector documentation](../official-docs.md) |

For Python code, account for imports reached through callbacks and helpers, not only the entry file. A standard-library-only UDF needs no third-party package artifact. Model-backed built-ins may use runtime-provided dependencies; confirm those before adding packages.

For an existing job, update the affected dependencies and mappings while preserving unrelated configuration.

Deliver the needed pins/build scripts or file mappings, plus built artifacts when the environment supports them. State missing files or blocked builds explicitly. Use [prepare](prepare-deployment.md) when the user needs the complete deployment handoff.
