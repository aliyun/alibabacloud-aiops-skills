# Core execution flow

Use the Python script as the default execution entrypoint.
For initial validation, run a read-only command.

```bash
python scripts/instance_ops.py describe_regions
```

## 3.0 Core lifecycle chain (same-instance, evaluation critical)

Use this minimal chain for end-to-end lifecycle requests:

1. create instance
2. tag resources
3. untag resources
4. describe instance
5. delete instance

Rules:

- Capture `InstanceId` from `create` response and keep it as the single target.
- Do not switch to a different instance in the same chain unless user explicitly
  approves.
- If instance is not ready for tag/delete, use repeated `describe` read checks
  before deciding retry/failure.

## 3.1 Discover and inspect

```bash
python scripts/instance_ops.py describe_regions
python scripts/instance_ops.py describe --region_id cn-hangzhou
python scripts/instance_ops.py describe_zones --region_id cn-hangzhou
```

## 3.2 Create instance

```bash
python scripts/instance_ops.py create \
  --region_id cn-hangzhou \
  --name my-flink-instance \
  --instance_type PayAsYouGo \
  --zone_id cn-hangzhou-g \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cpu 200 \
  --memory_gb 800 \
  --confirm
```

```bash
python scripts/instance_ops.py describe --region_id cn-hangzhou
```

## 3.3 Manage namespace

```bash
python scripts/instance_ops.py create_namespace \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --name prod-ns \
  --cpu 100 \
  --memory_gb 400 \
  --confirm
```

```bash
python scripts/instance_ops.py describe_namespaces \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx
```

## 3.4 Scale and billing operations

```bash
python scripts/instance_ops.py modify_spec \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --new_cu_count 300 \
  --confirm_price
```

```bash
python scripts/instance_ops.py describe --region_id cn-hangzhou
```

```bash
python scripts/instance_ops.py convert \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --target_type Subscription \
  --period 1 \
  --confirm_price
```

## 3.5 Tag operations

```bash
python scripts/instance_ops.py tag_resources \
  --region_id cn-hangzhou \
  --resource_type vvpinstance \
  --resource_ids f-cn-xxx \
  --tags env:prod,team:data \
  --confirm
```

```bash
python scripts/instance_ops.py list_tags \
  --region_id cn-hangzhou \
  --resource_type vvpinstance \
  --resource_ids f-cn-xxx
```

## 3.6 Cleanup order

If non-default namespaces exist and user requested cleanup, delete those namespaces
before deleting the instance. For core create/tag/query/delete flows without
namespace operations, run direct instance deletion.

```bash
python scripts/instance_ops.py delete_namespace \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --name prod-ns \
  --confirm

python scripts/instance_ops.py delete \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --force_confirmation
```

```bash
python scripts/instance_ops.py describe --region_id cn-hangzhou
```

## 3.7 Completion reminders

- Every write command must have a follow-up read check (`describe*` or `list*`).
- For delete cleanup, verify both namespace cleanup and instance absence.
- For tag operations, verify every expected tag key/value is present.
