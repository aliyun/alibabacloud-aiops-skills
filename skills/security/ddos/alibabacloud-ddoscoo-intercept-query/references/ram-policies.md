# RAM Policy Requirements

This skill requires the following RAM permissions to operate correctly.

## Minimum Required Permissions

### DDoS Pro (ddoscoo) Permissions

| Action | Resource | Description |
|--------|----------|-------------|
| `yundun-ddoscoo:DescribeInstances` | `*` | Query DDoS Pro instance list |
| `yundun-ddoscoo:DescribeInstanceIds` | `*` | Query DDoS Pro instance IDs |
| `yundun-ddoscoo:DescribeSlsOpenStatus` | `*` | Check SLS open status |
| `yundun-ddoscoo:DescribeLogStoreExistStatus` | `*` | Check if log store exists |
| `yundun-ddoscoo:DescribeSlsLogstoreInfo` | `*` | Get SLS logstore info (project, logstore, capacity, TTL) |
| `yundun-ddoscoo:DescribeWebAccessLogStatus` | `*` | Check domain full log status |
| `yundun-ddoscoo:DescribeWebAccessLogDispatchStatus` | `*` | Check all domains full log dispatch status |
| `yundun-ddoscoo:DescribeWebRules` | `*` | Query website forwarding rules |
| `yundun-ddoscoo:DescribeWebCcRulesV2` | `*` | Query CC protection rules |
| `yundun-ddoscoo:DescribeWebPreciseAccessRule` | `*` | Query precise access control rules |
| `yundun-ddoscoo:DescribeWebAreaBlockConfigs` | `*` | Query region blocking configs |
| `yundun-ddoscoo:DescribeAutoCcBlacklist` | `*` | Query auto CC blacklist |
| `yundun-ddoscoo:DescribeL7GlobalRule` | `*` | Query global defense policy |

### SLS Permissions

| Action | Resource | Description |
|--------|----------|-------------|
| `log:GetLogStoreLogs` | `acs:log:*:*:project/<ddos-sls-project>/logstore/<ddos-logstore>` | Query DDoS Pro full logs from SLS |

### Optional Permissions (Log Service Management)

These permissions are only needed when enabling full log for a domain:

| Action | Resource | Description |
|--------|----------|-------------|
| `yundun-ddoscoo:EnableWebAccessLogConfig` | `*` | Enable full log for a domain (enable only, disable is not permitted) |

### Optional Permissions (Rule Operations)

These permissions are only needed when the user requests to disable a rule:

| Action | Resource | Description |
|--------|----------|-------------|
| `yundun-ddoscoo:DisableWebCcRule` | `*` | Disable CC custom rule for a domain |
| `yundun-ddoscoo:ModifyWebPreciseAccessSwitch` | `*` | Toggle precise access control switch |

## Sample RAM Policy (JSON)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddoscoo:DescribeInstances",
        "yundun-ddoscoo:DescribeInstanceIds",
        "yundun-ddoscoo:DescribeSlsOpenStatus",
        "yundun-ddoscoo:DescribeLogStoreExistStatus",
        "yundun-ddoscoo:DescribeSlsLogstoreInfo",
        "yundun-ddoscoo:DescribeWebAccessLogStatus",
        "yundun-ddoscoo:DescribeWebAccessLogDispatchStatus",
        "yundun-ddoscoo:DescribeWebRules",
        "yundun-ddoscoo:DescribeWebCcRulesV2",
        "yundun-ddoscoo:DescribeWebPreciseAccessRule",
        "yundun-ddoscoo:DescribeWebAreaBlockConfigs",
        "yundun-ddoscoo:DescribeAutoCcBlacklist",
        "yundun-ddoscoo:DescribeL7GlobalRule"
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

- DDoS Pro resources use `*` because instance IDs and domains are dynamically discovered during execution.
- SLS resource can be narrowed to specific projects/logstores if known in advance.
- Rule disable permissions are intentionally excluded from the base policy. Only grant when rule disable operations are needed.
- This skill **never** calls delete APIs for rules — deletion is explicitly prohibited.
