# Acceptance Criteria: alibabacloud-ddos-security-monitor

**Scenario**: DDoS Security Product Inspection & Monitoring
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product - Product Code Verification

#### Correct
```bash
aliyun antiddos-public describe-instance-ip-address ...
aliyun ddosbgp describe-instance-list ...
aliyun ddoscoo describe-instances ...
```

#### Incorrect
```bash
aliyun antiddospublic ...        # Error: missing hyphen
aliyun ddos-bgp ...              # Error: incorrect product code spelling
aliyun ddos-coo ...              # Error: incorrect product code spelling
```

## 2. Command - Command Format (MUST use plugin mode)

#### Correct (plugin mode, kebab-case)
```bash
aliyun ddosbgp describe-instance-list --page-no 1 --page-size 10 --region cn-hangzhou
aliyun ddoscoo describe-instances --page-number 1 --page-size 10 --region cn-hangzhou
aliyun ddoscoo describe-ddos-events --instance-ids <id> --start-time <ts> --end-time <ts> --page-number 1 --page-size 50 --region cn-hangzhou
aliyun ddoscoo describe-domain-qps-list --start-time <ts> --end-time <ts> --interval 300 --region cn-hangzhou
aliyun ddoscoo describe-port-flow-list --instance-ids <id> --start-time <ts> --end-time <ts> --interval 300 --region cn-hangzhou
aliyun ddoscoo describe-domain-status-code-list --start-time <ts> --interval 300 --query-type gf --region cn-hangzhou
aliyun ddosbgp describe-ddos-event --instance-id <id> --start-time <ts> --end-time <ts> --page-no 1 --page-size 50 --biz-region-id cn-hangzhou
aliyun ddosbgp describe-traffic --start-time <ts> --region cn-hangzhou
aliyun ddosbgp describe-pack-ip-list --instance-id <id> --page-no 1 --page-size 50 --biz-region-id cn-hangzhou
```

#### Incorrect (PascalCase traditional format)
```bash
aliyun ddosbgp DescribeInstanceList --PageNo 1 --PageSize 10 --RegionId cn-hangzhou
aliyun ddoscoo DescribeInstances --PageNumber 1 --PageSize 10 --RegionId cn-hangzhou
aliyun ddoscoo DescribeDDoSEvents --InstanceIds.1 <id> --StartTime <ts> --EndTime <ts>
aliyun ddoscoo DescribeDomainQPSList --StartTime <ts> --EndTime <ts> --Interval 300
```
**Reason**: The specification requires all CLI commands to use plugin mode format (lowercase with hyphens). PascalCase traditional API format is not allowed.

## 3. Parameters - Parameter Format Verification

#### Correct
```bash
# Region parameter - ddoscoo/ddosbgp most commands use --region global parameter
aliyun ddoscoo describe-instances --page-number 1 --page-size 10 --region cn-hangzhou

# ddosbgp some commands use --biz-region-id
aliyun ddosbgp describe-ddos-event --instance-id <id> --start-time <ts> --end-time <ts> --page-no 1 --page-size 50 --biz-region-id cn-hangzhou

# Instance list parameter - space-separated
aliyun ddoscoo describe-ddos-events --instance-ids id1 id2 id3 ...
```

#### Incorrect
```bash
# Error: Using PascalCase parameter names
aliyun ddosbgp describe-instance-list --PageNo 1 --PageSize 10 --RegionId cn-hangzhou

# Error: Using .N format for instance list
aliyun ddoscoo describe-ddos-events --InstanceIds.1 <id>

# Error: ddosbgp describe-ddos-event using --region instead of --biz-region-id
aliyun ddosbgp describe-ddos-event --instance-id <id> --region cn-hangzhou
```

## 4. Authentication - Security Rules

#### Correct
```bash
# Only check credential status
aliyun configure list
```

#### Incorrect
```bash
# Error: Printing AK/SK values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID

# Error: Passing plaintext credentials in command line
aliyun configure set --mode AK --access-key-id LTAI5t... --access-key-secret ...
```

## 5. AI-Mode Lifecycle

#### Correct
```bash
# Enable at start
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ddos-security-monitor"

# ... execute inspection ...

# Disable at ALL exit paths
aliyun configure ai-mode disable
```

#### Incorrect
```bash
# Error: Missing AI-Mode enable/disable
# Error: Missing user-agent setting
# Error: Only disabling on success path, missing on error path
```

## 6. Non-existent Commands

#### Incorrect
```bash
# Error: describe-instance-flow does not exist in ddoscoo plugin mode
aliyun ddoscoo describe-instance-flow --instance-ids <id> ...
```
**Note**: `describe-instance-flow` does not exist in ddoscoo. Use `describe-port-flow-list` instead.
