# Alibaba Cloud Bailian Managed Agents Product Capability Whitepaper

> Site: [https://agent.console.aliyun.com/managed-agent](https://agent.console.aliyun.com/managed-agent)

> **Revision note (2026-09-18):** This local English edition of the official whitepaper has been updated using the user's explicit product corrections; it is no longer an unchanged historical snapshot. Confirmed launches and the distinction between MA Memory Store and Bailian Memory Library are recorded in [status.md](status.md). Current official documentation remains authoritative for API contracts and availability scope.

<!-- Maintainer's collation notes:
The authoritative source is https://docs.agent.bailian.aliyun.com/zh/managed-agents.
The API reference entry is https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/introduction.
Mount path: the filled-in mount_path automatically gains the /mnt/session/uploads prefix; the system prompt must state the real path.
The structured view lives in overview.md / concepts.md / faq.md.
-->


## One-sentence positioning & value

*   **Product positioning:** Managed Agents is Bailian's "managed agent runtime" — the agent's session state, isolated sandbox, tool execution, and event stream are all hosted in the cloud, so the enterprise only has to care about agent logic itself to deliver long-running tasks such as "multi-step tool calls, code execution, file processing".

*   **Customer value:** you no longer build your own Agent Loop, manage sandboxes, wire tool chains, or maintain session state — delegate the task to a managed agent; it plans, calls tools, runs code, and produces files on its own, with the whole process observable, interruptible, and resumable.

---

## 1. Why Managed Agents are needed (customer pain points)

When enterprises push agents into production, they almost universally stall on the engineering gap between "demo" and "runnable system":

*   **Long-running tasks fall over**: a real task often takes minutes to hours with dozens of tool calls; a stateless Q&A-style architecture cannot sustain it — a mid-run break means starting over.

*   **Self-building agent infrastructure is expensive**: you must implement the Agent Loop, sandbox isolation, tool scheduling, timeout retry, event persistence, secret management yourself… an enormous engineering effort unrelated to the business.

*   **Code execution / file processing has no safe landing spot**: letting an agent run scripts, install dependencies, and read/write files requires an isolated, controllable, recyclable runtime.

*   **The process is unobservable and unintervenable**: the agent runs in a "black box"; when something breaks you cannot see the process, correct mid-course, or approve high-risk operations.

*   **State and context are hard to reuse**: file-system state, context, secrets, and skills across turns cannot accumulate for reuse.

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/ee0613ba-ef24-446d-b89a-79c9242ed6cf.png)

**Managed Agents converges all of that agent engineering onto the platform side with the trio "managed runtime + isolated sandbox + session event stream", quickly delivering long-running tasks such as "multi-step tool calls, code execution, file processing".**

---

## 2. Core concepts (the product's "noun system" made clear)

**You only need 5 core objects to understand Managed Agents:** ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/165ba563-c522-4341-b98c-57dfb800a5b8.png)

| Concept | Role | Description |
| --- | --- | --- |
| **Agent** | Reusable capability definition | The combined configuration of model + system prompt + tools + MCP services + Skill; referenced by ID after creation, reused across sessions; every save auto-generates a new version |
| **Environment** | Sandbox configuration | The cloud container sandbox where sessions run; dependencies can be preinstalled |
| **Session** | One run instance | One run in which the agent executes a task in a given environment and produces results; the server holds session state, supporting interruption and resumption |
| **Event** | Interaction record unit | Messages, tool results, and status changes between the application and the agent — all recorded as events and persisted server-side |
| **Vault** | Centralized auth management | A "safe"-style central store for external services' API keys / tokens; decrypted and injected by the backend at runtime |
| **Deployment** | Scheduled triggering | With a fixed Agent + Environment + Vault configuration, sessions are launched on schedule for a periodic service. |

---

## 3. Capability panorama

Managed Agents' capabilities divide into five "domains": **runtime foundation, tools and extensions, context and data, security and credentials, observability and integration**. A quick tour by domain follows.

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/e909eb50-b78a-4326-80e5-23c1ecae53df.png)

### (1) Runtime foundation (hosting & isolation) — the root of "zero infrastructure"

| **Capability** | **One-line value** |
| --- | --- |
| **Managed agent runtime** | The platform hosts session state, sandbox, tool execution, and event stream — zero infrastructure for customers |
| **Leading Agent Harness framework** | 1. A leading built-in agent framework (Agent Loop, checkpoint resumption, error self-recovery, context Cache) that makes agents fast, stable, and cheap.<br>2. **Advanced MultiAgent capability** `[launched]` — parallel multi-agent task execution, faster and more effective. |
| **Session state machine (stateful sessions)** | Keeps context and file-system state across turns; supports interruption, resumption, tool-call approval |
| **Isolated sandbox (cloud container isolation)** | Command execution / file read-write happen inside an isolated sandbox; safe, recyclable, with preinstallable dependencies |

### (2) Unified agent context and resource control (resource mounting, cross-session reuse)

| **Capability** | **One-line value** |
| --- | --- |
| **File upload and mounting** | Files are standalone resources mounted by `mount_path`; lifecycle decoupled from sessions, reused across sessions |
| **Github/Gitee repository mounting** `[coming soon]` | Github / Gitee repositories mounted by URL + token, so the agent can directly read the real codebase for related work. |
| **Memory Store working memory** `[launched]` | MA built-in memory, primarily for working memory and task context across sessions; distinct from the UserId-scoped personalized Bailian Memory Library |

### (3) Tools and extensions (letting agents do work, extend, and accumulate)

| **Capability** | **One-line value** |
| --- | --- |
| **Built-in tool set (continuously expanding)** | `[integrated]` bash / read / write / edit / glob / grep / download\_file, ready out of the box;<br>`[coming soon]` aliyun-cli deeply integrating the Alibaba Cloud ecosystem<br>`[launched]` web_search / web_fetch — built-in web search and web fetching |
| **MCP service integration** | Connect external tool services via MCP; `[launched]` browser\_use is available through MCP, not as a built-in tool |
| **Agent Skills (capability packaging)** | Package end-to-end task workflows as skills; configure once, reuse across agents; includes an official skill marketplace |

### (4) Security and credentials (enterprise security baseline)

| **Capability** | **One-line value** |
| --- | --- |
| **Vault authentication** | Centralized management of external auth material; plaintext never echoed; decrypted and injected by the backend |
| **Sandbox execution isolation** | Commands and file operations run inside an isolated container; guards against privilege escalation / escape; recyclable at session end |

### (5) Observability and integration (transparent process, production runs, open access)

| **Capability** | **One-line value** |
| --- | --- |
| **Session event stream (SSE) real-time observability** | Messages / tool calls / MCP calls / status changes pushed in real time; the process is fully transparent |
| **Deployment (managed scheduling)** | Crystallize an agent into a schedulable / on-demand deployment; every run is recorded |
| **CLI ecosystem + open API + SDK (multi-terminal calls)** | Full REST API + Python / Java SDK; any application / IDE / CLI can orchestrate calls |

---

## 4. Core capability highlights (pain point → solution → scenario)

### [Highlight 1]: Fully managed runtime — from "self-built agent infrastructure" to "just write agent logic"

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/4a101549-8ff7-40e9-80b2-50cc5873871c.png)

**Customer pain point**: turning an agent into a runnable system means implementing the Agent Loop, sandbox orchestration, tool scheduling, session state, and event persistence yourself — unrelated to the business yet extremely labor-intensive.

**Managed Agents solution**:

*   The platform hosts **session state, sandbox environment, tool execution, event history** — all managed server-side.

*   The customer only defines the agent (pick a model, write the prompt, check tools/MCP/Skills); the platform handles the rest.

*   Session state is held server-side with **interruption and resumption** — checkpoints of long tasks are never lost.

**Typical scenario**: delegate the task "produce a data-processing report" — the agent autonomously installs dependencies, runs scripts, and produces files; tens of minutes unattended, with progress inspectable and correctable mid-course at any time.

---

### [Highlight 2]: Industry-leading Agent Harness framework — from "model capability" to "long-horizon tasks done fast, stably, cheaply"

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/b86cc66c-c62a-4a78-b076-151b92051c4d.png)

**Customer pain point**: a large model only outputs tokens; what makes an agent "finish and finish correctly" in complex multi-step tasks is the **runtime orchestration and tuning above the model** — how the Agent Loop schedules, how context is cached and reused, how errors self-heal, how effectiveness is measured. Get these wrong and you get "the demo runs, production doesn't".

**Managed Agents solution**: the platform builds in an **industry-leading Harness (runtime framework)** capability, letting agents consistently produce trustworthy results in long-horizon tasks while helping customers quantify value and optimize the input-output ratio.

**(1) Effectiveness — long-horizon execution correctness & task completion rate**

*   **Long-horizon multi-step stability**: the Agent Loop has built-in checkpoint resumption, timeout retry, and error self-recovery — a single-step failure does not fail the whole pipeline; long-horizon (hundreds-of-steps) tasks can run unattended for tens of minutes to hours.

**(2) Cost — cache reuse, lowering cost and raising efficiency**

*   **Context Cache**: recurring context fragments and intermediate results are cached and reused, cutting repeated inference overhead; a Cache hit incurs no extra model-call fee.

### [Highlight 3]: Stateful sessions + event stream — from "black-box execution" to "fully observable and intervenable"

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/55c7a328-4e7f-4dec-b1c2-b1734cc32dac.png)

**Customer pain point**: the agent runs in a black box — no visibility into the process, no mid-course correction, no way to approve high-risk operations.

**Managed Agents solution**:

*   **Session state machine**: a session carries one run instance, supporting the **interruption mechanism** and **tool-call approval** — high-risk operations get a human gate.

*   **Session event stream (SSE)**: full-process events pushed in real time

*   **History persistence**: every interaction in the session is recorded as events, persisted server-side, **requiring no other customer storage resources**; poll for the full event list when not subscribing to the stream. The console supports filtering events by All / User / Agent / Tool / Tool\_output / Error / Model / System.

**Recent enhancements**:

*   `[launched]` **Events support multimodal**: event messages support multimodal content such as images; customers can send/receive mixed image-and-text messages

*   `[launched]` **Events support Delta incremental returns & Agent Thinking event returns**: assistant output supports Delta incremental streaming, and the agent's Thinking process can be returned as events — more real-time interaction, more transparent process.

### [Highlight 4]: Rich context management — resources decoupled from sessions, reused across sessions

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/5fde7b33-3e76-4508-ba76-df2c2836458b.png)

**Customer pain point**: files, data, and context across multi-turn tasks are hard to accumulate and reuse — everything gets re-uploaded every time.

**Managed Agents solution**:

*   Files are uploaded as **standalone resources**, lifecycle **decoupled** from sessions, reusable by multiple sessions.

**Typical scenario**: one master data file mounted into several analysis sessions — no re-uploading.

**Recent enhancements**:

*   `[launched]` **Resource add/remove**: dynamic add/remove management of session resources — mount/unmount resources flexibly at runtime.

*   `[coming soon]` **Github / Gitee resource mounting**: beyond files, mount Github / Gitee repositories by repository URL + access token (PAT), cloned by default to `/data/workspace/<repo-name>`, letting the agent work directly on the real codebase (code understanding, batch refactoring, review, etc.).

*   `[launched]` **Memory Store**: MA built-in memory, primarily for working memory and task context across sessions.

    **Different from Bailian Memory Library:** the latter is a separate service primarily for personalized memory with a supplied **UserId** dimension. The two products have distinct contracts; do not interchange their APIs, identifiers or binding semantics.

### [Highlight 5]: Rich extension ecosystem — built-in tools + the MCP/Skills ecosystem

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/6ea3b362-63a9-484e-bb6e-e1fa3f6b6ed7.png)

**Customer pain point**: built-in tools cover generic needs, but enterprises have many private systems and proprietary workflows to connect and accumulate.

**Managed Agents solution**:

*   **MCP services**: connect any external tool service via the MCP protocol — capability extends without ceiling.

*   **Agent Skills**: package common tasks' **end-to-end workflows as skills**; the agent decides autonomously when to invoke one from the skill description (`SKILL.md`); one skill can be reused by multiple agents.

    *   **Official skill marketplace**: ready out of the box — already includes PDF / Word / Excel / PowerPoint processing, bailian-cli, and more.

    *   **Custom skills**: upload a zip (≤10MB, `SKILL.md` at the root); automatic system review (`checking` → `active` mountable / `rejected` not mountable).

**Typical scenario**: an enterprise packages "contract element extraction → risky-clause comparison → review opinion generation" into one custom Skill; the legal, sales, and procurement agents all reuse the same skill.

---

### [Highlight 6]: Deployment managed runs + Webhook notifications — crystallizing agents into schedulable services

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/ac136f15-e736-4538-8abc-500a775af943.png)

**Customer pain point**: a verified agent needs to run stably in production on schedule / on demand, with timely result notification and a full audit trail.

**Managed Agents solution**: Deployment crystallizes the agent into a managed deployment supporting create, pause/resume, archive, trigger run (run), and run-record queries (list-runs / get-run).

**Recent enhancements**:

*   `[launched]` **Webhook notification capability**: run results/status can be pushed proactively to customer systems (IM, ticketing, monitoring) via Webhook, enabling event-driven downstream integration and alerting.

---

## 5. External-system customer integration capability — API First

> API docs: https://docs.agent.bailian.aliyun.com/zh/api-reference/managed-agents/introduction

**Design philosophy: API First, all capabilities All For API**

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/1c4645f3-bbdb-4895-9efb-5797c93ebedd.png)

Managed Agents was designed from day one on the API First principle: every object and every capability of the product is defined API-first and delivered API-first. **The console is only a visualization shell on top of this API set, not the boundary of capability. This means: whatever the console can do, the API can do — full API control + full API access; there is no hidden capability that "can only be clicked in the UI and not called from code".**

**For customers, All For API brings threefold value:**

*   First, full lifecycle programmability — the create, query, update, archive, and schedule operations of the nine major objects Agent / Environment / Session / Event / File / Skill / Vault / Credential / Deployment are all open, fully drivable from code without the console;

*   Second, easy integration and embedding — one API Key covers every resource under the workspace, naturally fitting CI/CD pipelines, business backends, in-house platforms, and third-party agents / IDEs / CLIs (Claude Code, Codex, Qoder, etc.) for orchestrated calls;

*   Third, capability alignment and synchronized evolution — new features ship with the API as the delivery baseline, so customers' automated integrations adopt them on day one, without waiting for UI adaptation.

---

## 6. Typical scenarios and industry examples

### Scenario 1: an insurance company — the underwriting team's "complex policy clause review"

**Details:** [Best Practice Case · Packaging a "Senior Underwriting Expert" as an Agent](https://alidocs.dingtalk.com/i/nodes/YQBnd5ExVEjea40qCgXk9waOJyeZqMmz?utm_scene=team_space)

### Scenario 2: a SaaS company — the SRE team's "server stability monitoring + release risk control"

**Background**: a B2B SaaS company runs 3 core service clusters online (order engine, billing system, open platform). The on-call SRE, Lao Wang, logs into SLS every morning to pull logs, opens Grafana for dashboards, and digs through the ticketing system to confirm yesterday's alerts were closed out — 40 minutes minimum. Before each biweekly release he also walks the GitLab MR list one by one assessing risk; last time a missed database field change nearly caused a production incident.

**How it runs now**:

**(1) Daily stability report (Deployment triggers daily at 07:30)**:

1.  The agent connects to the log service SLS via the Alibaba Cloud CLI (the Token injected by Vault) and pulls the last 24h of ERROR/FATAL logs from the three clusters.

2.  `bash` runs the aggregation script: group and count by service name × error type, outputting the Top-10 high-frequency exceptions (with stack snippets).

3.  `read` reads the mounted `baseline_7d.json` (the same-week baseline) and compares item by item:

    *   Order engine `TimeoutException`: 237 yesterday vs baseline 42 → **flag red**, +464% period-over-period.

    *   Billing system `NullPointerException`: 5 yesterday vs baseline 3 → normal fluctuation.

    *   Open platform `RateLimitExceeded`: 89 yesterday vs baseline 12 → **flag orange**, needs attention.

4.  `write` produces "stability_report_0730.md": health scores for the three clusters (green/orange/red), new-exception details, and suggested handling priorities.

**(2) Release risk assessment (a session manually triggered once by the R&D lead before a release)**:

1.  The R&D lead mounts this release's MR list file (`release_v3.12_mr_list.csv`, with MR titles, changed file paths, affected modules) into the session.

2.  The agent `read`s the MR list and analyzes each entry:

    *   MRs involving `schema migration` → auto-flagged high risk ("contains database DDL changes").

    *   MRs touching the `payment` path → high risk ("touches the core payment chain").

    *   MRs involving `config/feature-flag` → medium risk ("config change — confirm the canary strategy").

3.  `read` reads the mounted historical incident library `postmortem_index.json` and matches each high-risk MR against past incident patterns (e.g. "last P1 was also an incompatible schema migration").

4.  `write` produces "release_risk_assessment_v3.12.md": one row per MR, with risk level + risk reason + suggested regression test items + related historical incident numbers.

**Lao Wang's experience**: in the morning he just opens DingTalk and reads the report conclusion; only a red light needs intervention; release assessment went from "a 1-hour meeting" to "5 minutes confirming the agent's assessment sheet".

**Customer gains**:

| Gain dimension | Quantified effect |
| --- | --- |
| Timeliness | Daily inspection **40 minutes** → **zero manual**; ready automatically before the morning shift handover |
| Risk coverage | 100% of MRs reviewed + cross-checked against the incident library |
| Traceability | Reports + assessment sheets all archived; review and audit have evidence |
| Standardization | Risk-judgment rules execute uniformly, no longer dependent on individual experience |

---

### Scenario 3: an e-commerce platform — the operations lead's "morning data briefing"

**Background**: Li, operations director of a mid-size e-commerce platform, needs the full picture of the previous day's business before the 9 a.m. standup. The data lives in three places — traffic/conversion CSVs exported from the business advisor, GMV/refund Excel from the ERP system, and inventory turnover tables from the warehouse WMS. Previously a data intern arrived at 7 a.m. daily to merge tables, draw charts, and write conclusions by hand — error-prone and often missing the 9 o'clock meeting.

**How it runs now (Deployment triggers daily at 07:00 automatically)**:

1.  The agent starts and pulls the three files from OSS via `download_file` (the OSS AccessKey is injected by Vault; file paths are auto-assembled from date templates: `/daily-export/2024-07-30/traffic.csv`, `gmv.xlsx`, `inventory.xlsx`).

2.  `bash` starts the Python environment and runs the preset analysis script (the sandbox has pandas + matplotlib persistently installed):

    *   Merge the three tables; compute GMV period-over-period / year-over-year, refund rate, UV→order conversion, inventory turnover days.

    *   Threshold alerts for each metric: GMV down >10% period-over-period flags red; refund rate >5% flags red; turnover days >45 flags orange.

3.  `write` produces two files:

    *   `daily_briefing_0730.xlsx`: 5 sheets (overview + per-dimension detail); the overview top has 4 core number cards + a trend line chart.

    *   `standup_digest_0730.md`: three core conclusions (e.g. "GMV 2.58M, +3.2% period-over-period, normal"; "women's-wear refund rate 6.8%, over threshold — investigate the SKU-3842 sizing issue"; "inventory turnover 38 days, healthy") + a paragraph of anomaly attribution.

4.  On detecting the women's-wear refund-rate breach → the agent further `grep`s the refund-detail table for SKU-3842's refund-reason distribution, finds "runs small" at 72%, and writes it into the attribution advice.

5.  On completion, via an MCP-connected IM channel, the result is pushed to the operations DingTalk group: "@Li today's briefing is generated ✓ 1 alert (women's-wear refund rate), see the attachments", with direct links to both files.

**Li at the 9 a.m. standup**: opens the DingTalk message, reads the three conclusions, and reports; opens the Excel for details when digging deeper. No more dependence on the intern; reports also arrive on weekends and holidays.

**Customer gains**:

| Gain dimension | Quantified effect |
| --- | --- |
| Labor | Frees 1 data role's daily repetitive work; **40+ hours saved monthly** |
| Quality | Threshold alerts + auto-attribution: **anomaly detection 60%+ better than manual table-scanning** |
| Stability | Weekends / holidays / staff changes change nothing — **365 days uninterrupted** |
| Extensibility | Adding a business line = one more OSS export file + one changed path config line |

---

## 7. Commercialization and billing

> Note — commercialization notice: [https://www.aliyun.com/notice/118456?spm=a2c4g.11186623.0.0.2c0e55de8JppdB](https://www.aliyun.com/notice/118456?spm=a2c4g.11186623.0.0.2c0e55de8JppdB)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/J9LnW65yJbr4WlvD/img/4094da4e-0e41-4cf7-9e8f-f46ef6fc070a.png)

### 7.1 Free quota

*   **Granted quota:** after official commercialization, all customers are granted 10 hours of free runtime (i.e.: supports 1 session running free for 10 hours).

*   **Offset scope:** only offsets Managed Agents session runtime fees (0.5 CNY/hour); cannot offset model invocation fees or tool/MCP invocation fees.

*   **Validity:** valid for 30 days from the free quota's effective date; expires thereafter.

### 7.2 Billing standard

*   **Managed Agents session runtime fee (base billing item)**

    *   Billing standard: 0.5 CNY / hour.

    *   Billing description: billed by the running time of the Managed Agents sessions you create and enable (in the running state). Sub-hour portions are pro-rated precisely by actual usage duration.

> **Note: this fee accrues only while the Session is in the "running" state; idle sessions are not billed.**

*   **Model invocation fee**

    *   Billing standard: computed separately per the invoked model's actual billing standard.

    *   Billing description: the Token consumption fee from Managed Agents calling the underlying large model (e.g. the Qwen family) while running and reasoning — not included in the 0.5 CNY/hour runtime fee. This part is charged per the Bailian platform's public pay-as-you-go standard for the corresponding model.

*   **Tool and MCP service invocation fees**

    *   Billing standard: computed separately per the invoked tool's or MCP service's actual billing standard.

---

## Appendix 1: an AI-native quick-start taste of Managed Agent

*   Without writing a single line of integration code, **copy the natural-language instruction below to your local agent** (Qoder, Claude Code, Codex, or any agent supporting the command line and tool calls), and it will use the Bailian CLI to walk the full loop for you — "login → create agent → attach skill → run session → fetch outputs" — a direct demonstration of the "zero-code / AI-native" experience on top of All For API.

```shell
I want to use the "Managed Agents" application published on Alibaba Cloud Bailian.

Reference docs:
- CLI install and login: https://bailian.aliyun.com/cli/install.md

Please help me with the following steps:
1. First log in with the Bailian CLI: bl auth login --console
2. Create a web-design Managed Agent for me, configure the corresponding Skill capability,
   send a message asking the agent to design a simple personal homepage template as a test,
   and finally download the produced files for me.
```

**What happens (the full process your local agent executes behind the scenes)**

Having read the instruction, the local agent autonomously decomposes it into a series of tool calls and completes the five steps below for you — you just watch the progress:

1.  **Install and log in to the CLI:** install the Bailian CLI per the reference docs, run `bl auth login --console` to open the authorization page and complete login, obtaining workspace credentials.

2.  **Initialize and define the Agent:** run `bl managed-agent init` to generate the config file (agents.yaml) and auto-fill it for the "web design" request — pick the model, write the system prompt, check the built-in tools (including `write` / `download_file` for producing files).

3.  **Attach a skill and create:** configure the official "frontend-design" Skill for the agent, giving it end-to-end web-design capability; then `validate` (offline check) → `plan` (preview the change) → `apply --yes` to formally create the agent on Bailian (saving auto-generates a version).

4.  **Start a session and run the test:** run `bl managed-agent session run --agent <your agent> --prompt "Design a simple personal homepage template"`; the cloud immediately spins up an isolated sandbox running the Session. You will see events stream in real time — the agent first reasons about the layout (message), then calls `write` to generate the HTML/CSS in the sandbox (tool\_call → tool\_call\_output), searching for references with `web\_search` if needed, until `session\_status` turns `idle` signaling completion.

5.  **Fetch the outputs:** after the session ends, the local agent downloads the generated homepage files from the sandbox to your local directory and tells you the path — open it in a browser to preview.

---

## Appendix 2: positioning differences versus Flow Agent (agent app)

The Bailian platform offers both **Flow Agent (agent app 2.5)** and **Managed Agents**. They complement rather than replace each other — the core difference in one sentence:

> **Flow Agent is the business assistant that "talks"; Managed Agents is the digital employee that "does work".**

### One-line selection advice

*   The customer wants "**Q&A interaction / conversational apps / lightweight plugin calls**" → recommend Flow Agent 2.5

*   The customer wants "**run code / produce files / long tasks / scheduled automation / sandbox isolation**" → recommend Managed Agents

### Product positioning comparison

| Dimension | Flow Agent (agent app 2.5) | Managed Agents (CMA) |
| --- | --- | --- |
| Core scenario | **Light interaction** over conversation and knowledge | **Heavy execution** over code and files |
| Product role | Servitized conversational app | Production-grade automation infrastructure |
| Technical hub | App-layer orchestration around the **Chat API** | Bottom-layer sandbox hosting around the **Session** |
| Run model | Stateless / short-lived state; context maintained by the application | Server-held session state; supports interruption, resumption, approval |
| Execution environment | Shared runtime | Per-session isolated sandbox (cloud container isolation) |
| Task duration | Seconds ~ minutes | Minutes ~ hours, unattended long-horizon execution |
| Tool capability | Plugin-style function calls | 7 built-in tools in the sandbox + MCP + Skill; can execute code and read/write files |
| Event model | Response-level streaming | Session-level SSE event stream with full history persisted |
| Credential security | Managed by the app itself | Vault centralized custody; plaintext never echoed; injected by the backend |
| Scheduling | Triggered by the business side itself | Built-in Deployment (scheduled / on-demand / Webhook notification) |

### Fine-grained capability comparison:

| **Comparison dimension** | **Bailian Agent 2.5 (Flow Agent)** | **Managed Agents (cloud-managed agents)** | **Frontline sales / conversion hook (Takeaway)** |
| --- | --- | --- | --- |
| **Product positioning & mindshare** | App-layer conversational agent framework<br>Emphasizes fast build-out of conversational scenarios; **the servitized Chat API is a first-class citizen.** | Production-grade agent hosting infrastructure<br>**Provides the fully managed Harness runtime and an isolated sandbox; the Session is a first-class citizen.** | 2.5 sells "apps and experience" (fast build, fast use);<br>CMA sells "infrastructure and productivity" (heavy work, long work). |
| **Core USP** | 1. Zero-code/low-code rapid build<br>2. Visual reasoning-chain tracing | 1. Harness engineering capability (auto decision-making / fault tolerance / context compaction)<br>2. Enterprise-grade security-isolated sandbox execution environment (code / files / network fully isolated)<br>3. Ultra-long async with high reliability (disconnect recovery / very long-horizon task execution) | 2.5 sells "cost reduction and efficiency", lowering the AI-app barrier;<br>CMA sells "production-ready", solving the pain of complex tasks that "won't run through / break mid-way". |
| **Typically suitable scenarios** | **"Q&A and light interaction" scenarios**<br>intelligent customer service, knowledge-base Q&A, routine document parsing, lightweight data analysis, conversational business assistants. | **"Event-driven and heavy execution" scenarios**<br>complex code generation and execution, deep report generation, long-pipeline data processing. | **Scenario-splitting rule:**<br>"talking and asking" picks 2.5;<br>"doing work / producing files" picks CMA. |
| **Interaction & service model** | **Synchronous / short-async servitization**<br>moderate timeouts (30min-1h); maintains the traditional Chat service-interaction model. | **Ultra-long async and event-driven**<br>supports autonomous runs spanning hours, with event-log replay and progress persistence. The Session is a first-class citizen | 2.5 fits embedding into existing chat boxes / web pages;<br>CMA fits embedding into background task centers / pipelines. |
| **Execution environment & sandbox** | **No independent system-level sandbox**<br>relies on platform built-in tools or external API calls; cannot spin up environments. | **Container-level fully isolated sandbox**<br>supports preinstalling multiple packages; code execution, file read-write, and network access fully sandboxed. | A customer who needs to "run Python scripts, generate and modify local files" must be steered to CMA. |
| **State & reliability** | **Single-task chain tracing**<br>focuses on reasoning-state management within one conversation; no cross-session hard-state persistence. | **Session-level hard-state persistence**<br>natively supports disconnect auto-recovery and automatic failure recovery; can run across multiple lifecycles. | For finance / government and other customers demanding extreme task success rates, sell CMA's "failure recovery". |
| **Security, compliance & enterprise** | App-layer permission configuration<br>emphasizes reasoning-process visibility and app-layer servitized auth. | Physical-level isolation and enterprise-grade unified control<br>**the Harness and sandbox network are isolated; credentials never enter the sandbox**; supports enterprise security policies centrally enforced and non-overridable. | When facing enterprise security / compliance review, CMA's "credentials never touch disk + hard network isolation" is the key deal-passing weapon. |
| **Billing model** | Mainly by Token consumption or API call count; conversational Token consumption is usually small. | Token consumption + sandbox runtime duration (not yet billed); CMA Token consumption is often several times that of an ordinary Q&A agent. |  |
| **Comparable competitors** | Coze, Dify, Baidu Qianfan AppBuilder | Claude Managed Agents, etc. |  |

### When to recommend Managed Agents

| **Customer need signature** | **Recommendation rationale** |
| --- | --- |
| **Long-running complex tasks**: deep research, multi-step data analysis, code generation, etc.; execution from minutes to hours with many consecutive tool calls | Agent Loop + checkpoint resumption + error self-recovery; long-horizon unattended |
| **A safe cloud execution environment**: needs an isolated sandbox with preconfigured dependencies and network; no VM to operate yourself | Isolated sandbox out of the box, persistable as a whole, zero configuration |
| **Fast development / low ops**: only wants to write agent logic, not self-build the Agent Loop, sandbox orchestration, and tool-execution infrastructure | Fully managed runtime + All For API; zero-infrastructure start |
| **Persistent stateful interaction**: remembering context across sessions, retaining files, maintaining conversation history (iterative coding assistant, long-term project manager) | Session state machine + Memory Store + cross-session file mounting |
| **Automated scheduled tasks**: running on cron cycles (daily reports, periodic monitoring, data inspection) | Deployment built-in scheduling + run records + Webhook notifications |

---

## Appendix 3: core information sources

*   Product usage docs: https://docs.agent.bailian.aliyun.com/zh/managed-agents

*   API docs: https://docs.agent.bailian.aliyun.com/zh/api-reference/managed-agents/introduction

*   API docs index for agents: https://docs.agent.bailian.aliyun.com/llms.txt
