# Identity Resolver — API Commands

## Identity Resolver Reference

### Credential Configuration Comparison

| Branch | Profile Mode | Credential Type | Trigger Condition |
|--------|-------------|----------------|-------------------|
| A: Local AK | AK | Long-term AccessKey | No service-level credentials |
| B: Role Assumption | RamRoleArn | Auto-refreshed temp credentials | Service AK + User ID available |

### Environment Variables for Branch Detection

| Variable | Description | Purpose |
|----------|-------------|---------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | Platform-injected AK | Create temporary profile if found |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | Platform-injected SK | Same as above |
| `ALIBABA_CLOUD_SERVICE_ACCESS_KEY_ID` | Agent service-level AK | Determine role assumption branch |
| `ALIBABA_CLOUD_SERVICE_ACCESS_KEY_SECRET` | Agent service-level SK | Same as above |
| `CURRENT_USER_ID` | Platform-injected user ID | Construct target role ARN |

### Role ARN Construction

```
acs:ram::{{CURRENT_USER_ID}}:role/cert-operator
```

Role trust policy:
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Principal": { "Service": ["aideepsign.aliyuncs.com"] }
  }]
}
```

### GetCallerIdentity Response

| Field | Description | Example |
|-------|-------------|---------|
| `AccountId` | Alibaba Cloud main account UID | `"1234567890"` |
| `Arn` | Current identity ARN | `"acs:ram::123456:root"` or `"acs:ram::123456:user/alice"` |
| `Type` | Identity type | `Account` / `RAMUser` / `AssumedRoleUser` |

### RAM Policies for cert-operator Role

| Policy Name | Coverage | Necessity |
|-------------|----------|-----------|
| `AliyunYundunCertFullAccess` | `cas:*` full certificate service access | Convenience (quick trial only) |
| `AliyunDNSFullAccess` | `alidns:*` DNS operations (TXT record auto-add) | Convenience (quick trial only) |

> **Least privilege (recommended for production):** skip the broad system policies above and attach the [Fine-Grained Custom Policy](#fine-grained-custom-policy-alternative) at the bottom of this file instead.

### Environment Variables Output

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| `ALIYUN_CMD` | `/opt/homebrew/bin/aliyun` | Full CLI path |
| `CERT_PROFILE` | `cert-operator` | `--profile` parameter for all skills |
| `CERT_ACCOUNT_ID` | `1234567890` | Logging and permission verification |
| `CERT_REGION` | `cn-hangzhou` | `--region` parameter for all skills |

### CLI Installation

| System | Command |
|--------|---------|
| macOS | `brew install aliyun-cli` |
| Linux (x64) | Download official binary package |
| Verification | `aliyun version` |

---

## Identity Resolver — CLI Detection Detail

Three-level probing for aliyun CLI:

**Level 1:** `aliyun version 2>/dev/null` → Set `ALIYUN_CMD="aliyun"`

**Level 2:** Search common paths:
```bash
for p in /opt/homebrew/bin/aliyun /usr/local/bin/aliyun "$HOME/.local/bin/aliyun" /opt/pmk/env/global/bin/aliyun; do
  [ -x "$p" ] && echo "FOUND:$p" && break
done
```

**Level 3:** Full search: `find /usr /opt "$HOME" -name "aliyun" -type f -perm +111 2>/dev/null | head -3`

**All failed** → `brew install aliyun-cli` or https://help.aliyun.com/document_detail/139508.html

## Identity Resolver — Role Creation Commands

### Check Role Existence

```bash
$ALIYUN_CMD ram get-role --role-name cert-operator --profile {{profile_name}} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

### Create Role

```bash
$ALIYUN_CMD ram create-role \
  --role-name cert-operator \
  --description "SSL certificate automation operations role" \
  --assume-role-policy-document '{"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":["aideepsign.aliyuncs.com"]}}],"Version":"1"}' \
  --max-session-duration 3600 --profile {{profile_name}} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

### Attach Permission Policies

> Quick-trial convenience path (broad `cas:*` / `alidns:*` access). For least privilege, create and attach the Fine-Grained Custom Policy (below) instead.

```bash
$ALIYUN_CMD ram attach-policy-to-role --policy-type System --policy-name AliyunYundunCertFullAccess --role-name cert-operator --profile {{profile_name}} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
$ALIYUN_CMD ram attach-policy-to-role --policy-type System --policy-name AliyunDNSFullAccess --role-name cert-operator --profile {{profile_name}} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

### Trust Policy JSON

```json
{
  "Statement": [{
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Principal": { "Service": ["aideepsign.aliyuncs.com"] }
  }],
  "Version": "1"
}
```

### Fine-Grained Custom Policy (Alternative)

> This policy covers exactly the CAS/RAM/STS/Alidns permissions required by this skill — nothing beyond its own workflows.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cas:ListInstances",
        "cas:GetInstanceDetail",
        "cas:UpdateInstance",
        "cas:ApplyCertificate",
        "cas:GetTaskAttribute",
        "cas:UploadUserCertificate",
        "cas:ListCertificates",
        "cas:ListContact"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ram:GetRole",
        "ram:CreateRole",
        "ram:AttachPolicyToRole",
        "ram:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "alidns:AddDomainRecord",
        "alidns:DescribeDomainRecords",
        "alidns:DescribeDomains"
      ],
      "Resource": "*"
    }
  ]
}
```

---

