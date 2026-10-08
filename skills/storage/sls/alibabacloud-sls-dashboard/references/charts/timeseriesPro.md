# Time-series algorithm chart

Use when displaying SLS smoothing, detection, forecasting, regression, or root-cause algorithm results.

## Usage

- Use one query returning original output from a supported SLS time-series analysis function.
- Preserve the output structure and names; do not add aliases, extra aggregation or ordinary XY bindings.
- Use linepro for ordinary time/value trends.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `innerTokenOption` | object[] | No | [] | Static chart-local selectors; see [local variables](../features/local-variables.md). |

## Query and display

Examples include `ts_smooth_simple`, `ts_smooth_fir`, `ts_smooth_iir`,
`ts_period_detect`, `ts_find_peaks`, `ts_cp_detect`, `ts_breakout_detect`,
`ts_predicate_ar`, `ts_predicate_simple`, `ts_predicate_arma`, `ts_predicate_arima`,
`ts_regression_predict` and `rca_kpi_search_complex`.

The server supplies `marker` as query-response metadata, not a Dashboard JSON
option. Do not add it to chart, query, or `display` configuration.

The display fragment can be empty:

```json
{}
```

A missing or unsupported `marker` produces a help message and table. The selected
algorithm determines axes, series, prediction bands and anomaly points.
