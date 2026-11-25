# Fees and refunds guide: rule-based recompute and evidence pack

Scope: a dispute about a refund, a downgrade credit, an unexpected charge, or a fee the
customer ties to a platform action. Related: [migration checklist](migration-checklist.md),
[incident and SLA](incident-sla-guide.md), [hand-off boundaries](handoff-boundaries.md).

## Boundary first

This skill has no billing API. It does not read the bill, does not quote a price, and cannot
decide any waiver, adjustment, or voucher. It only applies the published formula to numbers the
customer supplies, points them at the self-service evidence, and packages an escalation.

## Apply the published formula to the customer's own numbers

- Downgrade refund = (order amount actually paid - consumed amount) x (new-vs-old config price
  ratio). The consumed amount uses the OFFICIAL LIST price daily rate x used duration, not the
  discounted price the customer paid.
  Doc: https://help.aliyun.com/zh/user-center/description-of-downgrade-refund-rules
- Non-full unsubscribe refund = order amount actually paid - consumed amount, where consumed is
  again computed at the official list price x used duration. Downgrade during renewal is gated
  by the 15-day-before-expiry window.
  Docs: https://help.aliyun.com/zh/user-center/cancel-subscription/ ,
  https://help.aliyun.com/zh/ecs/downgrade-instance-configurations-during-renewal
- Burstable-performance instances: sustained CPU above the baseline consumes earned credits, and
  in unlimited mode extra credit fees are billed on top. Verify the hourly figures yourself;
  do not assert a single number without the customer's bill.
  Doc: https://help.aliyun.com/zh/ecs/user-guide/billing

## Self-service evidence the customer gathers

- Bill by instance with an hourly filter:
  https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance
- Vouchers / coupons received: https://billing-cost.console.aliyun.com/coupons/coupon
- Refund destinations: https://help.aliyun.com/zh/user-center/user-guide/refund-destinations
- The customer exports the CSV and screenshots the hourly line and the CPU monitor curve.

## Escalation evidence pack (hand to a billing specialist)

- [ ] instance id and the disputed billing period
- [ ] exported hourly cost detail (CSV) and the CPU monitor screenshot
- [ ] the order / refund page amount screenshot
- [ ] the notification or open-time the customer relies on
- [ ] a short timeline of prior tickets and calls

## Hard limits to state plainly (these came straight from resolved tickets)

- Post-paid (pay-as-you-go) consumption that already occurred cannot be refunded, waived, or
  converted into a subscription; only a forward switch to fixed-bandwidth billing is possible.
- A goodwill voucher issued for service experience is explicitly "not compensation" and
  "one-time only"; it is a specialist decision, not an admission of fault.
- A negotiated manual refund path and a self-service unsubscribe are mutually exclusive: confirm
  the on-page amount before submitting, because self-service unsubscribing can void the manual
  goodwill deal that was pending.
- The platform does not retain historical per-process CPU, so past usage cannot be re-derived
  after the fact; real-time tools only. Set a high-consumption alert going forward.

## Wording for the "you should just pay me" expectation

Explain the SLA/compensation routes are application-based and that any voucher is a manual
discretionary goodwill action reviewed by a specialist. Offer to assemble the evidence pack and
name the channel. Never promise an amount or an approval.
