# GA Diagnostics and Monitoring API Reference (Step 7)

This document provides complete CLI scripts for health checks, diagnostics, and monitoring of Global Accelerator links.

> **Session setup**: Before running any cloud API call, source the session initialization script so that `$GA_USER_AGENT` is available:
> ```bash
> source "${SKILL_ROOT}/scripts/init-session.sh"
> ```

---

## 1. get-health-status

Query endpoint health status.

### Basic call

```bash
aliyun ga get-health-status \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT"
```

### Format health status output

```bash
aliyun ga get-health-status \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '{
    ListenerId,
    HealthStatus,
    EndpointGroups: [.EndpointGroups[] | {
      EndpointGroupId,
      EndpointGroupType,
      HealthStatus,
      Endpoints: [.Endpoints[] | {
        EndpointId,
        Address,
        Type,
        Port,
        HealthStatus,
        HealthDetail
      }]
    }]
  }'
```

### Parameter reference

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` |
| AcceleratorId | string | Yes | GA instance ID |
| ListenerId | string | Yes | Listener ID |
| ClientToken | string | No | Idempotency token |
| DryRun | boolean | No | Dry run |

### Key response fields

| Field | Type | Description |
|-------|------|-------------|
| ListenerId | string | Listener ID |
| HealthStatus | string | Overall listener health status |
| EndpointGroups[].EndpointGroupId | string | Endpoint group ID |
| EndpointGroups[].HealthStatus | string | Endpoint group health status |
| EndpointGroups[].Endpoints[].Address | string | Endpoint address |
| EndpointGroups[].Endpoints[].HealthStatus | string | Endpoint health status |
| EndpointGroups[].Endpoints[].HealthDetail | string | Health check detail |

### Health status values

| Value | Description |
|-------|-------------|
| `normal` | All endpoints are healthy (listener level) |
| `abnormal` | All endpoints are abnormal (listener level) |
| `partiallyAbnormal` | Some endpoints are abnormal (listener level) |
| `Healthy` | Endpoint is healthy (endpoint level) |
| `Unhealthy` | Endpoint is unhealthy (endpoint level) |
| `Unknown` | Status unknown (endpoint level) |

---

## 2. Full-link diagnostics script

### One-click diagnostics for all links

```bash
source "${SKILL_ROOT}/scripts/init-session.sh"
bash "${SKILL_ROOT}/scripts/ga-diagnostics.sh" ga-bp1xxxx
```

For the standalone script source, see `scripts/ga-diagnostics.sh`.

---

## 3. Bounded health check script

### Bounded monitoring (default: 10 checks / 10 minutes)

The script always returns once either budget is reached, so it is safe to run in the foreground of a tool call:

```bash
source "${SKILL_ROOT}/scripts/init-session.sh"
bash "${SKILL_ROOT}/scripts/ga-health-monitor.sh" ga-bp1xxxx lsr-bp1xxxx 60 \
  --count 10 --max-duration 600
```

Exit code is `0` only when the last check was `normal`; `1` when the last check was abnormal or the API call failed; `2` on a usage error.

For a single status check, call `get-health-status` directly instead of the monitor script.

### Continuous monitoring (background only)

Long-running monitoring must NOT occupy the foreground of a tool call - an unbounded foreground command never returns and the session is killed by its wall-clock limit. Start it in the background and hand the PID to the user:

```bash
nohup bash "${SKILL_ROOT}/scripts/ga-health-monitor.sh" ga-bp1xxxx lsr-bp1xxxx 60 \
  --unbounded > ga-health-monitor.log 2>&1 &
echo "PID: $!"
```

For the standalone script source, see `scripts/ga-health-monitor.sh`.

---

## 4. Common issue diagnostics

### Issue 1: endpoint health check fails

When a user reports a health-check alarm for a GA instance, always follow this diagnostic order:

1. Verify the GA instance status with `describe-accelerator`.
2. List listeners to find the affected listener IDs.
3. Call `get-health-status` for each listener to identify unhealthy endpoints.
4. Inspect the endpoint group health-check configuration.
5. Test backend reachability from a machine with network access.

```bash
# 1. Query GA instance status
aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '{AcceleratorId, Name, State, Spec}'

# 2. List listeners
aliyun ga list-listeners \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '.Listeners[] | {ListenerId, Protocol, PortRanges, State}'

# 3. Get health status for each listener and filter unhealthy endpoints
aliyun ga get-health-status \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '.EndpointGroups[].Endpoints[] | select(.HealthStatus != "Healthy")'

# 4. View endpoint group health check configuration
aliyun ga describe-endpoint-group \
  --biz-region-id cn-hangzhou \
  --endpoint-group-id "${EPG_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '{
    HealthCheckEnabled,
    HealthCheckProtocol,
    HealthCheckPort,
    HealthCheckPath,
    HealthCheckIntervalSeconds,
    ThresholdCount
  }'

# 5. Test backend reachability from a machine with network access.
# Authorized network exception: these probes target only the backend addresses the
# user supplies for this accelerator (their own endpoints). Keep the timeouts, send
# no request body, and prefer HTTPS or a pure TCP connect over cleartext HTTP.
curl -v --max-time 10 "https://${ENDPOINT_IP}:${PORT}/"
# or, when the backend only serves plain HTTP:
curl -v --max-time 10 "http://${ENDPOINT_IP}:${PORT}/"
# or a pure TCP connect (no payload):
nc -zv -w 5 "${ENDPOINT_IP}" "${PORT}"
```

### Issue 2: acceleration effect is not obvious

```bash
# 1. Confirm acceleration IP allocation
aliyun ga list-ip-sets \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '.IpSets[] | {AccelerateRegionId, IpAddressList, Bandwidth}'

# 2. Check acceleration region bandwidth limit
aliyun ga get-ipsets-bandwidth-limit \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"

# 3. Test latency via acceleration IP
ping -c 10 "${ACCELERATE_IP}"

# 4. Test direct latency for comparison
ping -c 10 "${ENDPOINT_IP}"

# 5. Confirm DNS resolves to acceleration IP
nslookup "${DNS_NAME}"
```

### Issue 3: cross-border acceleration does not work

```bash
# 1. Query cross-border approval status
aliyun ga query-cross-border-approval-status \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT"

# 2. Check GA instance cross-border status
aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{CrossBorderStatus, CrossDomainBandwidthPackage}'

# 3. Enable cross-border transmission if not enabled
aliyun ga update-accelerator-cross-border-status \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --cross-border-status true
```

### Issue 4: GA instance state is abnormal

```bash
# 1. Query instance detailed state
aliyun ga describe-accelerator \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{State, InstanceChargeType, ExpiredTime}'

# 2. If PREPAY, check whether it has expired
EXPIRED=$(aliyun ga describe-accelerator \
  --user-agent "$GA_USER_AGENT" \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" | jq -r '.ExpiredTime' )
echo "Expiration timestamp: $EXPIRED"
echo "Expiration time: $(date -d @$((EXPIRED/1000)) '+%Y-%m-%d %H:%M:%S')"

# 3. View auto-renewal status
aliyun ga describe-accelerator-auto-renew-attribute \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## 5. Origin probing (application monitor)

### Create a probe task

```bash
aliyun ga create-application-monitor \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --listener-id "${LISTENER_ID}" \
  --task-id "${TASK_NAME}" \
  --address "${TARGET_URL}" \
  --detect-enable true \
  --user-agent "$GA_USER_AGENT" \
  --detect-threshold 3
```

### List probe tasks

```bash
aliyun ga list-application-monitor \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

### Query probe results

```bash
aliyun ga list-application-monitor-detect-result \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

### Trigger a probe manually

```bash
aliyun ga detect-application-monitor \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --task-id "${MONITOR_TASK_ID}"
```

---

## 6. ACL access control diagnostics

### Check whether a listener is associated with an ACL

```bash
aliyun ga list-listeners \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '.Listeners[] | {ListenerId, AclType, AclIds: .RelatedAcls}'
```

### View ACL rule details

```bash
aliyun ga get-acl \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --acl-id "${ACL_ID}"
```

---

## 7. Deployment validation checklist script

Run this script after deployment for comprehensive validation:

```bash
source "${SKILL_ROOT}/scripts/init-session.sh"
bash "${SKILL_ROOT}/scripts/ga-validate-deployment.sh" ga-bp1xxxx
```

For the standalone script source, see `scripts/ga-validate-deployment.sh`.

---

## 8. Diagnostic report template (mandatory)

Every diagnostic or import answer uses this structure. Sections 1-3 are all required; a report that lists missing resources without section 3 is incomplete.

```markdown
### 1. 已配置
| Resource | ID | Region | State | Notes |
|---|---|---|---|---|

### 2. 未配置 / 异常
- <layer>: not configured / abnormal — <evidence: API, field, value>

### 3. 后续建议
1. <item from section 2> → <exact command> — <constraint>
```

Rules:

1. **Never omit a missing layer.** If the instance has no acceleration region, no endpoint group, or no endpoint, list it in section 2 explicitly instead of only saying the resources that do exist.
2. **Every item in section 2 gets at least one item in section 3**, with the exact command and the constraints that apply:

   | Missing / abnormal | Suggested command | Constraint to state |
   |---|---|---|
   | Basic: no acceleration region (empty `BasicIpSetId`) | `create-basic-ip-set --accelerate-region-id <region> --bandwidth 2` | one acceleration region, IPv4 only, bandwidth >= 2 Mbps |
   | Basic: no endpoint group (empty `BasicEndpointGroupId`) | `create-basic-endpoint-group --endpoint-group-region <region>` | region must differ from the acceleration region |
   | Basic: no endpoint / binding | `create-basic-endpoint` then `create-basic-accelerate-ip-endpoint-relation` | ECS primary ENI must not already carry a public IP |
   | Standard: no IP set | `create-ip-sets --accelerate-region AccelerateRegionId=<region> Bandwidth=<mbps> ...` | bandwidth > 2 Mbps |
   | Standard: no listener | `create-listener --protocol <proto> --port-ranges FromPort=<p> ToPort=<p>` | - |
   | Standard: no endpoint group | `create-endpoint-group` then `update-endpoint-group` | two-step flow; endpoints are added by the update call |
   | Standard: no endpoint | `update-endpoint-group --endpoint-configurations ...` | replaces the whole endpoint list |
   | Unhealthy endpoint | see `Issue 1`, then check backend reachability | - |

3. **Health is reported separately from configuration.** With no endpoint configured, the health conclusion is "not applicable", not "abnormal".
4. **Suggestions are read-only advice.** Diagnosing an instance never authorizes changing it: present the commands and let the user confirm before any write operation.
