---
name: alibabacloud-flink-python-coding
description: |
  Use this skill when the user needs help with a Flink Python or PyFlink job, especially on Alibaba Cloud Realtime Compute for Apache Flink (VVR): write, modify, review, or debug PyFlink jobs; explain or select Flink Python APIs; resolve package or file dependencies for PyFlink jobs; or prepare PyFlink job deployment.
---

# Alibaba Cloud Flink Python Coding

Apply the DataFrame-first workflow below.

Unless the user explicitly requests a non-DataFrame API or SQL, the main job pipeline must start with `import pyflink.dataframe as pf`. An implementation written entirely with Table API or SQL is not a DataFrame fallback or Table bridge.

## Scenario Description

Develop version-aware Python jobs for Alibaba Cloud Realtime Compute for Apache Flink without inventing target-platform details.

**Architecture:** local repository + exact `ververica-flink` API package + VVR DataFrame API + upload-ready project artifacts + Alibaba Cloud Flink workspace + confirmed sources, sinks, connectors, dependencies, and runtime files.

The core scope is code, local validation, and deployment artifact preparation. Do not upload files, mutate a workspace, create/start/stop a deployment, or call Alibaba Cloud APIs unless the user separately requests those operations.

## RAM Policy

The core workflow invokes no Alibaba Cloud API. No Alibaba Cloud API authorization is needed.

## Core Workflow

Choose one branch in step 1 and follow only its path:

| Branch | Requests | Path |
|---|---|---|
| **Read-only** | API questions, explanations, reviews, or diagnoses with no requested file change | Steps 1–2, then stop |
| **Implementation** | Any request to create or change code, configuration, dependencies, runtime files, or deployment artifacts | Steps 1–6 |

### 1. Route and Inventory

Read repository instructions and every supplied artifact that can affect the result. Route the whole request to **Implementation** when any requested deliverable writes or changes files; otherwise route it to **Read-only**. Inventory every requested outcome, affected file and schema, existing API style, and explicit user constraint.

Complete this step when exactly one branch is selected and every supplied artifact, governing instruction, and requested outcome is accounted for.

### 2. Resolve the Target Contract

Read [references/official-docs.md](references/official-docs.md) and build the branch's evidence set. Resolve one target contract covering the VVR, Python, and local `ververica-flink` versions; source and sink types and schemas; end-to-end data flow; Python dependencies; and runtime files.

- For a new job with no declared VVR version, target VVR 11.8.
- If an existing job targets a version earlier than VVR 11.8, state that this skill supports only VVR 11.8 or later, recommend upgrading to VVR 11.8 for the latest DataFrame API, AI, and multimodal capabilities, and stop without modifying files or creating deployment artifacts.
- On the Implementation branch, represent an unclear source or sink with centralized, visibly labeled local examples for connector type, resource identifier, format, schema, startup behavior, and delivery semantics. Mark every example for replacement before deployment.
- Ask for a missing value only when a labeled local example would change the requested semantics or create an unsafe result.

For **Read-only**, correlate the supplied artifacts with direct evidence, deliver the answer, review, or diagnosis, and finish the branch. Its output is evidence-backed analysis rather than file changes or runnable deployment artifacts. For **Implementation**, classify every target-contract item as confirmed, not applicable, or a labeled example before continuing.

Complete **Read-only** when every requested outcome or finding is tied to direct evidence. Complete **Implementation** step 2 when every target-contract field has a classification, every version has an exact source, and every labeled example has a replacement condition.

### 3. Design the Documented DataFrame Path

For **Implementation**, trace the complete operation graph from source to sink and map every source, transformation, time operation, join, aggregation, and sink to public APIs documented for the exact target version. Unless the user explicitly requests a non-DataFrame API or SQL, design the main pipeline from `pyflink.dataframe` and select APIs in this order: direct `pyflink.dataframe` or `pyflink.multimodal` methods; `pyflink.table.expressions` accepted by a documented DataFrame method; then the smallest documented Table bridge. A bridge uses `df.to_table()`, only the required public Table operation, and documented `pf.from_table(...)`; `pf.DataFrame(table_result)` is not a valid bridge. Do not switch the whole job to Table API or SQL merely because it chains Python functions or UDFs. Record the reason and location of every bridge.

Use DataFrame APIs according to the transformation shape:

- Prefer DataFrame column expressions and built-in functions for projections, filters, joins, and aggregations.
- Prefer documented built-in Multimodal expressions when they implement the requested multimodal operation.
- Use user defined functions when non-built-in logic is needed:
  a. Use `@udf` with `with_column` or `with_columns` for one-to-one scalar Python transformations. Declare `return_dtype` when type inference is unclear, and compose multiple scalar UDFs in the DataFrame pipeline instead of moving the pipeline to SQL.
  b. Use `map` when a Python function consumes and returns one complete row.
  c. Use `@udtf` with `join_lateral`, or use `flat_map`, for verified one-to-many transformations.
  d. Use `map_batches` or a documented vectorized UDF for batch-oriented Pandas or Arrow processing.

Resolve each connector contract through [references/official-docs.md](references/official-docs.md). When reachable code imports third-party packages or defines Python callbacks, read and apply [references/python-dependencies.md](references/python-dependencies.md). When code opens data, models, certificates, configuration, or other files, read and apply [references/runtime-files.md](references/runtime-files.md). Derive the complete list of required and conditional deployment artifacts from those decisions.

Complete this step when every operation has an exact-version API path; every connector and third-party import is resolved; every runtime-file read has a local-to-target mapping; every bridge and example is recorded; and every resulting deployment artifact appears in the artifact list.

### 4. Implement

Before the first write, read [references/project-layout.md](references/project-layout.md), classify the repository as new or existing, and resolve every output location. Write code and supporting files only to those locations.

Unless the user explicitly requested a non-DataFrame API or SQL, start the main job with `import pyflink.dataframe as pf` and keep its source, transformations, and sink on documented DataFrame public APIs. Apply the transformation-shape rules from step 3. Keep a single job file until reusable project modules or complexity justify a modular layout.

Follow the repository's established style and preserve unrelated files. Centralize connector, model, secret-reference, example-contract, and target-path values as configuration. When implementation introduces or changes an import, connector, operation, or file read, return to step 3 and update the documented path before continuing.

Complete this step when every requested file exists at its resolved location; deployable code covers the complete operation graph; schemas and semantics match the target contract; every example and Table bridge is documented; and searches find no hardcoded secret or unresolved template placeholder.

### 5. Validate

Read and apply sections 1–3 of [references/verification-method.md](references/verification-method.md). Run every applicable repository, compile, exact-version import, and bounded-behavior check, then record each result in that reference's evidence format.

Complete this step when every applicable check has a complete evidence entry under the status rules in that reference.

### 6. Prepare Deployment Artifacts

Read and apply [the deployment artifact rules](references/handoff-deliverables.md) and [the console/runtime mapping](references/platform-runtime.md). Use [the bundled README template](assets/handoff/README.md.template) for a new project and adapt its applicable sections to an existing project's documentation. Generate only the project-side scripts and conditional artifacts identified in step 3, then run sections 4–5 of [references/verification-method.md](references/verification-method.md). Finish at upload-ready local artifacts; cloud upload, workspace mutation, deployment, and job start require a separate user request.

Complete this step when the selected layout contains exactly the artifact list; each generated script is syntax-checked; each built ZIP passes integrity and layout checks; every deployment field is confirmed or explicitly unresolved; every target-only check has an owner and expected observation; and the README matches the filesystem with no raw placeholder or secret.

## Success Verification Method

For the read-only branch, success is an evidence-backed answer or report tied to the exact documentation collected in step 2. For the implementation branch, use [references/verification-method.md](references/verification-method.md); require locally evidenced code checks, a verified upload-ready artifact set in the selected project layout, and an explicit list of VVR-only checks. Never report an API-only import check or unexecuted packaging command as a successful target artifact.

## Cleanup

Remove only temporary local artifacts created by this task and only when they are safe to delete. Preserve user environments, caches, fixtures, and unrelated files by default. The core workflow creates no cloud resource or deployment, so it performs no cloud cleanup. For any separately authorized operational expansion, define cleanup and rollback before execution.

## Command Tables

Read [references/related-commands.md](references/related-commands.md) before running a documented command. Substitute placeholders only after confirmation.

## Best Practices

1. Treat the exact version identity as a compatibility contract, not a label.
2. Prefer DataFrame public APIs and built-in expressions; make every fallback auditable.
3. Preserve confirmed source/sink schemas, keys, time semantics, changelog mode, and delivery expectations; keep any example contract explicit, centralized, and replaceable before deployment.
4. Keep the local API package, VVR runtime, deployment attachments, and connector dependencies distinct.
5. Use the canonical deployment attachment mapping in [references/platform-runtime.md](references/platform-runtime.md).
6. Validate code and deployment artifacts with bounded evidence and disclose target-only uncertainty.
7. Keep secrets out of files, commands, logs, examples, and conversation text.
8. Stop at upload-ready deployment artifacts unless the user explicitly authorizes cloud operations.

## Reference Links

| Reference | Read when |
|---|---|
| [references/official-docs.md](references/official-docs.md) | Resolving versions, API symbols, VVR behavior, or official URLs |
| [references/python-dependencies.md](references/python-dependencies.md) | A job imports third-party packages or defines Python callbacks/UDFs |
| [references/runtime-files.md](references/runtime-files.md) | A job opens data, models, certificates, configuration, or other files |
| [deployment artifact rules](references/handoff-deliverables.md) | Placing and validating upload-ready artifacts in a new or existing project |
| [references/platform-runtime.md](references/platform-runtime.md) | Preparing Alibaba Cloud VVR deployment artifacts |
| [references/verification-method.md](references/verification-method.md) | Planning or running validation |
| [references/ram-policies.md](references/ram-policies.md) | Scope expands to console or cloud API operations, or permission fails |
| [references/related-commands.md](references/related-commands.md) | Running local prerequisite, install, search, compile, or test commands |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Reviewing skill output or testing correct and incorrect patterns |
