---
name: alibabacloud-flink-python-coding
description: |
  Use this skill when the user needs help with a Flink Python or PyFlink job, especially on Alibaba Cloud Realtime Compute for Apache Flink (VVR): write, modify, review, or debug PyFlink jobs; explain or select Flink Python APIs; resolve package or file dependencies for PyFlink jobs; or prepare PyFlink job deployment.
---

# Alibaba Cloud Flink Python Coding

Support **VVR 11.8 and newer**. For an older job, establish an upgrade target before applying this skill's development or repair guidance.

For every VVR/PyFlink factual answer and API choice, first inspect the selected version's product/API documentation or package source that supports the conclusion. Use model knowledge to guide lookup and reasoning, never as the sole evidence for capabilities, limitations, signatures, or workarounds. Skill references are navigation and product context, not a complete API manual: when they do not cover a question, continue to the linked API documentation or source.

## VVR PyFlink and DataFrame

VVR is Alibaba Cloud's managed Flink runtime. Its Python surface includes **`pyflink.dataframe`**, introduced in VVR 11.8, alongside Table and DataStream APIs. Community PyFlink knowledge alone misses these VVR capabilities:

- **DataFrame:** relational transformations, connector I/O, Python UDFs, and bridges to Table/DataStream.
- **AI inference:** [Flink AI Service](references/dataframe-api.md#ai-and-multimodal-capabilities) and built-in LLM operations for prediction, classification, extraction, summarization, and embeddings.
- **Multimodal processing:** image, audio, and video operations, including decoding, transformation, frame extraction, and model-backed analysis.

Flink sources and sinks connect to external data systems through **connectors**. DataFrame `read_*` / `write_*` methods are convenient Python entry points to them. Use the [connector access routes and capability index](references/dataframe-api.md#source-and-sink-selection) to choose a dedicated wrapper, a generic connector call, or access to a catalog table prepared in VVP.

DataFrame column expressions reuse `pyflink.table.expression.Expression`; that API is part of normal DataFrame development.

For new jobs and general API questions, prioritize DataFrame, including its built-in AI and multimodal functions. Use Table/DataStream when explicitly requested or when the target DataFrame API cannot express the required behavior. Preserve the API structure of existing jobs unless migration is requested.

The local distribution is **`ververica-flink`**, the import namespace is **`pyflink`**, and execution takes place on **VVR**. The package supplies API code and docstrings for development, not a supported local VVR runtime. See [versions and API source](references/product-contract.md) when establishing a target or obtaining source for inspection.

### Execution mode

Streaming mode can process **bounded data** and has more complete feature support in VVR. Prefer it for new jobs, including one-time scans. Configure finite reading through the source's bounded or snapshot settings. Consider batch mode for an explicit user requirement or a workload-specific benefit, after confirming support from the required connectors and operators.

## Route

Read the workflow matching the request before answering or implementing. Workflows can compose: development can call dependency resolution and artifact preparation.

| Use case | Reference |
|---|---|
| Write a new job | [New job](references/workflows/new-job.md) |
| Modify or review an existing job | [Existing job](references/workflows/modify-existing-job.md) |
| Answer an API question, including whether a feature is supported | [API inquiry](references/workflows/api-inquiry.md) |
| Debug an error or failing job | [Debug](references/workflows/debug.md) |
| Resolve Python packages, runtime files, or connector JARs | [Dependencies](references/workflows/resolve-dependencies.md) |
| Prepare local deployment artifacts and instructions | [Prepare deployment](references/workflows/prepare-deployment.md) |

Use [official documentation](references/official-docs.md) for direct product and API entry points, and its [source precedence](references/official-docs.md#source-precedence) when documentation conflicts. Exact API behavior comes from the selected version's package source/docstrings or online documentation and source; connector selection also requires the connector documentation.

This skill delivers local code, answers, and deployment artifacts. The README supports manual deployment or handoff to an available job-submission skill when the user requests deployment. Cloud submission is a separate operation; this skill's local workflows require no Alibaba Cloud API permissions.
