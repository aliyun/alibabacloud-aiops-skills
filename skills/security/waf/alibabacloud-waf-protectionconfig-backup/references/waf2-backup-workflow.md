# WAF 2.0 Backup Workflow

API Version: `2019-09-10` | Product Code: `waf-openapi`

**CRITICAL:** All WAF 2.0 commands MUST include `--api-version 2019-09-10` and `--region {region}`. The `--region` flag sets the API endpoint region — without it, non-China-mainland instances (e.g., ap-southeast-1) cannot be found.

All commands below also require `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}`.

## Excel Output Convention

All backup data for a region is saved into a single Excel workbook: `{BACKUP_DIR}/waf2-{region}.xlsx`. Each data module is written as a separate sheet within the workbook. The `openpyxl` Python library is used to generate .xlsx files. Complex/nested fields (e.g., `Content`) are serialized as JSON strings within Excel cells. API error responses are skipped (not written to sheets).

---

## Phase 1: Detect WAF 2.0 Instance

```bash
aliyun waf-openapi describe-instance-info \
  --api-version 2019-09-10 \
  --region {region} \
  --biz-region-id {region} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Extract instance information from the response. If no instance exists, skip this region for WAF 2.0.

Parse and write to sheet **"instance-info"** of `{BACKUP_DIR}/waf2-{region}.xlsx`

**Columns:** `Region, InstanceId, PayType, Status, EndDate, InDebt, SubscriptionType, Version`

---

## Phase 2: List All Domains

```bash
aliyun waf-openapi describe-domain-names \
  --api-version 2019-09-10 \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.DomainNames[]` array and write to sheet **"domain-names"**

**Columns:** `Region, Domain`

Extract the list of domain names from the response for iteration in Phase 3.

---

## Phase 3: Backup Per-Domain Protection Rules

For each domain, iterate through all 16 DefenseType values.

### DefenseType Values to Iterate

```
waf-codec, tamperproof, dlp, ng_account, bot_crawler,
bot_intelligence, antifraud, antifraud_js, bot_algorithm,
bot_wxbb_pkg, bot_wxbb, ac_blacklist, ac_highfreq,
ac_dirscan, ac_custom, whitelist
```

### Step 3.1: Get Protection Module Rules

For each domain + DefenseType combination:

```bash
aliyun waf-openapi describe-protection-module-rules \
  --api-version 2019-09-10 \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --domain {domain} \
  --defense-type {DefenseType} \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.Rules[]` array and **append** to sheet **"protection-rules"**

**Columns:** `Region, Domain, DefenseType, RuleId, Status, Time, Version, Content`

### Step 3.2: Get Protection Module Status

For each domain + DefenseType combination:

```bash
aliyun waf-openapi describe-protection-module-status \
  --api-version 2019-09-10 \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --domain {domain} \
  --defense-type {DefenseType} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

### Step 3.3: Get Protection Module Mode

For each domain + DefenseType combination:

```bash
aliyun waf-openapi describe-protection-module-mode \
  --api-version 2019-09-10 \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --domain {domain} \
  --defense-type {DefenseType} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Combine status (Step 3.2) and mode (Step 3.3) results and **append** to sheet **"protection-status"**

**Columns:** `Region, Domain, DefenseType, ModuleStatus, Mode`

> Note: If either status or mode API returns an error for a given DefenseType, skip the `Mode` column or the entire row as appropriate. Many DefenseType values do not support the mode query — this is expected.

---

## Phase 4: Backup Domain Rule Group

For each domain:

```bash
aliyun waf-openapi describe-domain-rule-group \
  --api-version 2019-09-10 \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --domain {domain} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse and **append** to sheet **"domain-rule-groups"**

**Columns:** `Region, Domain, RuleGroupId, RuleGroupName, WafVersion, PolicyId`

---

## Output Structure

```
{BACKUP_DIR}/waf2-{region}.xlsx
  ├── Sheet: instance-info
  ├── Sheet: domain-names
  ├── Sheet: protection-rules
  ├── Sheet: protection-status
  └── Sheet: domain-rule-groups
```

## Error Handling

- If a DefenseType returns empty rules for a domain, this is **normal**. No rows are appended to the sheet.
- Some DefenseType values (e.g., `antifraud`, `bot_wxbb`) may not be enabled or available for all WAF 2.0 editions. If the API returns an error, skip it and continue to the next DefenseType.
- If pagination is needed (large rule sets), `--pager` handles it automatically.
- If API returns a throttling error (HTTP 429), wait 1-2 seconds and retry.

## Important Notes

- WAF 2.0 is organized per-domain, unlike WAF 3.0 which uses defense templates.
- Always use `--api-version 2019-09-10` and `--region {region}` for every WAF 2.0 command.
- Domain names with special characters should be quoted in shell commands.
- All per-domain data is aggregated into shared sheets with `Domain` and `DefenseType` columns for filtering.
