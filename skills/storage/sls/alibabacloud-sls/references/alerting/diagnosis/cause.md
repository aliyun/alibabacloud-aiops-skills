# Diagnose why an alert fired

Start with the [incident and evidence scope](diagnose.md#start-with-the-incident).

You can use the execution record's `Results` to query and verify the source data with
the recorded `Project`, `Store`, `Region`, `Query`, `StartTime`, and `EndTime`.
The time fields describe the actual query interval, not the alert's trigger
time; see [execution fields](../../sls-insights/alert-execution-fields.md). Compare the results
with the recorded trigger condition to explain why the alert fired. When running
a new source query, include the executed query and returned rows as evidence.
Identify `RawResults` from the execution record as historical evidence.

For a user-specified archive whose ingestion timestamp differs from event time,
cover the archive ingestion range and apply the recorded source window to the
event-time field. Preserve the recorded search and aggregation semantics and
explain this time mapping when reporting the query.

If further analysis is needed, query other relevant logs or Logstores around
that interval and correlate the evidence to investigate the root cause.
Report the supporting records and distinguish confirmed findings from hypotheses.
