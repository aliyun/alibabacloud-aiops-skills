# Acceptance Criteria: alibabacloud-lindorm-agent-skill

**Scenario**: Full-scenario Lindorm O&M management
**Purpose**: Skill acceptance criteria

---

## Correct CLI Command Patterns

### 1. Lindorm API Calls, aliyun hitsdb

#### ✅ CORRECT

```bash
# Query instance list, default Shanghai region.
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# Query instance details.
aliyun hitsdb get-lindorm-instance --instance-id ld-uf6l5kr48wqm6rf1h

# Query storage details.
aliyun hitsdb get-lindorm-fs-used-detail --instance-id ld-uf6l5kr48wqm6rf1h

# Query V2 instance storage details.
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id ld-uf64f07n285tlbaz2

# Query engine list.
aliyun hitsdb get-lindorm-instance-engine-list --instance-id ld-uf6l5kr48wqm6rf1h

# Query IP whitelist.
aliyun hitsdb get-instance-ip-white-list --instance-id ld-uf6l5kr48wqm6rf1h

# Query region list.
aliyun hitsdb describe-regions

# Query instance overview, all regions.
aliyun hitsdb get-instance-summary
```

#### ❌ INCORRECT

```bash
# Error: incorrect instance ID format.
aliyun hitsdb get-lindorm-instance --instance-id lindorm-xxx --region cn-shanghai  # ❌ Use ld-xxx format.

# Error: missing required parameter.
aliyun hitsdb get-lindorm-instance --region cn-shanghai  # ❌ Missing --instance-id.

# Error: incorrect region format.
aliyun hitsdb get-lindorm-instance-list --region Shanghai  # ❌ Use cn-shanghai.
```

### 2. CloudMonitor API Calls, aliyun cms

#### ✅ CORRECT

```bash
# Query Lindorm monitoring metric list.
aliyun cms describe-metric-meta-list --namespace acs_lindorm

# Query latest CPU idle rate data.
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6l5kr48wqm6rf1h"}]'

# Query historical monitoring data, specified time range.
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6l5kr48wqm6rf1h"}]' \
    --start-time "2026-04-14 08:00:00" \
    --end-time "2026-04-14 09:00:00" \
    --period 60
```

#### ❌ INCORRECT

```bash
# Error: incorrect namespace.
aliyun cms describe-metric-meta-list --namespace acs_hbase --region cn-shanghai  # ❌ Use acs_lindorm.

# Error: incorrect metric name.
aliyun cms describe-metric-last --metric-name cpu_usage  # ❌ Use cpu_idle.

# Error: incorrect dimensions format.
aliyun cms describe-metric-last --dimensions "instanceId=ld-xxx"  # ❌ Use JSON array format.
```

---

## Parameter Validation Patterns

### 1. Instance ID Format

#### ✅ CORRECT

```text
ld-uf6l5kr48wqm6rf1h  # ✅ Starts with ld-, followed by letters and digits.
ld-bp1234567890abcdef  # ✅ Correct format.
```

#### ❌ INCORRECT

```text
lindorm-xxx  # ❌ Does not start with ld-.
ld_xxx  # ❌ Uses underscore instead of hyphen.
LD-XXX  # ❌ Uses uppercase. Lowercase is recommended.
```

### 2. Region Format

#### ✅ CORRECT

```text
cn-shanghai  # ✅ Correct format.
cn-beijing  # ✅ Correct format.
cn-hangzhou  # ✅ Correct format.
```

#### ❌ INCORRECT

```text
shanghai  # ❌ Missing cn- prefix.
CN-SHANGHAI  # ❌ Uses uppercase.
cn_shanghai  # ❌ Uses underscore.
```

### 3. Time Format

For time format rules, see SKILL.md → "Time format". Acceptance examples:

#### ✅ CORRECT

```bash
--start-time "2026-04-14 08:00:00"  # ✅ Local time format, recommended, parsed as CST.
--start-time "1773897600000"        # ✅ Unix millisecond timestamp.
--start-time "2026-04-14T08:00:00Z" # ✅ ISO 8601 UTC, parsed as UTC. Note timezone conversion: UTC+8=CST.
```

#### ❌ INCORRECT

```bash
--start-time "2026-04-14T08:00Z"     # ❌ ISO 8601 short format without seconds is unsupported and reports parse param time error.
--start-time "2026/04/14 08:00:00"  # ❌ Uses slashes as separators.
--start-time "08:00:00"             # ❌ Provides only time and lacks date.
```

---

## Output Format Validation

### 1. Monitoring Data Output

#### ✅ CORRECT Output Structure

```json
{
  "Datapoints": [
    {
      "instanceId": "ld-uf6l5kr48wqm6rf1h",
      "timestamp": 1773897600000,
      "Average": 75.5
    }
  ],
  "DatapointCount": 1,
  "Success": true
}
```

#### Validation Points

- `Datapoints` array exists and is not empty.
- Each data point contains `instanceId`, `timestamp`, and `Average`. Some metrics contain `Maximum`/`Minimum`.
- `Average` is within a reasonable range, such as 0 to 100 for CPU idle rate.

### 2. Instance List Output

#### ✅ CORRECT Output Structure

```json
{
  "InstanceList": [
    {
      "InstanceId": "ld-uf6l5kr48wqm6rf1h",
      "InstanceAlias": "production-environment",
      "InstanceStatus": "ACTIVATION",
      "RegionId": "cn-shanghai"
    }
  ],
  "TotalCount": 1
}
```

#### Validation Points

- `InstanceList` array exists.
- Each instance contains `InstanceId` and `InstanceStatus`.
- `InstanceStatus` is a valid status value: ACTIVATION, CREATING, or STOPPED.

---

## Error Handling Patterns

### 1. API Error Response

#### ✅ CORRECT Error Handling

```json
{
  "Code": "InvalidParameter.InstanceId",
  "Message": "The specified instance ID is invalid.",
  "RequestId": "xxx"
}
```

**Handling flow**:
1. Read the `Code` field to identify the error type.
2. Refer to `references/02-ops/error-troubleshoot.md` to find a solution.
3. Guide the user to check parameters or permissions.

#### ❌ INCORRECT Error Handling

- Ignore the error code and directly return the raw error message.
- Guess the error cause based on training knowledge. Official documentation should be checked.

---

## Scenario Trigger Validation

### Correct Trigger Scenarios

| User Input | Triggered Scenario | Execution Document |
|---------|---------|---------|
| "Which Lindorm instances do I have?" | Instance query | `02-ops/instance-management.md` |
| "What is the CPU utilization?" | Monitoring query | `02-ops/monitoring-guide.md` |
| "Error InvalidParameter" | Error troubleshooting | `02-ops/error-troubleshoot.md` |
| "How do I connect to Lindorm?" | Connection guide | `01-dev/connection-guide.md` |
| "How do I create a table?" | Table creation guide | `01-dev/table-design.md` |

### Incorrect Trigger Scenarios

| User Input | Error Handling |
|---------|---------|
| "Which RDS instances do I have?" | ❌ Should not trigger Lindorm skill. Prompt the user to use RDS skill. |
| "How do I use MySQL?" | ❌ Should not trigger unless Lindorm SQL is explicitly mentioned. |

---

## Security Specification Validation

For security rules, see SKILL.md → "Prerequisites → Credentials configured".

#### ❌ FORBIDDEN

```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID           # ❌ Reading or printing AK/SK is forbidden.
"Please enter your AccessKey ID"            # ❌ Asking the user to enter it in the conversation is forbidden.
aliyun configure set --access-key-id LTAI5t  # ❌ Hardcoding credentials is forbidden.
```