# Core execution flow

This document defines the execution flow for Alibaba Cloud Flink VVP instance operations.

## When to Use This Skill

**Trigger when user request is about Flink instance/namespace lifecycle create/query.**

### English triggers
- "create a Flink instance" / "create Flink"
- "query Flink instance" / "describe Flink"
- "list Flink namespaces" / "query namespace"
- "what regions support Flink" / "Flink regions"
- "Flink VVP" / "Flink on Cloud"

### Chinese triggers (中文触发词)
- "创建Flink实例" / "创建实时计算实例"
- "查询Flink实例" / "查询实例信息"
- "创建命名空间" / "Flink命名空间"
- "Flink VVP实例" / "实时计算Flink版"
- "查询Flink区域" / "Flink可用区"

### Explicitly DO NOT trigger for
- Flink SQL queries ("运行Flink SQL", "Flink job")
- Other Alibaba Cloud services (ECS, Kafka, OSS, DataWorks)
- Update/delete operations (拒绝此类请求并说明scope)

## Execution Entry Point

Use the Python script as the default execution entrypoint.
For initial validation, run a query-only command.

```bash
python scripts/instance_ops.py describe_regions
```

## 1) Lifecycle chain

Use this minimal chain for end-to-end requests:

1. discover target scope
2. create resource
3. query read-back verification

Rules:

- Capture `InstanceId` from `create` response and keep it as the single target.
- Do not switch to a different instance in the same chain unless user explicitly approves.
- If resource is not visible immediately after create, use repeated read checks
  before deciding retry/failure.
- Do not mark lifecycle flow completed when namespace create fails.

## 2) Discover and inspect

```bash
python scripts/instance_ops.py describe_regions
python scripts/instance_ops.py describe --region_id cn-hangzhou
python scripts/instance_ops.py describe_zones --region_id cn-hangzhou
```

## 3) Create instance

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

If required network parameters (`--vpc_id`, `--vswitch_id`) are missing, stop and ask
user to provide explicit values. Do not fabricate values.

```bash
python scripts/instance_ops.py describe --region_id cn-hangzhou
```

## 4) Create namespace

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

## 5) Query tag state

```bash
python scripts/instance_ops.py list_tags \
  --region_id cn-hangzhou \
  --resource_type vvpinstance \
  --resource_ids f-cn-xxx
```

## 6) Completion reminders

- Every create command must have a follow-up read check (`describe*` or `list*`).
- Report completion based on read-back result, not create response alone.
- Max attempts: 2 total for the same operation (initial + one corrected retry).
- Keep auditable confirmation evidence in output (`SafetyCheckRequired` or `--confirm`).
- For lifecycle requests requiring instance+namespace create, `completed` means both
  create operations succeeded.
