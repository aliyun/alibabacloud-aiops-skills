# Terraform 默认参数

Path A 使用 Terraform 模块部署时，以下参数作为默认值。**必须向用户展示并确认**，不可静默使用。

## 通用默认参数

| Parameter | Default | Notes |
|-----------|---------|-------|
| `region` | `cn-hangzhou` | 杭州；可改为 cn-beijing / cn-shanghai / cn-shenzhen |
| `availability_zone` | `cn-hangzhou-h` | 跟随 region 对应的可用区 |
| `vpc_cidr` | `172.16.0.0/12` | |
| `vswitch_cidr` | `172.16.0.0/24` | |
| `instance_type` | `ecs.c7.large` | 2C4G；GPU 场景改为 `ecs.gn6i-c8g1.2xlarge` |
| `instance_name` | `<solution-name>-server` | 以方案名为前缀 |
| `disk_size` | `40` (GB) | 系统盘 |
| `rds_instance_type` | `mysql.n2.medium.1` | 2C4G RDS |
| `password` | *(must ask user)* | Passwords are sensitive credentials — never generate or assume one. The user must provide it. |

## 确认格式示例

```
将使用以下参数部署，请确认或告知需要修改：
• Region: cn-hangzhou
• Instance type: ecs.c7.large
• VPC CIDR: 172.16.0.0/12
• Password: (请提供)
```

## 模块特定参数

不同模块有额外参数，运行时检查模块 README：
- Terraform Registry: `https://registry.terraform.io/modules/alibabacloud-automation/<module_name>/alicloud/latest`