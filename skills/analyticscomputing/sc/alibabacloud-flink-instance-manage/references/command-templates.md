# Command Templates

Copy-paste ready command templates for all operations.

## Query Operations

### List all regions
```bash
python scripts/instance_ops.py describe_regions
```

### List zones in a region
```bash
python scripts/instance_ops.py describe_zones --region_id cn-beijing
```

### Query instances in a region
```bash
python scripts/instance_ops.py describe --region_id cn-beijing
```

### Query namespaces in an instance
```bash
python scripts/instance_ops.py describe_namespaces \
  --region_id cn-beijing \
  --instance_id f-cn-xxx
```

### List tags for resources
```bash
python scripts/instance_ops.py list_tags \
  --region_id cn-beijing \
  --resource_type vvpinstance \
  --resource_ids f-cn-xxx,f-cn-yyy
```

## Create Operations

### Create instance (PayAsYouGo) - using cu_count
```bash
python scripts/instance_ops.py create \
  --region_id cn-beijing \
  --name my-flink-instance \
  --instance_type PayAsYouGo \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cu_count 4 \
  --confirm
```

**Note**: `--cu_count N` = N cores + (N × 4) GB memory

### Create instance (PayAsYouGo) - using cpu + memory
```bash
python scripts/instance_ops.py create \
  --region_id cn-beijing \
  --name my-flink-instance \
  --instance_type PayAsYouGo \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cpu 4 \
  --memory_gb 16 \
  --confirm
```

### Create instance (Subscription)
```bash
python scripts/instance_ops.py create \
  --region_id cn-beijing \
  --name my-flink-instance \
  --instance_type Subscription \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cpu 4 \
  --memory_gb 16 \
  --period 12 \
  --confirm
```

### Create namespace (with resources)
```bash
python scripts/instance_ops.py create_namespace \
  --region_id cn-beijing \
  --instance_id f-cn-xxx \
  --name prod-namespace \
  --cpu 100 \
  --memory_gb 400 \
  --confirm
```

## Required Parameters Summary

| Command | Required Flags |
|---------|---------------|
| `describe_regions` | none |
| `describe_zones` | `--region_id` |
| `describe` | `--region_id` |
| `create` | `--region_id`, `--name`, `--instance_type`, `--vswitch_id`, `--vpc_id`, resource spec, `--confirm` |
| `describe_namespaces` | `--region_id`, `--instance_id` |
| `create_namespace` | `--region_id`, `--instance_id`, `--name`, `--cpu`, `--memory_gb`, `--confirm` (for new namespace) |
| `list_tags` | `--region_id`, `--resource_type` |

## Resource Specification for Create

**Option 1**: `--cu_count N`
- Automatically calculates: N cores + (N × 4) GB
- Example: `--cu_count 4` = 4 cores + 16 GB

**Option 2**: `--cpu N --memory_gb M`
- Both flags required together
- Example: `--cpu 4 --memory_gb 16`

**❌ Invalid**: `--cpu` alone or `--memory_gb` alone
