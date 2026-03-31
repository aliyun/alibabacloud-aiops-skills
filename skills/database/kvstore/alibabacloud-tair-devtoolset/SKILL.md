---
name: alibabacloud-tair-devtoolset
description: |
  Alicloud Service Scenario-Based Skill. 使用阿里云 CLI 创建 Tair 企业版实例并配置公网访问。
  Triggers: "tair", "创建 tair 实例", "tair instance".
---

# Tair DevToolset — 创建实例与公网配置

通过阿里云 CLI 自动化创建 Tair 企业版云原生实例、配置公网访问、设置 IP 白名单。

**Architecture**: `VPC + VSwitch + Tair Enterprise Instance + Public Endpoint`

---

## 1. Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# 验证 CLI 版本
aliyun version

# 启用自动插件安装
aliyun configure set --auto-plugin-install true

# 验证 jq
jq --version
```

如未安装 jq：
```bash
brew install jq   # macOS
```

---

## 2. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> 所有凭证配置沿用 aliyun CLI 已有配置，无需在脚本中单独设置。
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## 3. RAM Policy

本 Skill 涉及的 RAM 权限详见 [references/ram-policies.md](references/ram-policies.md)。

核心权限：

| RAM Action | Description |
|-----------|-------------|
| `r-kvstore:CreateTairInstance` | 创建 Tair 实例 |
| `r-kvstore:DescribeInstanceAttribute` | 查询实例状态 |
| `r-kvstore:ModifySecurityIps` | 修改白名单 |
| `r-kvstore:AllocateInstancePublicConnection` | 分配公网地址 |
| `r-kvstore:DescribeDBInstanceNetInfo` | 查询网络信息 |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## 4. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| VPC_ID | **Yes** | 专有网络 ID，如 `vpc-bp1xxx` | — |
| VSWITCH_ID | **Yes** | 交换机 ID，如 `vsw-bp1xxx` | — |
| REGION_ID | No | 地域 ID | `cn-hangzhou` |
| ZONE_ID | No | 可用区 ID | `cn-hangzhou-h` |
| INSTANCE_TYPE | No | 实例系列 | `tair_rdb` |
| INSTANCE_CLASS | No | 实例规格 | `tair.rdb.1g` |
| INSTANCE_NAME | No | 实例名称 | `tair-benchmark-<timestamp>` |

### 常用规格

#### 标准架构

| InstanceClass | 内存 | 带宽 | 最大连接数 | QPS 参考值 |
|---------------|------|------|-----------|-----------|
| tair.rdb.1g | 1 GB | 768 Mbps | 30,000 | 300,000 |
| tair.rdb.2g | 2 GB | 768 Mbps | 30,000 | 300,000 |
| tair.rdb.4g | 4 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.8g | 8 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.16g | 16 GB | 768 Mbps | 40,000 | 300,000 |
| tair.rdb.24g | 24 GB | 768 Mbps | 50,000 | 300,000 |
| tair.rdb.32g | 32 GB | 768 Mbps | 50,000 | 300,000 |
| tair.rdb.64g | 64 GB | 768 Mbps | 50,000 | 300,000 |

## 5. Core Workflow

### 方式一：自动化脚本（推荐）

使用收集到的参数设置环境变量，运行一体化脚本：

```bash
export VPC_ID="<用户确认的 VPC_ID>"
export VSWITCH_ID="<用户确认的 VSWITCH_ID>"

# 可选参数
export REGION_ID="cn-hangzhou"
export ZONE_ID="cn-hangzhou-h"
export INSTANCE_TYPE="tair_rdb"
export INSTANCE_CLASS="tair.rdb.1g"
# NAT 环境需手动设置公网 IP
# export MY_PUBLIC_IP="你的公网IP"

bash scripts/create-and-connect-test.sh
```

脚本将自动完成：创建实例 → 等待就绪 → 配置白名单 → 分配公网地址 → 获取公网连接信息。

### 方式二：手动分步执行

#### Task 1: 创建 Tair 实例

```bash
aliyun r-kvstore create-tair-instance \
  --biz-region-id "${REGION_ID}" \
  --zone-id "${ZONE_ID}" \
  --vpc-id "${VPC_ID}" \
  --vswitch-id "${VSWITCH_ID}" \
  --instance-name "${INSTANCE_NAME}" \
  --instance-type "${INSTANCE_TYPE}" \
  --instance-class "${INSTANCE_CLASS}" \
  --charge-type PostPaid \
  --shard-type MASTER_SLAVE \
  --auto-pay true \
  --user-agent AlibabaCloud-Agent-Skills
```

从返回中提取 `InstanceId`。

#### Task 2: 等待实例就绪

轮询实例状态直到 `Normal`：

```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

检查 `Instances.DBInstanceAttribute[0].InstanceStatus` 为 `Normal`。建议每 30 秒查询一次，最多等待 10 分钟。

#### Task 3: 配置 IP 白名单

```bash
# 通过 ifconfig 获取本机 IP，或手动设置
MY_PUBLIC_IP=$(ifconfig | grep 'inet ' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -v '127.0.0.1' | head -n1)
# NAT 环境请手动设置: export MY_PUBLIC_IP="你的公网IP"

aliyun r-kvstore modify-security-ips \
  --instance-id "${INSTANCE_ID}" \
  --security-ips "${MY_PUBLIC_IP}" \
  --security-ip-group-name "benchmark" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 4: 分配公网连接地址

```bash
CONNECTION_PREFIX=$(echo "${INSTANCE_ID}" | tr '[:upper:]' '[:lower:]' | sed 's/-//g' | cut -c1-20)pub

aliyun r-kvstore allocate-instance-public-connection \
  --instance-id "${INSTANCE_ID}" \
  --connection-string-prefix "${CONNECTION_PREFIX}" \
  --port "6379" \
  --user-agent AlibabaCloud-Agent-Skills
```

等待实例恢复 `Normal` 状态后继续。

#### Task 5: 获取公网连接地址

```bash
aliyun r-kvstore describe-db-instance-net-info \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

从返回中找到 `IPType` 为 `Public` 的 `ConnectionString` 和 `Port`。

---

## 6. Success Verification

详细验证步骤见 [references/verification-method.md](references/verification-method.md)。

快速验证实例状态：
```bash
aliyun r-kvstore describe-instance-attribute \
  --instance-id "${INSTANCE_ID}" \
  --user-agent AlibabaCloud-Agent-Skills
```

确认 `InstanceStatus` 为 `Normal` 且公网地址已分配。

---

## 7. Troubleshooting

| 问题 | 解决方案 |
|------|---------|
| 连接超时 | 检查白名单是否包含当前公网 IP（必须 IPv4） |
| 公网地址为空 | 确认 `allocate-instance-public-connection` 执行成功并等待实例恢复 Normal |

---

## 8. Best Practices

1. 使用按量付费（PostPaid）进行测试
2. 白名单仅添加测试机公网 IP，遵循最小权限原则

---

## 9. Reference Links

| Reference | Description |
|-----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI 安装与配置指南 |
| [references/ram-policies.md](references/ram-policies.md) | RAM 权限策略文档 |
| [references/related-commands.md](references/related-commands.md) | 相关 CLI 命令列表与参数 |
| [references/verification-method.md](references/verification-method.md) | 成功验证方法 |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | 验收标准 |
