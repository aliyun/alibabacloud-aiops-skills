# Filebeat filestream parsers

> Source: https://www.elastic.co/docs/reference/beats/filebeat/filebeat-input-filestream (parsers subsection) and https://www.elastic.co/docs/reference/beats/filebeat/multiline-examples
>
> The `filestream` input applies parsers in order under `parsers:` (`02-input-filestream.md`). Each entry is a map with one parser type and its options.

## multiline

> The filestream parsers page only references this option block; full sub-options live on the dedicated multiline page.

| Field | Default | Notes |
|---|---|---|
| `type` | `pattern` | Strategy: `pattern` (regex marker on first or non-first line), `count` (fixed N lines per record), `while_pattern` (collapse while regex matches). |
| `pattern` | — | Regex used by `type: pattern` and `while_pattern`. |
| `negate` | `false` | (`pattern`) Invert — start a record on a NON-match. |
| `match` | `after` | (`pattern`) `after` (continuations follow) or `before` (continuations precede) the line that matches. |
| `count_lines` | — | (`count`) Fixed number of lines per record. |
| `flush_pattern` | — | Flush an in-progress record when a line matches this regex. |
| `lines_to_skip` | — | Drop the first N lines of every record after merge. |
| `max_lines` | `500` | Cap per merged record; over-long groups are split. |
| `timeout` | `5s` | Send a partial record if no matching line arrives within this window. |
| `skip_newline` | `false` | Strip the joining newline. |

```yaml
parsers:
  - multiline:
      type: pattern
      pattern: '^[[:space:]]'
      negate: false
      match: after
      max_lines: 1000
      timeout: 5s
```

## ndjson

| Field | Default | Notes |
|---|---|---|
| `target` | — | Destination object name; `""` lifts decoded keys to the event root. |
| `message_key` | — | The JSON key whose string value is used for line filtering and downstream multiline. |
| `document_id` | — | JSON key used as the document id; removed from source and stored in `@metadata._id`. |
| `overwrite_keys` | `false` | Allow decoded keys to overwrite Filebeat-added keys. |
| `expand_keys` | `false` | `{"a.b.c":1}` → `{"a":{"b":{"c":1}}}`. Recommended for ECS-style loggers. |
| `add_error_key` | `false` | Set `error.message` + `error.type=json` on parse failure / unusable `message_key`. |
| `ignore_decoding_error` | `false` | Suppress decode-error logs. |

## container

For container-runtime log files (Docker JSON / containerd CRI / CRI-O).

| Field | Default | Notes |
|---|---|---|
| `format` | `auto` | `auto` / `docker` / `cri`. Setting any value other than `auto` disables auto-detection. |
| `stream` | `all` | `all` / `stdout` / `stderr`. |

`paths` is set on the **input**, not on this parser.

## syslog

| Field | Default | Notes |
|---|---|---|
| `format` | `auto` | `rfc3164` / `rfc5424` / `auto`. |
| `timezone` | `Local` | IANA name (`America/New_York`), fixed offset (`+0200`), or `Local`. |
| `log_errors` | `false` | Log syslog parsing errors. |
| `add_error_key` | `true` | Append parsing errors to `error.message`. |

## include_message

Drops lines whose `message` doesn't match any pattern. Runs **inside the parser pipeline**, before `include_lines` (which runs after parsers).

| Field | Notes |
|---|---|
| `patterns` | List of regexes — keep on any match. |

## Stacked example

Container logs → strip CRI envelope → parse JSON body → keep only WARN/ERR → recombine 3-line JSON records:

```yaml
filebeat.inputs:
  - type: filestream
    id: containers
    paths: [/var/log/containers/*.log]
    parsers:
      - container:
          stream: stdout
          format: auto
      - ndjson:
          target: ""
          message_key: log
          overwrite_keys: false
          expand_keys: true
          add_error_key: true
      - include_message:
          patterns: ["^ERR", "^WARN"]
      - multiline:
          type: count
          count_lines: 3
```

Order matters: parsers earlier in the list run earlier.
