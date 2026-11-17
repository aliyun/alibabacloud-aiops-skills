# M2: Billing Under the Unlimited (No Performance Constraint) Mode

Why a **prepaid** (subscription) burstable instance grows a **postpaid**
bill line, what it is made of, and where the money conversation must stop.
**Freshness rule:** rates and console paths below come from this tier's
ticket evidence and linked official documents; the current official pages are
the authority and require human re-verification before release.

## The mechanic (misconception: "I paid for the year, this bill is wrong")

- With the unlimited (no performance constraint) mode ON, after the accrued
  credits and then the **advanced credits** are spent, the instance keeps
  running above baseline by consuming **excess credits**. Excess credits are
  billed **pay-as-you-go** even on a subscription instance — the bill item
  is the "excess credits" postpaid line (tickets T-2F07C4BD, T-E42721B9).
- Spending order above baseline: accrued credits -> advanced credits ->
  excess credits (billed). When usage drops, new credits repay the advanced
  portion first, so the balance looks frozen while the bill keeps growing
  retroactively (T-E42721B9).
- Rate in this tier's ticket evidence: **0.005 CNY per credit**
  (ticket T-5664EC80). Quote it only with the official fee page and the
  "verify against the current price" note. The monthly total depends on real
  usage above baseline and its duration — it **cannot** be pre-computed
  exactly (support could not either).
- Sources:
  - Excess-credit fee: https://help.aliyun.com/document_detail/90581.html#section-lqi-vqf-dsc
  - Burstable billing: https://help.aliyun.com/zh/ecs/user-guide/billing.md
  - Bill detail entry: https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance

## Recognizing the charge from customer input

- The entry script matches the pasted bill text against the excess-credit
  pattern ("excess credit..." tokens). Credit-related but unmatched text is
  returned as INCONCLUSIVE and the Agent must ask for the exact billing-item
  label — never guess a charge identity.
- A bill label in the customer's own console language may differ from the
  English tokens above; the customer pasting the exact item name from the
  bill export resolves that.

## Why no one warned them (misconception: "the balance alert should have caught this")

- The **account cost/balance alert** and the **CloudMonitor CPU-credit
  threshold alarm** are two independent features (root cause of tickets
  T-6F237607, T-0495147E). There is no default real-time notice for each
  excess-credit accrual; the credit alarm must be configured (see
  [monitoring-setup.md](burstable-instance-guide__monitoring-setup.md)) and the cost alert separately
  (https://help.aliyun.com/zh/user-center/cost-alert — daily SMS/email/
  station-letter reminders per the official page).
- Turning the mode OFF stops the item **going forward**, and immediately
  pins the instance at baseline — always emit the consequence warning first
  ([mode-switch-guide.md](burstable-instance-guide__mode-switch-guide.md)); a workload above baseline
  will slow down or look unreachable (real lesson: site down after switch
  off, ticket T-2F07C4BD).

## Cost-reducing routes (customer-executed only)

1. Switch the unlimited mode OFF in the console (stop the accrual; accept
   baseline performance) — steps in [mode-switch-guide.md](burstable-instance-guide__mode-switch-guide.md).
2. Reduce CPU above baseline (schedule jobs off-peak, cap threads, move
   bursty components elsewhere).
3. Move to a non-burstable family (c/g series) where sustained high CPU is
   the purchased spec — decision rules in
   [credit-rules.md](burstable-instance-guide__credit-rules.md) and the sizing topic.

## Hard scope boundary (commercial)

- Fee review, refunds, waivers, vouchers/coupons and compensation are
  **human commercial processes**. Support precedent (30- and 50-CNY experience
  vouchers, tickets T-6F237607 / T-0495147E) proves the outcome is a human
  decision; this skill only explains the rule and hands off:
  "Bill review and fee handling require a human billing ticket — please
  submit one selecting the billing issue category."
