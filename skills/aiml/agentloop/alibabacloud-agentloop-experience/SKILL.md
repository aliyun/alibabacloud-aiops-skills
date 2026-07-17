---
name: alibabacloud-agentloop-experience
description: >
  Proactively use AgentLoop Recall to retrieve prior Alibaba Cloud AgentLoop
  experience through the bundled SearchContext CLI whenever the user asks or
  implies that prior work may help. Trigger for requests to check, search,
  recall, retrieve, look up, review, consult, reference, or compare prior
  experience, historical troubleshooting cases, past fixes, comparable
  incidents, lessons learned, old runbooks, previous remediations, or
  successful workflows before or during work. Also trigger for Chinese requests
  such as 先查历史经验、回忆类似案例、召回过往排障记录、看看之前有没有处理过类似问题、
  参考以前怎么处理、找找之前的踩坑记录、翻一下历史排障、有没有类似经验、先看看过去的案例.
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

Use this skill proactively — **recall prior experience first**. Before you start analyzing or implementing, make recalling prior AgentLoop experience one of your very first actions, using the local CLI at `scripts/search_context.js`.
The CLI reads auth and endpoint configuration from `recall.env`; never pass tokens or secrets as CLI arguments.

Favor using this skill when the user mentions prior experience, similar cases, historical fixes, previous incidents, old runbooks, lessons learned, or asks to avoid repeating past mistakes. The request does not need to use the exact words "recall" or "experience"; phrases like "有没有类似", "以前怎么处理", "先参考过去", "少走弯路", "look up old notes", or "anything we learned before" are enough.

Current scope: only `experience` context is supported. `memory` context is reserved for a future rollout and should not be used in prompts, examples, or evals.

## Prerequisites

Install Node.js 18 or later. The script uses only Node.js built-in modules and does not require npm packages.

Configure recall credentials and endpoint in `~/.agentloop/recall.env`, the nearest project `.agentloop/recall.env`, or process environment variables. Use `assets/recall.env.example` as the template.

## Workflow

1. Before any recall call, ensure the user has approved sending the query text to the configured AgentLoop Recall endpoint. Treat the current request as approval for a matching query when it asks or implies checking prior work, including "先查", "看看之前", "有没有类似", "参考历史", "回忆案例", "avoid repeating past mistakes", or similar wording.
2. After approval, strongly prefer to recall up front: run recall at least once before choosing an implementation path, and again whenever you hit a non-trivial obstacle or change your approach. Recall whenever the current task includes a concrete service, error, incident, operation, migration, performance issue, or debugging goal and prior experience could plausibly help. Run the CLI with `node scripts/search_context.js`, not with `bash`. Include `--confirm-outbound` in the CLI command.
3. For later debugging, ask for approval again if the new query would transmit materially different task data, then call recall with a focused query based on the concrete error, case, service, API, file path, or observed symptom.
4. Use returned results as context only. Verify recalled content against the current repository, logs, and user request before acting on it.

Build concise queries. Include stable identifiers from the user request or tool output, such as service name, request id, case id, error text, API action, benchmark, module, or goal. Do not invent identifiers.

If the request is mildly underspecified but the service, symptom, or goal is clear, build the best concise query from the available facts and use defaults (`--limit 5`, `--threshold 0.6`, `--filter-json '{}'`). Ask a clarifying question only when there is no usable query target or when multiple materially different recall directions are equally likely.

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
- `--context-type experience`
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
