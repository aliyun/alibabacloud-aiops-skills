# Price-Mismatch Attribution Playbook (Decision Tree B1-B11)

Machine-readable copy of this tree is embedded in `scripts/areas/renewal_pricing_discount/_constants.py`
(`MISMATCH_BRANCHES`) and routed by
`python3 scripts/areas/renewal_pricing_discount/ecs_renewal_price.py explain --symptom "<customer wording>"`.
This file is the full human-readable version; every attribution below is
distilled from real support-ticket dialogues in the renewal-pricing tier.

Ground rules for every branch:

- Ticket ids in the **Sources** lines are internal evidence metadata for the
  agent only; NEVER surface them (or any wording that reveals other
  customers' tickets) in a customer-facing answer.

- The skill NARRATES rules and shows list-price compositions. It never states
  a payable amount, never approves a discount, never operates an order, and
  never hand-computes a refund ("the console/system computes the figure" is
  the documented practice; internal billing engines are not exposed to
  support either).
- Amount outputs MUST carry the list-price disclaimer verbatim.
- Manual console steps are guidance only: name the page, the expected effect
  and the risks, then stop.

## Entry triage (ask which question the customer is really asking)

| Question | Route |
|---|---|
| "How much is it / how is the price built?" | inventory -> pricing-modules -> quote (composition + disclaimer); if the ask contains "give me a discount" jump to the business routing in discount-routing.md |
| "Why is it different from before / from the page?" | branches B1-B11 below |
| "Is there any promotion / discount for me?" | discount-routing.md three-way split |
| "Expiring / stopped / auto-renew?" | inventory + expiring, then B9 (which item actually expired) and console renewal guidance |

## B1 — Discount tier follows the remaining subscription duration

**Identify:** a renewal/upgrade quote that changed by itself between two
dates days apart; instance remaining duration near a whole-year boundary.
**Attribution:** duration-bound tiers are matched automatically against the
REMAINING validity at order time. Documented example from a ticket: an
instance expiring 2028-07-31 quoted at the 2-year tier (about 5.5x10%-off
level) on 7/30 and at the 1-year tier (about 6.5) on 8/3 once the remainder
dropped below two years, so the upgrade top-up rose from ~2200 to ~2600.
The console is already showing the best available price for the CURRENT
remainder; the tier cannot be manually pinned higher. Renewing to extend the
validity makes the system re-match the tier on the new remainder, and a
single-month renewal order usually carries NO discount at all.
**Do:** read real ExpiredTime (inventory); optionally demo the step with
`quote --compare-periods 12,24,36`; state the mechanism, not a promise; if
the customer wants a better commercial price, go to the business channel
with a handoff package.
**Sources:** ticket dialogue `T-F59CD9A0`. Tier percentages and threshold
behavior are ticket-sourced operational facts: they may change - the order
page is authoritative.

## B2 — Discount entitlement not refreshed / previous low-price order voided

**Identify:** page shows a promotional renewal price (e.g. 199) but the
payment step shows the original price (e.g. 2507.7); sometimes an earlier
low-price renewal order exists and was voided.
**Attribution:** the discount entitlement can lag after a voided order until
the system refreshes it. Support practice: wait, then regenerate the order.
The observed refresh window is roughly 2-3 hours - EMPIRICAL, not an SLA.
**Do (manual sequence, customer performs every step in the console):**
1. void the high-priced UNPAID renewal order on the order page;
2. wait for the entitlement refresh;
3. regenerate the renewal order and verify the price on the payment page
   before paying. If the original price persists, check eligibility (B3).
**Never:** place/void/pay orders on the customer's behalf; promise the 199.
**Sources:** ticket dialogue `T-D510E2FE` (resolved by exactly this
sequence).

## B3 — Activity eligibility doubt; the appeal path

**Identify:** renewal price far above the activity price the customer
believes applies; the customer reports failing an activity check or a
rejected appeal.
**Attribution:** participation rules (including same-person /
same-account purchase history) gate activity prices. A self-service-center
diagnosis + appeal tool submits materials to a review team (~1 business day);
results arrive via the review ticket / SMS. Review reasons are not visible
to support, so nobody can explain or overturn them here. Re-submitting the
same blurry material usually does not change the outcome - clearer evidence
is what moved the second review in the source ticket.
**Do:** give the appeal entry and material checklist (discount-routing.md),
state no prediction. **Never:** claim eligibility will pass.
**Sources:** tickets `T-768DBA2E`, `T-EE2FAEBE` (same-person rule).

## B4 — Flash-sale stock sold out; the page auto-switches the offer

**Identify:** an entry-page sale price (e.g. 38) vs a different checkout
price (e.g. 68) for the same entry.
**Attribution:** per-session flash-sale stock is limited; once sold out, the
page automatically displays the next best offer available to the account
(e.g. a new-user price at 68), which explains the mismatch legitimately.
Session times announced in the source ticket: daily 10:00 and 15:00 -
time-sensitive, verify on the activity page. NOTE: the source sample was a
Simple Application Server product, not ECS; the mechanism narrative is
shared, the specific session schedule belongs to that product's page.
**Do:** explain the mechanism, point to the next session, promise nothing.
**Sources:** ticket dialogue `T-653BAC07`.

## B5 — Activity commodities are independent (no difference-payment swap)

**Identify:** "I bought the plain activity instance; can I top up the
difference to get the instance+database bundle?" or "if I cancel and re-order
do I lose the activity price?"
**Attribution:** bundles under one activity are separate commodities; there
is NO difference-payment upgrade path between them. In the source ticket,
cancelling the original order and re-ordering STILL qualified for the
activity price (subject to activity terms at ordering time). Products such
as RDS inside a combo are that product's channel once purchased.
**Do:** state the independence rule, re-order caveat, and data-backup
reminder before any refund-rebuy cycle; UID-anchor when the customer
"cannot find" the order (it may belong to another account - ticket
`T-81F952D0` shows agents answering this from the order page).
**Sources:** ticket dialogue `T-81F952D0`.

## B6 — A billing-method conversion triggered a new payment

**Identify:** "I only did an upgrade - why does it ask me to pay 700?"
**Attribution:** what looked like a temporary upgrade may have been a
subscription-to-pay-as-you-go conversion (which re-rates and re-collects),
or bandwidth switched to pay-by-traffic (publicly documented reference rate
0.8 CNY/GB outbound; inbound not billed) producing surprise balances.
**Do:** read `InstanceChargeType` + `InternetChargeType` via inventory to
show what the account actually is now; explain which change requires
payment; cite the public-bandwidth billing doc. WHO consumed the traffic is
out of scope - boundary-handoff.md.
**Sources:** ticket dialogue `T-66556C0B`.

## B7 — Downgrade / unsubscription refund computes to 0 (or near 0)

**Identify:** "refund shows 0 yuan"; "why not pro-rata by remaining days?"
**Attribution (the documented formulas):**
- Downgrade refund = remaining cost of the OLD spec - purchase cost of the
  NEW spec, with the already-consumed period re-priced at ORIGINAL prices
  with discount rules; if usage was under 30 days a 1.5 factor MAY apply to
  the consumed amount. With a deep purchase discount the result can be 0.
- Non-full unsubscription converts the used period at ORIGINAL price too -
  a 99 purchase used briefly can refund 0.
- Fixed-bandwidth-to-traffic conversion auto-refunds the bandwidth balance;
  when discounts applied the bandwidth refund can be 0, and switching back
  later can cost extra.
- Special-case manual refunds exist but only via human review ("one-time"
  in the source ticket), and the issued link had a short validity (about 3
  days) with the amount DECREASING over time.
**Do:** output the mandatory risk notices (refund-downgrade-risks.md) FIRST,
then the formula narrative, then point to the console's own expected-refund
display (e.g. stop on the downgrade page before confirming) and the refund
rules doc. **Never:** compute a figure, submit an unsubscription, or retry
a failed submission for the customer (the page-string "unsubscription
request submission failed, contact customer service" marks a HUMAN
special-application case).
**Sources:** tickets `T-CECFF6D5`, `T-EE2FAEBE`, `T-402BBB88`.

## B8 — Upgrade top-up exceeds the price of buying the same spec new

**Identify:** "the 4c8g->8c16g top-up is 5000+ while a brand-new 8c16g costs
3000+ - I want the difference explained."
**Attribution CANDIDATES (no auto-conclusion - evidence is a phone-summary
ticket, not a verified dialogue):** original order's discount attribution,
different pricing time points/promotions between upgrade and new-purchase
pages, or a configuration mismatch in what was compared.
**Do:** trial both compositions with quote (list-price basis) or read both
console pages item by item; list the candidates; if a refund-rebuy path is
weighed, force the data-migration / asset-loss notice (B7 notices). Final
figure stays with the checkout page.
**Sources:** ticket summary `T-86E81B7E` (weak verification; present as
candidates only).

## B9 — Independent billing items confused with each other

**Identify:** "I already paid, why is it stopped / why another charge?"
**Attribution:** domains and ECS renew separately (a 78 domain payment never
renewed the instance in the source ticket); EIP bills its own
configuration + traffic fees (free configuration fee while bound to an ECS
instance under the quota note in the source ticket - verify current rules);
Cloud Security Center trial items can keep accruing pay-as-you-go after
expiry; ECS snapshot storage is a separate product line.
**Do:** inventory + expiring to name WHICH item is expiring/overdue; order
page for payment matching. Snapshot mechanics and domain work: handoff.
**Sources:** tickets `T-49D1B64B` (phone-only, summary-sourced),
`T-4AE4D797`, `T-768DBA2E`, `T-A9447F52`.

## B10 — A pro-rata remainder figure misread as a full-cycle fee

**Identify:** "the page says 207 - is that a whole month or what?" or an
amount much smaller than the expected yearly figure.
**Attribution:** amounts beside an upgrade/expansion commonly cover ONLY the
remaining validity (pro-rata difference to the subscription end); the final
renewal total is then shaped again by discounts and vouchers. The phone
explanation in the source ticket confirmed "207 = remaining-period
difference" (weak verification).
**Do:** explain the pro-rata semantics; send the customer to the expansion/
purchase page real-time quote; never assert beyond the page label.
**Sources:** ticket `T-B3C9E763` (key conclusion inside a phone call).

## B11 — Changing configuration can forfeit long-term low-price renewals

**Identify:** "I run a 99-plan instance; can I safely upgrade bandwidth/
disks?" followed later by "why is my renewal no longer discounted".
**Attribution:** in the source ticket the agent explicitly warned that
participating in a long-term low-price activity (e.g. 99 CNY/year) plus a
configuration change can make FUTURE renewals lose the activity price.
**Do:** pre-change risk notice FIRST; tell the customer to read the current
activity terms and the checkout page effect before confirming any change.
**Never:** execute or approve the change.
**Sources:** ticket `T-CECFF6D5` notice list.

## Customer-visible page strings -> branch quick map

| Quoted page string / symptom | Branch |
|---|---|
| "discount on renewal page, original price at payment" | B2, then B3 |
| "unsubscription request submission failed, contact customer service" | B7 (human special application) |
| "refund amount shows 0" | B7 |
| "why am I asked to pay after my upgrade click" | B6, B10 |
| "page price 38 but checkout 68" | B4 |
| "already paid yet stopped" | B9 |
| "quote higher than a few days ago" | B1 |
| "top-up higher than a brand-new instance" | B8 |
| "re-ordering the activity deal" | B5 |
| "will my 99 price survive the change" | B11 |

## Official documentation pointers (verified by help-search during Phase A)

- Renewal with configuration change: https://help.aliyun.com/zh/ecs/user-guide/renewal-change.md
- Downgrade during renewal: https://help.aliyun.com/zh/ecs/user-guide/downgrade-instance-configurations-during-renewal.md
- Free-trial expiry handling: https://help.aliyun.com/zh/ecs/user-guide/what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md
- Pay-as-you-go starter guide: https://help.aliyun.com/zh/ecs/user-guide/ecs-pay-as-you-go-starter-guide.md
- Billing-method best practices: https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-ecs-billing-methods.md
- Configuration-change overview: https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md
- Retired instance types (why old specs re-rate differently): https://help.aliyun.com/zh/ecs/user-guide/retired-instance-types.md
- Public bandwidth billing (fixed vs traffic): https://help.aliyun.com/zh/ecs/public-bandwidth (ticket-sourced link; re-verify before citing)
- Downgrade refund rules: https://help.aliyun.com/zh/user-center/description-of-downgrade-refund-rules (ticket-sourced link; re-verify before citing)
