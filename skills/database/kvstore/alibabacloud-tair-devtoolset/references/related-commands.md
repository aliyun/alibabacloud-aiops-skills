# Related CLI Commands — Tair Skill

## R-KVStore Product Commands

| CLI Command | API | Description |
|------------|-----|-------------|
| `aliyun r-kvstore create-tair-instance` | CreateTairInstance | Create Tair Enterprise Edition cloud-native instance |
| `aliyun r-kvstore describe-instance-attribute` | DescribeInstanceAttribute | Query instance attribute (including status) |
| `aliyun r-kvstore modify-security-ips` | ModifySecurityIps | Configure IP whitelist |
| `aliyun r-kvstore allocate-instance-public-connection` | AllocateInstancePublicConnection | Allocate public connection endpoint |
| `aliyun r-kvstore describe-db-instance-net-info` | DescribeDBInstanceNetInfo | Query instance network info |

## Key Parameters Reference

### create-tair-instance

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--biz-region-id` | Yes | Region ID, e.g. `cn-hangzhou` |
| `--instance-class` | Yes | Instance specification, e.g. `tair.rdb.1g` |
| `--instance-type` | Yes | Instance series: `tair_rdb` / `tair_scm` / `tair_essd` |
| `--vpc-id` | Yes | VPC ID |
| `--vswitch-id` | Yes | VSwitch ID |
| `--password` | No | Connection password (8-32 chars, at least 3 of: uppercase, lowercase, digits, special chars) |
| `--charge-type` | No | Billing method: `PostPaid` (pay-as-you-go) / `PrePaid` (subscription) |
| `--auto-pay` | No | Whether to auto pay |
| `--shard-type` | No | Shard type: `MASTER_SLAVE` (default) / `STAND_ALONE` |
| `--zone-id` | No | Zone ID |
| `--instance-name` | No | Instance name |

### describe-instance-attribute

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | Instance ID |

### modify-security-ips

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | Instance ID |
| `--security-ips` | Yes | Whitelist IPs, separated by commas |
| `--security-ip-group-name` | No | Whitelist group name |
| `--modify-mode` | No | Modify mode: `Cover` / `Append` / `Delete` |

### allocate-instance-public-connection

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | Instance ID |
| `--connection-string-prefix` | Yes | Public connection prefix (lowercase, 8-40 chars) |
| `--port` | Yes | Port number (1024-65535) |

### describe-db-instance-net-info

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | Instance ID |
