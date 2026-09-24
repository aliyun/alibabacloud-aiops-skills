# Deployment Artifacts and README

Use from [prepare deployment](workflows/prepare-deployment.md). Keep outputs in the job's [selected layout](project-layout.md).

## Select and build artifacts

| Job needs | Output |
|---|---|
| A single Python file | The source `.py` |
| Multiple project modules | Code ZIP plus a reproducible packaging command/script |
| Packages absent or incompatible in the target runtime | Pinned requirements, dependency build script, and `deps.zip` when built |
| Runtime files or custom JARs | Available resource files plus their deployment mapping |

For modular code, generate `scripts/package_code.sh` or use the existing project tooling. Preserve Python import paths at the ZIP root and ensure Entry Module resolves there. Package deployable code; keep environments, caches, secrets, generated archives, and non-runtime tests out.

Run packaging and check the ZIP's integrity and layout. Follow [Python dependencies](python-dependencies.md) for dependency builds. When a build cannot complete, retain the usable script and report the missing archive and cause.

## Write the README

For new jobs, write `README.md` in the user's language, honoring any explicit documentation-language preference. Localize the template's headings, prose, and table labels; preserve executable commands, code identifiers, file paths, configuration keys, and product/API names.

Adapt [the README template](../assets/handoff/README.md.template), or update the existing deployment documentation. Include what this job needs:

- Purpose, source/sink behavior, target VVR/Python, and any meaningful API fallback.
- Entry point, delivered files, and commands to rebuild applicable artifacts.
- Artifact-to-console-field mapping and runtime settings from [platform runtime](platform-runtime.md).
- Runtime arguments, file paths, model/service setup, and remaining environment-specific values.
- For jobs using [Flink AI Service](https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service), explain its role in the job, identify the models/tasks used, and describe required service activation/configuration based on the official documentation. A documentation link alone does not satisfy this requirement.
- Manual upload/deployment/start instructions, usable by a job-submission skill as well.
- Completed local checks, outstanding VVR checks, and any blocked build or missing resource.

Replace template markers with actual values or clearly labeled unresolved parameters. The documented files and commands should match the delivered project. A missing deployment endpoint need not prevent code delivery, but its required value must be clear to whoever submits the job.
