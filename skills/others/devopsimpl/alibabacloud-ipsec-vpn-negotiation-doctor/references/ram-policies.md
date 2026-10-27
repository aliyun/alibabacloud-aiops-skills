# RAM Policy Declarations

This Skill only calls read-only (Describe) Alibaba Cloud OpenAPI. The following RAM permissions are required:

## Required Permissions

| Permission | Service | Action | Description |
|------------|---------|--------|-------------|
| VPN Connection Query | VPC | `vpc:DescribeVpnConnection` | Query VPN connection status, IKE/IPSec config, tunnel info |
| VPN Negotiation Logs | VPC | `vpc:DescribeVpnConnectionLogs` | Query IPSec tunnel negotiation logs for diagnosis |

## Minimum RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpnConnection",
        "vpc:DescribeVpnConnectionLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- All operations are **read-only**. No write permissions are required or requested.
- Resource scope can be restricted to specific VPN connection ARNs for tighter security:
  `acs:vpc:{region}:{account-id}:vpnconnection/{vpn-connection-id}`
