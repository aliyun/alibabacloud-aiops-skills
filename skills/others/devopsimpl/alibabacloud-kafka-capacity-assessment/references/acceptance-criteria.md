# Acceptance Criteria: kafka-capacity-assessment

**Scenario**: Kafka Instance Capacity Assessment
**Purpose**: Skill acceptance criteria and test scenarios

---

# Correct CLI Command Patterns

## 1. Product — alikafka

#### ✅ CORRECT
```bash
aliyun alikafka get-instance-list --biz-region-id cn-hangzhou --region cn-hangzhou
```

#### ❌ INCORRECT
```bash
# Traditional API format (not plugin mode)
aliyun alikafka GetInstanceList --RegionId cn-hangzhou
```

## 2. Product — cms

#### ✅ CORRECT
```bash
aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV2
```

#### ❌ INCORRECT
```bash
# Traditional API format (not plugin mode)
aliyun cms DescribeMetricList --Namespace acs_kafka --MetricName InstanceMessageInputRatioV2
```

## 3. Parameter Names — Plugin Mode Format

#### ✅ CORRECT
```bash
aliyun alikafka get-instance-list --biz-region-id cn-hangzhou --region cn-hangzhou --instance-id i-xxx --series v2
aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV2 --period 60 --start-time "2026-01-01 00:00:00" --end-time "2026-01-01 01:00:00" --dimensions '[{"instanceId":"alikafka_post-cn-xxx"}]'
```

#### ❌ INCORRECT
```bash
# PascalCase parameter names (not plugin mode)
aliyun alikafka get-instance-list --BizRegionId cn-hangzhou --InstanceId.1 i-xxx
aliyun cms describe-metric-list --Namespace acs_kafka --MetricName InstanceMessageInputRatioV2 --Period 60 --StartTime "2026-01-01 00:00:00" --EndTime "2026-01-01 01:00:00" --Dimensions '[{"instanceId":"alikafka_post-cn-xxx"}]'
```

## 4. No Cross-Series Metric Usage (v2 / v3)

#### ✅ CORRECT
```bash
# v2 instance uses V2-suffixed metrics
aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV2 ...
# v3 instance uses V3-suffixed metrics
aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV3 ...
```

#### ❌ INCORRECT
```bash
# V3 metric used on a v2 instance
aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV3 ...
# V2 metric used on a v3 instance
aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV2 ...
```

## 5. No Write Operations Permitted

#### ✅ CORRECT
```bash
# Read-only query operations only
aliyun alikafka get-instance-list --biz-region-id cn-hangzhou --region cn-hangzhou
aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV2 ...
```

#### ❌ INCORRECT
```bash
# Any write operation
aliyun alikafka upgrade-instance ...
aliyun alikafka modify-instance-name ...
```

## 6. Observability — --user-agent Required on Every API Command

#### ✅ CORRECT
```bash
# Every aliyun API command includes --user-agent with session-id
aliyun alikafka get-instance-list --biz-region-id cn-hangzhou --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6

aliyun cms describe-metric-list --namespace acs_kafka --metric-name InstanceMessageInputRatioV2 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

## 7. Credential Verification

#### ✅ CORRECT
```bash
aliyun configure list
# Verify the output contains a valid profile before proceeding
```

#### ❌ INCORRECT
```bash
# Directly reading or printing AK/SK values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID

# Asking the user to input AK/SK in the conversation
aliyun configure set --access-key-id LTAI5txxx --access-key-secret 8dxxx
```
