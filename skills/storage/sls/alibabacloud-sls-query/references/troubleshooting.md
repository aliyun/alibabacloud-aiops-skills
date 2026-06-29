# Query & Analysis Troubleshooting

When the user reports "no data", "wrong result", or "SQL/SPL error", troubleshoot in this order.

## 1. Time Range

- Verify that `--from` / `--to` covers the target time window
- Newly written logs may have a brief indexing delay (seconds)

## 2. Index Configuration

- Is indexing enabled at all?
- Does the target field have a field index?
- Was the full-text index used incorrectly, causing tokenization rules to conflict with field index expectations?
- Does the log contain Chinese text requiring Chinese tokenization?
- After modifying the index, historical data is not re-indexed automatically

## 3. Field Type and Statistics

- Range queries require `long` / `double` field types
- SQL analysis requires the field to have statistics enabled (`doc_value: true`)
- Text statistics fields have a default max length; overly long content may be truncated
- Query-type Logstores do not support statistics

## 4. Syntax Issues

- `AND` has higher precedence than `OR` in index queries
- Wildcard queries cannot start with `*` (e.g., `*error` is invalid)
- Phrase exact match uses `#"..."`
- Field existence check uses `key: *`
- SQL and SPL cannot be mixed in one statement
- SPL strings are not escape-processed by default; `\n` is a literal, not a newline

## 5. Field Name Issues

- Field names in the index configuration are case-sensitive
- If field names in the log differ in case from the index config, the index will not match
- In SPL, field names containing special characters must be quoted with double quotes

## 6. When to Consider an Alternative Approach

- No index but analysis is required: switch to SCAN mode
- Index tokenization cannot do exact phrase matching: use SPL `where ... like` or SQL instead
- High-volume / high-concurrency SQL performance is insufficient: consider Dedicated SQL (PowerSQL)
- Critical metrics require zero error tolerance: use fully precise SQL

## 7. ProjectNotExist / Wrong Region

- `ProjectNotExist` typically means `--region` or `--endpoint` does not match
- If the user is unsure which region the project belongs to, use cross-region discovery:

```bash
aliyun sls get-project \
  --project <project-name> \
  --cross-region true \
  --endpoint cn-zhangjiakou.log.aliyuncs.com  # fixed endpoint, cross-region query only available in cn-zhangjiakou
```

- Once found, use the returned `internetEndpoint` as `--endpoint`
- Full details: [regions.md — Cross-Region Discovery](regions.md#cross-region-discovery)

## Source YAMLs

- `./query_analysis/overview.yaml`
- `./query_analysis/indexSearch.yaml`
- `./query_analysis/indexConfig.yaml`
- `./query_analysis/sql.yaml`
- `./spl/overview.yaml`
