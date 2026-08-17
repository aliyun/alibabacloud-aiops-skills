# Diagnostic Report Template

Use this template when generating the final diagnostic report in Step 5.

```markdown
## CDN Diagnostic Report

### Target Information
- URL: {target_url}
- UID: {target_uid}
- Domain: {domain}

### Information Sources (mandatory)
For every parameter above, state where it came from. If any value was auto-filled (not provided by the user), declare it explicitly, e.g.:
- URL: user-provided / auto-extracted from refresh task records
- UID: user-provided / auto-derived via sts:GetCallerIdentity
- Domain: user-provided / auto-discovered via DescribeUserDomains

If all parameters were user-provided, state "All parameters were user-provided".

### Active Probe Results
- Remote probe time: {probe_time}
- DNS: {dns_result} (CNAME: {cname_result})
- HTTPS status code: {https_status}
- Current status: Issue reproducible / Resolved

### Problem Classification
Classification: {matched_categories}
Basis: {classification_reasons}

### Diagnostic Confidence
- Level: High / Medium / Low
- Evidence: Task records + remote cache verification + origin probing

### Evidence Chain

#### 1. Refresh/Preload Task Records
- Query window, task count, status distribution
- Matching tasks: URL, type, status, submission and completion time

#### 2. Cache Verification
- X-Cache / Age / Via headers
- Cache HIT or MISS determination

#### 3. Origin Probe (when applicable)
- Origin response status and headers
- Cache-Control / Last-Modified / ETag analysis

### L1 Engineer Judgment Review

| L1 Engineer Claim | Evidence Verification | Accepted |
|-------------------|----------------------|----------|
| {engineer_claim} | {log_evidence} | Yes/No |

### Root Cause
- **Root cause**: {root_cause}
- **Cache amplification**: {cdn_caching_amplification} (if applicable)

### Recommended Actions

**Immediate fix (CDN side)**: 1. {immediate_fix}
**Prevent recurrence (CDN side)**: 2. {long_term_cdn_config}
**Root cause fix (origin side)**: 3. {root_cause_fix}

### Suggested Customer Reply
{recommended_reply}
```
