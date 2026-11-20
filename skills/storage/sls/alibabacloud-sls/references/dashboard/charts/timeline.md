# Event timeline

Use when presenting discrete events as time-ordered cards, rather than state-duration intervals.

## Usage

Use one query and one row per event, ordered by its event time.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `queryOptionMap.<queryName>.xAxisKey` | string | Yes | None | Event-time column. |
| `queryOptionMap.<queryName>.yAxisKeys` | string[] | Yes | None | One or more columns shown in event cards; their field colors affect card backgrounds. |
| `queryOptionMap.<queryName>.tipColumn` | string[] | No | All row fields except built-in system fields | Supplemental tooltip columns. [] removes supplemental fields; with merge=false, the tooltip still includes event time separately. |
| `timeAxisOptions.dataColumn` | number | No | 10 | Visible event count: 4, 6, 8, or 10. Navigation buttons move through events without truncating the query result. |
| `timeAxisOptions.merge` | boolean | No | — | true places time labels outside cards beside the axis; false places them inside cards. Does not aggregate event rows. |

See [field colors](../features/standard-options.md) and [field overrides](../features/field-overrides.md) when styling card content.

## Examples

### Ordered event timeline

Query `A` formats Unix seconds in the `Asia/Shanghai` time zone and sorts by event time:

```sql
* | select date_format(from_unixtime(event_ts, 'Asia/Shanghai'), '%Y-%m-%d %H:%i:%s') as event_time,
           summary, severity, source
from unnest(
  array[1790787000, 1790787060, 1790787120],
  array['Deploy', 'Warning', 'Recovered'],
  array['info', 'warn', 'info'],
  array['audit', 'audit', 'audit']
) as t(event_ts, summary, severity, source)
order by event_ts
```

Display fragment:

```json
{
  "isTimeSeries": false,
  "timeAxisOptions": {
    "dataColumn": 6,
    "merge": true
  },
  "queryOptionMap": {
    "A": {
      "xAxisKey": "event_time",
      "yAxisKeys": [
        "summary"
      ],
      "tipColumn": [
        "severity",
        "source"
      ]
    }
  }
}
```
