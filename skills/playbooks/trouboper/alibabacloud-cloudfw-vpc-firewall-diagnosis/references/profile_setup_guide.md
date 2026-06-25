# CLI Profile Setup Guide

This guide explains how to configure an Alibaba Cloud CLI profile for VPC firewall diagnosis.

## Quick Check

Run the following read-only checks:

```bash
aliyun configure list
aliyun sts get-caller-identity \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

If the identity command returns account information, the profile is usable.

## Configure a Profile

Use interactive configuration:

```bash
aliyun configure --profile <profile-name>
```

Provide the following values when prompted:

- **Aliyun Access Key ID**: your AccessKey ID.
- **Aliyun Access Key Secret**: your AccessKey Secret.
- **Default Region ID**: the region where your resources are located, for example `cn-hangzhou`.
- **Default Output Format**: JSON is recommended.
- **Default Language**: `en` is recommended for portable diagnostic output.

## Security Requirements

- Never hardcode a concrete profile name in skill files.
- Never store AccessKey values in scripts or documentation.
- Never extract AccessKey values from local configuration files.
- Always ask the user which profile to use before running diagnosis.

## Minimum RAM Permission Scope

The profile must have the read-only permissions listed in [ram-policies.md](ram-policies.md). The skill does not require any create, modify, or delete permissions.

## Validation Command

After configuration, validate a representative read-only Cloud Firewall API:

```bash
aliyun cloudfw describe-vpc-firewall-precheck-detail \
  --VpcId <vpc-id> \
  --Region <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Note: `describe-vpc-firewall-precheck-detail` uses `--Region`, not `--RegionId`.
