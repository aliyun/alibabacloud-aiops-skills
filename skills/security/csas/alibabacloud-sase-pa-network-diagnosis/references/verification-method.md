# Verification Method: SASE PA Network Diagnosis

## Verification Steps

### 1. Verify Diagnosis Task Created Successfully

```bash
# Create task and extract DiagnoseId
DIAGNOSE_ID=$(aliyun csas create-pa-diagnosis-task \
  --diagnose-type FullLink --host <target_address> --port <port> --protocol TCP \
  --username <username> --dev-tag <DeviceTag_from_Task0> --pop-mode AutoSelect \
  --cli-query 'DiagnosisTask.DiagnoseId' --quiet)

echo "DiagnoseId: $DIAGNOSE_ID"
# ✅ Verification: Non-empty DiagnoseId means task created successfully
```

### 2. Verify Diagnosis Task Completed

```bash
# Manually poll the status with a bounded loop
MAX_POLLS=20
POLL_INTERVAL=10
POLL_COUNT=0
STATUS=""

while [ "$POLL_COUNT" -lt "$MAX_POLLS" ]; do
  sleep "$POLL_INTERVAL"
  POLL_COUNT=$((POLL_COUNT + 1))
  STATUS=$(aliyun csas get-pa-diagnosis-task \
    --diagnose-id $DIAGNOSE_ID \
    --cli-query 'DiagnosisTask.Status' --quiet 2>/dev/null | tr -d '[:space:]"')
  echo "Current status: $STATUS"
  if echo "$STATUS" | grep -qE 'Finished|Failed'; then
    break
  fi
done

if ! echo "$STATUS" | grep -qE 'Finished|Failed'; then
  echo "Polling timed out after $((MAX_POLLS * POLL_INTERVAL)) seconds; retrieve the full task result once and explain that the task may still be running or status parsing failed."
fi
# ✅ Verification: Status is "Finished" means completed; "Failed" is terminal and must be analyzed as a failed diagnosis task
```

### 3. Verify Diagnosis Result

```bash
# Check overall diagnosis result
aliyun csas get-pa-diagnosis-task \
  --diagnose-id $DIAGNOSE_ID \
  --cli-query 'DiagnosisTask.Result.Success'
# ✅ Verification: true means the diagnosis flow completed normally

# Check error message (on failure)
aliyun csas get-pa-diagnosis-task \
  --diagnose-id $DIAGNOSE_ID \
  --cli-query 'DiagnosisTask.Result.ErrorMessage'

# Check network node details
aliyun csas get-pa-diagnosis-task \
  --diagnose-id $DIAGNOSE_ID \
  --cli-query 'DiagnosisTask.Result.NetworkLinkInfo.Nodes[].[NodeType, Name, Address, Success]'

# Check DNS resolution result
aliyun csas get-pa-diagnosis-task \
  --diagnose-id $DIAGNOSE_ID \
  --cli-query 'DiagnosisTask.Result.NetworkLinkInfo.Dns'
```

### 4. Verify Zero-Trust Policy Match (FullLink only)

```bash
# Check policy match result
aliyun csas get-pa-diagnosis-task \
  --diagnose-id $DIAGNOSE_ID \
  --cli-query 'DiagnosisTask.Result.PolicyInfo.ZeroTrustPolicyInfo'
# ✅ Pass: Action is "allow" means policy permits access
# ❌ Fail: Action is "block" means policy blocked access
```

## Common Failure Scenarios

| Failure Scenario | Possible Cause | Troubleshooting Direction |
|------------------|----------------|---------------------------|
| `DiagnosisTask.NumberExceedsLimit` | Concurrent running tasks reached limit (5) | Retry up to 5 times with incremental waits of 30/60/90/120/150 seconds; if still failing, ask the user to clear idle Console tasks or confirm switching diagnosis type, then disable AI-mode and stop |
| Task status `Failed` | Device offline / network unreachable | Check device online status and network connectivity |
| Node-level Success=false | A link segment is disconnected | Locate the failed segment by FromNode/ToNode |
| DNS resolution failure | DNS configuration error | Check PrivateZone or DNS server configuration |
| Zero-trust policy block | Policy denies access | Check zero-trust policy configuration and security baseline |
| ErrorMessage: device offline | Endpoint device offline | Confirm SASE App is connected |
