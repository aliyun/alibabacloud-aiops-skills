# Testing Checklist: Verification Matrix with Success Pictures

Run in order. `$E2E_ENDPOINT` is the invocation URL from `04_reachability.sh`;
`$ID_TOKEN` is a fresh token from the user's IdP. Every case lists the
command, the expected success picture, and where to look when it fails.

**Presentation rule (user hands-on):** the agent may pre-flight cases
itself to confirm the chain is healthy (never let the user walk into a known
failure), but the verification EXPERIENCE belongs to the USER. For every
case, hand the user a ready-to-paste command (or a chat question to ask),
let THEM run it and watch the agent's real response — the tool list, the
weather answer, the OSS file content, the document URL. Never summarize
"all cases passed" without the user having exercised the tools themselves:
the user must experience the sample working first-hand.

Helper (all cases):

```bash
ask() { curl -sS -m 180 "$E2E_ENDPOINT" -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$1\"}],\"stream\":false}" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"; }
```

## T1 Inbound authentication

```bash
curl -sS -m 30 "$E2E_ENDPOINT" -X POST -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"ping"}],"stream":false}' -w "\nHTTP:%{http_code}\n"
```

- **Pass**: `401` + `Agent Identity enabled but no ID token provided`.
- With a valid token: HTTP 200, OpenAI-style response body.

## T2 Tool list (Group B baseline)

```bash
ask "你有什么工具？只列工具名"
```

- **First call** (or after token expiry): the response IS an OAuth2
  authorization URL. Hand it to the user IMMEDIATELY — links expire in
  minutes. After they authorize, re-run.
- **Pass**: the list shows the hosted MCP's tool(s) (filtered by Cedar if
  policies are bound) plus the four local tools (`weather_search`,
  `get_object_from_oss`, `get_current_time`, `get_schedule`).

## T3 Cedar tool-level (partial evaluation)

Prereq: `06_cedar_setup.sh` ran with real `<subtool>` names substituted, and
the policy set is BOUND to the tool in the AgentIdentity console.

```bash
ask "你有什么工具？只列工具名"
```

- **Pass**: unpermitted MCP tools vanished from the list (e.g. a 37-tool
  DingTalk MCP shows exactly the permitted three). No error shown — that is
  partial evaluation working.

## T4 Cedar parameter-level (`when`)

```bash
ask "调用 <subtool>，参数 <param> 填 <needle-contains> ..."   # should PASS
ask "调用 <subtool>，参数 <param> 填 <no-needle> ..."          # should 403
```

- **Pass**: the matching call returns real results; the non-matching call
  fails with a tool error (the `when` condition denied it).

## T5 Local tools (Groups A/C + OAuth2 annotation)

```bash
ask "旧金山天气怎么样？调用天气工具"
ask "读取 OSS 文件：bucket 是 <E2E_OSS_BUCKET>，key 是 hello.txt"
ask "现在几点？调用时间工具"
ask "查一下 2026-08-15 的日程"
```

- **Pass pictures** (all field-verified):
  - weather: "It's 20 degrees and foggy." (API key injected, none in code)
  - OSS: the file content `AgentRun e2e test file: ...` (STS exchanged)
  - time: a timestamp (OAuth2 token via the SDK annotation; first use may
    produce an authorization URL — click it and re-ask)
  - schedule: the mock schedule lines (STS injected)

## T6 Group E: DingTalk marketplace MCP

Prereq: tool registered (console) from a mcp.dingtalk.com URL, added to
`TOOL_NAME`, redeployed; Cedar policy permits `create_document`.

```bash
ask "调用 create_document，创建一篇标题为 AgentRun E2E 验证文档 的钉钉文档"
```

- **Pass**: a real document URL (`https://alidocs.dingtalk.com/i/nodes/...`)
  plus nodeId. The marketplace `?key=` authenticates upstream; AgentIdentity
  governed who could call.

## Interpreting failures

Match the exact signature against `troubleshooting.md` before changing
anything. Two universal rules from the field:

1. **Unwrap ExceptionGroups** — `('unhandled errors in a TaskGroup', [...])`
   hides the real error; always read the sub-exception before diagnosing.
2. **Authorization prompts are normal** — tokens last 1 hour; an
   authorization URL response is a state, not a failure.
