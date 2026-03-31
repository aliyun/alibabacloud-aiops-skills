# RAM Permission Policies for GA Deployment

This document lists the RAM permissions required to deploy Global Accelerator services using the `alibabacloud-network-ga-deploy-acceleration` skill.

---

## 1. Least Privilege Policy (Recommended)

For scenarios that only perform GA deployment and operations.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ga:DescribeAcceleratorServiceStatus",
        "ga:OpenAcceleratorService",
        "ga:CreateAccelerator",
        "ga:DescribeAccelerator",
        "ga:UpdateAccelerator",
        "ga:DeleteAccelerator",
        "ga:UpdateAcceleratorCrossBorderStatus",
        "ga:UpdateAcceleratorCrossBorderMode",
        "ga:QueryCrossBorderApprovalStatus",
        "ga:ListAccelerateAreas",
        "ga:CreateIpSets",
        "ga:DescribeIpSets",
        "ga:ListIpSets",
        "ga:UpdateIpSets",
        "ga:DeleteIpSets",
        "ga:CreateListener",
        "ga:DescribeListener",
        "ga:ListListeners",
        "ga:UpdateListener",
        "ga:DeleteListener",
        "ga:CreateEndpointGroup",
        "ga:DescribeEndpointGroup",
        "ga:ListEndpointGroups",
        "ga:UpdateEndpointGroup",
        "ga:DeleteEndpointGroup",
        "ga:GetHealthStatus",
        "ga:CreateForwardingRules",
        "ga:DescribeForwardingRules",
        "ga:ListForwardingRules",
        "ga:UpdateForwardingRules",
        "ga:DeleteForwardingRules"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 2. Read-only Policy

For scenarios that only query GA configurations and status, without creating/modifying/deleting resources.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ga:DescribeAcceleratorServiceStatus",
        "ga:DescribeAccelerator",
        "ga:ListAccelerateAreas",
        "ga:DescribeIpSets",
        "ga:ListIpSets",
        "ga:DescribeListener",
        "ga:ListListeners",
        "ga:DescribeEndpointGroup",
        "ga:ListEndpointGroups",
        "ga:GetHealthStatus",
        "ga:DescribeForwardingRules",
        "ga:ListForwardingRules",
        "ga:QueryCrossBorderApprovalStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 3. Full Operations Policy (Including Related Services)

For scenarios that require full operational capabilities, including certificate queries and monitoring metrics.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ga:DescribeAcceleratorServiceStatus",
        "ga:OpenAcceleratorService",
        "ga:CreateAccelerator",
        "ga:DescribeAccelerator",
        "ga:UpdateAccelerator",
        "ga:DeleteAccelerator",
        "ga:UpdateAcceleratorCrossBorderStatus",
        "ga:UpdateAcceleratorCrossBorderMode",
        "ga:QueryCrossBorderApprovalStatus",
        "ga:ListAccelerateAreas",
        "ga:CreateIpSets",
        "ga:DescribeIpSets",
        "ga:ListIpSets",
        "ga:UpdateIpSets",
        "ga:DeleteIpSets",
        "ga:CreateListener",
        "ga:DescribeListener",
        "ga:ListListeners",
        "ga:UpdateListener",
        "ga:DeleteListener",
        "ga:CreateEndpointGroup",
        "ga:DescribeEndpointGroup",
        "ga:ListEndpointGroups",
        "ga:UpdateEndpointGroup",
        "ga:DeleteEndpointGroup",
        "ga:GetHealthStatus",
        "ga:CreateForwardingRules",
        "ga:DescribeForwardingRules",
        "ga:ListForwardingRules",
        "ga:UpdateForwardingRules",
        "ga:DeleteForwardingRules",
        "cas:ListUserCertificateOrder",
        "cms:DescribeMetricList"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 4. Permission-to-API Mapping

| API Operation | Permission Action | Use Case |
|----------|-------------|----------|
| **Service Management** | | |
| DescribeAcceleratorServiceStatus | ga:DescribeAcceleratorServiceStatus | Query GA service activation status |
| OpenAcceleratorService | ga:OpenAcceleratorService | Activate the Global Accelerator service |
| **Instance Management** | | |
| CreateAccelerator | ga:CreateAccelerator | Create a GA instance |
| DescribeAccelerator | ga:DescribeAccelerator | Query instance details/status |
| UpdateAccelerator | ga:UpdateAccelerator | Update instance configuration |
| DeleteAccelerator | ga:DeleteAccelerator | Delete a GA instance |
| **Cross-border Configuration** | | |
| UpdateAcceleratorCrossBorderStatus | ga:UpdateAcceleratorCrossBorderStatus | Enable/disable cross-border acceleration |
| UpdateAcceleratorCrossBorderMode | ga:UpdateAcceleratorCrossBorderMode | Set cross-border mode |
| QueryCrossBorderApprovalStatus | ga:QueryCrossBorderApprovalStatus | Query cross-border approval status |
| **Acceleration Region** | | |
| ListAccelerateAreas | ga:ListAccelerateAreas | Query supported acceleration regions |
| CreateIpSets | ga:CreateIpSets | Create acceleration regions |
| DescribeIpSets | ga:DescribeIpSets | Query single acceleration region details |
| ListIpSets | ga:ListIpSets | Query acceleration region list |
| UpdateIpSets | ga:UpdateIpSets | Update acceleration region configuration |
| DeleteIpSets | ga:DeleteIpSets | Delete acceleration regions |
| **Listener** | | |
| CreateListener | ga:CreateListener | Create a listener |
| DescribeListener | ga:DescribeListener | Query single listener details |
| ListListeners | ga:ListListeners | Query listener list |
| UpdateListener | ga:UpdateListener | Update listener configuration |
| DeleteListener | ga:DeleteListener | Delete a listener |
| **Endpoint Group** | | |
| CreateEndpointGroup | ga:CreateEndpointGroup | Create an endpoint group |
| DescribeEndpointGroup | ga:DescribeEndpointGroup | Query single endpoint group details |
| ListEndpointGroups | ga:ListEndpointGroups | Query endpoint group list |
| UpdateEndpointGroup | ga:UpdateEndpointGroup | Update endpoint group configuration |
| DeleteEndpointGroup | ga:DeleteEndpointGroup | Delete an endpoint group |
| GetHealthStatus | ga:GetHealthStatus | Query endpoint health status |
| **Forwarding Rules** | | |
| CreateForwardingRules | ga:CreateForwardingRules | Create forwarding rules |
| DescribeForwardingRules | ga:DescribeForwardingRules | Query single forwarding rule details |
| ListForwardingRules | ga:ListForwardingRules | Query forwarding rule list |
| UpdateForwardingRules | ga:UpdateForwardingRules | Update forwarding rules |
| DeleteForwardingRules | ga:DeleteForwardingRules | Delete forwarding rules |
| **Related Services** | | |
| ListUserCertificateOrder | cas:ListUserCertificateOrder | Query SSL certificates (for HTTPS scenarios) |
| DescribeMetricList | cms:DescribeMetricList | Query monitoring metric data |

---

## 5. Custom Policy (Resource-level Authorization)

To restrict access to a specific GA instance, use resource-level authorization:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ga:DescribeAccelerator",
        "ga:ListListeners",
        "ga:ListEndpointGroups"
      ],
      "Resource": "acs:ga:*:*:accelerator/ga-xxxxxxxxx"
    }
  ]
}
```

---

## 6. System Policies

Alibaba Cloud predefined system policies (may have broader scope):

| Policy Name | Description |
|----------|------|
| `AliyunGAFullAccess` | Full management access to Global Accelerator |
| `AliyunGAREADOnlyAccess` | Read-only access to Global Accelerator |

---

## 7. Permission Verification Commands

Use the following commands to verify the permissions of the current identity:

```bash
# Test GA service activation status query permission
aliyun ga DescribeAcceleratorServiceStatus --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# Test basic GA permissions
aliyun ga ListAccelerateAreas --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# Test instance query permission
aliyun ga DescribeAccelerator --AcceleratorId <ga-id> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# Test listener query permission
aliyun ga ListListeners --AcceleratorId <ga-id> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

If a `Forbidden` or `Unauthorized` error is returned, contact your administrator to grant the required permissions.

---

## 8. Related Documentation

- [RAM Policy Syntax](https://help.aliyun.com/zh/ram/user-guide/policy-syntax)
- [GA API Permission Reference](https://help.aliyun.com/zh/ga/developer-reference/api-overview)
- [Alibaba Cloud Access Control](https://ram.console.aliyun.com/)
