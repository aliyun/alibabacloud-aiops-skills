# Agent tool configuration: defaults and explicit overrides

Sources: user-provided configuration clarification, **2026-10-29**; knowledge retrieval contract checked against the official Create Agent documentation on **2026-11-09**.

Use this reference when creating or updating an Agent, or supplying an Agent configuration through another API that accepts the same `tools` structure. The rule applies within each tool group, including `builtin_toolkit` and `mcp_toolkit`.

## Priority within a tool group

For each tool, look for its name in that group's `configs[]`:

- **An explicit entry exists:** the explicit configuration takes precedence over `default_config`.
- **No entry exists:** the tool uses the group's `default_config`.

For `enabled`, this means:

| `default_config.enabled` | Matching entry in `configs[]` | Effective enablement |
| --- | --- | --- |
| `false` | No entry | Disabled |
| `false` | `enabled: true` | Enabled |
| `true` | No entry | Enabled |
| `true` | `enabled: false` | Disabled |

`default_config` supplies the fallback; it is not a master switch that blocks explicit enables or forces explicit disables back on. The older claim that `default_config.enabled: true` never delivers tools is superseded by this clarification. Historical missing-tool observations do not establish that general rule.

## Recommended: disable by default, explicitly enable what is needed

Declare the tools the Agent needs in `configs[]` and set `default_config.enabled` to `false`. For example, this `tools` fragment enables `bash` and `read`, explicitly disables `write`, and leaves other configurable tools disabled:

```json
{
  "tools": [
    {
      "type": "builtin_toolkit",
      "default_config": {"enabled": false},
      "configs": [
        {"name": "bash", "enabled": true},
        {"name": "read", "enabled": true},
        {"name": "write", "enabled": false}
      ]
    }
  ]
}
```

This keeps the enabled tool inventory stable as the toolkit evolves: a newly added tool remains disabled until explicitly enabled. Review and add new tools deliberately. Explicit declaration is the recommended strategy for predictable behavior, not an API requirement for every tool to be usable.

For MCP, apply the same strategy to each `mcp_toolkit`, and keep its `mcp_server_name` aligned with the mounted `mcp_servers[].name`; tool enablement does not replace service mounting.

## Knowledge retrieval with `search_knowledgebases`

Knowledge retrieval needs an explicit `configs[]` entry with `enabled: true` and `params.knowledge_application_id` set to the published retrieval service ID (`aid-…`). `params` is at the same level as `name` and `enabled`. The ID is not an individual knowledge base ID. At most one such entry is allowed; an enabled default does not supply the missing service configuration. Preserve other tools when updating the toolkit.

For complete configuration, prerequisites and runtime error handling, read [knowledge and memory integration](knowledge-and-memory.md#configure-knowledge-retrieval).

## Alternative: enable by default to follow toolkit additions

If the Agent should automatically adopt new tools as the ecosystem evolves, set `default_config.enabled` to `true`. Tools absent from `configs[]`, including newly added ones, then use that enabled default. Explicit entries still take precedence: for example, `{"name": "bash", "enabled": false}` keeps `bash` disabled even with the default enabled.

Choose this strategy deliberately because the available tool inventory can grow without editing the Agent's explicit tool list. These strategies govern configurable toolkit tools; platform-injected runtime tools such as `mark_artifacts` are described separately in [core concepts](../product/concepts.md#tool-and-mcp).

## Task planning with `todo_write`

`todo_write` maintains a structured to-do list of task steps and their status, for breaking down long tasks and tracking multi-step execution progress. Capability source: [user clarification, 2026-11-02](../product/status.md#task-planning-tool-user-clarification-2026-11-02).

To enable it under the explicit-tool strategy above, add this entry to the existing `builtin_toolkit.configs[]`, preserving the other tool entries:

```json
{"name": "todo_write", "enabled": true}
```

This is a toolkit enablement entry, not the tool's invocation payload. The invocation schema is not recorded here; use the actual tool definition for parameters and supported status values.
