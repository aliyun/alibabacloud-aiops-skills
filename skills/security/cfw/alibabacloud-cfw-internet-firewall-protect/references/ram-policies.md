# RAM Permission List

## Read Permissions

- `yundun-cloudfirewall:DescribeAssetList` - Query public IP assets and protection status
- `yundun-cloudfirewall:DescribeResourceTypeAutoEnable` - Query auto-protection settings

## Write Permissions

- `yundun-cloudfirewall:PutEnableFwSwitch` - Enable firewall protection for specified assets
- `yundun-cloudfirewall:PutDisableFwSwitch` - Disable firewall protection for specified assets
- `yundun-cloudfirewall:PutEnableAllFwSwitch` - Enable firewall protection for all public IPs
- `yundun-cloudfirewall:PutDisableAllFwSwitch` - Disable firewall protection for all public IPs
- `yundun-cloudfirewall:ModifyResourceTypeAutoEnable` - Modify auto-protection settings for new assets

## Notes

- The RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall`, NOT `cloudfw`. Using the wrong prefix will cause the policy to not take effect, resulting in NoPermission / ImplicitDeny errors.
- For read-only access, grant only `DescribeAssetList` and `DescribeResourceTypeAutoEnable`.
- Global switch operations (EnableAll/DisableAll) affect all public IPs — restrict to operations administrators.
