# Node Renew (F4) - bssopenapi renew-instance

Renew a **subscription** Lingjun node (subscription billing model). PAYG / pay-as-you-go nodes do **not** require renewal - `bssopenapi renew-instance` returns `Failure to check order` for them.

## CLI

```bash
safe_aliyun aliyun bssopenapi renew-instance \
  --endpoint business.aliyuncs.com \
  --instance-id <NodeId> \
  --product-code bccluster \
  --product-type bccluster_eflocomputing_public_cn \
  --renew-period <month> \
  --client-token <uuid>
```

## Endpoint selection (MANDATORY, billing gateway)

`bssopenapi` does **not** use eflo-controller regional endpoints; try in this order:

1. **Preferred** `--endpoint business.aliyuncs.com` (China-site central gateway), paired with `--product-type bccluster_eflocomputing_public_cn`.
2. **Fall back** to `--endpoint business.ap-southeast-1.aliyuncs.com` (International-site gateway), paired with `--product-type bccluster_eflocomputing_public_intl`, when the first one fails. "Failure" means: network-level failure (connection refused / timeout / DNS) or a site-mismatch business error (e.g. `Product code is invalid` / `NotApplicable`).
3. Still failing after the fallback -> report as [FAIL] execution failure; do not try any other endpoint.

Note: keep the **same** `--client-token` UUID across the fallback retry (idempotency). Under the test region `cn-wulanchabu-test-6`, `safe_aliyun` still auto-appends `--insecure`; the billing gateway accepts it.

## Parameters

| Flag | Required (CLI?) | Required (Business?) | Notes |
|---|---|---|---|
| `--instance-id` | [OK] | [OK] | Lingjun `NodeId`, e.g., `e01-cn-aaa` |
| `--product-code` | [OK] | [OK] | **fixed `bccluster`** |
| `--product-type` | [BLOCK] optional | [OK] business-required | China: `bccluster_eflocomputing_public_cn` ; International: `bccluster_eflocomputing_public_intl` |
| `--renew-period` | [OK] | [OK] | months; allowed `1..9`, `12`, `24`, `36`. **`forbidden_inference`** |
| `--client-token` | [BLOCK] | [OK] business-required | UUID; **same value** across retries to ensure idempotency |

`--client-token` empty -> multiple retries can create duplicate orders. The Agent **must** generate one UUID before Phase 1 and reuse it through Phase 2 + retries.

## Pre-Check

```bash
safe_aliyun aliyun eflo-controller describe-node \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId>
```

Verify:

- `BillingType  in  {PrePaid, Subscription}` - proceed.
- `BillingType = PostPaid` - abort, this is a PAYG node, no renewal flow.
- Read `ExpiredTime` for the danger box.

## Confirmation (mandatory, single step)

The danger box and the parameter confirmation table are shown in **one message**, ending with the closing prompt (see `render.confirm_prompt` in `lib/core/i18n.sh`); the user replies the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`) to submit. The danger box must show:

- `InstanceId`, current `ExpiredTime`, target `RenewPeriod` (months), expected new expiry, `ProductType`.

## Verify

```bash
# Verify order succeeded
safe_aliyun aliyun bssopenapi query-orders \
  --product-code bccluster --page-num 1 --page-size 20 \
  --create-time-start <ISO8601-just-before-submit>
# Inspect: .Data.OrderList.Order[].Status == "Success"
#          and .Data.OrderList.Order[].OrderType == "Renew"
```

```bash
# Verify expiry advanced
safe_aliyun aliyun eflo-controller describe-node \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId>
# expect: .ExpiredTime advanced by <RenewPeriod> months
```

## Common errors

| Code | Cause | Fix |
|---|---|---|
| `Failure to check order` | wrong `ProductCode` / `ProductType`; PAYG node | use `bccluster` + region-correct ProductType; verify `BillingType` first |
| `InvalidProductType` | typo (`lingjun` etc.) | use `bccluster_eflocomputing_public_cn` (China) / `..._intl` |
| `MissingParameter` on `RenewPeriod` | omitted | re-elicit; allowed values 1..9, 12, 24, 36 |
| `IdempotenceParameterMismatch` | same `ClientToken` reused with different parameters | generate a new UUID for a different request |
| `OrderQuantityInvalid` | exceeds account quota | contact account manager |

## Idempotency hard rule

If a 5xx / network error occurs **after** the request was sent but before a response was received:

1. **Do not** silently re-issue with a fresh UUID.
2. Query `bssopenapi query-orders --client-token <same-uuid>` (if supported) or by `--create-time-start` window of the last 5 min, looking for an order with the same `InstanceId` + `OrderType=Renew`.
3. If found -> treat as success, jump to verification.
4. If not found -> **safe** to retry with the **same** `ClientToken`.

Skipping this idempotency loop and re-issuing a fresh UUID is self-violation V2 (skipping the submission precondition checks); non-retryable.
