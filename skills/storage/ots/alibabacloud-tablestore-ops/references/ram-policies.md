# Tablestore Read-Only Operations - RAM Policies

This document describes the RAM (Resource Access Management) permissions required for Tablestore **read-only** operations via `aliyun otsutil`.

## Minimum Required Permissions

### Read-Only Operations Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ots:GetInstance",
        "ots:ListInstance",
        "ots:ListTable",
        "ots:DescribeTable"
      ],
      "Resource": "acs:ots:*:*:instance/*"
    }
  ]
}
```

## Permission Details

### Permission-to-Command Mapping

| CLI Command | Required Permission | Resource |
|-------------|---------------------|----------|
| `aliyun otsutil describe_instance` | `ots:GetInstance` | `acs:ots:*:*:instance/<instanceName>` |
| `aliyun otsutil list_instance` | `ots:ListInstance` | `acs:ots:*:*:instance/*` |
| `aliyun otsutil list` | `ots:ListTable` | `acs:ots:*:*:instance/<instanceName>` |
| `aliyun otsutil desc` | `ots:DescribeTable` | `acs:ots:*:*:instance/<instanceName>/table/<tableName>` |
| `aliyun otsutil use` | N/A | N/A (local operation) |
| `aliyun otsutil config` | N/A | N/A (local operation) |

### Permission Descriptions

| Permission | Description |
|------------|-------------|
| `ots:GetInstance` | View instance details |
| `ots:ListInstance` | List instances in a region |
| `ots:ListTable` | List tables in an instance |
| `ots:DescribeTable` | View table details (schema, TTL, versions) |

## Managed Policies

Alibaba Cloud provides managed policies for Tablestore:

### AliyunOTSFullAccess

Full access to all Tablestore operations (more than needed for read-only).

```json
{
  "Version": "1",
  "Statement": [
    {
      "Action": "ots:*",
      "Resource": "*",
      "Effect": "Allow"
    }
  ]
}
```

**Use case:** Not recommended for read-only workflows

### AliyunOTSReadOnlyAccess (Recommended)

Read-only access to Tablestore resources.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ots:BatchGet*",
        "ots:Describe*",
        "ots:Get*",
        "ots:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Use case:** Read-only query workflows (recommended for this skill)

## Custom Policy Examples

### Instance + Table Read-Only

For users who only need to query instances and table schemas:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ots:GetInstance",
        "ots:ListInstance",
        "ots:ListTable",
        "ots:DescribeTable"
      ],
      "Resource": "acs:ots:*:*:instance/*"
    }
  ]
}
```

### Region-Specific Access

Limit operations to specific regions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ots:GetInstance",
        "ots:ListInstance",
        "ots:ListTable",
        "ots:DescribeTable"
      ],
      "Resource": "acs:ots:cn-hangzhou:*:instance/*"
    }
  ]
}
```

### Specific Instance Read-Only Access

Limit access to specific instances:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ots:GetInstance",
        "ots:ListTable",
        "ots:DescribeTable"
      ],
      "Resource": [
        "acs:ots:cn-hangzhou:*:instance/prod-instance",
        "acs:ots:cn-hangzhou:*:instance/staging-instance"
      ]
    }
  ]
}
```

## Resource Format

### Instance Resource ARN

```
acs:ots:<region>:<account-id>:instance/<instance-name>
```

**Components:**
- `acs` - Alibaba Cloud Service prefix
- `ots` - Service name (Tablestore)
- `<region>` - Region ID (e.g., `cn-hangzhou`) or `*` for all regions
- `<account-id>` - Alibaba Cloud account ID or `*`
- `instance/<instance-name>` - Instance name or `*` for all instances

**Examples:**
- `acs:ots:*:*:instance/*` - All instances in all regions
- `acs:ots:cn-hangzhou:*:instance/*` - All instances in cn-hangzhou
- `acs:ots:cn-hangzhou:*:instance/myinstance` - Specific instance

## Applying Policies

### Via RAM Console

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Identities** > **Users**
3. Select the target user
4. Click **Add Permissions**
5. Select or create the policy
6. Click **OK** to apply

### Via Aliyun CLI

```bash
# Attach managed policy
aliyun ram attach-policy-to-user \
  --policy-name AliyunOTSFullAccess \
  --policy-type System \
  --user-name <username> \
  --user-agent AlibabaCloud-Agent-Skills

# Create custom policy
aliyun ram create-policy \
  --policy-name OTSInstanceManagement \
  --policy-document '{"Version":"1","Statement":[{"Effect":"Allow","Action":["ots:CreateInstance","ots:GetInstance","ots:ListInstance"],"Resource":"acs:ots:*:*:instance/*"}]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

## Security Best Practices

1. **Principle of Least Privilege:** Only grant permissions that are actually needed
2. **Use RAM Users:** Never use root account credentials for daily operations
3. **Separate Environments:** Use different RAM users/roles for dev/staging/production
4. **Regular Audits:** Review and remove unused permissions periodically
5. **Use STS:** For temporary access, use Security Token Service instead of long-term credentials
6. **Enable MFA:** Require multi-factor authentication for sensitive operations

## Troubleshooting Permission Issues

### Error: "Permission Denied"

1. Check RAM user has required policy attached
2. Verify policy includes the specific action (e.g., `ots:ListTable`, `ots:DescribeTable`)
3. Verify resource pattern matches the target instance

### Error: "Access Denied"

1. Confirm AccessKey belongs to the correct RAM user
2. Verify AccessKey is active (not disabled)
3. Check for deny policies that might override allow policies

### Debug Command

Use `aliyun` CLI to check current permissions:

```bash
aliyun ram list-policies-for-user --user-name <username> --user-agent AlibabaCloud-Agent-Skills
```

## Reference Links

- [RAM Documentation](https://help.aliyun.com/product/28625.html)
- [Tablestore Authorization](https://help.aliyun.com/zh/tablestore/developer-reference/ots-api-authorization-rules/)
- [RAM Console](https://ram.console.aliyun.com/)
- [Instance Operations Doc](https://help.aliyun.com/zh/tablestore/developer-reference/instance-operations)
- [Data Table Operations Doc](https://help.aliyun.com/zh/tablestore/developer-reference/widecolumn-modeled-data-table-operations-with-tablestore-cli)
