# Verification Method: alibabacloud-flink-ai-ops

Every command outputs a unified JSON envelope: `success/operation/data/error/request_id`. Verification principle: explain what is done, what is not, and the next step by combining business results, tool failures, and recheck evidence; never claim a fix solely from HTTP 200, textual promises, or the outer `success`. The `<angle brackets>` below are placeholders to be replaced with real values; omitting the `SKILL_SESSION_ID`/`SKILL_VERSION` prefix is for brevity only.

## 1. Patrol Config Read (get_patrol_config)

```bash
python3 scripts/flink_ai_ops_cli.py get_patrol_config -w <workspace> -n <namespace> -r <region>
```

✅ Success: `success: true` with `data` returning the current `cron/timezone/scopeType/scopeConfig/enabled`.

## 2. Patrol Config Modification (update_patrol_config)

1. Preview: run without `--confirm` and verify `data.preview: true` with `changes` covering only the user's explicit fields.
2. Authorized execution: add `--confirm` and distinguish three outcomes:
   - `unchanged: true, updateSubmitted: false, verified: true`: the explicit fields already satisfy the goal; no new PATCH was made — do not report as "just modified successfully";
   - `updated: true, updateSubmitted: true, verified: true`: the explicit fields read back after PATCH match; only the configuration definition is verified, with no concurrency-lock guarantee;
   - `VerificationFailed`: keep the patch, the read-back values, and the diff; do not PATCH again or auto-rollback.

✅ Success: the rechecked values of the explicit fields match the goal. Report mismatches as-is.

## 3. Trigger and Wait for Patrol (trigger_patrol / wait_patrol_report)

1. `trigger_patrol --body_file <path> --confirm` returns the real `reportId` and status; when missing, `InvalidResponse` is returned and the response is kept for verification — do not re-trigger.
2. `--wait` or `wait_patrol_report --report_id <actual-report-id>` bounded polling: `PENDING/IN_PROGRESS/COMPLETING` are non-terminal; after `COMPLETED` read the detail, and report the real failure on `FAILED`.
3. ✅ Wait success: `COMPLETED, evidenceComplete: true` (the detail contains `overview.total`, non-negative `riskSummary.critical/warning/info` counts, and the `unhealthyJobs` array); `healthVerified: false` means job health was not independently verified, and zero risk only covers the report's scope and moment.
4. Timeout: report the original `reportId`, `lastObserved`, and that "the local timeout did not cancel the cloud-side task"; do not auto-extend; when the user explicitly continues waiting, start one new bounded wait with the same report ID.

## 4. Report Query (list_patrol_reports / get_patrol_report_detail)

```bash
python3 scripts/flink_ai_ops_cli.py get_patrol_report_detail --date yesterday --timezone Asia/Shanghai -w ... -n ... -r ...
```

✅ Success: `success: true` with complete detail evidence (see above). Missing fields return `IncompleteReport`; never treat missing values as zero risk. The detail itself has no `status` field; never infer status by polling the detail.

## 5. AI Assistant Session (chat_ai_agent)

- `status: pending`: pending `hitlPending.items` were obtained; the outer success only means this collection succeeded — approvals and tool executions are not yet complete.
- `status: completed, streamComplete: true`: the event stream ended normally; `operationVerified: false` — actual changes still need resource rechecks.
- ✅ Write-effect verification: for authorized start/stop or configuration changes performed by the assistant, recheck the actual targets with pure-read commands of the installed `alibabacloud-flink-workspace-ops` such as `get_job` and `get_deployment`; assistant text cannot substitute. When another denied item makes the whole return `CHAT_FAILED`, still verify the authorized item that already executed — do not resend approvals or writes.
- Timeout / stream interruption: keep the session, tool IDs, and received events; first pair `toolCallId`s, then recheck unpaired calls read-only against known resources; never auto-resend. `StreamCleanupError` only means local stream cleanup failed, not a business outcome.

## 6. Common Failure Verification

Failure output keeps `error.code`, the redacted `error.message`, `request_id`, and partial `data`; a non-zero exit code means the command did not finish successfully. For error classification and recovery, select Agent Operating Protocol from the main skill's [Reference Links](../SKILL.md#13-reference-links).
