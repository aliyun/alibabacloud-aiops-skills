# Billing Model Basics (ECS Subscription vs Pay-As-You-Go)

Unified wording for explaining the two ECS billing modes and the trial /
savings-plan mechanics behind most "free server" confusion. Every claim is
tagged with its provenance; numbers that live only in the customer's
Billing Center are deliberately NOT reproduced here.

## The two modes

| Aspect | Subscription (pre-paid) | Pay-as-you-go (post-paid) |
|---|---|---|
| Payment | One fixed term up front (month/year) | Hourly metering, charged after use |
| Unit price | Lower for steady 24x7 workloads | Higher per unit, but stops when you release |
| Lifecycle driver | Expiry date: renew, or expire -> manual release next day, or auto-delete ~15 days after expiry | Balance health: arrears -> stop -> release, data unrecoverable |
| Opening condition | Order payment succeeds | Combined balance + vouchers at least 100 CNY [verified-dialog T-3CA25349] |
| Switching | Can be converted to pay-as-you-go (refund rules apply) | Can be converted to subscription (arrears hide the entry) |

Billing fields as returned by the read-only API: `InstanceChargeType` =
`PrePaid` (subscription) or `PostPaid` (pay-as-you-go); subscription
instances also carry `ExpiredTime`.

Authoritative background docs (injected help-search hits, quote the URL,
do not paraphrase numeric rules from memory):

- ECS billing methods overview:
  https://help.aliyun.com/zh/ecs/overview-of-billing-methods.md
- Payment-type selection best practices:
  https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-ecs-billing-methods.md
- Purchase flow illustrated (billing type chosen at purchase):
  https://help.aliyun.com/zh/ecs/user-guide/a-picture-is-to-teach-you-how-to-buy-cloud-server-ecs.md
- What is ECS:
  https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md

## Free trial and savings plans (top confusion source in this tier)

- A "free trial" server is NOT a separate free product. It is a normal
  pay-as-you-go instance whose hourly charges are deducted by a trial
  savings-plan (resource-package-style) deduction. [ticket-summary
  T-C3E9D9B3, wording echoed in the dialogue: "a resource package that
  offsets the pay-as-you-go charges"]
- When the trial period ends or its free quota is exhausted, charges fall
  through to the account balance; SMS/console reminders are sent.
  [ticket-summary T-52391345 -- exact quota/amount figures come from the
  trial page itself, never from this skill]
- The remaining deduction amount and the plan expiry date are NOT visible
  through the ECS read-only surface: ask the customer to check the Billing
  Center (resource packages) and paste a screenshot.
- Official free-trial-expiry handling doc (injected help-search hit):
  https://help.aliyun.com/zh/ecs/user-guide/what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md

## What keeps its own billing regardless of the instance mode

Data disks not yet converted, snapshots, custom images, public traffic
without a fixed-bandwidth subscription, and independently purchased
products (e.g. security-center add-ons) each carry their own
pay-as-you-go items. See `residual-billing-checklist.md`.

## Known customer misconceptions to defuse explicitly

1. "Free trial = an independently free server product." -> No; see above.
2. "Converting the instance converts everything." -> No; disks/snapshots/
   bandwidth are separate items (residual checklist).
3. "After release, charging stops on the same day." -> Bill issuance lags;
   charges seen days later were accrued before the release [ticket-summary
   T-82BD6370].
4. "Pay-as-you-go also has a ~100-200 CNY yearly price." -> Confusing
   campaign packages with the billing mode itself; campaign eligibility
   and price are sales-manager matters, never promised here [ticket-summary
   T-E089159A].
5. "Unsubscribing early and waiting for expiry are the same." -> Different
   paths and different money outcomes; see `lifecycle-unsubscribe.md`.

## Verification status

- Provenance tags: [verified-dialog] = confirmed verbatim in a real ticket
  dialogue this round; [ticket-summary] = from a ticket summary whose full
  dialogue was not re-checked; treat as directional.
- Doc URLs above are injected help-search hits (authoritative this round);
  dialogue-quoted URLs in sibling references carry their own re-verify
  notes. Record the re-check date when consulting each page live.
