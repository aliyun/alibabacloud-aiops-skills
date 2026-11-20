# Index configuration

An index controls indexed search and SQL analysis. Use [index inspection](manage-index-config.md#read-an-index)
to obtain the current settings.

- [Query behavior](#query-behavior)
- [Top-level parameters](#top-level-parameters)
- [Full-text settings](#full-text-settings-line)
- [Field settings](#field-settings-keys)

## Query behavior

### Field coverage

Full-text indexing (`line`) covers log fields with text-matching rules; `keys` configures
individual field indexes. A field-qualified search such as `body:test` uses that field's
index. A search without a field name covers indexed text fields and the full-text index
when configured. A field's own index settings take precedence over full-text settings.

Use the returned field names and check both `keys` and `line.auto_text_keys`.
Each automatically discovered field has a `text` index with analytics enabled,
even when absent from `keys`; its token delimiters,
case sensitivity and Chinese tokenization inherit `line`.

Numeric index-search comparisons and ranges require `long` or `double` indexes. Numeric-looking text
does not provide numeric-index behavior.

### Indexed SQL analysis

Indexed SQL on log data requires a Standard Logstore; Query-type Logstores do not support
analytics. Stored user fields used in `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY` or aggregates need
analytics enabled (`doc_value: true`). SQL uses the configured field types.
For fields without suitable indexes, see [query mode selection](../query/entry.md#2-choose-a-query-mode).

### Text matching

Token delimiters split text into indexed terms. With `-` as a delimiter, `123-456`
contains two terms and can match a longer value containing both. Without delimiters,
the value is one term. Use the target field's delimiter, case-sensitivity and Chinese
tokenization settings when explaining matching results.
For operators and quoting, see [index-search syntax](../query/index-search.md#basic-syntax).

### JSON field queries

An indexed JSON subfield uses its full path, such as `payload.status:success` or
`request.param.userId:186499`. A numeric index-search predicate requires a numeric
subfield index. JSON-looking content stored as `text`
does not provide indexed subfield paths.

In SQL, quote the whole dotted identifier: `SELECT "payload.status"`.
An indexed JSON path differs from a literal field name containing dots; see
[SPL field names](../query/spl/README.md#handling-dotted-field-names) and the
[JSON query reference](https://help.aliyun.com/zh/sls/faq-about-the-query-and-analysis-of-json-logs).

### Text length in SQL analysis

Text beyond `max_text_len` is truncated for indexed analysis, so an analytical value
can differ from the original log. Its range and default are in [top-level parameters](#top-level-parameters).

### Configuration changes and historical data

Index changes take about a minute to become effective and apply to newly written logs.
Changes to field types, tokenization, analytics or retained text length do not rebuild
historical indexes; older logs may need reindexing. The current configuration alone does
not establish how older data was indexed. Removing an index restricts indexed search
and SQL analysis without deleting stored logs.

## Top-level parameters

At least one of `line`, `keys`, or `scan_index` must be present in a write request.

| JSON property | Type | Purpose |
| --- | --- | --- |
| `line` | object | Full-text index settings. |
| `keys` | object | Field name to `IndexKey` map. |
| `scan_index` | boolean | Enable scan index. Default `false`. |
| `max_text_len` | integer | Maximum bytes per analyzed text value, 64–16384; default 2048. |
| `log_reduce` | boolean | Enable LogReduce log clustering. Default `false`. |
| `log_reduce_white_list` | string[] | Fields included in clustering when `log_reduce` is enabled. |
| `log_reduce_black_list` | string[] | Fields excluded from clustering when `log_reduce` is enabled. |

## Full-text settings (`line`)

| Property | Type | Purpose |
| --- | --- | --- |
| `token` | string[] | Required token delimiters, such as `[",", " ", ":"]`. |
| `caseSensitive` | boolean | Case-sensitive matching. Default `false`. |
| `chn` | boolean | Chinese tokenization. Default `false`; enabling it reduces tokenization and write throughput. |
| `auto_key_detect` | boolean | Discover unindexed fields automatically. Default `false`. |
| `auto_text_keys` | string[] | Service-maintained discovered field names; see [field coverage](#field-coverage). |
| `include_keys` | string[] | Restrict full-text indexing to these fields. Must not be non-empty when `exclude_keys` is non-empty. |
| `exclude_keys` | string[] | Exclude these fields from full-text indexing. Must not be non-empty when `include_keys` is non-empty. |

### Recommended token delimiters

Use `python3 scripts/index/tokens.py` to generate the recommended token delimiters
as a JSON array. Use the array as `line.token`
or a text/JSON field's `token` when needed. For example, embed the array in
the `--line` parameter when create index config:

```bash
--line '{"token": '"$(python3 scripts/index/tokens.py)"'}'
```

### Automatic index discovery

When enabled, automatic discovery continuously adds unindexed field names to `auto_text_keys`.
It requires a Standard Logstore, full-text indexing, and feature access; it discovers
up to 1,024 top-level fields. Feature access is in gradual rollout and may require a request.
Disabling it stops discovering new fields but keeps existing discovered indexes effective.
Changes to `line.token`, `line.caseSensitive`, or `line.chn` also affect these indexes.

Preserve returned `auto_text_keys` unless the user asks to change them; additional names may appear
between reads while discovery is enabled. For a new configuration, enable discovery only when
requested and do not invent discovered names.

## Field settings (`keys`)

Use `text` for strings, `long` for integers, `double` for floating-point values, and `json` for
JSON content. Each field has its own settings:

### `IndexKey` (entry value of `keys`)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `type` | string | yes | One of `text` / `long` / `double` / `json`. |
| `doc_value` | boolean | no | `true` enables indexed SQL analysis on this field. |
| `alias` | string | no | Field alias, optional. |
| `caseSensitive` | boolean | no | Case-sensitive matching for `text` / `json`. Default `false`. |
| `chn` | boolean | no | Chinese tokenization for `text` / `json`. Default `false`; enabling it reduces tokenization and write throughput. |
| `token` | string[] | no | Tokenizer delimiters for `text` / `json`. |
| `index_all` | boolean | no | For `json`. Auto-index all leaf text fields under the JSON. |
| `max_depth` | integer | no | For `json`. Max recursion depth; -1 means unlimited depth. |
| `json_keys` | object | no | For `json`. Per-leaf overrides: `{ <jsonPath>: <IndexJsonKey> }`. |
| `embedding` | string | no | Embedding model used for vector indexing. |
| `vector_index` | string | no | Vector index strategy. |

### `IndexJsonKey` (entry value of `json_keys`)

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `type` | string | yes | `text` / `long` / `double`. |
| `doc_value` | boolean | no | Enable analytics on this leaf. |
| `alias` | string | no | Leaf alias. |
| `caseSensitive` | boolean | no | Case-sensitive matching for a text leaf. |
| `chn` | boolean | no | Chinese tokenization for a text leaf. |
| `token` | string[] | no | Token delimiters for this JSON leaf. |

## References

- [Index schema](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-struct-index)
- [Configure indexes](https://help.aliyun.com/zh/sls/create-indexes)
- [Indexed analysis](https://help.aliyun.com/zh/sls/query-and-analyze-logs-in-index-mode/)
