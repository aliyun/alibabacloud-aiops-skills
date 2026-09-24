# DataFrame Capabilities and API Selection

Use this reference when choosing or reviewing connectors, transformations, AI/multimodal operations, or a Table/DataStream fallback. Check exact behavior in the target version's [source and docstrings](official-docs.md).

## DataFrame first

Start new DataFrame jobs with `import pyflink.dataframe as pf`. The API covers relational operations, Python callbacks, connector I/O, and AI/multimodal processing. It is a VVR execution API; familiar Pandas-style naming does not imply Pandas semantics or local execution.

Prefer DataFrame methods and expressions, then built-in AI/multimodal functions, before implementing a Python callback. For column operations, inspect the `Expression` returned by `pf.col()` in `pyflink/table/expression.py`, alongside the DataFrame and multimodal modules. For functionality outside these APIs, use the smallest suitable Table or DataStream bridge.

DataFrame/Table interoperability includes `df.to_table()` and `pf.from_table(...)`. DataStream interoperability goes through the Table environment. Verify type, changelog, and time semantics at each boundary. Explain a fallback where it affects the job; preserve an existing job's API architecture unless migration is requested.

## Source and sink selection

Flink source/sink access to external data systems runs through connectors. DataFrame `read_*` / `write_*` methods provide convenient access to those connectors. The available connector set extends beyond the dedicated Python wrappers.

Start with the required source/sink behavior and the specific [connector documentation](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/connectors) for the chosen VVR release, then select the matching Python access route:

| Access route | When to use it | DataFrame entry points |
|---|---|---|
| Dedicated connector wrapper | A helper covers the selected connector, such as Kafka or Hologres | `pf.read_kafka` / `df.write_kafka`, `pf.read_hologres` / `df.write_hologres` |
| Generic connector | A supported SQL connector has no dedicated wrapper | `pf.read_generic` / `df.write_generic`; use the connector factory identifier and SQL DDL `WITH` option names. Generic reads require a schema. |
| Catalog table | The source or sink is a table managed through a catalog | Create or reuse the table in VVP first, then use `pf.read_catalog_table("catalog.database.table")` / `df.write_catalog_table("catalog.database.table")`. The table definition supplies its schema and connector configuration. |

Catalog-table calls read or write an existing table. Ensure its catalog is available in the job's TableEnvironment, using the target version's catalog configuration APIs where needed. Include required VVP catalog/table setup in the deployment instructions; [Paimon Catalog management](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-apache-paimon-catalogs) illustrates that setup for a data lake.

Product documentation establishes connector capabilities; the selected Python package's source/docstrings establish the call signature. Use these mappings for common discovery gaps:

| Need | Product capability | Python entry point and semantics |
|---|---|---|
| Enumerate OSS objects under a path, including a one-time scan of existing files | [OSS CDC](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/oss-cdc-beta) | `pf.read_generic("oss-cdc", ...)`; `scan.startup.mode="SNAPSHOT"` scans existing objects without consuming incremental events. Produces object metadata and URIs. |
| Retrieve file bytes from an OSS, HTTP, or other supported URI | [FETCH_CONTENT](https://help.aliyun.com/zh/flink/realtime-flink/fetch-content-try-fetch-content) | `pf.col("uri").fetch_content()`; a column expression that turns a URI into binary content. |
| Write result rows to TaskManager logs | [Print connector](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/print-connector) | `df.write_generic("print", ...)`; select the documented logging options for the target. |

For OSS CDC, check the fixed schema, required non-null `key`, OSS access configuration, and target version. Its documented execution mode is streaming, including for `SNAPSHOT`; apply the [execution-mode guidance](../SKILL.md#execution-mode).

Object discovery and content retrieval are separate capabilities. An image pipeline can compose object metadata/URI → fetched bytes → image expressions or a Python UDF → sink. The [official DataFrame image example](https://help.aliyun.com/zh/flink/realtime-flink/dataframe-api) shows URI fetching and image expressions together.

**File access authentication:** when `fetch_content` reads `oss://` or `hdfs://` paths, configure the corresponding filesystem authentication in the deployment's **Flink parameters (Runtime Parameters → Other Configuration)** and include these settings in the README. Follow the same URI-specific configuration as the [OSS connector](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/oss-connector#0f6c7e6d18yvu): OSS bucket credentials and HDFS identity settings are distinct. Credentials configured for an upstream OSS CDC/MNS connector do not replace these filesystem settings.

Before introducing SDK-based discovery or file fetching, establish the missing capability against the target's connector and Expression APIs. I/O selection is complete when source output types, reading semantics, and downstream input types fit together with target-version evidence.

DataFrame methods load registered built-in connector artifacts automatically. Custom or non-built-in factories may require a JAR; use [dependency resolution](workflows/resolve-dependencies.md) for those.

## AI and multimodal capabilities

For code, API answers, examples, and deployment instructions, present only [Flink AI Service](https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service) by default. Introduce BYOK only when the user explicitly requests it or the required model is unsupported by Flink AI Service. Confirm the unsupported-model exception against the service's current model documentation before choosing it.

Inspect the built-ins before adding model SDKs or large Python callbacks:

- `df.llm` exposes model inference and tasks such as classification, extraction, summarization, translation, and embeddings.
- Model providers also configure Flink AI Service: specify the task on the provider and the model on the inference function, leaving API keys and endpoints unset. The [Flink AI Service example](examples/new-jobs/flink-ai-service.md) shows this configuration; verify it against the target version.
- DataFrame multimodal expressions and `pyflink.multimodal` provide image, audio, and video processing, including frame extraction and model-backed operators. Look up their input representations, output types, and runtime dependencies for the target release.

## Python callbacks

Use a UDF for custom scalar logic, row mapping for row-oriented work, and batch/vectorized APIs when the operation benefits from batches. Keep relational and built-in operations visible in the DataFrame pipeline, with explicit callback input/output types.

Whenever a UDF or other Python callback is used, apply [dependency resolution](workflows/resolve-dependencies.md), including any imported packages, model files, and other resources it consumes.

Optional worked patterns: [generic SQL connectors](examples/new-jobs/generic-sql.md), [Flink AI Service](examples/new-jobs/flink-ai-service.md), [multimodal video](examples/new-jobs/multimodal.md), and [UDF with a runtime file](examples/new-jobs/udf-with-runtime-file.md). Adapt them after checking the selected version's API.
