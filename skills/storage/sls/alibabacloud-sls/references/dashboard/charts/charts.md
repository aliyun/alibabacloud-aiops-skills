# Choose a chart

Select a chart by the question and query result shape. Each reference describes its
Dashboard JSON fields; [Plan](../model/plan.md#chart-options) configuration is listed
separately. For complete starting configurations, use [chart examples](examples.md).

## Trends and comparisons

| Chart | Input and use |
| --- | --- |
| [Line](linepro.md) | Time/value series or a wide table |
| [Grouped series](aggpro.md) | Time/category/value rows |
| [Metric comparison](metricspro.md) | Native metric series with interactive historical comparison |
| [Bar](barpro.md) | Categories and one or more numeric measures |
| [Radar](radarchart.md) | Several series across comparable dimensions |

## Values and distributions

| Chart | Input and use |
| --- | --- |
| [Statistic](statpro.md) | A KPI, reduced series, or labeled value rows |
| [Bar gauge](burgauge.md) | Progress or utilization with a meaningful range |
| [Semicircular gauge](gauge.md) | Values against a fixed or query-derived range |
| [Pie / donut](piepro.md) | Non-negative parts of a whole |
| [Treemap](treemappro.md) | One level of categories and sizes |
| [Histogram](histogram.md) | Observations and weights to bucket |
| [Box plot](box.md) | Minimum, quartiles, median and maximum |
| [Scatter / bubble](scatterchart.md) | Time/category positions, numeric values and optional size |

## Tables and states

| Chart | Input and use |
| --- | --- |
| [Table](tablepro.md) | Records or fields with formatted cells |
| [Pivot table](crosstable.md) | Row dimensions, a column category and a measure |
| [Data heatmap](heatmap.md) | One reduced value per field or metric series |
| [Status blocks](colorblockpro.md) | Time/category, group and state values |
| [Polystat](polystat.md) | Metric series represented as status nodes |
| [Event timeline](timeline.md) | One ordered row per event |
| [State timeline](timelinepro.md) | State change points or explicit intervals |

## Relationships and geography

| Chart | Input and use |
| --- | --- |
| [Funnel](funnelpro.md) | Stages displayed by decreasing value |
| [Sankey](sankeypro.md) | Acyclic source/target flows with weights |
| [Topology](topologypro.md) | Explicit parent/child nodes and optional metrics |
| [China map](chinadistrictmap.md) | Administrative regions or coordinates and weights |
| [World map](worlddistrictmap.md) | Country names/codes and weights |
| [Geographic points](geomappro.md) | Latitude,longitude strings and values |
| [Geographic heat](heatmappro.md) | Weighted geographic coordinates |
| [Trajectory](trajectory.md) | Object IDs and time-ordered locations |

## Specialized results

| Chart | Input and use |
| --- | --- |
| [Flame graph](flame.md) | A serialized Flamebearer profile |
| [Word cloud](cloudwordPro.md) | Words and numeric weights |
| [Time-series algorithms](timeseriesPro.md) | Original SLS algorithm output |
| [Time-series facets](facetPro.md) | Decomposition, cluster or root-cause result groups |

## Content and controls

| Chart | Input and use |
| --- | --- |
| [Markdown](markdownpro.md) | Notes or first-row query-field text |
| [Rich text](textpro.md) | Markdown or static HTML |
| [Static text](text.md) | Free-layout annotations |
| [Image](imagepro.md) | An image URL and builtin query |
| [SVG](svg.md) | An SVG URL in free layout |
| [Shapes](basic_graphics.md) | Rectangles or diamonds |
| [Row](dashboardrow.md) | Collapsible grid sections |
| [Dropdown](droplistpro.md) | Field filters, tokens or metric label filters |
