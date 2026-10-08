# Logstore

Specify region, project and name with `type=logstore`. Read indexes to establish search
and SQL analytics capability; doc_value is relevant to indexed SQL. Obtain a small
recent sample only when the task needs field shape or business context.

    python3 scripts/sls.py discover --type logstore --region REGION --project PROJECT --name STORE --output facts.json
    python3 scripts/sls.py query --type logstore --region REGION --project PROJECT --name STORE --from START --to END --language sql --query '* | select count(*) as requests'

Add --sample with --from/--to to discovery when required. Keep raw evidence. A field
only present in samples may require SPL or Scan SQL; never claim it is indexed.
For nested fields, use the configured index path and matching query syntax.

Field filters append to the search portion. Tokens require explicit placeholders. SQL
candidate queries return a named value column. Use SQL LIMIT for analytics; GetLogsV2
line/offset only limit raw search. See [SQL](../queries/sql.md),
[SPL](../queries/spl.md) and [variables](../features/variables.md).
