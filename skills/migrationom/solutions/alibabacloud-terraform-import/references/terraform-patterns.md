# Terraform HCL 代码模板库

各资源类型的 HCL 模板，以及常见 plan diff 修复模式。

---

## Provider 配置

```hcl
terraform {
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.220.0"
    }
  }
}

provider "alicloud" {
  access_key = var.access_key
  secret_key = var.secret_key
  region     = var.region
}

variable "access_key" { sensitive = true }
variable "secret_key" { sensitive = true }
variable "region"     { default = "cn-hangzhou" }
```

---

## 网络资源模板

### VPC

```hcl
resource "alicloud_vpc" "vpc_<name>" {
  vpc_name    = "<name>"
  cidr_block  = "10.0.0.0/8"
  description = ""
  tags = {
    Env = "production"
  }
}
```

### VSwitch

```hcl
resource "alicloud_vswitch" "vsw_<name>" {
  vswitch_name = "<name>"
  vpc_id       = alicloud_vpc.vpc_<vpc_name>.id
  cidr_block   = "10.0.1.0/24"
  zone_id      = "cn-hangzhou-h"
  description  = ""
  tags = {}
}
```

### 安全组

```hcl
resource "alicloud_security_group" "sg_<name>" {
  security_group_name = "<name>"  # 注意：provider 1.239.0+ 已废弃 name 字段，使用 security_group_name
  vpc_id              = alicloud_vpc.vpc_<vpc_name>.id
  description         = ""
  tags = {}
}

# 入方向规则
resource "alicloud_security_group_rule" "sgr_<name>_ingress_80" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "80/80"
  security_group_id = alicloud_security_group.sg_<name>.id
  cidr_ip           = "0.0.0.0/0"
  policy            = "accept"
  priority          = 1
}

# 出方向规则（通常允许所有出流量）
resource "alicloud_security_group_rule" "sgr_<name>_egress_all" {
  type              = "egress"
  ip_protocol       = "all"
  port_range        = "-1/-1"
  security_group_id = alicloud_security_group.sg_<name>.id
  cidr_ip           = "0.0.0.0/0"
  policy            = "accept"
  priority          = 1
}
```

### EIP

```hcl
resource "alicloud_eip_address" "eip_<name>" {
  address_name         = "<name>"
  payment_type         = "PayAsYouGo"
  internet_charge_type = "PayByTraffic"
  bandwidth            = "100"
  isp                  = "BGP"
  tags = {}
}

resource "alicloud_eip_association" "eip_assoc_<name>" {
  allocation_id = alicloud_eip_address.eip_<name>.id
  instance_id   = alicloud_instance.ecs_<name>.id
  instance_type = "EcsInstance"
}
```

### NAT 网关

```hcl
resource "alicloud_nat_gateway" "nat_<name>" {
  vpc_id           = alicloud_vpc.vpc_<vpc_name>.id
  vswitch_id       = alicloud_vswitch.vsw_<vsw_name>.id
  nat_gateway_name = "<name>"
  nat_type         = "Enhanced"
  payment_type     = "PayAsYouGo"
  tags = {}
}

resource "alicloud_snat_entry" "snat_<name>" {
  snat_table_id     = alicloud_nat_gateway.nat_<name>.snat_table_ids
  source_vswitch_id = alicloud_vswitch.vsw_<vsw_name>.id
  snat_ip           = alicloud_eip_address.eip_<name>.ip_address
}
```

---

## 计算资源模板

### ECS 实例

```hcl
resource "alicloud_instance" "ecs_<name>" {
  instance_name        = "<name>"
  instance_type        = "ecs.c6.large"
  image_id             = "aliyun_3_x64_20G_alibase_20240528.vhd"
  system_disk_category = "cloud_essd"
  system_disk_size     = 40

  vswitch_id         = alicloud_vswitch.vsw_<vsw_name>.id
  security_groups    = [alicloud_security_group.sg_<name>.id]
  availability_zone  = "cn-hangzhou-h"

  internet_max_bandwidth_out = 0
  internet_charge_type       = "PayByTraffic"

  key_name     = "<key-pair-name>"
  password     = var.ecs_password  # 或用 key_name，不要硬编码密码

  description  = ""
  host_name    = "<hostname>"

  tags = {
    Env = "production"
  }

  lifecycle {
    ignore_changes = [image_id, password]
  }
}

variable "ecs_password" {
  sensitive = true
  default   = ""
}
```

### 云盘

```hcl
resource "alicloud_disk" "disk_<name>" {
  disk_name         = "<name>"
  availability_zone = "cn-hangzhou-h"
  category          = "cloud_essd"
  size              = 100
  performance_level = "PL1"
  description       = ""
  tags = {}
}

resource "alicloud_disk_attachment" "disk_attach_<name>" {
  disk_id     = alicloud_disk.disk_<name>.id
  instance_id = alicloud_instance.ecs_<name>.id
}
```

---

## 存储资源模板

### OSS Bucket

```hcl
resource "alicloud_oss_bucket" "bucket_<name>" {
  bucket = "<bucket-name>"

  acl = "private"  # private / public-read / public-read-write

  versioning {
    status = "Enabled"  # Enabled / Suspended
  }

  lifecycle_rule {
    id      = "rule-1"
    enabled = true
    prefix  = "logs/"

    expiration {
      days = 30
    }
  }

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "POST"]
    allowed_origins = ["https://example.com"]
    max_age_seconds = 3000
  }

  server_side_encryption_rule {
    sse_algorithm = "AES256"
  }

  tags = {
    Env = "production"
  }
}
```

---

## 数据库资源模板

### RDS MySQL

```hcl
resource "alicloud_db_instance" "rds_<name>" {
  engine           = "MySQL"
  engine_version   = "8.0"
  instance_type    = "rds.mysql.s2.large"
  instance_storage = 20
  instance_name    = "<name>"
  vswitch_id       = alicloud_vswitch.vsw_<vsw_name>.id
  security_ips     = ["10.0.0.0/8"]
  payment_type     = "Postpaid"

  tags = {}

  lifecycle {
    ignore_changes = [instance_storage]
  }
}

resource "alicloud_db_database" "db_<name>" {
  instance_id   = alicloud_db_instance.rds_<name>.id
  name          = "<db-name>"
  character_set = "utf8mb4"
  description   = ""
}

resource "alicloud_db_account" "dba_<name>" {
  db_instance_id   = alicloud_db_instance.rds_<name>.id
  account_name     = "<username>"
  account_password = var.rds_password
  account_type     = "Normal"  # Normal / Super

  lifecycle {
    ignore_changes = [account_password]
  }
}

variable "rds_password" { sensitive = true }
```

### Redis（KVStore）

```hcl
resource "alicloud_kvstore_instance" "redis_<name>" {
  db_instance_class = "redis.master.small.default"
  instance_name     = "<name>"
  vswitch_id        = alicloud_vswitch.vsw_<vsw_name>.id
  engine_version    = "7.0"
  instance_type     = "Redis"
  payment_type      = "PostPaid"
  security_ips      = ["10.0.0.0/8"]

  tags = {}

  lifecycle {
    ignore_changes = [password]
  }
}
```

### MongoDB（DDS）

```hcl
resource "alicloud_mongodb_instance" "mongo_<name>" {
  engine_version      = "6.0"
  db_instance_class   = "dds.mongo.mid"
  db_instance_storage = 10
  name                = "<name>"
  vswitch_id          = alicloud_vswitch.vsw_<vsw_name>.id
  security_ip_list    = ["10.0.0.0/8"]
  payment_type        = "PostPaid"

  tags = {}

  lifecycle {
    ignore_changes = [account_password]
  }
}
```

---

## 负载均衡模板

### SLB

```hcl
resource "alicloud_slb_load_balancer" "slb_<name>" {
  load_balancer_name = "<name>"
  load_balancer_spec = "slb.s2.small"
  vswitch_id         = alicloud_vswitch.vsw_<vsw_name>.id
  payment_type       = "PayAsYouGo"
  address_type       = "intranet"  # intranet / internet

  tags = {}
}

resource "alicloud_slb_listener" "slb_listener_<name>_80" {
  load_balancer_id          = alicloud_slb_load_balancer.slb_<name>.id
  backend_port              = 80
  frontend_port             = 80
  protocol                  = "http"
  bandwidth                 = -1
  sticky_session            = "off"
  health_check              = "on"
  health_check_uri          = "/health"
  health_check_connect_port = 80
}

resource "alicloud_slb_attachment" "slb_attach_<name>" {
  load_balancer_id = alicloud_slb_load_balancer.slb_<name>.id
  instance_ids     = [alicloud_instance.ecs_<name>.id]
  weight           = 100
}
```

---

## DNS 模板

```hcl
resource "alicloud_dns_domain" "domain_<name>" {
  domain_name = "example.com"
}

resource "alicloud_dns_record" "record_www_<name>" {
  name        = "example.com"
  host_record = "www"
  type        = "A"
  value       = "1.2.3.4"
  ttl         = 600
  priority    = 0  # 仅 MX 记录需要
}
```

---

## 常见 plan diff 修复模式

### 1. 标签格式不匹配

**现象**：`tags` 字段显示有变更，但值看起来一样

**原因**：阿里云 API 返回的 tag key/value 大小写或格式与 HCL 不一致

**修复**：
```hcl
# 从 terraform show 查看实际 state 中的 tags 格式，严格匹配
tags = {
  "Env"  = "production"   # 注意大小写
  "Team" = "infra"
}
```

### 2. 密码字段无法读取

**现象**：`password` 字段显示 `(known after apply)` 或有 diff

**修复**：
```hcl
lifecycle {
  ignore_changes = [password, account_password]
}
```

### 3. 系统盘大小漂移

**现象**：`system_disk_size` 显示有变更

**修复**：
```hcl
lifecycle {
  ignore_changes = [system_disk_size]
}
```

### 4. 镜像 ID 变更

**现象**：`image_id` 显示有变更（阿里云更新了基础镜像）

**修复**：
```hcl
lifecycle {
  ignore_changes = [image_id]
}
```

### 5. ECS `dry_run` 字段 ✅ 已验证

**现象**：ECS import 后 plan 显示 `+ dry_run = false`

**原因**：`dry_run` 是 provider 内部计算字段，不对应云上实际属性

**修复**：
```hcl
lifecycle {
  ignore_changes = [image_id, password, user_data, dry_run]
}
```

### 5. 安全组规则顺序

**现象**：安全组规则显示有变更，但规则内容相同

**原因**：Terraform 对规则顺序敏感，API 返回顺序可能不同

**修复**：确保 HCL 中规则顺序与 `terraform state show` 输出一致

### 6. RDS 存储大小

**现象**：`instance_storage` 显示有变更

**原因**：RDS 存储只能扩容不能缩容，实际值可能已被手动扩容

**修复**：
```hcl
lifecycle {
  ignore_changes = [instance_storage]
}
```

### 7. ECS 带宽设置

**现象**：`internet_max_bandwidth_out` 显示有变更

**修复**：从 `terraform state show` 读取实际值并更新 HCL

### 8. 安全 IP 列表格式

**现象**：`security_ips` 显示有变更

**原因**：API 返回的 IP 列表顺序或格式（CIDR vs IP）与 HCL 不一致

**修复**：
```hcl
security_ips = ["10.0.0.0/8", "172.16.0.0/12"]  # 严格匹配 state 中的格式
```

### 9. OSS Bucket 加密配置

**现象**：`server_side_encryption_rule` 显示有变更

**修复**：若不需要管理加密配置，移除该块；或严格匹配 state 中的值

### 10. NAT 网关 SNAT 表 ID

**现象**：`snat_table_ids` 是计算字段，无法在 HCL 中直接引用

**修复**：
```hcl
# 使用 split 处理多个 SNAT 表 ID
resource "alicloud_snat_entry" "snat_xxx" {
  snat_table_id = split(",", alicloud_nat_gateway.nat_xxx.snat_table_ids)[0]
  ...
}
```

### 11. ECS 实例 userData

**现象**：`user_data` 显示有变更

**修复**：
```hcl
lifecycle {
  ignore_changes = [user_data]
}
```

### 12. SLB 监听健康检查默认值

**现象**：健康检查相关字段显示有变更

**修复**：从 `terraform state show` 读取所有健康检查字段的实际值，在 HCL 中显式设置

### 13. VSwitch 可用区 ID 格式

**现象**：`zone_id` 显示有变更

**原因**：API 返回的可用区 ID 格式可能是 `cn-hangzhou-h` 或 `cn-hangzhou-h`（带后缀）

**修复**：严格使用 `terraform state show` 中的 zone_id 值

### 14. Redis 实例规格

**现象**：`db_instance_class` 显示有变更

**原因**：API 返回的规格名称可能与 Terraform provider 期望的格式不同

**修复**：参考 alicloud provider 文档中的规格名称格式

### 15. 计算字段（read-only）

**现象**：某些字段在 plan 中显示变更，但这些字段是只读的

**修复**：
```hcl
lifecycle {
  ignore_changes = [
    # 列出所有只读/计算字段
    create_time,
    expired_time,
    status,
  ]
}
```
