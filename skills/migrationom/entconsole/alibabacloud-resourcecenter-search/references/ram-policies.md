# RAM Policies - Resource Center

## Required Permissions

### Single Account Operations

The following are the minimum RAM permissions required for single-account resource search and inventory:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "resourcecenter:EnableResourceCenter",
        "resourcecenter:DisableResourceCenter",
        "resourcecenter:GetResourceConfiguration",
        "tag:ListTagKeys",
        "tag:ListTagValues"
      ],
      "Resource": "*"
    }
  ]
}
```

### Cross-Account Operations (Requires Resource Directory Management Account or Delegated Admin)

The following are the RAM permissions required for cross-account resource search and inventory (must be executed by the Resource Directory management account or delegated admin account):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "resourcecenter:EnableMultiAccountResourceCenter",
        "resourcecenter:DisableMultiAccountResourceCenter",
        "resourcecenter:GetMultiAccountResourceCenterServiceStatus",
        "resourcecenter:SearchMultiAccountResources",
        "resourcecenter:GetMultiAccountResourceCounts",
        "resourcecenter:GetMultiAccountResourceConfiguration"
      ],
      "Resource": "*"
    }
  ]
}
```

### Read-Only Policy (Recommended for Search & Statistics Only)

If only search and statistics functionality is needed, the following read-only permissions can be used:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "resourcecenter:GetResourceConfiguration",
        "tag:ListTagKeys",
        "tag:ListTagValues",
        "resourcecenter:GetMultiAccountResourceCenterServiceStatus",
        "resourcecenter:SearchMultiAccountResources",
        "resourcecenter:GetMultiAccountResourceCounts",
        "resourcecenter:GetMultiAccountResourceConfiguration"
      ],
      "Resource": "*"
    }
  ]
}
```

## System Role

When enabling Resource Center, the system automatically creates the service-linked role `AliyunServiceRoleForResourceMetaCenter`. This role is used by Resource Center to call resource query or list APIs from cloud services to obtain resource metadata information.

## Notes

- Enabling/disabling the Resource Center service requires an Alibaba Cloud account or a RAM user with `EnableResourceCenter`/`DisableResourceCenter` permissions
- Cross-account operations must use the **Resource Directory management account** or **Resource Center delegated admin account**
- It is recommended to use the system policy `AliyunResourceCenterReadOnlyAccess` for read-only access
- It is recommended to use the system policy `AliyunResourceCenterFullAccess` for full access
