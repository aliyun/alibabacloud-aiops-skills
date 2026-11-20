# Create a dashboard

A dashboard combines [queries and sources](../datasources/overview.md),
[chart bindings](../charts/charts.md), [controls](../features/variables.md) and
[layout](../features/layout.md). The user's questions, supplied configuration and
available query results provide the starting context. The [design guide](../design.md)
connects common analysis goals to suitable panels.

## Plan construction

A [Plan](../model/plan.md) is a recommended, optional way to create a standard grid
dashboard from simple source, query, chart and control settings:

Start with the [standard dashboard template](../assets/plans/standard-charts.json)
or choose a chart's [fields and config](../model/plan.md#choose-a-chart).

```sh
python3 scripts/dashboard/dashboard.py build --plan plan.json --output final.json
```

`--report build-check.json` saves the build's validation report separately.
The generated `final.json` can be used as the starting point for further customization.

## Dashboard JSON

For custom charts or changes to an existing dashboard, edit
Dashboard JSON directly. Complete [chart examples](../charts/examples.md) can
also be adapted into a new dashboard. The [object model](../model/dashboard.md)
describes IDs, display names and query fields. Output aliases connect query results
to chart bindings.

The [publishing guide](publish.md) shows CLI commands for structured arguments and
complete Dashboard JSON.

## Available checks

[Validation tools](../validation/checks.md) check local configuration. Source queries
can establish returned fields and values, including example selections for
[variables](../features/variables.md).
