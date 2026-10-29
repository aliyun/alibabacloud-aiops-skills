# Required RAM Permissions

This skill interacts with Alibaba Cloud Global Accelerator (GA) and several dependent services. Apply the principle of least privilege: attach only the permissions required for the specific task the user wants to perform.

> **No wildcard actions**: Per policy requirements, every Action below is declared explicitly. Each statement lists only the actions that the commands and procedures documented in this skill actually use; no wildcard patterns are used.

## Core GA Permissions (Required)

The following custom policy covers Standard and Basic GA lifecycle management (create, describe, update, bind, ACL, certificate, forwarding rule, application monitor, tagging, log delivery, cross-border status).

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ga:AddEntriesToAcl",
        "ga:AssociateAclsWithListener",
        "ga:AssociateAdditionalCertificatesWithListener",
        "ga:AttachLogStoreToEndpointGroup",
        "ga:BandwidthPackageAddAccelerator",
        "ga:BandwidthPackageRemoveAccelerator",
        "ga:BindBandwidthPackage",
        "ga:CreateAccelerator",
        "ga:CreateAcl",
        "ga:CreateApplicationMonitor",
        "ga:CreateBandwidthPackage",
        "ga:CreateBasicAccelerateIp",
        "ga:CreateBasicAccelerateIpEndpointRelation",
        "ga:CreateBasicAccelerator",
        "ga:CreateBasicEndpoint",
        "ga:CreateBasicEndpointGroup",
        "ga:CreateBasicEndpoints",
        "ga:CreateBasicIpSet",
        "ga:CreateEndpointGroup",
        "ga:CreateEndpointGroups",
        "ga:CreateForwardingRules",
        "ga:CreateIpSets",
        "ga:CreateListener",
        "ga:DescribeAccelerator",
        "ga:DescribeAcceleratorAutoRenewAttribute",
        "ga:DescribeAcceleratorServiceStatus",
        "ga:DescribeBandwidthPackage",
        "ga:DescribeEndpointGroup",
        "ga:DescribeIpSet",
        "ga:DescribeListener",
        "ga:DescribeLogStoreOfEndpointGroup",
        "ga:DescribePricing",
        "ga:DetectApplicationMonitor",
        "ga:DissociateAclsFromListener",
        "ga:DissociateAdditionalCertificatesFromListener",
        "ga:GetAcl",
        "ga:GetApplicationMonitor",
        "ga:GetBasicAccelerateIp",
        "ga:GetBasicAccelerateIpEndpointRelation",
        "ga:GetBasicAccelerator",
        "ga:GetBasicEndpoint",
        "ga:GetBasicEndpointGroup",
        "ga:GetBasicIpSet",
        "ga:GetForwardingRule",
        "ga:GetHealthStatus",
        "ga:GetIpsetsBandwidthLimit",
        "ga:ListAccelerateAreas",
        "ga:ListAccelerators",
        "ga:ListAcls",
        "ga:ListApplicationMonitor",
        "ga:ListApplicationMonitorDetectResult",
        "ga:ListApplicationMonitors",
        "ga:ListAvailableAccelerateAreas",
        "ga:ListBandwidthPackages",
        "ga:ListBasicAccelerateIpEndpointRelations",
        "ga:ListBasicAccelerateIps",
        "ga:ListBasicAccelerators",
        "ga:ListBasicEndpoints",
        "ga:ListEndpointGroups",
        "ga:ListForwardingRules",
        "ga:ListIpSets",
        "ga:ListIspTypes",
        "ga:ListListenerCertificates",
        "ga:ListListeners",
        "ga:ListSystemSecurityPolicies",
        "ga:ListTagResources",
        "ga:OpenAcceleratorService",
        "ga:QueryCrossBorderApprovalStatus",
        "ga:RemoveEntriesFromAcl",
        "ga:ReplaceBandwidthPackage",
        "ga:TagResources",
        "ga:UntagResources",
        "ga:UpdateAccelerator",
        "ga:UpdateAcceleratorConfirm",
        "ga:UpdateAcceleratorCrossBorderStatus",
        "ga:UpdateAclAttribute",
        "ga:UpdateAdditionalCertificateWithListener",
        "ga:UpdateApplicationMonitor",
        "ga:UpdateBandwidthPackage",
        "ga:UpdateBasicAccelerator",
        "ga:UpdateBasicEndpoint",
        "ga:UpdateBasicEndpointGroup",
        "ga:UpdateBasicIpSet",
        "ga:UpdateEndpointGroup",
        "ga:UpdateEndpointGroupAttribute",
        "ga:UpdateEndpointGroups",
        "ga:UpdateForwardingRuleAttribute",
        "ga:UpdateIpSet",
        "ga:UpdateIpSets",
        "ga:UpdateListener"
      ],
      "Resource": "*"
    }
  ]
}
```

**Usage notes (grouped by feature):**

- **Accelerator lifecycle** — `CreateAccelerator`, `DescribeAccelerator`, `ListAccelerators`, `UpdateAccelerator`, `UpdateAcceleratorConfirm`, `OpenAcceleratorService`, `DescribeAcceleratorServiceStatus`, `DescribeAcceleratorAutoRenewAttribute` deploy and inspect GA instances.
- **Bandwidth packages** — `CreateBandwidthPackage`, `DescribeBandwidthPackage`, `ListBandwidthPackages`, `UpdateBandwidthPackage`, `ReplaceBandwidthPackage`, `BandwidthPackageAddAccelerator`, `BandwidthPackageRemoveAccelerator`, `BindBandwidthPackage` manage packages and their binding to accelerators.
- **Acceleration regions** — `ListAccelerateAreas`, `ListAvailableAccelerateAreas`, `ListIspTypes`, `CreateIpSets`, `ListIpSets`, `DescribeIpSet`, `UpdateIpSet`, `UpdateIpSets`, `GetIpsetsBandwidthLimit` allocate and tune acceleration regions.
- **Listeners and certificates** — `CreateListener`, `DescribeListener`, `ListListeners`, `UpdateListener`, `ListSystemSecurityPolicies`, `ListListenerCertificates`, `AssociateAdditionalCertificatesWithListener`, `DissociateAdditionalCertificatesFromListener`, `UpdateAdditionalCertificateWithListener` manage listeners and HTTPS certificates.
- **Endpoint groups and endpoints** — `CreateEndpointGroup(s)`, `DescribeEndpointGroup`, `ListEndpointGroups`, `UpdateEndpointGroup(s)`, `UpdateEndpointGroupAttribute` plus all `*Basic*` actions manage routing targets.
- **ACLs and forwarding rules** — `CreateAcl`, `ListAcls`, `GetAcl`, `AddEntriesToAcl`, `RemoveEntriesFromAcl`, `UpdateAclAttribute`, `AssociateAclsWithListener`, `DissociateAclsFromListener`, `CreateForwardingRules`, `ListForwardingRules`, `GetForwardingRule`, `UpdateForwardingRuleAttribute` control access and layer-7 routing.
- **Health and diagnostics** — `GetHealthStatus`, `DetectApplicationMonitor` and the application-monitor query actions pinpoint unhealthy endpoints.
- **Cross-border compliance** — `QueryCrossBorderApprovalStatus` checks the approval state and `UpdateAcceleratorCrossBorderStatus` enables cross-border service; the current cross-border status is read from the `CrossBorderStatus` field returned by `DescribeAccelerator`.
- **Tagging and logging** — `TagResources`, `UntagResources`, `ListTagResources` manage tags, while `AttachLogStoreToEndpointGroup` and `DescribeLogStoreOfEndpointGroup` bind and inspect SLS access-log delivery.
- **Pricing** — `DescribePricing` supports cost estimation.

## Optional Dependent Service Permissions

Add these statements only when the corresponding feature is used.

### Backend Resource Auto-Discovery

```json
{
  "Effect": "Allow",
  "Action": [
    "ecs:DescribeInstances",
    "ecs:DescribeNetworkInterfaces",
    "nlb:ListLoadBalancers",
    "slb:DescribeLoadBalancerAttribute",
    "slb:DescribeLoadBalancers"
  ],
  "Resource": "*"
}
```

### SSL Certificate Discovery

```json
{
  "Effect": "Allow",
  "Action": [
    "cas:ListCertificates",
    "cas:ListUserCertificateOrder"
  ],
  "Resource": "*"
}
```

### CloudMonitor Metrics and Alarms

```json
{
  "Effect": "Allow",
  "Action": [
    "cms:CreateMetricRuleTemplate",
    "cms:DescribeMetricList",
    "cms:DescribeMetricLast",
    "cms:DescribeMetricRuleList",
    "cms:PutResourceMetricRule"
  ],
  "Resource": "*"
}
```

### Billing and Cost Estimation

```json
{
  "Effect": "Allow",
  "Action": [
    "bssopenapi:QueryProductList",
    "bssopenapi:QueryInstanceBill",
    "bssopenapi:QueryBillOverview"
  ],
  "Resource": "*"
}
```

### Log Delivery to SLS

```json
{
  "Effect": "Allow",
  "Action": [
    "log:CreateLogStore",
    "log:CreateProject"
  ],
  "Resource": "*"
}
```

### STS Identity Check

`aliyun sts get-caller-identity` is used to verify credentials at the start of a session. Run it once so an invalid or expired credential surfaces before any GA call is attempted.

```json
{
  "Effect": "Allow",
  "Action": [
    "sts:GetCallerIdentity"
  ],
  "Resource": "*"
}
```

## Not Recommended: Full Access

For testing only, you can use `AliyunGAFullAccess`. Do **not** use it in production because it grants far more permissions than necessary.
