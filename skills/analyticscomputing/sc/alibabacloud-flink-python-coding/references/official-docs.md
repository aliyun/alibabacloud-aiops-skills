# Official Documentation

Use these entry points to reach product knowledge directly. Alibaba Cloud's Chinese documentation describes VVR availability and managed-runtime behavior; `ververica-flink` source/docstrings and its ReadTheDocs site describe the Python API.

## Source precedence

Alibaba Cloud's Flink documentation spans multiple API generations and may contain outdated information, especially feature limitations in articles outside the DataFrame API documentation. When claims about PyFlink capabilities or usage conflict, the **selected VVR version's PyFlink ReadTheDocs documentation or matching `ververica-flink` source/docstrings take precedence**. If those disagree, inspect the exact-version implementation.

Before stating that a feature is unsupported, verify the restriction against that version's API evidence. A limitation described for Table/DataStream or an older tutorial does not establish the same limitation for DataFrame. Use product documentation for release availability, connector configuration, and deployment requirements; keep unverified API compatibility explicit.

## Product documentation

| Need | Entry point |
|---|---|
| Formal releases and engine versions | [VVR release notes](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/release-notes) |
| Local DataFrame setup and first deployment | [DataFrame quickstart](https://help.aliyun.com/zh/flink/realtime-flink/quickstart) |
| DataFrame capability map and links to symbols | [Python DataFrame API](https://help.aliyun.com/zh/flink/realtime-flink/api-reference) |
| Source/sink support, options, and limitations | [Capability index](dataframe-api.md#source-and-sink-selection) for OSS object scans, URI content retrieval, and TM logs; [connector catalog](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/connectors) for other systems |
| Managed model access | [Flink AI Service](https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service) |
| Python runtimes, settings, pre-installed packages, and logs | [Python job development](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/develop-a-pyflink-job) |
| Python packages, archives, files, and JARs | [Use Python dependencies](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/use-python-dependencies) |
| Deployment fields and console operations | [Create a deployment](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/create-a-deployment) |

## Python API documentation and source

- [DataFrame API](https://ververica-flink-docs.readthedocs.io/en/latest/reference/pyflink.dataframe/index.html): transformations, I/O, UDFs, types, catalog, GPU, AI/LLM, and multimodal expressions.
- [UDF / UDTF](https://ververica-flink-docs.readthedocs.io/en/stable/reference/pyflink.dataframe/udf.html): decorators, synchronous/asynchronous and row/vectorized functions, and usage examples.
- [AI/LLM](https://ververica-flink-docs.readthedocs.io/en/latest/reference/pyflink.dataframe/ai.html): model providers and inference functions.
- [Multimodal operators](https://ververica-flink-docs.readthedocs.io/en/latest/reference/pyflink.multimodal/index.html): image, audio, and video processing.
- [Full API reference](https://ververica-flink-docs.readthedocs.io/en/latest/): also includes Table, DataStream, and common APIs.

For API behavior, read the actual symbol's signature, docstring, version notes, and linked implementation source when available. With a local package, search its source for the symbol; without one, follow ReadTheDocs symbol and source links.

The `latest` and `stable` URLs are discovery entry points, not version guarantees. Check the page's build/version and available version links against the [selected target](product-contract.md). Community documentation is supplementary and does not establish VVR-only API availability.

Every API answer should cite the relevant online page or identify the inspected local package version and symbol. Examples illustrate a pattern; recheck their APIs for the selected target.
