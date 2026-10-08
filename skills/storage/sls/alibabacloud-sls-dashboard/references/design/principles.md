# Design principles

Decide purpose and audience → operational questions → verified sources and query
results → controls and dependencies → charts → sections and layout.

For each user question, choose a chart whose [input contract](../charts/charts.md)
matches the query result.

Organize overview → trends → breakdown/ranking → evidence/details. Prefer bounded
dimensions for controls and series. Fix requested resource constraints in queries;
optional controls must not silently widen them.

Recommend a 24-column grid with non-overlapping panels, row sections and stable IDs.
Use free layout only when a custom layout requires free positioning or overlap.
Honor requested chart types when their input requirements are met; explain
conflicts before choosing another type. Preserve requested free layouts and
existing designs.
