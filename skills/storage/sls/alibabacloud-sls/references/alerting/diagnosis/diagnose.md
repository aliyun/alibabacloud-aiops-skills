# Alert event diagnosis

Use for an alert that fired: explain its trigger and root cause, determine its
frequency and duration. Diagnose read-only
first; do not rewrite a rule, broaden RAM access, or send another notification
as a diagnostic shortcut.

## Start with the incident

Resolve the rule and incident time range. Query a user-specified archive directly;
otherwise prefer global center history, using Project execution history when
the center is unavailable or lacks execution details. See
[alert history](../../sls-insights/alert-history.md) for storage locations,
activation, filters and field interpretation.

Historical event diagnosis does not require the rule to still exist; current
configuration may differ from the configuration at the incident time.

Use recorded firing events to explain the trigger. If no firing event is
available, report the evidence limit without inferring that a rule never ran.

For [trigger causes](cause.md), connect the condition result to evidence in
application and dependency logs. When counting triggers, deduplicate records
from the same execution and distinguish firing executions from continuous
firing periods. Use recovery evidence to bound duration; if recovery is missing,
report the observed interval and uncertainty.
