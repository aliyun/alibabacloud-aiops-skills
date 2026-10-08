# Common chart examples

Use these complete grid dashboards when you want a small starting configuration.
Each dashboard contains one chart with its display and data or content configuration.
SQL examples supply small illustrative datasets; replace their SQL with your own
query when using the chart for live metrics.

## Choose an example

| Chart | Result fields | Expected display | Dashboard JSON | Details |
| --- | --- | --- | --- | --- |
| Table | `service`, `requests` | Three rows: API 40, Worker 25, Web 15. | [tablepro.json](../../assets/dashboards/charts/tablepro.json) | [Table settings](tablepro.md), [field formatting](../features/field-overrides.md) |
| Line | `time`, `requests` | One line with five points, five minutes apart. | [linepro.json](../../assets/dashboards/charts/linepro.json) | [Line settings](linepro.md), [axes](../features/xy-options.md) |
| Pie | `service`, `requests` | API 50%, Worker 31.25%, Web 18.75% of 80 requests. | [piepro.json](../../assets/dashboards/charts/piepro.json) | [Pie settings](piepro.md), [legend](../features/legend.md) |
| Bar | `service`, `requests` | Three vertical bars with category labels and request counts. | [barpro.json](../../assets/dashboards/charts/barpro.json) | [Bar settings](barpro.md), [axes](../features/xy-options.md) |
| Sankey | `source`, `target`, `requests` | Web sends 80 to API and 20 to Cache; API sends 60 to Database and 20 to Worker. | [sankeypro.json](../../assets/dashboards/charts/sankeypro.json) | [Flow settings](sankeypro.md) |
| Semicircular gauge | `utilization` | 68.5% on a 0–100 dial. | [gauge.json](../../assets/dashboards/charts/gauge.json) | [Gauge settings](gauge.md), [numeric formats](../features/standard-options.md) |
| Histogram | `latency_ms`, `samples` | Twelve observations grouped into 20 ms buckets from 0 to 100 ms. | [histogram.json](../../assets/dashboards/charts/histogram.json) | [Bucket settings](histogram.md) |
| Radar | `dimension`, `team_a`, `team_b` | Two score polygons across five dimensions with comparable 0–100 scores. | [radarchart.json](../../assets/dashboards/charts/radarchart.json) | [Radar settings](radarchart.md) |
| Markdown | No query | A heading, a list, and a bold data note. | [markdownpro.json](../../assets/dashboards/charts/markdownpro.json) | [Markdown and placeholders](markdownpro.md) |
| Rich text | No query | An HTML runbook note with a heading and owner. | [textpro.json](../../assets/dashboards/charts/textpro.json) | [Content modes](textpro.md) |
| Image | Builtin simulated data | A static image loaded from its URL. | [imagepro.json](../../assets/dashboards/charts/imagepro.json) | [Image and required builtin configuration](imagepro.md) |

## Use an example

Copy the selected Dashboard JSON. Set `dashboardName` to the destination name.
For an SLS query, set `charts[0].search.chartQueries[0].region`, `project`, and
`logstore` to your source. Keep query output aliases aligned with the bindings.

From the skill directory:

```sh
python3 scripts/dashboard.py validate --input assets/dashboards/charts/barpro.json
```

Validation is offline. Follow [publishing](../workflows/publish.md) to create a
dashboard and inspect its page. Use the JSON's `dashboardName` for `--name`.
Markdown and rich-text examples need no datasource.
Keep the image example's builtin query when replacing its sample image URL and
alternative text so the image displays.

## Adapt the configuration

- For a trend, return numeric Unix seconds in `time` and sort them ascending.
- For a pie or bar, aggregate to one row per category before binding the result.
- For a flow, aggregate each directed source/target pair into one weight.
- For the gauge, a value of 68.5 means 68.5%, with bounds 0 and 100. A 0–1
  fraction needs `format="percent_decimal"` and bounds 0 and 1.
- For the histogram, `samples=1` gives each observation one count. If the query
  returns preaggregated frequencies, bind those frequencies as the weight column.
- For the radar, use measures on comparable scales so the polygons remain meaningful.

Use [standard options](../features/standard-options.md) for units and decimals,
[field overrides](../features/field-overrides.md) for individual columns or
series, and the linked chart references for further options.
