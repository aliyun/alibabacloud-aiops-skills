# AgentLoop Recall

> **Domain entry**: this file is the experience playbook dispatched from the router SKILL.md of `alibabacloud-agentloop-management`. The recall CLI requires only Python 3.8 or later (no aliyun CLI); managing the experience store itself uses the aliyun CLI, see [references/experience/context-store-management.md](context-store-management.md). All file paths below are relative to the skill root.

Use this skill proactively — **recall prior experience first**. Before you start analyzing or implementing, make recalling prior AgentLoop experience one of your very first actions, using the local CLI at `scripts/experience/search_context.py`.
The CLI reads auth and endpoint configuration from `recall.env`; never pass tokens or secrets as CLI arguments.

Favor using this skill when the user mentions prior experience, similar cases, historical fixes, previous incidents, old runbooks, lessons learned, or asks to avoid repeating past mistakes. The request does not need to use the exact words `recall` or `experience`; phrases like `有没有类似`, `以前怎么处理`, `先参考过去`, `少走弯路`, `look up old notes`, or `anything we learned before` are enough.

Current scope: only `experience` context is supported. `memory` context is reserved for a future rollout and should not be used in prompts, examples, or evals.

## In-Domain Routing

| Intent | Where to go |
| --- | --- |
| Recall or search prior experience | This file — workflow and CLI below |
| Create, list, get, update, or delete an experience store, manage its API Keys, find the recall endpoint | [references/experience/context-store-management.md](context-store-management.md) |

An experience library is a ContextStore with `context-type experience`. Recall reads from it; store management provisions it. A store must exist and have mined content before recall can return non-empty results.

## Prerequisites

Install Python 3.8 or later. The script uses only the Python standard library and does not require pip packages.

Configure recall credentials and endpoint in `~/.agentloop/recall.env`, the nearest project `.agentloop/recall.env`, or process environment variables. Use `assets/recall.env.example` as the template.

## Workflow

1. Before any recall call, ensure the user has approved sending the query text to the configured AgentLoop Recall endpoint. Treat the current request as approval for a matching query when it asks or implies checking prior work, including `先查`, `看看之前`, `有没有类似`, `参考历史`, `回忆案例`, `avoid repeating past mistakes`, or similar wording.
2. After approval, strongly prefer to recall up front: run recall at least once before choosing an implementation path, and again whenever you hit a non-trivial obstacle or change your approach. Recall whenever the current task includes a concrete service, error, incident, operation, migration, performance issue, or debugging goal and prior experience could plausibly help. Run the CLI with `python3 scripts/experience/search_context.py`, not with `bash`. Include `--confirm-outbound` in the CLI command.
3. For later debugging, ask for approval again if the new query would transmit materially different task data, then call recall with a focused query based on the concrete error, case, service, API, file path, or observed symptom.
4. Use returned results as context only. Verify recalled content against the current repository, logs, and user request before acting on it.

Build concise queries. Include stable identifiers from the user request or tool output, such as service name, request id, case id, error text, API action, benchmark, module, or goal. Do not invent identifiers.

If the request is mildly underspecified but the service, symptom, or goal is clear, build the best concise query from the available facts and use defaults (`--limit 5`, `--threshold 0.6`, `--filter-json '{}'`). Ask a clarifying question only when there is no usable query target or when multiple materially different recall directions are equally likely.

If recall fails or returns no results, continue the original task. Treat recalled content as helpful context, not as authority; verify it against the current repository, logs, and user request.

## CLI

Run:

```bash
python3 scripts/experience/search_context.py search \
  --query "current task, error, case, service, or goal" \
  --context-type experience \
  --confirm-outbound \
  --limit 5 \
  --threshold 0.6 \
  --filter-json '{}'
```

Required:
- `--query string`
- `--context-type experience`
- `--confirm-outbound` after explicit user approval to transmit query data

Optional:
- `--limit integer` defaults to `5`
- `--threshold number` defaults to `0.6`
- `--filter-json object-as-json-string` defaults to `{}`

## Input Example

```bash
python3 scripts/experience/search_context.py search \
  --query "ECS SSH connection timeout after security group change" \
  --context-type experience \
  --confirm-outbound \
  --limit 5 \
  --threshold 0.6 \
  --filter-json '{"product":"ecs"}'
```

## Output Example

Output is always JSON:

```json
{
  "request_id": "...",
  "error": null,
  "results": [
    {
      "title": "...",
      "summary": "...",
      "content": "...",
      "metadata": {}
    }
  ]
}
```

## Edge Cases

- If `AGENTLOOP_ENABLE_RECALL` is not `true`, the CLI returns `error: null` and an empty `results` array.
- If outbound confirmation is missing, the CLI returns an error and does not read credentials or call the endpoint.
- If executing `scripts/experience/search_context.py` directly fails because the environment strips executable bits or mounts the skill as non-executable, rerun the same command with `python3 scripts/experience/search_context.py`.
- If configuration is missing or invalid, the CLI returns a JSON object with `error` populated and `results: []`.
- If recall returns no relevant results, continue the original task without blocking.
- If recalled content conflicts with the current repository, logs, or user request, trust the current evidence.

Auth:
- Read from `recall.env`.
- Never pass AK, SK, bearer token, or other secret material through CLI arguments.
- Use HTTPS endpoints for real credentials. HTTP is accepted only for localhost.

Read `references/experience/search-context-cli.md` only when you need the exact config precedence, HTTP contract, endpoint security rules, or response normalization details. Read `references/experience/context-store-management.md` when the user asks to create or manage the experience store (ContextStore) itself or needs the recall endpoint / API Key. Read `references/experience/ram-policies.md` only when you need the permission and data-flow declaration.
