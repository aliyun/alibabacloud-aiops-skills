---
name: alibabacloud-sls-data-agent
description: |
  Invoke SLS DataAgent to autonomously perform data acquisition, processing, analysis, and visualization for Alibaba Cloud SLS (Simple Log Service). Acts as a fully automated data analyst — ask a question in natural language, get structured conclusions and charts.
  Use when the user asks about: 数据分析, 取数, 数据查询, 日志分析, SLS, 可视化, 图表, 数据洞察, data analysis, DataAgent, 全自动数据分析师.
---

# SLS DataAgent

SLS DataAgent is an AI assistant that **autonomously understands natural language** and
**automatically completes data acquisition, processing, analysis, and visualization**. It acts as
your "fully automated data analyst": you ask a question in natural language, and it fetches,
cleans, analyzes the data, and returns conclusions and visualizations.

It is invoked through the SLS DataAgent OpenAPI; the session streams the analysis process and
conclusions back over SSE.

## Capabilities

- **Natural language understanding**: turn colloquial data questions into well-defined analysis tasks.
- **Data acquisition**: automatically locate and pull relevant data (logs, metrics, etc.) within the SLS project.
- **Data processing**: cleaning, aggregation, transformation.
- **Data analysis**: statistics, trends, comparisons, anomalies / insights.
- **Visualization**: generate charts and structured conclusion reports.

## Digital Employee (agentId)

A session is handled by a "digital employee" (digital employee / agentId).

- Generic and customizable: `--digital-employee <name>` > `SLS_DATA_AGENT_EMPLOYEE` env var > script default **`apsara-ops`**.
- The console `assistantId` is the digital employee in use.

## Built-in Skill (capability routing)

Use `--skill` to select a DataAgent built-in skill; omit it to use the general capability.

| Skill ID | Description |
|----------|-------------|
| `builtin.sls.sls-sql-generation` | SQL generation |
| `builtin.sls.spl-generation` | SPL generation |
| `builtin.sls.sls-loongcollector` | LoongCollector ingestion ops |
| `builtin.sls.sls-visualization` | Dashboard assistant |

## Logstore context

Use `--logstore` to specify the target logstore, giving the analysis an explicit data source scope.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLS_DATA_AGENT_PROJECT` | Yes | SLS project name (the scope; can also be passed via `--project`). |
| `SLS_DATA_AGENT_REGION` | Yes | Region where the SLS project resides (e.g. `cn-shanghai`, `cn-beijing`). |
| `SLS_DATA_AGENT_EMPLOYEE` | No | Digital employee name (default `apsara-ops`). |
| `SLS_DATA_AGENT_LOGSTORE` | No | Default target logstore (can also be passed via `--logstore`). |
| `SLS_DATA_AGENT_SKILL` | No | Built-in skill ID (e.g. `builtin.sls.sls-sql-generation`). Omit to use the general capability. |

**Credentials** — uses the Alibaba Cloud Credentials SDK default chain (STS / RAM role / CLI profile
`~/.aliyun/config.json` / env vars `ALIBABA_CLOUD_ACCESS_KEY_ID`+`ALIBABA_CLOUD_ACCESS_KEY_SECRET`).

**Pre-flight check:**

```bash
missing=""
[ -z "$SLS_DATA_AGENT_PROJECT" ] && missing="$missing SLS_DATA_AGENT_PROJECT"
[ -z "$SLS_DATA_AGENT_REGION" ]  && missing="$missing SLS_DATA_AGENT_REGION"
if [ -n "$missing" ]; then echo "ERROR: Missing required environment variables:$missing" >&2; exit 1; fi
echo "OK: PROJECT=$SLS_DATA_AGENT_PROJECT REGION=$SLS_DATA_AGENT_REGION"
```

If a required value is empty, **stop and ask the user**; do not substitute a placeholder such as
`example-project`.

## Invocation

**`--pipe` is mandatory**: it guarantees stdout emits the `THREAD` line and the
`=== DATA AGENT ANSWER BEGIN/END ===` delimiters, so downstream can parse reliably.

```bash
pip3 install -r scripts/requirements.txt

# First question (auto-creates a session; most queries need --logstore)
python3 scripts/call_sls_data_agent.py \
  --logstore my_logstore \
  --question "<full data-analysis request>" --pipe

# Follow-up (reuse the THREAD ID from the previous step to keep context)
python3 scripts/call_sls_data_agent.py \
  --thread "<thread_id>" --question "<follow-up>" --pipe

# Specify a built-in skill
python3 scripts/call_sls_data_agent.py \
  --skill builtin.sls.sls-sql-generation \
  --logstore my_logstore \
  --question "number of error logs in the last 5 minutes" --pipe
```

Example output (pipe):

```text
THREAD: thread-abc123-xyz
DATA_AGENT_URL: https://starops.console.aliyun.com/chat?threadId=thread-abc123-xyz&assistantId=apsara-ops
=== DATA AGENT ANSWER BEGIN ===
(analysis conclusion / visualization description)
=== DATA AGENT ANSWER END ===
```

## Behavioral Notes

1. A DataAgent call is a long task: a single session may trigger multi-step internal analysis and take several minutes; the default timeout is 30 minutes.
2. Provide the full context in one go: SLS project, time range, target logstore/fields, the metrics to analyze, and the expected chart/conclusion form.
3. **Always reuse `--thread` for follow-ups**, otherwise context and intermediate results are lost.
4. **Always pass `--pipe`**: tool status and intermediate progress go to stderr; stdout keeps only the reusable thread id and the final answer.
5. **Conclusions must be based on the real return between the `BEGIN` / `END` delimiters**: cite concrete data points, do not fabricate. If the answer is empty, retry once with the same `--thread`; if still empty, state plainly that DataAgent returned no valid data.

## Troubleshooting

1. **HTTP 401/403** — credentials did not resolve to an authorized identity. Confirm the default chain resolves valid credentials and that the identity is allowed to call the SLS DataAgent OpenAPI. See [references/ram-policies.md](references/ram-policies.md).
2. **HTTP 404** — the digital employee (`--digital-employee`, default `apsara-ops`) or the SLS project (`SLS_DATA_AGENT_PROJECT`) does not exist. Verify both.
3. **ConfigError: Missing required SLS DataAgent configuration** — one of `SLS_DATA_AGENT_PROJECT` / `SLS_DATA_AGENT_REGION` is empty.
4. **CredentialError** — the default chain found no valid credential source.
5. **Idle timeout** — no SSE event within `--idle-timeout` seconds. Increase the value if needed, or retry with the same `--thread`.
6. **ModuleNotFoundError** — run `pip3 install -r scripts/requirements.txt` first.

## API Surface

The script calls the SLS DataAgent OpenAPI directly (ACS3-HMAC-SHA256 signing); the endpoint
defaults to `starops.cn-beijing.aliyuncs.com` and can be overridden via `SLS_DATA_AGENT_ENDPOINT`:

- Create a session (thread)
- Start a conversation and stream the analysis process and conclusions (SSE)

See [references/api-reference.md](references/api-reference.md) and
[references/ram-policies.md](references/ram-policies.md) for details.

## Observability

Every HTTP request carries a `user-agent` header for tracing:

```
AlibabaCloud-Agent-Skills/alibabacloud-sls-data-agent/{session-id}
```

- `alibabacloud-sls-data-agent` — fixed skill identifier (matches the `name` field).
- `{session-id}` — a 32-character hex string, read from the `SKILL_SESSION_ID` environment variable. If the env var is not set, the script falls back to generating `uuid.uuid4().hex`. The same session-id is shared across all requests in a single invocation (CreateThread + CreateChat), enabling correlation of API calls in server-side logs.
