# Related APIs and CLI Commands

## VPN Gateway

| Product | CLI Command | API Action | Description |
|---------|------------|------------|-------------|
| VPC | `aliyun vpc create-vpn-gateway` | CreateVpnGateway | Create VPN gateway |
| VPC | `aliyun vpc describe-vpn-gateway` | DescribeVpnGateway | Query specified VPN gateway details |
| VPC | `aliyun vpc describe-vpn-gateways` | DescribeVpnGateways | Query VPN gateway list |
| VPC | `aliyun vpc delete-vpn-gateway` | DeleteVpnGateway | Delete VPN gateway |

## Customer Gateway

| Product | CLI Command | API Action | Description |
|---------|------------|------------|-------------|
| VPC | `aliyun vpc create-customer-gateway` | CreateCustomerGateway | Create customer gateway |
| VPC | `aliyun vpc describe-customer-gateways` | DescribeCustomerGateways | Query customer gateway list |
| VPC | `aliyun vpc delete-customer-gateway` | DeleteCustomerGateway | Delete customer gateway |

## VPN Connection (IPsec)

| Product | CLI Command | API Action | Description |
|---------|------------|------------|-------------|
| VPC | `aliyun vpc create-vpn-connection` | CreateVpnConnection | Create IPsec connection |
| VPC | `aliyun vpc create-vpn-connection` | CreateVpnConnection | Create dual-tunnel IPsec connection (using JSON array format) |
| VPC | `aliyun vpc describe-vpn-connections` | DescribeVpnConnections | Query IPsec connection list |
| VPC | `aliyun vpc describe-vpn-connection` | DescribeVpnConnection | Query specified IPsec connection details |
| VPC | `aliyun vpc modify-vpn-connection-attribute` | ModifyVpnConnectionAttribute | Modify IPsec connection configuration |
| VPC | `aliyun vpc delete-vpn-connection` | DeleteVpnConnection | Delete IPsec connection |
| VPC | `aliyun vpc download-vpn-connection-config` | DownloadVpnConnectionConfig | Download IPsec connection config |

**Note on Dual-Tunnel Creation:**
- Use `--tunnel-options-specification` parameter with JSON array format containing two tunnel configurations
- Each entry specifies Role as either "master" or "slave"
- All parameters use lowercase with hyphens format (plugin mode standard)

## Diagnostics

| Product | CLI Command | API Action | Description |
|---------|------------|------------|-------------|
| VPC | `aliyun vpc describe-vpn-connection-logs` | DescribeVpnConnectionLogs | Query IPsec connection logs |
| VPC | `aliyun vpc diagnose-vpn-connections` | DiagnoseVpnConnections | Diagnose IPsec connection |
| VPC | `aliyun vpc diagnose-vpn-gateway` | DiagnoseVpnGateway | Diagnose VPN gateway |
