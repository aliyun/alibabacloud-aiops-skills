# Cloud Firewall ACL Diagnosis Framework

Complete diagnosis framework for Cloud Firewall ACL rules, including analysis mechanism, troubleshooting, and execution checklist.

---

## 1. Matching Mode Overview

### Matching Modes by Firewall Type

| Firewall Type | Mode | Matching Tuples | Description |
|--------------|------|----------------|-------------|
| Internet/NAT | Loose | 4-tuple | Source IP + Destination IP + Destination Port + Protocol |
| Internet/NAT | Strict | 7-tuple | 4-tuple + Application Protocol + Domain |
| VPC | Always Layer 4 | 4-tuple | No strict mode concept, domain rules not supported |

**Key Impact Example**:

In loose mode, with two rules:
1. Order=1, Source=any, Dest=10.0.0.1, Port=443, Proto=TCP, App=HTTPS, Action=**drop**
2. Order=2, Source=any, Dest=10.0.0.1, Port=443, Proto=TCP, App=SSL, Action=**accept**

An SSL (non-HTTPS) request to port 443:
- **Loose mode**: Matches Rule 1 (4-tuple matches, ignores App), gets **dropped**
- **Strict mode**: Rule 1 4-tuple matches but App mismatch (HTTPS != SSL), skips to Rule 2, gets **accepted**

---

## 2. Three-Layer Check Framework

### 2.1 Internet Firewall Three-Layer Check

All layers must pass for rules to take effect.

| Check Layer | Check Item | Judgment Method | Conclusion When Failed |
|--------|--------|----------|---------------|
| Rule layer | Rule enabled | `Release == "true"` | Enable rule in console |
| Rule layer | Priority order | Specific rule Order < broad rule Order | Adjust priority in console |
| Asset layer | Protection status | `ProtectStatus == "open"` | **Must enable protection first** |
| Asset layer | ACL engine mode (domain rules) | `EngineMode == "strict"` | Switch to strict mode in console |

**Note**: Internet Firewall has asset-level ACL engine mode, not global.

### 2.2 NAT Boundary Firewall Three-Layer Check

| Check Layer | Check Item | Judgment Method | Conclusion When Failed |
|--------|--------|----------|---------------|
| Rule layer | Rule enabled | `Release == "true"` | Enable rule in console |
| Rule layer | Priority order | Specific rule Order < broad rule Order | Adjust priority in console |
| Firewall layer | NAT firewall enabled | Query NatFirewallList, check status | **Must enable NAT firewall first** |
| Firewall layer | ACL engine mode (domain rules) | `StrictMode == 1` | Switch to strict mode in console |

**Note**: NAT Firewall has firewall-level ACL engine mode (StrictMode).

---

## 3. Common Problem Root Causes

### Internet Firewall

| Root Cause | Typical Manifestation | Resolution Direction |
|------|----------|----------|
| Asset protection not enabled | Rule created but ProtectStatus=closed | Enable protection in console |
| Asset ACL engine mode is loose | EngineMode=loose, domain rules not working | Switch asset to strict mode |
| Domain recognition mode not specified | Domain configured but FQDN/DNS not specified | Explicitly select recognition mode |
| Priority intercepted | Higher priority broad rule matches first | Adjust priority order |
| **Wrong direction** | in/out reversed | Inbound=external→internal, Outbound=internal→external |
| **Outbound Source/Destination misconfigured** | **Source=public IP in outbound rule** | **Source should be internal CIDR, Destination should be public IP** |
| Layer 7 pre-match | Unknown application triggers pre-match and allowed | Use DNS mode or configure Layer 4 fallback |

### VPC Boundary Firewall

| Root Cause | Typical Manifestation | Resolution Direction |
|------|----------|----------|
| Wrong VpcFirewallId | Cannot query rules | Confirm correct ID through console |
| VPC CIDR mismatch | Rule CIDR doesn't cover actual VPC CIDR | Confirm VPC CIDR, adjust address range |
| CEN instance abnormal | Cloud Enterprise Network not connected or status abnormal | Check CEN instance status |
| Priority intercepted | Higher priority broad rule matches first | Adjust priority order |

### NAT Boundary Firewall

| Root Cause | Typical Manifestation | Resolution Direction |
|------|----------|----------|
| **NAT firewall not enabled** | **Cannot query rules or logs** | **Enable NAT firewall in console first** |
| **ACL engine mode is loose** | **StrictMode=0, domain rules not working** | **Switch to strict mode in console** |
| **Test server IP not in rule CIDR** | **Rule hit count is 0** | **First query SNAT table to confirm actual IP, then configure rule** |
| Wrong NatFirewallId | Cannot query rules | Confirm correct ID through console |
| Priority intercepted | Higher priority broad rule matches first | Adjust priority order |
| Rule not enabled | Release=false, traffic not controlled by rule | Enable rule switch in console |
| Default allow fallback | All rules not matched, traffic allowed by default | Add drop 0.0.0.0/0 fallback rule at end |

---

## 4. Layer 7 Policy Split & Pre-Match Mechanism

**Applies to**: Internet/NAT Firewall domain rules in strict mode only

### Policy Split Mechanism

When you configure a Layer 7 policy (with domain) in strict mode, Cloud Firewall **splits it at底层** into multiple rules:

```
User configures one rule:
  Source: 10.0.0.0/8
  Destination: *.example.com
  DestinationType: domain
  Port: 443
  Proto: TCP
  App: HTTPS
  Action: accept
        ↓
Cloud Firewall splits into:
  Rule 1 (Layer 7): 4-tuple + App=HTTPS + Domain=*.example.com → accept
  Rule 2 (Layer 4 fallback): 4-tuple only (no App/Domain) → depends on configuration
```

**Why this matters for diagnosis**:

1. **Traffic log shows `AclPreRuleId`**: This indicates the traffic matched the pre-match rule (Layer 7 not yet identified)
2. **`AclPreState=app_unknown`**: Application not yet identified, traffic temporarily allowed
3. **Hit count discrepancy**: The visible rule's `HitTimes` may not match actual traffic count due to splitting

### Pre-Match Flow

```
Traffic arrives (e.g., telnet to example.com:80)
        ↓
System attempts application recognition (DPI)
        ↓
Cannot immediately recognize domain (no HTTP request) → AppName=Unknown
        ↓
"Pre-matches" to Layer 7 rule with domain configured (AclPreRuleId points to this rule)
        ↓
AclPreState = app_unknown → Allow first, wait for subsequent data to recognize domain
        ↓
If still cannot recognize (e.g., pure TCP traffic) → Traffic continuously allowed
```

### Pre-Match Problem Solutions

1. **Testing domain policies**: Use `curl -k "https://domain"`, **do NOT use telnet**
2. **Block pure TCP/Unknown traffic**: Use DNS resolution mode, or configure Layer 4 fallback policy
3. **Allow only HTTP/HTTPS outbound**: Configure Layer 7 domain policy + final Layer 4 0.0.0.0/0 deny rule

---

## 5. Testing Standardization

**⚠️ CRITICAL: Testing method MUST match ACL engine mode**

| Engine Mode | Testing Tool | Why | Example |
|-------------|-------------|-----|---------|
| **Loose mode** (Internet: EngineMode=loose, NAT: StrictMode=0) | `telnet`, `nc`, `curl` | Only 4-tuple matching, any TCP/UDP traffic works | `telnet example.com 443` |
| **Strict mode** (Internet: EngineMode=strict, NAT: StrictMode=1) + **Domain rules** | `curl`, `wget` **ONLY** | Requires HTTP/HTTPS request to trigger domain recognition | `curl -k "https://example.com"` |
| **Strict mode** + **IP rules** (no domain) | `telnet`, `nc`, `curl` | 4-tuple matching works normally | `telnet 203.0.113.10 443` |

### Common Testing Mistakes

❌ **Wrong**: Using `telnet` to test domain rules in strict mode
```bash
telnet example.com 443
# Problem: telnet only establishes TCP connection, doesn't send HTTP request
# Result: Domain cannot be recognized, AclPreState=app_unknown, traffic allowed
```

✅ **Correct**: Using `curl` to test domain rules in strict mode
```bash
curl -k "https://example.com"
# Correct: curl sends HTTP request with Host header
# Result: Domain recognized, Layer 7 rule matched correctly
```

**Why telnet fails for domain rules**:
1. Telnet only establishes TCP 3-way handshake
2. No HTTP request sent, no Host header
3. Cloud Firewall DPI cannot extract domain from TCP payload
4. System enters "pre-match" state, allows traffic temporarily
5. If still no domain recognized → Traffic continuously allowed, rule appears "not working"

### Testing Checklist

- [ ] Confirm ACL engine mode (loose vs strict)
- [ ] If strict mode + domain rules → MUST use `curl`/`wget`, NOT `telnet`
- [ ] Wait 10-30 seconds after rule modification before testing
- [ ] Check traffic logs for `AclPreState` field
- [ ] If `app_unknown` persists → Application recognition issue, not rule issue

---

## 6. Traffic Log Key Fields

| Field | Description |
|------|------|
| `RuleResult` | **0=allow, 2=deny** |
| `RuleId` / `RuleName` | Matched ACL rule |
| `AclPreRuleId` / `AclPreRuleName` | Pre-match rule (Layer 7 policy specific) |
| `AclPreState` | `app_unknown` = application not identified |
| `AppName` | Application type (HTTP/HTTPS/Unknown, Internet/NAT only) |

---

## 7. CLI Query Commands

### Internet Firewall

```bash
# Query asset list
aliyun cloudfw describe-asset-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# Query ACL rules (outbound)
aliyun cloudfw describe-control-policy \
  --Direction out \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# Query ACL rules (inbound)
aliyun cloudfw describe-control-policy \
  --Direction in \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# Query traffic logs
aliyun cloudfw describe-traffic-log \
  --StartTime <START_UNIX_TIMESTAMP> \
  --EndTime <END_UNIX_TIMESTAMP> \
  --SourceCode yundun \
  --FirewallType InternetFirewall \
  --Direction <in|out> \
  --CurrentPage 1 \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

### VPC Boundary Firewall

```bash
# Query firewall list
aliyun cloudfw describe-vpc-firewall-list \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# Query ACL rules
aliyun cloudfw describe-vpc-firewall-control-policy \
  --VpcFirewallId <VpcFirewallId> \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# Query traffic logs
aliyun cloudfw describe-traffic-log \
  --StartTime <START_UNIX_TIMESTAMP> \
  --EndTime <END_UNIX_TIMESTAMP> \
  --SourceCode yundun \
  --FirewallType VpcFirewall \
  --CurrentPage 1 \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

### NAT Boundary Firewall

```bash
# Query firewall list
aliyun cloudfw describe-nat-firewall-list \
  --PageNo 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# Query ACL rules
aliyun cloudfw describe-nat-firewall-control-policy \
  --NatFirewallId <NatFirewallId> \
  --CurrentPage 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis

# Query traffic logs
aliyun cloudfw describe-traffic-log \
  --StartTime <START_UNIX_TIMESTAMP> \
  --EndTime <END_UNIX_TIMESTAMP> \
  --SourceCode yundun \
  --FirewallType NatFirewall \
  --CurrentPage 1 \
  --PageSize 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

---

## 8. Diagnosis Execution Checklist (Internal Use)

**🔴 EXECUTION MANDATE**: This checklist MUST be executed when user describes a rule issues. NO EXCEPTIONS.

```markdown
## Step 0: Identify Protected Asset
- Direction: [in/out]
- Protected asset: [IP/address]
- Rule: Inbound → Protected asset = Destination; Outbound → Protected asset = Source

## Step 1: Confirm Policy Information
- Firewall type: [Internet/NAT/VPC]
- CLI query executed: [YES/NO]
- Policies found: [list or "none"]

## Step 2: Pre-check (MUST show actual CLI query results)
- Check 2.1 - Asset protection: 
  - CLI executed: [YES/NO]
  - Actual ProtectStatus value from CLI: [open/closed]
  - Result: [PASS/FAIL]
- Check 2.2 - Policy matches asset: 
  - Actual Source/Destination from CLI: [values]
  - Result: [PASS/FAIL]
- Check 2.3 - Policy enabled: 
  - Actual Release value from CLI: [true/false]
  - Result: [PASS/FAIL]
- Pre-check result: [ALL PASS/ANY FAIL]

[If ANY FAIL → STOP here, output conclusion]

## Step 3: Query Traffic Logs
- CLI query executed: [YES/NO]
- Logs found: [YES/NO]

## Step 4: Detailed Diagnosis
- Dimension 4.1 - Engine mode: 
  - Actual EngineMode value from CLI: [loose/strict]
- Dimension 4.2 - Layer 4/7: [analysis]
- Dimension 4.3 - Testing method: [analysis]
- Dimension 4.4 - Log analysis: [analysis]
```

**⚠️ FORBIDDEN**:
- ❌ Jump to conclusions before completing ALL Step 2 checks
- ❌ Mention "engine mode" before completing Step 2
- ❌ Skip any Step 2 check item
- ❌ Guess ProtectStatus/EngineMode values without CLI query

**⚠️ REQUIRED**:
- ✅ Execute ALL 3 Step 2 checks IN ORDER (2.1 → 2.2 → 2.3)
- ✅ Show ALL Step 2 check results with actual CLI values (even if some fail)
- ✅ Only output conclusion AFTER completing all Step 2 checks

---

## 9. Item-by-Item Troubleshooting Checklist

### Internet Firewall

- [ ] Asset protection enabled (ProtectStatus=open)
- [ ] ACL engine mode set to strict (EngineMode=strict) for domain rules
- [ ] Rule direction correct (in/out)
- [ ] Rule priority order correct (specific rules first)
- [ ] Domain recognition mode set (FQDN/DNS/Both)
- [ ] Rule enabled (Release=true)
- [ ] Waited 10-30 seconds after modification

### VPC Boundary Firewall

- [ ] VPC firewall enabled
- [ ] Correct VpcFirewallId used
- [ ] VPC CIDR matches rule configuration
- [ ] Rule priority order correct
- [ ] Rule enabled (Release=true)
- [ ] Waited 10-30 seconds after modification

### NAT Boundary Firewall

- [ ] NAT firewall enabled (query NatFirewallList)
- [ ] ACL engine mode set to strict (StrictMode=1) for domain rules
- [ ] Correct NatFirewallId used
- [ ] Source IP matches actual IP after SNAT
- [ ] Rule priority order correct
- [ ] Rule enabled (Release=true)
- [ ] Waited 10-30 seconds after modification

---

## 10. Conclusion Classification Requirements

**MUST classify all findings in the diagnosis report into three categories:**

1. **Verified** (`[Verified]`): Facts confirmed through actual CLI execution.
   - Example: `[Verified]` ProtectStatus=closed (from describe-asset-list output)

2. **Unverified** (`[Unverified]`): Possible causes based on theory, requiring further confirmation.
   - Example: `[Unverified]` IPv6 connection may bypass rules configured only for IPv4

3. **Blocked** (`[Blocked]`): Checks that could not be completed due to insufficient RAM permissions.
   - Example: `[Blocked]` Cannot verify ProtectStatus (Forbidden.RAM on describe-asset-list)

**Permission-blocked checks format in final report**:

| Blocked Check | Required Permission | Impact |
|--------------|--------------------|--------|
| [check name] | [RAM action needed] | [what cannot be verified] |

---

## 11. Rule Field Reference

### Common Fields

| Field | Description |
|------|------|
| `AclAction` | `accept` (allow) / `drop` (deny) / `log` (observe) |
| `Source` / `SourceType` | Source address and type: `net` / `group` / `location` |
| `Destination` / `DestinationType` | Destination address and type: `net` / `group` / `domain` (Internet/NAT outbound only) / `location` |
| `DestPort` | Destination port (e.g., `80/80`, `0/0`) |
| `Proto` | `TCP` / `UDP` / `ICMP` / `ANY` |
| `Order` | Priority, lower value matches first |
| `Release` | `true` (enabled) / `false` (disabled) |
| `HitTimes` | Hit count, helps determine rule effectiveness |
