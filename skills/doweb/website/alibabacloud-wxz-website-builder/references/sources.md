# Sources

## Product Documentation

- Product: AI Staff Website Builder
- Product code: `webbuild`
- API version: `2025-04-29`
- Legacy product code: `zero2staff` (RAM actions still use this prefix)

## OpenAPI Endpoints

- Production: `webbuild.aliyuncs.com`
- Endpoint format: No region suffix in URL (global endpoint)

## SDK

- Python SDK: Uses `alibabacloud_tea_openapi` generic client (no product-specific SDK)
- Install: `pip install alibabacloud_tea_openapi alibabacloud_tea_util`
- Auth: AccessKey via environment variables (`ALIBABACLOUD_ACCESS_KEY_ID` / `ALIBABACLOUD_ACCESS_KEY_SECRET`)
- Also accepts aliases: `ALIBABA_CLOUD_*` and `ALICLOUD_*` prefixes
- Optional STS token: `ALIBABACLOUD_SECURITY_TOKEN`

## Source Code References

- POP Facade Interface: `msea-ai-staff-api/.../agent/AIStaffChatPopFacade.java`
- POP Facade Implementation: `msea-ai-staff-app/.../agent/facade/AIStaffChatPopFacadeImpl.java`
- POP Param Classes: `msea-ai-staff-api/.../agent/param/`
- POP DTO Classes: `msea-ai-staff-api/.../agent/dto/`

## Site Management

- Production portal: `https://wanwang.aliyun.com/webdesign/home#/ai/manage/prd`
- Conversation link format: `?conversationId=<CONV_ID>`

## API Actions

| Action | Description |
|--------|-------------|
| `CreateAIStaffConversation` | Create a new website-building conversation |
| `CreateAIStaffChat` | Fire an async chat message |
| `RetryAIStaffChat` | Retry a failed chat |
| `ListAIStaffChatEvents` | Fetch incremental SSE events |

## Key Workflow Phases

1. **Conversation creation** — creates site instance + initial chat
2. **Requirement collection** — multi-round HITL with AskUserQuestion
3. **PRD generation** — auto-triggered after HITL resume (GeneratePrd/WritePrd tools)
4. **Code generation** — long-running (2-5 min), supports magic-fix auto-rounds

## HITL Tools Used by Platform

| Tool | Phase | Description |
|------|-------|-------------|
| `AskUserQuestion` | Requirement collection | Collects user input via forms (text-area, single-select, multi-select) |
| `GeneratePrd` | PRD generation | Generates product requirement document |
| `WritePrd` | PRD generation | Writes PRD content |
| `Bash` | Code generation | Executes build commands |
| `Read` | Code generation | Reads generated files |
| `Skill` | Code generation | Invokes sub-skills for component generation |
