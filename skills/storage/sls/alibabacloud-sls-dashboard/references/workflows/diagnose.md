# Diagnose a dashboard

Record observed and expected behavior, effective sources and time, and available
evidence. A screenshot proves visible state; stored JSON proves configuration.
Neither alone proves the root cause.

Trace the affected path: [source identity/access](../datasources/overview.md) → query and
[effective time](../queries/time-and-limits.md) → [filter/token/Adhoc input](../features/variables.md)
→ [returned fields and series](../model/result-shapes.md) → [transformations](../features/transformations.md)
→ [display bindings](../charts/charts.md) → [action context](../features/actions.md). Use read-only queries only when they resolve a missing fact.

Distinguish empty successful results from syntax, access, partial-response and binding
failures. Present likely causes supported by evidence and the shortest checks to
distinguish them. Apply a scoped fix through the [edit workflow](edit.md) when
requested. Do not silently broaden time, replace a StoreView with a member, or invent
field names.

For commands that fail before returning data, use [skill usage troubleshooting](../troubleshooting.md).
