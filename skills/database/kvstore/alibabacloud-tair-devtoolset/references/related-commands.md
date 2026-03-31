# Related CLI Commands — Tair Benchmark Skill

## R-KVStore Product Commands

| CLI Command | API | Description |
|------------|-----|-------------|
| `aliyun r-kvstore create-tair-instance` | CreateTairInstance | 创建 Tair 企业版云原生实例 |
| `aliyun r-kvstore describe-instance-attribute` | DescribeInstanceAttribute | 查询实例属性（含状态） |
| `aliyun r-kvstore modify-security-ips` | ModifySecurityIps | 配置 IP 白名单 |
| `aliyun r-kvstore allocate-instance-public-connection` | AllocateInstancePublicConnection | 分配公网连接地址 |
| `aliyun r-kvstore describe-db-instance-net-info` | DescribeDBInstanceNetInfo | 查询实例网络信息 |

## Key Parameters Reference

### create-tair-instance

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--biz-region-id` | Yes | 地域 ID，如 `cn-hangzhou` |
| `--instance-class` | Yes | 实例规格，如 `tair.rdb.1g` |
| `--instance-type` | Yes | 实例系列：`tair_rdb` / `tair_scm` / `tair_essd` |
| `--vpc-id` | Yes | VPC ID |
| `--vswitch-id` | Yes | 交换机 ID |
| `--password` | No | 连接密码（8-32位，至少包含大写、小写、数字、特殊字符中三种） |
| `--charge-type` | No | 计费方式：`PostPaid`（按量）/ `PrePaid`（包年包月） |
| `--auto-pay` | No | 是否自动付款 |
| `--shard-type` | No | 分片类型：`MASTER_SLAVE`（默认）/ `STAND_ALONE` |
| `--zone-id` | No | 可用区 ID |
| `--instance-name` | No | 实例名称 |

### describe-instance-attribute

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | 实例 ID |

### modify-security-ips

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | 实例 ID |
| `--security-ips` | Yes | 白名单 IP，多个用逗号分隔 |
| `--security-ip-group-name` | No | 白名单分组名称 |
| `--modify-mode` | No | 修改方式：`Cover`（覆盖）/ `Append`（追加）/ `Delete`（删除） |

### allocate-instance-public-connection

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | 实例 ID |
| `--connection-string-prefix` | Yes | 公网连接前缀（小写字母开头，8-40字符） |
| `--port` | Yes | 端口号（1024-65535） |

### describe-db-instance-net-info

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | 实例 ID |
