# M2 -- Refund Destination, Invoice and Withdrawal Linkage (CL-D)

Where the money goes, what happens to invoices, and how refunds interact
with balance withdrawal. Every customer-visible rule below ends at a manual
console entry: the refund path, the invoice reversal, the withdrawal
approval and the invoiced-amount figures are NOT queryable through this
skill's read whitelist -- answer with the rule + entry, degrade on numbers.

## 1. Destination branch (original path vs account balance)

Rule (as consistently relayed by support in the analyzed tickets, matching
the official refund-destinations page
`https://help.aliyun.com/zh/user-center/user-guide/refund-destinations`):

1. Refund normally returns along the ORIGINAL payment path within about
   2 business days.
2. For orders whose invoice has already been issued, the destination
   depends on the invoiceable amount of the account:
   - refund amount <= (current invoiceable amount + current-month
     non-invoiceable amount)  ->  original payment path is preferred;
   - refund amount  >  (that sum)  ->  the money goes directly to the
     Alibaba Cloud account balance.
3. Any refund reduces the account's invoiceable amount afterwards (see
   section 3 -- this is what can block a withdrawal).

**Degraded fields:** "current invoiceable amount" and "current-month
non-invoiceable amount" have NO query API in the whitelist. When the
customer needs the actual branch outcome, output
`STATUS: DEGRADED: invoiceable-amount figures unavailable`, and point to
the refund page, which itself shows the exact destination before submitting.
Never guess which branch applies.

## 2. Invoice (fapiao) reversal for already-invoiced orders

Manual steps to relay (from the invoice records page an agent cited):
`https://billing-cost.console.aliyun.com/invoice/home/record/aliyun`

1. Open the invoice management page in the billing console, locate the
   issued invoice for the order being refunded and start the reversal
   ("refund the invoice") there.
2. If the invoice has already been booked/used for deduction on the tax
   side, a red-letter confirmation must first be issued in the electronic
   tax bureau; the platform reversal then references it.
3. The order refund can only complete its money movement consistently with
   the invoice state -- advise sequencing: reverse the invoice first when
   it exists, then submit the unsubscription.

Invoice reversal is a human process with its own approvals; this skill
never submits it.

## 3. Withdrawal of the balance (why 90 CNY "sits stuck")

Support-verified position (no single authoritative page located -- relay as
the support position and let the withdrawal page be the checker):

- While PAY-AS-YOU-GO resources (ECS, SLB, ...) still exist under the
  account, the system reserves 100 CNY of the balance against overdue risk;
  a balance below/near that reserve cannot be withdrawn.
- A refund landing IN the balance raises the balance but also reduces the
  invoiceable amount, which can keep the withdrawal blocked even after the
  money arrives.
- To free the withdrawal: release all pay-as-you-go resources (stop is NOT
  release -- see M1 section 3), wait about 24 hours after the release, then
  apply for withdrawal manually in the billing console.
- Withdrawal approval itself is an offline review; its progress has no
  query API -- hand off to a human ticket with the account UID.

## 4. Vouchers and gifts at refund time

- Cash vouchers, coupons, extended service periods and other gifts attached
  to the refunded order are voided / cleared after the refund.
- The voucher-paid portion of a payment refunds only its residual value; an
  already-expired voucher is gone after unsubscription.
- Evidence hook: `python3 scripts/areas/unsubscribe_refund/ecs_unsubscribe_refund.py --estimate
  --billing-cycle <YYYY-MM>` lists the currently effective cash coupons
  (`cash_coupons_at_risk`) so the warning is grounded in the account's real
  holdings, not a generic sentence.

## 5. Order-type triage for money questions

| Object the customer names | Track | First evidence |
|---|---|---|
| Subscription ECS instance (`i-...`, prepaid) | refund track: eligibility + amount on refund page | `--inventory` ledger join |
| Pay-as-you-go ECS (`i-...`, postpaid) | release track: no refund exists; stop billing via manual release after backup | `--inventory` |
| Savings plan (`spn-...`) | special product: see M3 | `--inventory --instance-id spn-...` |
| Order number | order list page; orders are per-account -- confirm UID first | identity echo |
