# Quick Start

Create or query Alibaba Cloud Flink VVP instances and namespaces, and query or manage Flink AI Service.

## Trigger Recognition

Use this skill when request is about:
- Flink instance create/query
- Flink namespace create/query
- Flink region/zone/tag queries
- Flink AI Service status, activation, deactivation, free quota, or closure protection

Do not use this skill for:
- Flink SQL or Flink jobs
- Other Alibaba Cloud services (ECS, Kafka, OSS, DataWorks)
- Instance or namespace updates and deletion

## 1) Install Dependencies

```bash
pip install -r assets/requirements.txt
```

## 2) Configure Credentials

```bash
aliyun configure
aliyun configure list
```

## 3) Run Read-only Checks

```bash
python scripts/instance_ops.py describe_regions
python scripts/instance_ops.py describe_zones --region_id cn-hangzhou
python scripts/instance_ops.py describe --region_id cn-hangzhou
```

## 4) Create Instance and Verify

```bash
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

python scripts/instance_ops.py describe --region_id cn-hangzhou
```

## 5) Create Namespace and Verify

```bash
python scripts/instance_ops.py create_namespace \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --name prod-ns \
  --cpu 100 \
  --memory_gb 400 \
  --confirm

python scripts/instance_ops.py describe_namespaces \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx
```

## Command Scope

| Category | Commands |
|----------|----------|
| Query | `describe_regions`, `describe_zones`, `describe`, `describe_namespaces`, `list_tags` |
| Create | `create`, `create_namespace` |
| AI service queries | `get_flink_ai_service`, `get_flink_ai_service_free_quota` |
| AI service changes | `open_flink_ai_service`, `close_flink_ai_service`, `modify_ai_service_protection` |

## Required Confirmation

| Operation | Flag |
|-----------|------|
| `create` | `--confirm` |
| `create_namespace` | `--confirm` |
| AI service activation, deactivation, and closure protection changes | `--confirm` |

## Reference Map

| Document | Purpose |
|----------|---------|
| `../SKILL.md` | Main skill instructions and workflow |
| `trigger-recognition-guide.md` | Trigger and rejection examples |
| `core-execution-flow.md` | Standard operation flow |
| `parameter-validation.md` | Parameter checklist |
| `verification-method.md` | Read-back verification methods |
| `output-handling.md` | Retry and error handling |
| `common-failures.md` | Typical mistakes and fixes |
| `python-environment-setup.md` | Python setup guide |
| `related-apis.md` | API command mapping |
| `flink-ai-service.md` | AI service session setup, commands, and verification |

## Output Shape

```json
{
  "success": true,
  "operation": "describe",
  "data": {},
  "request_id": "..."
}
```

Exit codes: `0` = success, `1` = error.
