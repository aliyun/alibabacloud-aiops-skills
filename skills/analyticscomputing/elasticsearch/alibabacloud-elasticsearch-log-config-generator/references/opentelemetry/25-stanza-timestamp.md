# stanza — timestamp parsing (`time_parser` & embedded `timestamp:` blocks)

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/stanza/docs/types/timestamp.md

Used by the `time_parser` operator and by every parser's optional `timestamp:` block.

## Fields

| Field | Default | Description |
|---|---|---|
| `parse_from` | required | Field that holds the raw time string. |
| `layout_type` | `strptime` | One of `strptime`, `gotime`, `epoch`. |
| `layout` | required | Format string matching the raw value. |
| `location` | `Local` | IANA timezone applied when parsed value lacks one. |
| `time_zone_locations` | — | Map abbreviation → IANA zone (used with `%Z`). |

## Layout — strptime ↔ gotime

| strptime | gotime | Meaning |
|---|---|---|
| `%Y` | `2006` | 4-digit year |
| `%y` | `06` | 2-digit year |
| `%m` | `01` | Month, zero-pad |
| `%o` | `_1` | Month, space-pad |
| `%q` | `1` | Month, unpad |
| `%b` / `%B` | `Jan` / `January` | Month name (short / full) |
| `%d` / `%e` / `%g` | `02` / `_2` / `2` | Day (zero/space/unpad) |
| `%a` / `%A` | `Mon` / `Monday` | Weekday |
| `%H` | `15` | Hour 24h |
| `%I` / `%l` | `3` / `03` | Hour 12h |
| `%p` / `%P` | `PM` / `pm` | AM/PM |
| `%M` | `04` | Minute |
| `%S` | `05` | Second |
| `%L` | `999` | Millisecond |
| `%f` | `999999` | Microsecond |
| `%s` | `99999999` | Nanosecond |
| `%Z` | `MST` | Zone name |
| `%z` | `Z0700` | Offset ±HHMM |
| `%i` / `%j` / `%k` | `-07` / `-07:00` / `-07:00:00` | Offset variants |
| `%D` | `01/02/2006` | = `%m/%d/%y` |
| `%F` | `2006-01-02` | = `%Y-%m-%d` |
| `%T` | `15:04:05` | = `%H:%M:%S` |
| `%R` | `15:04` | = `%H:%M` |
| `%r` | `03:04:05 pm` | 12-hour clock |
| `%c` | `Mon Jan 02 15:04:05 2006` | Common date+time |
| `%n` / `%t` / `%%` | `\n` / `\t` / `%` | Literal |

## Layout — `epoch`

| Layout | Description | Accepts |
|---|---|---|
| `s` | Seconds | string / int64 / float64 |
| `ms` | Milliseconds | string / int64 / float64 |
| `us` | Microseconds | string / int64 / float64 |
| `ns` | Nanoseconds | string / int64 / float64 |
| `s.ms`, `s.us`, `s.ns` | Fractional seconds | string / int64¹ / float64² |

¹ ints behave like `s`. ² float `s.ns` may lose ≤100ns precision.

## Examples

Embedded in a parser:

```yaml
- type: regex_parser
  regex: '^Time=(?P<timestamp_field>\d{4}-\d{2}-\d{2}), Host=(?P<host>[^,]+)'
  timestamp:
    parse_from: attributes.timestamp_field
    layout_type: strptime
    layout: '%Y-%m-%d'
```

Standalone `time_parser`:

```yaml
- type: time_parser
  parse_from: body.timestamp_field
  layout_type: strptime
  layout: '%a %b %e %H:%M:%S %Z %Y'
```

`gotime`:

```yaml
- type: time_parser
  parse_from: body.timestamp_field
  layout_type: gotime
  layout: Jan 2 15:04:05 MST 2006
```

`epoch`:

```yaml
- type: time_parser
  parse_from: body.timestamp_field
  layout_type: epoch
  layout: s
```

Multiple zone abbreviations:

```yaml
- type: regex_parser
  regex: '^(?P<ts>\w{3} \w{3}\s+\d{1,2} \d{2}:\d{2}:\d{2} [A-Z]{2,5} \d{4})'
  timestamp:
    parse_from: attributes.ts
    layout_type: strptime
    layout: '%a %b %d %H:%M:%S %Z %Y'
    location: Asia/Kolkata
    time_zone_locations:
      PDT: America/Los_Angeles
      NZST: Pacific/Auckland
```

When a `timestamp:` block is set on a parser, parsing happens after the parser's other work and before forwarding.
