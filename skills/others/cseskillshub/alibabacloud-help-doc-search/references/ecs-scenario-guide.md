# ECS Documentation Scenario Workflow

Retrieval-first workflow for factual ECS questions. This scenario reuses the standard
`scripts/aliyun_help.py` subcommands; it only prescribes how to construct queries,
how to degrade when results are empty, and how to format the answer.

## When to apply this workflow

Apply it to factual ECS questions: instance types and instance families, product
capabilities, billing modes, best practices, quotas and usage limits, common error
messages, and API reference. For these questions the official documentation must be
retrieved **before** answering, instead of relying on model memory. ECS documentation
changes frequently — new instance generations are released, older instance types are
retired, and prices and quotas are adjusted — so model memory is often outdated. Model
memory may only be used as a last resort when retrieval has genuinely come back empty
through the whole degradation chain below, and in that case the answer must explicitly
tell the user that the claim is unverified against official documentation.

## Query construction

Build the search query from the user's question:

- Extract the core entities and attributes (e.g. the instance family names, the
  capability being asked about) and drop conversational filler.
- Prefer documentation/API terminology over colloquial wording; terminology matches
  document titles and summaries far better and greatly improves recall.
- For API-contract questions (exact parameters, error codes, RAM permission points of
  a specific ECS API) skip documentation search and go straight to
  `api-info ecs <ApiName>`, e.g. `api-info ecs DescribeInstanceTypeFamilies`.

Good vs. weak queries:

| User question (gist) | Weak query | Good query |
|---|---|---|
| "What is the difference between g6 and c6?" | `search "difference" -p ecs` | `search "g6 c6 instance family" -p ecs` |
| "I want to know what kinds of machines are available" | `search "machines" -p ecs` | `search "instance type family" -p ecs` (terminologized) |
| "How am I charged for a stopped pay-as-you-go instance?" | `search "stop charge" -p ecs` | `search "pay-as-you-go stopped instance billing" -p ecs` |

## Degradation chain: narrow, broad, rephrase

1. **Narrow**: start product-scoped —
   `python3 scripts/aliyun_help.py search "<terminology>" -p ecs`.
2. **Broad**: if the scoped search returns nothing or clearly irrelevant results,
   drop the product filter and search globally —
   `python3 scripts/aliyun_help.py search "<terminology>"`. (If the scoped search
   reported that the product index does not exist, verify the product code with
   `list-products` first.)
3. **Rephrase**: if still nothing, rephrase the query using terms taken from the
   titles of whatever partial results came back, or try synonyms; as a final fallback
   use WebSearch with `site:help.aliyun.com/zh/ecs/`.

For quota/limit questions, once a limits document is found, read its full body with
the `read` subcommand — the limits live in tables, which `read` converts to Markdown
automatically, and search summaries alone usually omit the concrete numbers.

## Answer format

Structure the answer in this order:

1. **Direct answer first** — state the conclusion up front (e.g. the key differences
   between the two instance families).
2. **Key details from the retrieved content** — specification tables, billing rules,
   or parameter tables quoted from what the retrieval actually returned, not from
   memory.
3. **Sources section** — end with a `Sources` block listing the help.aliyun.com URLs
   that back the answer so the user can verify each claim.

## Out of scope

Do not apply this scenario workflow to:

- Third-party software questions (e.g. OpenClaw, Hermes-Agent, QwenPaw and similar
  internal knowledge-base categories); they are not covered by this skill.
- Live state of the user's own account ("list my instances", "what is the status of
  this machine"); that is OpenAPI runtime data, not documentation retrieval, and this
  skill makes no credentialed calls.
- Questions about products other than ECS; answer them with the general search
  workflow described in SKILL.md rather than this ECS-specific flow.
