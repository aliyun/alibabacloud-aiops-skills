# Verification Methods for ECS Diagnostics

This document provides detailed verification steps to confirm the success of each diagnostic stage in the ECS diagnostics workflow.

## Basic Diagnostics: Cloud Platform Checks Verification

### Step 1: Instance Identification Verification

**Success Criteria:**
- Command returns HTTP 200 status
- Response contains `Instances.Instance` array with at least one element
- Instance details include required fields: `InstanceId`, `Status`, `InstanceName`

**Verification Command:**
```bash
aliyun ecs describe-instances \
  --region-id <region-id> \
  --instance-ids '["<instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq '.Instances.Instance | length'
```

**Expected Output:** A number >= 1

**Failure Indicators:**
- Error: `InvalidInstanceId.NotFound` - Instance ID does not exist in specified region
- Error: `Forbidden.RAM` - Insufficient permissions
- Output: `0` - No instances found matching criteria

---

### Step 2: Instance Status Verification

**Success Criteria:**
- `Status` field is present in response
- Status value is one of: `Running`, `Stopped`, `Starting`, `Stopping`, `Expired`, `Locked`

**Verification Command:**
```bash
aliyun ecs describe-instances \
  --region-id <region-id> \
  --instance-ids '["<instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Instances.Instance[0].Status'
```

**Expected Output:** One of the valid status values

**Status Interpretation:**
- `Running` ✅ - Instance is operational
- `Stopped` ⚠️ - Instance is shut down
- `Starting` ⏳ - Instance is booting
- `Stopping` ⏳ - Instance is shutting down
- `Expired` ❌ - Instance subscription has expired
- `Locked` ❌ - Instance is locked due to security or payment issues

---

### Step 3: System Events Verification

**Success Criteria:**
- Command executes successfully
- Response contains `InstanceSystemEventSet.InstanceSystemEventType` array
- Each event has `EventCycleStatus`, `EventType`, `NotBefore` fields

**Verification Command:**
```bash
aliyun ecs describe-instance-history-events \
  --region-id <region-id> \
  --instance-id <instance-id> \
  --instance-event-cycle-status.1 Executing \
  --instance-event-cycle-status.2 Inquiring \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq '.InstanceSystemEventSet.InstanceSystemEventType | length'
```

**Expected Output:**
- `0` - No active events (good)
- `>0` - Active events present (requires attention)

**Event Impact Assessment:**
- `SystemMaintenance.Reboot` ⚠️ - System maintenance reboot scheduled
- `SystemFailure.Reboot` ❌ - System failure recovery reboot
- `InstanceFailure.Reboot` ❌ - Instance failure recovery reboot
- `SystemMaintenance.Stop` ⚠️ - Planned maintenance shutdown
- `SystemMaintenance.Redeploy` ⚠️ - Instance migration scheduled

---

### Step 4: Security Group Rules Verification

**Success Criteria:**
- Command returns security group permissions array
- Response contains `Permissions.Permission` with rules
- Each rule has `Direction`, `IpProtocol`, `PortRange`, `Policy` fields

**Verification Command:**
```bash
aliyun ecs describe-security-group-attribute \
  --region-id <region-id> \
  --security-group-id <sg-id> \
  --direction ingress \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq '.Permissions.Permission | length'
```

**Expected Output:** Number of rules >= 0

**Key Checks:**
- ✅ SSH (port 22) allowed from trusted IPs for Linux instances
- ✅ RDP (port 3389) allowed from trusted IPs for Windows instances
- ✅ Application ports allowed as needed
- ⚠️ No overly permissive rules (0.0.0.0/0 on all ports)
- ❌ No explicit `Drop` rules blocking required traffic

**Rule Validation Example:**
```bash
# Check if SSH port 22 is open
aliyun ecs describe-security-group-attribute \
  --region-id <region-id> \
  --security-group-id <sg-id> \
  --direction ingress \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq '.Permissions.Permission[] | select(.PortRange == "22/22" and .IpProtocol == "tcp")'
```

---

### Step 5: Network Configuration Verification

**VPC Verification:**

**Success Criteria:**
- VPC status is `Available`
- VPC ID matches instance's VPC

**Verification Command:**
```bash
aliyun vpc describe-vpcs \
  --region-id <region-id> \
  --vpc-id <vpc-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Vpcs.Vpc[0].Status'
```

**Expected Output:** `Available`

**EIP Verification:**

**Success Criteria:**
- If instance requires public access, EIP should be bound
- EIP status is `InUse`

**Verification Command:**
```bash
aliyun vpc describe-eip-addresses \
  --region-id <region-id> \
  --associated-instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.EipAddresses.EipAddress[0].Status'
```

**Expected Output:** `InUse` (if EIP is bound)

---

### Step 6: Monitoring Metrics Verification

**Success Criteria:**
- Command returns metric data points
- `Datapoints` field contains at least one measurement
- Values are within expected ranges

#### CPU Utilization Verification

**Verification Command:**
```bash
aliyun cms describe-metric-last \
  --region-id <region-id> \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions '[{"instanceId":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average'
```

**Thresholds:**
- ✅ 0-70%: Normal
- ⚠️ 70-90%: High
- ❌ 90-100%: Critical

#### Memory Utilization Verification

**Verification Command:**
```bash
aliyun cms describe-metric-last \
  --region-id <region-id> \
  --namespace acs_ecs_dashboard \
  --metric-name memory_usedutilization \
  --dimensions '[{"instanceId":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average'
```

**Thresholds:**
- ✅ 0-70%: Normal
- ⚠️ 70-90%: High
- ❌ 90-100%: Critical

#### Disk Utilization Verification

**Verification Command:**
```bash
aliyun cms describe-metric-last \
  --region-id <region-id> \
  --namespace acs_ecs_dashboard \
  --metric-name diskusage_utilization \
  --dimensions '[{"instanceId":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average'
```

**Thresholds:**
- ✅ 0-80%: Normal
- ⚠️ 80-90%: High
- ❌ 90-100%: Critical

#### Network Traffic Verification

**Inbound Traffic:**
```bash
aliyun cms describe-metric-last \
  --region-id <region-id> \
  --namespace acs_ecs_dashboard \
  --metric-name InternetInRate \
  --dimensions '[{"instanceId":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average'
```

**Outbound Traffic:**
```bash
aliyun cms describe-metric-last \
  --region-id <region-id> \
  --namespace acs_ecs_dashboard \
  --metric-name InternetOutRate \
  --dimensions '[{"instanceId":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average'
```

**Assessment:**
- Compare current traffic to baseline patterns
- Check for unexpected spikes or drops
- Verify traffic doesn't exceed bandwidth limits

---

## Deep Diagnostics: System & Service Checks Verification

### Step 7: System Load Verification

**Success Criteria:**
- Command execution status is `Finished`
- Output is successfully decoded from Base64
- `top`, `uptime`, and `free` commands all return data

**Verification Command:**
```bash
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].InvocationStatus'
```

**Expected Output:** `Finished`

**Output Analysis:**
```bash
# Decode and view output
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' \
  | base64 -d
```

**Load Average Thresholds:**
- ✅ Load < CPU cores: Normal
- ⚠️ Load = 1-2x CPU cores: High
- ❌ Load > 2x CPU cores: Critical

---

### Step 8: Disk Usage Verification

**Success Criteria:**
- Command completes successfully
- `df -h` shows all mounted filesystems
- `lsblk` shows all block devices

**Verification Command:**
```bash
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].InvocationStatus'
```

**Expected Output:** `Finished`

**Disk Usage Thresholds:**
- ✅ 0-80%: Normal
- ⚠️ 80-90%: High
- ❌ 90-100%: Critical

**Critical Checks:**
- Root partition `/` usage
- `/var` partition usage (logs)
- `/tmp` partition usage
- Inode usage (`df -i`)

---

### Step 9: Network Connectivity Verification

**Success Criteria:**
- `ss -tlnp` shows listening ports
- `ip addr` shows network interfaces
- Required ports are in LISTEN state

**Verification Command:**
```bash
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' \
  | base64 -d
```

**Port Checks:**
- ✅ SSH (22) listening for Linux
- ✅ RDP (3389) listening for Windows
- ✅ Application ports listening as expected
- ❌ Unexpected ports listening (security concern)

**Interface Checks:**
- ✅ Primary interface is UP
- ✅ IP address correctly assigned
- ⚠️ Interface is DOWN or no IP

---

### Step 10: System Logs Verification

**Success Criteria:**
- `dmesg` returns recent kernel messages
- `journalctl` returns systemd logs (if available)
- No critical errors in logs

**Verification Command:**
```bash
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' \
  | base64 -d
```

**Critical Error Patterns:**
- ❌ `Out of memory: Kill process` - OOM killer activated
- ❌ `I/O error` - Disk hardware failure
- ❌ `segfault` - Application crashes
- ⚠️ `NMI watchdog` - CPU lock-up
- ⚠️ `temperature above threshold` - Overheating

---

### Step 11: Process Status Verification

**Success Criteria:**
- `ps aux` returns process list
- Top CPU processes are identified
- No excessive zombie processes

**Verification Command:**
```bash
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' \
  | base64 -d
```

**Process Checks:**
- ✅ Critical services running (sshd, systemd, etc.)
- ⚠️ High CPU processes identified
- ❌ Zombie processes (state Z) > 10
- ❌ Suspicious processes (crypto miners, etc.)

---

## Common Failure Scenarios and Verification

### Scenario 1: Cloud Assistant Not Available

**Symptoms:**
- Deep Diagnostics fail to execute
- Error: `The CloudAssistant is not installed on the instance`

**Verification:**
```bash
aliyun ecs describe-instance-attribute \
  --region-id <region-id> \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.CloudAssistantStatus'
```

**Expected Output:** `true`

**Resolution:**
- Install Cloud Assistant agent on the instance
- Verify agent is running: `systemctl status aliyun.service` (Linux)

---

### Scenario 2: Command Timeout

**Symptoms:**
- Command invocation status is `Timeout`
- No output returned

**Verification:**
```bash
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].InvocationStatus'
```

**Output:** `Timeout`

**Resolution:**
- Increase timeout value in `run-command`
- Check if instance is overloaded
- Simplify command for faster execution

---

### Scenario 3: Permission Denied in Guest OS

**Symptoms:**
- Command status is `Failed`
- Error message contains `Permission denied`

**Verification:**
```bash
aliyun ecs describe-invocation-results \
  --region-id <region-id> \
  --invoke-id <invoke-id> \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Invocation.InvocationResults.InvocationResult[0].ErrorInfo'
```

**Resolution:**
- Cloud Assistant runs as root by default
- Check file permissions in error message
- Verify SELinux/AppArmor policies

---

## End-to-End Diagnostics Verification

**Complete Success Criteria:**
1. ✅ All Basic Diagnostics API calls complete successfully
2. ✅ Instance status is `Running`
3. ✅ No critical system events active
4. ✅ Security groups allow required ports
5. ✅ Network configuration is correct
6. ✅ All monitoring metrics within normal ranges
7. ✅ (If Deep Diagnostics executed) All Cloud Assistant commands complete
8. ✅ No critical errors in system logs
9. ✅ Key services are running
10. ✅ Resource usage within acceptable limits

**Partial Success:**
- Some checks pass, others fail or return warnings
- Diagnostic report should clearly indicate which checks failed
- Provide specific recommendations for each failure

**Complete Failure:**
- Multiple critical checks fail
- Instance may be in non-running state
- Immediate intervention required

---

## Automated Verification Script

For automated testing, use this verification script:

```bash
#!/bin/bash
# verify-diagnostics.sh

REGION_ID="$1"
INSTANCE_ID="$2"

echo "=== ECS Diagnostics Verification ==="
echo "Region: $REGION_ID"
echo "Instance: $INSTANCE_ID"
echo ""

# Basic Diagnostics Checks
echo "[1/6] Verifying instance exists..."
INSTANCE_COUNT=$(aliyun ecs describe-instances \
  --region-id "$REGION_ID" \
  --instance-ids "[\"$INSTANCE_ID\"]" \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq '.Instances.Instance | length')

if [ "$INSTANCE_COUNT" -eq 1 ]; then
  echo "✅ Instance found"
else
  echo "❌ Instance not found"
  exit 1
fi

echo "[2/6] Verifying instance status..."
INSTANCE_STATUS=$(aliyun ecs describe-instances \
  --region-id "$REGION_ID" \
  --instance-ids "[\"$INSTANCE_ID\"]" \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Instances.Instance[0].Status')

echo "Status: $INSTANCE_STATUS"
if [ "$INSTANCE_STATUS" = "Running" ]; then
  echo "✅ Instance is running"
else
  echo "⚠️ Instance is not running"
fi

echo "[3/6] Checking system events..."
EVENT_COUNT=$(aliyun ecs describe-instance-history-events \
  --region-id "$REGION_ID" \
  --instance-id "$INSTANCE_ID" \
  --instance-event-cycle-status.1 Executing \
  --instance-event-cycle-status.2 Inquiring \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq '.InstanceSystemEventSet.InstanceSystemEventType | length')

if [ "$EVENT_COUNT" -eq 0 ]; then
  echo "✅ No active system events"
else
  echo "⚠️ $EVENT_COUNT active system event(s)"
fi

echo "[4/6] Checking CPU utilization..."
CPU_UTIL=$(aliyun cms describe-metric-last \
  --region-id "$REGION_ID" \
  --namespace acs_ecs_dashboard \
  --metric-name CPUUtilization \
  --dimensions "[{\"instanceId\":\"$INSTANCE_ID\"}]" \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average // "N/A"')

echo "CPU: $CPU_UTIL%"

echo "[5/6] Checking memory utilization..."
MEM_UTIL=$(aliyun cms describe-metric-last \
  --region-id "$REGION_ID" \
  --namespace acs_ecs_dashboard \
  --metric-name memory_usedutilization \
  --dimensions "[{\"instanceId\":\"$INSTANCE_ID\"}]" \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average // "N/A"')

echo "Memory: $MEM_UTIL%"

echo "[6/6] Checking disk utilization..."
DISK_UTIL=$(aliyun cms describe-metric-last \
  --region-id "$REGION_ID" \
  --namespace acs_ecs_dashboard \
  --metric-name diskusage_utilization \
  --dimensions "[{\"instanceId\":\"$INSTANCE_ID\"}]" \
  --user-agent AlibabaCloud-Agent-Skills \
  | jq -r '.Datapoints' | jq -r '.[0].Average // "N/A"')

echo "Disk: $DISK_UTIL%"

echo ""
echo "=== Verification Complete ==="
```

**Usage:**
```bash
chmod +x verify-diagnostics.sh
./verify-diagnostics.sh cn-hangzhou i-xxxxx
```

---

## Related Links

- [ECS API Error Codes](https://www.alibabacloud.com/help/ecs/developer-reference/api-error-codes)
- [Cloud Assistant Troubleshooting](https://www.alibabacloud.com/help/ecs/user-guide/troubleshoot-cloud-assistant)
- [Cloud Monitor Metrics Reference](https://www.alibabacloud.com/help/cms/developer-reference/metrics-of-ecs)
