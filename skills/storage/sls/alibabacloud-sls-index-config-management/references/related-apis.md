# Related APIs - SLS Index Configuration Manager

This document is the API / CLI reference for the index management skill. It covers the four
index-management endpoints: `GetIndex`, `CreateIndex`, `UpdateIndex`, and `DeleteIndex`.

## Command List

| CLI Command               | API Action  | Operation Type      | Description                                           | Documentation                                                                            |
| ------------------------- | ----------- | ------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `aliyun sls get-index`    | GetIndex    | read                | Read the current index configuration of a Logstore    | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getindex)    |
| `aliyun sls create-index` | CreateIndex | write               | Create the initial index configuration for a Logstore | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createindex) |
| `aliyun sls update-index` | UpdateIndex | write (overwrite)   | Replace the entire index configuration of a Logstore  | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-updateindex) |
| `aliyun sls delete-index` | DeleteIndex | write (destructive) | Remove the entire index configuration of a Logstore   | [Doc](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-deleteindex) |

---

## CLI Conventions

- Always use the product namespace `aliyun sls` and kebab-case subcommands / flags.
- Do not use PascalCase OpenAPI action names (`UpdateIndex`) as CLI subcommands.
- Do not pass a JSON `--params` blob. The SLS plugin exposes request fields as individual flags.
- For object-valued index parameters, write compact JSON to files and pass them with `$(cat ...)`, for example `--line "$(cat /tmp/sls-index-line.json)"` and `--keys "$(cat /tmp/sls-index-keys.json)"`.
- Pass scalar body properties directly, for example `--max-text-len 2048`, `--scan-index true`, or `--log-reduce false`.

---

## Index Configuration Schema

The same JSON object is shared by `CreateIndex`, `UpdateIndex`, and the response of `GetIndex`.

| Field                   | Type     | Required                | Description                                                                                                     |
| ----------------------- | -------- | ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| `line`                  | object   | conditional             | Full-text index. At least one of `line` / `keys` / `scan_index` must be present.                                |
| `line.token`            | string[] | yes (if `line` present) | Tokenizer delimiters, e.g. `[",", " ", ";", "=", "(", ")", "[", "]", "{", "}", ":", "\n", "\t", "\r"]`.         |
| `line.caseSensitive`    | boolean  | no                      | Default `false`.                                                                                                |
| `line.chn`              | boolean  | no                      | Enable Chinese tokenization. Default `false`. Enabling reduces write throughput.                                |
| `line.include_keys`     | string[] | no                      | Restrict full-text index to these fields. Mutually exclusive with `exclude_keys`.                               |
| `line.exclude_keys`     | string[] | no                      | Exclude these fields from full-text index. Mutually exclusive with `include_keys`.                              |
| `keys`                  | object   | conditional             | Field index map: `{ <fieldName>: <IndexKey> }`. At least one of `line` / `keys` / `scan_index` must be present. |
| `scan_index`            | boolean  | no                      | Enable scan index. Default `false`. At least one of `line` / `keys` / `scan_index` must be present.             |
| `max_text_len`          | integer  | no                      | Max bytes per analyzed `text` value, range `64`–`16384`, default `2048`.                                        |
| `log_reduce`            | boolean  | no                      | Enable log clustering (LogReduce). Default `false`.                                                             |
| `log_reduce_white_list` | string[] | no                      | Field whitelist for clustering. Effective only when `log_reduce: true`.                                         |
| `log_reduce_black_list` | string[] | no                      | Field blacklist for clustering. Effective only when `log_reduce: true`.                                         |
| `ttl`                   | integer  | response-only           | Index lifetime in days. Read via `GetIndex`.                                                                    |
| `index_mode`            | string   | response-only           | Index version, typically `v2`. Read via `GetIndex`.                                                             |
| `lastModifyTime`        | integer  | response-only           | Last modification time in Unix seconds. Read via `GetIndex`.                                                    |
| `storage`               | string   | response-only           | Storage type, fixed to `pg`. Read via `GetIndex`.                                                               |

### `IndexKey` (entry value of `keys`)

| Field           | Type     | Required | Description                                                                                       |
| --------------- | -------- | -------- | ------------------------------------------------------------------------------------------------- |
| `type`          | string   | yes      | One of `text` / `long` / `double` / `json`.                                                       |
| `doc_value`     | boolean  | no       | `true` enables SQL analytics (`SELECT`, `GROUP BY`, `WHERE`) on this field. **Required for SQL.** |
| `alias`         | string   | no       | Field alias, optional.                                                                            |
| `caseSensitive` | boolean  | no       | For `text` / `json`. Default `false`.                                                             |
| `chn`           | boolean  | no       | For `text` / `json`. Default `false`. Enable only when content contains Chinese.                  |
| `token`         | string[] | no       | Tokenizer delimiters for `text` / `json`.                                                         |
| `index_all`     | boolean  | no       | For `json`. Auto-index all leaf text fields under the JSON.                                       |
| `max_depth`     | integer  | no       | For `json`. Max recursion depth.                                                                  |
| `json_keys`     | object   | no       | For `json`. Per-leaf overrides: `{ <jsonPath>: <IndexJsonKey> }`.                                 |

### `IndexJsonKey` (entry value of `json_keys`)

| Field           | Type    | Required | Description                                                     |
| --------------- | ------- | -------- | --------------------------------------------------------------- |
| `type`          | string  | yes      | `text` / `long` / `double`.                                     |
| `doc_value`     | boolean | no       | Enable analytics on this leaf.                                  |
| `alias`         | string  | no       | Leaf alias.                                                     |
| `caseSensitive` | boolean | no       | For `text`.                                                     |
| `chn`           | boolean | no       | For `text`.                                                     |

`IndexJsonKey` does not support its own `token`; text leaves use the parent `json` field's
tokenizer.

### Minimum example — full-text only

```json
{
  "line": {
    "chn": false,
    "caseSensitive": false,
    "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
  }
}
```

### Mixed example — full-text + field index

```json
{
  "line": {
    "chn": false,
    "caseSensitive": false,
    "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", "?", "&", "/", ":", "\n", "\t", "\r"]
  },
  "keys": {
    "status": { "type": "long", "doc_value": true },
    "request_time": { "type": "double", "doc_value": true },
    "request_uri": {
      "type": "text",
      "doc_value": true,
      "caseSensitive": false,
      "chn": false,
      "token": [",", " ", ";", "=", "(", ")", "[", "]", "{", "}", ":", "/", "\n", "\t", "\r"]
    },
    "extra": {
      "type": "json",
      "doc_value": true,
      "index_all": true,
      "max_depth": 4
    }
  },
  "max_text_len": 2048
}
```

---

## GetIndex

`GET /logstores/{logstore}/index` — invoke via `aliyun sls get-index`.

### Input — Required

| Parameter | Type   | CLI Flag     | Description    |
| --------- | ------ | ------------ | -------------- |
| Project   | string | `--project`  | Project name.  |
| Logstore  | string | `--logstore` | Logstore name. |

### Output

The full index configuration object (see schema above) plus response-only fields `ttl`, `index_mode`, `lastModifyTime`, `storage`.

### Common Errors

| HTTP Status | ErrorCode             | Meaning                                                          |
| ----------- | --------------------- | ---------------------------------------------------------------- |
| 404         | `ProjectNotExist`     | Project name is wrong or in a different region.                  |
| 404         | `LogStoreNotExist`    | Logstore name is wrong.                                          |
| 404         | `IndexConfigNotExist` | The Logstore has no index configured — proceed to `CreateIndex`. |

---

## CreateIndex

`POST /logstores/{logstore}/index` — invoke via `aliyun sls create-index`.

### Input — Required

| Parameter | Type   | CLI Flag     | Description    |
| --------- | ------ | ------------ | -------------- |
| Project   | string | `--project`  | Project name.  |
| Logstore  | string | `--logstore` | Logstore name. |

### Input — Optional (effectively required: at least one of `line` / `keys` / `scan_index` must be present in the body)

| Parameter             | Type     | CLI Flag                  | Description                          |
| --------------------- | -------- | ------------------------- | ------------------------------------ |
| line                  | object   | `--line`                  | Full-text index config. JSON.        |
| keys                  | object   | `--keys`                  | Field index map. JSON.               |
| scan_index            | boolean  | `--scan-index`            | Enable scan index.                   |
| max_text_len          | integer  | `--max-text-len`          | Max bytes per analyzed `text` value. |
| log_reduce            | boolean  | `--log-reduce`            | Enable LogReduce clustering.         |
| log_reduce_white_list | string[] | `--log-reduce-white-list` | Whitelist for LogReduce.             |
| log_reduce_black_list | string[] | `--log-reduce-black-list` | Blacklist for LogReduce.             |

### Common Errors

| HTTP Status | ErrorCode           | Meaning                                                                   |
| ----------- | ------------------- | ------------------------------------------------------------------------- |
| 400         | `IndexInfoInvalid`  | Body missing required fields (e.g. `token` for `line`) or malformed JSON. |
| 400         | `IndexAlreadyExist` | The Logstore already has an index — use `UpdateIndex` instead.            |
| 404         | `ProjectNotExist`   | Project name is wrong or region mismatch.                                 |
| 404         | `LogStoreNotExist`  | Logstore name is wrong.                                                   |

---

## UpdateIndex

`PUT /logstores/{logstore}/index` — invoke via `aliyun sls update-index`.

### Input — Required

Same as `CreateIndex`.

### Body Semantics — **Replace Full Config**

The request body **replaces** the entire index configuration. Any field not included in the body is **dropped**. Treat `update-index` like `create-index` against an existing Logstore: prepare the complete final config, then submit it.

Call `get-index` first when you need a backup or a reference for the existing config.

### Common Errors

Same set as `CreateIndex`, plus:

| HTTP Status | ErrorCode             | Meaning                                                     |
| ----------- | --------------------- | ----------------------------------------------------------- |
| 404         | `IndexConfigNotExist` | The Logstore has no index yet — call `CreateIndex` instead. |

---

## DeleteIndex

`DELETE /logstores/{logstore}/index` — invoke via `aliyun sls delete-index`.

### Input — Required

| Parameter | Type   | CLI Flag     | Description    |
| --------- | ------ | ------------ | -------------- |
| Project   | string | `--project`  | Project name.  |
| Logstore  | string | `--logstore` | Logstore name. |

### Effect & Risk

- Removes **all** field indexes and full-text indexes; query / SQL / SPL on this Logstore will stop working.
- The deletion takes effect within ~1 minute; in-flight queries may continue to succeed during the propagation window.
- **Always confirm with the user before invoking.** This skill never chains `delete-index` after another write.

### Common Errors

| HTTP Status | ErrorCode          | Meaning                                   |
| ----------- | ------------------ | ----------------------------------------- |
| 404         | `ProjectNotExist`  | Project name is wrong or region mismatch. |
| 404         | `LogStoreNotExist` | Logstore name is wrong.                   |

## Reference Documentation

| Document                                                                                             | Description                                               |
| ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [GetIndex API](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getindex)       | Official API reference                                    |
| [CreateIndex API](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createindex) | Official API reference                                    |
| [UpdateIndex API](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-updateindex) | Official API reference                                    |
| [DeleteIndex API](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-deleteindex) | Official API reference                                    |
| [Index configuration overview](https://help.aliyun.com/zh/sls/user-guide/create-indexes)             | Concepts: full-text, field index, tokenization, doc_value |
| [Aliyun CLI — SLS plugin](https://github.com/aliyun/aliyun-cli)                                      | CLI source and release notes                              |
