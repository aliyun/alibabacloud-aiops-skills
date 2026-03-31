# Acceptance Criteria: alibabacloud-tair-devtoolset

**Scenario**: Tair Benchmark — 创建 Tair 企业版实例并执行 redis-benchmark 性能测试
**Purpose**: Skill 测试验收标准

---

# Correct CLI Command Patterns

## 1. Product — 产品名必须为 `r-kvstore`

#### CORRECT
```bash
aliyun r-kvstore create-tair-instance ...
```

#### INCORRECT
```bash
# 错误：产品名不正确
aliyun redis create-tair-instance ...
aliyun tair create-tair-instance ...
aliyun kvstore create-tair-instance ...
```

## 2. Command — 必须使用插件模式（小写连字符）

#### CORRECT
```bash
aliyun r-kvstore create-tair-instance ...
aliyun r-kvstore describe-instance-attribute ...
aliyun r-kvstore modify-security-ips ...
aliyun r-kvstore allocate-instance-public-connection ...
aliyun r-kvstore describe-db-instance-net-info ...
aliyun r-kvstore release-instance-public-connection ...
```

#### INCORRECT
```bash
# 错误：使用传统 API 大驼峰格式
aliyun r-kvstore CreateTairInstance ...
aliyun r-kvstore DescribeInstanceAttribute ...
aliyun r-kvstore ModifySecurityIps ...
```

## 3. Parameters — 参数名必须使用连字符格式

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
# 错误：使用大驼峰参数名
aliyun r-kvstore create-tair-instance \
  --RegionId cn-hangzhou \
  --InstanceClass tair.rdb.1g

# 错误：region 参数名不正确（应为 --biz-region-id）
aliyun r-kvstore create-tair-instance \
  --region-id cn-hangzhou
```

## 4. user-agent — 每条 aliyun 命令必须携带

#### CORRECT
```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id r-bp1xxx \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# 错误：缺少 --user-agent
aliyun r-kvstore describe-instance-attribute \
  --instance-id r-bp1xxx
```

## 5. InstanceType 枚举值

#### CORRECT
```bash
--instance-type tair_rdb    # DRAM 内存型
--instance-type tair_scm    # 持久内存型
--instance-type tair_essd   # ESSD/SSD 磁盘型
```

#### INCORRECT
```bash
--instance-type rdb         # 错误：不完整
--instance-type TAIR_RDB    # 错误：大写
--instance-type redis       # 错误：无效枚举
```

## 6. ShardType 枚举值

#### CORRECT
```bash
--shard-type MASTER_SLAVE   # 主从高可用
--shard-type STAND_ALONE    # 单节点
```

#### INCORRECT
```bash
--shard-type master_slave   # 错误：应为全大写
--shard-type MasterSlave    # 错误：格式不对
```

## 7. ChargeType 枚举值

#### CORRECT
```bash
--charge-type PostPaid      # 按量付费
--charge-type PrePaid       # 包年包月
```

#### INCORRECT
```bash
--charge-type postpaid      # 错误：大小写不对
--charge-type PayAsYouGo    # 错误：无效枚举
```

---

# Script Execution Patterns

## 8. 脚本调用方式

#### CORRECT
```bash
export VPC_ID="vpc-bp1xxx"
export VSWITCH_ID="vsw-bp1xxx"
bash scripts/create-and-connect-test.sh
```

#### INCORRECT
```bash
# 错误：未设置必填环境变量
bash scripts/create-and-connect-test.sh

# 错误：参数传递方式不对
bash scripts/create-and-connect-test.sh --vpc-id vpc-bp1xxx
```
