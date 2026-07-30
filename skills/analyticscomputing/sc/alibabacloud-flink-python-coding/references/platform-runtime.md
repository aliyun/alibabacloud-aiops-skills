# Alibaba Cloud VVR Deployment Runtime

Use this reference after implementation and local validation to map upload-ready artifacts and parameters to the VVR console. Operational changes to a workspace or deployment require a separate user request.

## Inject credentials

When a job uses a credential:

1. Create a variable with the user-approved name under **Security > Variables**.
2. Put a reference in **Entry Point Main Arguments**, using the form `--<argument-name> ${secret_values.<VARIABLE_NAME>}`.
3. Parse `--<argument-name>` as a normal entry-point argument in Python.
4. Document these setup steps in the project README without recording the credential value.

The `${secret_values.<VARIABLE_NAME>}` expression is valid only in **Entry Point Main Arguments**. Source, committed arguments, examples, logs, and README files contain only the argument and variable names.

## Map artifacts to console fields

| Artifact | Console field | Runtime contract |
|---|---|---|
| Single `.py` or modular code ZIP | Python File Path | A code ZIP also requires Entry Module |
| `deps.zip` or third-party wheel | Python Libraries | Added to the Python worker `PYTHONPATH` |
| Custom environment or data archive | Python Archives | Extracted in the Python worker working directory |
| Job file, data file, configuration, or connector JAR | Additional Dependency Files | Available under `/flink/usrlib` |

Use one matching field per artifact. A Session-cluster target is development-only and does not support Additional Dependency Files, monitoring alerts, or automatic tuning.

## Document deployment parameters

For each applicable field, record the confirmed value, its evidence, or an explicit unresolved marker:

| Console field | Required record |
|---|---|
| Deployment mode | Stream or batch; stream is recommended |
| Deployment name | Confirmed job name |
| Engine version | Exact supported VVR version |
| Python File Path | Uploaded `.py` or code `.zip` |
| Entry Module | Module at the code ZIP root; intentionally empty for a single `.py` |
| Entry Point Main Arguments | Confirmed arguments and secret references |
| Python Libraries | Third-party wheels or `deps.zip` |
| Python Archives | Custom environment or data archives |
| Additional Dependency Files | Job files, data files, configuration, or connector JARs |

For Python 3.10 or 3.11, record the confirmed `python.executable` and `python.client.executable` settings. For attached JARs, record the exact `pipeline.classpaths` value.

## Preserve runtime contracts

Write these mappings into the deployment documentation selected by [project-layout.md](project-layout.md). Preserve source and sink keys, startup positions, event-time semantics, changelog mode, partitioning, and delivery expectations from the resolved target contract. Keep local evidence separate from checks that require VVR.

## Completion criterion

Complete runtime mapping when every deployment field is confirmed or explicitly unresolved, every credential has a variable and argument path, every artifact maps to exactly one console field, and the documentation matches the selected project layout.
