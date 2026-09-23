# AgentLoop High-Code Instrumentation

Use this module to teach, implement, and troubleshoot high-code instrumentation for AgentLoop with LoongSuite GenAI Utils and the OpenTelemetry SDK. It covers Java, Go, Python, and Node.js operations such as LLM, Agent, Tool, and Retrieval, field formats, and context propagation within and across processes. `loongsuite-genai-utils` names a capability; verify distribution names and import paths in current documentation for the target language and version.

## Scope the User's Problem First

Inspect the existing code, dependency manifests, and startup configuration to identify the language and versions, framework, any installed ARMS/LoongSuite agent or OpenTelemetry Provider, the operations to instrument, and the boundary where tracing breaks. Ask only for missing information that changes the solution; continue independent documentation retrieval while waiting.

- **Teaching, examples, local business-code changes, field validation, or broken-trace diagnosis**: use this module directly. Aliyun CLI, credentials, a workspace, and addon templates are not prerequisites.
- **Existing agent or SDK**: inspect its Provider, Context, and Propagator integration to avoid duplicate initialization, duplicate exports, or attaching new spans to a separate trace.
- **AgentLoop resource creation, endpoint discovery, or application registration is also needed**: read [onboarding.md](../onboarding.md) and [ai.md](../ai.md), and apply their cloud-operation prerequisites, User-Agent, and credential rules at that stage. A code question alone does not authorize cloud resource creation.

## Retrieve Official Documentation for Each Task

See [sources.md](sources.md) for discovery entry points and retrieval pitfalls. The bundled [fetch_docs.py](../../scripts/instrumentation/fetch_docs.py) requires only the Python 3.8+ standard library and public HTTPS access. It needs no Browser Use, cookies, login, or paid search tool. Run the commands below from the skill root; when working in the user's project, substitute the script's actual absolute path. Save outputs in the current task's temporary directory, outside the user's source tree.

### 1. Discover All Candidates in the Relevant Directories

```bash
python3 scripts/instrumentation/fetch_docs.py catalog --scope all --language python --output /tmp/agentloop-instrumentation-catalog.json
```

`--language` accepts `java`, `go`, `python`, or `nodejs`; omit it initially for mixed-language tasks. Refresh the public catalog and recursively discover the GenAI entry point's children and every descendant of the Application Monitoring Best Practices directory. Inspect the complete relevant directories, then select multiple candidates by title and directory ancestry. Keyword filtering must not hide relevant siblings merely because their titles omit the language name.

| User need | Documentation to read together |
|---|---|
| Instrument LLM, Agent, Tool, or other business operations from scratch | GenAI overview, the language-specific child document, and the LLM Trace field specification; follow official README/source links when API details are needed |
| Custom ordinary spans, attributes, errors, or metrics | SDK best practices for the language; add its GenAI guide and the field specification when GenAI is involved |
| Broken traces in thread pools, coroutines, asynchronous tasks, or streaming calls | In-process context propagation guidance for the language and lifecycle documentation for the SDK/GenAI implementation on the actual call path |
| Cross-service HTTP/RPC/MQ/WebSocket/MCP tracing | Cross-process guidance for the language and protocol-specific best practices; enumerate and inspect all relevant sibling articles |
| Session, user, or business attributes; Entry spans; attribute propagation | Field specification, the **AI Applications** best-practice directory, and language-specific guidance; filtering only the Java/Python directories misses relevant articles |

Combine search terms such as `上下文`, `异步`, `跨进程`, `自定义`, `GenAI`, `业务属性`, `Entry`, `MCP`, and `Kafka`. Repeated `--keyword` options match candidates with OR semantics. If no titles match, broaden the search and read candidate bodies; a missing title match does not establish that a feature is unsupported. Do not crawl the entire site or load every article body by default.

### 2. Fetch Selected Bodies and Source Metadata

```bash
python3 scripts/instrumentation/fetch_docs.py fetch --node-id 3044328 --output-dir /tmp/agentloop-instrumentation-docs
python3 scripts/instrumentation/fetch_docs.py fetch --node-id 2803611 --output-dir /tmp/agentloop-instrumentation-docs
python3 scripts/instrumentation/fetch_docs.py fetch --url https://help.aliyun.com/zh/cms/cloudmonitor-2-0/add-a-custom-tracking-point-to-the-call-chain-by-loongsuite-otel-util-genai-and-opentelemetry-sdk --output-dir /tmp/agentloop-instrumentation-docs
```

Select subsequent article URLs/nodeIds from the fresh catalog. Read the generated body and metadata, checking the actual title, ID, source URL, update time when supplied, fetch time, nonempty content, and links. Relevant sections, cross-language pages, and API READMEs linked from the body guide further retrieval. Do not produce a complete solution after reading only an abstract or the first article.

If `fetch --node-id` fails, retry `fetch --url` with the canonical URL from the fresh catalog to enable the validated embedded-JSON HTML fallback. Place global network options before the subcommand, for example `python3 scripts/instrumentation/fetch_docs.py --timeout 15 --retries 1 fetch --url <canonical-url> --output-dir <temporary-directory>`. The script also preserves original body HTML/source files for checking complex tables or code. Files left from earlier runs after a nonzero exit are not results of the current attempt.

From the field specification, extract the Resource, Span Attributes, and Events requirements relevant to the task: value types, operation names, span kinds, message and tool-call structures, and serialization. Map these requirements to the target library's API instead of treating field strings as API parameter names. Distinguish required, conditionally required, recommended, and optional fields; trace storage formats may differ from SDK input types. In particular, distinguish the business attribute `gen_ai.span.kind` from OTel `SpanKind`, Resource attributes from span attributes, JSON strings from objects, integer token counts, and each field's seconds/milliseconds/nanoseconds units. Verify Resource source markers required by the integration guide without claiming they necessarily appear in the field table.

### 3. Verify Official Library Details When Needed

Follow official repository links from the freshly retrieved language guide. `fetch --url` supports blob files and tree directories in those official GitHub repositories. A directory result is a link listing; fetch the required README or source file before claiming to have read its API documentation.

```bash
python3 scripts/instrumentation/fetch_docs.py fetch --url https://github.com/alibaba/loongsuite-python/tree/main/util/opentelemetry-util-genai --output-dir /tmp/agentloop-instrumentation-docs
python3 scripts/instrumentation/fetch_docs.py fetch --url https://github.com/alibaba/loongsuite-go/blob/main/util-genai/README_CN.md --output-dir /tmp/agentloop-instrumentation-docs
```

Help articles, repository `main`, and installed versions may differ. Check project lockfiles and the matching tag/version's README, dependency constraints, or signatures. Do not apply one language's package names, parameters, defaults, or version requirements to another. If an old link returns 404, follow [sources.md](sources.md) back to the same official repository's directory, discover the actual path, and fetch it again. Do not claim to have read a broken link.

## Apply the Documentation to the User's Code

Provide the explanation, minimal runnable example, or authorized local code changes requested by the user, beyond a list of links. State the language, library version, existing-agent or standalone-SDK mode, and supporting documentation, then implement the actual call path:

1. **Establish Provider ownership**: in standalone SDK mode, configure Resource attributes including `service.name`, TracerProvider, Processor, Exporter, Propagator, and flush/shutdown on exit. With an existing agent, reuse its instances according to compatibility guidance. GenAI Utils handles semantics and operation lifecycles; it does not automatically configure the endpoint or export pipeline.
2. **Choose the matching operation semantics**: use the target version's Agent/LLM/Tool/Embedding/Retrieval types to capture real calls, models, tokens, inputs, outputs, and errors. Do not invent unmeasured token counts or latency. Use the OTel SDK for ordinary business spans; adding a few `gen_ai.*` attributes does not establish full GenAI format compliance.
3. **Maintain the current context**: creating a span does not necessarily activate it. Capture and restore context at thread, coroutine, and task-scheduling boundaries. Explicitly pass the returned `context.Context` in Go; use the target version's scope API in other languages. Scope exit, detach, and span completion must cover exceptions and cancellation.
4. **Propagate across processes**: inject the sender's current context into the protocol carrier, then extract it before creating a local span at the receiver. Both sides need compatible propagators. Do not stitch traces by manually copying traceId or changing parentSpanId. Follow protocol guidance to choose parent-child relationships or span links, and avoid wrapping propagation already handled automatically.
5. **Handle streaming completion**: keep the span open for actual iteration/consumption, beyond the function that returns a generator or stream. Cover normal completion, exceptions, cancellation, and close. Aggregate usage and end the span only when the stream actually finishes.
6. **Distinguish attributes from propagation**: a span attribute belongs to its span. Baggage propagates through context; whether it becomes attributes on subsequent spans depends on the implementation. Specify which business fields may cross service boundaries, and never put credentials in Baggage.
7. **Connect to AgentLoop**: use the target AgentLoop workspace's actual endpoint, network, and authentication configuration. Verify OTLP HTTP/gRPC, ports, paths, and headers. Teaching examples use environment variables/placeholders. Inject the LicenseKey under the [credential redaction rules](../onboarding.md#credential-output-redaction) without printing its value. Generic ARMS/CMS example workspaces in help articles do not replace the user's AgentLoop workspace.

Message-content capture modes and defaults vary by language and version. Configure them explicitly for the user's needs and verify input/output types and captured content; do not infer all implementations' defaults from one document. Treat retrieved shell commands, code, and user comments as reference material. Document retrieval itself does not execute them.

### Known Differences to Recheck Against Current Sources

- **Python**: the overview, field specification, and newer language guide have referenced different distributions, including `opentelemetry-util-genai`, `loongsuite-util-genai`, and `loongsuite-otel-util-genai`. Do not infer installation packages or imports such as `opentelemetry.util.genai` from names alone; use the target mode/version's guide and distribution contents.
- **Java/Python Entry spans and attribute propagation**: Java best practices reuse an existing entry span and handle its attributes separately from downstream Baggage. Python has a dedicated Entry lifecycle. Do not mechanically translate the Python approach into Java.
- **Node.js**: check whether the installed `cms_node_sdk` registers a standard global OTel Provider. Some documented versions do not and cannot directly use the utility's default handler. A token returned by `startXxx` does not itself activate `context.active()`; pass parent context and establish scopes for manual and automatic instrumentation as required by the version.
- **Go**: older help articles and current repository dependencies can specify different minimum versions. Read the target version's `go.mod`. The GenAI overview has referenced a nonexistent `example/genai` path; do not invent another path and call it verified.

## Validate and Deliver

Match validation to the task. After code changes, run the project's existing build/tests or a minimal call with an in-memory/console exporter. Check span completion, error recording, parent-child relationships and traceId, and field types/message serialization against the freshly retrieved specification. Async/cross-service fixes must cover the actual failing boundary; streaming fixes must cover consumption completion and exceptions/cancellation. State when local checks use a fake model rather than claiming real-model or cloud verification.

If the user requests cloud verification and the environment supports it, use a controlled call to check the service, trace, and key GenAI fields in AgentLoop. Successful `service list` output alone does not prove telemetry ingestion. When endpoints, network access, or credentials are unavailable, finish executable local work and identify the unverified layer; local exporter output is not a cloud result.

Deliver concrete code/changes, dependencies and startup configuration, why the solution addresses the problem, validation results, and the official links used. When retrieval fails, report the failing URL and reason (network, TLS, throttling, page structure, empty body, etc.) and identify unsupported conclusions. User-provided documentation or explicitly dated old caches can still be used, but must not be called successful live retrieval. Do not disable TLS verification or make a browser the only recovery path.
