# Managed Agents Getting Started: Build a Data-Analysis Agent

> This recipe walks you through the Bailian Managed Agents REST API with curl: create an Agent and an Environment, upload and mount a "dirty" dataset, open a Session and let the agent autonomously run data quality check → cleaning → conclusions, then retrieve the artifacts and archive the resources.

## Overview

This is a beginner recipe. We hand the agent an order ledger with dirty data mixed in and let it run the "quality check → clean → compute metrics → write report" loop by itself, producing a cleaned dataset and a conclusion with concrete numbers.

The scenario is chosen because it carries a natural feedback loop: the agent must discover what is wrong with the data before it can compute correct metrics, and after computing it must loop back and verify the numbers are self-consistent. The example covers the API shapes every later recipe uses: Agent / Environment / Session, file mounting, the event stream, artifact retrieval, archiving.

> This recipe focuses on **the API mechanics themselves**, getting the pipeline running with minimal dependencies; artifacts are Markdown + CSV. Output-quality topics (narrative HTML reports, plotly interactive charts, publication-grade system prompts) can be layered on top of this pipeline.

Before starting, agree on a few environment variables; every curl example below uses them:

```bash
# Your workspace-specific Base URL (cn-beijing region only, currently)
export BASE="https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
# DashScope API Key; one key covers all resources in the workspace
export API_KEY="sk-xxxxxxxx"
```

As the flow progresses we will also export `AGENT_ID`, `ENV_ID`, `SESSION_ID`, and `FILE_ID`.

## The three resource concepts

Bailian Managed Agents has three core resources:

- **Agent**: reusable, versionable configuration holding `model`, `system` (the system prompt), and `tools`. Every update auto-bumps `version`.
- **Environment**: the container template (sandbox), specifying `packages` and `networking`.
- **Session**: binds the Agent to the Environment, mounts files, and produces the event stream. Session creation locks a full snapshot of the Agent's latest version.

Agent and Environment are created once and reused across many Sessions. Each Session is one self-contained run.

## Step 1: Create the Agent

The output quality of a data-analysis agent lives mostly in the system prompt. Instead of a "how to" procedure, we write **work discipline** — verify the data before concluding, clean conservatively, every conclusion carries numbers. The agent figures out the rest.

Tools use the builtin toolkit, `type` being `builtin_toolkit` (an Agent carries at most 1 builtin toolkit). **Six configurable core tools**: `bash`, `read`, `write`, `edit`, `glob`, `grep` — all enabled in this example. Two others to avoid: `download_file` **is officially announced as offline — stop adding it to configs** (some workspaces can still call it during the transition; do not rely on it; retrieve artifacts via the Files API, see Step 6); `mark_artifacts` is injected automatically by the platform runtime and needs no declaration (the example below still lists it explicitly only for a self-evident tool inventory; omitting it changes nothing). For internet access, prefer built-in `web_search` / `web_fetch`, enabled in the same toolkit. Use MCP for browser interaction or specialized services.

> ⚠️ **The most common trap: `default_config.enabled: true` does not actually deliver the tools to the model.** Every tool you want must be **explicitly listed one by one** in `configs[]` with `enabled: true`. With only `default_config.enabled: true` and no `configs`, the tool list the agent receives contains just the platform-injected `mark_artifacts`; any `bash` call then returns `TOOL_NOT_FOUND: Tool 'bash' not found. Available tools: ['mark_artifacts']`, and the turn ends with an apology about having no tools.

Pick `qwen3.8-max` for the model. Managed Agents currently accepts model IDs from this generation: `qwen3.8-max` / `qwen3.7-max` / `qwen3.7-plus` / `qwen3.6-plus` / `qwen3.6-flash` (field-tested workspaces also run `auto`, `glm-5.2`, `deepseek-v4-pro`) — legacy generic DashScope IDs like `qwen3-max` are rejected outright (`400 AGENT_010 model not found`). The definitive list is Bailian's official support list.

The system prompt contains newlines; stuffing it into shell single quotes is error-prone — write it to a file first and use `-d @`:

```bash
cat > agent.json <<'EOF'
{
  "name": "data-analyst-intro",
  "model": { "id": "qwen3.8-max" },
  "system": "You are a data analyst. Your way of working is \"verify the data first, then conclude\":\n\n- Always write python3 scripts to process data; never draw conclusions by eyeballing tables.\n- Before computing any metric, run a data-quality check first: row count, duplicate rows, missing values, and the actual values of every categorical field.\n- Clean conservatively. Only fix provable issues: fully duplicated rows, missing values derivable from other columns, synonymous values written inconsistently.\n- Data that looks extreme but is internally consistent is real business data — call it out in the report, do not delete it.\n- Every conclusion must carry concrete numbers.\n\nWrite artifacts under /mnt/session/outputs/; once all are written, register them in one shot with mark_artifacts.",
  "tools": [
    {
      "type": "builtin_toolkit",
      "default_config": {
        "enabled": true,
        "permission_policy": { "type": "always_allow" }
      },
      "configs": [
        { "name": "bash",  "enabled": true },
        { "name": "read",  "enabled": true },
        { "name": "write", "enabled": true },
        { "name": "edit",  "enabled": true },
        { "name": "glob",  "enabled": true },
        { "name": "grep",  "enabled": true },
        { "name": "mark_artifacts", "enabled": true }
      ]
    }
  ]
}
EOF

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @agent.json
```

Take `id` from the response (like `agent_<ULID>`); the response also echoes `version: 1`:

```bash
export AGENT_ID="agent_xxxxxxxx"
```

Two lines in this prompt are the crux of this example and worth calling out:

- **"run a data-quality check first"**: without it the model tends to `read` a glance of the data and start reporting numbers, silently carrying dirty data into conclusions.
- **"data that looks extreme but is internally consistent — do not delete"**: this is the guardrail against **over-cleaning**. Our dataset plants one wholesale order with a huge but fully legitimate amount, accounting for over half of total revenue. Without this line the model would likely drop it as an outlier and report a "prettier" but wrong total.

> Note: `builtin_toolkit` has two switch levels — `default_config.{enabled, permission_policy}` and `configs[].{name, enabled, permission_policy}`. `permission_policy` is a real field (this example uses `{ "type": "always_allow" }` so tool calls execute directly, no confirmation round trip). If a tool call ever needs human approval it surfaces via SSE `stop_reason.type == requires_action`; you then send a `tool_approval_response` event to approve. This beginner example does not hit that path.
>
> Also, the platform **auto-injects a `mark_artifacts` tool** (no need — and no way — to declare it in `configs`). The agent uses it to register artifacts under `/mnt/session/outputs/` and **get `file_id` back instantly**, optionally attaching a description — the recommended route for Step 6 retrieval. Note registration is not an "exit permit": the outputs directory itself is scanned by the platform, and unregistered files can still be found in the file listing and downloaded later (field-tested); the value of `mark_artifacts` is **not having to wait for the scan or dig through the listing afterwards**.

### Updating config uses POST + version

To adjust tools or the prompt later, the update endpoint is **`POST /agents/{agent_id}`** (`PATCH` returns `405 method not allowed`), and the **body must carry the current `version`** as the optimistic lock, else `400 AGENT_010 invalid agent parameter - version: version cannot be empty`. On success `version` auto-increments:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "version": 1, "name": "data-analyst-intro", "model": { "id": "qwen3.8-max" }, "system": "...", "tools": [ ... ] }'
```

Note that Session creation locks an Agent version snapshot — **existing Sessions never pick up new versions**; after editing the Agent you need a new Session for it to take effect.

## Step 2: Create the Environment

Pick `cloud` for `config.type` to use the managed sandbox (immutable after creation). Data analysis needs pandas — declare it in `config.packages.pip` and **it is already installed when the Session's container starts**, so the agent spends no turn time on `pip install`:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/environments" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "data-analyst-env-01",
    "description": "Introductory data-analysis environment: pandas + openpyxl preinstalled",
    "config": {
      "type": "cloud",
      "packages": { "apt": [], "pip": ["pandas", "openpyxl"], "npm": [] },
      "networking": { "type": "unrestricted" }
    }
  }'
```

`openpyxl` here is not optional: our dataset is Excel (see Step 3), and `pandas.read_excel` needs the openpyxl engine to read `.xlsx` — pandas does not bundle it. Miss it and the agent burns a turn discovering the missing optional dependency and installing it.

Take `id` (like `env_<...>`):

```bash
export ENV_ID="env_xxxxxxxx"
```

The response echoes `config.packages` verbatim (plus one extra `"type": "packages"` field). Whether preinstall actually worked can be confirmed in Step 5's task by having the agent print version numbers — field-tested, the sandbox had `pandas 2.2.3` and `openpyxl 3.1.5`, and the agent never ran a single `pip install`.

> Note: the Environment's networking policy is currently `{ "type": "unrestricted" }` (all outbound allowed) — that is the value at creation; tighter egress, host allowlists, and other finer tiers follow the official support list. This example logically needs no network — packages are preinstalled and the analysis runs fully offline.

## Step 3: Upload the dataset

We craft a 26-row order ledger with three kinds of dirty data and one "trap" planted inside. The data (save as `orders.csv` first; the next step converts it to Excel):

```csv
order_id,order_date,region,category,unit_price,quantity,amount
1001,2026-07-01,East,Electronics,1200,2,2400
1002,2026-07-01,North,Home,150,4,600
1003,2026-07-02,east,Electronics,1200,1,1200
1004,2026-07-02,South,Apparel,80,5,400
1005,2026-07-03,East,Home,150,3,450
1006,2026-07-03, East,Apparel,80,2,
1007,2026-07-04,North,Electronics,900,1,900
1008,2026-07-04,South,Home,150,2,300
1009,2026-07-05,East,Electronics,900,3,2700
1010,2026-07-05,east,Apparel,80,10,800
1011,2026-07-06,North,Apparel,80,3,240
1012,2026-07-06,South,Electronics,1200,1,1200
1013,2026-07-07,East,Home,150,6,900
1014,2026-07-07,East,Electronics,900,2,1800
1015,2026-07-08,North,Home,150,1,150
1016,2026-07-08,South,Apparel,80,4,320
1017,2026-07-09, East,Electronics,1200,2,2400
1018,2026-07-09,north,Home,150,5,750
1019,2026-07-10,East,Apparel,80,6,
1020,2026-07-10,South,Electronics,900,1,900
1014,2026-07-07,East,Electronics,900,2,1800
1021,2026-07-11,North,Electronics,1200,1,1200
1022,2026-07-11,South,Home,150,3,450
1023,2026-07-12,East,Home,150,2,300
1024,2026-07-12,North,Apparel,80,7,560
1025,2026-07-13,East,Electronics,1200,20,24000
```

What is planted:

| # | Issue | Where | Correct handling |
|---|---|---|---|
| 1 | Fully duplicated row | `1014` appears twice | Drop the copy, 26 rows → 25 |
| 2 | `amount` missing | `1006`, `1019` | Backfill with `unit_price × quantity` (160, 480) |
| 3 | `region` written inconsistently | `east`, `north`, ` East` (leading space) | `strip` + normalize case; 6 spellings merge into 3 regions |
| 4 | **Trap**: an extreme value | `1025` (1200 × 20 = 24000) | **Keep it.** Amount is consistent with unit_price × quantity — a real bulk order |

Issue 3 is downstream of 1 and 2: until region is normalized, `east` and `East` count as two regions, revenue splits apart, and the regional ranking is simply wrong. Issue 4 exists specifically to test whether the agent over-cleans — it is 52.68% of total revenue; delete it and the whole picture changes.

The correct answers (after cleaning):

- 25 rows; region has only the three values `East` / `North` / `South`
- Total revenue **45,560**
- By region: East `37,590` > North `4,400` > South `3,570`
- By category: Electronics `38,700` > Home `3,900` > Apparel `2,960`
- Largest single order: `1025`, `24,000`, **52.68%** of total revenue

Keep these numbers; Step 6 uses them to check the agent's math.

### 3.1 Convert to Excel

One trap first: **`.csv` cannot be uploaded directly**. The Files API whitelists by extension, `.csv` is not on it, and a direct upload is rejected with `415` (details in 3.3). `.xlsx` is whitelisted, so we convert to Excel — which also matches reality for data analysis, since what the business hands you is usually Excel anyway.

Convert with openpyxl (locally, `pip install openpyxl`):

```bash
python3 - <<'PY'
import csv
from openpyxl import Workbook

wb = Workbook(); ws = wb.active; ws.title = "orders"
rows = list(csv.reader(open('orders.csv')))
ws.append(rows[0])
for oid, date, region, cat, price, qty, amt in rows[1:]:
    ws.append([int(oid), date, region, cat, int(price), int(qty),
               int(amt) if amt else None])   # empty amount becomes an empty cell
wb.save('orders.xlsx')
print("saved orders.xlsx")
PY
```

Note `int(amt) if amt else None`: a missing `amount` must land as an **empty cell**, not the string `""` or `0`, otherwise planted issue 2 loses its meaning. Also the leading-space ` East` survives into Excel verbatim — dirty data does not get washed by a trip through Excel.

### 3.2 Upload

Upload the `.xlsx` directly, no renaming needed:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -X POST "$BASE/files" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@orders.xlsx"
```

Take `id`:

```bash
export FILE_ID="file_xxxxxxxx"
```

You cannot mount immediately after upload. The response's `status` starts at `checking`; poll `GET /files/{id}` until it becomes `available` (other values: `rejected` / `type_rejected`):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/files/$FILE_ID" \
  -H "Authorization: Bearer $API_KEY"
# watch the "status" field in the response body until it reads "available"
```

Field-tested, this 5.8 KB xlsx went from `checking` to `available` in under 10 seconds. Binary files pass through a scan — do not create the Session right after uploading.

### 3.3 Appendix: what if you only have CSV

The Files API whitelists by **extension**; changing `Content-Type` (`;type=text/csv`, `text/plain`, `application/octet-stream`) does nothing — the check is on the extension, not the MIME type:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -X POST "$BASE/files" -H "Authorization: Bearer $API_KEY" -F "file=@orders.csv"
# {"error":{"code":"11900014","message":"file type not allowed"}}   HTTP 415
```

Field-tested accept / reject results:

| Result | Extensions |
|---|---|
| ✅ accepted | `.txt`, `.md`, `.json`, `.yaml`, `.py`, `.html`, `.xml`, `.xlsx`, `.pdf`, `.zip` |
| ❌ rejected | `.csv`, `.tsv`, `.yml`, `.sh`, `.log`, `.dat`, `.parquet`, `.gz`, `.ipynb`, no extension |

(Note `.yaml` is accepted while `.yml` is rejected. The definitive whitelist is the official one.)

If you would rather not convert to Excel, two other routes:

- **Add a suffix, then name it back**: upload `orders.csv.txt`, and write `mount_path` as `/uploads/orders.csv` at mount time. The filename inside the sandbox is decided by `mount_path`, independent of the uploaded filename, so the agent gets a perfectly normal `orders.csv`. Field-tested working.
- **Bundle**: for larger data or many tables at once, pack a `.zip`, upload it, and let the agent unzip after mounting.


## Step 4: Create the Session

A Session binds the Agent and the Environment, mounts files, and starts a fresh container. `resources` places the data into the container before the agent begins.

Two hard constraints on mount paths:

- `resources[].mount_path` **must start with `/uploads/`**.
- The file's actual path inside the sandbox is `/mnt/session` + `mount_path`; i.e. `mount_path: "/uploads/orders.xlsx"` → actual path `/mnt/session/uploads/orders.xlsx`, **read-only**.

Also, `mount_path` decides the filename inside the sandbox, independent of the uploaded name — that is exactly what makes the CSV-renaming route in 3.3 work.

Because the mount is read-only, the agent must copy files to a writable directory (e.g. `/mnt/user` or `/tmp`) before processing. Artifacts to retrieve must be written under `/mnt/session/outputs/`.

Note the `agent` field takes the Agent ID string directly (the Session auto-locks a full snapshot of that Agent's latest version — no explicit version needed; the first input arrives via a `message` event after Session creation, see Step 5):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "'"$AGENT_ID"'",
    "environment_id": "'"$ENV_ID"'",
    "title": "Order data quality check and analysis",
    "resources": [
      { "type": "file", "file_id": "'"$FILE_ID"'", "mount_path": "/uploads/orders.xlsx" }
    ]
  }'
```

Take `id` (like `sesn_<ULID>`); the response also carries `status` (`idle` / `running` / `terminated`):

```bash
export SESSION_ID="sesn_xxxxxxxx"
```

> In the response, `resources[].file_id` becomes a **new ID** — the platform copies your file into the session scope; the original file is untouched.

## Step 5: Drive the agent and observe

This step is itself two steps: first send a `message` event carrying the task, then read the event stream until the turn ends.

> Note: Session creation carries no initial input, so driving the agent takes two steps — create the Session, then separately POST one `message` event. (If you want "trigger with the first message attached", use a **Deployment** — it supports `initial_events`, delivered at trigger time.)

The event stream is one SSE connection (better than polling for watching the agent iterate live; this example runs about two and a half minutes). Two essentials:

1. **Open the stream first, then send the message.** Establish the SSE connection before sending the `message` to guarantee observability; sending first opens a race where events are lost.
2. **Exit when the Session is `idle` with `stop_reason.type == end_turn`.** The Session goes `idle` whenever it waits for input (both at turn end and when self-hosted tool results need backfilling); use `stop_reason` to tell them apart — only `end_turn` is a real exit signal.

### 5.1 Open the SSE stream first

The SSE endpoint needs the `Accept: text/event-stream` header. Establish the connection first:

```bash
# keep this connection alive in one terminal
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 300 -N -X GET "$BASE/sessions/$SESSION_ID/events/stream" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: text/event-stream"
```

Right after connecting you receive one comment line `:connected`; each event then arrives as a four-line group (note: **no space** after the colons):

```
id:1
event:message
:HTTP_STATUS/200
data:{"object":"message","status":"completed","id":"sevt_...","type":"session_status","content":[...]}
```

The real payload is only the `data:` line — a JSON Message object. Note the `event:` line is **always `message`** (it is the SSE frame type, not the event type); the real event type lives in `type` inside `data`.

Besides `:connected`, the stream interleaves two more comment kinds: `:HTTP_STATUS/200` before each event, and `:keepalive` every 30 seconds when idle. When parsing, skip every line starting with `:`.

> Note: `GET /sessions/{id}/events/stream` is the streaming endpoint. Requesting `GET /sessions/{id}/events` (without `/stream`) with `Accept: text/event-stream` does not upgrade to a stream — it returns the one-shot historical-events JSON as usual.

### 5.2 Then send the task message

Send the `message` event from another terminal. Paths inside the task text must use the **actual sandbox paths** `/mnt/session/uploads/...`:

```bash
cat > msg.json <<'EOF'
{
  "input": [
    {
      "type": "message",
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "/mnt/session/uploads/orders.xlsx is an e-commerce order ledger in Excel, columns: order_id, order_date, region, category, unit_price, quantity, amount.\n\nFirst print the versions of pandas and openpyxl to confirm they are preinstalled in the environment. Then copy the file under /mnt/user and work from there, completing two things:\n\n1. Run a data-quality check and clean the data; write the cleaned data to /mnt/session/outputs/orders_clean.csv.\n2. Based on the cleaned data, answer four questions: what is total revenue; the revenue ranking by region; the revenue ranking by category; which single order has the largest amount and what share of total revenue it is. Write it to /mnt/session/outputs/findings.md.\n\nFor every issue found in the quality check, explain in findings.md how you handled it. Register both artifacts with mark_artifacts."
        }
      ]
    }
  ]
}
EOF

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/events" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @msg.json
```

The task states what, not how to clean — discovering the issues and choosing the handling is the agent's job. In the send body the `type` is `message`; the server echo and the stream events also use `type: message`, with `role` telling who spoke (`user` is the echo, `assistant` is agent output).

### 5.3 How to read the event stream

Commonly used fields of the Message object inside `data:`: `type`, `status`, `id`, `created_at`, `sequence_number`, `role`, `thread_id`, `content[]`.

Two easy-to-get-wrong spots:

1. **The top-level `status` is not the session state.** It is the status of this message itself (usually `completed`). The session state hides inside `content[0].data.session_status`.
2. **`thread_id` is top-level**, not under `metadata`.

Event `type` values you will actually see:

| `type` | Meaning |
|---|---|
| `message` | Message text. `role: user` is the echo of what you sent; `role: assistant` is agent output; the text is in `content[].text` |
| `reasoning` | Thinking placeholder event; field-tested it carries **no `content` field** (be defensive when parsing — do not blindly take `d["content"]`) |
| `tool_call` | The agent calls a tool; `content[0].data` = `{ name, arguments, call_id }` |
| `tool_call_output` | Tool return; `content[0].data` = `{ name, call_id, output }`, where `output` is a JSON **string** |
| `model_request_start` / `model_request_end` | Start/end of each model request; `_end`'s `content[0].data` carries `input_tokens` / `output_tokens` / cache hits — handy for cost accounting |
| `session_status` | Session state change, see below |

The `session_status` payload sits in `content[0].data`:

- Starts running: `{ "session_status": "running" }`
- Turn ends: `{ "session_status": "idle", "stop_reason": { "type": "end_turn" } }` → **break**
- Session terminates: `{ "session_status": "terminated" }` → **break**
- Tool results need backfilling: `{ "session_status": "idle", "stop_reason": { "type": "requires_action" } }` → send `tool_approval_response` or `function_call_output`, **do not exit**

So the exit check is:

```python
if d["type"] == "session_status":
    data = d["content"][0]["data"]
    if data["session_status"] == "terminated":
        break
    if data["session_status"] == "idle" and data.get("stop_reason", {}).get("type") == "end_turn":
        break
```

### 5.4 The field-tested trajectory

One turn runs about 110-185 seconds. Below is one complete field-tested trajectory (the agent's exact moves vary run to run, but the skeleton is stable):

1. `bash` prints versions, confirming `pandas 2.2.3` / `openpyxl 3.1.5` are preinstalled
2. `bash` `mkdir -p /mnt/user /mnt/session/outputs`, then copies the xlsx from the read-only mount into `/mnt/user`
3. `write` a quality-check script → `bash` runs it
4. **Steps into a pit and climbs out on its own**: the script was named `inspect.py`, same as the standard library, so when importing pandas, numpy's internal `import inspect` picked up this script and threw a pile of tracebacks. The agent read the errors, `mv`'d it to `health_check.py`, and the rerun was clean
5. Check output: `(26, 7)`, 1 fully duplicated row, 2 missing `amount` values, region in 6 spellings. In dtypes, `amount` is `float64` — the two empty Excel cells read as `NaN`, promoting the whole column to float
6. `write` a clean+analyze script → `bash` runs it. The script carries its own sanity check: rows where `amount == unit_price × quantity` fails count `0`
7. `write` writes `findings.md`
8. **Self-review**: spawns `bash python3 - <<EOF` to read back the artifact CSV and recompute. The first version called `df.order_id.is_unique` as a method, raising `TypeError: 'bool' object is not callable`; the agent switched to attribute access and the rerun passed
9. `mark_artifacts` **registers both artifacts in one call**, returning each one's `file_id`
10. assistant summary → `end_turn`

Steps 4 and 8 are exactly what "getting started" wants to show you: nobody told it `inspect.py` would collide, and nobody looked up the pandas API for it — it found the problem in the error output, fixed, and reran. That is where "iteration" happens.

Which exact pit gets stepped into varies — the `inspect.py` collision appeared in 2 of 4 field runs; the other two were one where a numeric column was written as `1200.0` floats and the agent itself `edit`ed the script to add integer conversion, and one entirely error-free run (the script happened to be named `inspect_clean.py`, dodging the collision; 10 tool calls, zero rework). But the "run → read result → fix and rerun" loop is stable, and the final numbers were identical across all four runs.

> Dedup and reassembly: the SSE stream currently offers no cursor / resume token; when reconnecting after a drop, deduplicate by event `id`. Streaming assistant text should in theory accumulate by `sequence_number`, but field tests show that field is usually `null` and text arrives as whole `completed` messages — parse as "accumulate when `sequence_number` exists, otherwise treat as a whole message" for maximum robustness.

## Step 6: Retrieve the artifacts and verify

When the agent calls `mark_artifacts`, the return value already carries each artifact's `file_id`:

```json
{
  "marked": [
    { "path": "/mnt/session/outputs/orders_clean.csv", "description": "...", "file_id": "file_0qwg..." },
    { "path": "/mnt/session/outputs/findings.md",      "description": "...", "file_id": "file_zckv..." }
  ],
  "failed": []
}
```

If you did not note these IDs, list files by session scope (two query parameters, `scope_type` + `scope_id`; note **not** the nested `scope[type]` form — that filter is silently ignored and you get the whole workspace's files):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/files?scope_type=session&scope_id=$SESSION_ID&limit=100" \
  -H "Authorization: Bearer $API_KEY"
```

After the turn ends, **every file written under `/mnt/session/outputs/` appears in this listing with `downloadable: true`** — regardless of `mark_artifacts` registration (field-tested: the agent wrote two files and registered only one; the other still listed and downloaded fine). The dividing line is the directory, not the registration act: files **you uploaded as inputs** (mounted under `/mnt/session/uploads/`) are `downloadable: false` — they do not come back. The real gain from `mark_artifacts` is instant `file_id` + a description, saving you from digging through the listing guessing which file is which.

Download via the `/content` subpath (there is no `/download` endpoint — it 404s):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -X GET "$BASE/files/$CLEAN_FILE_ID/content" \
  -H "Authorization: Bearer $API_KEY" -o orders_clean.csv

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 120 -X GET "$BASE/files/$FINDINGS_FILE_ID/content" \
  -H "Authorization: Bearer $API_KEY" -o findings.md
```

Once retrieved, check against the correct answers from Step 3. This is the habit a getting-started recipe most needs to instill — **the agent saying it got it right doesn't count; you verify it yourself**:

```bash
python3 - <<'EOF'
import csv
from collections import defaultdict

rows = list(csv.DictReader(open('orders_clean.csv')))
by_region = defaultdict(float)
for r in rows:
    by_region[r['region']] += float(r['amount'])

assert len(rows) == 25, f"expected 25 rows, got {len(rows)}"
assert sorted({r['region'] for r in rows}) == ['East', 'North', 'South']
assert sum(float(r['amount']) for r in rows) == 45560.0
assert sorted(by_region.items(), key=lambda x: -x[1]) == [
    ('East', 37590.0), ('North', 4400.0), ('South', 3570.0)]
print("✅ cleaned output matches expectations")
EOF
```

Field-tested, all four assertions pass. The four answers in `findings.md` also match expectations exactly: total revenue 45,560; East `37,590` / North `4,400` / South `3,570`; Electronics `38,700` / Home `3,900` / Apparel `2,960`; largest single order `1025` at `52.68%`.

> Small pit: the agent typically writes `to_csv(..., encoding="utf-8-sig")`, so the retrieved CSV carries a BOM and `csv.DictReader` sees the first column name as `\ufefforder_id` instead of `order_id`. The assertions above happen not to touch the first column, so they are unaffected; to read by `order_id`, use `open(..., encoding="utf-8-sig")`.

The most interesting part is an extra section in the report — the agent did not delete the huge order `1025`; it called it out separately and added a robustness analysis (verbatim from one field run; wording varies, but "keep + annotate separately" was the handling in all four runs):

> Order 1025 alone contributes over half of revenue... Excluding it: East revenue is 13,590, still first; Electronics revenue is 14,700, still first. That is, both ranking conclusions are insensitive to this extreme order, but share numbers like "East at 82.51%" and "Electronics at 84.94%" depend heavily on it — annotate when citing.

That is exactly the line from Step 1 — "data that looks extreme but is internally consistent — do not delete" — doing its job.

### A quick look at this run's bill

The `GET /sessions/{id}` response carries `stats` and `usage` — glance at the cost after the run:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $API_KEY"
```

The Excel run, field-tested: `stats` is `{ "active_seconds": 113.7, "duration_seconds": 139.6 }`, and `usage` is `{ "input_tokens": 118011, "output_tokens": 4431, "cache_read_input_tokens": 104152, "cache_creation_input_tokens": 13793 }`. Four field runs landed in the 110-185 seconds / 115k-171k input-tokens range, depending on how often the agent reworked midway. Note 82%-88% of input is cache hits — multi-turn tool calls repeatedly carry the same context, so the cache hit rate dominates cost.

## Step 7: Cleanup (archive)

Use archive to close out Session / Environment / Agent — it tears down the container, stops metering, and hides them from default listings, while keeping records, configuration, and event history for audit. Archive in the order Session → Environment → Agent:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/archive" \
  -H "Authorization: Bearer $API_KEY"

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/environments/$ENV_ID/archive" \
  -H "Authorization: Bearer $API_KEY"

curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID/archive" \
  -H "Authorization: Bearer $API_KEY"
```

After archiving, the Session's `status` becomes `terminated`; the Environment and Agent carry an `archived_at` timestamp and disappear from the default list endpoints.

> In practice, the Agent and Environment are worth keeping for long-term reuse — next time new data arrives, just `POST /sessions` to start a new Session and mount it; no rebuild needed.

## How it works — summary

- **Agent / Environment / Session, three decoupled layers**: the Agent is the versionable "persona + tools", the Environment the reusable "sandbox template", the Session one self-contained run. The first two are built once and reused.
- **Dependencies live in the Environment, not in the turn**: packages declared in `config.packages.pip` are ready at container start (field-tested `pandas 2.2.3` / `openpyxl 3.1.5`), so the agent spends no tokens or time on `pip install`. Reading `.xlsx` — remember `openpyxl`.
- **Tools must be enabled one by one**: `default_config.enabled: true` is only the toolkit master switch; what actually decides which tools the model gets is each `enabled: true` entry in `configs[]`. Skip this and the agent has only `mark_artifacts`.
- **Uploads are constrained by the extension whitelist**: `.csv` is rejected with `415`, `.xlsx` passes — so prefer Excel for datasets. If you must ship CSV, upload as `.txt` / `.zip` and use `mount_path` to name it back; the sandbox filename is decided by `mount_path`. Also, binary files sit at `checking` after upload — wait for `available` before creating the Session.
- **Files are read-only mounts + a writable workspace**: uploaded files mount under `/mnt/session/uploads/` (read-only); the agent must copy to `/mnt/user` or `/tmp` to modify, and write artifacts to `/mnt/session/outputs/`. Note `/mnt/user` and `/mnt/session/outputs` **may not exist yet** in a fresh container (field-tested: the agent's first `ls /mnt/user` got "No such file"); `mkdir -p` before copying covers it.
- **Artifacts exit via `/mnt/session/outputs/`**: files written there get scanned by the platform; after the turn they are visible and downloadable in the session-scoped file listing (field-tested: even unregistered ones download). The value of `mark_artifacts` is getting `file_id` **instantly** plus a description — no waiting for the scan, no digging through listings afterwards, and one call registers multiple artifacts.
- **Drive by events, observe via SSE**: send a `message` event to put the agent into `running`; the SSE stream relays assistant text and tool calls in real time; use `session_status` + `stop_reason` to decide when to stop.
- **`idle` needs disambiguation**: the session state `idle` fires both on "turn ended (`end_turn`)" and "self-hosted tool results need backfilling (`requires_action`)" — always separate them by `stop_reason.type`; exit only on `end_turn`.
- **Guardrails live in the system prompt**: "quality check before conclusions" and "do not delete extreme-but-self-consistent data" decided this example's fate — they beat any procedure description.

## Appendix: polling instead of streaming

For shorter tasks, or production code that cannot hold a long connection, switch to polling the historical-events endpoint `GET /sessions/{session_id}/events`. After sending the message, pull events every 2 seconds and check the last one for completion:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X GET "$BASE/sessions/$SESSION_ID/events?order=desc&limit=1" \
  -H "Authorization: Bearer $API_KEY"
```

The returned `data[0]` has the same structure as the SSE Message, so the exit condition is the same — look at `content[0].data` of the entry with `type == "session_status"`:

```json
{
  "data": [
    {
      "object": "message",
      "status": "completed",
      "id": "sevt_...",
      "type": "session_status",
      "content": [ { "type": "data", "data": { "session_status": "idle", "stop_reason": { "type": "end_turn" } } } ]
    }
  ],
  "next_page": "MTc4ODI0..."
}
```

`session_status` of `terminated`, or `idle` with `stop_reason.type == end_turn` → done.

> In historical events `sequence_number` is often `null`; combine `order` (asc/desc) with `created_at[gt|gte|lt|lte]` for time filtering, and page with `next_page`.

**Trade-offs:**

- **Streaming (SSE)**: best for watching the agent work live; the cost is holding a long connection (the process must stay alive; a network drop kills the stream).
- **Polling**: stateless, survives process restarts, composes well with queues / schedulers; the cost is latency and invisible progress.

In production, when the agent runs for minutes and your handler cannot hold a long connection, polling is the recommendation.

> Note: the production "waiting for human approval (HITL)" case can be built without event push — combine "polling historical events + the `requires_action` stop_reason", or "Deployment (cron / manual `/run`) + post-hoc run queries" (recipe 02, field-tested). Platform-side event push (Webhook) is recipe 06 (field-tested).

## Cheat sheet

**Model IDs**: `qwen3.8-max` / `qwen3.7-max` / `qwen3.7-plus` (no flash tier; generic DashScope IDs like `qwen3-max` and `qwen-plus` are rejected).

**Builtin tools**: six configurable core tools — `bash`, `read`, `write`, `edit`, `glob`, `grep`, **each requiring `enabled: true` in `configs[]`**. The platform additionally auto-injects `mark_artifacts` (no declaration needed). `download_file` is officially offline — stop configuring it. Prefer the launched built-in `web_search` / `web_fetch` for internet search and page reading; use MCP for browser interaction or specialized integrations.

**Upload whitelist** (by extension): `.txt` `.md` `.json` `.yaml` `.py` `.html` `.xml` `.xlsx` `.pdf` `.zip` accepted; `.csv` `.tsv` `.yml` `.sh` `.log` `.dat` `.parquet` `.gz` `.ipynb` and extension-less files rejected with `415`. Changing the MIME type does nothing. **Tabular data goes as `.xlsx`** (remember `openpyxl` in the Environment). After upload, wait for `status` to go from `checking` to `available` before mounting.

**File paths**:

- Upload mount point: `/mnt/session/uploads/<mount_path minus the /uploads/ prefix>` (read-only). `mount_path` must start with `/uploads/` and **decides the sandbox filename** — use it to rename `xxx.csv.txt` back to `xxx.csv`.
- Writable scratch area: `/mnt/user` or `/tmp`.
- Artifact retrieval area: `/mnt/session/outputs/` — writing there is enough for scan-and-download (no registration needed); `mark_artifacts` gets you the `file_id` instantly + a description.

**API details that bite**:

| Item | Correct form |
|---|---|
| Updating an Agent | `POST /agents/{id}` (not PATCH), body must carry the current `version` |
| SSE stream | `GET /sessions/{id}/events/stream` (without `/stream` it does not upgrade to a stream) |
| Message type in events | `message` (`role` separates the user echo from assistant output); the thinking event is `reasoning`. The SSE frame's `event:` line is always `message` — never treat it as the event type |
| Session state location | `content[0].data.session_status` (the top-level `status` is the message status, always `completed`) |
| Thread ID location | top-level `thread_id` (not inside `metadata`) |
| Listing files by session | `?scope_type=session&scope_id=sesn_...` (the nested `scope[type]` form is ignored) |
| Downloading a file | `GET /files/{id}/content` (`/download` is 404) |

**`idle` disambiguation**: the session state `idle` fires both on `end_turn` and when self-hosted tool results need backfilling (`requires_action`); separate them by `stop_reason.type`.
