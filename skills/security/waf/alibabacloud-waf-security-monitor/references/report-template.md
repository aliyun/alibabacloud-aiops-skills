# WAF Inspection Report Template

> **Mandatory**: Every inspection report MUST strictly follow this template structure. No sections may be omitted.

---

## Normal Scenario Template

```markdown
# WAF Security Inspection Report

## Inspection Summary

| Item | Value |
|------|-------|
| Inspection Time | <current time> |
| Base Period | <base_start> ~ <base_end> |
| Compare Period | <compare_start> ~ <compare_end> |
| Comparison Mode | <day-over-day / hour-over-hour / 30-min / custom> |
| WAF Instance | <instance ID> <version> <region> |

---

## Asset Inventory

| Asset Type | Count | Details |
|-----------|-------|---------|
| CNAME Domains | N | <domain list> |
| Cloud Product Access | N | ALB: N, ECS: N, CLB: N |
| SSL Certificates | N | Expiring soon (<30 days): M |

### Detailed Asset List

#### CNAME Domains
| Domain | Status | Protection | CNAME |
|--------|--------|-----------|-------|
| <...> | Normal/Abnormal | Protected/Unprotected | <CNAME value> |

#### Cloud Product Access
| Product Type | Instance ID | Instance Name | Region | Status |
|-------------|-------------|---------------|--------|--------|
| ALB/ECS/CLB | <...> | <...> | <...> | Normal |

> **Cross-Region Check**: If `[REGION_MISMATCH_SUMMARY]` exists in the log (output by `scripts/detect_region_mismatch.py`), add a "Cross-Region Resource Risk" section immediately after this table (see template below).

#### SSL Certificates
| Certificate Name | Bound Domain | Expiry Date | Days Remaining | Status |
|-----------------|-------------|-------------|----------------|--------|
| <...> | <...> | <YYYY-MM-DD> | <N> days | Normal / Expiring Soon / Critical |

---

## Inspection Results

### 1. Attack Event Statistics (auto-query template IDs)

**Protection Scenario**: BOT Management (bot_manager)

#### By Protection Scenario
| Scenario Type | Rule Count |
|--------------|------------|
| human_machine_challenge | N |
| normal_intelligence | N |
| suspicious_idc | N |
| web_malicious_crawler | N |
| ... | ... |
| **Total** | **N** |

#### By Rule Action
| Action Type | Rule Count | Description |
|------------|------------|-------------|
| monitor | N | Observe mode |
| captcha | N | CAPTCHA challenge |
| block | N | Block |
| bypass | N | Allow |
| js | N | JS challenge |

#### By Rule Status
| Status Code | Rule Count | Meaning |
|------------|------------|---------|
| 0 | N | Allow |
| 1 | N | Block |

**Block Rate**: X% (N/N)

#### API Security Events
| Base Period | Compare Period | Change Rate |
|-----------|---------------|-------------|
| N events | N events | No change / Increased / Decreased |

---

### 2. Traffic Analysis

| Metric | Base Period Peak | Compare Period Peak | Change Rate |
|--------|-----------------|--------------------|-----------  |
| Request QPS | N | N | <+/-X% or No data> |
| Bandwidth (Mbps) | N | N | <+/-X% or No data> |

---

### 3. HTTP Status Code Analysis (Period-over-Period)

#### Frontend Status Codes (WAF Response)
| Status Code Type | Base Period | Compare Period | Change Rate |
|-----------------|-----------|---------------|-------------|
| 4xx Errors | N | N | <+/-X% or No data> |
| 5xx Errors | N | N | <+/-X% or No data> |

#### Upstream Status Codes (Origin Response)
| Status Code Type | Base Period | Compare Period | Change Rate |
|-----------------|-----------|---------------|-------------|
| 4xx Errors | N | N | <+/-X% or No data> |
| 5xx Errors | N | N | <+/-X% or No data> |

**Anomaly Thresholds**:
- 4xx/5xx change rate +/-50% ~ +/-100% --> Attention
- 4xx/5xx change rate > +/-100% --> Anomaly

---

### 4. Top Protected Objects (by Request Count)

| Rank | Domain/Resource | Requests | Blocked | Block Rate |
|------|----------------|----------|---------|------------|
| 1 | <...> | N | N | X% |
| 2 | <...> | N | N | X% |
| 3 | <...> | N | N | X% |

---

### 5. Protection Status

| Check Item | Status | Details |
|-----------|--------|---------|
| Protection Switch | Normal / Paused | PauseStatus=0/1 |
| Defense Templates | N templates | <template list summary> |
| Current Alarms | N alarms | <alarm summary> |
| DDoS Attack | Yes/No | - |
| Major Protection Black IPs | N IPs | <IP list summary> |

---

## Conclusion: No Anomalies Found

**All metrics normal** during the past <time range>:
- API Security Events: 0
- Protection Status: Normal
- Certificates: No expiry risk
- No current alarms
- BOT protection rules configured properly

---

## Data Notes

| Module | Data Status | Reason |
|--------|-----------|--------|
| Traffic time-series | Has data / No data | <explanation> |
| Top Resources/URLs | Has data / No data | <explanation> |
| Attack event statistics | Partially available | Only bot_manager scenario template supports statistics query |
```

---

## Anomaly Scenario Template

When anomalies are found, replace the Conclusion section with:

```markdown
## Conclusion: <N> Anomalies Found

### Anomaly Summary
| Module | Metric | Anomaly Type | Details |
|--------|--------|-------------|---------|
| <module> | <metric name> | Anomaly / Attention | <change rate / event details> |

### Remediation Recommendations
1. <specific actionable recommendation>
2. <...>
```

---

## Certificate Expiry Risk Template

When certificates are expiring soon, add a dedicated section:

```markdown
## Certificate Expiry Risk

| Certificate Name | Bound Domain | Expiry Date | Days Remaining | Urgency |
|-----------------|-------------|-------------|----------------|---------|
| <...> | <...> | <...> | <N> days | Critical / Attention |

### Remediation Recommendations
1. Contact certificate administrator to renew immediately
2. If using Alibaba Cloud SSL Certificate Service, one-click renewal is available in the console
3. After renewal, re-upload the certificate to WAF
```

---

## Cross-Region Resource Risk Template

When `[REGION_MISMATCH_SUMMARY]` is present in the log, add this section under Asset Inventory:

```markdown
### Cross-Region Resource Risk

> **Risk**: The following cloud resources are connected to a WAF instance in a different region.
> This may cause increased latency, routing anomalies, or protection policy mismatches.
> Confirm whether this is intentional (e.g. Global Accelerator scenarios). If not, reconfigure the access.

| WAF Instance Region | Resource Type | Resource ID | Resource Region | Recommendation |
|---------------------|---------------|-------------|-----------------|----------------|
| ap-southeast-1 | ecs | i-xxx | cn-hangzhou | Verify intent; reconfigure if unintentional |
| <waf_region> | <resource_type> | <resource_id> | <resource_region> | Verify intent |
```
