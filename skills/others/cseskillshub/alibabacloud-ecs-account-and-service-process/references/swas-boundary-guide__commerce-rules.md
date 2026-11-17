# Commerce & Lifecycle Rules: Wording, Boundaries and Handoff

Support for the commerce/lifecycle answers of
`scripts/axes/swas_boundary_guide/swas_boundary_guide.py` (`--rules --topic commerce`,
`--rules --topic lifecycle`, `--refer`). Everything here is explanation and
escalation wording only: **this skill never executes a commercial action**
(no refund, no eligibility restore, no price negotiation, no release, no
unsubscribe, no purchase), and never promises an outcome. Rule sources:
[references/swas-boundary-guide__boundary-rules.md](boundary-rules.md) topics `commerce` and
`lifecycle` (real support tickets).

## 1. Promotional eligibility rules (quote, do not interpret)

### New-customer SWAS offers (e.g. the 68 CNY/year tier)

- Limited to Alibaba Cloud NEW users: accounts that have **never generated
  an order record** (or whose cumulative order amount is 0).
- Once an order exists, the account no longer qualifies -- **a refund does
  NOT restore eligibility**; the repurchase page then shows the regular
  price (a real ticket saw the price jump from 68 CNY to 400+ CNY after
  refund-and-rebuy).
- Proactive duty: warn the customer BEFORE they refund that refunding
  forfeits the promotional price. After the fact, explain the rule and
  offer the commercial handoff (section 4) -- never simulate a different
  outcome.

### 99 CNY/year ECS activity

- Economy-type e instance: 2 vCPU / 2 GiB memory / 3 Mbps bandwidth /
  40 GiB ESSD Entry system disk; real-name verification required; limited
  to ONE instance per person.
- Renewal at the activity price is not guaranteed after an image-based
  replacement; the 40 GiB system disk commonly blocks image migration from
  a 50 GiB SWAS source (see
  [references/swas-boundary-guide__migration-paths.md](migration-paths.md)).
- Authoritative current terms: <https://www.aliyun.com/daily-act/ecs/99program>

### 5-day unconditional refund

- Ticket wording: limited to **once per year per product per account** --
  using it on Simple Application Server excludes using it on ECS within the
  same year. **[summary evidence]** No verified policy URL exists in this
  skill's evidence set: quote it as ticket wording and point the customer
  to the official refund policy / Billing Management console for the
  authoritative conditions.

## 2. Lifecycle self-service (expiry / renewal / release)

- **Expiry & renewal data are billing-side.** This skill has no verified
  billing API and does not query one. Guide self-service instead:
  - Billing Management console -> Orders / Renewal: expiry dates, renewal
    prices, order history;
  - SWAS console -> Servers: per-server expiry time;
  - ECS console -> Instances: per-instance expiry time.
- **Free-trial instances** expiring soon can simply be left unrenewed;
  proactive release is unnecessary (ticket-verified advice).
- **Release/unsubscribe requests are never executed by this skill.**
  Provide self-service steps only:
  - subscription resources: Billing Management -> Unsubscribe management,
    or let the instance expire;
  - pay-as-you-go resources: release from the product console;
  - warn that releasing erases all data irreversibly -- back up first.
- Customers who cannot operate the console (e.g. mobile-only users asking
  support to release resources for them): give the step list above plus the
  support-ticket channel; the decision and the click stay with the customer
  or human support.

## 3. What online support itself could not resolve (parity statement)

Real tickets show human agents also could not restore promo eligibility,
refund, or negotiate prices online -- they escalated to a sales manager or
an offline ticket. This skill matches that behavior exactly: explain the
rule, then hand off. Claiming any better outcome would be fabrication.

## 4. Handoff wording (use verbatim, adapt names)

- Sales/commercial channel: "If you do need ECS/SWAS at a specific budget,
  I can note your contact number so a sales manager follows up on pricing
  options. Eligibility restoration and refunds are decided by the
  commercial process -- I can explain the published rule, but I cannot
  change the outcome here."
- Support ticket: "Please submit a ticket from the console Support entry and
  attach: account UID, instance id, region, the order/activity name, the
  price you saw (screenshot), and the timestamps. This evidence list speeds
  up the offline review."
- Never say: "I have restored your eligibility", "the refund is approved",
  "I released the instance for you" -- none of these can be done by this
  read-only skill, and asserting them is fabrication.

## 5. Billing-adjacent technical symptoms (boundary reminder)

When a commerce question arrives mixed with a technical symptom (ticket
pattern: "68 CNY server has high memory usage AND I want a refund"):

1. Split the two asks explicitly.
2. Technical part: attribute the product (`--identify`), classify the
   symptom (`--refer`); in-guest usage problems (memory/disk/inode) go to
   the resource-usage diagnosis channel, not to this skill.
3. Commercial part: apply sections 1-4 above.
4. Report both tracks separately so nothing is silently dropped.
