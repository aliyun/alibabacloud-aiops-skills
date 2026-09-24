# Debug

Diagnose a VVR PyFlink problem from its error, relevant code, and runtime context.

## Establish context

Confirm VVR and Python from the job or user, then locate or fetch the matching [API source](../product-contract.md#obtain-api-source). Obtain the relevant traceback/log section and code or deployment configuration needed to locate the failure.

## Follow the failing layer

Use the selected package's source/docstrings and [product documentation](../official-docs.md) to interpret the error:

| Evidence | Useful VVR-specific checks |
|---|---|
| Missing symbol, unexpected argument, or type mismatch | Package/runtime version alignment, target API signature, and input/output types |
| Connector discovery or source/sink failure | Connector support and options for that VVR version; built-in loading versus custom JAR |
| Python import, native library, or file-path failure | [Dependency resolution](resolve-dependencies.md), target interpreter/ABI, upload field, and worker path |
| AI or multimodal failure | Provider/model configuration, operator input representation, target dependencies, and Flink AI Service setup |
| Gateway or runtime failure during local execution | The API-only package does not provide a supported local VVR runtime |

Python UDF logging is available in TaskManager logs; the [Python job guide](../official-docs.md) explains the platform context. Reproduce pure-Python helper failures locally when possible. Planning, connector, and service failures need VVR evidence.

## Resolve

Explain the supported cause, or the remaining hypothesis and the specific evidence needed to distinguish it. If a fix is requested, apply [modify](modify-existing-job.md) and its affected dependency/artifact updates.

Report what was checked locally and what still requires VVR. An unexecuted cloud fix remains a proposed fix, not a verified resolution.
