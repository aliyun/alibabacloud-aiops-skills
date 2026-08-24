# Module 4: Operational Timeline Report

## Purpose
Reconstruct a chronological timeline of all malicious operations, synthesize findings into a structured conclusion, and provide prioritized remediation recommendations.

## Report Structure

### Section 1: Executive Summary (Conclusion)

The conclusion is generated in English with six structured sub-sections (I through VI).

#### Conclusion Template (English)

```
I. Incident Overview
The AccessKey <AK_ID> belonging to <resource_type> <resource_name> is suspected to have been leaked.
This AK belongs to account <account_UID/name>, currently in <Active/Deleted/Disabled> status,
created on <createTime>, <has been deleted/has not been deleted>.
Alibaba Cloud Security Center <did/did not> issue an "AccessKey Abnormal Invocation" alert at <alert_time>.
AK ban status <was/was not> inferred from ActionTrail error codes.

II. Intrusion Path & Anomalous Characteristics
The AK was used to invoke Alibaba Cloud OpenAPIs from the following abnormal IP addresses:
- <IP1> (<geolocation>)
- <IP2> (<geolocation>)

Key timeline:
<time1>: First observed <Service:EventName> invocation from IP <IP>;
<time2>: Rapid succession of <Service:EventName> calls, <action details>;
<time3>: Alibaba Cloud risk control triggered <alert_type> alert.

Anomalous characteristics:
1. Source IPs are foreign / non-business / cloud-hosted;
2. Invocation behavior rapidly escalates from low-frequency Describe probes to high-frequency Create/Run operations;
3. Operations concentrated within a short time window, consistent with automated attack tooling.

III. Impact Actions Detail
Through ActionTrail audit, the AK generated <N> event records within <time_window>,
of which <N> were high-risk operations across <N> services:

[RAM]
- Created sub-account <sub-account-name> (<time>)
- Granted <policy-name> permission to sub-account <sub-account-name> (<time>)

[ECS]
- Invoked RunInstances to create <N> ECS instances (<time>)
- Created security group and opened <port> (<time>)

[Other Services]
- <Service:EventName> (<time>, <risk_level>)

IV. Impact Scope
| Impact Dimension | Details |
|---------|---------|
| Account Security | <N> sub-accounts created, <N> permission policies modified |
| Resource Security | <N> ECS instances, <N> security groups created |
| Billing Security | Abnormal instances <incurred $amount/no charges>, ongoing billing risk exists |
| Data Security | RDS/DMS data access <detected/not detected> |
| DNS Security | DNS record tampering <detected/not detected> |

V. Risk Analysis
1. Account Level: Leaked AK has sub-account creation and authorization capability; attacker can maintain long-term access;
2. Resource Level: <N> ECS instances created, potentially used for mining, C2, DDoS, or other malicious purposes;
3. Billing Level: Unauthorized resources will incur uncontrollable cloud costs;
4. Data Level: If sub-accounts were granted broad permissions, data exfiltration or tampering risk exists;
5. Compliance Level: AK leak incident must be reported and handled per security incident procedures.

VI. Remediation Recommendations (Priority-Ordered)

[P0 — Immediate (Within 30 Minutes)]
1. Disable and delete the leaked AK <AK-ID>;
2. Delete attacker-created sub-accounts <usernames> and all their AKs and attached policies;
3. [If CloudSSO] Delete attacker-created Access Configurations and revoke associated Access Assignments;
4. [If ECS] Terminate attacker-created <N> ECS instances and associated EIPs/security groups.

[P1 — Urgent (Within 2 Hours)]
5. Rotate all remaining AccessKeys on this account;
6. [If DNS] Restore deleted/modified DNS records, compare current records against known-good baseline;
7. [If notification tampering] Re-enable disabled security alert subscriptions;
8. Tighten RAM permissions to least-privilege principle.

[P2 — Important Hardening (Within 24 Hours)]
9. Investigate AK leakage source (code repositories, CI/CD configs, third-party platforms) and remediate;
10. Enable mandatory MFA policy for all RAM users;
11. If leaked AK belongs to root account, migrate to RAM user AK and delete root AK;
12. Implement human/machine separation: console users and API users managed separately.

[P3 — Long-term Governance (Within 1 Week)]
13. Migrate to credential-free architecture (ECS Instance Role / RRSA / KMS Secrets Manager);
14. Clean up idle AKs and idle RAM users;
15. Enable ActionTrail real-time delivery to SLS + CloudMonitor alerts;
16. Enable RAM Cloud Governance with all detection items active.

See [module5_remediation_best_practices.md](module5_remediation_best_practices.md) for details.
```

### Section 2: Operational Timeline

Chronological table of all detected events, sorted by `eventTime`:

| EventTime (UTC) | Service | EventName | Risk | SourceIP | UserAgent | User |
|-----------------|---------|-----------|------|----------|-----------|------|
| 2026-01-04 02:55:42 | Location | DescribeEndpoints | LOW | 140.213.130.243 | ... | guoyu |
| 2026-01-04 02:56:00 | ECS | RunInstances | HIGH | 140.213.130.243 | ... | guoyu |

### Section 3: Event Summary Statistics

| Metric | Value |
|--------|-------|
| Total Events | 42 |
| High Risk Events | 5 |
| Medium Risk Events | 8 |
| Services with Activity | 3 |
| Sub-Accounts Created | 1 |
| Abnormal Source IPs | 2 |

### Section 4: Risk Assessment

| Risk Item | Severity | Description |
|-----------|----------|-------------|
| Unauthorized resource creation | HIGH | ECS instances created without authorization |
| Financial loss | MEDIUM | Billing incurred by unauthorized instances |
| Data exfiltration | MEDIUM | Potential data access via DMS / RDS |
| Privilege escalation | HIGH | Admin policies attached to rogue sub-accounts |
| Malicious use | HIGH | Instances may be used for further attacks |

### Section 5: Recommendations

| Priority | Action | Owner |
|----------|--------|-------|
| CRITICAL | Disable leaked AK and rotate all credentials | Security Team |
| HIGH | Terminate unauthorized ECS instances | Cloud Ops |
| HIGH | Remove rogue RAM users/roles/policies | IAM Admin |
| HIGH | Review and revert DNS changes if any | Network Team |
| MEDIUM | Audit SMS sending logs for abuse | Security Team |
| MEDIUM | Enable CloudMonitor + ActionTrail alerts | Security Team |
| LOW | Document incident and update AK rotation policy | Security Team |

## Reference Documents

- AccessKey Restrictive Protection: https://www.alibabacloud.com/help/en/ram/user-guide/accesskey-restrictive-protection-description
- AccessKey Leakage Solution: https://www.alibabacloud.com/help/en/ram/user-guide/solution-to-accesskey-leakage
- **Detailed Remediation Best Practices**: See [module5_remediation_best_practices.md](module5_remediation_best_practices.md) for P0-P3 priority framework with official documentation sources

## Output Formats

### Markdown (default)
Human-readable report with tables, timeline, and structured sections suitable for incident tickets or documentation.

### JSON
Machine-readable structured report for downstream automation and SIEM integration.
