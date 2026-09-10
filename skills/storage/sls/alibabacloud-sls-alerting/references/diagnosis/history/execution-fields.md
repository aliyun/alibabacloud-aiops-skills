# Rule execution event fields

## Interpret the fields

| Field | Meaning |
| --- | --- |
| `AlertName` | Rule name, unique within the Project; primary filter across executions. |
| `AlertDisplayName` | Human-readable rule name. |
| `AlertID` | Execution ID, newly generated for each run; use it to find all events from that execution. |
| `Status` | Execution outcome; `Success` does not mean the alert fired. |
| `AlertStatus` | `inactive`: not firing; `firing`: triggered; `error`: execution error; `paused`: temporarily disabled; `pending`: consecutive threshold not reached. |
| `Fired` | Whether this execution fired an alert (`true` / `false`). |
| `NotifyStatus` | `Success`, `Failed`, `NotNotified`, or `PartialSuccess`. For current alerts, this describes handoff to alert management, not final recipient delivery. |
| `Reason` | Reason for failure or no notification, such as `Alert condition not met`. |
| `Condition`, `FireCount` | Evaluated condition and accumulated trigger count; interpret alongside the consecutive threshold. |
| `Severity`, `Labels` | Recorded severity and labels; a non-firing result can have severity `0`. |
| `Dashboard` | Associated dashboard, commonly `internal-alert-analysis`. |
| `Results` | Per-query source, query text, time window, and results. |

Decode `Results` and `Labels` if returned as JSON strings. In each Results entry,
`Project`, `Region`, `Store`, and `StoreType` identify the source; `StartTime` and
`EndTime` are Unix seconds defining the actual query interval `[StartTime, EndTime)`,
not the alert's trigger time. `Query` is the executed query text.
Inspect `RawResultCount`, `RawResults`, `FireResult`, and `Truncated` to explain the condition outcome. Result values can be strings;
convert numeric values before comparing them.

History fields are distinct from the rule configuration's `status`
(`ENABLED` / `DISABLED`).
See the [history-field reference](https://help.aliyun.com/zh/sls/fields-in-alert-rule-evaluation-logs)
for additional fields and version-specific meanings.
