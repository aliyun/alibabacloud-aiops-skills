# Result Presentation

After results pass validation, prefer the current agent's chart capabilities. Use Markdown tables when no chart tool is available.

- Use line charts for trends, bar charts for TopN or category comparisons, and tables for details. Answer directly for a single value.
- Label charts with metric definitions, units, project/logstore, and the actual query time window.
- Use only values returned by executed queries. Do not invent missing groups or fill absent rows with zeros.
- Distinguish multiple data sources by origin. Combine results only when definitions, filters, and time windows match and the results can be combined.
- Include key conclusions, executed queries, and coverage limits alongside charts. Exclude credentials and unredacted logs.
