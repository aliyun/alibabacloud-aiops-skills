# Create a dashboard

1. Establish the analysis goal and exact SLS sources. Read the [datasource overview](../datasources/overview.md)
   and the selected source reference. Discover only missing fields, metrics or labels.
2. Design queries and expected results before choosing chart types. Use the
   [chart input contracts](../charts/charts.md) and [design principles](../design/principles.md)
   to define charts, controls, relationships and layout.
3. Prefer a [Plan](../model/plan.md) when designing new content. If the user supplies complete Dashboard
   JSON, validate it directly. Replace template sources with the target resources.
4. For a Plan, run dashboard.py build --plan plan.json --output final.json; repeat
   --facts for supplied [fact files](../model/source-facts.md). For complete JSON, run dashboard.py validate
   --input final.json. These checks do not execute queries.
5. For online verification, execute changed queries. Use explicit
   test values for [variables](../features/variables.md) and preserve placeholders in the final configuration.
6. Follow [publishing](publish.md) when publishing is authorized; otherwise deliver the artifact
   with performed checks and unverified items.
