# RAM Permission Policies — Domain Query

## Required Permissions

| # | RAM Action | Description | Type |
|---|-----------|-------------|------|
| 1 | `domain:QueryDomainList` | Query domain list | Read |
| 2 | `domain:QueryAdvancedDomainList` | Advanced domain list query | Read |
| 3 | `domain:QueryDomainByDomainName` | Query domain by name | Read |
| 4 | `domain:QueryDomainByInstanceId` | Query domain by instance ID | Read |

## Minimum Required Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "domain:QueryDomainList",
        "domain:QueryAdvancedDomainList",
        "domain:QueryDomainByDomainName",
        "domain:QueryDomainByInstanceId"
      ],
      "Resource": "*"
    }
  ]
}
```

## How to Attach Policy

### Via RAM Console
1. Go to https://ram.console.aliyun.com/policies → Create Policy → JSON
2. Name: `AliyunDomainQueryAccess`
3. Paste the JSON policy above
4. Attach to target user/role

### Via CLI
```bash
aliyun ram create-policy \
  --policy-name AliyunDomainQueryAccess \
  --policy-document '{"Version":"1","Statement":[{"Effect":"Allow","Action":["domain:QueryDomainList","domain:QueryAdvancedDomainList","domain:QueryDomainByDomainName","domain:QueryDomainByInstanceId"],"Resource":"*"}]}' \
  --description "Read-only access for domain query operations"

aliyun ram attach-policy-to-user \
  --policy-type Custom \
  --policy-name AliyunDomainQueryAccess \
  --user-name <username>
```

## Alternative: Use System Policy

If the user already has `AliyunDomainFullAccess` or `AliyunDomainReadOnlyAccess` attached, no additional custom policy is needed.

## Permission Verification

```bash
aliyun domain query-domain-list \
  --api-version 2018-01-29 \
  --page-num 1 \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

If the command returns successfully (even with an empty list), permissions are correctly configured.
