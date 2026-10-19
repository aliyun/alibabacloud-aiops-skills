# Manage Index Configuration

Use this reference for direct SLS Logstore index work: view, create, replace, or delete an index
configuration.

| Operation | CLI subcommand            |
| --------- | ------------------------- |
| Create    | `aliyun sls create-index` |
| Read      | `aliyun sls get-index`    |
| Update    | `aliyun sls update-index` |
| Delete    | `aliyun sls delete-index` |

Use `aliyun help sls <subcommand>` for command-specific flags and examples, such as
`aliyun help sls create-index`.

## Core Rules

- `create-index` and `update-index` use nearly the same flags. Use `create-index` when no index
  exists; use `update-index` when replacing an existing config.
- `update-index` overwrites the whole index config. The submitted `line` / `keys` files must
  represent the complete final config, not a partial fragment. Read and back up the current
  config first; preserve unrelated settings, including `line.auto_text_keys`.
- At least one of `line`, `keys`, or `scan_index` must be present.
- Prefer passing object-valued parameters such as `line` and `keys` from JSON files. Correctly
  quoted inline JSON or serialized variables are also acceptable.
- Index writes apply only to new logs after propagation, usually within ~1 minute.
- Initialize the UA as described in [Observability](../SKILL.md#observability) before using the
  examples below; retain the same value for all API calls.

## Index Basics

SLS index config is mainly `line` + `keys`.

| Part   | Purpose                                                                       |
| ------ | ----------------------------------------------------------------------------- |
| `line` | Full-text index. Enables keyword search such as `"error"`.                    |
| `keys` | Field indexes. Enables field filters such as `status: 500` and SQL analytics. |

Common field types:

| Type     | Use for                             |
| -------- | ----------------------------------- |
| `text`   | Strings and keyword/equality search |
| `long`   | Integers                            |
| `double` | Floating-point values               |
| `json`   | JSON object/array strings           |

Common field options:

- `doc_value`: enable SQL analytics for the field. Use it for fields in `SELECT`, `WHERE`,
  `GROUP BY`, `ORDER BY`, or aggregations.
- `caseSensitive`: case-sensitive text matching.
- `chn`: Chinese tokenization, disabled by default. Enabling it substantially reduces
  tokenization and write throughput.
- `token`: token delimiters for full-text/text fields.
- `index_all`, `max_depth`, `json_keys`: JSON indexing controls.

## Automatic Index Discovery

Automatic index discovery is configured inside `line` and submitted through `--line`:

- `auto_key_detect` (boolean, default `false`): when enabled, the server continuously discovers
  unindexed fields and adds their names to `auto_text_keys`.
- `auto_text_keys` (string[]): field names returned by `get-index`, all indexed as `text` with
  analytics enabled. Token delimiters and case sensitivity inherit `line.token` and
  `line.caseSensitive`; changes to those settings also affect these fields.

Disabling automatic index discovery stops adding new fields; existing discovered indexes remain
effective. On updates, preserve `line.auto_text_keys` exactly as returned unless the user explicitly
requests a change. Read back to verify the requested settings and retention of existing fields;
additional names may appear while automatic index discovery is enabled.

For new configs, enable automatic index discovery only when requested and do not invent discovered
names. See the [API schema](related-apis.md#index-configuration-schema) for the official reference.

## Examples

Each example shows the JSON file(s), then the matching `create-index` and `update-index`
commands.

### Full-Text Only

`/tmp/sls-index-line.json`:

```json
{
  "caseSensitive": false,
  "chn": false,
  "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
}
```

```bash
aliyun sls create-index \
  --user-agent "$SLS_INDEX_USER_AGENT" \
  --project <project> --logstore <logstore> \
  --line "$(cat /tmp/sls-index-line.json)" \
  --max-text-len 2048
```

### Full-Text + Field Indexes

`/tmp/sls-index-line.json`:

```json
{
  "caseSensitive": false,
  "chn": false,
  "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
}
```

`/tmp/sls-index-keys.json`:

```json
{
  "status": { "type": "long", "doc_value": true },
  "request_time": { "type": "double", "doc_value": true },
  "request_uri": {
    "type": "text",
    "doc_value": true,
    "caseSensitive": false,
    "chn": false,
    "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", ":", "/", "\n", "\t", "\r"]
  }
}
```

```bash
aliyun sls update-index \
  --user-agent "$SLS_INDEX_USER_AGENT" \
  --project <project> --logstore <logstore> \
  --line "$(cat /tmp/sls-index-line.json)" \
  --keys "$(cat /tmp/sls-index-keys.json)" \
  --max-text-len 2048
```

## Common Errors

| Error              | Action                                                            |
| ------------------ | ----------------------------------------------------------------- |
| `ParameterInvalid` | Check and Fix the parameter value according to the error message. |
| `Unauthorized`     | Check [ram-policies.md](ram-policies.md).                         |
