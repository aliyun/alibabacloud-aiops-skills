---
name: alibabacloud-waf-checkresponse-intercept-query
description: |
  Diagnose why a request was blocked by Alibaba Cloud WAF. Retrieves block logs, identifies the triggering rule, and provides remediation guidance. Supports disabling problematic rules and managing WAF log collection settings.
  Use when users report being blocked by WAF, encounter 405/block error pages, see "Your request has been blocked" messages, or need to investigate and fix WAF interception issues.
  Trigger words: "WAF block query", "blocked by WAF", "405 troubleshooting", "request blocked", "checkresponse", "intercept query", "WAF拦截", "被WAF拦截", "disable WAF rule", "enable WAF log"
---

# WAF CheckResponse Intercept Query

## Prerequisites

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> see https://help.aliyun.com/document_detail/139508.html for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## Observability

**UA Template** — Every `aliyun` CLI command invocation must include `--user-agent` with the following format:

```
AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/{session-id}
```

**session-id generation rules**:
- Generate **once** at the start of each skill session (before the first CLI command)
- Format: 32-character lowercase hexadecimal string (e.g. `a1b2c3d4e5f67890abcdef1234567890`)
- Generation method: `python3 -c "import uuid; print(uuid.uuid4().hex)"`
- Reuse the **same** session-id for all CLI commands within the same session

Example:
```bash
# Generate session-id once at the beginning
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")

# Use in every CLI command
aliyun waf-openapi describe-instance --region cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

Before execution, you **must** collect the following information from the user:

| Parameter | Description | Required |
|-----------|-------------|----------|
| Request ID | The traceid obtained from the HTML body of WAF's block (intercept) response, or the Request ID shown on the 405 block page displayed in the browser | Yes |

**Optional**: WAF Instance ID, SLS Project name, SLS Logstore name (will be auto-discovered if not provided)

**Notes**:
- Request ID (traceid) is obtained from the HTML body of WAF's block response, or from the 405 block page displayed in the browser
- Uses Alibaba Cloud default credential chain for authentication (ECS RAM Role, ~/.alibabacloud/config, etc.)

## Region Information

| RegionId Value | Region | Description |
|----------------|--------|-------------|
| `cn-hangzhou` | Chinese Mainland | WAF instances within mainland China |
| `ap-southeast-1` | Outside Chinese Mainland | WAF instances in overseas and Hong Kong/Macao/Taiwan regions |

## Query Workflow

### Step 1: Information Collection

Confirm the Request ID (traceid) with the user. If the user has not provided one, guide them to obtain it from:
1. The 405 block page displayed in the browser, which shows the Request ID directly
2. The HTML body of WAF's block (intercept) response, which contains the traceid

### Step 2: Auto-Discover WAF Instances and Verify Log Service

If the user has not provided WAF Instance ID and SLS configuration, perform auto-discovery:

#### Step 2a: Discover WAF Instances

```bash
# Query WAF instances in both regions in parallel
aliyun waf-openapi describe-instance --region cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
aliyun waf-openapi describe-instance --region ap-southeast-1 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

#### Step 2b: Check Log Service Status (Mandatory Before Querying Logs)

**Before retrieving SLS configuration, you MUST first verify that the WAF instance has log service enabled** by calling `describe-sls-log-store-status`:

```bash
aliyun waf-openapi describe-sls-log-store-status --region <region-id> --instance-id '<instance-id>' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

- If the response indicates log service is **already enabled** (`SlsLogStoreStatus` is true/enabled), **skip** the enable operation and proceed directly to **Step 2c** (idempotent: no redundant writes).
- If log service is **not enabled**, inform the user that WAF log service must be activated before log queries can proceed. With user consent, call `modify-user-waf-log-status` to enable it:

```bash
aliyun waf-openapi modify-user-waf-log-status \
  --region <region-id> \
  --instance-id '<instance-id>' \
  --log-status 1 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

> **Constraint**: This skill only supports **enabling** log service (`--log-status 1`). Disabling log service is **not permitted**. Never call this API with `--log-status 0`.

After enabling, wait a moment and re-verify with `describe-sls-log-store-status` to confirm activation.

#### Step 2c: Retrieve SLS Configuration (Mandatory After Confirming Log Service is Enabled)

Once `describe-sls-log-store-status` confirms that log service is enabled, you **must immediately** call `describe-sls-log-store` to obtain the WAF log Project and Logstore information:

```bash
aliyun waf-openapi describe-sls-log-store --region <region-id> --instance-id '<instance-id>' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

Key fields in the `describe-sls-log-store` response:

| Field | Description |
|-------|-------------|
| `ProjectName` | SLS Project name associated with the WAF instance |
| `LogStoreName` | SLS Logstore name for WAF logs |
| `Ttl` | Log retention period (in days) |

**Cross-region note**: The SLS log storage region may differ from the WAF instance region (e.g., WAF in `ap-southeast-1` but SLS logs stored in `ap-southeast-5`). When querying SLS in Step 3, always use the region where the SLS Project is located, not the WAF instance region.

> **Note**: The `describe-instance` command does not require `--biz-region-id` when `--region` is specified. The `--region` flag determines the endpoint routing. Only pass `--biz-region-id` if you need to override the business region separately from the endpoint.

### Step 3: Query SLS Logs

Use the `ProjectName`, `LogStoreName` and SLS region obtained from Step 2 to query block logs (prefer using the Python script):

```bash
# Query using script (recommended, supports automatic time range expansion)
python3 scripts/get_waf_logs.py \
  --project <project-name> \
  --logstore <logstore-name> \
  --request-id <request-id> \
  --region <sls-region>
```

Or use CLI directly:

```bash
TO_TIME=$(python3 -c "import time; print(int(time.time()))")
FROM_TIME=$((TO_TIME - 86400))

aliyun sls get-logs \
  --project <project-name> \
  --logstore <logstore-name> \
  --from $FROM_TIME \
  --to $TO_TIME \
  --query "<request-id>" \
  --region <sls-region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

**Important**: The `--region` here must be the SLS log storage region, which may differ from the WAF instance region. Check the `describe-sls-log-store` response from Step 2 to determine the correct SLS region.

### Step 4: Query Rule Details

Extract `rule_id` and `final_plugin` from the logs to query the rule configuration.

**Note**: If you don't know the `TemplateId`, first use `describe-defense-templates` to find the template that contains the rule. The `describe-defense-templates` API uses `--defense-scene` to filter by scenario:

| final_plugin | DefenseScene |
|--------------|---------------|
| customrule | custom_acl or custom_cc |
| waf | waf_group |
| scanner_behavior | antiscan |
| dlp | dlp |
| tamperproof | tamperproof |

```bash
# Step 4a: Find the template containing the rule (use --defense-scene to filter)
aliyun waf-openapi describe-defense-templates \
  --region <region-id> \
  --instance-id '<instance-id>' \
  --defense-scene '<defense-scene>' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

```bash
# Step 4b: Query rule details (describe-defense-rule does NOT use --defense-scene)
aliyun waf-openapi describe-defense-rule \
  --region <region-id> \
  --instance-id '<instance-id>' \
  --template-id <template-id> \
  --rule-id <rule-id> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

### Step 5: Output Analysis Report

Output using the following template:

```markdown
## WAF Block Analysis Report

### Request Information
- Request ID: {request_id}
- Block Time: {time}
- Client IP: {real_client_ip (masked, e.g. 192.***.***.***)} 
- Request URL: {host}{request_path}?{masked_query_params}

### Block Details
- Rule ID: {rule_id}
- Rule Name: {rule_name}
- Action: {action}

### Recommendations
{Provide recommendations based on rule type, refer to references/common-block-reasons.md}
```

## Troubleshooting

### No Logs Found

1. **Re-check global log service status** (should have been verified in Step 2b, but re-confirm):
   ```bash
   aliyun waf-openapi describe-sls-log-store-status --region <region-id> --instance-id '<instance-id>' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
   ```
   If not enabled, prompt the user and enable with `modify-user-waf-log-status` (see Step 2b). Only enabling (`--log-status 1`) is allowed.

2. **List protection objects** (to get resource names for the next step):
   ```bash
   aliyun waf-openapi describe-defense-resources --region <region-id> --instance-id '<instance-id>' --query '{"PageNumber":1,"PageSize":20}' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
   ```
   Extract the `Resource` field from each item in the response (e.g., `ddddingdang.xyz-waf`, `alb-xxx-alb`).

3. **Check protection object log switch**:
   ```bash
   aliyun waf-openapi describe-resource-log-status --region <region-id> --instance-id '<instance-id>' --resources '<resource-name-1>,<resource-name-2>' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
   ```
   The `--resources` value is a comma-separated list of resource names obtained from `describe-defense-resources` above.

4. **Enable protection object log collection** (check-then-act: only if `describe-resource-log-status` shows log collection is disabled for the target resource; skip if already enabled):
   ```bash
   aliyun waf-openapi modify-resource-log-status \
     --region <region-id> \
     --instance-id '<instance-id>' \
     --resource '<resource-name>' \
     --status true \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
   ```

See [references/common-block-reasons.md](references/common-block-reasons.md) for protection object naming conventions.

### Permission Denied Errors

If you encounter permission errors, check the following:

1. **Verify CLI profile configuration**:
   ```bash
   aliyun configure list
   ```

2. **Check RAM policy permissions**:
   Required permissions:
   - `waf-openapi:DescribeInstance`
   - `waf-openapi:DescribeSlsLogStoreStatus`
   - `waf-openapi:DescribeSlsLogStore`
   - `waf-openapi:ModifyUserWafLogStatus` (optional, for enabling log service)
   - `waf-openapi:DescribeDefenseRule` (for rule details)
   - `sls:GetLogs` (for log queries)

3. **Try specifying a different profile**:
   ```bash
   aliyun waf-openapi describe-instance --profile <profile-name> --region <region-id> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
   ```

### Request ID Not Found

If the Request ID is not found in the logs:

1. **Verify Request ID format**: Should be 32 characters without hyphens
2. **Check time range**: The script automatically expands search up to 90 days
3. **Verify the correct region**: Try both `cn-hangzhou` and `ap-southeast-1`
4. **Check log retention (TTL)**: Default is 180 days, use `--ttl` parameter if different

### Multi-Instance Scenarios

If both Chinese Mainland and non-Chinese Mainland instances exist, determine based on query results:
- Logs found in only one region -> use that region directly
- Logs found in both regions -> ask the user for clarification
- No logs found in either region -> ask the user for the expected region, check protection object log switch

**Note**: Follow the same discovery commands as in Step 2, then query logs across all discovered SLS projects until the Request ID is found.

## Rule Operation Constraints

### Warning: Rule Disabling Policy

When the user requests to disable a rule:
1. **Check current rule status first** — call `describe-defense-rule` to query the rule's current status. If the rule is already in the target state (e.g., already disabled), **skip** the write operation and inform the user (idempotent check-then-act pattern)
2. **Only perform disable operations** (`modify-defense-rule-status` with `--rule-status 0`)
3. **Never delete rules**
4. **Never modify rule content**
5. Must confirm with user before executing

```bash
# Disable a rule (only after confirming it is currently enabled)
aliyun waf-openapi modify-defense-rule-status \
  --region <region-id> \
  --instance-id '<instance-id>' \
  --rule-id <rule-id> \
  --rule-status 0 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-checkresponse-intercept-query/${SESSION_ID}"
```

See [references/rule-operations.md](references/rule-operations.md) for detailed instructions.

## References

- [RAM Policy Requirements](references/ram-policies.md)
- [Rule Configuration Details](references/rule-config-details.md)
- [Rule Operation Policy](references/rule-operations.md)
- [Common Block Reasons](references/common-block-reasons.md)
- [WAF OpenAPI](https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference)
