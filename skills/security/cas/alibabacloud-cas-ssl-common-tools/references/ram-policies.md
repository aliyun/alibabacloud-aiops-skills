# RAM Policies — SSL Certificate Tools

## Required Permissions

### CAS (Certificate Authority Service)

| Action | Description | Required |
|--------|-------------|----------|
| `cas:ListInstances` | List certificate instances | Yes |
| `cas:GetInstanceDetail` | Get instance detail (new API) | Yes |
| `cas:UpdateInstance` | Fill in application info | Conditional |
| `cas:ApplyCertificate` | Submit certificate application | Conditional |
| `cas:GetTaskAttribute` | Poll async task result | Conditional |
| `cas:UploadUserCertificate` | Upload third-party certificate | Upload tool |
| `cas:ListCertificates` | List uploaded certificates | Upload tool |
| `cas:ListContact` | List contacts | Conditional |

### RAM (Resource Access Management)

| Action | Description | Required |
|--------|-------------|----------|
| `ram:GetRole` | Check role existence | Identity resolver |
| `ram:CreateRole` | Create cert-operator role | Identity resolver |
| `ram:AttachPolicyToRole` | Attach permission policies | Identity resolver |
| `ram:GetCallerIdentity` | Get current identity info | Identity resolver |

### STS (Security Token Service)

| Action | Description | Required |
|--------|-------------|----------|
| `sts:GetCallerIdentity` | Get current identity info | Identity resolver |

### DNS (Alibaba Cloud DNS)

| Action | Description | Required |
|--------|-------------|----------|
| `alidns:AddDomainRecord` | Add DNS TXT record for verification | Domain verify |
| `alidns:DescribeDomainRecords` | Check existing DNS records | Domain verify |
| `alidns:DescribeDomains` | List domains | Domain verify |

## System Policies (Convenience — Quick Trials Only)

> These system policies grant broad `cas:*` / `alidns:*` access. Accept them only for quick trials; for production, always use the fine-grained custom policy below (least privilege).

| Policy Name | Coverage |
|-------------|----------|
| `AliyunYundunCertFullAccess` | Full CAS API access |
| `AliyunDNSFullAccess` | DNS operations (TXT record auto-add) |

## Fine-Grained Custom Policy (Recommended — Least Privilege)

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
