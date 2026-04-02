# Acceptance Criteria: alibabacloud-tair-devtoolset

**Scenario**: Create Tair Enterprise Edition Instance
**Purpose**: Skill Test Acceptance Criteria

---

# Correct CLI Command Patterns

## 1. Product — Product name must be `r-kvstore`

#### CORRECT
```bash
aliyun r-kvstore create-tair-instance ...
```

#### INCORRECT
```bash
# Error: Incorrect product name
aliyun redis create-tair-instance ...
aliyun tair create-tair-instance ...
aliyun kvstore create-tair-instance ...
```

## 2. Command — Must use plugin mode (lowercase with hyphens)

#### CORRECT
```bash
aliyun r-kvstore create-tair-instance ...
aliyun r-kvstore describe-instance-attribute ...
aliyun r-kvstore modify-security-ips ...
aliyun r-kvstore allocate-instance-public-connection ...
aliyun r-kvstore describe-db-instance-net-info ...
```

#### INCORRECT
```bash
# Error: Using legacy API PascalCase format
aliyun r-kvstore CreateTairInstance ...
aliyun r-kvstore DescribeInstanceAttribute ...
aliyun r-kvstore ModifySecurityIps ...
```

## 3. Parameters — Parameter names must use hyphen format

#### CORRECT
```bash
aliyun r-kvstore create-tair-instance \
  --biz-region-id cn-hangzhou \
  --instance-class tair.rdb.1g \
  --instance-type tair_rdb \
  --vpc-id vpc-bp1xxx \
  --vswitch-id vsw-bp1xxx \
  --password "YourPassword123!" \
  --charge-type PostPaid \
  --auto-pay true \
  --shard-type MASTER_SLAVE \
  --zone-id cn-hangzhou-h \
  --instance-name my-tair-test \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: Using PascalCase parameter names
aliyun r-kvstore create-tair-instance \
  --RegionId cn-hangzhou \
  --InstanceClass tair.rdb.1g

# Error: Incorrect region parameter name (should be --biz-region-id)
aliyun r-kvstore create-tair-instance \
  --region-id cn-hangzhou
```

## 4. user-agent — Must be included in every aliyun command

#### CORRECT
```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id r-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Error: Missing --user-agent
aliyun r-kvstore describe-instance-attribute \
  --instance-id r-bp1xxx
```

## 5. InstanceType Enum Values

#### CORRECT
```bash
--instance-type tair_rdb    # DRAM memory type
--instance-type tair_scm    # Persistent memory type
--instance-type tair_essd   # ESSD/SSD disk type
```

#### INCORRECT
```bash
--instance-type rdb         # Error: Incomplete
--instance-type TAIR_RDB    # Error: Uppercase
--instance-type redis       # Error: Invalid enum
```

## 6. ShardType Enum Values

#### CORRECT
```bash
--shard-type MASTER_SLAVE   # Master-slave high availability
--shard-type STAND_ALONE    # Single node
```

#### INCORRECT
```bash
--shard-type master_slave   # Error: Should be uppercase
--shard-type MasterSlave    # Error: Incorrect format
```

## 7. ChargeType Enum Values

#### CORRECT
```bash
--charge-type PostPaid      # Pay-as-you-go
--charge-type PrePaid       # Subscription
```

#### INCORRECT
```bash
--charge-type postpaid      # Error: Incorrect case
--charge-type PayAsYouGo    # Error: Invalid enum
```

---

# Script Execution Patterns

## 8. Script Invocation

#### CORRECT
```bash
export VPC_ID="vpc-bp1xxx"
export VSWITCH_ID="vsw-bp1xxx"
bash scripts/create-and-connect-test.sh
```

#### INCORRECT
```bash
# Error: Required environment variables not set
bash scripts/create-and-connect-test.sh

# Error: Incorrect parameter passing method
bash scripts/create-and-connect-test.sh --vpc-id vpc-bp1xxx
```
