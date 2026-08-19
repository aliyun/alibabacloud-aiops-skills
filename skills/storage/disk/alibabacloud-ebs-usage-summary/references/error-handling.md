# Error Handling Reference

## 1. CLI / API Timeout — Retry Counter & Hard Stop Template

**Trigger**: a single `aliyun ebs describe-metric-data` (or resource overview API) call exceeds the agent runtime timeout (e.g. 120 s) with no output, or returns a gateway timeout / 504 / `RequestTimeout`.

**[MUST] Maintain an explicit retry counter** for `describe-metric-data` per task. Reset it only when the user explicitly re-confirms parameters via the Parameter Confirmation gate. The counter governs which row of the table below applies:

| Retry # | Status before this call | Allowed adjustment | Required user-visible action BEFORE the call |
|---------|-------------------------|--------------------|----------------------------------------------|
| **#1** (1st retry, after the original call timed out) | counter = 1 | Choose **ONE**: (a) reduce `[StartTime, EndTime]` to the latest **1/4** of the original range, keep `Period` unchanged; OR (b) keep the range, raise `Period` one step (`5 -> 60 -> 300 -> 600 -> 3600`). For ranges > 6h, jump directly to `Period=300` or `600`. | Announce the adjustment in plain text, e.g. *"Original 24h window timed out, auto-shortened to latest 6h, period kept at 300s, retry 1/2"*. |
| **#2** (2nd retry, after #1 still timed out) | counter = 2 | Apply **BOTH** adjustments together (shorter window AND larger period). | Announce, e.g. *"1st retry still timed out, this time shrinking window to latest 90min and raising period to 600s, retry 2/2"*. |
| **#3** | counter = 2 → would become 3 | **FORBIDDEN.** A 3rd silent retry is a workflow failure. | **Hard Stop** — do NOT issue another `describe-metric-data` call. Output the **Hard Stop Template** (below) and re-enter the Parameter Confirmation gate. |

**[MUST] Hard Stop Output Template** — when retry counter would reach #3, you MUST output the verbatim Hard Stop template listing the 2 attempted combinations, possible causes, and offering the user A/B/C options. Violating any of the Forbidden-behavior rules = workflow failure.

## 2. Time-Range / Boundary Errors

**Trigger**: API returns `InvalidStartTime.TooEarly`, `InvalidStartTime.Malformed`, `InvalidEndTime.*`, `InvalidParameter: Period exceeds time range limit`, or any `InvalidTimeRange.*` family error.

**Required handling**:

1. **STOP. Do NOT silently rewrite the user's original date.** Auto-mutating the user's timestamp without notice is treated as a workflow failure.
2. **Surface the error to the user verbatim** (error code + message + the exact `StartTime` / `EndTime` you sent).
3. **Compute and propose a valid window** based on the API's documented limits:
   - `Period=5` supports max **12 hours** lookback;
   - `Period=10` supports max **24 hours** lookback;
   - `Period=60` supports max **7 days** lookback;
   - `Period=300` / `600` / `3600` support max **30 days** lookback;
   - For all metrics, `EndTime` MUST NOT exceed the current UTC time, and `StartTime` MUST NOT precede the disk's metric retention horizon.
4. **Ask the user to choose**: either (a) accept the proposed valid window, (b) provide a different window, or (c) cancel. Re-enter the Parameter Confirmation gate with the chosen window.
5. Only after the user explicitly approves the new time range may you reissue the CLI call.

## 3. Permission Errors

For `Forbidden.RAM`, `NoPermission`, `403`, etc., follow the flow in `## RAM Policy → Permission Failure Handling`.

## 4. Other Recoverable Errors

| Error pattern | Required action |
|---------------|-----------------|
| `Throttling` / `Throttling.User` | Wait 5 s, retry once. If still throttled, surface to user. |
| `InvalidDiskId.NotFound` / `InvalidInstanceId.NotFound` | Stop. Ask the user to verify the resource ID; do **not** strip or guess. |
| Empty `DataList` with valid `RequestId` | Inform the user the API call succeeded but returned no data; suggest widening the dimension filter or checking the time range. Do **not** retry blindly. |

## 5. Resource Overview API Errors (get-report / list-reports)

| Error Code | Cause | Required Action |
|------------|-------|-----------------|
| `MissingParameter: ReportId` | `--report-type history` was supplied without `--report-id` | Call `aliyun ebs list-reports` to obtain a valid report ID, then pass `--report-id <report-id>` |
| `NoSuchResource` | Specified report or resource does not exist | Verify the report ID against a `list-reports` response; for `get-report --report-type present`, ensure CloudLens for EBS has been enabled for ≥ 10 minutes in the target region |
| `OperationDenied` | Current operation is not allowed | Check if CloudLens for EBS is enabled for the specified region; verify account status |
| `BLOCK.LimitedRequest` (HTTP 429) | API rate limit exceeded | Wait and retry with exponential backoff. Reduce call frequency |
| `LastTokenProcessing` | A request with the same client token is still processing | Wait a few seconds and retry; do NOT submit duplicate requests |
| `InvalidApi.NotFound` / `unknown flag` | Local CLI plugin is stale or missing | Run `aliyun plugin update`, then retry the same lowercase-hyphenated command and flags |
| Empty `Datas` array with valid `RequestId` | CloudLens for EBS just enabled (data preparation ~10 min) or no disks in this region | Wait and retry, or call `aliyun ebs list-reports` to confirm at least one historical report has been generated. Do NOT mistake this for a permission error |
