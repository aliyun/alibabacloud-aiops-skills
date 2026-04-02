# Verification Methods

Step-by-step verification methods for Flink instance create/query operations.

## Mandatory rule

All executable examples in this document use:

```bash
python scripts/instance_ops.py <command> ...
```

Do not run raw `aliyun foasconsole` resource commands as substitutes.

## Pre-operation verification

### 1) Environment diagnostics

```bash
aliyun version
aliyun configure list
python scripts/instance_ops.py describe_regions
```

If the Python command fails with missing modules, follow `python-environment-setup.md`.

### 2) Region/network readiness (when create is needed)

```bash
python scripts/instance_ops.py describe_regions
python scripts/instance_ops.py describe_zones --region_id cn-hangzhou
```

If VPC/VSwitch is missing, provide explicit parameters before create execution.

## Operation verification pattern

For every create operation, follow:

1. execute create with required confirmation flag
2. run read-back verification
3. conclude status based on read-back result

### Example: create instance

```bash
python scripts/instance_ops.py create \
  --region_id cn-hangzhou \
  --name verify-demo \
  --instance_type PayAsYouGo \
  --vswitch_id vsw-xxx \
  --vpc_id vpc-xxx \
  --cpu 200 \
  --memory_gb 800 \
  --confirm
```

Read-back:

```bash
python scripts/instance_ops.py describe --region_id cn-hangzhou
```

### Example: create namespace

```bash
python scripts/instance_ops.py create_namespace \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx \
  --name verify-ns \
  --cpu 100 \
  --memory_gb 400 \
  --confirm
```

Read-back:

```bash
python scripts/instance_ops.py describe_namespaces \
  --region_id cn-hangzhou \
  --instance_id f-cn-xxx
```

## Failure verification

- Parse `error.code` and `error.message` from command output
- For create operations, also inspect `confirmation_check` for auditable `--confirm` evidence
- Apply retry policy in `output-handling.md`
- Retry only same operation with corrected parameters (max one retry)
- If unresolved, report as incomplete with remediation
- For lifecycle flows requiring both create steps, keep overall status non-completed when
  namespace create fails (for example `InsufficientResources`)

## References

- `core-execution-flow.md`
- `required-confirmation-model.md`
- `output-handling.md`
- `python-environment-setup.md`
