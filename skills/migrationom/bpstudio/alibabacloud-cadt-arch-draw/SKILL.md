---
name: alibabacloud-cadt-arch-draw
description: |
  Draw cloud architecture diagrams via CADT AI agent.
  Submit a product/resource description, the backend creates the architecture and returns a summary.
  Triggers: "画架构图", "架构绘图", "CADT 绘图", "draw architecture".
---

# CADT Architecture Diagram Drawing

Submit a product/resource description → CADT AI agent creates the architecture (nodes, connections, validation, layout) and returns a Markdown summary.

## Prerequisites

```bash
aliyun version              # >= 3.3.3
aliyun configure list       # valid profile exists
```

If not met, see [`references/related-commands.md`](references/related-commands.md) § Installation.

> **Security**: NEVER read/echo AK/SK values, NEVER ask user to input credentials in conversation.

---

## Flow

### Step 1: Submit Drawing Request (SendMessage)

```bash
aliyun bpstudio execute-operation-sync \
  --service-type ai_agent \
  --operation SendMessage \
  --region cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cadt-arch-draw/{SESSION_ID}" \
  --attributes '{
    "prompt": "一台 Web ECS + 一台 MySQL RDS + 一台 SLB，部署在同一个 VPC 内"
  }'
```

- **prompt** (required): product/resource list — be specific about products, quantities, and relationships
- **sessionId** (optional): omit for new session; pass to iterate on existing architecture
- **scene** (optional): reserved for future drawing modes — currently no available values, omit

> **Session reuse (MANDATORY)**: If the user provides a `sessionId` (e.g. "sessionId 是 1001", "在上次那个架构基础上改", "继续修改刚才的图"), you MUST pass that exact `sessionId` in this SendMessage call to iterate on the existing CADT session. NEVER start a fresh session and NEVER regenerate the architecture locally. A new execution environment does NOT lose the session — the session lives on the CADT backend, keyed by `sessionId`; just pass it through the CLI.

Response:
```json
{
  "Code": 200,
  "Data": {
    "Status": "SUCCESS",
    "Arguments": { "triggered": true, "sessionId": 1001, "requestId": "xxx-xxx" }
  }
}
```

> Architecture generation typically takes **30–120 seconds** depending on complexity.

### Step 2: Poll for Result (ListMessage)

```bash
aliyun bpstudio execute-operation-sync \
  --service-type ai_agent \
  --operation ListMessage \
  --region cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cadt-arch-draw/{SESSION_ID}" \
  --attributes '{"sessionId": 1001}'
```

Response structure:
```json
{
  "Data": {
    "Status": "SUCCESS",
    "Arguments": {
      "hasMore": false,
      "hasNext": false,
      "lastMessageId": 5002,
      "messageList": [
        {
          "messageId": 5001,
          "sessionId": 1001,
          "senderType": "customer",
          "senderId": "120012345678****",
          "content": "...",
          "status": "done",
          "messageSendTime": 1700000000000
        },
        {
          "messageId": 5002,
          "sessionId": 1001,
          "senderType": "robot",
          "senderId": "robot",
          "content": "...Markdown architecture summary...",
          "status": "done",
          "prompt": "...",
          "messageSendTime": 1700000090000
        }
      ]
    }
  }
}
```

**Polling logic**:
- Find the last message where `senderType == "robot"`
- If its `status == "ongoing"` → wait **5s**, poll again
- If its `status == "done"` → proceed to Step 3
- If `messageList` is empty / has no robot message → keep polling with the **same** `sessionId` (this alone is NOT a reason to switch sessions)
- Max poll: 30 times (~150s), then timeout → **stop and report to the user**

> **On timeout or persistently empty response**: NEVER create a new session as a workaround. Report to the user that session `{sessionId}` returned no response (it may not exist, may have expired, or may belong to another environment) and ask how to proceed. Creating a new session without the user's explicit consent violates Hard Rule #6.

> **Multi-turn**: The robot may ask clarifying questions (e.g., "部署在哪个地域?") instead of directly drawing.
> In that case, `status == "done"` but `content` is a question — present it to the user, collect their reply, and call SendMessage again with the same `sessionId`.
>
> **Invalid input**: Nonexistent products/regions (e.g. a made-up product name or a fake region like `cn-nowhere`) do NOT return `FAILURE` — the robot replies with a clarifying question (Case B) pointing out what it cannot recognize. Relay that clarification faithfully; NEVER fabricate a successful architecture.

### Step 3: Deliver Result

When the robot's last message has `status == "done"`, check its `content`:

**Case A — Architecture complete** (content contains resource table / topology / validation):
1. Present the robot's Markdown `content` to the user
2. Inform user the architecture has been created in CADT and can be viewed/edited at [CADT Console](https://bpstudio.console.aliyun.com)
3. Offer to continue modifying (reuse the same `sessionId`)

**Case B — Clarifying question** (content is a question asking for more info):
1. Present the question to the user
2. Collect user's reply
3. Call SendMessage again with the same `sessionId` and the reply as `prompt`
4. Go back to Step 2

---

## Prompt Tips

| Style | Example |
|-------|---------|
| Simple | "一台 ECS + 一台 RDS" |
| With roles | "Web ECS + MySQL RDS + SLB 负载均衡" |
| With topology | "VPC 内两台 ECS，通过 SLB 对外暴露，后接 Redis 和 PolarDB" |
| Multi-AZ | "两个可用区各一台 ECS，共享 RDS 和 Redis" |
| Constraints | "高可用架构：ALB + 2 台 ECS 跨 AZ，RDS 主备" |

## Error Handling

| Status | Action |
|--------|--------|
| `SUCCESS` | Proceed with Arguments data — **never retry** |
| `FAILURE` (business error, e.g. permission/quota/parameter error) | Show `Message` to user and stop — **do NOT retry** |
| `FAILURE` + "Failed to invoke" in Message (backend service unavailable) | Transient backend outage only — wait 30s and retry **once**; if it still fails, report to user |
| Robot message `status` stays `ongoing` beyond 150s | Inform user of timeout — **keep the same sessionId, do NOT create a new session** |
| `messageList` empty / no robot message after max polls | Report to user that session `{sessionId}` returned no response — **never start a new session without user consent** |

> **Retry policy**: Retry is a conditional edge-case that applies **only** to the `Failed to invoke` backend-unavailable `FAILURE`. A `SUCCESS` response or any business-error `FAILURE` MUST NOT trigger any retry.

## Observability

All `aliyun` CLI calls in this skill MUST include `--user-agent` for tracing.

**UA template** (placeholder form):

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cadt-arch-draw/{SESSION_ID}
```

**UA actual example** (runtime form):

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cadt-arch-draw/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

**Session-id rules:**
- If env var `SKILL_SESSION_ID` is set, use its value directly
- Otherwise, generate a 32-char lowercase hex string (`uuid4().hex`) once at skill session start
- Reuse the same session-id across all CLI calls within one user interaction session

---

## Hard Rules

1. All calls via `aliyun bpstudio execute-operation-sync` — no raw HTTP
2. uid is auto-injected by gateway — never pass in attributes
3. Poll by checking robot message `status`, not a top-level `ongoing` field
4. Present the robot's Markdown content faithfully — do not fabricate results
5. **NEVER generate architecture diagrams locally** (no local `.md`/`.html`/image files, no drawing from scratch). The architecture is ALWAYS produced by the CADT backend via `aliyun` CLI — your only job is to call the API and relay its output.
6. **When the user provides a `sessionId`, you MUST reuse it** by passing it to SendMessage — never create a new session or start over. A new/restarted execution environment does NOT invalidate the session; it persists on the CADT backend keyed by `sessionId`. **Even on polling timeout or an empty response, do NOT switch to a new session — stop and report to the user; only the user may authorize a new session.**
7. This skill is architecture-creation only — no resource provisioning or deployment
8. Every `aliyun` call MUST carry `--user-agent` as specified in Observability section
