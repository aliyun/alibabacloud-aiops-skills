# Application Monitor (Origin Probe) Reference

This document describes how to configure GA application monitors to proactively probe backend health and detect origin failures early.

> **Important**: Application monitors are active probes initiated by GA. They differ from endpoint group health checks but serve a similar purpose.

---

## 1. Application Monitor vs Health Check

| Attribute | Application Monitor | Endpoint Group Health Check |
|---|---|---|
| Probe initiator | GA control plane | GA forwarding plane |
| Probe target | Origin associated with the listener | Endpoints in the endpoint group |
| Granularity | Listener level | Endpoint group level |
| Protocols | TCP/HTTP/HTTPS | TCP/HTTP/HTTPS |
| Alarm support | Yes | No independent alarms |

---

## 2. Create an Application Monitor

### TCP Probe

```bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"

aliyun ga create-application-monitor \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --protocol TCP \
  --port 80 \
  --interval 60 \
  --timeout 3 \
  --user-agent "$GA_USER_AGENT" \
  --silence-time 300
```

### HTTP Probe

```bash
aliyun ga create-application-monitor \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --protocol HTTP \
  --port 80 \
  --path "/healthz" \
  --method GET \
  --interval 60 \
  --timeout 3 \
  --silence-time 300 \
  --user-agent "$GA_USER_AGENT" \
  --verify-content "ok"
```

### HTTPS Probe

```bash
aliyun ga create-application-monitor \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --protocol HTTPS \
  --port 443 \
  --path "/healthz" \
  --method GET \
  --interval 60 \
  --timeout 5 \
  --user-agent "$GA_USER_AGENT" \
  --silence-time 300
```

---

## 3. Parameter Reference

| Parameter | Required | Description |
|---|---|---|
| AcceleratorId | Yes | GA accelerator ID |
| ListenerId | Yes | Listener ID |
| Protocol | Yes | TCP/HTTP/HTTPS |
| Port | Yes | Probe port |
| Path | No | HTTP/HTTPS probe path, default `/` |
| Method | No | HTTP/HTTPS method, default GET |
| Interval | No | Probe interval in seconds |
| Timeout | No | Probe timeout in seconds |
| SilenceTime | No | Alarm silence time in seconds |
| VerifyContent | No | Expected response content for HTTP/HTTPS probes |

---

## 4. Query Application Monitors

### Single monitor

```bash
aliyun ga get-application-monitor \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '{
    TaskId,
    Protocol,
    Port,
    Path,
    Interval,
    Timeout,
    SilenceTime,
    State
  }'
```

### All monitors under a listener

```bash
aliyun ga list-application-monitors \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --user-agent "$GA_USER_AGENT" | jq '.ApplicationMonitors[] | {
    TaskId,
    Protocol,
    Port,
    Path,
    State
  }'
```

---

## 5. Update an Application Monitor

```bash
aliyun ga update-application-monitor \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --task-id "task-bp1xxxx" \
  --interval 30 \
  --timeout 5 \
  --user-agent "$GA_USER_AGENT" \
  --silence-time 600
```

---

## 6. Query Probe Results

```bash
aliyun ga list-application-monitor-detect-result \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --task-id "task-bp1xxxx" \
  --begin-time "2026-06-01T00:00:00Z" \
  --end-time "2026-06-23T23:59:59Z" \
  --user-agent "$GA_USER_AGENT" | jq '.DetectResults[] | {
    DetectTime,
    Status,
    ErrorCode,
    ErrorMessage
  }'
```

---

## 7. Complete Example

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"
REGION="cn-hangzhou"

echo "=== Creating HTTP application monitor ==="

RESULT=$(aliyun ga create-application-monitor \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --protocol HTTP \
  --port 80 \
  --path "/healthz" \
  --method GET \
  --interval 60 \
  --timeout 3 \
  --silence-time 300 \
  --verify-content "ok" \
  --user-agent "$GA_USER_AGENT")

TASK_ID=$(echo "$RESULT" | jq -r '.TaskId')
echo "Probe task ID: $TASK_ID"

# Verify
sleep 5
aliyun ga get-application-monitor \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '{TaskId, Protocol, Port, Path, State}'
```

---

## 8. Skill Integration Notes

After Step 4 (create listener), optionally ask:

```
Question: Do you want to enable application monitoring for this listener?
- Option 1: No (default)
- Option 2: Yes, TCP probe
- Option 3: Yes, HTTP probe
- Option 4: Yes, HTTPS probe

If yes:
1. Ask for the probe port.
2. For HTTP/HTTPS, ask for the probe path and expected response content.
3. Call create-application-monitor.
4. Call get-application-monitor to verify.
```

---

## 9. Notes

1. Application monitors apply only to Standard accelerator listeners.
2. The probe target is the origin associated with the listener, not the GA accelerate IP.
3. Probes may generate a small amount of traffic; refer to official billing documentation.
4. Combine with CloudMonitor alarms to notify operators on probe failures.
