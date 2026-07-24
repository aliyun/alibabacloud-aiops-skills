# STAROps API Specification

## Tool Dependencies

All STAROps API calls are executed via the built-in `starops_manager.py` script. STS / cloud product read-only APIs are executed via `aliyun` CLI.

STAROps APIs have different invocation methods:

| API | Response Type | Invocation Method |
|-----|--------------|-------------------|
| CreateThread | Standard JSON | Via `starops_manager.py create-thread` subcommand |
| CreateChat | SSE Streaming | Via `starops_manager.py chat` subcommand |
| ListDigitalEmployees | Standard JSON | Via `starops_manager.py list-employees` subcommand |
| GetDigitalEmployee | Standard JSON | Via `starops_manager.py get-employee` subcommand |
| CreateDigitalEmployee | Standard JSON | Via `starops_manager.py create-employee` subcommand |
| DeleteDigitalEmployee | Standard JSON | Via `starops_manager.py delete-employee` subcommand |

## STAROps Product Information

| Property | Value |
|----------|-------|
| Product | StarOps |
| API Version | 2026-04-28 |
| Endpoint | starops.cn-beijing.aliyuncs.com |
| Signing Algorithm | ACS3-HMAC-SHA256 |

> **Endpoint Note**: STAROps uses the cn-beijing global endpoint, which is region-agnostic. Even if the workspace is deployed in Hangzhou, Shanghai, or other regions, `starops.cn-beijing.aliyuncs.com` is always used as the endpoint.

## Digital Employee Discovery API (for onboarding)

Used when profile credentials exist but STAROps configuration is missing, to automatically discover available digital employees under the account (see [SKILL.md Step 2]). These are standard JSON read-only APIs, invoked via `starops_manager.py` subcommands. They **must bind to the profile/credentials of the selected UID** (specified via `--profile` parameter, same rationale as [CreateThread API](#createthread-api) constraint).

| API | Request | Purpose |
|-----|---------|---------|
| `ListDigitalEmployees` | `GET /digital-employee` | Enumerate digital employees under the account |
| `GetDigitalEmployee` | `GET /digital-employee/{name}` | Get single digital employee details by name (auxiliary confirmation) |

### ListDigitalEmployees

**Request parameters** (all optional, for pagination/filtering):

| Parameter | Location | Type | Description |
|-----------|----------|------|-------------|
| maxResults | query | integer | Page size, default 20, max 100 |
| nextToken | query | string | Next page token; when response returns non-empty `nextToken`, continue pagination until empty |
| name / displayName / employeeType / resourceGroupId / tags | query | - | Optional filter conditions |

**Key response fields**:

```json
{
  "total": 56,
  "nextToken": "xxxxx",
  "digitalEmployees": [
    {"name": "emp-1", "displayName": "Inspection Assistant", "description": "...", "employeeType": "custom"}
  ]
}
```

- `digitalEmployees[].name` is the **`employeeId`** required for configuration (the `name` path parameter for CreateThread).
- `displayName` / `description` are for user identification and selection.

### GetDigitalEmployee

Path parameter `name` (= employeeId, required), no request body. Response includes `name` / `displayName` / `description` / `knowledges` / `toolPolicy` and other details. **Does not return `workspace`** (`workspace` is an optional session attribute of CreateThread, not related to digital employees):

```json
{
  "name": "emp-1",
  "displayName": "Inspection Assistant",
  "knowledges": {
    "bailian": [
      {"workspaceId": "llm-xxxx", "indexId": "index-xxxx", "region": "cn-beijing"}
    ]
  }
}
```

- `knowledges.bailian[].workspaceId` is the Bailian knowledge base workspaceId, which has different semantics from CreateThread's `body.variables.workspace`. **Do not use it as `workspace` configuration**.
- `workspace` is an optional session attribute of CreateThread. The user may provide it manually if needed. If not provided, it is omitted.

> **Note**: STAROps does not have a standalone workspace enumeration API. Digital employees do not have a `workspace` concept.

## Digital Employee Management API (for onboarding)

These APIs manage STAROps digital employees during onboarding. They are **user-explicitly-triggered configuration actions**, not part of the read-only diagnostic workflow.

### CreateDigitalEmployee

Invoked via the `starops_manager.py create-employee` subcommand.

**Request**: `POST /digital-employee`

| Parameter | Location | Type | Description |
|-----------|----------|------|-------------|
| body.displayName | body | string | Display name for the digital employee |
| body.description | body | string | Description (optional, default empty) |

**Response**: Standard JSON response with the created digital employee details.

```bash
python3 <skill-root>/scripts/starops_manager.py create-employee \
  --display-name "<name>" [--description "<desc>"] [--profile "<profile>"]
```

### DeleteDigitalEmployee

Invoked via the `starops_manager.py delete-employee` subcommand.

**Request**: `DELETE /digital-employee/{name}`

| Parameter | Location | Type | Description |
|-----------|----------|------|-------------|
| name | path | string | Digital employee name (= employeeId) |

**Response**: Standard JSON response confirming deletion.

```bash
python3 <skill-root>/scripts/starops_manager.py delete-employee "<name>" [--profile "<profile>"]
```

> **Note**: API request/response formats follow REST conventions: POST creates with body, DELETE removes by name path parameter.

## Idempotency Key Specification

This specification is the **single source of truth** for idempotency keys. All locations that generate `idempotencyKey` (the `create_thread()` function in `starops_manager.py`, the `create-thread` subcommand) must follow it. SKILL.md references this specification.

The idempotency key is based on the `uid` / `employeeId` / `workspace` / `title` tuple, using **structured JSON encoding followed by sha256** (not raw string `|` concatenation):

```python
idempotencyKey = sha256_hex(
    json.dumps(
        {"uid": uid, "employeeId": employeeId, "workspace": workspace, "title": title},
        separators=(",", ":"), sort_keys=True,
    ).encode()
)
```

- **Structured encoding**: First construct the four-tuple dictionary, serialize to JSON with `sort_keys=True` and compact separators, then compute the sha256 hex digest of its UTF-8 bytes. This avoids ambiguity when field values contain the delimiter character, compared to raw `|` concatenation.
- **Includes uid for account isolation**: The key includes the session-unique `uid`, so different accounts will not reuse the same Thread even if `employeeId`/`workspace`/`title` are identical.
- **Consistency requirement**: Regardless of which side generates it, the field set, sorting, and serialization method must be exactly identical to ensure idempotent matching.

## CreateThread API

Invoked via the `starops_manager.py create-thread` subcommand.

> **Credentials must bind to the session-selected profile**: `starops_manager.py` specifies the aliyun CLI profile via the `--profile` parameter and **read-only resolves** `~/.aliyun/config.json` to obtain the corresponding credentials (without modifying `current`). This constraint is consistent with the SKILL.md "Credential source matches the selected profile" behavioral constraint.

### Request Parameters

| Parameter | Location | Type | Description |
|-----------|----------|------|-------------|
| name | path | string | employeeId (digital employee ID) |
| body.title | body | string | Session title (<=80 characters) |
| body.idempotencyKey | body | string | Idempotency key to prevent duplicate creation. See [Idempotency Key Specification](#idempotency-key-specification) (structured sha256 based on uid/employeeId/workspace/title, includes uid for account isolation) |
| body.variables.workspace | body | string | Workspace name (optional, `required: false`) |
| body.attributes.source | body | string | Source identifier, fixed `alibabacloud-sre-toolkit` |

### Invocation Example (starops_manager.py create-thread)

```bash
python3 <skill-root>/scripts/starops_manager.py create-thread \
  --employee-id "<employeeId>" --config "<config.json path>" --uid "<UID>" \
  [--profile "<profile>"] [--workspace "<workspace>"] [--title "<title>"]
```

The `create-thread` subcommand resolves `profile` / `uid` / `workspace` from config (or directly via `--profile`), auto-generates the idempotency key, and outputs `threadId`.

### Response

Standard JSON response, extract threadId:

```json
{
  "body": {
    "threadId": "thread-xxx-yyy"
  }
}
```

Extract `body.threadId` (or directly `threadId`, depending on the response structure level).

## CreateChat API

Invoked via the built-in `starops_manager.py` script. CreateChat returns an SSE streaming response. Standard OpenAPI tools only receive the stream-end marker without diagnostic content, so a dedicated script is required.

> **Script responsibilities**: `starops_manager.py` provides 4 subcommands: `create-thread` (create Thread, return threadId), `chat` (execute CreateChat + SSE streaming query and parsing based on an existing threadId), `list-employees` (enumerate digital employees), `get-employee` (get digital employee details).

### Invocation Method

```bash
python3 <skill-root>/scripts/starops_manager.py chat "<thread-id>" "<diagnostic prompt>" \
  --config "<config.json path>" [--uid "<UID>"] \
  [--idle-timeout <seconds>] [--endpoint <host>]
```

### Parameter Description

| Parameter | Description |
|-----------|-------------|
| `<thread-id>` | threadId returned by CreateThread |
| `<diagnostic prompt>` | Natural language diagnostic question sent to STAROps |
| `--config` | STAROps configuration file path (see [starops-config.md](starops-config.md)) |
| `--uid` | Select account from `accounts[]` by UID. Can be omitted for single-account or legacy flat format. **Multi-account without `--uid` raises an error** (lists available UIDs) |
| `--idle-timeout` | SSE stream idle timeout in seconds (default 120) |
| `--endpoint` | STAROps endpoint (default starops.cn-beijing.aliyuncs.com) |
| `--stream` | Real-time SSE event output to stderr (shows thinking process) |
| `--raw` | Raw SSE JSON payload output to stderr (for debugging) |
| `--json` | Structured JSON output `{thinking, answer}` to stdout |

> **Credentials by profile**: The script resolves credentials from `~/.aliyun/config.json` based on the selected account's `profile` **read-only** (supports AK / STS mode), **without modifying `current`**. When `profile` is empty, it falls back to the default credential chain (aliyun current). All STAROps API requests (CreateThread / CreateChat / ListDigitalEmployees / GetDigitalEmployee) are signed using the selected account's profile credentials.

### Internal Implementation

The script performs the following internally:
1. Sends an HTTPS POST request with ACS3-HMAC-SHA256 signing
2. Parses SSE JSON payloads after the `data:` prefix line by line
3. (Optional) In `--stream` / `--raw` mode, outputs each payload to stderr in real-time
4. Extracts `role=assistant` text content from `messages[]` and deduplicates
5. Outputs the complete diagnostic text to stdout

### Output Modes

| Mode | stdout | stderr | Description |
|------|--------|--------|-------------|
| Default | Diagnostic text | (none) | Final answer only |
| `--stream` | Diagnostic text | `[role] content` real-time events | Real-time thinking process display |
| `--raw` | Diagnostic text | Raw JSON payload | Debug SSE structure |
| `--json` | `{"thinking":..., "answer":...}` | (none) | Structured output for programmatic processing |

> `--stream` / `--raw` output to stderr, does not affect stdout pipe capture. `--json` replaces stdout with JSON structure. The three flags can be combined (e.g., `--stream --json`).

### Host Environment Streaming

The `--stream` stderr output uses `flush=True`, which is real-time at the subprocess PIPE level. However, different host environments' Bash tools may have additional output buffering, preventing real-time event display during foreground calls. Choose the appropriate integration method from the table below:

| Host Environment | Recommended Method | Description |
|-----------------|---------------------|-------------|
| Agent runtime (Qoder, etc.) | Background execution + polling | Start command with `is_background=true`, poll incremental stderr output via `GetTerminalOutput` every 3-5 seconds, read stdout after command completes |
| Programming framework (Eino / LangChain / LlamaIndex) | Direct import `stream_chat()` + `on_event` | No subprocess overhead, callback triggers in real-time, zero buffering |
| Direct terminal | Run `--stream` directly | stderr connected to terminal, line-buffered, real-time |

**Programming framework example**:

```python
from starops_manager import stream_chat

def on_event(payload: dict) -> None:
    # Each SSE event triggers callback in real-time, no PIPE buffering
    print(f"[event] {payload}", flush=True)

answer = stream_chat(
    employee_id="alibabacloud-sre",
    thread_id="thread-xxx",
    question="inspect Hangzhou ACK cluster",
    on_event=on_event,
)
```

### Follow-up Queries

For follow-up questions, reuse the same threadId and call again.
