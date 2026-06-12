# WAF 3.0 Backup Workflow

API Version: `2021-10-01` | Product Code: `waf-openapi`

All commands below require `--region {region}` and `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}`.

## Excel Output Convention

All backup data for a region is saved into a single Excel workbook: `{BACKUP_DIR}/waf3-{region}.xlsx`. Each data module is written as a separate sheet within the workbook. The `openpyxl` Python library is used to generate .xlsx files:

```python
python3 -c "
import json, sys
from openpyxl import Workbook
wb = Workbook()
# Create sheets, parse JSON responses, write rows
wb.save('{BACKUP_DIR}/waf3-{region}.xlsx')
"
```

Complex/nested fields (e.g., `Config`, `Details`) are serialized as JSON strings within Excel cells. API error responses are skipped (not written to sheets).

---

## Phase 1: Detect WAF 3.0 Instance

```bash
aliyun waf-openapi describe-instance \
  --region {region} \
  --biz-region-id {region} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Extract `InstanceId` from the response. If no instance exists, skip this region for WAF 3.0.

Parse and write to sheet **"instance"** of `{BACKUP_DIR}/waf3-{region}.xlsx`

**Columns:** `Region, InstanceId, Edition, Status, PayType, StartTime, EndTime, InDebt, RegionId, Details`

---

## Phase 2: Backup Defense Resources

### 2.1 Defense Resources

```bash
aliyun waf-openapi describe-defense-resources \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.Resources[]` array and write to sheet **"defense-resources"**

**Columns:** `Region, Resource, Product, Pattern, InstanceId, OwnerUserId, GmtCreate, GmtModified, ResourceOrigin, XffStatus, AcwCookieStatus, AcwSecureStatus, AcwV3SecureStatus, Detail, ResourceManagerResourceGroupId`

### 2.2 Defense Resource Groups

```bash
aliyun waf-openapi describe-defense-resource-groups \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.Groups[]` array and write to sheet **"defense-resource-groups"**

**Columns:** `Region, GroupId, GroupName, Description, Resources, GmtCreate, GmtModified`

---

## Phase 3: Backup Defense Templates and Rules

For each `DefenseScene` value listed below, perform the three-step backup.

### DefenseScene Values to Iterate

**Template-level scenes (DefenseType=template):**
```
waf_group, waf_base, waf_base_compliance, waf_base_sema, cc,
antiscan_dirscan, antiscan_highfreq, antiscan_scantools,
ip_blacklist, custom_acl, region_block, tamperproof, dlp,
custom_response_block, spike_throttle
```

**Resource-level scenes (DefenseType=resource):**
```
account_identifier, custom_response, waf_codec
```

**Global-level scenes (DefenseType=global):**
```
regular_custom, address_book, custom_response
```

> Note: When iterating, use the corresponding `DefenseType` value (`template`, `resource`, or `global`) together with the `DefenseScene` value.

### Step 3.1: List Defense Templates for a Scene

```bash
aliyun waf-openapi describe-defense-templates \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --defense-scene {DefenseScene} \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.Templates[]` array and **append** to sheet **"defense-templates"**

**Columns:** `Region, DefenseScene, TemplateId, TemplateName, TemplateType, TemplateStatus, TemplateOrigin, GmtModified`

If the result is empty (no templates for this scene), skip Steps 3.2 and 3.3 for this scene.

### Step 3.2: Get Rules for Each Template

For each `TemplateId` found in Step 3.1, use the corresponding `DefenseType` (`template`, `resource`, or `global`) and pass the filter conditions via `--query` as a JSON string:

```bash
aliyun waf-openapi describe-defense-rules \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --defense-type {DefenseType} \
  --query '{"DefenseScene":"{DefenseScene}","TemplateId":{TemplateId}}' \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

> **Note:** The `--defense-type` parameter accepts `template`, `resource`, or `global`. The `--query` parameter is a JSON string that filters by `DefenseScene` and `TemplateId`.

Parse `.Rules[]` array and **append** to sheet **"defense-rules"**

**Columns:** `Region, DefenseScene, DefenseType, TemplateId, RuleId, RuleName, Status, DefenseOrigin, GmtModified, Config`

### Step 3.3: Get Template-Resource Bindings

For each `TemplateId` found in Step 3.1:

```bash
aliyun waf-openapi describe-template-resources \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --template-id {TemplateId} \
  --resource-type single \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.Resources[]` array and **append** to sheet **"template-resource-bindings"**

**Columns:** `Region, DefenseScene, TemplateId, Resource`

---

## Phase 4: Backup Major Protection Black IPs

```bash
aliyun waf-openapi describe-major-protection-black-ips \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.BlackIps[]` array and write to sheet **"major-protection-black-ips"**

---

## Phase 5: Backup Address Books

```bash
aliyun waf-openapi describe-addresses \
  --region {region} \
  --instance-id {InstanceId} \
  --biz-region-id {region} \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-waf-protectionconfig-backup/{session-id}
```

Parse `.Addresses[]` array and write to sheet **"addresses"**

---

## Output Structure

```
{BACKUP_DIR}/waf3-{region}.xlsx
  ├── Sheet: instance
  ├── Sheet: defense-resources
  ├── Sheet: defense-resource-groups
  ├── Sheet: defense-templates
  ├── Sheet: defense-rules
  ├── Sheet: template-resource-bindings
  ├── Sheet: major-protection-black-ips
  └── Sheet: addresses
```

## Error Handling

- If a DefenseScene returns empty templates, this is **normal** — many scenes are not used by every account. Simply skip that scene (no rows appended to sheet).
- If pagination is needed (large result sets), `--pager` handles page-number-based pagination automatically.
- If API returns a throttling error (HTTP 429), wait 1-2 seconds and retry.
- API error responses (e.g., `InvalidParameter`) should be skipped — do not write error rows to sheets.
