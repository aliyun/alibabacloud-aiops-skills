# Terraform State Operations Reference

---

## Common State Commands

```bash
# List all resources in state
terraform state list

# Filter by type
terraform state list | grep alicloud_instance
terraform state list | grep alicloud_vpc

# View detailed attributes of a single resource
terraform state show alicloud_instance.ecs_web_01

# View complete state (JSON format)
terraform show -json

# Remove resource from state (does not delete cloud resource)
terraform state rm alicloud_instance.ecs_web_01

# Rename resource in state
terraform state mv alicloud_instance.old_name alicloud_instance.new_name

# Manually pull remote state
terraform state pull > backup.tfstate

# Manually push state (dangerous operation, use with caution)
terraform state push backup.tfstate

# Force unlock state (when state is locked)
terraform force-unlock <lock-id>
```

---

## State File JSON Structure

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

Key fields:
- `resources[].type`: Terraform resource type
- `resources[].name`: Resource name (corresponds to the identifier in HCL)
- `resources[].instances[].attributes`: All attribute values of the resource
- `resources[].instances[].dependencies`: List of other resource addresses this resource depends on

---

## Extracting Dependencies from State

```bash
# Method 1: Using terraform graph (requires graphviz)
terraform graph | dot -Tsvg > graph.svg

# Method 2: Extract from JSON state (Python)
terraform show -json | python3 -c "
import json, sys
state = json.load(sys.stdin)
resources = state.get('values', {}).get('root_module', {}).get('resources', [])
print(f'Total resources: {len(resources)}')
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

# Method 3: List all resources with their IDs
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

## Checking if a Resource is Already in State

```bash
# Check if a specific resource exists
terraform state list | grep "alicloud_instance.ecs_web_01"
# Non-empty return = exists, empty = does not exist

# Batch check (for idempotent imports)
check_in_state() {
  local resource="$1"
  terraform state list | grep -q "^${resource}$"
  return $?
}

if check_in_state "alicloud_vpc.vpc_prod_main"; then
  echo "Already in state, skipping import"
else
  terraform import alicloud_vpc.vpc_prod_main vpc-bp1xxx
fi
```

---

## State Backup and Recovery

```bash
# Backup state before import
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d_%H%M%S)

# Or use terraform state pull
terraform state pull > backup_$(date +%Y%m%d_%H%M%S).tfstate

# Restore state (use with caution)
cp terraform.tfstate.backup terraform.tfstate
# Or
terraform state push backup.tfstate
```

---

## Remote State (OSS Backend)

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

Migrating to remote state:
```bash
# 1. Add backend configuration to backend.tf
# 2. Execute migration
terraform init -migrate-state
# 3. Confirm migration
```

---

## Common State Issues

**Issue 1: State doesn't match HCL after import**
```bash
# View actual attribute values in state
terraform state show alicloud_instance.ecs_web_01
# Update HCL based on output to make both consistent
```

**Issue 2: Resource was manually deleted, still exists in state**
```bash
# Remove from state (won't delete cloud resource since it no longer exists)
terraform state rm alicloud_instance.ecs_web_01
```

**Issue 3: Resource ID changed (e.g., resource was recreated)**
```bash
# Remove old state first
terraform state rm alicloud_instance.ecs_web_01
# Then import new ID
terraform import alicloud_instance.ecs_web_01 i-bp1new_id
```

**Issue 4: State locked (during concurrent operations)**
```bash
# View lock info
terraform state pull | python3 -c "import json,sys; s=json.load(sys.stdin); print(s.get('lock_info','no lock'))"
# Force unlock (confirm no other operations are in progress)
terraform force-unlock <lock-id>
```
