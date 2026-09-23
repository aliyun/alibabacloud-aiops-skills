# Resource Types

Valid resource types for Cloud Firewall Internet Firewall.
Source: `DescribeResourceTypeAutoEnable` API + `DescribeAssetList` query results,
cross-checked against `aliyun Cloudfw <action> --help`.

The CLI's own `--help` enum for `DescribeAssetList.ResourceType` is a shorter list than
what the API actually returns: it omits the `*IPv6` variants and `BastionHostAll`, and it
lists both `BastionHostEgressIP` and `BastionHostIP`. The tables below follow the observed
API behaviour, which is the authority for what a filter value actually matches — treat the
CLI help enum as a lower bound, not as the full set.

## Mapping User Wording to Filter Values

Users may name products with informal wording, while the filters accept only the
exact values listed in this file. `validate_resource_type` compares
case-sensitively against a fixed allowlist, so a plausible-looking value is
rejected rather than corrected. Resolve the product name before building a command.

The following reference data maps common user phrases to the API values:

```text
"ECS 公网IP" / "ECS 固定公网 IP"       -> EcsPublicIP
"ECS 弹性公网 IP" / "ECS EIP"          -> EcsEIP
"EIP" / "弹性公网 IP"                  -> EIP
"NAT 网关" / "NAT EIP"                 -> NatEIP (EIP form) or NatPublicIP (public IP form)
"负载均衡" / "SLB" / "CLB 公网IP"      -> SlbPublicIP (public IP form) or SlbEIP (EIP form)
"应用型负载均衡" / "ALB"                -> AlbEIP
"网络型负载均衡" / "NLB"                -> NlbEIP
"IPv6 地址"                              -> the *IPv6 variant of the matching product
```

> When the user says a product name without specifying the address class ("所有负载均衡的公网IP"),
> both the `*PublicIP` and the `*EIP` form can apply. Query both and report what exists rather than
> picking one silently — a wrong guess returns an empty set that reads as "no assets to protect".

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

All 28 types from `DescribeResourceTypeAutoEnable` are accepted (excluding `BastionHostAll`):

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
| `VpnEIP` | VPN Gateway EIP |

> **Note:** `VpnEIP` is an auto-protect-only type. It is returned by `DescribeResourceTypeAutoEnable` but is NOT a valid `--resource-type` filter for the `DescribeAssetList` query API.
