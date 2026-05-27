# DDoS Native Protection Intercept Query — RAM Permission Checklist

> Complete list of RAM Actions corresponding to all CLI calls used by this skill. When the CLI returns a `Forbidden.RAM` / `NoPermission` error, refer to this table and ask the administrator to grant the missing permissions. All Actions in this skill are read-only queries (`Describe*` / `List*` types) and do not involve any write operations.

## 1. Required Permissions

Missing any of these will cause a break in the primary troubleshooting workflow.

| RAM Action | Corresponding CLI Command | Purpose | Impact if Missing |
|---|---|---|---|
| `ddosbgp:DescribeNetworkLayerIntercepts` | `aliyun ddosbgp describe-network-layer-intercepts` (on `aliyun-cli-ddosbgp` 0.3.0 the plugin rejects this, so the skill falls back to the OpenAPI route — see `related-commands.md`) | Query network-layer intercept records (core) | Cannot retrieve any intercept records |
| `ddosbgp:ListPolicyAttachment` | `aliyun ddosbgp list-policy-attachment` | Query policies bound to an instance | Cannot attribute intercept records to specific policies |
| `ddosbgp:ListPolicy` | `aliyun ddosbgp list-policy` | Query detailed policy configuration | Cannot read policy configuration details even when the policy name is known |
| `antiddos-public:DescribeBgpPackByIp` | `aliyun antiddos-public describe-bgp-pack-by-ip` | Derive the protection pack instance ID from an IP | Cannot derive the InstanceId when the user only provides an instance IP |

## 2. Optional Permissions

Missing optional permissions do not affect the primary troubleshooting workflow, but prevent answering deeper questions such as "which machine does this IP belong to".

| RAM Action | Corresponding CLI Command | Purpose |
|---|---|---|
| `antiddos-public:DescribeIpLocationService` | `aliyun antiddos-public describe-ip-location-service` | Query IP region and asset type |
| `antiddos-public:DescribeInstanceIpAddress` | `aliyun antiddos-public describe-instance-ip-address` | Query associated ECS instances and protection status |

## 3. Minimal Authorization Policy Document Example

When bundling the above permissions for a RAM user or role, the following policy document (JSON) can be used directly:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ddosbgp:DescribeNetworkLayerIntercepts",
        "ddosbgp:ListPolicyAttachment",
        "ddosbgp:ListPolicy",
        "antiddos-public:DescribeBgpPackByIp",
        "antiddos-public:DescribeIpLocationService",
        "antiddos-public:DescribeInstanceIpAddress"
      ],
      "Resource": "*"
    }
  ]
}
```

To grant only the minimal required permissions (excluding optional ones), simply remove the last two Actions.
