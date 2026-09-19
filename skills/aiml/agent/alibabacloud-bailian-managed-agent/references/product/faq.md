# Selection Comparison and Common Objections (FAQ)

> Fact sources: official live docs (https://docs.agent.bailian.aliyun.com/zh/managed-agents ) + the official whitepaper
> ([whitepaper-source.md](whitepaper-source.md)). This file provides **judgment frameworks and pitch language**;
> assertions not yet archived here (e.g. compliance certifications) still need an official wording from the product / compliance team.

## Managed Agents vs Flow Agent (agent app 2.5)

**One sentence**: **Flow Agent is the business assistant that "talks"; Managed Agents is the digital employee that "does work".**
The two complement each other; neither replaces the other.

**One-line selection rule**
- The customer wants "Q&A interaction / conversational apps / lightweight plugin calls" → recommend **Flow Agent 2.5**
- The customer wants "run code / produce files / long tasks / scheduled automation / sandbox isolation" → recommend **Managed Agents**

**Official-docs wording (safe to quote directly to customers, four dimensions)**

| Dimension | Agent app | Managed Agents |
| --- | --- | --- |
| Run model | Stateless invocation; the application side maintains context | The server maintains session state; supports interruption and resumption |
| Execution environment | Shared runtime | Isolated sandbox, cloud container |
| Event model | Response-level streaming output | Session-level SSE event stream with persisted event history |
| Typical scenarios | Q&A, conversation, lightweight tasks | Long-running tasks such as multi-step tool calls, code execution, file processing |

**Product-positioning comparison (whitepaper-refined version, for pre-sales deep dives)**

| Dimension | Flow Agent (agent app 2.5) | Managed Agents (CMA) |
| --- | --- | --- |
| Core scenario | **Light interaction** over conversation and knowledge | **Heavy execution** over code and files |
| Product role | Servitized conversational app | Production-grade automation infrastructure |
| Technical hub | Orchestrated at the app layer around the **Chat API** | Bottom-layer sandbox hosting around the **Session** |
| Run model | Stateless / short-lived state; context maintained by the application | Server-held session state; supports interruption, resumption, approval |
| Execution environment | Shared runtime, no independent system-level sandbox | Per-session isolated sandbox (cloud container isolation) |
| Task duration | Seconds ~ minutes (timeout 30min-1h) | Minutes ~ hours, unattended long-horizon execution |
| Tool capability | Plugin-style function calls | Sandbox built-in tools (bash / read / write / edit / glob / grep) + MCP + Skill; can execute code and read/write files |
| Event model | Response-level streaming | Session-level SSE event stream with full history persisted |
| Credential security | Managed by the app itself | Two layers: session environment variables injected in plaintext (non-sensitive config) + Vault centrally holding secrets (sandbox only sees placeholders; the egress gateway substitutes per the allowlist; credentials never enter the sandbox) |
| Scheduling | Triggered by the business side | Built-in Deployment (scheduled / on-demand / Webhook notification) |
| Billing | Mostly by Token / call count; consumption is small | Token + sandbox runtime duration; **token consumption is often several times that of a Q&A agent** |
| Comparable competitors | Coze, Dify, Baidu Qianfan AppBuilder | Claude Managed Agents, etc. |

**Selling hooks**
- 2.5 sells "apps and experience" (fast to build and use, lowering the AI-app barrier); CMA sells "infrastructure and productivity" (heavy work, long work, solving "it won't run through / breaks mid-way").
- Scenario-splitting rule: **"talking and asking" picks 2.5; "doing work / producing files" picks CMA.**
- The customer needs to "run Python scripts, generate and modify files" → **must** recommend CMA.
- Finance / government and other sectors demanding extreme task success rates → sell CMA's "disconnect auto-recovery / failure recovery".
- Facing enterprise security / compliance review → CMA's "credentials never touch disk + hard network isolation" is the key deal-passing weapon.

## How to answer "can't I just build one with an open-source framework"

Do not disparage self-building; lay out the engineering gap — where customers actually get stuck (whitepaper pain-point chapter):

| Self-building must solve | CMA already includes |
| --- | --- |
| Agent Loop, timeout retry, error self-recovery | Harness framework (with context Cache; hits cost no extra model fee) |
| Sandbox isolation and recycling | Per-session isolated container sandbox with preinstallable dependencies |
| Session state, checkpoint resumption | Session state machine, state held server-side |
| Event persistence, process observability | SSE event stream + full server-side persistence; no self-built storage |
| Secret management | Vault central custody + placeholder injection + egress gateway substitution per the `allowed_hosts` allowlist |
| Scheduled triggering with run records | Deployment (run / list-runs / get-run) |

Closing pitch: **the cost of self-building is not "getting it to run once" — it is "running stably for three months + multi-person collaboration + auditability".**

## How to answer "how is data security / compliance guaranteed"

Official wording you can state directly:
- **Container-level fully isolated sandbox**: command execution, file read-write, and network access are all sandboxed; guards against privilege escalation / escape; recyclable at session end.
- **Credentials never touch the sandbox (2026-09 security model, field-tested)**: Vault centrally manages them and never echoes plaintext; **the sandbox only receives placeholders** (`BMA_SECRET_PLACEHOLDER_*`); real values only substitute the `Authorization` header when the egress gateway hits that credential's `allowed_hosts` allowlist — secret plaintext never enters the sandbox, the model context, or the event stream.
  Non-sensitive config goes through session-level `environment_variables` (plaintext passthrough), layered separately from secrets.
- **Egress leak prevention**: requests to non-whitelisted hosts carry the placeholder as-is; the destination never sees the real secret.
- **Hard network isolation**: the Harness and the sandbox network are isolated.
- **Enterprise security policies**: centrally enforceable and non-overridable.
- **Auditable process**: every interaction is persisted server-side as events and can be replayed.

[TODO] The following still need an official product / compliance wording — do not infer on your own: data-storage regions, whether data is used for model training, log retention period, MLPS / industry compliance certification list, VPC / dedicated-line connectivity plans.

## How to answer "can it connect to our own systems / databases / intranet services"

Separate the two directions first; the solutions differ completely:
1. **Business system calls the Agent** → go through API / SDK integration (API First; anything the console can do, the API can do), see [../integration/patterns.md](../integration/patterns.md).
2. **Agent calls the business system** → connect external tools via MCP services. Marketplace services are called through the platform proxy with no credentials needed;
   for custom MCP the auth headers are **filled in during console registration and stored on the Bailian side**; the platform attaches them at call time — **you do not need to put another copy into the Vault**
   (the Vault is for external-service secrets the agent itself uses inside the sandbox, such as an OSS AccessKey — note that under the new model the sandbox receives a placeholder and the egress gateway substitutes the real value; full chain in [../cookbook/08-vault-secret-injection-and-egress-gateway.md](../cookbook/08-vault-secret-injection-and-egress-gateway.md)). `[coming soon]` aliyun-cli deeply integrates the Alibaba Cloud ecosystem.

[TODO] The official intranet / VPC connectivity plan is pending.

## How to answer "what if results are unstable"

1. The platform already builds in Agent Loop, checkpoint resumption, timeout retry, and error self-recovery — a single-step failure does not kill the whole pipeline.
2. Distill error-prone multi-step workflows into a **Skill** (`SKILL.md` description + end-to-end flow); more stable than pure prompting, and reusable across agents.
3. Use the **event stream** to pinpoint the failing step (console filters by Tool / Error / Model, or `bl managed-agent session events`), then adjust the instruction or switch the model accordingly (selection see skill `bailian-model-recommend`).
4. Put high-risk actions behind **tool-call approval** and the interruption mechanism for human control; never let the agent make single-point decisions.

## How to answer "how much does it cost / is the quota enough"

Billing wording (official billing page: https://docs.agent.bailian.aliyun.com/zh/managed-agents/pricing/billing ):
- Session runtime fee **0.5 CNY/hour** (billed only while running, not while idle; sub-hour usage pro-rated precisely by actual duration)
- **Model invocation fee is separate** (per Bailian's public pay-as-you-go standard); CMA token consumption is often several times that of a Q&A agent
- Tool / MCP invocation fee is separate
- **10 hours** of free runtime granted, no session-count limit, **offsets only the runtime fee** (not model or tool fees), valid for **30 days**

**Official billing example** (usable to walk customers through the math): 2 sessions each running 5 hours, together consuming 1M Input + 200K Output Tokens of qwen-plus
(Input 0.004 CNY per 1K tokens, Output 0.012 CNY per 1K tokens):

| Item | Calculation | Amount |
| --- | --- | --- |
| Session runtime fee | 10 hours × 0.5 | 5.0 CNY |
| Model invocation fee | 1000 × 0.004 + 200 × 0.012 | 6.4 CNY |
| **Total** | | **11.4 CNY** |

**Closing pitch**: the runtime fee is the smaller part (44% in this example); **the model fee is the main cost** — quotes must estimate model consumption separately;
quoting only 0.5 CNY/hour severely underestimates the total.

Quoting method: estimate the runtime fee from "daily session count × average runtime", then estimate the model fee separately;
check the account's actual quota with `bl quota` / `bl usage` (skill `bailian-cli`).
**Cost-saving tip**: archive sessions promptly when tasks finish, to avoid paying for idle spinning.

## Common misconceptions, corrected

| What users say | Correction |
| --- | --- |
| "CMA is just a hosted version of the agent app" | Different positioning: 2.5 is light-interaction Q&A; CMA is heavy-execution infrastructure |
| "0.5 CNY/hour is the whole cost" | Model fees and tool/MCP fees are billed separately, and token consumption is larger |
| "A session burns money as soon as it's created" | Only the "running" state is billed; idle is free |
| "Memory Store and Bailian Memory Library are the same" | MA Memory Store is launched built-in working memory. Bailian Memory Library is a separate service for UserId-scoped personalized memory; their APIs and identifiers are not interchangeable. See [status.md](status.md) |
| "How should an Agent access the web?" | Prefer built-in `web_search` for search and `web_fetch` for reading pages; enable these exact names in `builtin_toolkit.configs[]`. Use MCP for `browser_use` or specialized integrations. The old “no such built-in” observation is superseded. |
| "Enabling `enabled: true` under `default_config` turns tools on" | It does not. They must be listed one by one in `configs[]`, otherwise the agent only gets `mark_artifacts` and replies "I have no tools available" |
| "Webhook isn't live yet, only polling" | The whitepaper wording lags; `webhook_endpoints` **is field-tested as usable**; but delivery is at-least-once and may be out of order — receivers must be idempotent |
| "`download_file` still works for fetching outputs" | Officially announced as deprecated. Fetch outputs via `/mnt/session/outputs/` auto-scan + `GET /files/{id}/content` |
| "Some capabilities can only be clicked in the console" | Mostly API First: the full lifecycle of core resources is API-driven; the known exception is registering custom MCP services (console only; the API side can only reference registered services) |
| "`state rm` deletes the resource" | It only removes local tracking; deleting the remote resource takes `destroy` |
| "Scheduled tasks need your own cron" | Deployments are scheduled server-side (`schedule.type: cron` + timezone, executed by the server) |
| "Multi-agent collaboration hasn't launched" | The official docs already open the `multiagent.coordinator` formation config (1-20 members); that whitepaper edition's information is outdated |
| "A deleted session's history is still queryable" | Deletion is a hard delete (metadata + event history + resource copies all wiped); to keep an audit trail you must use **archive** |
| "Editing an Agent changes sessions currently running" | Sessions snapshot the Agent version at creation and are unaffected by later edits |
