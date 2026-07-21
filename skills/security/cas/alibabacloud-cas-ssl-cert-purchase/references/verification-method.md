# Success Verification Method

Verification steps for the alibabacloud-cas-ssl-cert-purchase skill.

## 1. Verify Certificate Instance Status

After certificate application submission, check the instance status:

```bash
aliyun cas get-instance-detail --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE \
  --region $CERT_REGION \
  --instance-id "{{instance_id}}"
```

### Expected Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `inactive` | Instance not yet used | Normal before update-instance |
| `pending` | Application under review | Normal for OV/EV (1-5 business days) |
| `normal` | Certificate issued successfully | DV may complete in minutes |
| `willExpire` | Certificate expiring soon | Consider renewal |
| `expired` | Certificate has expired | Apply for new certificate |
| `closed` | Instance closed/refunded | No action possible |

## 2. Verify Async Task Result

After `apply-certificate`, poll the task:

```bash
aliyun cas get-task-attribute --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE \
  --region $CERT_REGION \
  --task-id "{{instance_id}}" \
  --task-type "ApplyCertificate"
```

> **[TODO verify]** `--task-id` currently reuses `instance_id`. Confirm against a real `apply-certificate` response whether a distinct task id is required.

### Expected Task Results

| TaskStatus | Meaning |
|------------|---------|
| `COMPLETED` | Application submitted successfully |
| `FAILED` | Application failed — check error message |
| `PENDING` | Still processing — retry after 30 seconds |

## 3. Verify BSS Purchase Result

After purchasing via `scripts/bss-purchase.sh create-instance`, verify the order:

```bash
bash scripts/bss-purchase.sh get-order-detail \
  --profile $CERT_PROFILE \
  --region $CERT_REGION \
  --order-id "{{order_id}}"
```

### Expected Results

- `OrderStatus` = `Paid` → Purchase successful
- `OrderStatus` = `Unpaid` → Payment pending, check account balance
- `OrderStatus` = `Cancelled` → Order cancelled

## 4. Verify Instance Appears in List

After purchase, confirm the new instance is visible:

```bash
aliyun cas list-instances --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-purchase/{session-id}" \
  --profile $CERT_PROFILE \
  --region $CERT_REGION \
  --status inactive \
  --keyword "{{instance_id}}"
```

The purchased instance should appear with status `inactive` and the correct spec.

## 5. Instance Status Meanings

See §1 "Expected Status Values" above for the full status/action table.
