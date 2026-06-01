# Cloud Firewall CLI Command Reference

> This file contains complete examples of all Cloud Firewall-related CLI commands.
> 
> Agent should read this file before executing commands to get correct command formats.

---

## Credential Usage

### Profile Handling Rules (Critical)

**IMPORTANT: To ensure Skill portability, MUST follow these rules:**

- ❌ **DO NOT use `--profile` parameter** (Evaluation system Forbidden rule)
- ❌ **DO NOT auto-detect user's profile** (Do NOT run `aliyun configure list`)
- ❌ **DO NOT run `aliyun configure get`** (Exposes AK/SK, serious security violation)
- ❌ **DO NOT assume or hardcode profile names**
- ✅ **Rely on default profile** (Do NOT explicitly specify any profile parameter)
- ✅ **Rely on environment variables or ~/.aliyun/config.json default configuration**

**Correct Approach**:
```bash
# ✅ Correct: No --profile specified, relies on default configuration
aliyun cloudfw describe-asset-list --CurrentPage 1 --PageSize 50

# ❌ Wrong: Using --profile (Forbidden)
aliyun cloudfw describe-asset-list --profile default --CurrentPage 1 --PageSize 50

# ❌ Wrong: Running configure get (Exposes AK/SK)
aliyun configure get --profile default
```

**Alibaba Cloud CLI (aliyun)**:
- **Do NOT use `--profile` parameter**, rely on default credential chain
- **Do NOT explicitly pass credentials**
- All commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis`

---

## 1. Internet Firewall Commands

### 1.1 Query Asset List

```bash
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

**Key Response Fields**:
- `Assets[].InternetAddress` - Public IP address
- `Assets[].ProtectStatus` - `open` (protected) / `closed` (unprotected, rules won't work!)
- `Assets[].EngineMode` - `loose` / `strict` (domain rules require strict)

### 1.2 Query ACL Rules (Outbound)

```bash
aliyun cloudfw describe-control-policy \
  --Direction out \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

### 1.3 Query ACL Rules (Inbound)

```bash
aliyun cloudfw describe-control-policy \
  --Direction in \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

**Key Response Fields**:
- `Policy[].AclAction` - `accept` / `drop` / `log`
- `Policy[].Source` / `Policy[].SourceType` - Source address and type
- `Policy[].Destination` / `Policy[].DestinationType` - Destination address and type
- `Policy[].Order` - Priority (lower = higher priority)
- `Policy[].Release` - `true` (enabled) / `false` (disabled)
- `Policy[].HitTimes` - Hit count

### 1.4 Query Traffic Logs

```bash
aliyun cloudfw describe-traffic-log \
  --StartTime 1712000000 \
  --EndTime 1712086400 \
  --SourceCode yundun \
  --FirewallType InternetFirewall \
  --SrcIP '1.2.3.4' \
  --DstIP '5.6.7.8' \
  --DstPort 80 \
  --Direction out \
  --CurrentPage 1 \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

**Key Response Fields**:
- `RuleResult` - **0=allow, 2=deny**
- `RuleId` / `RuleName` - Matched ACL rule
- `AclPreRuleId` / `AclPreState` - Pre-match rule (L7 only, `app_unknown` = not identified)
- `AppName` - Application type (HTTP/HTTPS/Unknown)

---

## 2. VPC Boundary Firewall Commands

### 2.1 Query Firewall List

```bash
aliyun cloudfw describe-vpc-firewall-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

**Key Response Fields**:
- `VpcFirewalls[].VpcFirewallId` - VPC firewall instance ID
- `VpcFirewalls[].VpcFirewallName` - Firewall name
- `VpcFirewalls[].Status` - Firewall status

### 2.2 Query ACL Rules

```bash
aliyun cloudfw describe-vpc-firewall-control-policy \
  --VpcFirewallId vfw-xxx \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

### 2.3 Query Traffic Logs

```bash
aliyun cloudfw describe-traffic-log \
  --StartTime 1712000000 \
  --EndTime 1712086400 \
  --SourceCode yundun \
  --FirewallType VpcFirewall \
  --SrcIP '10.0.0.1' \
  --DstIP '10.0.0.2' \
  --DstPort 443 \
  --CurrentPage 1 \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

---

## 3. NAT Boundary Firewall Commands

### 3.1 Query Firewall List

```bash
aliyun cloudfw describe-nat-firewall-list \
  --PageNo 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

**Key Response Fields**:
- `NatFirewalls[].NatFirewallId` - NAT firewall instance ID
- `NatFirewalls[].StrictMode` - `0`=loose, `1`=strict (domain rules require 1)

### 3.2 Query ACL Rules

```bash
aliyun cloudfw describe-nat-firewall-control-policy \
  --NatFirewallId nfw-xxx \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

### 3.3 Query Traffic Logs

```bash
aliyun cloudfw describe-traffic-log \
  --StartTime 1712000000 \
  --EndTime 1712086400 \
  --SourceCode yundun \
  --FirewallType NatFirewall \
  --SrcIP '1.2.3.4' \
  --DstIP '5.6.7.8' \
  --DstPort 80 \
  --CurrentPage 1 \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

---

## 4. Common Errors and Solutions

| Error | Cause | Solution |
|------|------|---------|  
| `InvalidInstance.NotFound` | Firewall instance not found | Check instance ID, verify region |
| `Forbidden.RAM` | Insufficient permissions | Add AliyunYundunCloudFirewallReadOnlyAccess policy |
| `InvalidParameter` | Used `--profile` | Remove `--profile`, rely on default credential chain |
| No logs returned | Wrong time range or FlowType set | Check timestamps, remove FlowType parameter |
| Plugin not found | Cloud Firewall plugin not installed | Run: `aliyun plugin install --names aliyun-cli-cloudfw` |

---

## 5. Important Notes

1. **Direction Parameter**: Only required for Internet Firewall (`--Direction in|out`), NOT needed for VPC/NAT firewall
2. **FlowType**: **Do NOT set**, keep empty, setting it may cause no logs found
3. **Time Conversion**: `date -d "2026-04-01 11:25:00" +%s`
4. **Pagination**: Always check `TotalCount`, use `--CurrentPage 2` if needed
5. **User-Agent**: ALL commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis`
6. **No Profile**: NEVER use `--profile` parameter in any command
