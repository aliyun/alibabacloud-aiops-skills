---
name: alibabacloud-sls-data-agent
description: Select this Skill for SLS log analysis, including clarification of missing model, resource or time parameters, Context/Source Model definition or readiness reviews, and DataAgent Chat requests, including interaction or recovery reviews of recorded DataAgent Chat results; load it before the first reply. Query and analyze SLS logs with Source Models or Context Models, or delegate multi-turn analysis and business model management to SLS DataAgent Chat. Use when users request SLS log statistics, investigations or analysis through SLS models, ask a DataAgent to handle a task, continue its Chat, or handle its interactions and recovery. Do not select this Skill for retention changes, resource migration or archival, log collection setup, or product/API documentation lookup requests unless the user explicitly delegates that task to a DataAgent.
---
# SLS Model Queries and DataAgent Chat

## Workflow selection

| Scenario | Workflow |
| --- | --- |
| The user asks a DataAgent to handle the task or continue an existing Chat, or no Context Model/Source Model is selected and no Project/Logstore is identified in the current request or existing context (the default route) | [DataAgent Chat](references/data-agent-chat.md) |
| Otherwise, the current request or existing context explicitly selects a Context Model/Source Model, or identifies the Project/Logstore to analyze | [Model queries](references/model-data-qa.md) |

Keep the workflow selected by the table. If the DataAgent, model, or logstore information required by that workflow is missing or incomplete, consult [Resource information examples](references/target-configuration.md) to confirm or complete it. Skip that reference when the information is already clear and complete.

For Chat, ask for an unknown Chat Region before discovering DataAgents; an empty candidate list does not select the Model queries workflow.

## Runtime prerequisites

- For CLI and Python prerequisites, dependency installation, and credential entry points, see [Installation and configuration](references/cli-installation-guide.md).
- When checking authorization or handling permission errors, read [RAM permissions](references/ram-policies.md) and authorize the actual operations and resources. Ordinary queries do not require model-write permissions by default.
- During diagnosis, keep the configured authentication and the operation’s confirmed region, endpoint and resource scope. Check only whether explicitly required environment variables are set; never enumerate the environment or display credential values, even masked. After an explicit permission denial, stop the denied operation and ask the user to resolve authorization for the reported action and resource before retrying it. If an opaque pagination cursor is rejected, ask for a valid replacement; never guess, clear or omit it to substitute another page. For other persistent failures, stop retrying. Use only a documented fallback applicable to the selected workflow and confirmed scope; otherwise report failure and end the request without offering another retry cycle.

## Request attribution

Before this Skill's first cloud call in a conversation, run `python3 "<skill-dir>/scripts/_skill_user_agent.py" init` once. Retain its JSON and pass it unchanged in the per-call environment variable `ALIBABACLOUD_SLS_DATA_AGENT_SESSION` for every `chat.py` and `model_qa.py` invocation, including follow-ups and retries. Reuse it only for this Skill, installed directory and conversation.

Each script invocation reads this Skill's [manifest](references/manifest.json) and uses its `version` with that binding. Missing or invalid attribution stops before cloud calls; never guess a version. On switching or returning to a Skill, use its own binding and reread its manifest.

For direct `aliyun` cloud calls, pass the same JSON through `ALIBABACLOUD_SLS_DATA_AGENT_SESSION` to `python3 "<skill-dir>/scripts/_skill_user_agent.py" user-agent`. Only after it succeeds, execute `env -u ALIBABA_CLOUD_USER_AGENT aliyun ... --no-cli-ai-mode --user-agent "<resolved-user-agent>"`. Apply this to every actual cloud command, including commands generated at runtime. The format is `AlibabaCloud-Agent-Skills/<frontmatter-name>/<32-hex-session-id> skill-version/<manifest-version>`. Bundled Chat calls apply the same isolation without changing global CLI configuration. Local help, `version`, `plugin`, `configure`, and evidence export do not require attribution.
