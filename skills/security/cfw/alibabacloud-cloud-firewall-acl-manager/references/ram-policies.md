# Required RAM Permissions

This skill calls Alibaba Cloud Cloud Firewall (Cloudfw) OpenAPI via HTTPS.
The RAM identity must be granted the actions below.

## Option A: system policy (simplest)

Attach `AliyunCloudFirewallFullAccess` to the RAM user or role.

## Option B: custom policy (least privilege)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-cloudfirewall:DescribeAddressBook",
        "yundun-cloudfirewall:AddAddressBook",
        "yundun-cloudfirewall:DescribeControlPolicy",
        "yundun-cloudfirewall:AddControlPolicy",
        "yundun-cloudfirewall:ModifyControlPolicy",
        "yundun-cloudfirewall:DescribeNatFirewallControlPolicy",
        "yundun-cloudfirewall:CreateNatFirewallControlPolicy",
        "yundun-cloudfirewall:ModifyNatFirewallControlPolicy",
        "yundun-cloudfirewall:DescribeNatFirewallList",
        "yundun-cloudfirewall:DescribeVpcFirewallControlPolicy",
        "yundun-cloudfirewall:CreateVpcFirewallControlPolicy",
        "yundun-cloudfirewall:ModifyVpcFirewallControlPolicy",
        "yundun-cloudfirewall:DescribeVpcFirewallAclGroupList",
        "yundun-cloudfirewall:DescribeAckClusterConnectors",
        "yundun-cloudfirewall:CreateAckClusterConnector",
        "yundun-cloudfirewall:DescribePrivateDnsEndpointList",
        "yundun-cloudfirewall:DescribePrivateDnsEndpointDetail",
        "yundun-cloudfirewall:DescribePrivateDnsDomainNameList",
        "yundun-cloudfirewall:CreatePrivateDnsEndpoint",
        "yundun-cloudfirewall:AddPrivateDnsDomainName"
      ],
      "Resource": "*"
    }
  ]
}
```

## Action breakdown by capability

### Backup (read-only)

| Action | Purpose |
|--------|---------|
| yundun-cloudfirewall:DescribeAddressBook | Backup address books (custom IP, cloud asset IP, domain, port) |
| yundun-cloudfirewall:DescribeControlPolicy | Backup Internet boundary ACL policies |
| yundun-cloudfirewall:DescribeNatFirewallControlPolicy | Backup NAT boundary ACL policies |
| yundun-cloudfirewall:DescribeNatFirewallList | Enumerate NAT gateways for NAT boundary scope |
| yundun-cloudfirewall:DescribeVpcFirewallControlPolicy | Backup VPC boundary ACL policies |
| yundun-cloudfirewall:DescribeVpcFirewallAclGroupList | Enumerate VPC policy groups |
| yundun-cloudfirewall:DescribeAckClusterConnectors | Backup ACK cluster sync nodes |
| yundun-cloudfirewall:DescribePrivateDnsEndpointList | Backup private DNS sync nodes |
| yundun-cloudfirewall:DescribePrivateDnsEndpointDetail | Fetch private DNS endpoint details |
| yundun-cloudfirewall:DescribePrivateDnsDomainNameList | Fetch private DNS domain names |

### Restore and analysis (write where noted)

| Action | Purpose |
|--------|---------|
| yundun-cloudfirewall:AddAddressBook | Restore address books (write) |
| yundun-cloudfirewall:AddControlPolicy | Restore/add Internet boundary policies (write) |
| yundun-cloudfirewall:ModifyControlPolicy | Enable/disable Internet boundary policies (write) |
| yundun-cloudfirewall:CreateNatFirewallControlPolicy | Restore/add NAT boundary policies (write) |
| yundun-cloudfirewall:ModifyNatFirewallControlPolicy | Enable/disable NAT boundary policies (write) |
| yundun-cloudfirewall:CreateVpcFirewallControlPolicy | Restore/add VPC boundary policies (write) |
| yundun-cloudfirewall:ModifyVpcFirewallControlPolicy | Enable/disable VPC boundary policies (write) |
| yundun-cloudfirewall:CreateAckClusterConnector | Restore ACK cluster sync nodes (write) |
| yundun-cloudfirewall:CreatePrivateDnsEndpoint | Restore private DNS endpoints (write) |
| yundun-cloudfirewall:AddPrivateDnsDomainName | Restore private DNS domain names (write) |

## Notes

- The action prefix is `yundun-cloudfirewall`. The legacy `cloudfw` prefix is
  not recognized by the service and causes silent permission failures.
- Read-only analysis commands (hit, dup, shadow, audit) only need the Describe
  actions listed under Backup.
- This skill never deletes policies or address books; no Delete actions are
  required.
