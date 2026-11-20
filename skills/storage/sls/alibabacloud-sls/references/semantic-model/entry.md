# Semantic model

Provides business context for understanding logs, identifying Project/Logstore data sources and applying field, term and metric definitions.

## When to use

- Use when business definitions or source selection affect log discovery, queries, investigations, dashboards or alerts, or when the user explicitly requests semantic models.
- Pure query-syntax questions and resource operations without semantic dependencies can use the corresponding capability directly.

## Check availability first

Follow [Availability checks](availability.md) for the selected model/resource scope under the confirmed CLI profile, region and endpoint. Reuse sufficient checks from the same task and identity.

**Only after availability is confirmed, read [the detailed guide](guide.md).** Check task-specific definition coverage there.

For unavailable or unconfirmed results, follow [result handling](availability.md#result-handling). Only required semantic-model use warrants reporting and troubleshooting; otherwise continue the original task with independently verified definitions, preserving its scope and constraints.
