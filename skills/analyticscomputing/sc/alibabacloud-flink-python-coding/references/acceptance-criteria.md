# Acceptance Criteria

Apply every criterion relevant to the selected workflow.

## Routing and interface gate

### Pass

- Routes a read-only answer, new job, and existing-job change to distinct workflows.
- For a new job, selects exactly one public method for every required source, transformation, and sink before writing files.
- Consolidates missing interface selectors into a blocking question and creates no artifact before the answer.
- Treats real-time/streaming language and business entities as pipeline semantics, not connector evidence.
- On a failed interface gate, returns only a brief reason and the consolidated question, with no code, pseudocode, API sample, or file plan.
- Uses labeled placeholders only for parameters of an already-selected method.
- Consults new-job examples only after the interface gate passes, then adapts their parameters without changing the confirmed methods.
- Delivers complete source-to-sink code with defined symbols and an entry point, plus the full contents and deployment mapping of every selected companion file.

### Fail

- Chooses an example source or sink when the source/sink system is unknown.
- Starts implementation while `read_kafka`, `read_hologres`, and `read_generic` are still plausible.
- Defaults to Kafka or another connector because the request says real-time, streaming, continuously arriving, or names an event type.
- Loads new-job examples during an API inquiry or existing-job modification.
- Delivers a fragment with an undefined source, omitted sink, ellipsis, or referenced companion file whose contents are absent.

## Versions and packages

### Pass

- Keeps VVR, community Flink, Python, documentation, distribution, and import versions separate.
- Keeps VVR 11.8 as the fixed minimum supported release.
- Defaults an unspecified target to the newest formal, non-Preview release resolved directly from the live Chinese VVR release notes.
- Records the short VVR release, full deployment engine version, and matching `ververica-flink` package version as separate identities.
- Treats `ververica-flink` as optional read-only API evidence and `pyflink` as the runtime-provided import namespace.

### Fail

- Treats community Flink 1.20 or 2.3 as VVR 11.8.
- Uses a fixed VVR release for an unspecified target without resolving the live Chinese release notes for that request.
- Selects a Preview release by default or derives deployment/package versions from the short VVR label without exact evidence.
- Attempts to run a VVR job locally through the API-only distribution.
- Adds `ververica-flink`, `pyflink`, `flink`, or `apache-flink` to VVR deployment requirements.

## DataFrame path

### Pass

- Uses the dedicated DataFrame connector wrapper when one exists.
- Uses `read_generic` or `write_generic` for a confirmed SQL connector without a dedicated wrapper.
- Relies on DataFrame automatic built-in artifact loading.
- Maps operations through DataFrame expressions, built-in AI, and multimodal functions before selecting a callback.
- Keeps each callback scoped to one unavailable leaf operation.

### Fail

- Adds manual `pipeline.used-builtin-connectors` for a DataFrame connector.
- Claims a SQL connector requires a Table/SQL pipeline solely because it lacks a dedicated wrapper.
- Puts parsing, model calls, business logic, and sink shaping into one callback when built-ins cover those stages.
- Constructs `pf.DataFrame(table_result)` as a bridge.

## Documentation

### Pass

- Uses the directly opened Chinese VVR release-notes page to resolve an unspecified target and records the lookup date.
- After resolving the target release, uses the bundled static VVR 11.8 Markdown snapshot first when its manifest version applies, and checks the resolved package version and source commit.
- Uses `ververica-flink-docs.readthedocs.io` for live DataFrame symbol fallback.
- Uses Chinese Alibaba Cloud product documentation for VVR availability, pre-installed packages, runtime paths, connectors, and deployment behavior.
- Records the target version and provenance of every live fallback.

### Fail

- Uses a cached search-result snippet or an English Alibaba Cloud page to choose the newest VVR release when the Chinese release notes differ or have not been opened.
- Repeatedly searches overview pages for a snapshot-covered symbol.
- Uses `pyflink.readthedocs.io`, a synthesized version URL, or a live mutable `latest` page as immutable evidence without recording a snapshot or source revision.
- Selects a Table API example over a documented DataFrame method because the overview is stale.

## AI and multimodal work

### Pass

- Uses documented built-in functions and routes new model access through Flink AI Service.
- Keeps model operations visible in the DataFrame graph.

### Fail

- Documents a new-job model-access path other than Flink AI Service.
- Hides supported AI or multimodal operations inside a general-purpose UDF.

## Python dependencies

### Pass

- Traces every reachable third-party import to its distribution and consumer.
- Separates pre-installed packages from exact-pinned packaged dependencies.
- Records Python ABI, CPU, and glibc compatibility.
- Generates a dependency build script only when required and maps a successfully verified `deps.zip` to Python Libraries.
- Reports an unavailable build as `deps.zip: not built`.

### Fail

- Treats a local package as target-preinstalled evidence.
- Adds an unpinned dependency, reuses an incompatible build image, or claims an archive without successful build and ZIP checks.
- Removes an existing pin while reachable code still imports it.

## Runtime files and connector JARs

### Pass

- Maps every reachable file/JAR to source, consumer, format, local path, deployment artifact, console field, target path, and status.
- Maps independent files and custom connector JARs to Additional Dependency Files and documented `/flink/usrlib` paths.
- Maps extracted archives to Python Archives.
- Attaches a connector JAR only when the selected connector is confirmed non-built-in.

### Fail

- Fabricates a missing file, binds target code to a workstation path, or packages credentials.
- Attaches a JAR for an automatically loaded built-in connector.
- Mixes runtime files, connector JARs, Python Libraries, and code archives into one undifferentiated ZIP.

## Validation and handoff

### Pass

- Runs static/repository checks and pure-Python helper tests without starting Flink.
- Separates local checks from DataFrame, connector, AI, runtime-file, and operational VVR checks.
- Produces only conditionally selected artifacts and maps each to one console field.
- Stops at upload-ready local artifacts unless cloud operations are explicitly requested.

### Fail

- Reports DataFrame construction, collection, or connector reachability as locally passed.
- Leaves raw template markers, hardcoded credentials, or undocumented artifacts.
- Uploads or starts a deployment from a coding-only request.

## Completion criterion

Acceptance passes only when every applicable pass criterion is satisfied, no fail criterion is present, and each unresolved target value or blocked artifact is explicit.
