# Success Verification Method — Tair DevToolset

## Scenario Goal

**Expected Outcome**: Tair 企业版实例创建成功，公网 TCP 端口可达。

---

## Step-by-Step Verification

### 1. 验证实例创建成功

```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id "${INSTANCE_ID}" \
  --cli-query "Instances.DBInstanceAttribute[0].InstanceStatus" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicator**: 返回值为 `Normal`

### 2. 验证白名单配置

```bash
aliyun r-kvstore describe-security-ips \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicator**: 返回的 `SecurityIpGroups` 中包含 benchmark 分组，且 IP 地址与本机公网 IP 一致。

### 3. 验证公网地址分配

```bash
aliyun r-kvstore describe-db-instance-net-info \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Indicator**: 返回 `NetInfoItems.InstanceNetInfo` 中存在 `IPType` 为 `Public` 的记录，且 `ConnectionString` 非空。

