# Discount-Path Routing (self-service / business / appeal)

Machine template copy embedded in `scripts/areas/renewal_pricing_discount/_constants.py`
(`HANDOFF_CHANNELS`); build any package with
`python3 scripts/areas/renewal_pricing_discount/ecs_renewal_price.py handoff --channel <name>`.

A renewal/discount request must land in exactly ONE of three lanes. Decide
the lane first, then speak:

## 1. Self-service lane (the skill answers with facts + documented rules)

Eligible questions:

- "what is the renewal built of / how much at list price" -> inventory +
  pricing-modules + quote trial (list-price basis) or the purchase-page
  wizard;
- "when does it expire, is auto-renew on, which item actually lapsed" ->
  inventory / expiring;
- "why is this quote different" -> playbook branches B1-B11;
- "which billing-method direction is cheaper for my pattern" -> point to
  the official billing-method best-practices doc (comparison of approaches,
  no recommendation of specific SKUs, no purchase);
- cost-optimization products (savings plans / reserved instances /
  storage capacity units) may be mentioned ONLY as documented optimization
  directions pointing to the official best-practices document; this skill
  never buys or quotes them (purchase actions are out of its whitelist).

Time-sensitive activity facts (99 program cut-off date, fixed-IP inclusion,
flash-sale session times) may be relayed ONLY with the tag "sourced from
support practice, verify on the activity/order page - the page is
authoritative".

## 2. Business lane (approval authority is NOT with technical support)

Anything requiring a discretionary commercial decision leaves to the account
business manager. Boundary sentence to relay: "after-sales technical support
has no discount-approval or quoting authority; commercial terms are handled
by the business manager." Typical triggers: negotiated discount, fee waiver,
itemized cost statement for internal approval, partner/channel pricing,
"special price for our organization".

### Information package (fields fixed by the handoff mode)

1. Account UID (evidenced via sts_token, never guessed)
2. Instance id(s), region, spec, disks, bandwidth (inventory output)
3. Expiration time + auto-renew state (inventory output)
4. Request type in the customer's own words
5. Expected outcome (e.g. "quote for 1 year with discount")
6. Paths already attempted
7. Contact details: LEFT TO THE CUSTOMER - they supply them directly to the
   business channel; this skill never collects, stores or forwards phone
   numbers or emails (a real ticket showed a mistyped mailbox suffix
   breaking the whole follow-up: an argument for customer-supplied contact,
   not agent-copied contact).

Anti-pattern observed in tickets and forbidden here: "leave your phone and
wait for a call back, no facts" - always attach the full package, and set
the expectation that business response timing is not something this skill
can guarantee.

## 3. Appeal lane (activity eligibility doubts)
<!-- anchor: appeal -->

Only for B3-shaped cases (customer believes they qualify for an activity
price and got blocked):

- entry: the self-service-center diagnosis + appeal tool (ticket-sourced
  console tool page; give the entry description, let the console navigate);
- materials: clear, legible, matching the listed requirements - blurry
  material is the recorded rejection cause;
- review window: about 1 business day per the source ticket; result is
  delivered in the review ticket / SMS;
- hard limits: review reasons are NOT visible to support; do not predict
  outcomes; do not advise re-submitting identical material after a
  rejection; final activity eligibility is decided by the ordering system
  at checkout.

## 4. Console self-check lane (order facts)
<!-- anchor: console -->

This skill has no order-query API. For "which order was this / where is my
purchase / a renewal order was voided" the customer checks: the order
management list page (billing console), the renewal list with
not-yet-effective-renewal refund entry, and the bill detail by instance
(expense center). The skill may anchor the account UID to rule out
wrong-account confusion, then refers to these pages.

## Never-do list (all lanes)

- never promise a discount, waiver amount, review result, price validity or
  stock;
- never place, cancel, pay, void or refund any order;
- never quote another customer's price or any internal pricing logic;
- never collect contact details;
- never state an amount without the list-price disclaimer.
