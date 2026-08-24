# OT AI Trace Collection Spec

**Status: Development**

LLM Trace is a semantic convention defined by Alibaba Cloud on top of the
OpenTelemetry standard and the concepts of the large-language-model application
domain. It extends Attributes, Resource, and Event to describe LLM application
call-chain data, capturing key operations such as model input/output requests and
token consumption. It provides rich, context-aware semantic data for Completion,
Chat, RAG, Agent, and Tool scenarios so that data can be traced and reported. The
semantic fields keep evolving with the community.

Span top-level fields follow the OTel open-source standard. For the detailed
top-level trace fields of the underlying storage used by Alibaba Cloud
Observability OpenTelemetry Edition, see the
[product documentation](https://help.aliyun.com/zh/arms/application-monitoring/developer-reference/trace-explorer-parameters#concept-2144432).

**Note:** the LLM-related SpanKind is an *Attribute*. It is not the same thing as
the OpenTelemetry trace
[Span kind](https://opentelemetry.io/docs/concepts/signals/traces/#span-kind).

Requirement levels used in the tables below follow the OTel convention:
`Required`, `Conditionally Required`, `Recommended`, and `Opt-In`.

# Common Part

**Status: Development**

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.session.id` | Session ID | string | `ddde34343-f93a-4477-33333-sdfsdaf` | Conditionally Required | Alibaba Cloud extension |
| `gen_ai.user.id` | End-user identifier of the application | string | `u-lK8JddD` | Conditionally Required | Alibaba Cloud extension |
| `gen_ai.user.name` | End-user name of the application | string | `zhangsan@example.com` | Opt-In | Internal use, not yet exposed to customers |
| `gen_ai.span.kind` | Operation type [1] | string | See LLM Span Kind | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type [2] | string | See LLM Operation Name | Required |  |
| `gen_ai.framework` | Framework in use | string | `langchain`; `llama_index` | Conditionally Required | Alibaba Cloud extension |

**[1] `gen_ai.span.kind`**: this field will eventually be replaced by
`gen_ai.operation.name`. Because a large number of consumers still read it, the
probe side must keep recording it, and the server side can gradually switch to
values derived from `gen_ai.operation.name`. The mapping is:

| `gen_ai.span.kind` | `gen_ai.operation.name` | Description | Notes |
| --- | --- | --- | --- |
| RETRIEVER | `retrieval` | Document retrieval |  |
| LLM | `chat`; `generate_content`; `text_completion` | Model invocation |  |
| EMBEDDING | `embeddings` | Embedding |  |
| TOOL | `execute_tool` | Tool invocation |  |
| AGENT | `create_agent`; `invoke_agent` | Agent invocation |  |
| RERANKER | - | Rerank invocation | Not in the community spec yet; to be added |
| CHAIN | - | Chain (invocation unit) | Not in the community spec yet; needs further definition |
| TASK | - | Task invocation | Not in the community spec yet; needs further definition |
| ENTRY | - | Entry-point marker | Not in the community spec yet; needs further definition |
| STEP | - | ReAct round marker | Not in the community spec yet; needs further definition |

**[2] `gen_ai.operation.name`**: the second-level operation type. It should come
from one of the following values, or be a custom value:

| Value | Description |
| --- | --- |
| `chat` | Chat completion operation |
| `create_agent` | Create a GenAI agent |
| `embeddings` | Word-embedding operation |
| `execute_tool` | Invoke a tool |
| `generate_content` | Multimodal content generation |
| `invoke_agent` | Invoke a GenAI agent |
| `retrieval` | Document retrieval |
| `text_completion` | Text completion |

## Resources

| ResourceKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `host.name` | Host name | string | `local`; `127.0.0.1` | Conditionally Required | Internal use, not yet exposed to customers |
| `service.name` | Application name | string | `test-easy-rag` | Required |  |
| `service.id` | Application ID, user-defined | string | `23432-234-sdfasd-ddd` | Opt-In | Internal use, not yet exposed to customers |
| `service.version` | Application version | string | `1.0` | Opt-In | Internal use, not yet exposed to customers |
| `service.owner.id` | Alibaba Cloud primary account of the owning developer | string | `1672753017899339` | Opt-In | Internal use, not yet exposed to customers |
| `service.owner.sub_id` | Alibaba Cloud RAM sub-account of the owning developer | string | Sub-account ID under `1672753017899339` | Opt-In | Internal use, not yet exposed to customers |
| `service.app.name` | Developer-facing application name | string | `HR Assistant` | Opt-In | Internal use, not yet exposed to customers |
| `service.app.id` | Developer-facing application ID, user-defined | string | `6f57a126f466455cb48f50145de14d1e` | Opt-In | Internal use, not yet exposed to customers |
| `service.app.owner_id` | Alibaba Cloud UID of the application developer | string | `1672753017899339` | Opt-In | Internal use, not yet exposed to customers |
| `acs.cms.workspace` | Cloud Monitor workspace [1] | string | `arms-test` | Conditionally Required | Maps to the Cloud Monitor 2.0 workspace |
| `acs.arms.service.id` | Cloud Monitor service ID [2] | string | `ggxw4lnjuz@b63ba5a1d60b517ae374f` | Conditionally Required | Unique service ID |
| `ali.trace.source` | Application source | string | `mse-gateway`; `alb` | Conditionally Required | Identifies the originating cloud product in integrations |

**[1] `acs.cms.workspace`**: **must** be added once the probe supports Cloud
Monitor 2.0.

**[2] `acs.arms.service.id`**: **must** be added once the probe supports Cloud
Monitor 2.0.

# Chain

**Status: Development**

A Chain wires an LLM together with several other components to accomplish a
complex task. It can contain retrieval, embedding, and LLM calls, and it can
nest other Chains.

The span should be named `chain {chain_name}`, or just `chain` when `chain_name`
cannot be obtained.

**Note**: the OpenTelemetry community does not yet define a semantic convention
for this span type.

**Note**: the Chain span is currently used only by the LangChain framework.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `CHAIN` | Required | Extension; not present in the OTel spec |
| `gen_ai.operation.name` | Second-level operation type | string | `workflow`; `task` | Conditionally Required |  |
| `input.value` | Input content | string | `Who Are You!` | Recommended | Needed for evaluation |
| `output.value` | Returned content | string | `I am ChatBot` | Recommended | Needed for evaluation |
| `gen_ai.user.time_to_first_token` | Time to first token [2] | integer | 1000000 | Recommended | Used for XTrace metric aggregation |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In a Chain the value
**must** be `CHAIN`.

**[2] `gen_ai.user.time_to_first_token`**: the end-to-end time to first token for
one question, measured from the moment the server receives the user request until
the first packet is returned, in nanoseconds.

# Retriever

**Status: Development**

A Retriever typically represents access to a vector store or a database, usually
to supply extra context that improves the accuracy and efficiency of the LLM
response.

`gen_ai.operation.name` should be `retrieval`. When `gen_ai.operation.name` is
`retrieval`, `gen_ai.span.kind` can be inferred as RETRIEVER.

The span should be named `{gen_ai.operation.name} {gen_ai.data_source.id}`; other
naming formats are acceptable in special cases.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `RETRIEVER` | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type [2] | string | `retrieval` | Required |  |
| `gen_ai.data_source.id` | Unique data-source identifier [3] | string | `H7STPQYOND` | Conditionally Required |  |
| `gen_ai.provider.name` | Model provider | string | `openai` | Conditionally Required |  |
| `gen_ai.request.model` | Model name specified in the request | string | `gpt-4` | Conditionally Required |  |
| `gen_ai.request.top_k` | topK specified in the request | float | `1.0` | Recommended |  |
| `gen_ai.retrieval.documents` | List of retrieved documents [4] | string | `[{"id": "doc_123","score": 0.95},{"id": "doc_456","score": 0.87},{"id": "doc_789","score": 0.82}]` | Opt-In |  |
| `gen_ai.retrieval.query.text` | Retrieval query text | string | `what is the topic in xxx?` | Opt-In |  |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In a Retriever the
value **must** be `RETRIEVER`.

**[2] `gen_ai.operation.name`**: the second-level operation type.

**[3] `gen_ai.data_source.id`**: the unique ID of the data source that an AI Agent
or RAG application depends on. It can be an external database, object storage, a
document collection, a website, or any other storage system.

**[4] `gen_ai.retrieval.documents`**: records the list of retrieved documents and
**must** follow the retrieved-document JSON Schema
(`gen-ai_messages_schema/gen-ai-retrieval-documents.json` in the upstream spec).
Each document object should carry at least: `id` (string), the unique document
identifier, and `score` (double), the relevance score.

# Reranker

**Status: Development**

A Reranker scores several input documents against the question and reorders them,
possibly returning only the top-K documents to the LLM.

The span should be named `rerank {reranker.model_name}`, or just `rerank` when
`reranker.model_name` cannot be obtained.

**Note**: the OpenTelemetry community does not yet define a semantic convention
for this span type.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `RERANKER` | Required | Extension; not present in the OTel spec |
| `reranker.query` | Reranker request input | string | `How to format timestamp?` | Opt-In |  |
| `reranker.model_name` | Model used by the reranker | string | `cross-encoder/ms-marco-MiniLM-L-12-v2` | Opt-In |  |
| `reranker.top_k` | Rank cut-off after reranking | integer | `3` | Opt-In |  |
| `reranker.input_document` | Metadata of the input documents [2] | string | See example | Required |  |
| `reranker.output_document` | Metadata of the output documents [3] | string | See example | Required |  |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In a Reranker the value
**must** be `RERANKER`.

**[2] `reranker.input_document`**: the rerank input documents, as a JSON array.
`metadata` holds basic document information such as path, file name, and source.
For the format see the upstream `gen-ai_content-schema` document.

**[3] `reranker.output_document`**: the rerank output documents, as a JSON array.
`metadata` holds basic document information such as path, file name, and source.
For the format see the upstream `gen-ai_content-schema` document.

# LLM

**Status: Development**

LLM marks the invocation or inference of a large model, for example calling
different models through an SDK or OpenAPI for inference or text generation.

`gen_ai.operation.name` should be one of `chat`, `generate_content`, or
`text_completion`. When it holds one of those values, `gen_ai.span.kind` can be
inferred as LLM.

The span should be named `{gen_ai.operation.name} {gen_ai.request.model}`; other
naming formats are acceptable in special cases.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `LLM` | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type [2] | string | `chat`; `generate_content`; `text_completion` | Required |  |
| `gen_ai.provider.name` | Model provider | string | `openai` | Required |  |
| `gen_ai.conversation.id` | Unique conversation ID [3] | string | `conv_5j66UpCpwteGg4YSxUnt7lPY` | Conditionally Required |  |
| `gen_ai.output.type` | Output type requested from the LLM [4] | string | `text`; `json`; `image`; `audio` | Conditionally Required |  |
| `gen_ai.request.choice.count` | Number of candidate generations requested | int | `3` | Conditionally Required when not 1 |  |
| `gen_ai.request.model` | Model name specified in the request | string | `gpt-4` | Required |  |
| `gen_ai.request.seed` | Seed specified in the request | string | `gpt-4` | Conditionally Required |  |
| `gen_ai.request.frequency_penalty` | Frequency penalty in the request | float | `0.1` | Recommended |  |
| `gen_ai.request.max_tokens` | Maximum token count in the request | integer | `100` | Recommended |  |
| `gen_ai.request.presence_penalty` | Presence penalty in the request | float | `0.1` | Recommended |  |
| `gen_ai.request.temperature` | Temperature in the request | float | `0.1` | Recommended |  |
| `gen_ai.request.top_p` | topP in the request | float | `1.0` | Recommended |  |
| `gen_ai.request.top_k` | topK in the request | float | `1.0` | Recommended |  |
| `gen_ai.request.stop_sequences` | LLM stop sequences | string[] | `["stop"]` | Recommended |  |
| `gen_ai.response.id` | Unique ID generated by the LLM | string | `gpt-4-0613` | Recommended |  |
| `gen_ai.response.model` | Model that produced the generation | string | `gpt-4-0613` | Recommended |  |
| `gen_ai.response.finish_reasons` | Reasons the LLM stopped generating | string[] | `["stop"]` | Recommended |  |
| `gen_ai.response.time_to_first_token` | Model-side time to first token in streaming responses [5] | integer | `1000000` | Recommended | Alibaba Cloud extension |
| `gen_ai.response.reasoning_time` | Reasoning time of a reasoning model [6] | integer | `1248` | Recommended | Alibaba Cloud extension |
| `gen_ai.usage.input_tokens` | Input tokens used | integer | `100` | Recommended |  |
| `gen_ai.usage.output_tokens` | Output tokens used | integer | `200` | Recommended |  |
| `gen_ai.usage.total_tokens` | Total tokens used | integer | `300` | Recommended | Alibaba Cloud extension |
| `gen_ai.usage.cache_creation.input_tokens` | Tokens written into the provider cache [7] | integer | `25` | Recommended |  |
| `gen_ai.usage.cache_read.input_tokens` | Tokens read from the provider cache [8] | integer | `50` | Recommended |  |
| `gen_ai.input.messages` | Model input content [9] | string | `[{"role": "user", "parts": [{"type": "text", "content": "Weather in Paris?"}]}, {"role": "assistant", "parts": [{"type": "tool_call", "id": "call_VSPygqKTWdrhaFErNvMV18Yl", "name":"get_weather", "arguments":{"location":"Paris"}}]}, {"role": "tool", "parts": [{"type": "tool_call_response", "id":" call_VSPygqKTWdrhaFErNvMV18Yl", "result":"rainy, 57 deg F"}]}]` | Opt-In |  |
| `gen_ai.output.messages` | Model output content [10] | string | `[{"role":"assistant","parts":[{"type":"text","content":"The weather in Paris is currently rainy with a temperature of 57 deg F."}],"finish_reason":"stop"}]` | Opt-In |  |
| `gen_ai.system_instructions` | System prompt content [11] | string | `[{"type": "text", "content": "You are a helpful assistant"}]` | Opt-In |  |
| `gen_ai.tool.definitions` | Tool definition list [12] | string | `[{"type":"function","name":"get_current_weather","description": "Get the current weather in a given location","parameters":{"type":"object","properties":{"location":{"type":"string","description":"The city and state, e.g. San Francisco, CA"},"unit": {"type":"string","enum":["celsius","fahrenheit"]}},"required":["location","unit"]}}]` | Opt-In |  |
| `gen_ai.latency.time_in_model_prefill` | LLM prefill time, in nanoseconds | integer | `1000` | Recommended | Alibaba Cloud extension; collected only for inference engines |
| `gen_ai.latency.time_in_model_decode` | LLM decode time, in nanoseconds | integer | `1000` | Recommended | Alibaba Cloud extension; collected only for inference engines |
| `gen_ai.latency.time_in_model_inference` | LLM inference time (prefill plus decode), in nanoseconds | integer | `1000` | Recommended | Alibaba Cloud extension; collected only for inference engines |
| `gen_ai.input.multimodal_metadata` | Multimodal data referenced by the model input [13] | string[] | `[{"type":"uri","mime_type":"image/jpeg","uri":"sls://project/logstore/date/object","modality":"image"}]` | Recommended | Alibaba Cloud extension; used for vector indexing in SLS |
| `gen_ai.output.multimodal_metadata` | Multimodal data referenced by the model output [14] | string[] | `[{"type":"uri","mime_type":"image/jpeg","uri":"sls://project/logstore/date/object","modality":"image"}]` | Recommended | Alibaba Cloud extension; used for vector indexing in SLS |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In an LLM span the value
**must** be `LLM`.

**[2] `gen_ai.operation.name`**: the second-level operation type.

**[3] `gen_ai.conversation.id`**: the unique conversation ID. It **should** be
collected whenever instrumentation can obtain it conveniently.

**[4] `gen_ai.output.type`**: **should** be collected when it is available and the
request specified a type (for example an output format). The value should belong
to the following enum, or be a custom value:

| Value | Description |
| --- | --- |
| `image` | Image |
| `json` | A JSON object with a defined shape |
| `speech` | Speech |
| `text` | Plain text |

**[5] `gen_ai.response.time_to_first_token`**: the end-to-end time to first token
for one question, measured from the moment the server receives the user request
until the first packet is returned, in nanoseconds.

**[6] `gen_ai.response.reasoning_time`**: the duration of the reasoning phase of
the response, in milliseconds.

**[7] `gen_ai.usage.cache_creation.input_tokens`**: this value should already be
included in `gen_ai.usage.input_tokens`.

**[8] `gen_ai.usage.cache_read.input_tokens`**: this value should already be
included in `gen_ai.usage.input_tokens`.

**[9] `gen_ai.input.messages`**: records the input content of the LLM call. It
**must** follow the input-message JSON Schema
(`gen-ai_messages_schema/gen-ai-input-messages.json` in the upstream spec), and
messages **must** be supplied in the order they were sent to the model or agent.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[10] `gen_ai.output.messages`**: records the model output content. It **must**
follow the output-message JSON Schema
(`gen-ai_messages_schema/gen-ai-output-messages.json` in the upstream spec), and
messages **must** be supplied in the order they were sent to the model or agent.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[11] `gen_ai.system_instructions`**: records the system prompt or system
instruction content separately. It **must** follow the system-instruction JSON
Schema (`gen-ai_messages_schema/gen-ai-system_instructions.json` in the upstream
spec). When the system prompt can be obtained on its own, it **should** be
recorded in this field; when it is part of the model call, record it inside
`gen_ai.input.messages` instead.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[12] `gen_ai.tool.definitions`**: records the tool definitions carried in the
model request. It **must** follow the tool-definition JSON Schema
(`gen-ai_messages_schema/gen-ai-tool-definitions.json` in the upstream spec). The
attribute can be very large, so by default collection may keep only the `type` and
`name` fields. The remaining fields are collected only when the
`otel.instrumentation.genai.capture-message-content` switch is enabled.

**[13] `gen_ai.input.multimodal_metadata`**: aggregates the multimodal data
referenced by the model input. It **must** follow the input-message JSON Schema
and **only** contains UriPart messages.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[14] `gen_ai.output.multimodal_metadata`**: aggregates the multimodal data
referenced by the model output. It **must** follow the output-message JSON Schema
and **only** contains UriPart messages.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

## Recording instructions, inputs, and outputs

User input and model responses may be recorded as events (that is, logs)
associated with the GenAI span. For details see the upstream LLM Logs document.

### Full (buffered) content

Model instructions, user messages, and model output are generally considered
sensitive and are large in volume.

Recording large or sensitive content in telemetry can be problematic because of
storage cost, regulatory requirements, or the need for different access controls
over operational data and user data.

Instrumentation therefore should not capture this content by default, but should
offer an option that lets users opt in.

Application developers should pick the mode that matches their needs and
maturity:

1. [Default] Do not record instructions, inputs, or outputs.

2. Record instructions, inputs, and outputs on the GenAI span using the
   corresponding attributes (`gen_ai.system_instructions`,
   `gen_ai.input.messages`, `gen_ai.output.messages`). This suits environments
   where telemetry volume is manageable, where no privacy regulation applies, or
   where telemetry storage already meets the relevant requirements - for example
   pre-production.

3. Store the content externally and record a reference on the span. This is the
   recommended production mode when telemetry volume is large or sensitive data
   needs careful handling. External storage also allows independent access
   control.

#### Recording content in attributes

The content captured in `gen_ai.system_instructions`, `gen_ai.input.messages`, and
`gen_ai.output.messages` can be large.

It may include multimodal content, and even as text it can exceed the telemetry
backend's limits on payload or attribute-value size.

The input and output attributes follow the common structure formally defined by
the input-message and output-message JSON Schemas in the upstream spec.

> [!NOTE]
>
> Structured attributes are supported on events (or logs) but may not be
> supported on spans yet. See the OTel proposal
> [extending attributes to support complex values](https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/4485-extending-attributes-to-support-complex-values.md).
> In a language where spans do not support structured attributes yet, serialize
> the attribute value to a JSON string on the span and record it in structured
> form on the event.

Instrumentation may offer a configuration option that truncates attributes such
as individual message content while keeping the JSON structure intact.

#### Uploading content to external storage

Instrumentation may support a user-defined in-process hook that handles content
upload.

That hook should be independent of the flags that control capturing
`gen_ai.system_instructions`, `gen_ai.input.messages`, and
`gen_ai.output.messages`.

When such a hook is supported and configured, instrumentation should call it
regardless of the sampling decision, passing:

- the instruction, input, and output objects in the format defined by this spec
  (before serialization to a JSON string);
- the span instance.

The hook implementation should be able to enrich and modify the incoming span,
instructions, and message objects.

If instrumentation is also configured to record the
`gen_ai.system_instructions`, `gen_ai.input.messages`, and
`gen_ai.output.messages` attributes, it should record them after calling the hook
and should record the values as possibly modified by the hook.

The hook API should be generic. The application or the distribution owns the hook
implementation, including:

- uploading content synchronously or asynchronously;
- recording a reference to the uploaded content on the span;
- handling the content in some other way.

The application or an OpenTelemetry distribution may also implement content
upload inside the data-processing pipeline (in process or through the Collector)
based on the `gen_ai.system_instructions`, `gen_ai.input.messages`, and
`gen_ai.output.messages` attributes. Given the possible data volume, tune the
batching and export settings of the OpenTelemetry SDK pipeline accordingly.

TODO: provide a generic example for recording a reference to externally stored
content on a span.

For an LLM call example, see the upstream `gen-ai-messages-example` document.

### Streaming chunks

TODO

# Embedding

**Status: Development**

Embedding marks one embedding operation, for example running a text-embedding
model so that later similarity queries can improve the answer.

`gen_ai.operation.name` should be `embeddings`. When `gen_ai.operation.name` is
`embeddings`, `gen_ai.span.kind` can be inferred as EMBEDDING.

The span should be named `{gen_ai.operation.name} {gen_ai.request.model}`; other
naming formats are acceptable in special cases.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `EMBEDDING` | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type [2] | string | `embeddings` | Required |  |
| `gen_ai.provider.name` | Model provider | string | `openai` | Required |  |
| `gen_ai.request.model` | Model name specified in the request | string | `gpt-4` | Conditionally Required |  |
| `gen_ai.embeddings.dimension.count` | Number of dimensions the embedding should have | integer | `1024` | Recommended |  |
| `gen_ai.request.encoding_formats` | Encoding formats requested for the embedding | string[] | `["base64"]`; `["float", "binary"]` | Recommended |  |
| `gen_ai.usage.input_tokens` | Tokens consumed by the input text | integer | `10` | Opt-In |  |
| `gen_ai.usage.total_tokens` | Total tokens consumed by the embedding | integer | `10` | Opt-In | Alibaba Cloud extension |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In an Embedding span
the value **must** be `EMBEDDING`.

**[2] `gen_ai.operation.name`**: the second-level operation type.

# Tool

**Status: Development**

Tool marks a call to an external tool, for example invoking a calculator or
requesting a weather API for the latest conditions.

`gen_ai.operation.name` should be `execute_tool`. When `gen_ai.operation.name` is
`execute_tool`, `gen_ai.span.kind` can be inferred as TOOL.

The span should be named `{gen_ai.operation.name} {gen_ai.tool.name}`; other
naming formats are acceptable in special cases.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `TOOL` | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type | string | `execute_tool` | Required |  |
| `gen_ai.tool.call.id` | Tool call ID | string | `call_mszuSIzqtI65i1wAUOE8w5H4` | Recommended |  |
| `gen_ai.tool.description` | Tool description | string | `Multiply two numbers` | Recommended |  |
| `gen_ai.tool.name` | Tool name | string | `get_weather` | Recommended |  |
| `gen_ai.tool.type` | Tool type | string | `function`; `extension`; `datastore` | Recommended |  |
| `gen_ai.tool.call.arguments` | Tool call arguments [2] | string | `{"location": "San Francisco?","date": "2025-10-01"}` | Opt-In |  |
| `gen_ai.tool.call.result` | Tool call result [3] | string | `{"temperature_range": {"high": 75,"low": 60},"conditions": "sunny"}` | Opt-In |  |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In a Tool span the
value **must** be `TOOL`.

**[2] `gen_ai.tool.call.arguments`**: the tool call arguments, as a JSON string.
Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[3] `gen_ai.tool.call.result`**: the tool call result, as a JSON string.
Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

# Agent

**Status: Development**

Agent represents the agent scenario: a more complex Chain that decides the next
step from the model's reasoning output. It may involve several LLM and Tool calls
that step by step arrive at the final answer.

`gen_ai.operation.name` should be `invoke_agent` or `create_agent`. When it holds
one of those values, `gen_ai.span.kind` can be inferred as AGENT.

The span should be named `{gen_ai.operation.name} {gen_ai.agent.name}`; other
naming formats are acceptable in special cases.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `AGENT` | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type [2] | string | `invoke_agent`; `create_agent` | Required |  |
| `gen_ai.conversation.id` | Unique conversation ID [3] | string | `conv_5j66UpCpwteGg4YSxUnt7lPY` | Conditionally Required |  |
| `gen_ai.agent.description` | Agent description | string | `Helps with math problems`; `Generates fiction stories` | Conditionally Required |  |
| `gen_ai.agent.id` | Unique agent identifier | string | `asst_5j66UpCpwteGg4YSxUnt7lPY` | Conditionally Required |  |
| `gen_ai.agent.name` | Agent name | string | `Math Tutor`; `Fiction Writer` | Conditionally Required |  |
| `gen_ai.data_source.id` | Unique data-source identifier [4] | string | `H7STPQYOND` | Conditionally Required |  |
| `gen_ai.usage.input_tokens` | Input tokens used | integer | `100` | Recommended |  |
| `gen_ai.usage.output_tokens` | Output tokens used | integer | `200` | Recommended |  |
| `gen_ai.usage.total_tokens` | Total tokens used | integer | `300` | Recommended | Extension; not present in the OTel spec |
| `gen_ai.usage.cache_creation.input_tokens` | Tokens written into the provider cache [5] | integer | `25` | Recommended |  |
| `gen_ai.usage.cache_read.input_tokens` | Tokens read from the provider cache [6] | integer | `50` | Recommended |  |
| `gen_ai.input.messages` | Model input content [7] | string | `[{"role": "user", "parts": [{"type": "text", "content": "Weather in Paris?"}]}, {"role": "assistant", "parts": [{"type": "tool_call", "id": "call_VSPygqKTWdrhaFErNvMV18Yl", "name":"get_weather", "arguments":{"location":"Paris"}}]}, {"role": "tool", "parts": [{"type": "tool_call_response", "id":" call_VSPygqKTWdrhaFErNvMV18Yl", "result":"rainy, 57 deg F"}]}]` | Opt-In |  |
| `gen_ai.output.messages` | Model output content [8] | string | `[{"role":"assistant","parts":[{"type":"text","content":"The weather in Paris is currently rainy with a temperature of 57 deg F."}],"finish_reason":"stop"}]` | Opt-In |  |
| `gen_ai.system_instructions` | System prompt content [9] | string | `[{"type": "text", "content": "You are a helpful assistant"}]` | Opt-In |  |
| `gen_ai.tool.definitions` | Tool definition list [10] | string | `[{"type":"function","name":"get_current_weather","description": "Get the current weather in a given location","parameters":{"type":"object","properties":{"location":{"type":"string","description":"The city and state, e.g. San Francisco, CA"},"unit": {"type":"string","enum":["celsius","fahrenheit"]}},"required":["location","unit"]}}]` | Opt-In |  |
| `gen_ai.response.time_to_first_token` | Agent time to first token | integer | `1000000` | Recommended | Not supported by the OTel community yet |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In an Agent span the
value **must** be `AGENT`.

**[2] `gen_ai.operation.name`**: the second-level operation type.

**[3] `gen_ai.conversation.id`**: the unique conversation ID. It **should** be
collected whenever instrumentation can obtain it conveniently.

**[4] `gen_ai.data_source.id`**: the unique ID of the data source that an AI Agent
or RAG application depends on. It can be an external database, object storage, a
document collection, a website, or any other storage system.

**[5] `gen_ai.usage.cache_creation.input_tokens`**: this value should already be
included in `gen_ai.usage.input_tokens`.

**[6] `gen_ai.usage.cache_read.input_tokens`**: this value should already be
included in `gen_ai.usage.input_tokens`.

**[7] `gen_ai.input.messages`**: records the input content of the LLM call. It
**must** follow the input-message JSON Schema, and messages **must** be supplied
in the order they were sent to the model or agent.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[8] `gen_ai.output.messages`**: records the model output content. It **must**
follow the output-message JSON Schema, and messages **must** be supplied in the
order they were sent to the model or agent.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[9] `gen_ai.system_instructions`**: records the system prompt or system
instruction content separately. It **must** follow the system-instruction JSON
Schema. When the system prompt can be obtained on its own, it **should** be
recorded in this field; when it is part of the model call, record it inside
`gen_ai.input.messages` instead.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[10] `gen_ai.tool.definitions`**: records the tool definitions carried in the
model request. It **must** follow the tool-definition JSON Schema. The attribute
can be very large, so by default collection may keep only the `type` and `name`
fields. The remaining fields are collected only when the
`otel.instrumentation.genai.capture-message-content` switch is enabled.

# Task

**Status: Development**

Task marks one internal custom method, for example calling a local function or
other application-defined logic.

The span should be named `run_task {gen_ai.task.name}`; other naming formats are
acceptable in special cases.

**Note**: the OpenTelemetry community does not yet define a semantic convention
for this span type, so `gen_ai.operation.name` may still change.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `TASK` | Required | Extension; not present in the OTel spec |
| `gen_ai.operation.name` | Second-level operation type | string | `run_task` | Required |  |
| `input.value` | Input parameters | string | Input parameters in a custom JSON format | Opt-In |  |
| `input.mime_type` | Input MIME type | string | `text/plain`; `application/json` | Opt-In |  |
| `output.value` | Returned result | string | Output result in a custom JSON format | Opt-In | Internal use, not yet exposed to customers |
| `output.mime_type` | Output MIME type | string | `text/plain`; `application/json` | Opt-In |  |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In a Task span the
value **must** be `TASK`.

# Entry

**Status: Development**

Entry marks the entry point of a call into the AI application system.

The span should be named `enter_ai_application_system`; other naming formats are
acceptable in special cases.

**Note**: the OpenTelemetry community does not yet define a semantic convention
for this span type, so `gen_ai.operation.name` may still change.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `ENTRY` | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type | string | `enter` | Recommended |  |
| `gen_ai.session.id` | Session ID | string | `ddde34343-f93a-4477-33333-sdfsdaf` | Conditionally Required | Alibaba Cloud extension |
| `gen_ai.user.id` | End-user identifier of the application | string | `u-lK8JddD` | Conditionally Required | Alibaba Cloud extension |
| `gen_ai.input.messages` | Model input content [2] | string | `[{"role": "user", "parts": [{"type": "text", "content": "Weather in Paris?"}]}, {"role": "assistant", "parts": [{"type": "tool_call", "id": "call_VSPygqKTWdrhaFErNvMV18Yl", "name":"get_weather", "arguments":{"location":"Paris"}}]}, {"role": "tool", "parts": [{"type": "tool_call_response", "id":" call_VSPygqKTWdrhaFErNvMV18Yl", "result":"rainy, 57 deg F"}]}]` | Opt-In |  |
| `gen_ai.output.messages` | Model output content [3] | string | `[{"role":"assistant","parts":[{"type":"text","content":"The weather in Paris is currently rainy with a temperature of 57 deg F."}],"finish_reason":"stop"}]` | Opt-In |  |
| `gen_ai.response.time_to_first_token` | Time to first token in streaming responses [4] | integer | `1000000` | Recommended | Alibaba Cloud extension |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In an Entry span the
value **must** be `ENTRY`.

**[2] `gen_ai.input.messages`**: records the input content of the LLM call. It
**must** follow the input-message JSON Schema, and messages **must** be supplied
in the order they were sent to the model or agent.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[3] `gen_ai.output.messages`**: records the model output content. It **must**
follow the output-message JSON Schema, and messages **must** be supplied in the
order they were sent to the model or agent.

Collected only when the `otel.instrumentation.genai.capture-message-content`
switch is enabled.

**[4] `gen_ai.response.time_to_first_token`**: the end-to-end time to first token
for one question, measured from the moment the server receives the user request
until the first packet is returned, in nanoseconds.

# ReAct Step

**Status: Development**

Step marks one Reasoning-Acting iteration of an Agent.

The span should be named `react step`; other naming formats are acceptable in
special cases.

**Note**: the OpenTelemetry community does not yet define a semantic convention
for this span type, so `gen_ai.operation.name` may still change.

## Attributes

| AttributeKey | Description | Type | Example | Requirement level | Notes |
| --- | --- | --- | --- | --- | --- |
| `gen_ai.span.kind` | Operation type [1] | string | `STEP` | Required | Alibaba Cloud extension |
| `gen_ai.operation.name` | Second-level operation type | string | `react` | Recommended |  |
| `gen_ai.react.finish_reason` | Why this ReAct round ended | string | `error` | Recommended | Alibaba Cloud extension |
| `gen_ai.react.round` | Round number of this ReAct iteration [2] | integer | `1` | Recommended | Alibaba Cloud extension |

**[1] `gen_ai.span.kind`**: a dedicated LLM spanKind enum. In a ReAct Step span
the value **must** be `STEP`.

**[2] `gen_ai.react.round`**: the ReAct round number should start at 1 and
increment by 1 on each iteration.
