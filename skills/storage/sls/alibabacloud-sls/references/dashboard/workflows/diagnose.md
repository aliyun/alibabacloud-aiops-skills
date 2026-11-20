# Diagnose dashboard behavior

The symptom helps select the relevant information:

| Symptom | Useful checks |
| --- | --- |
| Missing or unexpected rows | [Source identity](../datasources/overview.md), [query time](../queries/time-and-limits.md), filters and actual query results |
| Incorrect values or series | [Result shape](../model/result-shapes.md), [transformations](../features/transformations.md), aggregation and chart bindings |
| Controls do not affect charts | [Filter/token scope and consumers](../features/variables.md) |
| Incorrect display | [Chart settings](../charts/charts.md), [appearance](../index.md#appearance), and the current page |
| Click navigation is wrong | [Action fields and time context](../features/actions.md) |
| Command fails | [Troubleshooting](../troubleshooting.md) |

Stored JSON shows configuration, query responses show returned data, and the page
shows rendering and interactions. CLI reads, local validation and page inspection
can provide the evidence needed for the affected part of the dashboard.

The [edit guide](edit.md) describes configuration changes when a fix is requested.
