# RAM Policies — SSL Certificate Deployment

## Required Permissions

### CAS (Certificate Authority Service)

| Action | Description | Required |
|--------|-------------|----------|
| `cas:CreateDeploymentJob` | Create deployment job | Yes |
| `cas:UpdateDeploymentJobStatus` | Start/modify deployment job state | Yes |
| `cas:DescribeDeploymentJobStatus` | Query deployment execution stats | Yes |
| `cas:DescribeDeploymentJob` | Query deployment job details | Yes |
| `cas:ListDeploymentJob` | List deployment jobs | Yes |
| `cas:DeleteDeploymentJob` | Delete deployment job | Conditional |
| `cas:UpdateDeploymentJob` | Update deployment job config | Conditional |
| `cas:ListCloudResources` | List cloud product resources | Yes |
| `cas:ListWorkerResource` | List sub-task workers | Yes |
| `cas:UpdateWorkerResourceStatus` | Rollback sub-task | Conditional |
| `cas:ListDeploymentJobCert` | List certs in deployment job | Conditional |
| `cas:ListDeploymentJobResource` | List resources in deployment job | Conditional |
| `cas:ListUserCertificateOrder` | List user certificate orders | Yes |
| `cas:GetUserCertificateDetail` | Get certificate detail (domain info, Step 1) | Yes |
| `cas:GetInstanceDetail` | Resolve InstanceId to CertId (Step 1 Case B) | Yes |
| `cas:ListContact` | List contacts | Yes |

### CDN

| Action | Description | Required |
|--------|-------------|----------|
| `cdn:DescribeUserDomains` | List CDN domains | CDN helper |
| `cdn:AddCdnDomain` | Create CDN acceleration domain | CDN helper |
| `cdn:DescribeCdnDomainDetail` | Poll CDN domain status | CDN helper |
| `cdn:SetCdnDomainSSLCertificate` | Deploy cert to CDN | CDN helper |
| `cdn:DescribeDomainCertificateInfo` | Verify CDN cert status | CDN helper |

### WAF 3.0

| Action | Description | Required |
|--------|-------------|----------|
| `waf:DescribeInstance` | Get WAF instance | WAF helper |
| `waf:CreateDomain` | Onboard domain to WAF | WAF helper |

### OSS

| Action | Description | Required |
|--------|-------------|----------|
| `oss:CreateCnameToken` | Domain ownership verification | OSS helper |
| `oss:PutBucketCname` | Bind custom domain with cert | OSS helper |

### ALB / NLB / SLB

| Action | Description | Required |
|--------|-------------|----------|
| `alb:CreateListener` | Create HTTPS listener | ALB helper |
| `alb:ListListeners` | List listeners | ALB helper |
| `alb:UpdateListenerAttribute` | Update listener cert | ALB helper |
| `alb:ListServerGroups` | List server groups | ALB helper |
| `alb:AddServersToServerGroup` | Add backend servers | ALB helper |

## Recommended System Policies

| Policy Name | Coverage |
|-------------|----------|
| `AliyunYundunCertFullAccess` | Full CAS API access (deployment jobs) |
| `AliyunCDNFullAccess` | CDN domain management |
| `AliyunWAF2FullAccess` | WAF 3.0 domain management |
| `AliyunOSSFullAccess` | OSS bucket and CNAME management |
| `AliyunALBFullAccess` | ALB listener and server group management |

## Fine-Grained Custom Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cas:CreateDeploymentJob",
        "cas:UpdateDeploymentJobStatus",
        "cas:DescribeDeploymentJobStatus",
        "cas:DescribeDeploymentJob",
        "cas:ListDeploymentJob",
        "cas:DeleteDeploymentJob",
        "cas:UpdateDeploymentJob",
        "cas:ListCloudResources",
        "cas:ListWorkerResource",
        "cas:UpdateWorkerResourceStatus",
        "cas:ListDeploymentJobCert",
        "cas:ListDeploymentJobResource",
        "cas:ListUserCertificateOrder",
        "cas:ListContact"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cdn:DescribeUserDomains",
        "cdn:AddCdnDomain",
        "cdn:DescribeCdnDomainDetail",
        "cdn:SetCdnDomainSSLCertificate",
        "cdn:DescribeDomainCertificateInfo"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "waf:DescribeInstance",
        "waf:CreateDomain"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:CreateCnameToken",
        "oss:PutBucketCname"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "alb:CreateListener",
        "alb:ListListeners",
        "alb:UpdateListenerAttribute",
        "alb:ListServerGroups",
        "alb:AddServersToServerGroup"
      ],
      "Resource": "*"
    }
  ]
}
```
