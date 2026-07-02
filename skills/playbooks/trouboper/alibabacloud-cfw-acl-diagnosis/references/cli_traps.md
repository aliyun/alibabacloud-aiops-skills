# Alibaba Cloud Cloud Firewall CLI Pitfalls and Notes

This document records pitfalls and solutions encountered when using the Alibaba Cloud CLI to diagnose Cloud Firewall issues.

> ⚠️ This skill is a read-only diagnostic tool. This document only covers pitfalls for query commands and does not include write operations.

---

## 1. Region Issues

### Myth: You need to ask for the Region

**Facts**:
- Cloud Firewall is a **global service**. Rule configuration is independent of Region.
- Any Region (e.g., `cn-hangzhou`) can be used to call the API.
- **Do NOT ask the user for the Region where assets are located.**

---

## 2. Asset Protection Status Diagnosis Trap

### Trap: Rule exists but does not take effect → forgot to check ProtectStatus

**Symptoms**:
- The corresponding ACL rule can be found in the rule list.
- Traffic is still not controlled by the rule.

**Root Cause**:
- The asset's `ProtectStatus` is `closed` (protection not enabled).
- Rules do not take effect when protection is not enabled. This is the most common issue.

**Diagnosis Method**:
```bash
aliyun cloudfw describe-asset-list --CurrentPage 1 --PageSize 50 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis/{{SESSION_ID}}"
```

Check the `ProtectStatus` field:
- `open`: Protection is enabled ✅
- `closed`: Protection is not enabled ❌ → Instruct the user to enable it manually in the console.

---

## 3. Engine Mode Diagnosis Trap

### Trap: Domain rules do not take effect in loose mode → forgot to check EngineMode/StrictMode

**Symptoms**:
- A rule with `DestinationType=domain` is configured.
- Access to the target domain does not match the rule.

**Root Cause**:
- The Internet Firewall asset `EngineMode=loose`, or NAT Firewall `StrictMode=0`.
- In loose mode, the **domain does not participate in matching**. Only the 4-tuple (source IP + destination IP + destination port + protocol) is matched.

**Diagnosis Method**:
- Internet Firewall: `describe-asset-list` → check the `EngineMode` field of the target asset.
- NAT Firewall: `describe-nat-firewall-list` → check the `StrictMode` field.

**Tell the user**: Switch the engine mode to strict mode in the console to make domain rules effective.

---

## 4. NAT Firewall SNAT Source IP Trap

### Trap: Rule source address does not match the actual traffic source IP

**Symptoms**:
- The NAT rule is configured with an internal IP range, but the rule hit count is 0.

**Root Cause**:
- NAT Firewall inspects the public IP **after SNAT translation**, not the internal private IP.
- The rule source address must be configured as the actual egress IP after SNAT.

**Diagnosis Direction**:
- Tell the user to check the SNAT table in the NAT Gateway console to confirm the actual egress IP.
- Compare whether the rule Source address matches the SNAT egress IP.

---

## 5. Traffic Log Query Traps

### Trap: Setting FlowType causes no results

**Symptoms**: Traffic log query returns empty, but traffic actually exists.

**Root Cause**: The `FlowType` parameter filters out some traffic.

**Correct Approach**: **Do NOT set the `FlowType` parameter**. Leave it empty to query all traffic.

### Trap: Timestamp Units

**Time Conversion**:
```bash
date -d "2026-04-01 11:25:00" +%s   # Linux
date -j -f "%Y-%m-%d %H:%M:%S" "2026-04-01 11:25:00" +%s  # macOS
```

---

## 6. Pagination Query Trap

### Trap: Only the first page is returned by default, mistakenly thinking "these are all the rules"

**Notes**:
- Default `PageSize=10`. When there are many rules/assets, there are multiple pages.
- Must check `TotalCount`. If `TotalCount > PageSize`, continue querying with `--CurrentPage 2`.
- Before concluding "all assets/rules", **must query all pages**.

---

## 7. Credentials and Profile Traps

| Prohibited Operation | Reason |
|---------|------|
| `--profile` parameter | Evaluation system Forbidden rule |
| `aliyun configure get` | Exposes AK/SK, serious security violation |
| `aliyun configure list` | Scans all profiles |
| `cat ~/.aliyun/config.json` | Reads credential file |

**Correct Approach**: Rely on the default credential chain (environment variables or default profile in `~/.aliyun/config.json`).

---

## 8. Activation Delay

Rules do not take effect immediately after modification; there is a **5-15 second** delay.

If the user says "I just modified it and tested, but it doesn't work" → remind them to wait a moment and retry.
