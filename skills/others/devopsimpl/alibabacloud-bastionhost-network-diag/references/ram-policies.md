# RAM Permission List

The RAM permissions required for this Skill to run (all are read-only permissions):

## Bastion Host Product (yundun-bastionhost)

`yundun-bastionhost:DescribeInstances` — Query the Bastion Host instance list to obtain basic information such as instance ID, public/private domain names, etc.

`yundun-bastionhost:DescribeInstanceAttribute` — Query the detailed attributes of a Bastion Host instance, including the public network switch, whitelist configuration, custom ports, etc.

## Cloud Firewall Product (cloudfw)

`yundun-cloudfw:DescribeAssetList` — Query whether the Bastion Host public ingress IP has been added to Cloud Firewall protection

`yundun-cloudfw:DescribeTrafficLog` — Query Cloud Firewall traffic logs to detect whether there are drop/interception records

## Permission Usage Notes

- All permissions above are **read-only query permissions** and do not involve any write, modify, or delete operations
- No wildcard permissions (such as `yundun-bastionhost:*`) are used
- If a permission is missing during execution, the corresponding diagnosis step will be skipped and the user will be informed
