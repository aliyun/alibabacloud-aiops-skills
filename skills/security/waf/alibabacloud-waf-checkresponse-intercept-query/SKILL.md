---
name: alibabacloud-waf-checkresponse-intercept-query
description: |
  Query Alibaba Cloud WAF block reasons via SLS logs and WAF CLI. Analyzes detailed information about blocked requests. Optionally supports disabling WAF rules (ModifyDefenseRuleStatus) and managing log service settings (ModifyUserWafLogStatus, ModifyResourceLogStatus).
  Use when users report being blocked by WAF, encounter 405/block error pages, or need to investigate and remediate WAF security rules.
  Trigger words: "WAF block query", "blocked by WAF", "405 troubleshooting", "request blocked", "checkresponse", "intercept query", "disable WAF rule", "enable WAF log"
---

# WAF CheckResponse Intercept Query

## Prerequisites

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

**Important**: All `aliyun` CLI calls in this skill **must** include the header `--header User-Agent=AlibabaCloud-Agent-Skills` to identify the caller.

### Step 1: Information Collection

Confirm the Request ID (traceid) with the user. If the user has not provided one, guide them to obtain it from:
1. The 405 block page displayed in the browser, which shows the Request ID directly
2. The HTML body of WAF's block (intercept) response, which contains the traceid

### Step 2: Auto-Discover WAF Instances and Verify Log Service

If the user has not provided WAF Instance ID and SLS configuration, perform auto-discovery:

#### Step 2a: Discover WAF Instances

```bash
# Query WAF instances in both regions in parallel
aliyun waf-openapi DescribeInstance --region cn-hangzhou --RegionId cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills
aliyun waf-openapi DescribeInstance --region ap-southeast-1 --RegionId ap-southeast-1 --header User-Agent=AlibabaCloud-Agent-Skills
```

#### Step 2b: Check Log Service Status (Mandatory Before Querying Logs)

**Before retrieving SLS configuration, you MUST first verify that the WAF instance has log service enabled** by calling `DescribeSlsLogStoreStatus`:

```bash
aliyun waf-openapi DescribeSlsLogStoreStatus --region <region-id> --InstanceId '<instance-id>' --RegionId '<region-id>' --header User-Agent=AlibabaCloud-Agent-Skills
```

- If the response indicates log service is **already enabled** (`SlsLogStoreStatus` is true/enabled), **skip** the enable operation and proceed directly to **Step 2c** (idempotent: no redundant writes).
- If log service is **not enabled**, inform the user that WAF log service must be activated before log queries can proceed. With user consent, call `ModifyUserWafLogStatus` to enable it:

```bash
aliyun waf-openapi ModifyUserWafLogStatus \
  --region <region-id> \
  --InstanceId '<instance-id>' \
  --Status 1 \
  --RegionId '<region-id>' \
  --header User-Agent=AlibabaCloud-Agent-Skills
```

> **Constraint**: This skill only supports **enabling** log service (`Status=1`). Disabling log service is **not permitted**. Never call this API with `Status=0`.

After enabling, wait a moment and re-verify with `DescribeSlsLogStoreStatus` to confirm activation.

#### Step 2c: Retrieve SLS Configuration (Mandatory After Confirming Log Service is Enabled)

Once `DescribeSlsLogStoreStatus` confirms that log service is enabled, you **must immediately** call `DescribeSlsLogStore` to obtain the WAF log Project and Logstore information:

```bash
aliyun waf-openapi DescribeSlsLogStore --region <region-id> --InstanceId '<instance-id>' --RegionId '<region-id>' --header User-Agent=AlibabaCloud-Agent-Skills
```

Key fields in the `DescribeSlsLogStore` response:

| Field | Description |
|-------|-------------|
| `ProjectName` | SLS Project name associated with the WAF instance |
| `LogStoreName` | SLS Logstore name for WAF logs |
| `Ttl` | Log retention period (in days) |

**Cross-region note**: The SLS log storage region may differ from the WAF instance region (e.g., WAF in `ap-southeast-1` but SLS logs stored in `ap-southeast-5`). When querying SLS in Step 3, always use the region where the SLS Project is located, not the WAF instance region.

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
  --header User-Agent=AlibabaCloud-Agent-Skills
```

**Important**: The `--region` here must be the SLS log storage region, which may differ from the WAF instance region. Check the `DescribeSlsLogStore` response from Step 2 to determine the correct SLS region.

### Step 4: Query Rule Details

Extract `rule_id` and `final_plugin` from the logs to query the rule configuration:

**Important**: The `DescribeDefenseRule` API requires the `DefenseScene` parameter. Common defense scenes include:
- `custom_acl` - Custom access control rules
- `custom_cc` - Custom rate limiting rules (CC rules)
- `waf_group` - WAF protection rules
- `antiscan` - Anti-scan rules
- `dlp` - Data leakage prevention
- `tamperproof` - Anti-tampering

You can determine the defense scene from `final_plugin` field in the logs:
| final_plugin | DefenseScene |
|--------------|---------------|
| customrule | custom_acl or custom_cc |
| waf | waf_group |
| scanner_behavior | antiscan |
| dlp | dlp |

```bash
# Query rule details with DefenseScene
aliyun waf-openapi DescribeDefenseRule \
  --region <region-id> \
  --InstanceId '<instance-id>' \
  --TemplateId <template-id> \
  --RuleId <rule-id> \
  --DefenseScene '<defense-scene>' \
  --RegionId '<region-id>' \
  --header User-Agent=AlibabaCloud-Agent-Skills
```

**Note**: If you don't know the `TemplateId`, first use `DescribeDefenseTemplates` to list templates:
```bash
aliyun waf-openapi DescribeDefenseTemplates \
  --region <region-id> \
  --InstanceId '<instance-id>' \
  --DefenseScene '<defense-scene>' \
  --RegionId '<region-id>' \
  --header User-Agent=AlibabaCloud-Agent-Skills
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
   aliyun waf-openapi DescribeSlsLogStoreStatus --region <region-id> --InstanceId '<instance-id>' --RegionId '<region-id>' --header User-Agent=AlibabaCloud-Agent-Skills
   ```
   If not enabled, prompt the user and enable with `ModifyUserWafLogStatus` (see Step 2b). Only enabling (`Status=1`) is allowed.

2. **Check protection object log switch**:
   ```bash
   aliyun waf-openapi DescribeResourceLogStatus --region <region-id> --InstanceId '<instance-id>' --RegionId '<region-id>' --header User-Agent=AlibabaCloud-Agent-Skills
   ```

3. **Enable protection object log collection** (check-then-act: only if `DescribeResourceLogStatus` shows log collection is disabled for the target resource; skip if already enabled):
   ```bash
   aliyun waf-openapi ModifyResourceLogStatus \
     --region <region-id> \
     --InstanceId '<instance-id>' \
     --Resource '<resource-name>' \
     --Status true \
     --header User-Agent=AlibabaCloud-Agent-Skills
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
   aliyun waf-openapi DescribeInstance --profile <profile-name> --region <region-id> --header User-Agent=AlibabaCloud-Agent-Skills
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
1. **Check current rule status first** — call `DescribeDefenseRule` to query the rule's current status. If the rule is already in the target state (e.g., already disabled), **skip** the write operation and inform the user (idempotent check-then-act pattern)
2. **Only perform disable operations** (`ModifyDefenseRuleStatus` with `RuleStatus=0`)
3. **Never delete rules**
4. **Never modify rule content**
5. Must confirm with user before executing

```bash
# Disable a rule (only after confirming it is currently enabled)
aliyun waf-openapi ModifyDefenseRuleStatus \
  --region <region-id> \
  --InstanceId '<instance-id>' \
  --RuleId <rule-id> \
  --RuleStatus 0 \
  --RegionId '<region-id>' \
  --header User-Agent=AlibabaCloud-Agent-Skills
```

See [references/rule-operations.md](references/rule-operations.md) for detailed instructions.

## References

- [RAM Policy Requirements](references/ram-policies.md)
- [Rule Configuration Details](references/rule-config-details.md)
- [Rule Operation Policy](references/rule-operations.md)
- [Common Block Reasons](references/common-block-reasons.md)
- [WAF OpenAPI](https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference)
