# RAM Policies — SSL Certificate Purchase

## Required Permissions

### CAS (Certificate Authority Service)

| Action | Description | Required |
|--------|-------------|----------|
| `cas:ListInstances` | List certificate instances | Yes |
| `cas:GetInstanceDetail` | Get instance detail (new API) | Yes |
| `cas:UpdateInstance` | Fill in application info (DV/OV/EV) | Yes |
| `cas:ApplyCertificate` | Submit certificate application | Yes |
| `cas:GetTaskAttribute` | Poll async application result | Yes |
| `cas:ListContact` | List contacts for application | Yes |

### BSS (Business Support System)

| Action | Description | Required |
|--------|-------------|----------|
| `bssopenapi:CreateInstance` | Purchase certificate instance | Yes (paid certs) |
| `bssopenapi:QueryProductList` | Verify BSS plugin availability (check-plugin) | Conditional |
| `bssopenapi:GetOrderDetail` | Query order detail after purchase | Conditional |

## Recommended System Policies

| Policy Name | Coverage |
|-------------|----------|
| `AliyunYundunCertFullAccess` | Full CAS API access |
| `AliyunBSSFullAccess` | BSS billing and purchase operations |

## Fine-Grained Custom Policy

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
        "cas:ListContact"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bssopenapi:CreateInstance",
        "bssopenapi:QueryProductList",
        "bssopenapi:GetOrderDetail"
      ],
      "Resource": "*"
    }
  ]
}
```
