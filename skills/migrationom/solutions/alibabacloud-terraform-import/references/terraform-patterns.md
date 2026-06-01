# Terraform HCL Code Template Library

HCL templates for each resource type, plus common plan diff fix patterns.

---

## Provider Configuration

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
  region               = var.region
  configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-terraform-import"
}

variable "region" { default = "cn-hangzhou" }
```

---

## Networking Resource Templates

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

### Security Group

```hcl
resource "alicloud_security_group" "sg_<name>" {
  security_group_name = "<name>"  # Note: provider 1.239.0+ deprecated the name field, use security_group_name
  vpc_id              = alicloud_vpc.vpc_<vpc_name>.id
  description         = ""
  tags = {}
}

# Ingress rule
resource "alicloud_security_group_rule" "sgr_<name>_ingress_80" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "80/80"
  security_group_id = alicloud_security_group.sg_<name>.id
  cidr_ip           = "0.0.0.0/0"
  policy            = "accept"
  priority          = 1
}

# Egress rule (typically allow all outbound traffic)
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

### NAT Gateway

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

## Compute Resource Templates

### ECS Instance

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
  password     = var.ecs_password  # Or use key_name; never hardcode passwords

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

### Disk

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

## Storage Resource Templates

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

## Database Resource Templates

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

### Redis (KVStore)

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

### MongoDB (DDS)

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

## Load Balancing Templates

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

## DNS Templates

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
  priority    = 0  # Only required for MX records
}
```

---

## Common Plan Diff Fix Patterns

### 1. Tag format mismatch

**Symptom**: `tags` field shows changes, but values look identical

**Cause**: Tag key/value case or format returned by Alibaba Cloud API differs from HCL

**Fix**:
```hcl
# Check actual tags format in state via terraform show, match exactly
tags = {
  "Env"  = "production"   # Note case sensitivity
  "Team" = "infra"
}
```

### 2. Password field unreadable

**Symptom**: `password` field shows `(known after apply)` or has diff

**Fix**:
```hcl
lifecycle {
  ignore_changes = [password, account_password]
}
```

### 3. System disk size drift

**Symptom**: `system_disk_size` shows changes

**Fix**:
```hcl
lifecycle {
  ignore_changes = [system_disk_size]
}
```

### 4. Image ID change

**Symptom**: `image_id` shows changes (Alibaba Cloud updated base image)

**Fix**:
```hcl
lifecycle {
  ignore_changes = [image_id]
}
```

### 5. ECS `dry_run` field (verified)

**Symptom**: ECS import followed by plan shows `+ dry_run = false`

**Cause**: `dry_run` is a provider-internal computed field, not a real cloud attribute

**Fix**:
```hcl
lifecycle {
  ignore_changes = [image_id, password, user_data, dry_run]
}
```

### 6. Security group rule ordering

**Symptom**: Security group rules show changes but rule content is identical

**Cause**: Terraform is sensitive to rule ordering; API return order may differ

**Fix**: Ensure HCL rule order matches `terraform state show` output

### 7. RDS storage size

**Symptom**: `instance_storage` shows changes

**Cause**: RDS storage can only be scaled up, not down; actual value may have been manually expanded

**Fix**:
```hcl
lifecycle {
  ignore_changes = [instance_storage]
}
```

### 8. ECS bandwidth settings

**Symptom**: `internet_max_bandwidth_out` shows changes

**Fix**: Read actual value from `terraform state show` and update HCL

### 9. Security IP list format

**Symptom**: `security_ips` shows changes

**Cause**: IP list order or format (CIDR vs IP) returned by API differs from HCL

**Fix**:
```hcl
security_ips = ["10.0.0.0/8", "172.16.0.0/12"]  # Exactly match format in state
```

### 10. OSS Bucket encryption configuration

**Symptom**: `server_side_encryption_rule` shows changes

**Fix**: If encryption config management is not needed, remove the block; or exactly match values in state

### 11. NAT Gateway SNAT table ID

**Symptom**: `snat_table_ids` is a computed field that cannot be directly referenced in HCL

**Fix**:
```hcl
# Use split to handle multiple SNAT table IDs
resource "alicloud_snat_entry" "snat_xxx" {
  snat_table_id = split(",", alicloud_nat_gateway.nat_xxx.snat_table_ids)[0]
  ...
}
```

### 12. ECS instance userData

**Symptom**: `user_data` shows changes

**Fix**:
```hcl
lifecycle {
  ignore_changes = [user_data]
}
```

### 13. SLB listener health check defaults

**Symptom**: Health check related fields show changes

**Fix**: Read all health check field actual values from `terraform state show` and explicitly set them in HCL

### 14. VSwitch availability zone ID format

**Symptom**: `zone_id` shows changes

**Cause**: Availability zone ID format returned by API may differ

**Fix**: Use the exact zone_id value from `terraform state show`

### 15. Redis instance class

**Symptom**: `db_instance_class` shows changes

**Cause**: Instance class name returned by API may differ from what the Terraform provider expects

**Fix**: Refer to alicloud provider documentation for instance class name format

### 16. Computed fields (read-only)

**Symptom**: Some fields show changes in plan, but these fields are read-only

**Fix**:
```hcl
lifecycle {
  ignore_changes = [
    # List all read-only/computed fields
    create_time,
    expired_time,
    status,
  ]
}
```
