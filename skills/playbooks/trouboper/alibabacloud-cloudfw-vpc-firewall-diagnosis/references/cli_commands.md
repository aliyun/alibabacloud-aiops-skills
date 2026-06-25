# CLI Command Reference

This document lists common read-only CLI commands for VPC firewall diagnosis. All Alibaba Cloud CLI examples use plugin mode with lowercase-hyphenated actions.

## Global Requirements

- Always pass the user-provided profile through `--profile <profile>`.
- Always include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis` for every Alibaba Cloud service CLI command.
- Run CLI AI-Mode setup and plugin update before service API calls.
- Disable CLI AI-Mode after the diagnostic workflow ends.
- Never hardcode AccessKey values or concrete profile names.
- Never run write actions from this diagnostic skill.

## AI-Mode and Plugin Update

Run this block before any Alibaba Cloud service API call:

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
aliyun plugin update
```

Run this command after the diagnostic workflow ends:

```bash
aliyun configure ai-mode disable
```

Notes:

- `aliyun configure ai-mode enable` and `aliyun configure ai-mode disable` are local CLI configuration commands.
- `aliyun configure ai-mode set-user-agent` sets the default AI-Mode User-Agent for this skill.
- `aliyun plugin update` is a local/system CLI command; do not add the User-Agent flag to it.
- Local-only checks such as `aliyun version`, `aliyun configure list`, and `python3 --version` do not require the User-Agent flag because they do not call Alibaba Cloud service APIs.

## Environment Checks

```bash
aliyun version
aliyun configure list
aliyun sts get-caller-identity \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
python3 --version
```

## Cloud Firewall Read-only Commands

### Query VPC firewall list

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --RegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query VPC firewall precheck details

```bash
aliyun cloudfw describe-vpc-firewall-precheck-detail \
  --VpcId <vpc-id> \
  --Region <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Note: this API uses `--Region`, not `--RegionId` or `--RegionNo`.

### Query route policy task status

```bash
aliyun cloudfw describe-firewall-task \
  --TaskType VPC \
  --ChildInstanceId <vpc-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query rollback target route table

```bash
aliyun cloudfw describe-tr-firewall-policy-back-up-association-list \
  --FirewallId <firewall-id> \
  --TrFirewallRoutePolicyId <route-policy-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query VPC firewall ACL policies

```bash
aliyun cloudfw describe-vpc-firewall-control-policy \
  --VpcFirewallId <vpc-firewall-id> \
  --PageSize 50 \
  --CurrentPage 1 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

## ActionTrail Read-only Commands

### Query route policy operations in the recent time window

```bash
aliyun actiontrail lookup-events \
  --StartTime <start-time> \
  --EndTime <end-time> \
  --MaxResults 10 \
  --LookupAttribute.1.Key EventName \
  --LookupAttribute.1.Value CreateTrFirewallV2RoutePolicy \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query all write events in a time window for correlation

```bash
aliyun actiontrail lookup-events \
  --StartTime <start-time> \
  --EndTime <end-time> \
  --MaxResults 50 \
  --LookupAttribute.1.Key EventRW \
  --LookupAttribute.1.Value Write \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Paginate ActionTrail results

```bash
aliyun actiontrail lookup-events \
  --StartTime <start-time> \
  --EndTime <end-time> \
  --MaxResults 50 \
  --NextToken <next-token> \
  --LookupAttribute.1.Key EventRW \
  --LookupAttribute.1.Value Write \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

## CBN and Transit Router Read-only Commands

### Query transit routers

```bash
aliyun cbn list-transit-routers \
  --RegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query VPC attachments

```bash
aliyun cbn list-transit-router-vpc-attachments \
  --RegionId <region> \
  --TransitRouterId <tr-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query route tables

```bash
aliyun cbn list-transit-router-route-tables \
  --RegionId <region> \
  --TransitRouterId <tr-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query route entries

```bash
aliyun cbn list-transit-router-route-entries \
  --TransitRouterRouteTableId <route-table-id> \
  --MaxResults 100 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Query rejected route entries

```bash
aliyun cbn list-transit-router-route-entries \
  --TransitRouterRouteTableId <route-table-id> \
  --TransitRouterRouteEntryStatus Rejected \
  --MaxResults 100 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

## VPC Read-only Commands

```bash
aliyun vpc describe-vpcs \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

```bash
aliyun vpc describe-vpc-attribute \
  --RegionId <region> \
  --VpcId <vpc-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

## Date Helpers

### macOS

```bash
date -u -v-1d '+%Y-%m-%dT%H:%M:%SZ'
date -u '+%Y-%m-%dT%H:%M:%SZ'
```

### Linux

```bash
date -u -d '1 day ago' '+%Y-%m-%dT%H:%M:%SZ'
date -u '+%Y-%m-%dT%H:%M:%SZ'
```

## Common Mistakes

| Mistake | Correct usage |
|---|---|
| PascalCase CloudFirewall CLI action | `aliyun cloudfw describe-vpc-firewall-precheck-detail` |
| PascalCase ActionTrail CLI action | `aliyun actiontrail lookup-events` |
| Route entry query with unnecessary transit router ID | `aliyun cbn list-transit-router-route-entries --TransitRouterRouteTableId <route-table-id>` |
| `--RegionNo` for precheck details | Use `--Region` |
| User-Agent without skill identifier | Use `AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis` |
| Missing AI-Mode setup | Run `aliyun configure ai-mode enable`, `aliyun configure ai-mode set-user-agent`, and `aliyun plugin update` before service API calls |
| AI-Mode left enabled after diagnosis | Run `aliyun configure ai-mode disable` after the workflow ends |
