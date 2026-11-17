# Renewal / Unsubscription / Refund / Extension: rules and manual workflows

Everything on this page is either a rule statement with an evidence tag or a
MANUAL workflow. This skill executes none of these actions: renewing,
unsubscribing, refunding, voiding orders and submitting extension requests
are all performed by the customer in the console or by human support. See
`lifecycle-rules.md` for the tag legend.

## 1. Renewal

| Rule / step | Detail | Source |
|---|---|---|
| Authoritative expiry first | Always take `ExpiredTime` from the API (the diagnosis script cross-checks it against the billing-side query). Never accept customer arithmetic on order numbers: a bandwidth-upgrade order was once mistaken for an extension order. | [ticket:T-263837C7] [ticket:T-CB867A71] |
| Renew inside the retention window | A subscription instance stopped by expiry can be renewed and restored only inside the 15-day retention window `[TO VERIFY]`; after release, renewal is impossible. | [ticket:T-C12BF6F7] |
| Auto-renewal state | The script READS the auto-renewal attribute (RenewalStatus / AutoRenewEnabled) and reports it. Changing it is a manual console action; the skill never modifies it. | verified API + design rule |
| Renewal-time downgrade | Renewal can be combined with a configuration downgrade to cut cost -- manual ordering, out of scope here. | [doc:https://help.aliyun.com/zh/ecs/user-guide/downgrade-instance-configurations-during-renewal.md] [doc:https://help.aliyun.com/zh/ecs/user-guide/renewal-change.md] |

## 2. Unsubscription (how a not-yet-expired subscription instance is "deleted")

A subscription instance that has not expired cannot simply be released; the
customer unsubscribes (refund) it. Manual path: Billing console ->
Unsubscribe/Refund page (see `console-paths.md`). Rules stated by front-line
support [ticket:T-263837C7]:

1. Data is NOT retained after unsubscription -- back up first
   (snapshot-first rule).
2. The refund typically arrives within about 2 working days (as stated in
   that ticket; confirm on the rules page).
3. The invoiceable quota is reduced accordingly.
4. Gifted/voucher items attached to the order are voided and zeroed.
5. The amount shown on the refund page is final.
6. Rule references:
   [doc:https://help.aliyun.com/zh/user-center/user-guide/unsubscription-rules]
   and
   [doc:https://help.aliyun.com/zh/user-center/user-guide/refund-destinations].

After expiry, the instance can also be released manually (from 00:00 of the
day after `ExpiredTime`) without waiting for the automatic release
[ticket:T-263837C7].

## 3. Refunds, fee waivers, compensation -- HAND OFF, never promise

- Refund AMOUNT disputes, fee waivers, compensation and coupon requests are
  human/business decisions. The skill states the facts (billing matrix,
  order nature), then hands off with the 4-element handoff script (see
  `handoff-boundaries.md`).
- Observed waiver language requires an explicit customer "confirm" reply
  before a human applies it, and general-purpose coupons do not offset
  overdue bills
  [doc:https://help.aliyun.com/zh/user-center/user-guide/faq-about-coupons#5c82133892xps].
- Never estimate a refund amount; the refund page is authoritative
  [ticket:T-263837C7].

## 4. Expiry extension ("grace period") -- manual approval, never promised

Facts the skill CAN establish (read-only):

- authoritative expiry time (API + billing cross-check);
- auto-renewal state;
- whether the instance is already expired/stopped.

Facts this area does NOT verify in this run:

- unpaid renewal orders -- verifiable read-only with `bssopenapi QueryOrders`
  (RAM action `bss:DescribeOrderList`; `PaymentStatus=Unpaid` plus a
  `CreateTimeStart`/`CreateTimeEnd` window) and `GetOrderDetail` by order id,
  but this area does not call them yet; the customer can also self-check
  Billing console -> Orders. Say plainly that the precondition was NOT
  verified;
- whether an extension was already used this calendar year (no read-only
  query for extension records is documented or verified in this tier).

Rules to disclose verbatim:

- Limits: one account / one calendar year / one time / one day / one
  instance [ticket:T-63376A9B].
- Precondition: any unpaid renewal order must be voided first; voiding is
  IRREVERSIBLE -- the order cannot be paid afterwards and renewal must be
  re-ordered [ticket:T-88CA26A9] [ticket:T-63376A9B].
- Conflicting front-line statements exist: "expiry stop cannot be delayed"
  [ticket:T-B92D8D06] vs granted 1-day / 24-hour extensions
  [ticket:T-084C4147] [ticket:T-CD20304A] [ticket:T-240B40F6]. Present
  both; the outcome depends on manual case-by-case approval and is NEVER
  promised.
- An EIP does not extend together with the instance
  [ticket:T-C8B6DAEA, low confidence -- phone-only evidence].
- Extension consent prototype: support only submitted the request after the
  customer explicitly replied "agree" [ticket:T-240B40F6] -- mirror this
  confirmation discipline in any guided workflow.

### Extension application material package (template)

The script emits this package pre-filled with API-verified facts; the
customer (or agent) submits it through the human ticket channel:

```text
Instance ID           : <from API>
Region                : <from API>
Authoritative expiry  : <ExpiredTime, raw API value>
Auto-renewal status   : <from API>
Business reason       : <customer's words, e.g. payment approval cycle>
Requested extension   : 1 day (only granularity observed in evidence)
Customer confirmation : <explicit "agree" reply required before submission>
Unpaid-order check    : NOT verified by the skill -- customer self-check result: <...>
```

## 5. Free-trial conversions

- Trial = pay-as-you-go instance + granted savings-plan-style package
  offsetting the bill; it does not auto-renew at trial end
  [ticket:T-C3E9D9B3] [ticket:T-EDCE8535].
- Conversion docs (manual actions):
  [doc:https://help.aliyun.com/zh/ecs/user-guide/what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md],
  [doc:https://help.aliyun.com/zh/ecs/user-guide/common-operations-for-the-ecs-free-trial.md],
  [doc:https://help.aliyun.com/zh/ecs/user-guide/ecs-pay-as-you-go-starter-guide.md].
- Plan/pricing recommendations and sales-page questions are commercial
  topics -- hand off (see `handoff-boundaries.md`).
