# Acceptance Criteria: alibabacloud-lindorm-agent-skill

**Scenario**: Lindorm 全场景运维管理
**Purpose**: Skill 验收标准

---

## Correct CLI 命令模式

### 1. Lindorm API 调用（aliyun hitsdb）

#### ✅ CORRECT

```bash
# 查询实例列表（默认上海地域）
aliyun hitsdb get-lindorm-instance-list --region cn-shanghai

# 查询实例详情
aliyun hitsdb get-lindorm-instance --instance-id ld-uf6l5kr48wqm6rf1h

# 查询存储详情
aliyun hitsdb get-lindorm-fs-used-detail --instance-id ld-uf6l5kr48wqm6rf1h

# 查询 V2 实例存储详情
aliyun hitsdb get-lindorm-v2-storage-usage --instance-id ld-uf64f07n285tlbaz2

# 查询引擎列表
aliyun hitsdb get-lindorm-instance-engine-list --instance-id ld-uf6l5kr48wqm6rf1h

# 查询 IP 白名单
aliyun hitsdb get-instance-ip-white-list --instance-id ld-uf6l5kr48wqm6rf1h

# 查询地域列表
aliyun hitsdb describe-regions

# 查询实例概览（所有地域）
aliyun hitsdb get-instance-summary
```

#### ❌ INCORRECT

```bash
# 错误：实例 ID 格式错误
aliyun hitsdb get-lindorm-instance --instance-id lindorm-xxx --region cn-shanghai  # ❌ 应使用 ld-xxx 格式

# 错误：缺少必需参数
aliyun hitsdb get-lindorm-instance --region cn-shanghai  # ❌ 缺少 --instance-id

# 错误：使用错误的地域格式
aliyun hitsdb get-lindorm-instance-list --region Shanghai  # ❌ 应使用 cn-shanghai
```

### 2. 云监控 API 调用（aliyun cms）

#### ✅ CORRECT

```bash
# 查询 Lindorm 监控指标列表
aliyun cms describe-metric-meta-list --namespace acs_lindorm

# 查询 CPU 空闲率最新数据
aliyun cms describe-metric-last \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6l5kr48wqm6rf1h"}]'

# 查询历史监控数据（指定时间范围）
aliyun cms describe-metric-data \
    --namespace acs_lindorm \
    --metric-name cpu_idle \
    --dimensions '[{"instanceId":"ld-uf6l5kr48wqm6rf1h"}]' \
    --start-time "2026-04-14 08:00:00" \
    --end-time "2026-04-14 09:00:00" \
    --period 60
```

#### ❌ INCORRECT

```bash
# 错误：错误的 namespace
aliyun cms describe-metric-meta-list --namespace acs_hbase --region cn-shanghai  # ❌ 应使用 acs_lindorm

# 错误：错误的指标名称
aliyun cms describe-metric-last --metric-name cpu_usage  # ❌ 应使用 cpu_idle

# 错误：dimensions 格式错误
aliyun cms describe-metric-last --dimensions "instanceId=ld-xxx"  # ❌ 应使用 JSON 数组格式
```

---

## 参数验证模式

### 1. 实例 ID 格式

#### ✅ CORRECT

```
ld-uf6l5kr48wqm6rf1h  # ✅ 以 ld- 开头，后接字母数字
ld-bp1234567890abcdef  # ✅ 正确格式
```

#### ❌ INCORRECT

```
lindorm-xxx  # ❌ 不以 ld- 开头
ld_xxx  # ❌ 使用下划线而非连字符
LD-XXX  # ❌ 使用大写（建议使用小写）
```

### 2. 地域格式

#### ✅ CORRECT

```
cn-shanghai  # ✅ 正确格式
cn-beijing  # ✅ 正确格式
cn-hangzhou  # ✅ 正确格式
```

#### ❌ INCORRECT

```
shanghai  # ❌ 缺少 cn- 前缀
CN-SHANGHAI  # ❌ 使用大写
cn_shanghai  # ❌ 使用下划线
```

### 3. 时间格式

时间格式规则见 SKILL.md →「时间格式」，验收正误对比：

#### ✅ CORRECT

```bash
--start-time "2026-04-14 08:00:00"  # ✅ 本地时间格式（推荐），解析为 CST
--start-time "1773897600000"        # ✅ Unix 毫秒时间戳
--start-time "2026-04-14T08:00:00Z" # ✅ ISO 8601 UTC，解析为 UTC（注意时区换算：UTC+8=CST）
```

#### ❌ INCORRECT

```bash
--start-time "2026-04-14T08:00Z"     # ❌ ISO 8601 短格式（无秒）不支持，报 parse param time error
--start-time "2026/04/14 08:00:00"  # ❌ 使用斜杠分隔
--start-time "08:00:00"             # ❌ 仅提供时间，缺少日期
```

---

## 输出格式验证

### 1. 监控数据输出

#### ✅ CORRECT 输出结构

```json
{
  "Datapoints": [
    {
      "instanceId": "ld-uf6l5kr48wqm6rf1h",
      "timestamp": 1773897600000,
      "Average": 75.5
    }
  ],
  "DatapointCount": 1,
  "Success": true
}
```

#### 验证要点

- `Datapoints` 数组存在且非空
- 每个数据点包含 `instanceId`, `timestamp`, `Average`（部分指标含 `Maximum`/`Minimum`）
- `Average` 在合理范围（如 CPU 空闲率 0-100）

### 2. 实例列表输出

#### ✅ CORRECT 输出结构

```json
{
  "InstanceList": [
    {
      "InstanceId": "ld-uf6l5kr48wqm6rf1h",
      "InstanceAlias": "生产环境",
      "InstanceStatus": "ACTIVATION",
      "RegionId": "cn-shanghai"
    }
  ],
  "TotalCount": 1
}
```

#### 验证要点

- `InstanceList` 数组存在
- 每个实例包含 `InstanceId`, `InstanceStatus`
- `InstanceStatus` 为有效状态值（ACTIVATION, CREATING, STOPPED）

---

## 错误处理模式

### 1. API 错误响应

#### ✅ CORRECT 错误处理

```json
{
  "Code": "InvalidParameter.InstanceId",
  "Message": "The specified instance ID is invalid.",
  "RequestId": "xxx"
}
```

**处理流程**：
1. 读取 `Code` 字段识别错误类型
2. 参考 `references/02-ops/error-troubleshoot.md` 查找解决方案
3. 引导用户检查参数或权限

#### ❌ INCORRECT 错误处理

- 忽略错误码，直接返回原始错误信息
- 凭训练知识猜测错误原因（应查官方文档）

---

## 场景触发验证

### 正确触发场景

| 用户输入 | 触发场景 | 执行文档 |
|---------|---------|---------|
| "我有哪些 Lindorm 实例" | 实例查询 | `02-ops/instance-management.md` |
| "CPU 使用率是多少" | 监控查询 | `02-ops/monitoring-guide.md` |
| "报错 InvalidParameter" | 错误排查 | `02-ops/error-troubleshoot.md` |
| "怎么连接 Lindorm" | 连接指南 | `01-dev/connection-guide.md` |
| "怎么建表" | 建表指南 | `01-dev/table-design.md` |

### 错误触发场景

| 用户输入 | 错误处理 |
|---------|---------|
| "RDS 实例有哪些" | ❌ 不应触发 Lindorm skill，应提示使用 RDS skill |
| "MySQL 怎么用" | ❌ 不应触发，除非明确提到 Lindorm SQL |

---

## 安全规范验证

安全规则见 SKILL.md →「前置条件 → 凭证已配置」。

#### ❌ FORBIDDEN

```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID           # ❌ 禁止读取/打印 AK/SK
"请输入您的 AccessKey ID"                    # ❌ 禁止在对话中要求用户输入
aliyun configure set --access-key-id LTAI5t  # ❌ 禁止硬编码凭证
```