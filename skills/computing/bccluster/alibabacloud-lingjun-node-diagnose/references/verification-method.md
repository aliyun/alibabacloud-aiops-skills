# Verification Method

> After every operation, the success condition must be verified against the **real API response** as the sole source of truth. Judging success merely by "CLI exit code 0" or "no error" is **forbidden**.

---

## 1. Diagnostic Submission Success

**Pre-condition**: HTTP 2xx + response body contains a non-empty `DiagnosticId`.

```bash
resp=$(safe_aliyun aliyun eflo-controller create-diagnostic-task ...)
did=$(echo "$resp" | jq -r '.DiagnosticId // empty')
[[ -n "$did" ]] || { echo "❌ create failed: $resp"; exit 1; }
```

[WAIT] State: [WAIT] Submitted, pending poll.

---

## 2. Diagnostic Terminal Verdict

**Pre-condition**: the state field of the `describe-diagnostic-result` response body is not in `{InProgress, Running, Pending, Diagnosing}`.

```bash
resp=$(safe_aliyun aliyun eflo-controller describe-diagnostic-result --diagnostic-id "$did" ...)
state=$(echo "$resp" | jq -r '.Status // .DiagnosticState // ""')
case "$state" in
  InProgress|Running|Pending|Diagnosing|"") return 1 ;;  # not yet
  *) return 0 ;;                                           # terminal
esac
```

[PASS] Verdict source: top-level `Status` / `DiagnosticState` in the response body, plus `DiagnosticResults[].Status` (per check item).

---

## 3. Reboot Verification

**Pre-condition**: the reboot request returns 2xx, and within 5-10min `describe-node.OperatingState` equals `Using` again.

```bash
for i in $(seq 1 20); do  # 30s x 20 = 10min
  resp=$(safe_aliyun aliyun eflo-controller describe-node --node-id <nid> ...)
  state=$(echo "$resp" | jq -r '.OperatingState')
  [[ "$state" == "Using" ]] && break
  sleep 30
done
[[ "$state" == "Using" ]] || { echo "❌ reboot timeout, state=$state"; exit 1; }
```

---

## 4. Reimage Verification

**Pre-condition**: 2xx + terminal `OperatingState=Using` AND `ImageId == <new ImageId>`.

```bash
new_img=<the chosen ImageId>
resp=$(safe_aliyun aliyun eflo-controller describe-node --node-id <nid> ...)
state=$(echo "$resp" | jq -r '.OperatingState')
img=$(echo "$resp" | jq -r '.ImageId')
[[ "$state" == "Using" && "$img" == "$new_img" ]] || { echo "❌ reimage failed"; exit 1; }
```

---

## 5. Stop Verification

`describe-node.OperatingState=Stopped` (poll for <= 5min).

---

## 6. ReportNodeStatus Verification

Success conditions: CLI returns 2xx + non-empty `ReportId` (i-<12 digits>) + `RequestId` (synchronous), and a `list-fault-reports` re-check shows the new report with `Status=Processing`; `describe-node` shows the node leaving `Using` (`PreparationForDiagnosingClusterNode`). For post-report deep-diagnosis progress tracking and termination, see Section 7 (Feature 8: `list-fault-reports` / `describe-fault-report` / `stop-node-diagnostic`).

---

## 7. StopNodeDiagnostic Verification

Success conditions (both are mandatory):
1. The `stop-node-diagnostic` CLI returns 2xx + non-empty `RequestId`;
2. A re-check via `describe-fault-report --report-id <rid>` shows `Status`  in {`DiagnosisTerminating`, `DiagnosisTerminated`} (a short poll <= 1min may be needed; `DiagnosisTerminating` is an intermediate state).

Auxiliary verification: a `describe-node` re-check shows the node is available again (`OperatingState` back to `Using` or the user-expected state). The node state not returning to `Using` does not mean the termination failed - the fault-report `Status` is authoritative, and the user must be told the truth.

---

## 8. Anti-hallucination verification

Every field (`DiagnosticId` / `RequestId` / `NodeId` / `ReportId` / `Hostname` / `MachineType` / `OperatingState` / verdict) in the report / completion message **must** be found verbatim in the retained fixture (response-body JSON); if any stitched / inferred / "looks reasonable" value is found -> destroy the report immediately and re-run the real-API verification flow.
