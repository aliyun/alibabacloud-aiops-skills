---
name: alibabacloud-parse-x
description: >
  Alibaba Cloud Parse-X intelligent document parsing and extraction tool.
  Supports two capabilities: (1) Parse — convert documents, images, and
  audio/video to structured Markdown/JSON/HTML with layout, table, and
  synopsis support; (2) Extract — schema-driven information extraction with
  citations from parsed or new documents. Uses Parse-X HTTP (Spectrum gateway,
  Bearer token via DASHSCOPE_API_KEY).

  **When to use this skill** — the user asks to:
  - Parse / convert / analyze any document, image, spreadsheet, or media file
    (PDF, Word, PPT, Excel, Markdown, HTML, images, audio, video)
  - Extract structured fields or entities from a document
  - Convert files to Markdown or JSON format
  - Process files with mentions of: 解析, 文档解析, 文件解析, 表格, Excel,
    xlsx, xls, PDF, Word, PPT, 合同, 发票, 报告, 图片, 本地文件, 上传,
    markdown, JSON, 提取, 抽取, 字段, parse, extract, document parsing,
    parse file, 解析文档, 解析文件, 文件转换, 图片解析, 表格提取
---

# Parse-X Document Parsing & Extraction

## Two Capabilities

| Capability | Sub-command | Description |
|------------|-------------|-------------|
| **Parse**  | `parse`     | Convert documents / images / audio / video to structured output (Markdown, JSON, HTML, visual_layout_info) |
| **Extract**| `extract`   | Schema-driven information extraction with optional citations, reusing parse results or fresh files |

## Invocation Mode

**Parse-X HTTP (Spectrum gateway)**: Authenticate with `DASHSCOPE_API_KEY` Bearer token; simple HTTP calls, no SDK needed. Accepts file URLs or local file paths — local files are automatically uploaded via DashScope file service, parsed, then cleaned up.

Key headers: `X-DashScope-OssResourceResolve: enable` (parse/extract — resolves `oss://bailian` URIs internally), `X-DashScope-Inner-Include-Url: true` (file upload — returns `oss://bailian/{id}` URL).

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DASHSCOPE_API_KEY` | API key for Parse-X HTTP (Bearer token) | **Required** |
| `PARSE_X_ENDPOINT`  | Parse-X base URL (default: `https://dashscope.aliyuncs.com/api/v2/apps/pre-parse-x`) | Optional |
| `SKILL_SESSION_ID`  | Session identifier for User-Agent (auto-generated 32-char hex if unset) | Optional |

---

## Usage

```bash
python scripts/parse_x.py <command> <file_url_or_path> [options]
```

### Parse Examples

```bash
# Parse a document URL (PDF)
python scripts/parse_x.py parse https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf
# Parse a local file (auto-uploads via file service, parses, then cleans up)
python scripts/parse_x.py parse ./contract.pdf --output markdown
# Parse with AUTO enhancement, pages 1-5
python scripts/parse_x.py parse https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf \
  --enhancement AUTO --pages 1-5
# Parse with visual layout info and markdown tables
python scripts/parse_x.py parse https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf \
  --visual-layout --layout-table-format markdown --output markdown

# Parse headers and footers with image captions
python scripts/parse_x.py parse https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf \
  --head-foot --image-caption

# Parse audio/video with synopsis and diarization
python scripts/parse_x.py parse https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/Wan3.0模型创意视频.mp4 \
  --enable-synopsis --enable-diarization
```

### Extract Examples

```bash
# Extract structured fields from a document URL using an inline schema
python scripts/parse_x.py extract https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf \
  --extract-schema '{"type":"object","properties":{"buyer":{"type":"string"},"total_amount":{"type":"number"}}}'

# Extract using a schema JSON file
python scripts/parse_x.py extract https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf \
  --extract-schema ./schema.json --user-prompt "金额用小写，用财务规范书写"

# Extract from an already-parsed document (reuse parse biz_id, skip re-parsing)
python scripts/parse_x.py extract \
  --parsed-biz-id parse-x-20260901-xxxx \
  --extract-schema '{"type":"object","properties":{"contract_number":{"type":"string"}}}'

# Extract from a local file (auto-uploads, extracts, then cleans up)
python scripts/parse_x.py extract ./contract.pdf \
  --extract-schema ./schema.json --user-prompt "金额用小写，用财务规范书写"

# Allow inference and disable citations
python scripts/parse_x.py extract https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf \
  --extract-schema ./schema.json --allow-inference --no-citation
```

---

## Parse Parameters

| Parameter | CLI Flag | Type | Description |
|-----------|----------|------|-------------|
| `<file_url_or_path>` | positional | string | File URL or local file path (local files are auto-uploaded) |
| `processing.enhancement_mode` | `--enhancement` | `BASIC`/`ADVANCE`/`AUTO` | Enhancement mode |
| `processing.user_prompt` | `--user-prompt` | string | Custom prompt |
| `processing.doc_processing_config.page_index` | `--pages` | string | Page range, e.g. `1-5` |
| `processing.doc_processing_config.head_foot` | `--head-foot` | bool | Parse headers/footers |
| `processing.doc_processing_config.layout_position` | `--layout-position` | bool | Return bounding box coords |
| `processing.doc_processing_config.image_caption` | `--image-caption` | bool | Enable image descriptions |
| `processing.media_processing_config.enable_diarization` | `--enable-diarization` | bool | Speaker diarization (audio/video) |
| `processing.media_processing_config.enable_synopsis_parse` | `--enable-synopsis` | bool | Synopsis parse + segments + summary (audio/video) |
| `output.output_file_format` | `--output` | `markdown`/`json`/`html`/`visual_layout_info` | Output format |
| `output.layout_table_format` | `--layout-table-format` | `markdown`/`html` | Table format in markdown output |
| `output.layout_image_format` | `--layout-image-format` | `url` | Image output format |
| `output.visual_layout` | `--visual-layout` | bool | Include visual_layout_info in output |
| `config_id` | (not exposed) | string | Console config ID |
| `file_name_extension` | `--file-ext` | string | Override file extension |
| (endpoint) | `--endpoint` | string | Override Parse-X endpoint URL |
| (output file) | `--output-file` | string | Write output to file instead of stdout |

### Parse API Reference

**Submit**: `POST {endpoint}/parse/submit`

```json
{
  "file_url": "https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf",
  "file_name": "服务采购合同_扫描版.pdf",
  "processing": {
    "enhancement_mode": "AUTO",
    "user_prompt": "xxx",
    "doc_processing_config": {
      "page_index": "1-10",
      "head_foot": false,
      "layout_position": true,
      "image_caption": false
    },
    "media_processing_config": {
      "enable_diarization": true,
      "enable_synopsis_parse": true,
      "enable_synopsis_segments": true,
      "enable_synopsis_summary": true
    }
  },
  "output": {
    "output_file_format": ["markdown", "visual_layout_info"],
    "layout_table_format": "markdown",
    "layout_image_format": "url"
  },
  "notification": {
    "enable_event_callback": false
  }
}
```

**Query**: `POST {endpoint}/parse/result`

```json
{
  "biz_id": "parse-x-20260901-xxxx",
  "step_start": 0,
  "step_size": 100
}
```

Response fields: `status` (init/processing/success/fail), `processing` (progress %), `layouts` (document blocks), `segments` (audio/video), `synopsis_result`, `synopsis_segments`, `synopsis_summary`, `markdown_content`, `output_format_result`, `visual_layout_info`.

---

## Extract Parameters

| Parameter | CLI Flag | Type | Description |
|-----------|----------|------|-------------|
| `<file_url_or_path>` | positional | string | Document URL or local file path (optional if `--parsed-biz-id` given; local files auto-uploaded) |
| `--parsed-biz-id` | `--parsed-biz-id` | string | Reuse an existing parse result's biz_id |
| `--extract-schema` | `--extract-schema` | string | JSON schema (inline or file path) — **required** |
| `--user-prompt` | `--user-prompt` | string | Custom extraction prompt |
| `--no-citation` | `--no-citation` | bool | Disable citations in result |
| `--allow-inference` | `--allow-inference` | bool | Allow model inference for missing fields |
| `--output-file` | `--output-file` | string | Output file path |
| `file_name_extension` | `--file-ext` | string | Override file extension |
| (endpoint) | `--endpoint` | string | Override Parse-X endpoint URL |

### Extract API Reference

**Submit**: `POST {endpoint}/extract/submit`

```json
{
  "file_url": "https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf",
  "parsed_file_biz_id": "parse-x-20260901-xxxx",
  "processing": {
    "user_prompt": "金额用小写，用财务规范书写",
    "extract_processing_config": {
      "citation_required": true,
      "allow_inference": false,
      "extract_schema": "{\"type\":\"object\",\"properties\":{\"contract_number\":{\"type\":\"string\"},\"buyer\":{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\"}}},\"total_amount\":{\"type\":\"number\"}}}"
    }
  },
  "output": {},
  "notification": {
    "enable_event_callback": false
  }
}
```

> `file_url` and `parsed_file_biz_id` are mutually exclusive file sources. At least one is required.

**Query**: `POST {endpoint}/extract/result`

```json
{
  "biz_id": "parse-x-20260901-xxxx"
}
```

Response:
```json
{
  "data": {
    "status": "success",
    "page_count": 10,
    "extract_result_json": {
      "contract_number": "25462148",
      "buyer": { "name": "张三" },
      "total_amount": 144000
    },
    "fields": [
      {
        "path": "contract_number",
        "schema_type": "string",
        "status": "found",
        "value": "25462148",
        "citations": [
          { "citation_id": "cit_1", "quote": "合同编号：25462148", "page": 1, "bbox": [100, 100, 100, 100] }
        ]
      },
      {
        "path": "buyer.name",
        "schema_type": "string",
        "status": "inferred",
        "value": "张三",
        "citations": [
          { "citation_id": "cit_2", "quote": "姓名：张三", "page": 1, "bbox": [200, 200, 100, 100] }
        ]
      },
      {
        "path": "total_amount",
        "schema_type": "number",
        "status": "inferred",
        "value": 144000,
        "citations": [
          { "citation_id": "cit_a", "quote": "月服务费为人民币 12,000 元", "page": 1, "bbox": [400, 500, 100, 100] },
          { "citation_id": "cit_b", "quote": "服务期 12 个月", "page": 2, "bbox": [1200, 1200, 100, 100] }
        ],
        "reason": "Computed from monthly fee × service period"
      }
    ]
  },
  "request_id": "bdeea997-aa00-9d80-95e6-52789f1c546d"
}
```

---

## Workflow: Parse then Extract

A common pattern is to first parse a document, then run extraction on the parse result to avoid re-uploading:

```bash
# Step 1: Parse the document, note the biz_id from output
python scripts/parse_x.py parse https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf
# Step 2: Extract using the parse biz_id (faster, no re-upload)
python scripts/parse_x.py extract \
  --parsed-biz-id parse-x-20260901-xxxx \
  --extract-schema ./schema.json
```

---

## Agent Decision Protocol

**This section is critical — read before any action.** The Agent MUST follow this decision tree to avoid invalid calls and security violations.

### When to invoke this skill (Trigger)

Invoke `scripts/parse_x.py` when the user asks to:

| User Intent (Chinese) | User Intent (English) | Sub-command |
|------------------------|----------------------|-------------|
| 解析/分析/查看/读取 文档/PDF/Word/PPT/图片/音频/视频 | Parse / analyze / read any document or media | `parse` |
| 转换 文档/文件 为 Markdown/JSON/HTML | Convert files to structured format | `parse` |
| 提取/抽取 字段/信息/数据/内容 从文档 | Extract fields/data from documents | `extract` |
| 识别 表格/合同/发票 内容 | Recognize table, contract, invoice content | `extract` |
| 处理 本地文件 / 上传文件 解析 | Process local files for parsing | `parse` / `extract` |

### When NOT to invoke (Anti-trigger)

**Do NOT invoke `scripts/parse_x.py` in these situations:**

| Situation | Correct Behavior |
|-----------|-----------------|
| User wants to parse a **compressed archive** (.zip, .rar, .7z, .tar.gz, etc.) | Reject with "compressed archives are not supported" message — do **not** call parse_x.py |
| User provides **no file path or URL** (e.g., just "帮我解析文档") | Ask the user to provide the file path or URL — do **not** call parse_x.py |
| User asks to **read a text/code file** as context (e.g., ".md", ".py", ".json" as code reference) | Use local `read_file` — text/code files don't need document parsing |
| User asks to **create/edit/write** a file | Use local file tools — this is not document parsing |
| User's intent is **unclear** about what file to parse | Ask clarifying questions first |

### Security: Forbidden behaviors

| Forbidden | Severity |
|-----------|----------|
| **NEVER** expose `DASHSCOPE_API_KEY`, `AccessKey`, or any credentials in commands, scripts, or final answers | CRITICAL |
| **NEVER** fabricate a file path or URL when the user hasn't provided one | CRITICAL |
| **NEVER** call parse_x.py with a non-existent local file path | HIGH |
| **NEVER** skip required parameters (e.g., `--pages` when page range is specified, `--head-foot` when headers/footers are requested) | HIGH |

### Decision Flow

```
User requests document processing
  ├─ Is it a compressed archive (.zip/.rar/.7z/.tar.gz)?
  │   └─ YES → Reject with "format not supported" message. STOP.
  ├─ Has user provided a file path or URL?
  │   └─ NO → Ask user to provide the file. STOP.
  ├─ Is it a text/config/code file needing READ (not PARSE)?
  │   └─ YES → Use local read_file tool. STOP.
  ├─ Is the intent EXTRACTION of structured fields?
  │   └─ YES → invoke parse_x.py extract
  └─ Default → invoke parse_x.py parse
```

---

## Quota

| Mode | Free Quota | After Exhaustion |
|------|------------|------------------|
| Parse-X HTTP | Limited daily quota | Prompt to activate Alibaba Cloud Parse-X service |

When quota is exhausted, prompt the user to visit https://dashscope.console.aliyun.com to activate the service.

---

## Error Handling

| Error Code | HTTP | Meaning | Resolution |
|------------|------|---------|------------|
| `NotExistBizId` | 400 | biz_id not found | Verify the biz_id is correct |
| `ResultNotReady` | 409 | Task not yet complete | Continue polling |
| `FileDownloadFailed` | 400 | File download failed | Verify URL is accessible |
| `FileFormatNotSupported` | 400 | Unsupported format | Show supported formats |
| `FileSizeExceeded` | 400 | File too large | Reduce file size or split |
| `InvalidFileUrl` | 400 | URL invalid or inaccessible | Provide a public URL |
| `InvalidSchema` | 400 | Schema format invalid | Validate the JSON schema |
| `PageCountExceeded` | 400 | Too many pages | Reduce page range |
| `ProcessingFailed` | 500 | Internal engine error | Retry |
| `ServiceQuotaExhausted` | 503 | Quota exhausted | Activate Alibaba Cloud service |
| `ParseResultExpired` | 400 | Parse result > 30 days old | Re-parse the document |
| `ParseResultNotReusable` | 400 | Parse result not reusable for extract | Re-parse with correct type |
| `UnsupportedFileType` | 400 | Extract doesn't support audio/video | Use document input for extract |
| `AccountOverdue` | 403 | Account overdue | Top up account |

### Pre-validation

**Before invoking the script, the Agent MUST:**

1. **Verify file URLs are publicly accessible** before parse/extract (skip for local file paths — the script handles upload automatically).
2. For **extract with --parsed-biz-id**: ensure the biz_id is from a successful parse within 30 days and the input type is a document (not audio/video).

### Local File Flow

When a local file path is provided, the script automatically:
1. Uploads the file via DashScope file service (`POST /compatible-mode/v1/files`, purpose=`data`, with `X-DashScope-Inner-Include-Url: true`)
2. Constructs `oss://bailian/{file-id}` as the file URL — Parse-X resolves this internally via `X-DashScope-OssResourceResolve: enable`
3. Submits the parse/extract task
4. Deletes the uploaded file after processing (`DELETE /compatible-mode/v1/files/{file-id}`)

---

## Supported File Formats

- **Documents**: PDF, Word (doc/docx), PPT (ppt/pptx), Excel (xls/xlsx/xlsm)
- **Images**: JPG, JPEG, PNG, BMP, GIF
- **Other**: Markdown, HTML, EPUB, MOBI, RTF, TXT
- **Audio/Video** (parse only, not extract): MP4, MKV, AVI, MOV, WMV, MP3, WAV, AAC

---

## Output Formats

### Parse Output
- **Markdown**: Downloaded from `output_format_result` signed URL when available; otherwise constructed from `layouts` — layout blocks' `markdownContent` concatenated; tables embedded per `layout_table_format`.
- **JSON**: Raw response data serialized, with `markdown_content` downloaded from `output_format_result` URL if available.
- **HTML**: Downloaded from `output_format_result` signed URL when available; otherwise raw response.
- **visual_layout_info**: Layout bounding box and structure information (JSON string).

### Extract Output
- **JSON** (default): `extract_result_json` (structured data) + `fields` array with `path`, `value`, `status`, `citations`, and optional `reason`.
- **Markdown** (rendered): Human-readable field table with citations.

---

## Observability

All outbound HTTP requests set the `User-Agent` header following the SDK pattern. Session ID and skill version are read from environment variables before each cloud call:

```
AlibabaCloud-Agent-Skills/alibabacloud-parse-x/{session-id} skill-version/{version}
```

| Component | Value |
|-----------|-------|
| UA template | `AlibabaCloud-Agent-Skills/alibabacloud-parse-x/{session-id} skill-version/{version}` |
| session-id source | `SKILL_SESSION_ID` env var; fallback: freshly generated 32-char lowercase hex |
| version source | `references/manifest.json` (currently `1.0.0`); fallback: `0.0.0` |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | `>=2.20.0` | HTTP client for Parse-X API calls and file service operations |

Install via pip:

```bash
pip install requests>=2.20.0
```

---

## Local Development

### 1. Configure Environment Variables

Copy the example file and fill in real values:

```bash
cp .env.example .env
```

Edit `.env` with your DashScope API Key:

```env
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
# Optional: custom endpoint
# PARSE_X_ENDPOINT=https://dashscope.aliyuncs.com/api/v2/apps/pre-parse-x
```

Load environment variables:

```bash
# macOS / Linux
source .env
# or
export $(cat .env | xargs)
```

### 2. Verify the Script

```bash
# Test with a sample URL (no upload needed)
python scripts/parse_x.py parse https://docmind-api-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/static/服务采购合同_扫描版.pdf
# Test with a local file (auto upload → parse → cleanup)
python scripts/parse_x.py parse ./SKILL.md --output markdown
```

### 3. Run Evaluation Scenarios

Test cases are located in `evals/scenarios/`, organized by type:

| Directory | Description |
|-----------|-------------|
| `autoGenerated/` | Functional scenario tests (parsing various file types, field extraction, error handling, etc.) |
| `triggering/` | Trigger detection tests (should/should not trigger the parse-x skill) |

Each `.jsonc` file represents a test scenario containing:
- `prompt` — Simulated user input
- `param_kv` — Expected parameters passed to the script
- `expectations` — Expected cloud interactions and output validation
- `forbidden` — Forbidden behaviors
How to run:
```bash
# Run the script directly to verify a single scenario
python scripts/parse_x.py parse ./SKILL.md --output markdown

# Trigger scenarios: feed the testcase prompt to the Agent and observe whether it correctly identifies and invokes this skill
# should_trigger.jsonc  — Agent is expected to invoke parse-x
# should_not_trigger.jsonc — Agent is expected NOT to invoke parse-x
```
