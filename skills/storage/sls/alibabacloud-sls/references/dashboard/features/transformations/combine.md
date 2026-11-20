# Align and combine

Use these objects in `chart.search.transformers[]`. See the [common fields](../transformations.md#common-fields).

- [join](#join)
- [seriesToColumns](#seriestocolumns)
- [merge](#merge)
- [concatenate](#concatenate)

## join

Use when matching queries by explicit keys.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `joinType` | string | Yes | None | leftJoin keeps keys from the first result; rightJoin from the last; fullJoin from every result. |
| `joinFields` | string[] | Yes | None | Key columns shared by participating results. |

Unmatched cells are missing, not zero. A result lacking the key fields cannot
supply joined values. For A=(h1,10),(h2,20) and B=(h2,80),(h3,70), a left join
on host yields h1 with 10/missing and h2 with 20/80.

### Example: Join results by host

```json
{
  "name": "TA",
  "type": "join",
  "joinType": "leftJoin",
  "joinFields": ["host"]
}
```

## seriesToColumns

Use when aligning series by time or another single key.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `byField` | string | No | Time | Exact original name of the outer-join key. |
| `suffixRefId` | boolean | No | false | The first occurrence keeps its name. Later duplicates receive ` #<query ID>` when true, or ` 2`, ` 3`, etc. when false. true also orders input results by ascending query ID; false preserves input order. |

With at least two input results, matching results combine into a result named `A`.
The key is the first output column; all key values are retained in lexicographic
order, even for numeric keys. Missing samples are filled with 0.
Results missing the key are excluded if any result matches; if none match, inputs
stay unchanged. For repeated keys, each column retains its last non-null value.

### Example: Align series by time

```json
{
  "name": "TA",
  "type": "seriesToColumns",
  "byField": "Time",
  "suffixRefId": true
}
```

For A with `Time,cpu` rows `(1,10),(2,20)` and B with rows `(2,80),(3,90)`,
this produces result `A`:

```text
Time,cpu,cpu #B
1,10,0
2,20,80
3,0,90
```

## merge

No parameters. Match on fields common to all results, then combine compatible
rows. Conflicting values remain separate rows. Use `join` when keys and join type
must be controlled explicitly.

### Example: Merge compatible rows

```json
{
  "name": "TA",
  "type": "merge"
}
```

## concatenate

No parameters. Append columns by row position; duplicate names keep the first
column. No key alignment or missing-value filling occurs. Use only when row
positions already correspond.

### Example: Concatenate columns by position

```json
{ "name": "TA", "type": "concatenate" }
```
