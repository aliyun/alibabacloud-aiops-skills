# Verify an alert query

## Validate a new or changed query

Run the proposed query against its source over a representative time range,
using `aliyun sls get-logs-v2` or the available `alibabacloud-sls-query` skill.
Convert relative `start` and `end` to absolute Unix seconds for `--from`
(inclusive) and `--to` (exclusive).

Check that the result provides the columns, aliases, and value types used by
the trigger expression. Partial results cannot validate a threshold. An
unchanged, previously verified query does not need to be rerun.

Use exactly the alert-compatible search/SQL statement; substituting unsupported
scan/SPL or phrase-query features does not validate the alert query. A query
under the CLI profile does not verify the rule's [cross-account query role](cross-account.md).
