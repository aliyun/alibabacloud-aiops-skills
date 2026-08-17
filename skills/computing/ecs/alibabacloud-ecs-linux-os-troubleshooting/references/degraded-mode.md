# Degraded Mode (Instance Unavailable)

**Trigger condition**: `DescribeInstances` fails or returns an empty result, and the user confirms that the instance has been released; or the user denies the release but confirms that the instance ID is correct.

In this mode the instance is released or unreachable, so no data can be collected from the instance itself and no diagnostics can be triggered on it. The analysis can rely only on **evidence retained outside the instance**. Verify at the start of the mode which of the following data is still available, and state to the user which evidence is missing.

## Available Evidence

| Source | Purpose | Note |
| --- | --- | --- |
| `DescribeInstanceHistoryEvents` | Platform-side system events for the instance, such as restart, maintenance, and throttling events | Available only within the event retention period |
| `DescribeDiagnosticReports` + `DescribeDiagnosticReportAttributes` | Diagnostic reports created before the instance became unavailable | Available only if a report was created earlier |
| CloudMonitor metrics, see [cloudmonitor-metrics.md](utils/cloudmonitor-metrics.md) | Resource usage trends before the abnormality | Available only within the CloudMonitor data retention period |
| Information provided by the user | Original error messages, screenshots, command output collected earlier, operation history | The main evidence source in this mode |

**Unavailable capabilities**: `GetInstanceConsoleOutput`, `GetInstanceScreenshot`, `RunCommand` and any in-instance collection, `CreateDiagnosticReport`, and the offline troubleshooting workflow in [utils/guestos-pe-prep.md](utils/guestos-pe-prep.md).

**Time range policy**: query with the default time range first. If there is no valid result, ask the user for the approximate time when the problem occurred, and then query again with an explicit window.

## Phase Behavior Adjustments

| Phase | Degraded behavior |
| --- | --- |
| Phase 1: Clarify the abnormal issue | Collect data only from the available evidence listed above, and rely more on questions to the user |
| Phase 2: Classify into a phenomenon domain | Execute normally |
| Phase 3: Confirm whether it is a GuestOS issue | **Skip**. Treat it as a GuestOS issue directly, because the boundary judgment depends on instance-side data |
| Phase 4: Diagnostic tool investigation | **Degraded**. A new diagnostic report cannot be created. Only historical reports can be queried |
| Phase 5: GuestOS-internal component investigation | **Degraded**. Analyze only the retained evidence. Convert the steps that cannot be executed into troubleshooting recommendations for the user |
| Phase 6: Summary and recommendations | Execute normally, but the diagnosis report must state "based on limited data (instance unavailable)" |
