# Acceptance Criteria: alibabacloud-waf-protectionconfig-backup

**Scenario**: WAF Protection Config Backup
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — Verify product name

#### CORRECT
```bash
aliyun waf-openapi describe-defense-resources ...
```

#### INCORRECT
```bash
aliyun waf describe-defense-resources ...        # wrong product name
aliyun WAF-openapi describe-defense-resources ... # wrong case
```

### 2. Command — Plugin mode format (lowercase with hyphens)

#### CORRECT
```bash
aliyun waf-openapi describe-defense-resources
aliyun waf-openapi describe-protection-module-rules
```

#### INCORRECT
```bash
aliyun waf-openapi DescribeDefenseResources       # traditional API format, NOT plugin mode
aliyun waf-openapi describeDefenseResources        # camelCase, NOT plugin mode
```

### 3. API Version — WAF 2.0 requires explicit version

#### CORRECT
```bash
aliyun waf-openapi describe-protection-module-rules --api-version 2019-09-10 ...
aliyun waf-openapi describe-instance-info --api-version 2019-09-10 ...
```

#### INCORRECT
```bash
aliyun waf-openapi describe-protection-module-rules ...
# Missing --api-version 2019-09-10 — will default to WAF 3.0 API and fail

aliyun waf-openapi describe-protection-module-rules --api-version 2021-10-01 ...
# Wrong version — 2021-10-01 is WAF 3.0, this API only exists in WAF 2.0
```

### 4. Region Parameter — Use `--biz-region-id`, not `--region`

#### CORRECT
```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou
```

#### INCORRECT
```bash
aliyun waf-openapi describe-instance --region cn-hangzhou
# --region sets the API endpoint region, NOT the WAF business region
# --biz-region-id is the WAF-specific parameter for business region scoping
```

### 5. Region Values

#### CORRECT
```bash
--biz-region-id cn-hangzhou       # China mainland
--biz-region-id ap-southeast-1    # International / non-China
```

#### INCORRECT
```bash
--biz-region-id cn-beijing        # Not a valid WAF region
--biz-region-id us-east-1         # Not a valid WAF region
```

### 6. User-Agent — Required on every API command

#### CORRECT
```bash
aliyun waf-openapi describe-defense-resources \
  --instance-id waf-cn-xxx \
  --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/a1b2c3d4...
```

#### INCORRECT
```bash
aliyun waf-openapi describe-defense-resources \
  --instance-id waf-cn-xxx \
  --biz-region-id cn-hangzhou
# Missing --user-agent flag — violates observability requirement
```

### 7. Pagination — Use `--pager` for list APIs

#### CORRECT
```bash
aliyun waf-openapi describe-defense-resources \
  --instance-id waf-cn-xxx \
  --biz-region-id cn-hangzhou \
  --pager \
  --user-agent ...
```

#### INCORRECT
```bash
aliyun waf-openapi describe-defense-resources \
  --instance-id waf-cn-xxx \
  --biz-region-id cn-hangzhou \
  --page-number 1 --page-size 10 \
  --user-agent ...
# Manual pagination — should use --pager for automatic handling
```

### 8. Defense Scene — Correct parameter names per WAF version

#### CORRECT (WAF 3.0)
```bash
aliyun waf-openapi describe-defense-templates \
  --defense-scene custom_acl ...
```

#### CORRECT (WAF 2.0)
```bash
aliyun waf-openapi describe-protection-module-rules \
  --api-version 2019-09-10 \
  --defense-type ac_custom ...
```

#### INCORRECT
```bash
# Using WAF 2.0 parameter name for WAF 3.0 API
aliyun waf-openapi describe-defense-templates --defense-type ac_custom ...

# Using WAF 3.0 parameter name for WAF 2.0 API
aliyun waf-openapi describe-protection-module-rules --defense-scene custom_acl ...
```

---

## Output Validation

### Correct File Structure

#### CORRECT
```
waf-backup-20260608-143025/waf3-cn-hangzhou.xlsx          # One workbook per region+version
waf-backup-20260608-143025/waf2-cn-hangzhou.xlsx
waf-backup-20260608-143025/waf3-ap-southeast-1.xlsx
waf-backup-20260608-143025/manifest.json
```

#### INCORRECT
```
waf-backup/waf3.xlsx                            # Missing region info in filename
waf-backup/cn-hangzhou/waf3.xlsx                 # Region in subdirectory instead of filename
waf-backup/cn-hangzhou/waf3/defense-resources.csv  # CSV files instead of Excel workbook
waf-backup/cn-hangzhou/waf3/defense-resources.json # JSON files instead of Excel workbook
waf-backup/cn-hangzhou/waf3/CC/templates.xlsx    # Per-scene files — data should be aggregated in sheets
```

### Correct Excel Workbook Structure

#### CORRECT
- Single `.xlsx` workbook per region + WAF version
- Each data module as a separate sheet (e.g., "defense-resources", "defense-templates", "protection-rules")
- Header row as first row in each sheet with column names
- Complex fields serialized as JSON strings in cells
- All per-domain/per-scene data aggregated into shared sheets with filter columns (Region, Domain, DefenseScene, DefenseType)

#### INCORRECT
- Individual CSV or JSON files per API call
- Per-domain subdirectories with separate files per DefenseType
- Missing header row in sheets
- All data dumped into a single sheet (should be separated by module)
- Empty workbook with no sheets
