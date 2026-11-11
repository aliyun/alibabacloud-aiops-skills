# Alibaba Cloud Flink SQL AI Function Knowledge Base

This document summarizes the official Alibaba Cloud Realtime Compute for Apache Flink documentation. It covers 10 core inference, text, and vector functions, along with model management, embedding caches, major multimodal operations, and file helpers. All version numbers refer to **VVR engine versions**, not Apache Flink community versions. Entry point: [SQL AI functions](https://help.aliyun.com/zh/flink/realtime-flink/ai-function/).

Syntax conventions: code containing optional sections in square brackets, `...`, or placeholder names illustrates the call structure and must be completed before use. The customer-service ticket example provides concrete model declarations and input data, but has not been validated through cloud execution.

## 1. Capabilities and Prerequisites

| Requirement | Capability | Official entry point |
| --- | --- | --- |
| General model inference, image understanding, and multimodal input | `ML_PREDICT` | [General inference](https://help.aliyun.com/zh/flink/realtime-flink/ml-predict) |
| Classification, sentiment, extraction, summarization, translation, and masking | `AI_CLASSIFY`, `AI_SENTIMENT`, `AI_EXTRACT`, `AI_SUMMARIZE`, `AI_TRANSLATE`, `AI_MASK` | [Text functions](https://help.aliyun.com/zh/flink/realtime-flink/text-type/) |
| Text embeddings and similar-record retrieval | `AI_EMBED`, `VECTOR_SEARCH`, `VECTOR_SEARCH_AGG` | [Vector functions](https://help.aliyun.com/zh/flink/realtime-flink/vector-class/) |
| Image, audio, and video processing | Multimodal functions in the Python Module | [Python multimodal function library](https://help.aliyun.com/zh/flink/realtime-flink/python-module) |
| File downloads and file-type identification by extension | `FETCH_CONTENT`, `TRY_FETCH_CONTENT`, `MIME_TYPE` | [Multimodal data-processing functions](https://help.aliyun.com/zh/flink/realtime-flink/multimodal-data-processing-function/) |

**Function availability and the version required by the built-in model service are separate conditions.** For example, some text functions are available from VVR 11.4, but calling built-in models through Flink AI Service requires VVR 11.7 or later and service activation in the corresponding region. Individual functions and additional parameters must also meet the requirements below. [AI_CLASSIFY restrictions](https://help.aliyun.com/zh/flink/realtime-flink/ai-classify)

Flink AI Service is activated per region and becomes available to workspaces in that region. Managed built-in models do not require users to configure a model-service API-Key, Endpoint, or private-network connection. Do not extend this convenience to authentication for all external model services. [Flink AI Service](https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service)

## 2. Model Registration and Management

`MODEL` defines model input, output, and invocation settings. Confirm the output type required by the calling function before registering a model. Text-task functions and general inference need not use the same model output declaration. For managed built-in models, `provider`, `task`, and `model` in `WITH` select the service and task. [Model configuration](https://help.aliyun.com/zh/flink/realtime-flink/model-ddl)

| Setting | Meaning |
| --- | --- |
| `provider` | The documentation lists `openai-compat`, `dashscope`, and `triton`; `dashscope` is recommended for multimodal tasks, while Triton follows its separate integration guide |
| `task` | The current model-configuration documentation lists `chat/completions`, `embeddings`, and `multimodal-embedding` |
| `model` | Server-side model name, which must match the task |
| `system-prompt`, `user-prompt` | System and user prompts |
| `response-format` | Text-generation response format: `text` or `json_object` |
| `dimension` | Embedding dimension, subject to model support |
| `error-handling-strategy` | Defaults to `retry`; alternatives are `failover`, which raises an exception, and `ignore`, which skips the record |

Illustrative model-management statements:

```sql
SHOW MODELS;
SHOW CREATE MODEL ticket_llm;
DESCRIBE MODEL ticket_llm;
ALTER MODEL ticket_llm SET ('system-prompt' = 'Process the input according to business requirements');
ALTER MODEL ticket_llm RESET ('system-prompt');
DROP MODEL ticket_llm;
```

Create models with `CREATE MODEL` or `CREATE TEMPORARY MODEL`; remove temporary models with `DROP TEMPORARY MODEL`. See [model configuration](https://help.aliyun.com/zh/flink/realtime-flink/model-ddl) for complete parameter definitions and DDL syntax.

## 3. General Inference: ML_PREDICT

A registered model processes an input table and returns the input columns together with the model's declared output columns. Basic support requires VVR 11.1 or later; managed built-in models additionally require VVR 11.7 or later. [General inference](https://help.aliyun.com/zh/flink/realtime-flink/ml-predict)

```sql
ML_PREDICT(
  TABLE source_table,
  MODEL inference_model,
  DESCRIPTOR(input_column)
  [, CONFIG => MAP[...]]
)
```

This is a syntax illustration. Square brackets mark an optional section; it cannot be copied directly as complete SQL.

| Capability or parameter | Requirement |
| --- | --- |
| Multiple columns in `DESCRIPTOR`, call-level `CONFIG` | VVR 11.8+ and managed built-in models |
| `image_bytes`, `multi_image_bytes`, `video_bytes`, `video_url` | Managed built-in models, VVR 11.9+; column types are respectively `BYTES`, `ARRAY<BYTES>`, `BYTES`, and `STRING` |
| `bundle-size`, `bundle-allow-latency` | Call-level settings for managed built-in models; bundle processing requires VVR 11.9+ |

Call-level parameters override model settings for that invocation without persistently modifying the model. For multi-column input, separate `content-types` entries with semicolons. Their count must match both the `DESCRIPTOR` column count and the model's `INPUT` column count. `content-type` and `content-types` are mutually exclusive. `image_url` uses `STRING`, while `multi_image_urls` uses `ARRAY<STRING>`. Base64 images require the `data:image/<format>;base64,` prefix; raw Base64 or local paths cannot replace image-URL input. [Parameters and content types](https://help.aliyun.com/zh/flink/realtime-flink/ml-predict)

## 4. Text-Task Functions

All six functions below are available from **VVR 11.4**; managed built-in models additionally require **VVR 11.7+**. Input text is `STRING`, and the referenced model must declare its output as **`VARIANT`**. This is the model output declaration; the function's SQL result fields still use the concrete types below. The linked official pages describe each function's version and type requirements.

| Function | Purpose | Parameters besides `MODEL` and `INPUT` | SQL result fields |
| --- | --- | --- | --- |
| [AI_CLASSIFY](https://help.aliyun.com/zh/flink/realtime-flink/ai-classify) | Classify text using candidate labels | `LABELS`: constant `ARRAY<STRING>` | `category STRING`, `confidence DOUBLE` |
| [AI_SENTIMENT](https://help.aliyun.com/zh/flink/realtime-flink/ai-sentiment) | Analyze text sentiment | None | `score DOUBLE`, `label STRING`, `confidence DOUBLE` |
| [AI_EXTRACT](https://help.aliyun.com/zh/flink/realtime-flink/ai-extract) | Extract structured information | `EXTRACT_SCHEMA`: constant `STRING` describing the schema in JSON | `extracted_json STRING` |
| [AI_SUMMARIZE](https://help.aliyun.com/zh/flink/realtime-flink/ai-summarize) | Generate a summary | `MAX_LENGTH`: constant `INTEGER` specifying maximum length | `summary STRING` |
| [AI_TRANSLATE](https://help.aliyun.com/zh/flink/realtime-flink/ai-translate) | Translate text | `SOURCE_LANG`, `TARGET_LANG`: constant `STRING` values | `translated_text STRING`, `detected_language STRING` |
| [AI_MASK](https://help.aliyun.com/zh/flink/realtime-flink/ai-mask) | Mask specified sensitive entities | `MASK_ENTITIES`: constant `ARRAY<STRING>` | `masked_text STRING`, `detected_entities ARRAY<STRING>` |

Important semantic details:

- `AI_SENTIMENT.score` ranges from `[-1.0, 1.0]`, with labels `positive`, `negative`, and `neutral`. [Sentiment analysis](https://help.aliyun.com/zh/flink/realtime-flink/ai-sentiment)
- `AI_EXTRACT` returns a JSON **string**. Parse it when separate fields are needed; the return value is not an expanded `ROW`. [Information extraction](https://help.aliyun.com/zh/flink/realtime-flink/ai-extract)
- The `AI_SUMMARIZE` documentation specifies only a "maximum length" without identifying characters, words, or tokens as the unit. This document does not add such a definition. [Text summarization](https://help.aliyun.com/zh/flink/realtime-flink/ai-summarize)
- `AI_TRANSLATE` permits `auto` as the source language. Documented languages include `zh`, `en`, `ja`, `ko`, `fr`, `de`, `es`, `ru`, `ar`, and `pt`; actual support depends on the model. [Text translation](https://help.aliyun.com/zh/flink/realtime-flink/ai-translate)

Results are typically expanded through `LATERAL TABLE`. This customer-service ticket classification example illustrates the relationship between a model declaration and a function call. The model name comes from the official example reviewed for this document. Validate execution in a target environment where the service is activated; this example has not been executed in the cloud. [AI_CLASSIFY example](https://help.aliyun.com/zh/flink/realtime-flink/ai-classify)

```sql
CREATE TEMPORARY MODEL ticket_llm
INPUT (message STRING)
OUTPUT (content VARIANT)
WITH (
  'provider' = 'openai-compat',
  'task' = 'chat/completions',
  'model' = 'qwen3.6-flash'
);

CREATE TEMPORARY VIEW ticket_messages(ticket_id, message) AS
VALUES (1001, 'My delivery is two days late. Please check the shipping status.');

SELECT ticket_id, category, confidence
FROM ticket_messages,
LATERAL TABLE(
  AI_CLASSIFY(
    MODEL => MODEL ticket_llm,
    INPUT => message,
    LABELS => ARRAY['Shipping issues', 'After-sales requests', 'Product inquiries']
  )
);
```

Model-invocation throughput is constrained by the model platform's rate limits. Reaching those limits can cause backpressure and, in severe cases, timeouts or Job restarts. Check model-platform rate limiting when investigating throughput. [AI_CLASSIFY restrictions](https://help.aliyun.com/zh/flink/realtime-flink/ai-classify)

## 5. Embedding Generation, Caching, and Retrieval

### 5.1 AI_EMBED: Text Embeddings

Input is `STRING`, and the referenced model must declare its output as `ARRAY<FLOAT>`. The function returns `embedding ARRAY<FLOAT>`. Basic support requires VVR 11.4+; managed built-in models require VVR 11.7+. [AI_EMBED](https://help.aliyun.com/zh/flink/realtime-flink/ai-embed)

```sql
AI_EMBED(
  MODEL => MODEL embedding_model,
  INPUT => text_column
  [, DIMENSION => dimension_value]
)
```

`DIMENSION` defaults to **1024**, and the call argument takes precedence over the model's registered dimension setting. The model must support that dimension. Even when the argument is omitted, `AI_EMBED` passes the default dimension to the model. If the model does not accept a dimension parameter, the official recommendation is to use `ML_PREDICT`. Expand `embedding` through `LATERAL TABLE` as needed. [Dimension parameter](https://help.aliyun.com/zh/flink/realtime-flink/ai-embed)

### 5.2 Embedding Result Cache

From **VVR 11.8.preview1**, `AI_EMBED` can use a **Fluss primary key table** as a persistent cache through `CACHE_TABLE`. A hit returns the cached vector and skips the model call. A miss invokes the model, returns the result, and writes it back asynchronously. [Embedding result cache](https://help.aliyun.com/zh/flink/realtime-flink/vectorization-result-cache)

Additional function arguments:

```sql
CACHE_TABLE => TABLE cache_catalog.cache_db.embedding_cache,
CACHE_KEY => DESCRIPTOR(cache_key)
```

This is an `AI_EMBED` argument fragment. An explicit key must have a type compatible with the cache-table primary key, and the vector column is `ARRAY<FLOAT>`. When `CACHE_KEY` is omitted, the system generates a SHA256 key from the model identifier, dimension, and input text; the cache-table primary key then uses `STRING`. [Cache table and key](https://help.aliyun.com/zh/flink/realtime-flink/vectorization-result-cache)

Runtime settings use the `table.exec.async-ml-predict.` prefix:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `max-concurrent-operations` | `10` | Maximum number of records concurrently looking up the cache or invoking the model |
| `output-mode` | `ORDERED` | Preserve input order; `ALLOW_UNORDERED` applies only to INSERT-only streams, while Retract streams fall back to `ORDERED` |
| `timeout` | `3min` | Total timeout for the cache Lookup and model call |

With ordered output, an earlier cache miss may block later cache hits. Use Metrics such as `ai_function_cache.cache_hit` and `ai_function_cache.cache_miss` to assess cache effectiveness. [Tuning and monitoring](https://help.aliyun.com/zh/flink/realtime-flink/vectorization-result-cache)

### 5.3 VECTOR_SEARCH and VECTOR_SEARCH_AGG

Both functions use an input vector to query an external vector table. `TOP_K` is the **maximum number** of matches returned. The query vector is `ARRAY<FLOAT>` or `ARRAY<DOUBLE>`, and only INSERT-only input streams are supported. [VECTOR_SEARCH](https://help.aliyun.com/zh/flink/realtime-flink/vector-search), [VECTOR_SEARCH_AGG](https://help.aliyun.com/zh/flink/realtime-flink/vector-search-agg)

| Aspect | VECTOR_SEARCH | VECTOR_SEARCH_AGG |
| --- | --- | --- |
| Result shape | One row per match | One row per query; `search_results` is an array of matching `ROW` values |
| Search backend | Milvus; DLF Paimon requires VVR 11.8+ | The current page lists only Milvus |
| Streaming version | VVR 11.3+ | VVR 11.3+ |
| Batch version | **Conflicting official statements; see below** | The page explicitly lists VVR 11.4+ |
| Result-column pruning | `OUTPUT_COLUMNS`, VVR 11.9+ | `OUTPUT_COLUMNS`, VVR 11.9+ |

`VECTOR_SEARCH_AGG` aggregates the matches of one vector query, rather than performing a regular `GROUP BY` aggregation across the entire input stream. [Aggregated vector search](https://help.aliyun.com/zh/flink/realtime-flink/vector-search-agg)

The shared argument structure is shown below; substitute the required function name:

```sql
VECTOR_SEARCH(
  SEARCH_TABLE => TABLE vector_table,
  COLUMN_TO_SEARCH => DESCRIPTOR(indexed_vector),
  COLUMN_TO_QUERY => query_vector,
  TOP_K => 5
  [, CONFIG => MAP[...]]
  [, OUTPUT_COLUMNS => DESCRIPTOR(result_column, score)]
)
```

By default, all vector-table fields and an engine-generated `score DOUBLE` are returned. `OUTPUT_COLUMNS` can select only top-level fields and the generated score column. It cannot be empty, contain duplicates, or reference nested fields. If the vector table already has a `score` column, the generated column may receive a unique name such as `score0`; use the actual name. [Result fields](https://help.aliyun.com/zh/flink/realtime-flink/vector-search)

Asynchronous runtime parameters include `async`, `max-concurrent-operations` (default `10`), `output-mode` (default `ORDERED`), and `timeout` (default `3min`). Execution mode must be supported by the Connector. When it is not explicitly specified, the engine chooses the mode and prefers asynchronous execution if the Connector supports both. [Runtime parameters](https://help.aliyun.com/zh/flink/realtime-flink/vector-search-agg)

**Documentation conflict:** the `VECTOR_SEARCH` restrictions state both that batch mode is supported from version 11.4 and that batch mode is currently unsupported. This document therefore does not treat batch support as confirmed. For batch Jobs, confirm the target version's capability with the official provider. [Page containing the conflict](https://help.aliyun.com/zh/flink/realtime-flink/vector-search)

## 6. Python Multimodal Function Library

### 6.1 Loading and Parameter Rules

The Python Module requires **VVR 11.8+**. Once loaded in a Job, its built-in functions can be called directly without writing and registering individual Python UDFs. [Python multimodal function library](https://help.aliyun.com/zh/flink/realtime-flink/python-module)

```sql
LOAD MODULE python;
USE MODULES python, core;
```

Module functions use **positional arguments**. Configuration arguments such as formats, dimensions, thresholds, and model names must be constants. When a function specifically requires SQL literals, fields or `CAST` expressions cannot substitute for them. To set a later optional argument, specify the preceding arguments. Explicit `NULL` is not equivalent to omission; the argument's definition determines whether default behavior applies. [Module parameter conventions](https://help.aliyun.com/zh/flink/realtime-flink/python-module), [image-function calling rules](https://help.aliyun.com/zh/flink/realtime-flink/image-function-overview)

### 6.2 Image Data Representations

| Representation | SQL type | Purpose |
| --- | --- | --- |
| Encoded image | `BYTES` | Store or transfer file bytes such as JPEG or PNG |
| Decoded image | `IMAGE` | Pass pixels and image metadata between image functions |
| Data URL | `STRING` | Represent an image as `data:image/...;base64,...` |

Most image-processing functions accept `IMAGE`. For encoded-byte input, typically decode with `IMAGE_DECODE`, process the image, and then encode with `IMAGE_ENCODE` as required downstream. `IMAGE` does not preserve original-file metadata such as EXIF or ICC. Using `CAST` to convert it to `STRING` returns only a metadata summary, not the image contents. [Image-function overview](https://help.aliyun.com/zh/flink/realtime-flink/image-function-overview)

### 6.3 Image Detection, Recognition, and Embeddings

| Function | Capability and result | Current restrictions |
| --- | --- | --- |
| `IMAGE_DETECT_OBJECTS` | YOLO object detection; returns an array of classes, bounding-box coordinates, and confidence values | Only the default `yolov8n` model is currently supported |
| `IMAGE_SEGMENT` | FastSAM segmentation; returns a PNG-encoded mask as `BYTES` | Only the default `FastSAM-x.pt` model is currently supported |
| `IMAGE_OCR` | Returns an array of text regions, confidence values, and boundary coordinates | The current built-in model supports only English; use general model inference for multiple languages as described in the official guide |
| `IMAGE_DETECT_SUBPLOT` | Returns `ROW<is_subplot BOOLEAN, count INT>` | The subplot count is an estimate |

These functions accept `IMAGE` input. See [image detection and recognition](https://help.aliyun.com/zh/flink/realtime-flink/image-detection-and-recognition) for parameters, result structures, and model restrictions.

| Function | Result | Current restrictions |
| --- | --- | --- |
| `IMAGE_EMBEDDING` | `ARRAY<FLOAT>`, a CLIP image embedding | Defaults to `ViT-B/32` and `openai`; only the default architecture and weights are currently supported, and the documented default model typically returns 512 dimensions |
| `IMAGE_TEXT_SIMILARITY` | `DOUBLE`, CLIP image-text cosine similarity, typically in `[-1, 1]` | Text must be a string constant; per-row text columns are unsupported |

The model determines the dimension of `IMAGE_EMBEDDING`; do not apply the default 1024 dimensions of `AI_EMBED` to it. [Image embeddings and similarity](https://help.aliyun.com/zh/flink/realtime-flink/image-vectors-and-similarity)

For resizing, cropping, background processing, face processing, quality scoring, PDF-to-image conversion, and other capabilities, follow the parameter and version requirements of the relevant functions in the [image-function catalog](https://help.aliyun.com/zh/flink/realtime-flink/image-function/).

### 6.4 Audio Processing

| Function | Purpose |
| --- | --- |
| `AUDIO_DECODE` | Decode encoded bytes, a URI, or a segment reference into a float32 PCM waveform `ROW` |
| `AUDIO_ENCODE` | Encode waveforms as bytes in WAV, FLAC, AIFF, MP3, OGG, or other formats; actual format support depends on the runtime environment |
| `AUDIO_CONVERT_FORMAT` | Decode, then re-encode in the target format |
| `AUDIO_STANDARDIZE` | Convert channels, then resample |
| `AUDIO_RESAMPLE` | Change the sample rate while preserving the channel count |
| `AUDIO_CONCAT` | Concatenate audio in array order; sample rate, channel count, and sample format must match |

The SQL default `on_error` for `AUDIO_DECODE` is `'null'`, but it handles only the media-data errors listed in the documentation. URI access, argument, or dependency errors may still raise exceptions; not every failure returns NULL. [Audio decoding, encoding, and transformation](https://help.aliyun.com/zh/flink/realtime-flink/audio-codec-transform)

### 6.5 Video Processing

| Function | Call form | Purpose and result |
| --- | --- | --- |
| `VIDEO_METADATA` | Scalar function | Accepts a video URI and returns a metadata `ROW` with resolution, frame rate, duration, and other fields |
| `VIDEO_SPLIT` | Table-valued function through `LATERAL TABLE` | Returns video-segment references without copying video contents |
| `VIDEO_EXTRACT_FRAMES` | Scalar function | Collects extracted frames as an `ARRAY<IMAGE>` in one row |
| `VIDEO_EXPLODE_FRAMES` | Table-valued function through `LATERAL TABLE` | Emits an image and frame metadata per frame |

Segment references contain `uri`, `start_time_ms`, and `end_time_ms`, with times in milliseconds. Only `VIDEO_METADATA` is restricted to URI input; the other three functions also accept segment references. For long videos or large numbers of extracted frames, the official recommendation is `VIDEO_EXPLODE_FRAMES` to avoid retaining too many images in one row. [Video functions](https://help.aliyun.com/zh/flink/realtime-flink/video-function)

## 7. File Helper Functions

These three functions have separate version requirements. Do not apply the Python Module's VVR 11.8+ requirement to all of them.

| Function | Minimum version as documented | Input and result | Failure or special-input behavior |
| --- | --- | --- | --- |
| [FETCH_CONTENT](https://help.aliyun.com/zh/flink/realtime-flink/fetch-content-try-fetch-content) | VVR 11.7.0 | URI `VARCHAR` → file contents `VARBINARY` | Raises an exception after download failure and exhausted retries; returns NULL for a NULL URI |
| [TRY_FETCH_CONTENT](https://help.aliyun.com/zh/flink/realtime-flink/fetch-content-try-fetch-content) | VVR 11.9.0-preview.1 | URI `VARCHAR` → file contents `VARBINARY` | Returns NULL after a runtime download failure and exhausted retries; returns NULL for a NULL URI |
| [MIME_TYPE](https://help.aliyun.com/zh/flink/realtime-flink/mime-type) | VVR 11.6.0 | URI `VARCHAR` → MIME type `VARCHAR` | Returns `application/other` for an unknown extension; returns NULL for a NULL URI |

Download functions support HTTP/HTTPS and URIs supported by Flink FileSystem, such as OSS, HDFS, and `file://`. OSS requires corresponding authentication configuration. The optional `concurrency` parameter is the **size of the dedicated I/O thread pool per function instance**, defaulting to `max(8, processors available to the current JVM)`. It is not Job parallelism or model-call concurrency. The number of asynchronous in-flight records is controlled separately by `table.exec.async-scalar.max-concurrent-operations`. `TRY_FETCH_CONTENT` does not tolerate SQL validation errors such as incorrect argument counts or types. [File downloads](https://help.aliyun.com/zh/flink/realtime-flink/fetch-content-try-fetch-content)

`MIME_TYPE` **determines type from the extension** rather than inspecting file contents to detect the actual format. The current page lists BMP, JPEG, PNG, TIFF, WEBP, HEIC, and PDF; this does not establish support for identifying arbitrary audio or video formats. [Type identification](https://help.aliyun.com/zh/flink/realtime-flink/mime-type)

## 8. Usage and Troubleshooting Index

| Question to resolve | Reference |
| --- | --- |
| General inference or a text task with fixed result fields? | Sections 3 and 4; confirm model output declarations and function result fields |
| Do the model and function support the target engine version? | Version requirements in each section; check additional parameters separately |
| One row per search result or one result array? | Section 5.3; choose `VECTOR_SEARCH` or `VECTOR_SEARCH_AGG` accordingly |
| Repeated embedding calls or ineffective caching? | Section 5.2; inspect the cache table, keys, and hit Metrics |
| Multimodal function argument validation fails? | Section 6; check module loading, positional arguments, literals, and data representations |
| Stop or continue after a file download fails? | Section 7; distinguish `FETCH_CONTENT` from `TRY_FETCH_CONTENT` |

This summary of official documentation does not replace SQL validation against the specific engine version. When an official page contains conflicting or undefined details, leave them unconfirmed rather than presenting an inference as a function guarantee. Model availability and service regions can change; consult the latest [Flink AI Service documentation](https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service) when using the service.
