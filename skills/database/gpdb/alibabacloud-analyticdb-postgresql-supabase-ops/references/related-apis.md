# Related APIs - ADBPG Supabase Management

本文档列出了 ADBPG Supabase 管理相关的所有 CLI 命令和 API。

## CLI 命令列表

| Product | CLI Command | API Action | Description |
|---------|-------------|------------|-------------|
| GPDB | `aliyun gpdb list-supabase-projects` | ListSupabaseProjects | 查询 Supabase 实例列表 |
| GPDB | `aliyun gpdb get-supabase-project` | GetSupabaseProject | 查询 Supabase 实例详情 |
| GPDB | `aliyun gpdb get-supabase-project-api-keys` | GetSupabaseProjectApiKeys | 查询 Supabase 实例 API Keys |
| GPDB | `aliyun gpdb get-supabase-project-dashboard-account` | GetSupabaseProjectDashboardAccount | 查询 Supabase 项目 Dashboard 账号信息 |
| GPDB | `aliyun gpdb create-supabase-project` | CreateSupabaseProject | 创建 Supabase 项目 |
| GPDB | `aliyun gpdb pause-supabase-project` | PauseSupabaseProject | 暂停 Supabase 实例 |
| GPDB | `aliyun gpdb resume-supabase-project` | ResumeSupabaseProject | 恢复 Supabase 实例 |
| GPDB | `aliyun gpdb reset-supabase-project-password` | ResetSupabaseProjectPassword | 重置 Supabase 数据库密码 |
| GPDB | `aliyun gpdb modify-supabase-project-security-ips` | ModifySupabaseProjectSecurityIps | 修改 Supabase 项目白名单 |
| GPDB | `aliyun gpdb describe-regions` | DescribeRegions | 查询可用地域列表 |
| VPC | `aliyun vpc describe-vpcs` | DescribeVpcs | 查询 VPC（创建前可选） |
| VPC | `aliyun vpc describe-vswitches` | DescribeVSwitches | 查询交换机（创建前推荐，按可用区发现 VSwitch） |

## 命令参数详情

### list-supabase-projects

查询 Supabase 实例列表。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --biz-region-id | string | 否 | 地域 ID |
| --max-results | int | 否 | 最大返回数量，默认 10 |
| --next-token | string | 否 | 分页 Token |
| --page-number | int | 否 | 页码 |
| --page-size | int | 否 | 每页数量 |

### get-supabase-project

查询 Supabase 实例详情。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-id | string | **是** | Supabase 实例 ID (`spb-` + 后缀) |
| --biz-region-id | string | 否 | 地域 ID |

### get-supabase-project-api-keys

查询 Supabase 实例 API Keys。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-id | string | **是** | Supabase 实例 ID |
| --biz-region-id | string | 否 | 地域 ID |

### get-supabase-project-dashboard-account

查询 Supabase 项目 Dashboard 账号信息。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-id | string | **是** | Supabase 实例 ID |
| --biz-region-id | string | 否 | 地域 ID |

### create-supabase-project

创建 Supabase 项目（**异步**：接口较快返回 `ProjectId`，后台开通约 **3–5 分钟**；**开通成功**以 `get-supabase-project` 的 **`Status` = `running`** 为准）。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-name | string | **是** | 项目名称，1-128 字符，字母/数字/连字符/下划线，以字母或下划线开头 |
| --zone-id | string | **是** | 可用区 ID |
| --account-password | string | **是** | 初始账户密码，大小写字母+数字+特殊字符三种以上，8-32 位 |
| --security-ip-list | string | **是** | IP 白名单，127.0.0.1 表示禁止外部访问 |
| --vpc-id | string | **是** | VPC ID |
| --vswitch-id | string | **是** | VSwitch ID |
| --project-spec | string | **是** | 实例规格；官方文档默认 **1C1G**，本 Skill **默认推荐 2C2G** |
| --storage-size | int | 否 | 存储 (GB)；官方默认 **1**，本 Skill **默认推荐 20** |
| --disk-performance-level | string | 否 | 云盘 PL 等级：PL0 (默认) / PL1 |
| --pay-type | string | 否 | 付费类型；本 Skill **默认推荐 POSTPAY**（后付费） |
| --used-time | string | 否 | 与计费搭配，按需 |
| --period | string | 否 | 与计费搭配，按需 |
| --biz-region-id | string | 否 | 地域 ID |
| --client-token | string | 否 | 幂等性 Token |

详见 [create-supabase-project-parameters.md](create-supabase-project-parameters.md)（默认值、场景命名、密码生成、VPC/VSwitch 发现）。

### pause-supabase-project

暂停 Supabase 实例。暂停后服务不可用，但数据保留。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-id | string | **是** | Supabase 实例 ID |
| --biz-region-id | string | 否 | 地域 ID |

### resume-supabase-project

恢复 Supabase 实例。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-id | string | **是** | Supabase 实例 ID |
| --biz-region-id | string | 否 | 地域 ID |

### reset-supabase-project-password

重置 Supabase 数据库密码。重置后使用旧密码的连接将断开。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-id | string | **是** | Supabase 实例 ID |
| --account-password | string | **是** | 新密码，大小写字母+数字+特殊字符三种以上，8-32 位 |
| --biz-region-id | string | 否 | 地域 ID |

### modify-supabase-project-security-ips

修改 Supabase 项目白名单。

| 参数 | 类型 | 必填 | 描述 |
|-----|------|-----|------|
| --project-id | string | **是** | Supabase 实例 ID |
| --security-ip-list | string | **是** | IP 白名单，多个 IP 逗号分隔，支持 CIDR 格式 |
| --biz-region-id | string | 否 | 地域 ID |
| --update-db | bool | 否 | 是否修改数据库 5432 端口白名单，默认 true |
| --update-web | bool | 否 | 是否修改 HTTP/HTTPS 端口白名单，默认 true |

## 参考链接

- [GPDB API 文档](https://help.aliyun.com/document_detail/86906.html)
- [Supabase 产品文档](https://help.aliyun.com/product/85828.html)
