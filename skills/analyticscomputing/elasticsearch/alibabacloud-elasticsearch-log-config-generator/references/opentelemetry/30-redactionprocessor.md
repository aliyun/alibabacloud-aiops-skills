# redaction processor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/redactionprocessor/README.md
>
> Allow-lists attribute keys and masks/hashes values matching regex patterns. Stable for traces (beta); alpha for logs and metric datapoint attributes.

## Fields

| Field | Default | Description |
|---|---|---|
| `allow_all_keys` | `false` | When true, skip the allow-list (`blocked_values` still applies). |
| `allowed_keys` | `[]` | Keys retained on attributes. Empty list = drop **all** attributes. |
| `ignored_keys` | `[]` | Bypass redaction entirely; processed first. Use only for known-safe fields. |
| `blocked_values` | `[]` | List of regexes. Values matching are masked with `*` (or hashed if `hash_function` set). |
| `hash_function` | — | `md5`, `sha1`, `sha3` (=SHA-256), `hmac-sha256`, `hmac-sha512`. |
| `summary` | — | `silent` / `info` / `debug` — controls audit attributes added to records. |

Note: there is also an `allowed_values` field; when set, allowed-pattern matches override `blocked_values` for the same value.

## Pipeline order

Allow-list runs **first**; only surviving keys are checked against `blocked_values`. So a sensitive key not on the allow-list is removed before its value is even examined.

## Examples

Allow-list + mask credit cards:

```yaml
processors:
  redaction:
    allow_all_keys: false
    allowed_keys:
      - description
      - group
      - id
      - name
    blocked_values:
      - "4[0-9]{12}(?:[0-9]{3})?"   # Visa
      - "(5[1-5][0-9]{14})"          # MasterCard
    summary: debug
```

Hash sensitive values (don't strip keys):

```yaml
processors:
  redaction:
    allow_all_keys: true
    blocked_values:
      - "4[0-9]{12}(?:[0-9]{3})?"
      - "(5[1-5][0-9]{14})"
    hash_function: md5
    summary: info
```

## Audit attributes (when `summary` ≠ `silent`)

Added to each record: `redaction.redacted.keys`, `redaction.redacted.count`, `redaction.masked.keys`, `redaction.masked.count`, `redaction.allowed.keys`, `redaction.allowed.count`, `redaction.ignored.count`. Zero-valued attrs aren't emitted.
