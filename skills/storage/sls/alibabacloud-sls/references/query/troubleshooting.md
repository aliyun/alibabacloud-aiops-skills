# Troubleshooting

For CLI, authentication, permission, region or connection issues, see
[common troubleshooting](../troubleshooting.md).

## Query failures

| Symptom | What to check | Details |
| --- | --- | --- |
| `LogStoreNotExist` | Store name, owning Project, and service location. | [Query execution](query-execution.md), [regions](../regions.md) |
| `IndexConfigNotExist` | Target and index existence. | [Index lookup](../index/troubleshooting.md#index-operations) |
| No matching logs | Query time range, target, topic, page offset, whether logs were written, and indexing delay for recent writes. | [Index search](index-search.md) |
| Keyword matches too much or too little | Field coverage and matching settings. | [Field coverage](../index/index-configuration.md#field-coverage), [text matching](../index/index-configuration.md#text-matching) |
| Fuzzy search returns incomplete results | Wildcard expansion is limited to 100 matching terms. This can also affect exclusions using `not`. | [Fuzzy search](index-search.md#fuzzy-search) |
| Numeric range search fails or behaves unexpectedly | Field index type. | [Field coverage](../index/index-configuration.md#field-coverage) |
| JSON subfield search does not work | Subfield index, path and literal dotted names. | [JSON fields](../index/index-configuration.md#json-field-queries), [SPL field names](spl/README.md#handling-dotted-field-names) |
| SQL cannot analyze a field | Indexed SQL prerequisites and historical coverage. | [SQL requirements](../index/index-configuration.md#indexed-sql-analysis), [historical coverage](../index/index-configuration.md#configuration-changes-and-historical-data) |
| SQL returns truncated text | Retained analysis text length. | [Text length](../index/index-configuration.md#text-length-in-sql-analysis) |
| `SELECT *` does not return every raw field | Indexed SQL returns indexed analysis fields. Use index search for raw log records. | [SQL analysis](sql/README.md) |
| Index changes do not affect old logs | Configuration effective time and historical indexing. | [Historical coverage](../index/index-configuration.md#configuration-changes-and-historical-data) |
| Syntax or field-name error | The selected language's operators, quoting, and field naming rules. | [Index search](index-search.md), [SQL](sql/README.md), [SPL](spl/README.md) |
| `meta.progress` is not `Complete` | The result is imprecise. Consider the selected mode's execution limits and the task's precision requirements. | [SQL analysis](sql/README.md), [SQL SCAN](sql/sql-scan.md) |

For a different matching strategy, see [query mode selection](entry.md#2-choose-a-query-mode)
and [phrase search](phrase-search.md).

For SQL workloads that exceed the available analysis capacity, consult the
[official SQL capacity guidance](https://help.aliyun.com/zh/sls/query-and-analyze-logs-in-index-mode/).
