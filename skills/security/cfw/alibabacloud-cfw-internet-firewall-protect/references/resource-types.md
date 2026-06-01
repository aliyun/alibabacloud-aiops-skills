# Resource Types

Valid resource types for Cloud Firewall Internet Firewall.
Source: `DescribeResourceTypeAutoEnable` API + `DescribeAssetList` query results.

## Query API (DescribeAssetList)

| ResourceType | Description |
|---|---|
| `AiGatewayEIP` | AI Gateway EIP |
| `AiGatewayEIPv6` | AI Gateway IPv6 EIP |
| `AlbEIP` | ALB EIP |
| `AlbIPv6` | ALB IPv6 address |
| `ApiGatewayEIP` | API Gateway EIP |
| `ApiGatewayEIPv6` | API Gateway IPv6 EIP |
| `BastionHostAll` | All Bastion Host IPs (query-only aggregate type) |
| `BastionHostEgressIP` | Bastion Host egress IP |
| `BastionHostIngressIP` | Bastion Host ingress IP |
| `EIP` | Elastic IP address |
| `EcdEIP` | Elastic Cloud Desktop (ECD) EIP |
| `EcsEIP` | ECS Elastic IP |
| `EcsIPv6` | ECS IPv6 address |
| `EcsPublicIP` | ECS public IP |
| `EniEIP` | ENI Elastic IP |
| `EniEIPv6` | ENI IPv6 EIP |
| `GaEIP` | Global Accelerator EIP |
| `GaEIPV6` | Global Accelerator IPv6 EIP |
| `HAVIP` | High-availability virtual IP |
| `NatEIP` | NAT Gateway EIP |
| `NatPublicIP` | NAT Gateway public IP |
| `NlbEIP` | NLB EIP |
| `NlbIPv6` | NLB IPv6 address |
| `SlbEIP` | CLB (SLB) EIP |
| `SlbIPv6` | CLB IPv6 address |
| `SlbPublicIP` | CLB (SLB) public IP |
| `SwasEIP` | Simple Application Server (SWAS) EIP |

> **Note:** `BastionHostAll` is a query-only aggregate type that returns all Bastion Host IPs (both ingress and egress). It is NOT accepted by the write API or auto-protect API.

## Write API (PutEnableFwSwitch / PutDisableFwSwitch)

The ResourceTypeList parameter uses slightly different names for bastion host:

| ResourceType | Description |
|---|---|
| `BastionHostIP` | Bastion Host egress IP (note: different from query API's `BastionHostEgressIP`) |
| `BastionHostIngressIP` | Bastion Host ingress IP |
| All other types | Same as Query API |

> **Note:** When enabling/disabling protection, use `BastionHostIP` (not `BastionHostEgressIP`). The query API returns `BastionHostEgressIP`, but the write API expects `BastionHostIP`.

## Auto-Protect API (ModifyResourceTypeAutoEnable)

All 27 types from `DescribeResourceTypeAutoEnable` are accepted (excluding `BastionHostAll`):

| ResourceType | Description |
|---|---|
| `AiGatewayEIP` | AI Gateway EIP |
| `AiGatewayEIPv6` | AI Gateway IPv6 EIP |
| `AlbEIP` | ALB EIP |
| `AlbIPv6` | ALB IPv6 address |
| `ApiGatewayEIP` | API Gateway EIP |
| `ApiGatewayEIPv6` | API Gateway IPv6 EIP |
| `BastionHostEgressIP` | Bastion Host egress IP |
| `BastionHostIngressIP` | Bastion Host ingress IP |
| `BastionHostIP` | Bastion Host IP |
| `EIP` | Elastic IP address |
| `EcdEIP` | Elastic Cloud Desktop (ECD) EIP |
| `EcsEIP` | ECS Elastic IP |
| `EcsIPv6` | ECS IPv6 address |
| `EcsPublicIP` | ECS public IP |
| `EniEIP` | ENI Elastic IP |
| `EniEIPv6` | ENI IPv6 EIP |
| `GaEIP` | Global Accelerator EIP |
| `GaEIPV6` | Global Accelerator IPv6 EIP |
| `HAVIP` | High-availability virtual IP |
| `NatEIP` | NAT Gateway EIP |
| `NatPublicIP` | NAT Gateway public IP |
| `NlbEIP` | NLB EIP |
| `NlbIPv6` | NLB IPv6 address |
| `SlbEIP` | CLB (SLB) EIP |
| `SlbIPv6` | CLB IPv6 address |
| `SlbPublicIP` | CLB (SLB) public IP |
| `SwasEIP` | Simple Application Server (SWAS) EIP |
