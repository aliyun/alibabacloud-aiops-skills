# RAM Permission Declaration

This Skill is designed for Alibaba Cloud AIOps troubleshooting scenarios, performing **read-only** information queries and diagnostics without any write operations. When authorizing, users should strictly follow the **principle of least privilege** and grant the sub-account or STS role the corresponding **read-only** permissions as listed below.

## 1. Permission Overview

| RAM System Policy | Purpose | Related Skill Module |
|---|---|---|
| `AliyunECSReadOnlyAccess` | Query ECS instances, security groups, ENIs, images, etc. | scripts/ecs_public_troubleshoot.py |
| `AliyunVPCReadOnlyAccess` | Query VPC, VSwitches, NAT gateways, SNAT, route tables, EIPs, IPv4 gateways, network ACLs, etc. | scripts/ecs_public_troubleshoot.py, scripts/vpc_service_public_troubleshoot.py |
| `AliyunCloudFirewallReadOnlyAccess` | Query Cloud Firewall (CFW) instances and policy status | scripts/ecs_public_troubleshoot.py, scripts/vpc_service_public_troubleshoot.py |
| `AliyunYundunDDosReadOnlyAccess` | Query DDoS Protection, Anti-DDoS Basic, blackhole status | scripts/ecs_public_troubleshoot.py, scripts/vpc_service_public_troubleshoot.py |
| `AliyunBSSReadOnlyAccess` | Query account balance and overdue status (QueryAccountBalance) | Used in both Scenario 1 and Scenario 2 |
| `AliyunSTSAssumeRoleAccess` | Obtain STS temporary credentials via AssumeRole (optional) | scripts/sts_create.py |

> Warning: This Skill **prohibits the use of any write permissions** (e.g., `AliyunECSFullAccess`, `AliyunVPCFullAccess`). Granting FullAccess violates the principle of least privilege.

## 2. Minimal Custom Policy (Recommended)

To further restrict permissions, create the following **custom RAM Policy** and grant it to the sub-account/role:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeNetworkInterfaces",
        "ecs:DescribeRegions"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVpcAttribute",
        "vpc:DescribeVSwitches",
        "vpc:DescribeVSwitchAttributes",
        "vpc:DescribeNatGateways",
        "vpc:DescribeSnatTableEntries",
        "vpc:DescribeEipAddresses",
        "vpc:DescribeRouteTableList",
        "vpc:DescribeRouteEntryList",
        "vpc:DescribeNetworkAcls",
        "vpc:DescribeIpv4Gateways"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "yundun-cloudfirewall:DescribeInstanceMembers",
        "yundun-cloudfirewall:DescribeAssetList",
        "yundun-cloudfirewall:DescribeControlPolicy"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "yundun-ddos:DescribeInstanceIpAddress"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:QueryAccountBalance",
        "bssapi:QueryAccountBalance"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. Authorization Steps

These steps are performed **manually by an administrator in the RAM console** (or
via the administrator's own separate tooling). This skill is strictly read-only
and never issues any RAM write command (`create-policy`, `attach-policy-*`, etc.).

### Method 1: Attach System Policies to RAM User

In the RAM console: Users -> <ram-user-name> -> Add Permissions, then select the
system policies listed above (for example `AliyunECSReadOnlyAccess`).

### Method 2: Attach Custom Policy to RAM Role (Recommended for STS Scenarios)

In the RAM console: Policies -> Create Policy (paste the JSON document above and
name it `QoderSkillNetworkTroubleshootReadOnly`), then attach the policy to the
target RAM role. The skill consumes the resulting role's credentials via STS
AssumeRole and performs only the read-only actions listed in section 1.

## 4. Permission Verification

The Skill verifies credential validity via `sts:GetCallerIdentity` at startup. If `Forbidden.RAM` or `NoPermission` errors are encountered during the actual detection process, verify that the permissions listed above have been fully granted.

## 5. Security Constraints

- AK/SK must never appear in plaintext in scripts, logs, or tickets
- Prefer STS temporary credentials (validity <= 3600 seconds)
- Cache file `.sts_cache.json` has default permission 600 to prevent leakage
- This Skill **does not contain any write or delete operations**; if a non-read-only API call is detected, it should be immediately reported as an anomaly
