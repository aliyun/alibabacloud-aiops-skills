# Upload-Ready Deployment Artifacts

Use this reference after implementation and local code validation. Produce artifacts in the layout selected by [project-layout.md](project-layout.md); an existing project keeps its established layout.

## Select the artifact set

| Condition | Required project output |
|---|---|
| Single-file job | Source `.py` only |
| Modular job | All imported project modules, `scripts/package_code.sh`, and the code ZIP when packaging succeeds |
| Non-pre-installed Python package | Pinned `requirements.txt`, `scripts/build_dependencies.sh`, and `deps.zip` when the build succeeds |
| Runtime file or connector JAR | The file plus its documented upload field and target path |

Retain only artifacts selected by this table. Record a not-applicable or blocked reason for every conditional artifact the implementation identified but did not produce.

## Package modular code

Generate `scripts/package_code.sh` directly in the target project from this contract. The generated script must:

- accept source root, output ZIP, and Entry Module as arguments;
- package deployable project code while preserving import paths at the ZIP root;
- exclude environments, caches, runtime dependencies, secrets, tests not used at runtime, and generated artifacts;
- confirm that the Entry Module resolves to a module or package at the ZIP root;
- call the system `zip` utility, avoid privilege escalation, and refuse an existing output path instead of overwriting it.

Run the script when the local environment supports it. Include the code ZIP only after the script exits successfully and its integrity and root layout are verified; otherwise retain the script and record the blocker.

## Package third-party dependencies

Apply [python-dependencies.md](python-dependencies.md) whenever a reachable import is not pre-installed in the target VVR runtime. That reference is the single source for `requirements.txt`, `scripts/build_dependencies.sh`, compatibility, Docker image, and `deps.zip` requirements.

## Write deployment documentation

For a new project, adapt `assets/handoff/README.md.template` into the project-root `README.md`. For an existing project, merge the applicable sections into its established deployment documentation, or use the root `README.md` when none exists.

The final documentation must contain:

- the actual directory tree and purpose of each file;
- exact commands for building and inspecting applicable ZIPs;
- the artifact-to-console-field mapping from [platform-runtime.md](platform-runtime.md);
- every applicable deployment field with a confirmed value or explicit unresolved marker;
- confirmed source and sink contracts plus each labeled example awaiting replacement;
- each Table or API fallback with its reason and location;
- runtime settings, built-in connector/format/catalog identifiers, and JAR classpaths;
- completed local checks, remaining VVR checks, known limitations, and rollback owner;
- omitted conditional artifacts with their not-applicable or blocked reasons;
- the official Python development, dependency, and deployment URLs from [official-docs.md](official-docs.md).

Replace every template placeholder and keep credential values out of project artifacts. Claims about a generated ZIP must cite the successful build and ZIP checks.

When code uses or mentions DataFrame LLM functions such as `llm.predict` or `llm.ai_*`, guide the user to consider Flink AI Service for zero-configuration managed-model calls and include `https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service`.

## Completion criterion

Complete artifact preparation when every selected artifact exists or has a recorded blocker; each generated script is syntax-checked; each built ZIP passes integrity and layout checks; the deployment documentation matches the filesystem and [platform-runtime.md](platform-runtime.md); and no raw placeholder or credential value remains.
