---
name: alibabacloud-agentloop-management
description: |
  The skill should be used when the user asks about Alibaba Cloud AgentLoop platform for onboarding applications into observability, managing Datasets, building pipelines, evaluating, and recalling stored experience.
license: Apache-2.0
metadata:
  domain: aiops
  owner: agentloop
  contact: agentloop@alibaba-inc.com
---

# AgentLoop Skill Router

> **Positioning**: This skill is the single entry point for Alibaba Cloud **AgentLoop** requests. It only classifies the user's intent and dispatches to one of the five domain playbooks below. All executable rules - prerequisites, credentials, RAM policies, parameter confirmation, safety protocols, command usage, and verification - live inside the domain files. Do not run any cloud operation before reading the matched domain file.

**Compatibility**: cloud-operation domains require Aliyun CLI 3.3.15 or later; Pipeline requires `aliyun-cli-agentloop` 0.7.4 or later; bundled evaluation, experience-recall, and Pipeline scripts require Python 3.8 or later.

## Routing Table

| # | Domain | Intent | Entry file (read first) |
|---|--------|--------|-------------------------|
| 1 | Application onboarding (APM & AI observability) | Instrument an application so it reports to AgentLoop: probe or agent install, APM onboarding, `aliyun-bootstrap`, `AliyunJavaAgent`, `instgo`, `cms_node_sdk`, `ack-onepilot`, OpenTelemetry, LicenseKey, K8s/ACK/ECS onboarding, LLM and AI-framework tracing (Dify, LangChain, DashScope) | [references/onboarding.md](references/onboarding.md) - internally routes to [references/apm.md](references/apm.md) / [references/ai.md](references/ai.md) |
| 2 | Evaluation | Score model, agent, or trace quality: create and update evaluators and evaluator skills, one-shot sample tests, batch trace or Dataset evaluation, trace backfill, poll an evaluation task, analyze results and low-score cases | [references/evaluation/evaluation.md](references/evaluation/evaluation.md) |
| 3 | Dataset | Store and retrieve structured rows: Dataset lifecycle and schema, append rows with `add-dataset-data`, read-only queries with `execute-query`, SQL or SearchExpr, semantic search, embedding fields | [references/dataset/dataset.md](references/dataset/dataset.md) |
| 4 | Pipeline | Transform source data into a Dataset once or on a schedule: import Logstore/SLS data into a Dataset, import traces, design specs, preview/create/run, inspect runs, control the lifecycle, configure processing nodes, and map OT AI traces | [references/pipeline/pipeline.md](references/pipeline/pipeline.md) |
| 5 | Experience (recall & store management) | Reuse prior experience, similar cases, past incidents and fixes, old runbooks, and lessons learned; create and manage ContextStores and their API Keys | [references/experience/experience.md](references/experience/experience.md) - routes store lifecycle work to [references/experience/context-store-management.md](references/experience/context-store-management.md) |

## Dispatch Rules

1. Classify the request into one or more domains using the routing table, then read **only** the matched domain entry file(s). Never preload all domains.
2. Follow the matched domain file completely. Each domain defines its own prerequisites, credentials check, RAM policies, parameter confirmation, execution-safety protocol, and verification method.
3. If the request matches none of the domains, state that it is out of scope for this skill and do not dispatch.
4. If the intent is ambiguous between two domains, ask one clarifying question before dispatching.

### Disambiguating Dataset vs Pipeline vs Evaluation

- Writing or reading rows the user already has: **Dataset**.
- Deriving new rows from LogStore or trace data through processing nodes: **Pipeline**. Create or confirm the sink Dataset first.
- Judging the quality of existing traces or Dataset rows with an evaluator: **Evaluation**.

## Multi-Intent Handling

- Execute multiple domains sequentially in dependency order; finish and verify one mutation stage before starting the next.
- For Logstore-to-Dataset materialization: confirm or create the Dataset schema, preview the Pipeline, create and observe the Pipeline run, then read back and reconcile Dataset contents. Start Evaluation only after the Dataset field contract passes.
- Experience recall may run first as a preparatory step for any other domain when the user asks to reuse prior work.

## Shared Conventions

- **Session ID**: generate one 32-character lowercase hex session ID once at the start of the workflow (`openssl rand -hex 16`) and reuse that same value for the rest of the session. Keep the generated value and write it out literally in every command that needs it. Do not re-derive it per command, and do not reach for it through a shell variable or a `cat` of a saved file - either one forces an assignment in front of the call and breaks the command shape rule below.
- **User-Agent**: every `aliyun` CLI cloud API command must carry `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/{session-id}"`. Bundled Python wrappers read `SKILL_SESSION_ID`; local `configure`, `plugin`, and `version` commands are excluded.
- **Command shape**: every cloud API call must run as a single-line bare command whose first token is `aliyun`, or `python3` for a bundled wrapper, and whose last token is the final flag of that same call. Nothing may come before it - no `VAR=value` assignment, no `set -o pipefail`, no `source`, no `cd`, no `bash some_script.sh` wrapper - and a newline between an assignment and the call still counts as coming before it. Nothing may come after it either - no `| tee`, no `| head`, no `2>&1`, no `> file` redirect, and no `&&` or `;` chaining onto a second command. Diagnostic probes such as `--help` follow the same rule. When the environment asks for a log of executed actions, run the bare call first and then write the command text and its output into the log as a separate file-write step; a single action log listing each command and its result satisfies that requirement in full, so piping a call into `tee` adds nothing and only corrupts the record of what ran. The command that executes must be the API call itself and nothing else, so that run records, audit trails, and CLI tooling all see it verbatim.
- **Credential red lines**: never read, echo, or print AK/SK/STS-token values, the APM LicenseKey (`entryPointInfo.authToken`), or a ContextStore API Key - in chat answers, summaries, credential tables, generated snippets, or report files. Keep every retrieved credential inside an environment variable, report only whether it was obtained, and reference the variable name instead of the value. Never ask the user to paste literal credentials; never run `aliyun configure set` with literal credential values; use only `aliyun configure list` to check identity status. Onboarding redaction recipe: [references/onboarding.md](references/onboarding.md#credential-output-redaction).
- **RAM permissions**: use [references/ram-policies.md](references/ram-policies.md) as the skill-wide index. Never put `*` in an Action list. Grant destructive actions separately and deliberately.
- **Resource names**: confirm each resource's exact naming contract before create; Dataset, Pipeline, and ContextStore use different character sets.

| Resource | Flag | Pattern | Hyphen | Underscore |
|---|---|---|---|---|
| Pipeline | `--pipeline-name` | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` | Separator | Rejected |
| Dataset | `--dataset-name` | `^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$`, 4-63 chars | Rejected | Separator |
| ContextStore | `--context-store-name` | `^[a-z0-9_]+$`, 2-64 chars | Rejected | Allowed |
