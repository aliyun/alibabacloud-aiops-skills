# Testing Checklist: Verification Matrix with Success Pictures

Run T1–T5 in order; run T6 after the optional DingTalk setup in Phase 5. `$E2E_ENDPOINT` is the invocation URL from `04_reachability.sh`;
`$ID_TOKEN` is a fresh token from the user's IdP. Every case lists the
command, the expected success picture, and where to look when it fails.

**Presentation rule (user hands-on):** the agent may pre-flight cases
itself to confirm the chain is healthy, but the user should observe the
sample responses. For every
case, hand the user a ready-to-paste command (or a chat question to ask),
let the user run it and watch the agent's real response — the tool list, the
weather answer, the OSS file content, the document URL. Never summarize
"all cases passed" without the user having exercised the tools themselves:
the user must experience the sample working first-hand.

Run this helper and the current test command in the same Bash invocation with
the same absolute `TMPDIR`. Supply a fresh `ID_TOKEN` locally for that invocation;
do not save it in `env.sh` or share it in the conversation. Redefine the helper
when starting a new shell.

Helper (all cases):

```bash
source scripts/lib/common.sh
load_e2e_env
init_conda
ask() {
  local payload response ua
  ua=$(ua_string) || return
  payload=$(python3 -c 'import json,sys; print(json.dumps({"messages":[{"role":"user","content":sys.argv[1]}],"stream":sys.argv[2] == "true"}))' "$1" "${2:-false}") || return
  response=$(curl -sS -m 180 "$E2E_ENDPOINT" -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ID_TOKEN" \
    -H "User-Agent: $ua" \
    --data-binary "$payload" -w '\n%{http_code}') || return
  printf '%s' "$response" | python3 -c '
import json, sys
body, _, status = sys.stdin.read().rpartition("\n")
if not status.isdigit() or not 200 <= int(status) < 300:
    print(body)
    sys.exit("HTTP:" + status)
if sys.argv[1] == "true":
    print(body)
    sys.exit(0)
try:
    print(json.loads(body)["choices"][0]["message"]["content"])
except (ValueError, KeyError, IndexError, TypeError):
    print(body)
    sys.exit("Unexpected response format; inspect the actual body above.")
' "${2:-false}"
}
```

## T1 Inbound authentication

```bash
bash scripts/04_reachability.sh
```

- **Pass**: `401` + `Agent Identity enabled but no ID token provided`.
- With a valid token: HTTP 200, OpenAI-style response body.

## T2 Tool list (Group B baseline)

```bash
ask "你有什么工具？只列工具名"
```

- **First call** (or after token expiry): the response may be an OAuth2
  authorization URL. Open the link promptly — links expire in
  minutes. After they authorize, re-run.
- **Pass**: the list shows the hosted MCP's tool(s) (filtered by Cedar if
  policies are bound) plus the four local tools (`weather_search`,
  `get_object_from_oss`, `get_current_time`, `get_schedule`).

## T3 Cedar tool-level (partial evaluation)

Use the actual MCP function name and parameter schema. Record the test
values, then create and bind the tool-stage policy in ENFORCE mode:

```bash
save_kv E2E_MCP_TOOL "<hosted-MCP-tool-name>"
save_kv E2E_USER_SUB "<subject-issued-by-user-IdP>"
save_kv E2E_POLICY_SET "<test-policy-set-name>"
save_kv E2E_MCP_SUBTOOL "<actual-function-name>"
save_kv E2E_CEDAR_PARAM "<actual-parameter-name>"
save_kv E2E_CEDAR_NEEDLE "<matching-value>"
E2E_CEDAR_STAGE=tool bash scripts/06_cedar_setup.sh
```

Wait for READY and verify the saved binding before testing.

```bash
ask "你有什么工具？只列工具名"
```

- **Pass**: the actual Runtime tool-loading logs show only the permitted MCP
  function(s), compared with T2; a model-generated tool list alone is insufficient.
  Use the current request's Runtime execution logs. If filtering is unconfirmed,
  stop before T4.

## T4 Cedar parameter-level (`when`)

Replace the unconditional tool permit before testing parameters; keep the
same binding. An unconditional permit would bypass the condition.

```bash
E2E_CEDAR_STAGE=param bash scripts/06_cedar_setup.sh
```

```bash
ask "调用 <subtool>，参数 <param> 填 <needle-contains> ..."   # should PASS
ask "调用 <subtool>，参数 <param> 填 <no-needle> ..." true     # should 403
```

Use streaming for the denied call so the official sample exposes the underlying
tool exception in Runtime logs; non-streaming responses summarize it.

- **Pass**: the matching call returns real results; the non-matching call
  has a native HTTP 403 in the Runtime logs, not just a model-written denial.

## T5 Local tools (Groups A/C + OAuth2 annotation)

```bash
ask 'Call weather_search with query="San Francisco".'
ask "Read the OSS object from bucket $E2E_OSS_BUCKET, key $E2E_OSS_KEY, in region $E2E_OSS_REGION."
ask "现在几点？调用时间工具"
ask "查一下 2026-08-15 的日程"
```

- **Expected results**:
  - weather: "It's 20 degrees and foggy." for the `San Francisco` argument
    (API key injected). This is a fixed sample response, not a live weather query.
  - OSS: the actual content read back in Phase 2 (STS exchanged); reused objects
    may have content different from the default test text.
  - time: a timestamp (OAuth2 token via the SDK annotation; first use may
    produce an authorization URL — click it and re-ask)
  - schedule: the mock schedule lines (STS injected), not a live calendar query

## T6 Group E: DingTalk marketplace MCP

Prereq: tool registered (console) from a mcp.dingtalk.com URL, added to
`TOOL_NAME` and redeployed. Use the actual document-creation function and
input schema, with a non-empty body. If permission control is enabled, permit
that function; do not leave the T4 parameter condition attached to this test.

```bash
ask '调用 <actual-document-create-function>，按实际 schema 创建钉钉文档，标题设为 "AgentRun E2E 验证文档"，正文设为 "用于验证 AgentRun 文档创建流程。"，逐字写入引号内的值。允许服务自动追加重名后缀；不要更新或重命名文档。创建后返回实际文档链接。'
```

- **Pass**: the first creation returns a real document URL. Before any update,
  read back and open the document. Its title must match the requested title apart
  from a service-added duplicate suffix; its body must match the quoted body text exactly
  (a trailing paragraph newline is allowed). Record any service-added duplicate
  title suffix alongside the requested title. A later correction does not make
  the initial creation pass.
  Check any document identifier against the actual response schema.
  The marketplace `?key=` authenticates upstream; keep it private.

## Interpreting failures

Match the exact signature against `troubleshooting.md` before changing
anything. Apply these checks:

1. **Unwrap ExceptionGroups** — `('unhandled errors in a TaskGroup', [...])`
   hides the real error; always read the sub-exception before diagnosing.
2. **Authorization prompts are normal** — token expiry depends on the provider
   configuration; complete authorization before repeating the request.
