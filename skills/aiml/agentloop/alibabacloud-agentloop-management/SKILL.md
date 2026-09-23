---
name: alibabacloud-agentloop-management
description: |
  The skill should be used when the user asks about Alibaba Cloud AgentLoop platform for onboarding applications into observability, high-code instrumentation with loongsuite-genai-utils and OpenTelemetry SDK (高代码埋点、LLM Trace 字段、上下文传递与链路串联), Live-Debug runtime diagnostics, managing Datasets, building pipelines, and evaluating. Live-Debug covers ServiceTask dynamic logging, snapshots, metrics, spans, and JVM inspection.
license: Apache-2.0
metadata:
  domain: aiops
  owner: agentloop
  contact: agentloop@alibaba-inc.com
---

# AgentLoop Skill Router

> **Positioning**: This skill is the single entry point for Alibaba Cloud **AgentLoop** requests. It only classifies the user's intent and dispatches to one of the six domain playbooks below. All executable rules - prerequisites, credentials, RAM policies, parameter confirmation, safety protocols, command usage, and verification - live inside the domain files. Do not run any cloud operation before reading the matched domain file.

**Compatibility**: cloud-operation domains require Aliyun CLI 3.3.15 or later; Pipeline requires `aliyun-cli-agentloop` 0.7.4 or later; bundled evaluation, Pipeline, and public-document retrieval scripts require Python 3.8 or later. Instrumentation guidance and public-document retrieval do not require Aliyun CLI, cloud credentials, or a browser.

## Routing Table

| # | Domain | Intent | Entry file (read first) |
|---|--------|--------|-------------------------|
| 1 | Application onboarding (APM & AI observability) | Instrument an application so it reports to AgentLoop: probe or agent install, APM onboarding, `aliyun-bootstrap`, `AliyunJavaAgent`, `instgo`, `cms_node_sdk`, `ack-onepilot`, OpenTelemetry, LicenseKey, K8s/ACK/ECS onboarding, LLM and AI-framework tracing (Dify, LangChain, DashScope) | [references/onboarding.md](references/onboarding.md) - internally routes to [references/apm.md](references/apm.md) / [references/ai.md](references/ai.md) |
| 2 | Evaluation | Score model, agent, or trace quality: create and update evaluators and evaluator skills, one-shot sample tests, batch trace or Dataset evaluation, trace backfill, poll an evaluation task, analyze results and low-score cases | [references/evaluation/evaluation.md](references/evaluation/evaluation.md) |
| 3 | Dataset | Store and retrieve structured rows: Dataset lifecycle and schema, append rows with `add-dataset-data`, read-only queries with `execute-query`, SQL or SearchExpr, semantic search, embedding fields | [references/dataset/dataset.md](references/dataset/dataset.md) |
| 4 | Pipeline | Transform source data into a Dataset once or on a schedule: import Logstore/SLS data into a Dataset, import traces, design specs, preview/create/run, inspect runs, control the lifecycle, configure processing nodes, and map OT AI traces | [references/pipeline/pipeline.md](references/pipeline/pipeline.md) |
| 5 | Live-Debug runtime diagnostics | Diagnose an already-running Java or Python application with CMS ServiceTask: dynamic log/snapshot/metric/span probes, JVM commands (OGNL, decompile, thread/memory/runtime inspection), disable/clear probes, and query capture results through SLS | [references/live-debug-runtime.md](references/live-debug-runtime.md) |
| 6 | High-code instrumentation | Teach, implement, or troubleshoot manual instrumentation for AgentLoop with loongsuite-genai-utils / language-specific GenAI Utils and OpenTelemetry SDK: Java, Go, Python, Node.js; LLM/Agent/Tool/Retrieval spans, LLM Trace field formats, async/cross-process context propagation, business attributes and broken traces | [references/instrumentation/instrumentation.md](references/instrumentation/instrumentation.md) — dynamically retrieves official documentation without a browser |

## Dispatch Rules

1. Classify the request into one or more domains using the routing table, then read **only** the matched domain entry file(s). Never preload all domains.
   For high-code/manual instrumentation, GenAI field semantics, or context propagation, dispatch to **High-code instrumentation first**. Only add Application onboarding when cloud setup, endpoint discovery, or service registration is actually needed; code guidance must not be blocked by onboarding's CLI/workspace prerequisites.
2. Follow the matched domain file completely. Each domain defines its own prerequisites, credentials check, RAM policies, parameter confirmation, execution-safety protocol, and verification method.
   For Live-Debug, the migrated entry file preserves the original skill contract and is authoritative for that domain wherever its module-specific rules differ from the shared conventions below.
   For a vague Live-Debug request, apply its parameter-completeness gate immediately after reading the entry file: state which target information is missing and stop. Treat the clarification as a completed final response for this run, not a request for another message. Use only declarative wording such as `Required inputs for a future run: ...`. The response MUST NOT contain a question mark or any request/invitation phrase, including `please provide`, `provide`, `send`, `reply`, `tell me`, `can you`, `could you`, `请提供`, `请补充`, `提供`, `补充`, `告知`, or `回复`. End exactly with `No diagnostic or cloud action was executed; this run is complete.` Do not run prerequisite checks, discover workspaces/services, inspect credentials, create output files, or issue any cloud call until a future request already supplies the required information.
3. If the request matches none of the domains, state that it is out of scope for this skill and do not dispatch.
4. If the intent is ambiguous between two domains, ask one clarifying question before dispatching.

### Disambiguating Dataset vs Pipeline vs Evaluation

- Writing or reading rows the user already has: **Dataset**.
- Deriving new rows from LogStore or trace data through processing nodes: **Pipeline**. Create or confirm the sink Dataset first.
- Judging the quality of existing traces or Dataset rows with an evaluator: **Evaluation**.

## Delegated Domain: Experience

Experience work - recalling prior experience, similar cases, past incidents and fixes, old runbooks, lessons learned, and the lifecycle of experience stores (ContextStore) and their API Keys - is **not** implemented in this skill. It lives in the separate `alibabacloud-agentloop-experience` skill.

When a request needs experience, on its own or as one step of a multi-domain request:

1. Check whether the `alibabacloud-agentloop-experience` skill is available in the current environment.
2. If it is available, hand the experience part off to it and follow that skill's own rules. Do not reimplement recall or ContextStore commands here.
3. If it is not available, tell the user that this part requires the separate skill and point them at <https://skills.aliyun.com/skills/alibabacloud-agentloop-experience> to install it. Offer to help with the installation, and wait for the user's answer.
4. Never guess at experience behavior in place of the missing skill. Continue with the remaining in-scope domains and report the experience step as blocked on that skill.

## Multi-Intent Handling

- Execute multiple domains sequentially in dependency order; finish and verify one mutation stage before starting the next.
- For Logstore-to-Dataset materialization: confirm or create the Dataset schema, preview the Pipeline, create and observe the Pipeline run, then read back and reconcile Dataset contents. Start Evaluation only after the Dataset field contract passes.
- When the user also asks to reuse prior work, resolve that experience step through the delegated skill above before the in-scope domains start, and say so if the skill is missing.

## Shared Conventions

- **Skill version gate (before the first cloud call)**: read and parse [references/manifest.json](references/manifest.json), require a non-empty string `version`, and keep that exact value for the workflow. If the file is missing, invalid JSON, or has no valid `version`, stop before issuing any Alibaba Cloud API call and report the manifest error. Do not guess, hard-code, or fall back to another version.
- **Session ID**: generate one 32-character lowercase hex session ID once at the start of the workflow (`openssl rand -hex 16`) and reuse that same value for the rest of the session. Keep the generated value and write it out literally in every command that needs it. Do not re-derive it per command, and do not reach for it through a shell variable or a `cat` of a saved file - either one forces an assignment in front of the call and breaks the command shape rule below.
- **User-Agent**: every `aliyun` CLI cloud API command must carry `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/skill-version/{version}/{session-id}"`, using the manifest-derived version and the workflow session ID. Bundled wrappers enforce the same manifest gate and format. Local `configure`, `plugin`, and `version` commands are excluded because they are not cloud API calls.
- **Command shape**: every cloud API call must run as a single-line bare command whose first token is `aliyun`, or `python3` for a bundled wrapper, and whose last token is the final flag of that same call. Nothing may come before it - no `VAR=value` assignment, no `set -o pipefail`, no `source`, no `cd`, no `bash some_script.sh` wrapper - and a newline between an assignment and the call still counts as coming before it. Nothing may come after it either - no `| tee`, no `| head`, no `2>&1`, no `> file` redirect, and no `&&` or `;` chaining onto a second command. Diagnostic probes such as `--help` follow the same rule. When the environment asks for a log of executed actions, run the bare call first and then write the command text and its output into the log as a separate file-write step; a single action log listing each command and its result satisfies that requirement in full, so piping a call into `tee` adds nothing and only corrupts the record of what ran. The command that executes must be the API call itself and nothing else, so that run records, audit trails, and CLI tooling all see it verbatim.
- **Credential red lines**: never read, echo, or print AK/SK/STS-token values or the APM LicenseKey (`entryPointInfo.authToken`) - in chat answers, summaries, credential tables, generated snippets, or report files. Keep every retrieved credential inside an environment variable, report only whether it was obtained, and reference the variable name instead of the value. Never ask the user to paste literal credentials; never run `aliyun configure set` with literal credential values; use only `aliyun configure list` to check identity status. Onboarding redaction recipe: [references/onboarding.md](references/onboarding.md#credential-output-redaction).
- **RAM permissions**: use [references/ram-policies.md](references/ram-policies.md) as the skill-wide index. Never put `*` in an Action list. Grant destructive actions separately and deliberately.
- **Resource names**: confirm each resource's exact naming contract before create; Dataset and Pipeline use different character sets.

| Resource | Flag | Pattern | Hyphen | Underscore |
|---|---|---|---|---|
| Pipeline | `--pipeline-name` | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` | Separator | Rejected |
| Dataset | `--dataset-name` | `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`, 4-63 chars | Rejected | Separator |
