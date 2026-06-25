# RAM Permission List

This skill only performs read-only diagnostic operations without any write operations. Below are the minimum RAM permissions required:

## NAS File Storage

`nas:DescribeFileSystems` -- Query file system information (type, protocol, status)
`nas:DescribeMountTargets` -- Query mount target information (status, VPC, permission group)
`nas:DescribeAccessGroups` -- Query permission group configuration
`nas:DescribeAccessRules` -- Query permission group rules (authorized IP, read/write access)

## ECS Cloud Server

`ecs:DescribeInstances` -- Query ECS instance information (VPC, private IP, security group)
`ecs:DescribeSecurityGroups` -- Query security group type (Normal/Enterprise)
`ecs:DescribeSecurityGroupAttribute` -- Query security group inbound/outbound rules

## VPC Virtual Private Cloud

`vpc:DescribeVpcs` -- Query VPC information
`vpc:DescribeVSwitches` -- Query VSwitch information

## Recommended Custom Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "nas:DescribeFileSystems",
        "nas:DescribeMountTargets",
        "nas:DescribeAccessGroups",
        "nas:DescribeAccessRules"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    }
  ]
}
```
