# SAG Inspection Rules

Detailed threshold definitions and judgment logic for each inspection item.

## Status Levels

| Level | Symbol | Meaning | Action Required |
|-------|--------|---------|-----------------|
| Green | PASS | Normal, no action needed | None |
| Yellow | WARN | Attention needed, potential issue | Monitor or plan fix |
| Red | FAIL | Critical issue, immediate action | Fix immediately |

---

## Rule 1: Device Online Status

**API**: `describe-smart-access-gateways` -> `Status` field

**Judgment**:
```
if Status == "Active":
    return GREEN, "Device online and active"
elif Status == "Offline":
    return RED, "Device offline - check power, network cable, 4G card"
elif Status == "Ordered":
    return YELLOW, "Device ordered but not yet activated"
else:
    return YELLOW, f"Abnormal status: {Status}"
```

**Recommended Actions (Red)**:
1. Check physical power supply
2. Check network cable connection on WAN port
3. Check 4G SIM card if using cellular backup
4. Verify local firewall allows outbound UDP 500/4500
5. Contact Alibaba Cloud support if persists >30 minutes

---

## Rule 2: VPN Tunnel Status

**API**: `describe-smart-access-gateway-attribute` -> `VpnStatus` field

**Judgment**:
```
if VpnStatus == "UP":
    return GREEN, "VPN tunnel established"
elif VpnStatus == "DOWN":
    return RED, "VPN tunnel down"
else:
    return YELLOW, f"VPN status unknown: {VpnStatus}"
```

**Recommended Actions (Red)**:
1. Check device online status first (Rule 1)
2. Verify firewall allows UDP 500, UDP 4500 to POP access point IPs
3. Check if access point IP has changed (use ListSmartAGByAccessPoint)
4. Verify WAN port has valid public IP
5. If behind NAT, ensure NAT-T is supported

---

## Rule 3: HA Status

**API**: `describe-smart-access-gateway-ha`

**Judgment**:
```
if DeviceLevelBackupState == "Active" and all links normal:
    return GREEN, "HA normal, primary active"
elif frequent_switchover detected:
    return YELLOW, "HA flapping detected"
elif standby_offline:
    return RED, "Standby device offline, no redundancy"
else:
    return GREEN, "HA not configured (single device)"
```

**Recommended Actions (Yellow/Red)**:
- Flapping: Check physical links, avoid dual-active scenario
- Standby offline: Check standby device power and connectivity
- Consider upgrading firmware if flapping persists

---

## Rule 4: Instance Expiry

**API**: `describe-smart-access-gateways` -> `EndTime` field

**Judgment**:
```
days_remaining = (EndTime - now).days

if days_remaining > 30:
    return GREEN, f"Expires in {days_remaining} days"
elif days_remaining > 7:
    return YELLOW, f"Expires in {days_remaining} days - renew soon"
elif days_remaining > 0:
    return RED, f"Expires in {days_remaining} days - URGENT renewal needed"
else:
    return RED, f"EXPIRED {abs(days_remaining)} days ago - service may be suspended"
```

**Additional Context**:
- Expired instances may lose VPN connectivity within 24-72 hours

**Why these thresholds**: 30 days gives enough lead time for procurement approval and renewal processing in enterprise environments. 7 days is the critical window because Alibaba Cloud sends final warning notifications at T-7, and post-expiry grace periods are typically 24-72 hours before service suspension.

---

## Rule 5: Packet Drop (DropTopN)

**API**: `describe-sag-drop-topn` (with `--size 10`)

**Judgment**:
```
try:
    top_n = get_drop_topn(sag_id, size=10)
except SAG_QUERY_TOPN_ERROR:
    return SKIPPED, "DropTopN not supported in this region (edge/special region)"

drop_rate = calculate_drop_rate(top_n)   # aggregated % of dropped packets

if drop_rate < 0.01:                     # < 1%
    return GREEN, f"Packet drop rate {drop_rate*100:.2f}% (healthy)"
elif drop_rate < 0.05:                   # 1% - 5%
    return YELLOW, f"Packet drop rate {drop_rate*100:.2f}% (degraded)"
else:                                    # >= 5%
    return RED, f"Packet drop rate {drop_rate*100:.2f}% (severe loss)"
```

**Availability notes**:
- Returns real data in major regions (cn-shanghai, cn-hangzhou, ap-southeast-1, etc.)
- May return `SAG_QUERY_TOPN_ERROR` in some edge regions (e.g. cn-zhangjiakou-spe)
- On error, do NOT abort the inspection — mark this item as `skipped due to region unsupported` and continue

**Recommended Actions (Yellow/Red)**:
- Correlate with Rule 2 (VPN tunnel) and Rule 6 (4G link) — packet drop is often downstream of a degraded underlay link
- Check WAN interface error counters via `describe-sag-wan-list`
- If drops cluster on a specific destination CIDR, review ACL/routing for that target

---

## Rule 6: 4G Link Status

**API**: `describe-sag-wan-4g`

**Judgment**:
```
if Status == "connected" and Strength >= -85:
    return GREEN, f"4G connected, signal {Strength}dBm (good)"
elif Status == "connected" and Strength >= -100:
    return YELLOW, f"4G connected, signal {Strength}dBm (weak)"
elif Status == "connected" and Strength < -100:
    return RED, f"4G connected but signal very weak {Strength}dBm"
elif Status == "disconnected" or IP is empty:
    return RED, "4G disconnected - check SIM card"
else:
    return YELLOW, f"4G status: {Status}"
```

**Signal Strength Reference (dBm)**:
- Excellent: > -65
- Good: -65 to -85
- Fair: -85 to -100
- Poor: < -100

**Why these thresholds**: Based on 3GPP LTE reference signal received power (RSRP) standards. -85 dBm is the typical edge-of-cell threshold where modulation drops to lower order (slower speeds). -100 dBm approaches the sensitivity limit of most 4G modules in SAG devices, causing frequent disconnections and high retransmission rates.

**Recommended Actions (Red)**:
- Check SIM card insertion and activation
- Verify SIM card has data balance
- Check antenna connection
- Try different SIM card slot if available
- Consider external antenna for weak signal areas

---

## Rule 7: CCN/CEN Binding Completeness

**API**: `describe-cloud-connect-networks` + `describe-grant-sag-rules`

**Judgment**:
```
sag_has_ccn = (AssociatedCcnId is not None and not empty)
ccn_has_cen = (CCN.AssociatedCenId is not None and not empty)
has_grant_rules = (GrantRules is not empty)

if sag_has_ccn and ccn_has_cen and has_grant_rules:
    return GREEN, "Full chain: SAG -> CCN -> CEN (authorized)"
elif sag_has_ccn and ccn_has_cen and not has_grant_rules:
    return YELLOW, "CCN bound to CEN but no cross-account authorization found"
elif sag_has_ccn and not ccn_has_cen:
    return YELLOW, "SAG bound to CCN but CCN not attached to CEN"
else:
    return RED, "SAG not bound to any CCN - cloud connectivity not established"
```

**Chain Verification**:
```
SAG -> CCN -> CEN -> VPC (target)
 |        |       |
 bind     attach  route propagation
```

**Why this check matters**: SAG cloud connectivity requires a complete three-hop chain (SAG->CCN->CEN->VPC). From 701 historical support tickets, 11.4% of issues were caused by incomplete bindings — users often bind SAG to CCN but forget to authorize CCN to CEN, or miss the cross-account grant step. Checking the full chain proactively prevents these common misconfigurations.

**Recommended Actions**:
- Red: bindsmartaccessgateway to a CCN first
- Yellow (no CEN): Attach CCN to a CEN instance
- Yellow (no grant): For cross-account, run GrantSagInstanceToCcn

---

## Rule 8: Route Health

**API**: `describe-sag-route-list`

**Judgment**:
```
routes = get_route_list()
has_default = any(r.DestinationCidr == "0.0.0.0/0" for r in routes)
route_count = len(routes)
has_conflicts = check_overlapping_cidrs(routes)

if route_count > 0 and not has_conflicts:
    return GREEN, f"{route_count} routes, no conflicts"
elif route_count == 0:
    return RED, "No routes configured - traffic cannot be forwarded"
elif has_conflicts:
    return YELLOW, f"{route_count} routes but overlapping CIDRs detected"
else:
    return GREEN, f"{route_count} routes configured"
```

**Conflict Detection Logic**:
- Two routes overlap if their destination CIDRs intersect
- Longest prefix match applies, but overlaps may indicate misconfiguration
- Multiple default routes to different next-hops indicate potential black hole

---

## Rule 9: ACL/QoS Sanity

**API**: `describe-acls` + ACL rule queries

**Judgment**:
```
acl_bound = (ACL.SagCount > 0)
rules = get_acl_rules(acl_id)
has_deny_all = any(r.Policy == "drop" and r.DestCidr == "0.0.0.0/0" for r in rules)
has_allow_before_deny = check_allow_rules_before_deny_all(rules)

if not acl_bound:
    return GREEN, "No ACL bound (all traffic allowed by default)"
elif acl_bound and has_deny_all and has_allow_before_deny:
    return GREEN, "ACL configured with whitelist pattern"
elif acl_bound and has_deny_all and not has_allow_before_deny:
    return RED, "ACL has deny-all but no allow rules - all traffic blocked"
elif acl_bound and not has_deny_all:
    return YELLOW, "ACL bound but no deny-all fallback - may not be effective"
else:
    return GREEN, "ACL rules appear reasonable"
```

---

## Rule 10: Flow Logs

**API**: `describe-flow-logs`

**Judgment**:
```
flow_logs = get_flow_logs(sag_id)
active_logs = [fl for fl in flow_logs if fl.Status == "Active"]

if len(active_logs) > 0:
    return GREEN, f"Flow logs enabled ({len(active_logs)} active)"
else:
    return YELLOW, "Flow logs not enabled - troubleshooting visibility limited"
```

**Recommended Actions (Yellow)**:
- Enable flow logs for better traffic visibility
- Configure SLS project and logstore
- Useful for: bandwidth analysis, security audit, troubleshooting connectivity

---

## Composite Scoring

When running full inspection, calculate overall health score:

```python
def calculate_overall_status(results):
    red_count = sum(1 for r in results if r.level == RED)
    yellow_count = sum(1 for r in results if r.level == YELLOW)
    
    if red_count > 0:
        return "CRITICAL", f"{red_count} critical issues require immediate attention"
    elif yellow_count >= 3:
        return "ATTENTION NEEDED", f"{yellow_count} items need attention"
    elif yellow_count > 0:
        return "MOSTLY HEALTHY", f"{yellow_count} minor items to review"
    else:
        return "HEALTHY", "All inspection items passed"
```

## Priority of Remediation

When multiple issues found, fix in this order:
1. Device offline (Rule 1) - nothing works without connectivity
2. VPN tunnel down (Rule 2) - cloud access requires tunnel
3. Instance expired (Rule 4) - service may be suspended
4. CCN/CEN not bound (Rule 7) - routing chain broken
5. Route issues (Rule 8) - traffic cannot reach destination
6. Packet drop severe (Rule 5) - underlay link degraded
7. 4G link issues (Rule 6) - backup link degradation
8. Other items - operational improvements
