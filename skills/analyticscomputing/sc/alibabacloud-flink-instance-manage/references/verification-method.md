# Verification Methods

Step-by-step verification methods for Flink instance operations.

## Mandatory rule

All executable examples in this document use:

```bash
python scripts/instance_ops.py <command> ...
```

Do not run raw `aliyun foasconsole` resource commands as substitutes.

---

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

If VPC/VSwitch is missing, provide explicit parameters or use the skill network discovery flow.

---

## Operation verification pattern

For every write operation, follow:

1. execute write with required confirmation flag  
2. run read-back verification  
3. conclude completed/incomplete with evidence

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

### Example: tag + untag

```bash
python scripts/instance_ops.py tag_resources \
  --region_id cn-hangzhou \
  --resource_type vvpinstance \
  --resource_ids f-cn-xxx \
  --tags env:verify,suite:skill \
  --confirm

python scripts/instance_ops.py list_tags \
  --region_id cn-hangzhou \
  --resource_type vvpinstance \
  --resource_ids f-cn-xxx

python scripts/instance_ops.py untag_resources \
  --region_id cn-hangzhou \
  --resource_type vvpinstance \
  --resource_ids f-cn-xxx \
  --tag_keys env,suite \
  --confirm
```

### Example: delete instance

```bash
python scripts/instance_ops.py delete \
  --instance_id f-cn-xxx \
  --region_id cn-hangzhou \
  --force_confirmation

python scripts/instance_ops.py describe --region_id cn-hangzhou
```

---

## Failure verification

- Parse `error.code` and `error.message` from command output
- Apply retry policy in `output-handling.md`
- Retry only same operation with corrected parameters (max one retry)
- If unresolved, report as incomplete with remediation

---

## References

- `core-execution-flow.md`
- `required-confirmation-model.md`
- `output-handling.md`
- `python-environment-setup.md`
