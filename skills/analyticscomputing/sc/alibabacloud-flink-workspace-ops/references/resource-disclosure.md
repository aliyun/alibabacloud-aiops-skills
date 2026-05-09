# Resource Loading Policy

This skill keeps `SKILL.md` concise and loads detailed docs only when needed.

## Entry Contract (Always Loaded)

- `SKILL.md` — boundary, trigger priority, safety baseline, execution baseline.
- Keep concise; no long command encyclopedia.

## Loading Strategy

1. **After Trigger**: Load execution protocol and command routing table once per task.
2. **On Demand**: Load only the specific deep document required by current context (error handling, verification, RAM policies, full command catalog, playbooks, etc.).
3. Refer to the "Resources" section in `SKILL.md` for the complete list of available documents and when to load each.

## Loading Discipline

1. Do not preload all references.
2. Start from the entry contract, then task docs, then only the needed deep doc.
3. Prefer the smallest sufficient context for the current user request.
