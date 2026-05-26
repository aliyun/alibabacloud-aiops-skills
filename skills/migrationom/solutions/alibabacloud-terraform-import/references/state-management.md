# Terraform State 文件操作参考

---

## 常用 state 命令

```bash
# 列出 state 中所有资源
terraform state list

# 按类型过滤
terraform state list | grep alicloud_instance
terraform state list | grep alicloud_vpc

# 查看单个资源的详细属性
terraform state show alicloud_instance.ecs_web_01

# 查看完整 state（JSON 格式）
terraform show -json

# 从 state 移除资源（不删除云上资源）
terraform state rm alicloud_instance.ecs_web_01

# 重命名 state 中的资源
terraform state mv alicloud_instance.old_name alicloud_instance.new_name

# 手动拉取远程 state
terraform state pull > backup.tfstate

# 手动推送 state（危险操作，谨慎使用）
terraform state push backup.tfstate

# 强制解锁 state（state 被锁定时）
terraform force-unlock <lock-id>
```

---

## State 文件 JSON 结构

```json
{
  "version": 4,
  "terraform_version": "1.9.0",
  "serial": 42,
  "lineage": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "outputs": {},
  "resources": [
    {
      "mode": "managed",
      "type": "alicloud_vpc",
      "name": "vpc_prod_main",
      "provider": "provider[\"registry.terraform.io/aliyun/alicloud\"]",
      "instances": [
        {
          "schema_version": 0,
          "attributes": {
            "id": "vpc-bp1xxxxxxxxxxxxxxx",
            "vpc_name": "prod-main",
            "cidr_block": "10.0.0.0/8",
            "status": "Available",
            "tags": {
              "Env": "production"
            }
          },
          "sensitive_attributes": [],
          "dependencies": []
        }
      ]
    }
  ]
}
```

关键字段：
- `resources[].type`：Terraform 资源类型
- `resources[].name`：资源名称（对应 HCL 中的标识符）
- `resources[].instances[].attributes`：资源的所有属性值
- `resources[].instances[].dependencies`：依赖的其他资源地址列表

---

## 从 State 提取依赖关系

```bash
# 方法 1：使用 terraform graph（需要 graphviz）
terraform graph | dot -Tsvg > graph.svg

# 方法 2：从 JSON state 提取（Python）
terraform show -json | python3 -c "
import json, sys
state = json.load(sys.stdin)
resources = state.get('values', {}).get('root_module', {}).get('resources', [])
print(f'总资源数: {len(resources)}')
print()
for r in resources:
    addr = r['address']
    deps = r.get('depends_on', [])
    if deps:
        for d in deps:
            print(f'{d} --> {addr}')
    else:
        print(f'[root] --> {addr}')
"

# 方法 3：列出所有资源及其 ID
terraform show -json | python3 -c "
import json, sys
state = json.load(sys.stdin)
resources = state.get('values', {}).get('root_module', {}).get('resources', [])
for r in resources:
    rid = r.get('values', {}).get('id', 'N/A')
    print(f'{r[\"address\"]}: {rid}')
"
```

---

## 检查资源是否已在 State 中

```bash
# 检查特定资源是否存在
terraform state list | grep "alicloud_instance.ecs_web_01"
# 返回非空则已存在，返回空则不存在

# 批量检查（用于幂等性 import）
check_in_state() {
  local resource="$1"
  terraform state list | grep -q "^${resource}$"
  return $?
}

if check_in_state "alicloud_vpc.vpc_prod_main"; then
  echo "已在 state 中，跳过 import"
else
  terraform import alicloud_vpc.vpc_prod_main vpc-bp1xxx
fi
```

---

## State 备份与恢复

```bash
# 导入前备份 state
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d_%H%M%S)

# 或使用 terraform state pull
terraform state pull > backup_$(date +%Y%m%d_%H%M%S).tfstate

# 恢复 state（谨慎操作）
cp terraform.tfstate.backup terraform.tfstate
# 或
terraform state push backup.tfstate
```

---

## 远程 State（OSS Backend）

```hcl
# backend.tf
terraform {
  backend "oss" {
    bucket   = "my-terraform-state"
    prefix   = "alicloud-import"
    key      = "terraform.tfstate"
    region   = "cn-hangzhou"
    endpoint = "oss-cn-hangzhou.aliyuncs.com"
  }
}
```

迁移到远程 state：
```bash
# 1. 添加 backend 配置到 backend.tf
# 2. 执行迁移
terraform init -migrate-state
# 3. 确认迁移
```

---

## 常见 State 问题处理

**问题 1：import 后 state 与 HCL 不一致**
```bash
# 查看 state 中的实际属性值
terraform state show alicloud_instance.ecs_web_01
# 根据输出更新 HCL，使两者一致
```

**问题 2：资源被手动删除，state 中仍存在**
```bash
# 从 state 移除（不会删除云上资源，因为已不存在）
terraform state rm alicloud_instance.ecs_web_01
```

**问题 3：资源 ID 变更（如重建了资源）**
```bash
# 先移除旧 state
terraform state rm alicloud_instance.ecs_web_01
# 再 import 新 ID
terraform import alicloud_instance.ecs_web_01 i-bp1new_id
```

**问题 4：State 锁定（多人操作时）**
```bash
# 查看锁信息
terraform state pull | python3 -c "import json,sys; s=json.load(sys.stdin); print(s.get('lock_info','no lock'))"
# 强制解锁（确认没有其他操作在进行）
terraform force-unlock <lock-id>
```
