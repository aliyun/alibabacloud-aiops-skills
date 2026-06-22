---
name: alibabacloud-docmind-parse
description: >
  Alibaba Cloud DocMind intelligent document parsing tool. Supports PDF, Word, PPT, Excel,
  images and more, outputting structured Markdown/JSON/HTML. Offers two invocation modes —
  V2 API direct access and Alibaba Cloud POP — with automatic routing based on credential
  availability. Use when the user needs to parse documents, extract content (text/tables/images),
  convert documents to Markdown, or mentions "docmind", "document parsing", "parse file", etc.
---

# DocMind Document Parsing

## Two Invocation Modes

1. **Free Mode (V2 API Direct)**: Configure the endpoint via the `DOCMIND_V2_ENDPOINT` environment variable; limited daily free quota.
2. **Alibaba Cloud POP Mode**: Credentials are obtained automatically through the default credential chain; 3,000 pages per month free, pay-as-you-go beyond that.

### Routing Strategy

- When the Alibaba Cloud default credential chain is available, prefer **POP Mode**.
- When credentials are unavailable but `DOCMIND_V2_ENDPOINT` is configured, use **V2 Free Mode**.
- When the free quota is exhausted, prompt the user to activate the Alibaba Cloud DocMind service.

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DOCMIND_V2_ENDPOINT` | V2 API service endpoint (domain or IP). Defaults to `docmind.aliyuncs.com` | Optional |

POP Mode automatically obtains credentials through the Alibaba Cloud default credential chain (environment variables, config files, ECS RAM roles, etc.) — no manual management needed.

---

## Usage

```bash
python scripts/docmind_parse.py <file_path_or_url> [options]
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `<file_path_or_url>` | Local file path or file URL | Required |
| `--mode` | Invocation mode: `auto`, `v2`, `pop` | `auto` |
| `--enhancement` | Enhancement mode: `VLM`, `LLM`, `DIGITAL`, `OCR`, `AUTO` | None |
| `--output` | Output format: `markdown`, `json`, `html` | `markdown` |
| `--pages` | Page range to parse, e.g. `1-5` | All |
| `--output-file` | Output file path | Stdout |
| `--head-foot` | Parse headers and footers | Off |
| `--user-prompt` | Custom user prompt | None |
| `--option` | Document parsing options | None |
| `--markdown-table` | Table output format: `html`, `markdown` | None |
| `--markdown-image` | Image output format: `html`, `markdown` | None |
| `--file-ext` | File extension (alternative to fileName) | Auto-detected |

### Examples

```bash
# Parse a URL (auto-select mode)
python scripts/docmind_parse.py https://example.com/doc.pdf

# Parse with VLM enhancement
python scripts/docmind_parse.py https://example.com/doc.pdf --enhancement VLM

# Parse the first 5 pages, output to a Markdown file
python scripts/docmind_parse.py ./report.pdf --pages 1-5 --output-file result.md

# Parse a local file via V2 mode (auto base64 encoding)
python scripts/docmind_parse.py ./contract.pdf --mode v2

# Parse with custom table/image output formats
python scripts/docmind_parse.py https://example.com/doc.pdf --markdown-table markdown --markdown-image html

# Parse headers and footers with a custom prompt
python scripts/docmind_parse.py https://example.com/doc.pdf --head-foot --user-prompt "Extract all footnotes"

# Force Alibaba Cloud POP mode
python scripts/docmind_parse.py ./contract.pdf --mode pop
```

---

## V2 API Direct Access (Free Mode)

Supports both URL and local file (base64) upload. The request body is organized into four blocks: Document, Processing, Output, and Notification.

### Submit Endpoint

`POST {DOCMIND_V2_ENDPOINT}/skill/submit`

Full request schema:

```json
{
  "document": {
    "fileUrl": "https://example.com/doc.pdf",
    "fileBase64": "<base64-encoded file content, alternative to fileUrl>",
    "fileName": "doc.pdf",
    "fileNameExtension": "pdf"
  },
  "processing": {
    "enhancementMode": "VLM",
    "pageIndex": "1-5",
    "headFoot": false,
    "userPrompt": "Custom prompt",
    "option": "parsing-option"
  },
  "output": {
    "outputFormat": ["markdown"],
    "markdownTable": ["html"],
    "markdownImage": ["html"],
    "docExtraParameters": {"key": "value"},
    "extraParameters": "audio-video-extra-params",
    "ossConfig": {
      "bucket": "my-bucket",
      "endpoint": "oss-cn-hangzhou.aliyuncs.com",
      "accessKeyId": "...",
      "accessKeySecret": "...",
      "securityToken": "..."
    }
  },
  "notification": {
    "enableEventCallback": false
  }
}
```

> `document.fileUrl` and `document.fileBase64` are mutually exclusive. When parsing a local file via V2 mode, the script automatically reads and base64-encodes the file. `fileNameExtension` is auto-detected from the file extension when not explicitly provided.

Response:
```json
{
  "success": true,
  "data": { "bizId": "docmind-20260519-xxxx" }
}
```

### Query Endpoint

`POST {DOCMIND_V2_ENDPOINT}/skill/query`

```json
{
  "bizId": "docmind-20260519-xxxx",
  "layoutStepSize": 100,
  "layoutNum": 0
}
```

Response (on success):
```json
{
  "success": true,
  "data": {
    "status": "success",
    "processing": 100.0,
    "layouts": [ ... ]
  }
}
```

Rate limiting: max 5 tasks per second per IP, global limit 20.

---

## Alibaba Cloud POP Invocation

Three-step async workflow using the default credential chain to initialize the client:

1. **Submit task** - `SubmitDocParserJob` / `SubmitDocParserJobAdvance`
2. **Query status** - `QueryDocParserStatus` (poll until success/fail)
3. **Get result** - `GetDocParserResult` (incremental retrieval via LayoutNum + LayoutStepSize pagination)

POP endpoint: `docmind-api.cn-hangzhou.aliyuncs.com`, API version: `2022-07-11`

```python
from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_docmind_api20220711.client import Client as DocMindClient

cred = CredClient()
config = open_api_models.Config(
    credential=cred,
    endpoint="docmind-api.cn-hangzhou.aliyuncs.com",
    user_agent="AlibabaCloud-Agent-Skills/alibabacloud-docmind-parse/" + os.environ.get("SKILL_SESSION_ID", "unknown")
)
client = DocMindClient(config)
```

---

## Quota

| Mode | Free Quota | After Exhaustion |
|------|------------|------------------|
| V2 API Direct | Limited daily quota | Prompt to activate Alibaba Cloud service |
| Alibaba Cloud POP | 3,000 pages/month | Automatic pay-as-you-go |

When quota is exhausted, prompt the user to visit https://docmind.console.aliyun.com/doc-overview to activate the service.

---

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `QuotaExhausted` / `Throttling` | Quota exhausted or rate-limited | Prompt to activate Alibaba Cloud service |
| `FileUrlLegal` | Invalid file URL | Verify the URL is publicly accessible |
| `InvalidFileFormat` | Unsupported file format | Show the list of supported formats |
| `FileSizeExceeded` | File too large | V2 limit 5 MB, POP limit 150 MB |
| `OssAccessDeniedError` / HTTP 403 | URL points to a private or restricted OSS resource | See pre-validation rules below |

### Pre-validation and Exception Handling

**Before invoking the script, the Agent MUST perform the following checks:**

1. **Local file path validation**: If the input is a local file path, verify that the file exists and is readable before calling the script. If the file does not exist, **stop immediately and ask the user to verify the path**. The Agent must NEVER create, fabricate, or substitute a file to bypass a missing-file error.

2. **Private URL detection**: If the input is a URL and V2 mode returns `OssAccessDeniedError` or HTTP 403, the URL is likely private or requires authentication. In this case:
   - Inform the user that the URL is not publicly accessible.
   - Ask the user to either provide a publicly accessible URL, **or** download the file locally and re-run with the local path — the script will automatically encode it as base64 and upload via V2 (`--mode v2` handles base64 encoding transparently).

3. **Network unreachable**: If the script fails with a connection error (e.g. `ConnectionError`, `ConnectionRefused`), check that:
   - The `DOCMIND_V2_ENDPOINT` (default `docmind.aliyuncs.com`) is reachable from the current environment.
   - Proxy settings or firewall rules are not blocking outbound HTTPS traffic.

---

## Supported File Formats

- **Documents**: PDF, Word (doc/docx), PPT (ppt/pptx), Excel (xls/xlsx/xlsm)
- **Images**: JPG, JPEG, PNG, BMP, GIF
- **Other**: Markdown, HTML, EPUB, MOBI, RTF, TXT
- **Audio/Video** (POP mode only): MP4, MKV, AVI, MOV, WMV, MP3, WAV, AAC

---

## Output Formats

### Markdown Output

Each layout block's `markdownContent` field is concatenated; tables are embedded as HTML tables.

### JSON Output

Raw layouts structured data, including `type`/`subType`, `text`, `markdownContent`, `pageNum`, `index`, `pos` and other fields.

---

## Observability

All outbound HTTP requests (V2 API and Alibaba Cloud POP SDK) set the following `User-Agent` header:

```
AlibabaCloud-Agent-Skills/alibabacloud-docmind-parse/{session-id}
```

The `{session-id}` segment is read from the `SKILL_SESSION_ID` environment variable at runtime. If the variable is not set, the value falls back to `unknown`.

| Component | Value |
|-----------|-------|
| UA template | `AlibabaCloud-Agent-Skills/alibabacloud-docmind-parse/{session-id}` |
| session-id source | `SKILL_SESSION_ID` env var |
| Fallback | `unknown` |
| Env var example | `export SKILL_SESSION_ID=agent-abc123-session-xyz` |

All skill invocations sharing the same `SKILL_SESSION_ID` value are correlated as a single session in server-side logs.

---

## Dependency Installation

```bash
# POP mode
pip install "alibabacloud-docmind-api20220711>=1.0.0" \
            "alibabacloud-credentials>=1.0.0" \
            "alibabacloud-tea-openapi>=0.3.8" \
            "alibabacloud-tea-util>=0.3.0" \
            "alibabacloud-gateway-pop>=0.1.0"

# V2 mode
pip install "requests>=2.20.0"
```
