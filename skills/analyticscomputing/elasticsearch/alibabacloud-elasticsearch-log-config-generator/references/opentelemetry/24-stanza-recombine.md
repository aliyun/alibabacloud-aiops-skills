# stanza — `recombine`

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/operators/recombine.md

Merges consecutive entries into one when input is multiline (e.g., stack traces).

## Fields

| Field | Default | Description |
|---|---|---|
| `id` | `recombine` | Unique identifier. |
| `output` | next in pipeline | Downstream operators. |
| `on_error` | `send` | Standard error modes. |
| `if` | — | Per-entry gate; non-matches pass through unchanged. |
| `is_first_entry` | — | Expression: true on the first entry of a group. |
| `is_last_entry` | — | Expression: true on the last entry of a group. |
| `combine_field` | **required** | Field combined across entries. |
| `combine_with` | `"\n"` | Separator inserted between combined fields. |
| `max_batch_size` | `1000` | Max consecutive entries combined; `0` = unlimited. |
| `max_unmatched_batch_size` | `100` | Max consecutive non-matching entries before flush. |
| `overwrite_with` | `oldest` | Take non-combined fields from `oldest` or `newest`. |
| `force_flush_period` | `5s` | Flush a partial group after this duration. |
| `source_identifier` | `attributes["log.file.path"]` | Field that distinguishes sources. |
| `max_sources` | `1000` | Max simultaneous sources tracked. |
| `max_log_size` | `0` | Max bytes of combined field; `0` = unlimited. |

**Constraints:** Exactly one of `is_first_entry` / `is_last_entry` must be set. Designed for a single input.

## Java stack trace example

```yaml
- type: recombine
  combine_field: body
  is_first_entry: body matches "^[^\\s]"
```

Treats every non-indented line as a new record; indented `at ...` frames append to the preceding line via `combine_with` (default `\n`).

## Date-prefixed records

```yaml
- type: recombine
  combine_field: body
  is_first_entry: 'body matches "^\\d{4}-\\d{2}-\\d{2}"'
  source_identifier: attributes["log.file.path"]
  force_flush_period: 5s
```
