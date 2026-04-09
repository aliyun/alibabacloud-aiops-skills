# RAM Policy Requirements

This skill requires the following RAM permissions to operate correctly.

## Minimum Required Permissions

### WAF OpenAPI Permissions

| Action | Resource | Description |
|--------|----------|-------------|
| `waf:DescribeInstance` | `*` | Query WAF instance information |
| `waf:DescribeSlsLogStore` | `*` | Get SLS log storage configuration |
| `waf:DescribeSlsLogStoreStatus` | `*` | Check global log service status |
| `waf:DescribeResourceLogStatus` | `*` | Check protection object log switch |
| `waf:DescribeDefenseTemplates` | `*` | List defense templates |
| `waf:DescribeDefenseRule` | `*` | Query defense rule details |
| `waf:DescribeDefenseRules` | `*` | List defense rules |
| `waf:DescribeBaseSystemRules` | `*` | Query built-in system rule details |

### SLS Permissions

| Action | Resource | Description |
|--------|----------|-------------|
| `log:GetLogStoreLogs` | `acs:log:*:*:project/<waf-sls-project>/logstore/<waf-logstore>` | Query WAF block logs from SLS |

### Optional Permissions (Rule Operations)

These permissions are only needed when the user requests to disable a WAF rule:

| Action | Resource | Description |
|--------|----------|-------------|
| `waf:ModifyDefenseRuleStatus` | `*` | Disable/enable a defense rule (RuleStatus=0/1 only) |

### Optional Permissions (Log Service Management)

These permissions are only needed when enabling log service or log collection for a protection object:

| Action | Resource | Description |
|--------|----------|-------------|
| `waf:ModifyUserWafLogStatus` | `*` | Enable WAF log service for an instance (enable only, disable is not permitted) |
| `waf:ModifyResourceLogStatus` | `*` | Enable/disable log collection for a protection object |

## Sample RAM Policy (JSON)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:DescribeInstance",
        "waf:DescribeSlsLogStore",
        "waf:DescribeSlsLogStoreStatus",
        "waf:DescribeResourceLogStatus",
        "waf:DescribeDefenseTemplates",
        "waf:DescribeDefenseRule",
        "waf:DescribeDefenseRules",
        "waf:DescribeBaseSystemRules"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs"
      ],
      "Resource": "acs:log:*:*:project/*/logstore/*"
    }
  ]
}
```

## Notes

- The WAF resources use `*` because WAF instance IDs are dynamically discovered during execution.
- The SLS resource can be narrowed to specific projects/logstores if known in advance.
- Rule modification permissions (`ModifyDefenseRuleStatus`) are intentionally excluded from the base policy. Only grant when rule disable operations are needed.
- This skill **never** calls `DeleteDefenseRule` or `ModifyDefenseRule` — those actions are explicitly prohibited.
