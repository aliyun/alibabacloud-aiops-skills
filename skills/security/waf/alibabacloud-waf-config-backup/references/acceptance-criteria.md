# Acceptance Criteria: alibabacloud-waf-config-backup

**Scenario**: WAF 3.0 Full Configuration Backup
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — `waf-openapi`

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-instance --region cn-hangzhou
aliyun waf-openapi describe-domains --region cn-hangzhou --instance-id waf-cn-xxxxx --page-size 50
```

#### ❌ INCORRECT
```bash
# Wrong product name
aliyun waf describe-instance --region cn-hangzhou
aliyun yundun-waf describe-instance --region cn-hangzhou

# Wrong command format (PascalCase instead of kebab-case)
aliyun waf-openapi DescribeInstance --region cn-hangzhou
```

### 2. Commands — verify action exists under waf-openapi

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-instance
aliyun waf-openapi describe-domains
aliyun waf-openapi describe-domain-detail
aliyun waf-openapi describe-cloud-resources
aliyun waf-openapi describe-hybrid-cloud-resources
aliyun waf-openapi describe-defense-templates
aliyun waf-openapi describe-defense-rules
aliyun waf-openapi describe-defense-resources
aliyun waf-openapi describe-defense-resource-groups
# Multi-account topology probing
aliyun sts get-caller-identity
aliyun waf-openapi describe-account-delegated-status
aliyun waf-openapi describe-member-accounts
aliyun waf-openapi describe-defense-resource-owner-uid
```

#### ❌ INCORRECT
```bash
# Non-existent commands
aliyun waf-openapi list-domains
aliyun waf-openapi get-instance
aliyun waf-openapi describe-waf-rules
```

### 3. Parameters — verify parameter names

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-domains --region cn-hangzhou --instance-id waf-cn-xxx --page-size 50 --page-number 1
aliyun waf-openapi describe-defense-rules --region cn-hangzhou --instance-id waf-cn-xxx --rule-type defense --query-args '{"DefenseScene":"custom_acl","TemplateId":12345}'
```

#### ❌ INCORRECT
```bash
# Wrong parameter names
aliyun waf-openapi describe-domains --regionId cn-hangzhou  # should be --region
aliyun waf-openapi describe-domains --instanceId waf-cn-xxx  # should be --instance-id
aliyun waf-openapi describe-defense-rules --defense-scene custom_acl  # defense-scene goes in --query-args
```

### 4. Region Values

#### ✅ CORRECT
```bash
--region cn-hangzhou       # Chinese mainland
--region ap-southeast-1    # International
```

#### ❌ INCORRECT
```bash
--region cn-beijing        # WAF only supports cn-hangzhou for mainland
--region us-east-1         # WAF only supports ap-southeast-1 for international
```

### 5. DefenseScene Values

#### ✅ CORRECT
```
waf_group, custom_acl, cc, ip_blacklist, whitelist,
region_block, antiscan, bot_manager, dlp, tamperproof, custom_response
```

#### ❌ INCORRECT
```
waf, acl, ddos, blacklist, white_list, scan, bot
```

### 6. RuleType Values

#### ✅ CORRECT
```bash
--rule-type defense    # For 10 scene types
--rule-type whitelist  # Only for whitelist scene
```

#### ❌ INCORRECT
```bash
--rule-type waf
--rule-type custom
--rule-type all
```

## Correct Python Script Patterns

### 1. CLI Invocation via subprocess

#### ✅ CORRECT
```python
import subprocess, json

def run_cli(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)

data = run_cli("aliyun waf-openapi describe-instance --region cn-hangzhou")
```

#### ❌ INCORRECT
```python
# Using SDK directly instead of CLI
from alibabacloud_waf_openapi20211001.client import Client

# Hardcoding credentials
os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'] = 'LTAI...'
```

### 2. Pagination Handling

#### ✅ CORRECT
```python
def paginate(base_cmd, page_size=50):
    all_items = []
    page = 1
    while True:
        cmd = f"{base_cmd} --page-size {page_size} --page-number {page}"
        data = run_cli(cmd)
        if not data:
            break
        items = data.get("Domains", data.get("Rules", []))
        all_items.extend(items)
        total = data.get("TotalCount", 0)
        if page * page_size >= total:
            break
        page += 1
    return all_items
```

### 3. Error Tolerance

#### ✅ CORRECT
```python
# Tolerate unavailable dimensions (e.g., no hybrid cloud)
try:
    hybrid = run_cli(f"aliyun waf-openapi describe-hybrid-cloud-resources ...")
except Exception:
    hybrid = None  # Skip this dimension gracefully
```

#### ❌ INCORRECT
```python
# Failing hard on optional dimensions
hybrid = run_cli(f"aliyun waf-openapi describe-hybrid-cloud-resources ...")
assert hybrid is not None  # This would fail for accounts without hybrid cloud
```

## Output Verification Criteria

### Excel Workbook

#### ✅ CORRECT
- Summary sheet with metadata, Row 4 carrying caller UID + scenario, **Row 5 carrying the diff baseline line** (`Diff baseline: <prev_filename>` / `Diff baseline: none (baseline mode — no previous backup found)` / `Diff baseline: disabled via --no-diff`; the Chinese workbook substitutes the analogous localized strings, see `references/verification-method.md` §1), and counts
- Instance Info sheet with quotas and raw JSON
- Member Accounts sheet present **only** when caller is the WAF delegated administrator
- Per-region sheets only when data exists
- Member-scoped sheets (CNAME / Cloud Resource / Hybrid Cloud / Protected Objects / Bindings) carry `OwnerUid` (`归属账号`) as the first column, populated for every data row; admin-scoped sheets (Instance / Object Groups / Templates / Defense Rules) have no such column
- Raw JSON column is last column, contains complete untruncated JSON
- Filename embeds caller UID + timestamp: `waf_config_backup_<UID>_YYYYMMDD_HHMMSS.xlsx`
- A `Changes (Diff)` sheet is appended whenever a baseline was resolved (auto-discovered or `--prev`); columns are `Change Type / Region / Scene / RuleId / Rule Name / Details`; supports `Added` / `Removed` / `Modified` rows (Modified covers `Name` / `Status` / `Action` / `Conditions` field changes for same-RuleId rules)

#### ❌ INCORRECT
- Missing Summary sheet, or Summary Row 4 missing the caller UID / scenario line, or Summary Row 5 missing the diff baseline line
- Member Accounts sheet appearing in single-UID runs, or missing in delegated-admin runs
- Data rows with blank `OwnerUid` first column on member-scoped sheets
- `OwnerUid` column appearing on admin-scoped sheets (Instance / Object Groups / Templates / Defense Rules)
- Raw JSON truncated at 800 characters
- Fixed filename without UID prefix that overwrites previous backups
- Empty sheets for dimensions with no data (should be skipped)
- `Changes (Diff)` sheet appearing when `--no-diff` is set, or when no baseline was discovered (console must print `Baseline mode: no previous backup found`)
- `Changes (Diff)` sheet missing when a same-language baseline exists in the output directory and `--no-diff` was not passed

## Multi-Account Scenario Acceptance

The skill must auto-detect and behave correctly under both account topologies. Verification points:

### Scenario A — Single UID

- Console output contains `✓ Single-UID scenario` and `Scenario: Single UID (<uid>)`
- Summary Row 4: `Caller UID: <uid> (Scenario: Single UID)`
- No `Member Accounts` sheet in the workbook
- Member-scoped sheets show the same `OwnerUid` value (= caller UID) in every populated row; the column itself is **hidden by default** in this scenario (value-redundant)
- Admin-scoped sheets (Instance / Object Groups / Templates / Defense Rules) have no `OwnerUid` column
- Filename: `waf_config_backup_<uid>_YYYYMMDD_HHMMSS.xlsx`

### Scenario B — Delegated Administrator

- Console output contains `✓ Delegated administrator detected (N member accounts)` and `Scenario: Delegated Administrator (UID <uid>, N member accounts)`
- Console output during data collection contains `Resolving resource ownership for delegated administrator...` followed by `[<region>] X/Y resources resolved`
- Summary Row 4: `Caller UID: <uid> (Scenario: Delegated Administrator (managing N member accounts))`
- `Member Accounts` sheet present, listing exactly N members (count matches Summary Row 4)
- Member-scoped sheets may show **different** `OwnerUid` values across rows; resolved values must equal one of the member account IDs (or fall back to caller UID only when `DescribeDefenseResourceOwnerUid` cannot resolve a name)
- Admin-scoped sheets (Instance / Object Groups / Templates / Defense Rules) have no `OwnerUid` column — these resources are admin-owned by definition
- For protected objects, the `OwnerUid` first column should agree with the API-native `OwnerUserId` column on rows where the API returns it
- Filename: `waf_config_backup_<admin-uid>_YYYYMMDD_HHMMSS.xlsx` (admin UID, not member UIDs)

### Graceful Degradation

- If `sts get-caller-identity` fails, the script proceeds with `caller_uid = unknown`; filename becomes `waf_config_backup_unknown_<timestamp>.xlsx` and Summary Row 4 shows `Caller UID: unknown`
- If `DescribeAccountDelegatedStatus` fails or returns ambiguous fields, the script defaults to single-UID behavior (no member-account probing)
- If `DescribeDefenseResourceOwnerUid` fails partially, unresolved resources fall back to caller UID; the script does NOT abort

## Diff Comparison Acceptance

Diff is **on by default**; auto-discovered baseline is the safe path for periodic backups. The script prints exactly one diff status line per language and records the same state in Summary Row 5.

### Scenario D — Auto-discovered baseline (default)

- No `--prev` and no `--no-diff` is passed
- The script scans the output directory for `waf_config_backup_<caller_uid>_*[_<lang>]?.xlsx`, excludes the current run's output, filters by language, and picks the file with the largest mtime
- Console: `[<LANG>] Diff vs <basename> (auto)`
- Summary Row 5: `Diff baseline: <basename>` / `比对基线: <basename>`
- Workbook contains a `Changes (Diff)` (Chinese: `变更对比`) sheet
- Per-language: under `--lang all`, the `_zh.xlsx` baseline matches the `_zh.xlsx` output and likewise for `_en.xlsx`

### Scenario E — Explicit baseline (`--prev`)

- `--prev <path>` overrides auto-discovery (used as-is for both languages under `--lang all`)
- Console: `[<LANG>] Diff vs <basename> (explicit)`
- Summary Row 5: same `Diff baseline: <basename>` line
- Workbook contains a `Changes (Diff)` sheet
- Legacy baselines (per-scene rule sheets, no merged `Defense Rules`) still produce `Added` / `Removed` rows, plus `Modified` rows for `Name` changes; `Modified` rows on `Status` / `Action` / `Conditions` require a baseline that already uses the merged-rules layout (those fields are absent in legacy baselines and intentionally skipped to avoid `'' → '<value>'` noise)

### Scenario F — Baseline mode (no previous backup found)

- Auto-discovery returns no candidate (first-time run in this directory, or a different `caller_uid`/`lang`)
- Console: `[<LANG>] Baseline mode: no previous backup found`
- Summary Row 5: `Diff baseline: none (baseline mode — no previous backup found)` / `比对基线: 无（基线模式 — 未发现历史备份）`
- Workbook does **not** contain a `Changes (Diff)` sheet

### Scenario G — Diff disabled (`--no-diff`)

- `--no-diff` is passed; auto-discovery is skipped and `--prev` is ignored
- Console: `[<LANG>] Diff disabled via --no-diff`
- Summary Row 5: `Diff baseline: disabled via --no-diff` / `比对基线: 已通过 --no-diff 禁用`
- Workbook does **not** contain a `Changes (Diff)` sheet
