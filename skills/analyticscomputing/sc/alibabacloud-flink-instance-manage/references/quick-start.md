# alibabacloud-flink-instance-manage

Alibaba Cloud Flink portal operations - Python CLI for managing Flink instances.

## Quick Start

### 1. Install

```bash
pip install -r assets/requirements.txt
```

### 2. Configure

```bash
aliyun configure
aliyun configure list
```

### 3. Run

```bash
# List instances
python scripts/instance_ops.py describe --region_id cn-hangzhou

# Create instance
python scripts/instance_ops.py create \
  --region_id cn-hangzhou \
  --name my-instance \
  --instance_type PayAsYouGo \
  --zone_id cn-hangzhou-g \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cpu 200 \
  --memory_gb 800 \
  --confirm
```

### 4. Core lifecycle minimal chain

Use one instance ID for the full chain:

```bash
# 1) create (capture InstanceId from JSON)
python scripts/instance_ops.py create ... --confirm

# 2) tag + verify
python scripts/instance_ops.py tag_resources --region_id cn-hangzhou --resource_type vvpinstance --resource_ids f-cn-xxx --tags env:test --confirm
python scripts/instance_ops.py list_tags --region_id cn-hangzhou --resource_type vvpinstance --resource_ids f-cn-xxx

# 3) untag + verify
python scripts/instance_ops.py untag_resources --region_id cn-hangzhou --resource_type vvpinstance --resource_ids f-cn-xxx --tag_keys env --confirm
python scripts/instance_ops.py list_tags --region_id cn-hangzhou --resource_type vvpinstance --resource_ids f-cn-xxx

# 4) query + delete + verify
python scripts/instance_ops.py describe --region_id cn-hangzhou
python scripts/instance_ops.py delete --instance_id f-cn-xxx --region_id cn-hangzhou --force_confirmation
python scripts/instance_ops.py describe --region_id cn-hangzhou
```

## Commands

| Category | Commands |
|----------|----------|
| Instance | `create`, `describe`, `modify_spec`, `delete`, `renew`, `convert` |
| Namespace | `create_namespace`, `describe_namespaces`, `modify_namespace_spec` |
| Tag | `tag_resources`, `list_tags`, `untag_resources` |
| Query | `describe_regions`, `describe_zones` |

## Safety Checks

| Operation | Flag |
|-----------|------|
| Create/Renew/Tag/Untag | `--confirm` |
| Modify Spec/Convert | `--confirm_price` |
| Delete | `--force_confirmation` |

## Documentation

| Document | Purpose |
|----------|---------|
| `../SKILL.md` | Main skill instructions and workflow |
| `required-confirmation-model.md` | Confirmation gate and flag mapping |
| `core-execution-flow.md` | Operation command flow |
| `e2e-playbooks.md` | End-to-end completion playbooks |
| `output-handling.md` | Output handling and retry policy |
| `python-environment-setup.md` | Setup guide |
| `related-apis.md` | API reference |

## Output

```json
{
  "success": true,
  "operation": "describe",
  "data": {...},
  "request_id": "..."
}
```

Exit codes: `0` = success, `1` = error.

