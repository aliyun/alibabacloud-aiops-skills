# Bailian Managed Agents Product Capability Panorama

> **Source**: the official *Alibaba Cloud Bailian Managed Agents Product Capability Whitepaper*; the original text is archived at [whitepaper-source.md](whitepaper-source.md)
> This file is the structured view, used for explanation and solution benchmarking. Launch corrections and their provenance: [status.md](status.md).
> The comparison against Flow Agent lives in [faq.md](faq.md); quick-start hands-on lives in [../tutorials/index.md](../tutorials/index.md).
> Console: https://agent.console.aliyun.com/managed-agent

## One-sentence positioning

**Managed Agents (CMA for short) is Bailian's "managed agent runtime"** — session state, an isolated sandbox, tool execution, and the event stream of an agent are all hosted in the cloud; the enterprise only has to care about the agent logic itself to deliver long-running tasks such as "multi-step tool calls, code execution, file processing".

Customer-value pitch: **no more building your own Agent Loop, managing sandboxes, wiring tool chains, or maintaining session state** — delegate the task to a managed agent; it plans, calls tools, runs code, and produces files on its own, with the whole process observable, interruptible, and resumable.

One-line distinction: **Flow Agent (agent app 2.5) is the business assistant that "talks"; Managed Agents is the digital employee that "does work".**

## What problem it solves (customer pain points → platform solution)

| Where customers stall from demo to production | How Managed Agents solves it |
| --- | --- |
| Long-running tasks fall over: minutes to hours, dozens of tool calls; a mid-run break means starting over | The server holds session state, supports interruption and resumption; checkpoints are never lost |
| Self-building agent infrastructure is expensive: Agent Loop, sandbox isolation, tool scheduling, timeout retry, event persistence, secret management all DIY | Fully managed runtime + built-in Harness framework; zero infrastructure for the customer |
| Code execution / file processing has no safe landing spot | Per-session isolated cloud container sandbox, preinstallable dependencies, recyclable |
| The process is unobservable and unintervenable; high-risk operations cannot be approved | Session event stream (SSE) pushed in real time + interruption mechanism + tool-call approval |
| State and context are hard to reuse: files, context, secrets, skills never accumulate | Files are standalone resources mounted and reused across sessions; Vault centrally manages credentials; Skills are shared by multiple agents |

## Capability panorama (five domains)

### (1) Runtime foundation (hosting and isolation)

| Capability | Value |
| --- | --- |
| Managed agent runtime | Session state, sandbox, tool execution, and event stream are all hosted by the platform |
| Agent Harness framework | Built-in Agent Loop, checkpoint resumption, error self-recovery, context Cache |
| MultiAgent collaboration | `coordinator` formation: one coordinator orchestrates 1-20 member agents (official docs already open; see [concepts.md](concepts.md)) |
| Session state machine (stateful sessions) | Keeps context and file-system state across turns; supports interruption, resumption, tool-call approval |
| Isolated sandbox (cloud container isolation) | Command execution / file read-write happen inside an isolated sandbox; safe, recyclable, with preinstallable dependencies |

### (2) Unified context and resource control

| Capability | Value |
| --- | --- |
| File upload and mounting | Files are standalone resources mounted by `mount_path`; lifecycle decoupled from sessions, reusable across sessions; single file ≤10MB, workspace total ≤100GB, retained 30 days |
| Resource runtime mounting | Append/unmount file resources while a session runs; takes effect immediately without restart (official docs already open) |
| Code repository mounting `[coming soon]` | Github / Gitee mounted by repository URL + PAT, cloned by default to `/data/workspace/<repo-name>` |
| Memory Store working memory | Launched MA built-in working memory; distinct from the UserId-scoped personalized Bailian Memory Library |

### (3) Tools and extensions

| Capability | Value |
| --- | --- |
| Built-in tool set | `[integrated]` bash / read / write / edit / glob / grep (each must be explicitly enabled); `mark_artifacts` auto-injected by the runtime;<br>`download_file` **officially announced as deprecated — do not rely on it anymore**; launched built-in `websearch` / `webfetch`; `browser_use` via MCP; `[coming soon]` aliyun-cli (historical status, verify current docs) |
| MCP service integration | Connect any external tool service via the MCP protocol. Browser use is available through MCP; an alternative search integration is to mount the marketplace service `WebSearch` (tool name `bailian_web_search`); custom MCP lets you register an already-running MCP endpoint |
| Agent Skills | End-to-end task workflows packaged as skills; the agent decides when to invoke one from its `SKILL.md` description; reusable across agents |
| Official skill marketplace | Ready out of the box: PDF / Word / Excel / PowerPoint processing, bailian-cli, and more |
| Custom skills | Upload a zip (≤10MB, `SKILL.md` at the root); auto review: `checking` → `active` (mountable) / `rejected` |

### (4) Security and credentials

| Capability | Value |
| --- | --- |
| Session environment variables | Pass `environment_variables` at session creation for **plaintext injection** into the sandbox; the agent reads them straight from `os.environ` — the preferred path for non-sensitive configuration (API endpoints, log levels) |
| Vault secret store | Centrally manage external auth material, never echoing plaintext back; **placeholder injection**: the sandbox only sees placeholders, and real values only replace the `Authorization` header when the egress gateway hits a whitelisted host of the credential — **credentials never enter the sandbox** (2026-09 security model; field-tested in [cookbook/08](../cookbook/08-vault-secret-injection-and-egress-gateway.md)) |
| Sandbox execution isolation | Container-level isolation against privilege escalation / escape; recyclable at session end; network isolation |
| Egress gateway | Outbound sandbox traffic passes through a uniformly controlled gateway: secrets are substituted per the `allowed_hosts` allowlist; non-whitelisted destinations only receive the placeholder, preventing secret leakage |
| Enterprise security policies | Can be centrally enforced and cannot be overridden |

### (5) Observability and integration

| Capability | Value |
| --- | --- |
| Session event stream (SSE) | Messages / tool calls / MCP calls / status changes pushed in real time; poll for the full event list when not subscribing to the stream |
| Event history persistence | Persisted server-side, **no customer-side storage needed**; the console can filter by All / User / Agent / Tool / Tool_output / Error / Model / System |
| Events enhancements (launched) | Multimodal events (mixed image and text), Delta incremental returns, Agent Thinking events |
| Deployment managed scheduling | An agent crystallizes into a schedulable / on-demand deployment: create, pause/resume, archive, trigger a run, query run records (list-runs / get-run) |
| Webhook notifications | Run results / status pushed proactively to IM, ticketing, monitoring, and other customer systems. The whitepaper marks this `[coming soon]`, but **REST field-testing shows it is usable** (`webhook_endpoints` resource, 32 named events, HMAC signature verification); delivery is at-least-once and may be out of order — receivers must be idempotent |
| CLI + open API + SDK | Full REST API + Python SDK (`dashscope` ≥ v1.26.2) / Java SDK (≥ v2.22.24); any application / IDE / CLI can orchestrate calls |

> Whitepaper `[coming soon]` labels are historical; verify current docs before describing a capability as unavailable or on the roadmap. See [status.md](status.md) for confirmed launches, including Memory Store, built-in web tools and Events enhancements.

## Core capability highlights (lead with these 6 when presenting)

1. **Fully managed runtime**: from "self-built agent infrastructure" to "just write agent logic". Typical scenario: delegate "produce a data-processing report"; the agent autonomously installs dependencies, runs scripts, produces files — tens of minutes unattended, with progress inspectable and interruptible at any moment.
2. **Industry-leading Agent Harness**: the model only outputs tokens; finishing and finishing correctly depends on the runtime orchestration above the model — Agent Loop scheduling, context cache reuse, error self-healing. In effect it supports hundreds-of-steps long-horizon tasks running unattended for tens of minutes to hours; on cost, a context Cache hit incurs no extra model-call fee.
3. **Stateful sessions + event stream**: from "black-box execution" to "fully observable and intervenable" — interruption mechanism, tool-call approval, SSE event stream, full history persisted.
4. **Context management**: files are standalone resources decoupled from sessions; one master data file can be mounted into multiple analysis sessions without re-uploading.
5. **Extension ecosystem**: built-in tools + MCP + Skills. Typical scenario: an enterprise packages "contract element extraction → risky-clause comparison → review opinion generation" as a custom Skill, reused by the legal, sales, and procurement agents alike.
6. **Deployment managed runs**: crystallize a verified agent into a schedulable / on-demand service with run records, combined with Webhook for downstream integration.

## API First (the foundational design of integration capability)

**All capabilities, All For API**: every object and every capability is defined and delivered API-first; **the console is only a visualization shell on top of the APIs**.
The full lifecycle of core resources (Agent / Session / File / Skill / Vault / Deployment / Webhook, etc.) is API-driven;
one known exception today: **registering a custom MCP service can only be done in the console** (the API side can only reference already-registered services).

Threefold value:
1. **Full lifecycle programmability**: create, query, update, archive, and schedule the ten resource classes Agent / Environment / Session / Event / File / Skill / Vault / Credential / Deployment / Webhook (the whitepaper says "nine major objects"; after Webhook launched on 2026-08 the count is ten) — fully drivable from code, with no console required.
2. **Easy to integrate and embed**: one API Key covers every resource under the workspace; fits CI/CD, business backends, in-house platforms, and third-party agents / IDEs / CLIs (Claude Code, Codex, Qoder, etc.) for orchestrated calls.
3. **Capability alignment, synchronized evolution**: new features ship with an API baseline, so automated integrations get them on day one.

Integration hands-on → [../integration/api-quickstart.md](../integration/api-quickstart.md)

## Commercialization and billing

Commercialization notice: https://www.aliyun.com/notice/118456

| Item | Standard |
| --- | --- |
| Session runtime fee (base billing item) | **0.5 CNY / hour**, billed by the running time of sessions created and enabled (in the running state); sub-hour usage is pro-rated precisely by actual duration |
| Model invocation fee | Billed separately per the invoked model's Bailian public pay-as-you-go standard; **not included** in the runtime fee |
| Tool / MCP service invocation fee | Billed separately per the actual standard of the invoked tool or MCP service |
| Free quota | After official commercialization, **10 hours of free runtime** are granted (10 hours total, **no limit on session count, freely deductible** — the whitepaper's old wording "one session running 10 hours" is outdated); only offsets the session runtime fee, not model or tool fees; valid for **30 days** from the effective date |

Key points: **the runtime fee accrues only while a Session is in the "running" state; idle sessions are not billed.**
CMA token consumption is often several times larger than an ordinary Q&A agent's — always estimate the model fee separately when quoting.
Check the actual account quota with `bl quota` / `bl usage` (see skill `bailian-cli`); do not recite numbers from memory.

## When to recommend Managed Agents

| Customer need signature | Why it fits |
| --- | --- |
| Long-running complex tasks (deep research, multi-step data analysis, code generation; minutes to hours, many consecutive tool calls) | Agent Loop + checkpoint resumption + error self-recovery |
| Needs a safe cloud execution environment (isolated sandbox, preconfigured dependencies, no VM to operate) | Isolated sandbox out of the box, persistable as a whole |
| Only wants to write agent logic, not build infrastructure | Fully managed runtime + All For API |
| Persistent stateful interaction (cross-session context, retained files, maintained history) | Session state machine + cross-session file mounting + MA Memory Store working memory |
| Automated scheduled tasks (daily reports, periodic monitoring, data inspection) | Deployment scheduled triggering + run records + Webhook event notifications |

Conversely, for "Q&A interaction / conversational apps / lightweight plugin calls" recommend Flow Agent 2.5; see [faq.md](faq.md) for the detailed comparison.

## Core information sources

- Product usage docs: https://docs.agent.bailian.aliyun.com/zh/managed-agents
- API overview and auth: https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/introduction
- Docs index for agents: https://docs.agent.bailian.aliyun.com/llms.txt
- Billing description: https://docs.agent.bailian.aliyun.com/zh/managed-agents/pricing/billing
- Changelog: https://docs.agent.bailian.aliyun.com/zh/managed-agents/changelog
- Console: https://agent.console.aliyun.com/managed-agent
- Archived whitepaper original: [whitepaper-source.md](whitepaper-source.md)

> Appending `.md` to any doc URL yields the raw markdown for precise fact-checking; `llms.txt` is the site-wide page index.
> When product capabilities disagree with whitepaper wording, **the live docs win** (the whitepaper is a snapshot; the docs keep updating).

## Related files

- Concept definitions and resource relations → [concepts.md](concepts.md)
- Selection comparison (vs Flow Agent) and objection-handling pitches → [faq.md](faq.md)
- Hands-on getting started → [../tutorials/index.md](../tutorials/index.md)
