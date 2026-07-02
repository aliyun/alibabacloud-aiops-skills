# RAM Permission List

The RAM permissions required by this skill are read-only only; no write permissions are needed.

## Cloud Firewall Query Permissions

`yundun-cloudfw:DescribeAssetList` — Query Internet Firewall protected asset list and protection status.

`yundun-cloudfw:DescribePolicyAdvancedConfig` — Query Internet Firewall global strict-mode configuration.

`yundun-cloudfw:DescribeControlPolicy` — Query Internet Firewall ACL rule list.

`yundun-cloudfw:DescribeVpcFirewallList` — Query VPC boundary firewall instance list.

`yundun-cloudfw:DescribeVpcFirewallControlPolicy` — Query VPC boundary firewall ACL rule list.

`yundun-cloudfw:DescribeNatFirewallList` — Query NAT boundary firewall instance list.

`yundun-cloudfw:DescribeNatFirewallControlPolicy` — Query NAT boundary firewall ACL rule list.

`yundun-cloudfw:DescribeTrafficLog` — Query traffic logs (requires the log analysis feature to be enabled).

## SLS Query Permissions

`log:GetLogs` — Query logs through `aliyun sls get-logs-v2`.

## ActionTrail Query Permissions

`actiontrail:LookupEvents` — Query operation history through `aliyun actiontrail lookup-events`.

## Notes

- All permissions listed above are read-only. This skill does not invoke any Create/Update/Delete APIs.
- The skill relies on the default credential chain (environment variables or the default profile in `~/.aliyun/config.json`). It never uses the `--profile` parameter, never runs `aliyun configure get`, and never runs `aliyun configure list`.
- The Cloud Firewall `yundun-cloudfw:Describe*` permissions are included in the Alibaba Cloud managed policy `AliyunYundunCloudFirewallReadOnlyAccess`. You can attach this managed policy to the RAM user or role used for diagnosis.
- If you use `aliyun sls get-logs-v2` or `aliyun actiontrail lookup-events`, ensure the corresponding `log:GetLogs` and `actiontrail:LookupEvents` permissions are also granted.
