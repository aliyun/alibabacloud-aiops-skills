# Diagnose why an alert fired

Start with the [incident and evidence scope](diagnose.md#start-with-the-incident).

Use the execution record's `Results` to query and verify the source data with
the recorded `Project`, `Store`, `Region`, `Query`, `StartTime`, and `EndTime`.
The time fields describe the actual query interval, not the alert's trigger
time; see [execution fields](history/execution-fields.md). Compare the results
with the recorded trigger condition to explain why the alert fired. Include
the source query actually executed and its returned rows as evidence; copying
`RawResults` from the execution record alone is not a fresh source query.

For a user-specified archive whose ingestion timestamp differs from event time,
cover the archive ingestion range and apply the recorded source window to the
event-time field. Preserve the recorded search and aggregation semantics and
explain this time mapping when reporting the query.

If further analysis is needed, query other relevant logs or Logstores around
that interval and correlate the evidence to investigate the root cause.
Report the supporting records and distinguish confirmed findings from hypotheses.
