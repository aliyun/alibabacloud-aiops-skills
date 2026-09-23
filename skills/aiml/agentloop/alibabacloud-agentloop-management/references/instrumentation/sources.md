# Discovering and Fetching Manual Instrumentation Documentation over HTTP

These links provide discovery entry points and troubleshooting clues; they do not replace fresh catalog and article retrieval for each task. HTTPS access was verified on 2026-09-22 using only the Python standard library, without a browser or cookies. Article counts and versions reflect that observation and must not become fixed criteria for completeness in future runs.

## Three Official Entry Points

| Material | Official URL | Observed nodeId |
|---|---|---|
| GenAI overview and language-specific child articles | [Integrate LLM Applications with OpenTelemetry GenAI Utils](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/integrating-llm-applications-with-opentelemetry-genai-utils/) | 3044328 |
| Data format | [LLM Trace Field Definitions](https://help.aliyun.com/zh/arms/application-monitoring/developer-reference/llm-trace-field-definition-description) | 2803611 |
| User-provided starting page for locating best practices | [Tune Java GC Parameters with an AIOps Assistant](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/java-gc-parameters-tuning-with-aiops-agent) | 3043079 |
| Best-practices root catalog found by tracing the starting page's ancestors | [Application Monitoring Best Practices](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/application-monitoring-best-practices/) | 3000060 |

The GC page is a single leaf article, not a three-language SDK tutorial or the best-practices root catalog. Return to Application Monitoring Best Practices and enumerate all child nodes under Java, Go, Python, AI applications, and general practice tutorials. During verification, all 59 leaf articles returned nonempty content. The GenAI overview separately contains four child articles for Java, Python, Go, and Node.js; retain parent nodes that have their own content as well.

## Verified Public HTTP Data Structures

- Catalog: `https://help.aliyun.com/help/json/menupath.json?nodeId=3044328&website=cn&language=zh`; the best-practices starting page ID, `3043079`, also works. The response contains the complete product tree. Locate the target node and recursively traverse **all** `children`. Do not follow only selected nodes, the first item, or `directoryPath`.
- Article content: `https://help.aliyun.com/help/json/document_detail.json?nodeId=2803611&website=cn&language=zh`. Validate the application-level `code`, `success`, `data.nodeId`, `data.title`, and `data.content`; HTTP 200 alone is insufficient.
- HTML content fallback: GET the canonical article URL and use a JSON decoder to parse `window.__ICE_PAGE_PROPS__`. The content is at `docDetailData.storeData.data.content`; do not execute page JavaScript. `data.nodeId` is the actual document ID, while the HTML `main-<number>` may use a different identifier.
- `directoryPath` is only one ancestor path and does not contain all sibling nodes. Calling the content API for a directory-only node may return application-level `code=302` pointing to the first article. Following that redirect does not mean the directory has been enumerated.
- When the catalog API is unavailable, `div.directory` in the canonical directory page's HTML contains direct child links. Read **all** links in that container at each level; `window.globalData.nodeId` on the directory page provides a lookup clue. Header navigation and previous/next article links do not constitute a complete catalog. If catalog completeness cannot be established, report a discovery failure instead of substituting a handful of cached articles.

These public webpage data endpoints were verified during this run and may change. The script uses bounded retries and validates response structures. Changes to API paths or page structures must surface explicitly rather than silently returning an empty success. Preserve code indentation, tables, and links when extracting article content. Keep source files in their original format to avoid breaking examples.

## Select Multiple Candidates for the Task

The following IDs are lookup aids if the catalog changes; they do not replace a fresh catalog. Use source URLs from the current catalog response rather than constructing them from assumed paths.

| Topic | Java | Python | Go / Node.js |
|---|---|---|---|
| GenAI language guide | 3046607 | 3026992 | Go 3045979; Node.js 3049071 |
| Custom OTel spans | 2978907 | 3047977 | Go 2978902 |
| Asynchronous context within a process | 2978909; also check sibling articles about asynchronous tasks | 3047976 | Enumerate sibling Go articles about goroutines, asynchronous execution, and relevant frameworks |
| Cross-process context | 2978905; add Kafka and other articles as required by the protocol | 3048016 | Enumerate sibling Go articles about HTTP, MQ, WebSocket, and other relevant protocols |
| GenAI business attributes and entry points | 3050559 under AI applications | 3048848 under AI applications | Determine support from the current language API and field specification |
| MCP trace correlation | Add SDK documentation for the actual client and server languages | 2978918 under AI applications | Check transports and propagators at both ends |

The actual URLs of the three Python SDK articles are under `/zh/cms/`, without `/cloudmonitor-2-0/`; for example, [Cross-Process Context Propagation](https://help.aliyun.com/zh/cms/implement-cross-process-context-propagation-with-the-opentelemetry-python-sdk). The Java business-attributes article is also under `/zh/cms/`. Determine relevance from catalog membership rather than excluding articles by URL path prefix.

## Official Repository Materials without GitHub Page Rendering

For blob links in help articles, fetch the corresponding `raw.githubusercontent.com` file. For tree links, list all immediate children with `https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}`, then fetch the required README, API, or example files. A directory listing from the Contents API does not mean the file contents have been read. Report specific failures for rate limits or HTTP 404 responses. Determine the appropriate version ref from project dependencies and actual repository tags; do not guess tag names.

Verified deep links from entry pages or actual repository directories:

- Java: [docs/USAGE_zh.md](https://github.com/alibaba/loongsuite-java/blob/main/docs/USAGE_zh.md).
- Python: [util/opentelemetry-util-genai](https://github.com/alibaba/loongsuite-python/tree/main/util/opentelemetry-util-genai), including [README-loongsuite.rst](https://github.com/alibaba/loongsuite-python/blob/main/util/opentelemetry-util-genai/README-loongsuite.rst); do not assume the file is named `README.md`.
- Node.js: [opentelemetry-util-genai/README_CN.md](https://github.com/alibaba/loongsuite-js/blob/main/opentelemetry-util-genai/README_CN.md).
- Go: The overview linked to `alibaba/loongsuite-go/tree/main/example/genai`, which returned HTTP 404 during verification. Inspection of the [official repository root](https://github.com/alibaba/loongsuite-go/tree/main) confirmed that [util-genai/README_CN.md](https://github.com/alibaba/loongsuite-go/blob/main/util-genai/README_CN.md), [util-genai/go.mod](https://github.com/alibaba/loongsuite-go/blob/main/util-genai/go.mod), and [example/genai-demo/README.md](https://github.com/alibaba/loongsuite-go/blob/main/example/genai-demo/README.md) exist. Fetch these alternatives again and check their versions before using them.

At verification time, the documentation and repositories already differed in minimum language/OTel versions, distribution package names, and content-capture defaults. This module therefore does not embed a static multilingual SDK tutorial. Read the sources applicable to the user's dependency versions and clearly state any remaining conflicts or unverified details.
