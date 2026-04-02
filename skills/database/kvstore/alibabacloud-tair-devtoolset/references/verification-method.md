# Success Verification Method — Tair DevToolset

## Scenario Goal

**Expected Outcome**: Tair Enterprise Edition instance created successfully, public TCP port reachable.

---

## Step-by-Step Verification

### 1. Verify Instance Creation Success

```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id "${INSTANCE_ID}" \
  --cli-query "Instances.DBInstanceAttribute[0].InstanceStatus" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicator**: Return value is `Normal`

### 2. Verify Whitelist Configuration

```bash
aliyun r-kvstore describe-security-ips \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicator**: Returned `SecurityIpGroups` contains benchmark group, and IP address matches local public IP.

### 3. Verify Public Endpoint Allocation

```bash
aliyun r-kvstore describe-db-instance-net-info \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicator**: Returned `NetInfoItems.InstanceNetInfo` contains a record with `IPType` as `Public`, and `ConnectionString` is not empty.