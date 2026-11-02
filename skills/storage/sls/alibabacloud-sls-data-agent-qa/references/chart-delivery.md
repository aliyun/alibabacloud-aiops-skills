# Chart Delivery

Use the current host's chart capabilities near the conclusions, or Markdown tables when chart capabilities are unavailable. Use line charts for trends, bar charts for TopN/category comparisons, pie charts for shares across a few categories, tables for multi-column details, and an appropriate host-supported chart for flows by time and category.

- Reuse the data source and query from the corresponding validated query, allowing only whitespace changes that preserve its meaning. Do not change filters, literals, fields, aliases or calculations, or derive a new query for a chart.
- Reuse the corresponding query response's top-level `timeRange.from/to` directly for the time window.
- Use a title that describes the query's business purpose. Axes or category dimensions must correspond to actual column names in the returned data. Set units only when the obtained metric definition explicitly specifies them.
- Organize charts by answer branch. Do not create separate charts for internal retries or individual time partitions. Present partitioned or combined cross-source results as text or Markdown tables when no corresponding validated query exists.
