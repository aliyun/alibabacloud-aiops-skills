---
name: alibabacloud-waf-cname-config-export
description: |
  Batch export Alibaba Cloud WAF 3.0 CNAME-based domain configuration to Excel.
  Use when the user needs "export WAF domain config", "WAF onboarding checklist", "WAF domain audit", or "WAF config inspection".
---

# Alibaba Cloud WAF 3.0 CNAME Domain Configuration Batch Export

Batch query all CNAME-based domain configurations under WAF 3.0 instances and generate a structured Excel file for configuration audit, delivery documentation, and inspection reports.

**Architecture**: `WAF 3.0 Instance` → `CNAME Domains (DescribeDomains)` → `Domain Config: Listen + Redirect + Cert (DescribeDomainDetail)` → `Excel Export`

### Site and Instance Types

| Dimension | Chinese Mainland Instance | Non-Chinese Mainland Instance |
|-----------|--------------------------|-------------------------------|
| RegionId | `cn-hangzhou` | `ap-southeast-1` |
| Endpoint | `wafopenapi.cn-hangzhou.aliyuncs.com` | `wafopenapi.ap-southeast-1.aliyuncs.com` |

> A single account can have both instance types. Export must query both RegionIds and merge results.

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version` to verify >= 3.3.3. If not installed, see [references/cli-installation-guide.md](references/cli-installation-guide.md).

**Pre-check: Aliyun CLI plugin update required**

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

Python dependency (pinned version for reproducibility):

```bash
pip install openpyxl==3.1.5
```

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session**
> 3. Return and re-run after `aliyun configure list` shows a valid profile

> International site users must configure a separate profile (e.g., `aliyun configure --profile intl`). Chinese mainland and International site AKs are NOT interchangeable.

## RAM Policy

| Action | Description |
|--------|-------------|
| `yundun-waf:DescribeInstance` | Query WAF instance info |
| `yundun-waf:DescribeDomains` | Query domain list |
| `yundun-waf:DescribeDomainDetail` | Query domain detailed config |

Recommended: attach system policy `AliyunYundunWAFReadOnlyAccess`.

Full RAM policy list: see [references/ram-policies.md](references/ram-policies.md)

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default Value |
|-----------|-------------------|-------------|---------------|
| RegionId | Auto | Query both regions (cn-hangzhou + ap-southeast-1) | Both |
| InstanceId | Auto | Auto-discovered via DescribeInstance | — |
| CLI Profile | Optional | Uses default profile; add `--profile <name>` if user specifies | default |
| Output File | Auto | Fixed filename with timestamp | waf_cname_config_export_YYYYMMDD_HHMMSS.xlsx |

## Core Workflow

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-cname-config-export"
> ```

### Step 1: Auto-discover WAF Instances

> **[MUST] Query BOTH regions unconditionally.** Even if the user states they "only have domestic" / "only have overseas" / "only use one region", you MUST still execute both commands below. User assertions about instance distribution are NOT a reason to skip either region. Discovery is the only authoritative source.

```bash
aliyun waf-openapi describe-instance --region cn-hangzhou
aliyun waf-openapi describe-instance --region ap-southeast-1
```

If the response contains a non-empty `InstanceId`, the instance exists. International site users add `--profile intl`.

### Step 2: Batch Query Domain List

```bash
aliyun waf-openapi describe-domains \
  --region cn-hangzhou \
  --instance-id <InstanceId> \
  --page-number 1 \
  --page-size 50
```

Pagination: loop PageNumber when `TotalCount` > 50.

### Step 3: Query Detailed Config for Each Domain

```bash
aliyun waf-openapi describe-domain-detail \
  --region cn-hangzhou \
  --instance-id <InstanceId> \
  --domain <DomainName>
```

Returns Listen (HttpPorts/HttpsPorts/TLSVersion/CipherSuite/Http2Enabled/CertId) and Redirect (BackendList/BackupBackends/Loadbalance/SniEnabled/SniHost/Timeouts).

> **[MUST] Always call DescribeDomainDetail at least once per discovered instance.** Iterate the domain list from Step 2 and call this API for every domain. If Step 2 returns an empty list (`TotalCount == 0`) for a given instance, you MUST still issue **one** `describe-domain-detail` call against that instance using a placeholder domain (e.g. `--domain none`) to verify API reachability and permissions, then record "no domains" and continue. Do NOT skip this step based on an empty list.

### Step 4: Generate Excel Export

One sheet per region ("Chinese Mainland" / "Non-Chinese Mainland"). 18 columns: Domain, CNAME, Status, HTTP Ports, HTTPS Ports, Backends, Backup Backends, Load Balancing, TLS Version, HTTP/2, Cert ID, SNI, SNI Host, Connect Timeout(s), Read Timeout(s), Write Timeout(s), Force HTTP Backend, Resource Group.

**[MUST] Use the bundled script — this is the ONLY allowed execution path**:

```bash
python scripts/alibabacloud_waf_cname_config_export.py
```

> **Do NOT** rewrite, inline, or reimplement the export logic in your own Python code. The bundled script encapsulates the correct 18-column schema, per-region sheet layout, pagination, and field-name conventions. If the script fails, diagnose the failure (missing `openpyxl==3.1.5`, credential issues, etc.) and fix the root cause — do NOT fall back to ad-hoc code.

> **Field name notes**: Load balancing is `Redirect.Loadbalance` (not `LoadBalanceType`). Backend IP list is `Redirect.BackendList` (string array). Cert ID is at `Listen.CertId`.

### Step 5: Disable AI-Mode

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first.
> ```bash
> aliyun configure ai-mode disable
> ```

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

1. Excel file opens with one sheet per region
2. Each sheet has 18 column headers and data intact
3. Domain count per sheet matches WAF console display
4. Spot-check 2-3 domains against console for CNAME and backend config accuracy

## Cleanup

No resources created — no cleanup needed.

## Best Practices

1. Always query both regions to avoid missing dual-instance scenarios
2. Set PageSize to 50 (maximum) to reduce request count
3. Add at least 200ms delay between requests (`time.sleep(0.2)`) to prevent throttling
4. Non-CNAME domains may have empty CNAME fields; label them accordingly
5. Chinese mainland and International site CLI profiles must be configured separately

## References

| Topic | Link |
|-------|------|
| CLI Commands | See [references/related-commands.md](references/related-commands.md) |
| RAM Policies | See [references/ram-policies.md](references/ram-policies.md) |
| Verification Method | See [references/verification-method.md](references/verification-method.md) |
| Acceptance Criteria | See [references/acceptance-criteria.md](references/acceptance-criteria.md) |
| CLI Installation | See [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| DescribeDomains API | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/api-waf-openapi-2021-10-01-describedomains |
| DescribeDomainDetail API | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/api-waf-openapi-2021-10-01-describedomaindetail |
| DescribeInstance API | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/api-waf-openapi-2021-10-01-describeinstance |
