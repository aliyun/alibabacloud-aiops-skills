---
name: alibabacloud-waf-protectionconfig-backup
description: |
  Export and backup Alibaba Cloud WAF protection configurations for WAF 3.0 and WAF 2.0 instances.
  Supports both China mainland (cn-hangzhou) and international (ap-southeast-1) regions.
  Output format: Excel workbooks (.xlsx) with each data module as a separate sheet.
  Triggers: "WAF backup", "WAF config export", "WAF config backup", "protection config backup"
---

# WAF Protection Config Backup

Export and backup all WAF protection configurations as Excel workbooks (.xlsx) for disaster recovery, auditing, configuration migration, or compliance review. Each data module is saved as a separate sheet within the workbook.

## Architecture

```
Alibaba Cloud WAF Instance
├── WAF 3.0 (API 2021-10-01)
│   ├── Defense Resources
│   ├── Defense Resource Groups
│   ├── Defense Templates → Rules → Resource Bindings
│   │   └── 20 DefenseScene types (waf_group, cc, custom_acl, ip_blacklist, ...)
│   ├── Major Protection Black IPs
│   └── Address Books
│
└── WAF 2.0 (API 2019-09-10)
    └── Per-Domain Protection Rules
        └── 16 DefenseType types (ac_custom, whitelist, tamperproof, ...)
            ├── Rules / Status / Mode
            └── Domain Rule Group

Regions: cn-hangzhou (China) | ap-southeast-1 (International)
Output: waf3-{region}.xlsx (8 sheets) | waf2-{region}.xlsx (5 sheets)
```

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for detailed instructions.

**Pre-check: Aliyun CLI plugin update required**

> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Pre-check: Python openpyxl library required**

> Excel (.xlsx) output requires the `openpyxl` Python library.
> ```bash
> pip3 install openpyxl
> ```

## Environment Variables

No environment variables are required. All parameters are provided via CLI flags or confirmed interactively.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

This skill requires **read-only** permissions for WAF APIs. See [references/ram-policies.md](references/ram-policies.md) for the full IAM policy JSON.

| Action | WAF Version | Description |
|--------|------------|-------------|
| `waf:DescribeInstance` | 3.0 | Query instance info |
| `waf:DescribeDefenseResources` | 3.0 | List defense resources |
| `waf:DescribeDefenseResourceGroups` | 3.0 | List resource groups |
| `waf:DescribeDefenseTemplates` | 3.0 | List defense templates |
| `waf:DescribeDefenseRules` | 3.0 | List defense rules |
| `waf:DescribeTemplateResources` | 3.0 | List template-resource bindings |
| `waf:DescribeMajorProtectionBlackIps` | 3.0 | List major protection black IPs |
| `waf:DescribeAddresses` | 3.0 | List address book entries |
| `waf:DescribeInstanceInfo` | 2.0 | Query instance info |
| `waf:DescribeDomainNames` | 2.0 | List domains |
| `waf:DescribeProtectionModuleRules` | 2.0 | List protection rules |
| `waf:DescribeProtectionModuleStatus` | 2.0 | Query module status |
| `waf:DescribeProtectionModuleMode` | 2.0 | Query module mode |
| `waf:DescribeDomainRuleGroup` | 2.0 | Query domain rule group |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun waf-openapi describe-instance --region cn-hangzhou --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `REGIONS` | Optional | Regions to scan | `cn-hangzhou,ap-southeast-1` |
| `BACKUP_DIR` | Optional | Output directory path | `./waf-backup-{YYYYMMDD-HHmmss}` |
| `WAF_VERSION` | Optional | Target WAF version: `3.0`, `2.0`, or `auto` | `auto` |

## Core Workflow

### Phase 1: Initialize

```bash
BACKUP_DIR="./waf-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
```

### Phase 2: Detect WAF Version (per region)

For each region in `[cn-hangzhou, ap-southeast-1]`:

**Try WAF 3.0:**
```bash
aliyun waf-openapi describe-instance \
  --region {region} \
  --biz-region-id {region} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```
If response contains a valid `InstanceId` → WAF 3.0 detected. Parse response and write to "instance" sheet of `{BACKUP_DIR}/waf3-{region}.xlsx`.

**Try WAF 2.0:**
```bash
aliyun waf-openapi describe-instance-info \
  --api-version 2019-09-10 \
  --region {region} \
  --biz-region-id {region} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```
If response contains valid instance info → WAF 2.0 detected. Parse response and write to "instance-info" sheet of `{BACKUP_DIR}/waf2-{region}.xlsx`.

If neither returns results, skip this region.

### Phase 3: WAF 3.0 Backup

For each region with WAF 3.0 detected, follow the detailed steps in [references/waf3-backup-workflow.md](references/waf3-backup-workflow.md):

All data is written to `{BACKUP_DIR}/waf3-{region}.xlsx` with each module as a separate sheet:

1. **Backup Defense Resources** — `describe-defense-resources` with `--pager` → sheet "defense-resources"
2. **Backup Defense Resource Groups** — `describe-defense-resource-groups` with `--pager` → sheet "defense-resource-groups"
3. **Backup Defense Templates & Rules** — Iterate all 20 DefenseScene values:
   - For each scene: list templates → for each template: get rules + resource bindings
   - Aggregate all templates into sheet "defense-templates", all rules into sheet "defense-rules", all bindings into sheet "template-resource-bindings"
   - See [references/defense-scene-values.md](references/defense-scene-values.md) for the full enum list
4. **Backup Major Protection Black IPs** — `describe-major-protection-black-ips` with `--pager` → sheet "major-protection-black-ips"
5. **Backup Address Books** — `describe-addresses` with `--pager` → sheet "addresses"

### Phase 4: WAF 2.0 Backup

For each region with WAF 2.0 detected, follow the detailed steps in [references/waf2-backup-workflow.md](references/waf2-backup-workflow.md):

All data is written to `{BACKUP_DIR}/waf2-{region}.xlsx` with each module as a separate sheet:

1. **List Domains** — `describe-domain-names --api-version 2019-09-10` → sheet "domain-names"
2. **Per-Domain Backup** — For each domain, iterate all 16 DefenseType values:
   - `describe-protection-module-rules` → append to sheet "protection-rules"
   - `describe-protection-module-status` + `describe-protection-module-mode` → append to sheet "protection-status"
   - See [references/defense-scene-values.md](references/defense-scene-values.md) for the full enum list
3. **Backup Domain Rule Group** — `describe-domain-rule-group` per domain → append to sheet "domain-rule-groups"

> **CRITICAL:** All WAF 2.0 commands MUST include `--api-version 2019-09-10` and `--region {region}`.
> The `--region` flag sets the API endpoint region. Without it, non-China-mainland instances (e.g., ap-southeast-1) will not be found — the API defaults to cn-hangzhou and returns the China mainland instance instead.

### Phase 5: Generate Manifest

Create `{BACKUP_DIR}/manifest.json` containing:
- `backupTime` — ISO 8601 timestamp
- `regions` — object with per-region details (WAF version, instance ID, sheet counts)
- `totalFiles` — total number of backup Excel (.xlsx) files

## Success Verification

1. Verify `manifest.json` exists and is valid JSON
2. Compare Excel file count against `totalFiles` in manifest
3. Spot-check: open `waf3-{region}.xlsx` and verify "defense-resources" sheet has data rows (WAF 3.0), or open `waf2-{region}.xlsx` and verify "domain-names" sheet has data rows (WAF 2.0)
4. Validate all Excel files: `find {BACKUP_DIR} -name "*.xlsx" -exec python3 -c "import openpyxl; openpyxl.load_workbook('{}'); print('OK: {}')" \;`

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

## Cleanup

This is a **read-only** backup skill. No cloud resources are created or modified.

To remove backup files:
```bash
rm -rf {BACKUP_DIR}
```

## Command Tables

See [references/related-commands.md](references/related-commands.md) for the complete CLI command reference.

| Category | Key Commands | Version |
|----------|-------------|---------|
| Instance Detection | `describe-instance`, `describe-instance-info` | 3.0 / 2.0 |
| Defense Resources | `describe-defense-resources`, `describe-defense-resource-groups` | 3.0 |
| Defense Rules | `describe-defense-templates`, `describe-defense-rules`, `describe-template-resources` | 3.0 |
| Major Protection | `describe-major-protection-black-ips` | 3.0 |
| Address Book | `describe-addresses` | 3.0 |
| Domain Rules | `describe-protection-module-rules`, `describe-protection-module-status`, `describe-protection-module-mode` | 2.0 |
| Domain Rule Group | `describe-domain-rule-group` | 2.0 |

## Best Practices

1. Run backups on a regular schedule (daily or weekly) for disaster recovery
2. Store backup files in OSS with versioning enabled for long-term retention
3. Use `auto` version detection to support mixed WAF 2.0/3.0 environments
4. Always scan both `cn-hangzhou` and `ap-southeast-1` to capture all instances
5. Validate backup integrity using `manifest.json` file counts after each run
6. Keep at least 7 days of backup history before pruning old backups
7. Use `--pager` flag to handle large datasets without manual pagination
8. Compress backup directories (`tar -czf`) for archival storage

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [references/ram-policies.md](references/ram-policies.md) | Complete RAM policy JSON |
| [references/waf3-backup-workflow.md](references/waf3-backup-workflow.md) | WAF 3.0 detailed backup workflow |
| [references/waf2-backup-workflow.md](references/waf2-backup-workflow.md) | WAF 2.0 detailed backup workflow |
| [references/defense-scene-values.md](references/defense-scene-values.md) | DefenseScene / DefenseType enum reference |
| [references/related-commands.md](references/related-commands.md) | Complete CLI command reference |
| [references/verification-method.md](references/verification-method.md) | Backup verification procedures |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Testing acceptance criteria |
