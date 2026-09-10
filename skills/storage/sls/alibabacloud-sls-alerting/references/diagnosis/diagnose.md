# Alert event diagnosis

Use for an alert that fired: explain its trigger and root cause, determine its
frequency and duration. Diagnose read-only
first; do not rewrite a rule, broaden RAM access, or send another notification
as a diagnostic shortcut.

## Start with the incident

Resolve the rule and incident time range. Query a user-specified archive directly;
otherwise prefer
[alert center history](history/center.md), falling back to
[Project execution history](history/project.md) when the center is unavailable
or lacks the required details. These managed history resources are provisioned
through the console, not created manually.

Historical event diagnosis does not require the rule to still exist; current
configuration may differ from the configuration at the incident time.

Use recorded firing events to explain the trigger. If no firing event is
available, report the evidence limit without inferring that a rule never ran.

For [trigger causes](cause.md), connect the condition result to evidence in
application and dependency logs. When counting triggers, deduplicate records
from the same execution and distinguish firing executions from continuous
firing periods. Use recovery evidence to bound duration; if recovery is missing,
report the observed interval and uncertainty.
