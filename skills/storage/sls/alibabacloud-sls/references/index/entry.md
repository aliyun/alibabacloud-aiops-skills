# Index configuration

Scripts are in `scripts/index/`.

## Scenarios

| Scenario | Reference |
| --- | --- |
| Understand field coverage, matching or analytics | [Query behavior](index-configuration.md#query-behavior) |
| Inspect a Logstore or log-type StoreView index | [Index inspection](manage-index-config.md#read-an-index) |
| Create, update or delete a Logstore index | [Index operations](manage-index-config.md#changes) |
| Generate a configuration from structured log samples | [Generation](generate-index-from-logs.md) |
| Tune an existing index for queries, SQL, cost, or throughput | [Optimization](optimize-index-config.md) |

## Related documents

| Topic | Reference |
| --- | --- |
| Configuration fields | [Index parameters](index-configuration.md#top-level-parameters) |
| Install or update the CLI and SLS plugin | [Installation](../cli-installation-guide.md) |
| Resolve RAM permissions | [RAM policies](ram-policies.md) |
| Look up the underlying APIs | [Related APIs](related-apis.md) |

## Index validator

`python3 scripts/index/validate_index.py --input index.json` checks a writable
configuration locally. Supply a UTF-8 JSON file with `--input FILE` (or a positional
file argument), or use `--input -` for stdin. Duplicate keys and non-finite numbers
are rejected. Reports go to stdout; `--output FILE` saves the JSON report to a path
distinct from the input.

Reports contain `result`, `errors` and `warnings`; each diagnostic includes `code`,
`path` and `message`. The result is `valid`, `warning` or `error`. Errors return
exit code 1; warnings return 0 unless `--strict` is supplied. Strict mode changes
only the exit code. Malformed or unreadable input produces an `INPUT_ERROR`
report with exit code 1. Argument errors use exit code 2 and a usage message;
other runtime failures produce a JSON error report on stderr.

## Troubleshooting

For command, authentication, permission, or connection errors, see
[common troubleshooting](../troubleshooting.md).
For index lookup, request construction, and configuration failures, see
[index troubleshooting](troubleshooting.md).
