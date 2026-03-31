# OpenClaw Security Operations Workflow

The complete 7-step OpenClaw security operations workflow.

---

## Workflow Overview

```
Step 1: Query Instances → Step 2: Check Security → Step 3: Deep Dive
         ↓                        ↓                       ↓
    Asset Inventory           Risk Overview          Detailed Analysis
                                                           ↓
Step 7: Daily Report ← Step 6: Recommend ←        Step 4: Remediate
                                                           ↓
                                                   Step 5: Security Guardrail
```

---

## Step 1: Query OpenClaw Instances

**Goal**: Understand all OpenClaw deployments in the environment.

```bash
python -m scripts.query_openclaw_instances \
    --name-pattern openclaw --biz sca_ai
```

**Key focus areas**:
- Number and distribution of instances
- Version numbers of each instance (are there outdated versions?)
- Whether deployment paths are standardized
- Collect the UUID list for filtering in subsequent steps

**Output**: `output/openclaw_instances.json` + `.md`

---

## Step 2: Security Checks (Three Dimensions)

### 2.1 Vulnerability Check

```bash
python -m scripts.check_openclaw_vulns \
    --type emg --dealed n
```

Key focus areas:
- `emg` (emergency vulnerabilities): Usually high severity, must be addressed first
- `sca` (SCA vulnerabilities): Component-level vulnerabilities
- Check vulnerabilities with `Necessity=asap`

### 2.2 Baseline Check

```bash
python -m scripts.check_openclaw_baseline \
    --risk-id 320
```

Key focus areas:
- Weak password risks
- Insecure configuration items
- Unauthorized access risks
- OpenClaw listening on 0.0.0.0

### 2.3 Alert Check

```bash
python -m scripts.check_openclaw_alerts \
    --dealed N
```

Key focus areas:
- `serious` level alerts (handle urgently)
- Abnormal processes, abnormal logins
- Malicious Skills

---

## Step 3: Deep Analysis

Based on issues found in Step 2, perform targeted in-depth analysis.

### Query by Specific Host

```bash
# Query vulnerabilities for a specific host
python -m scripts.check_openclaw_vulns \
    --uuids <UUID> --type emg

# Query alerts for a specific host
python -m scripts.check_openclaw_alerts \
    --uuids <UUID>
```

### Correlation Analysis Approach

1. **Vulnerability → Alert**: A host with unpatched vulnerabilities + abnormal alerts = possible exploitation
2. **Baseline → Vulnerability**: Weak password + public exposure = high risk
3. **Alert → Instance**: What OpenClaw components are running on the alerted host

---

## Step 4: Remediation and Hardening

Execute remediation based on the analysis results. Refer to `remediation_guide.md`.

### Priority Ordering

1. **P0 Critical**: `serious` level alerts + emergency vulnerabilities
2. **P1 High**: Baseline non-compliance (weak passwords, unauthorized access)
3. **P2 Medium**: Other unpatched vulnerabilities
4. **P3 Low**: Informational alerts

### Remediation Methods

- Vulnerability remediation: One-click fix via Security Center or manual upgrade
- Baseline hardening: Modify configurations, strengthen password policies
- Alert handling: Isolate malicious processes, whitelist legitimate behavior
- Component upgrade: Upgrade OpenClaw to a secure version

---

## Step 5: Install Security Guardrail

Install the Alibaba Cloud security guardrail plugin to add continuous protection capabilities to OpenClaw instances.

```bash
python -m scripts.install_security_guardrail
```

### Verification

After installation, use the following command to verify the plugin is running correctly:

```bash
python -m scripts.query_guardrail_status \
    --instance-ids <instance-id1>,<instance-id2>
```

**Output**: `output/guardrail_status_<timestamp>.json` + `.md`

Check whether the `status` field is `running` and whether the version matches the installation expectation.

---

## Step 6: Security Product Recommendations

Recommend Alibaba Cloud security products for hardening based on the environment's risk profile.

See the product recommendation section in `remediation_guide.md`.

---

## Step 7: Generate Security Daily Report

```bash
python -m scripts.generate_security_report
```

**Daily report content**:
- Instance overview
- Vulnerability statistics (high/medium/low)
- Baseline compliance status
- Alert handling status
- Security recommendations
- Today's operations

**Output**: `output/security_report_YYYYMMDD.md` + `.json`

---

## Routine Inspection Recommendations

| Frequency | Content |
|-----------|---------|
| Daily | Run the security daily report, check for new alerts |
| Weekly | Full vulnerability scan, baseline check |
| Monthly | Security posture assessment, product configuration audit |
| Quarterly | Security policy review, permission audit |
