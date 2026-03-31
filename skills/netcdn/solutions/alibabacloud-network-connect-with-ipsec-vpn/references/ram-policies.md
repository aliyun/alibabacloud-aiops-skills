# RAM Policies

RAM permission requirements for all API operations involved in this scenario.

## Minimal Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeRegions",
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:DescribeRouteTableList",
        "vpc:CreateRouteEntry",
        "vpc:DescribeRouteEntryList",
        "vpc:CreateVpnGateway",
        "vpc:DescribeVpnGateway",
        "vpc:DescribeVpnGateways",
        "vpc:DeleteVpnGateway",
        "vpc:CreateCustomerGateway",
        "vpc:DescribeCustomerGateways",
        "vpc:DeleteCustomerGateway",
        "vpc:CreateVpnConnection",
        "vpc:DescribeVpnConnections",
        "vpc:DescribeVpnConnection",
        "vpc:DeleteVpnConnection",
        "vpc:DescribeVpnConnectionLogs",
        "vpc:DiagnoseVpnConnections",
        "vpc:DiagnoseVpnGateway"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Descriptions

| API Action | Description | Usage |
|-----------|-------------|-------|
| `ecs:DescribeRegions` | Query region list | Parameter collection: Select region |
| `vpc:DescribeVpcs` | Query VPC list | Parameter collection: Select VPC |
| `vpc:DescribeVSwitches` | Query VSwitch list | Parameter collection: Select VSwitch |
| `vpc:DescribeRouteTableList` | Query route table list | Step 4: Add VPC routes |
| `vpc:CreateRouteEntry` | Create route entry | Step 4: Add VPN routes |
| `vpc:DescribeRouteEntryList` | Query route entry list | Step 4: Verify routes |
| `vpc:CreateVpnGateway` | Create VPN gateway | Step 1: Create VPN gateway |
| `vpc:DescribeVpnGateway` | Query VPN gateway details | Step 1: Query VPN gateway status and public IPs |
| `vpc:DescribeVpnGateways` | Query VPN gateway list | Step 1: Query VPN gateway list |
| `vpc:DeleteVpnGateway` | Delete VPN gateway | Cleanup: Delete VPN gateway |
| `vpc:CreateCustomerGateway` | Create customer gateway | Step 2: Create customer gateway |
| `vpc:DescribeCustomerGateways` | Query customer gateway list | Step 2: Query customer gateway |
| `vpc:DeleteCustomerGateway` | Delete customer gateway | Cleanup: Delete customer gateway |
| `vpc:CreateVpnConnection` | Create IPsec connection | Step 3: Create IPsec connection |
| `vpc:DescribeVpnConnections` | Query IPsec connection list | Step 3/Verification: Query IPsec connection status |
| `vpc:DescribeVpnConnection` | Query IPsec connection details | Verification: Query IPsec connection configuration |
| `vpc:ModifyVpnConnectionAttribute` | Modify IPsec connection | Modify IPsec connection configuration |
| `vpc:DeleteVpnConnection` | Delete IPsec connection | Cleanup: Delete IPsec connection |
| `vpc:DownloadVpnConnectionConfig` | Download IPsec connection config | Get peer configuration |
| `vpc:DescribeVpnConnectionLogs` | Query IPsec connection logs | Diagnostic troubleshooting |
| `vpc:DiagnoseVpnConnections` | Diagnose IPsec connection | Diagnostic troubleshooting |
| `vpc:DiagnoseVpnGateway` | Diagnose VPN gateway | Diagnostic troubleshooting |

## Important Notes

- Above is minimal permission policy, recommend restricting `Resource` field to specific resource ARNs in production environments
- If creating VPC/VSwitch and other network resources required, additional `vpc:CreateVpc`, `vpc:CreateVSwitch`, etc. permissions needed
- VPN Gateway is PrePay (PREPAY) resource; creation requires corresponding payment permissions
