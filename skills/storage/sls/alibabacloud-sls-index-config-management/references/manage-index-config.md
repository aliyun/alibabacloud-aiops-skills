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
  represent the complete final config, not a partial fragment.
- At least one of `line`, `keys`, or `scan_index` must be present.
- Object-valued parameters such as `line` and `keys` should be written to `/tmp/*.json` and
  passed with `$(cat /tmp/file.json)`.
- Index writes apply only to new logs after propagation, usually within ~1 minute.

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
- `chn`: Chinese tokenization. Keep `false` unless Chinese keyword search is needed and user requires it.
- `token`: token delimiters for full-text/text fields.
- `index_all`, `max_depth`, `json_keys`: JSON indexing controls.

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
