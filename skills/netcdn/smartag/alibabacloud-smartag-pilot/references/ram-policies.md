# RAM Policies

Required RAM permissions for alibabacloud-sag-pilot skill. All operations are read-only (Describe/List actions only).

## Required Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "smartag:DescribeSmartAccessGateways",
        "smartag:DescribeSmartAccessGatewayAttribute",
        "smartag:DescribeSAGDeviceInfo",
        "smartag:DescribeSmartAccessGatewayVersions",
        "smartag:DescribeSagWanList",
        "smartag:DescribeSagWan4G",
        "smartag:DescribeSagStaticRouteList",
        "smartag:DescribeSagRouteList",
        "smartag:DescribeSagRouteProtocolBgp",
        "smartag:DescribeSagRouteProtocolOspf",
        "smartag:DescribeSagGlobalRouteProtocol",
        "smartag:DescribeCloudConnectNetworks",
        "smartag:DescribeGrantSagRules",
        "smartag:DescribeSagVbrRelations",
        "smartag:DescribeACLs",
        "smartag:DescribeACLAttribute",
        "smartag:DescribeQoses",
        "smartag:DescribeDnatEntries",
        "smartag:DescribeSnatEntries",
        "smartag:DescribeFlowLogs",
        "smartag:DescribeHealthChecks",
        "smartag:DescribeHealthCheckAttribute",
        "smartag:DescribeSmartAccessGatewayClientUsers",
        "smartag:DescribeSagOnlineClientStatistics",
        "smartag:DescribeSagCurrentDns",
        "smartag:DescribeSmartAccessGatewayHa",
        "smartag:DescribeSagTrafficTopN",
        "smartag:ViewSmartAccessGatewayRoutes"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Scope

- **Access level**: Read-only
- **Service**: Smart Access Gateway (smartag)
- **Resource scope**: All SAG resources under the authorized account
- **No write/modify/delete permissions** are required by this skill

## Minimum Permission Policy Name Suggestion

`AliyunSmartAGReadOnlyAccess`

If this managed policy is not available, create a custom policy with the JSON above.
