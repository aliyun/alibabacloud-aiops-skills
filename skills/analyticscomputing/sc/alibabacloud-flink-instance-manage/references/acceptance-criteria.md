# Acceptance Criteria: alibabacloud-flink-instance-manage

**Scenario**: Alibaba Cloud Flink instance operations  
**Purpose**: Ensure execution stays on the skill wrapper and closes with read-back evidence.

---

## 1) Entrypoint correctness (must pass)

### ✅ Correct

```bash
python scripts/instance_ops.py describe --region_id cn-hangzhou
python scripts/instance_ops.py create --region_id cn-hangzhou --name demo --instance_type PayAsYouGo --vswitch_id vsw-xxx --vpc_id vpc-xxx --cpu 200 --memory_gb 800 --confirm
python scripts/instance_ops.py delete --instance_id f-cn-xxx --region_id cn-hangzhou --force_confirmation
```

### ❌ Incorrect

```bash
aliyun foasconsole DescribeInstances --region cn-hangzhou
aliyun foasconsole CreateInstance --region cn-hangzhou ...
```

Any raw `aliyun foasconsole` execution for resource operations fails acceptance.

---

## 2) Safety flag correctness (must pass)

- `create`, `renew`, `tag_resources`, `untag_resources`, namespace create/delete/modify require `--confirm`
- `modify_spec`, `convert` require `--confirm_price`
- `delete` requires `--force_confirmation`

Missing required confirmation flag fails acceptance.

---

## 3) Verification correctness (must pass)

A write operation is accepted only when both are true:

1. write response has `success: true` (or valid idempotent equivalent)
2. follow-up read-back confirms target state

Write-only success claims fail acceptance.

---

## 4) Retry correctness (must pass)

- Max attempts for the same write command: 2 (initial + one corrected retry)
- No blind retries
- No cross-operation fallback without explicit user approval
  - example: `modify_*` failure must not auto-switch to `create_*`

---

## 5) Security correctness (must pass)

- No AK/SK hardcoding in commands or scripts
- Use default credential chain (CLI profile or RAM role)
- No secret values in output/report

---

## 6) Completion report correctness (must pass)

Final response must include:

- `operation`
- `write_result`
- `verify_result` (read-back evidence)
- `final_status` (`completed` or `incomplete`)
- remediation if incomplete
