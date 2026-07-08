---
name: alibabacloud-agentloop-experience
description: >
  Use AgentLoop Recall to retrieve prior Alibaba Cloud AgentLoop experience or
  memory through the bundled SearchContext CLI. Trigger when the user asks to
  check, search, recall, retrieve, or look up prior experience, historical
  troubleshooting cases, task-specific memories, past fixes, environment
  context, comparable incidents, or successful workflows before or during work.
  Also use for Chinese requests such as 先查历史经验、回忆类似案例、检索环境记忆、
  召回过往排障记录、看看之前有没有处理过类似问题.
license: Apache-2.0
compatibility: >
  Requires Node.js 18 or later and network access to the configured AgentLoop
  Recall or SearchContext endpoint. Intended for qwen-code, qoder, and openclaw.
metadata:
  domain: coding
  owner: cloud-skills-cloudnative
  contact: cloud-skills-cloudnative@alibaba-inc.com
---

# AgentLoop Recall

Use this skill to recall AgentLoop experience or memory through the local CLI at `scripts/search_context.js`.
The CLI reads auth and endpoint configuration from `recall.env`; never pass tokens or secrets as CLI arguments.

## Prerequisites

Install Node.js 18 or later. The script uses only Node.js built-in modules and does not require npm packages.

Configure recall credentials and endpoint in `~/.agentloop/recall.env`, the nearest project `.agentloop/recall.env`, or process environment variables. Use `assets/recall.env.example` as the template.

## Workflow

1. Before any recall call, ensure the user has approved sending the query text to the configured AgentLoop Recall endpoint. If the current user request explicitly asks to check, search, recall, or look up prior experience or memory, that request is approval for that matching query.
2. After approval, call recall once for environment and task context before choosing an implementation path. Run the CLI with `node scripts/search_context.js`, not with `bash`. Include `--confirm-outbound` in the CLI command.
3. For later debugging, ask for approval again if the new query would transmit materially different task data, then call recall with a focused query based on the concrete error, case, service, API, file path, or observed symptom.
4. Use returned results as context only. Verify recalled content against the current repository, logs, and user request before acting on it.

Build concise queries. Include stable identifiers from the user request or tool output, such as service name, request id, case id, error text, API action, benchmark, module, or goal. Do not invent identifiers.

If recall fails or returns no results, continue the original task. Treat recalled content as helpful context, not as authority; verify it against the current repository, logs, and user request.

## CLI

Run:

```bash
node scripts/search_context.js search \
  --query "current task, error, case, service, or goal" \
  --context-type experience \
  --confirm-outbound \
  --limit 5 \
  --threshold 0.6 \
  --filter-json '{}'
```

Required:
- `--query string`
- `--context-type experience|memory`
- `--confirm-outbound` after explicit user approval to transmit query data

Optional:
- `--limit integer` defaults to `5`
- `--threshold number` defaults to `0.6`
- `--filter-json object-as-json-string` defaults to `{}`

## Input Example

```bash
node scripts/search_context.js search \
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
- If executing `scripts/search_context.js` directly fails because the environment strips executable bits or mounts the skill as non-executable, rerun the same command with `node scripts/search_context.js`.
- If configuration is missing or invalid, the CLI returns a JSON object with `error` populated and `results: []`.
- If recall returns no relevant results, continue the original task without blocking.
- If recalled content conflicts with the current repository, logs, or user request, trust the current evidence.

Auth:
- Read from `recall.env`.
- Never pass AK, SK, bearer token, or other secret material through CLI arguments.
- Use HTTPS endpoints for real credentials. HTTP is accepted only for localhost.

Read `references/search-context-cli.md` only when you need the exact config precedence, HTTP contract, endpoint security rules, or response normalization details. Read `references/ram-policies.md` only when you need the permission and data-flow declaration.
