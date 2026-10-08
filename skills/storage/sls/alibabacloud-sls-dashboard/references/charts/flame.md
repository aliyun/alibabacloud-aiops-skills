# Flame graph

Use when exploring sampled call stacks or comparing profiles.

## Usage

- Supply one query returning a compatible Flamebearer profile as a serialized JSON string in `_col0` of its first row, not an object or stack strings.
- Only the first row is read; profiles in multiple rows are not combined. Aggregate profiles in the query or upstream service before returning one `_col0` value.
- Missing `_col0`, invalid JSON, or a `metadata.format` other than `single` or `double` produces a data-format error.
- Keep profile metadata, names, levels, tick counts, sample rate and units intact. Use a verified profile-producing query.

## Configuration parameters

Paths are relative to `display`.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `flameOption.flameChartVisType` | string | No | — | flamegraph, table, or both. |
| `flameOption.showTableSearch` | boolean | No | — | Show profile-table search when a table is visible. |

## Profile fields

| Field | Meaning |
| --- | --- |
| `version` | Profile format version. |
| `metadata.format` | single for one profile; double for comparison profiles. |
| `metadata.sampleRate` | Sampling rate. |
| `metadata.spyName` | Profile collector type. |
| `metadata.units` | Measurement unit. |
| `flamebearer.names` | Stack-frame name table. |
| `flamebearer.levels` | Encoded stack-frame levels. |
| `flamebearer.numTicks` | Total sample ticks. |
| `flamebearer.maxSelf` | Maximum self value. |

## Examples

Display fragments:

### Profile flamegraph

```json
{
  "flameOption": {
    "flameChartVisType": "flamegraph",
    "showTableSearch": false
  }
}
```

### Profile with table

```json
{
  "flameOption": {
    "flameChartVisType": "both",
    "showTableSearch": true
  }
}
```
