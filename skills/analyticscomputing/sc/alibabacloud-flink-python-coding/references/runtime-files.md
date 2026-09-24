# Runtime Files and Connector JARs

Use for data, model weights, dictionaries, configuration, certificates, archives, and Java dependencies. Consult the [dependency guide](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/use-python-dependencies) for target behavior.

## Map files to their consumers

For each needed resource, identify its source, consuming code and format, deployment artifact, upload field, and runtime path. Clarify unknown content/format when it affects implementation; an environment-specific path can remain a documented parameter.

| Resource | Deployment route |
|---|---|
| Files requiring extraction with stable relative paths | Python Archives; resolve paths relative to the extracted worker directory |
| Independent model, dictionary, configuration, certificate, or data file | Additional Dependency Files; refer to `/flink/usrlib/<filename>` |
| Custom/non-built-in connector or Java extension JAR | Additional Dependency Files; set the documented `pipeline.classpaths` when required |

DataFrame methods load registered built-in connector artifacts automatically. For Table/DataStream code, retain or configure the target's documented built-in connector settings. A custom connector's JAR must match the target Flink/JDK and, where applicable, Scala versions.

Keep workstation paths and VVR paths distinct. Preserve user-owned resource locations and existing mappings; package or update only what the job requires. Identify unavailable resources explicitly.

The delivered mapping should connect each resource's actual artifact to the path used by the code. [Prepare](workflows/prepare-deployment.md) includes it in the deployment README.
