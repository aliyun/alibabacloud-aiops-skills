# M4 -- Pre-Submission Notice and Confirmation Checklist (R2 gate / CL-F)

This is the OUTPUT GATE of the skill. Nothing counts as guidance until the
customer has seen Section 1 in full, and no assisted / special-approval
unsubscription should be requested before all six items of Section 2 have
been answered by the customer. Generate both sections with
`python3 scripts/areas/unsubscribe_refund/ecs_unsubscribe_refund.py --checklist` and paste the
output verbatim -- manual re-typing is where wording drifts.

## 1. Five-point notice (MANDATORY before any submission pointer)

Relay all five points; each one maps to a dispute that appeared in the
analyzed tickets when it was omitted.

1. **Eligibility** -- the instances eligible for self-refund (five-day
   no-reason or non-full) are exactly those listed on the refund page for
   this account; that page is the authority.
2. **Yearly limit** -- each user, per product, may use the five-day
   no-reason full refund on one instance per natural year (Jan 1 - Dec 31),
   and a subscription ECS instance shares that quota with resource packages
   and reserved instance coupons.
3. **Timing and destination** -- refunds normally return within about 2
   business days; when the refund exceeds the current invoiceable amount
   the money lands on the account balance instead of the original path.
4. **Gifts voided and retention is per resource** -- attached vouchers,
   coupons and extended service periods are voided and cleared after refund;
   the instance enters the "expired after refund" state where vCPU, memory
   and the fixed public IP are released within 24 hours and the cloud disks
   within 15 days (a disk is kept when "release disk with instance" is off).
5. **Amount and rules** -- the refund page shows the exact refundable
   amount: read it there before submitting; full rules at
   `https://help.aliyun.com/zh/user-center/cancel-subscription/`.

Add the data-retention line every time:

> After the refund the instance enters the "expired after refund" state:
> vCPU, memory and the fixed public IP are released within 24 hours, the
> cloud disks within 15 days (a disk is kept if "release disk with instance"
> is off). Take a snapshot before submitting. Before the resources are
> released you can still rescue the instance by renewing it manually in the
> ECS console, although data loss or a changed fixed public IP may remain.
> Stopping is NOT releasing; only release ends pay-as-you-go billing.

## 2. Six-item confirmation (customer replies to each line)

Template reused from a closed-loop ticket where the agent collected these
exact confirmations before an approved partial refund:

1. Refund reason (one factual line from the customer).
2. Target resources: instance id(s) and related order number(s) -- relay
   order numbers MASKED (e.g. `20**...**85`), never restate a full
   customer-supplied order number.
3. Voucher rule acknowledged: voucher-paid portions refund residual value
   only; expired vouchers are not reusable.
4. Billing reversion acknowledged: instances being deducted by the covered
   resource revert to normal pay-as-you-go billing once that resource is
   released.
5. Amount acknowledged: the exact figure shown on the refund page (this
   skill never states the final number; any relayed reference value carries
   the `ESTIMATE=... / AUTHORITATIVE=...` pair).
6. Repurchase limits acknowledged (e.g. a flexible-edition plan cannot be
   re-purchased after refund).

## 3. Manual entries to paste AFTER the gate has passed

| Purpose | Entry (customer performs it) |
|---|---|
| Self-service unsubscribe | `https://usercenter2.aliyun.com/refund/refund` |
| Refund center (billing console) | `https://billing-cost.console.aliyun.com/refund/refund` |
| Check whether an order/request exists | `https://billing-cost.console.aliyun.com/order/list` |
| Invoice reversal | `https://billing-cost.console.aliyun.com/invoice/home/record/aliyun` |
| Release a pay-as-you-go instance | `https://ecs.console.aliyun.com/server/region` |

## 4. What this skill never does

- It never submits, confirms, cancels or accelerates any refund, order,
  invoice or withdrawal -- the customer clicks; where a "confirmation tool"
  is involved, the customer clicks THAT too ("the product is unsubscribed
  only after you click the confirmation tool" -- a ticket where the
  customer assumed silence meant completion).
- It never claims a special approval will succeed; it prepares the six
  answers for the human ticket.
- It never states "your refund is in progress" without an order visible in
  the account's order list.
