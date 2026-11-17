# M3 -- Special Products and Order Types (CL-E triage)

Customers assume every purchased object is refundable the same way. It is
not -- refundability is per product type. Triage FIRST from the resource-id
prefix (shown by `--inventory` / `--checklist --instance-id`), then apply
the matching track below.

## 1. Triage table

| Prefix | Object | Unsubscribable? | This skill's job |
|---|---|---|---|
| `i-...` | ECS instance | subscription: yes (refund center, rules in M1); pay-as-you-go: no refund, release instead | full inventory + estimate + notice |
| `spn-...` | Savings plan | NOT self-service refundable; exceptions only via manual commercial approval | explain rules, evidence-check the covered instance, hand off the approval to a human ticket |
| `rm-...` | RDS instance (or other product id) | belongs to another product line | cross-product handoff; explain only the ECS-side linkage |

## 2. Savings plans (verified support position)

- A savings plan is a commitment that DEDUCTS the pay-as-you-go bills of
  the instances it covers; it is not itself an instance.
- It cannot be unsubscribed through the refund center. The ticket-verified
  wording: "this currently is not supported [for unsubscription] ... it
  deducts pay-as-you-go fees, but the instance is released, so it will not
  keep charging" -- i.e. once the covered instance is released there is
  nothing left to deduct and no ongoing charge attributable to it.
- Evidence step (what the skill automates): confirm with
  `--inventory`/`--estimate` that the covered instance really is gone and
  stops appearing in fresh bill cycles; then relay the rule. Do NOT state
  this from the customer's claim alone.
- Exception route: a special-approval unsubscription exists ("after special
  application we can unsubscribe it, the used part of the fee is not
  returned") -- it is a human approval, never promised by this skill; before
  such a request the customer must answer the six-item checklist (M4)
  including: voucher residual-only refund, covered instances revert to
  normal pay-as-you-go billing after the covering resource is released, and
  the refund amount as shown on the page.
- Flexible-edition plans: after refund the flexible edition cannot be
  re-purchased -- warn before proceeding.
- RDS-side plans: their FAQ
  (`https://help.aliyun.com/zh/rds/product-overview/faq-about-savings-plans`)
  and their approvals live on the RDS product line -- hand off, with the
  ECS-side evidence attached.

## 3. Campaign / activity packages

- Discounted SKUs are independent: two separately promoted products cannot
  be merged by paying the difference; a bundle swap = cancel + reorder.
- Re-eligibility for a campaign price after cancel-and-reorder has NO query
  API. In one analyzed ticket an agent said "yes" verbally for the 99-CNY
  offer -- a single-ticket answer is not a rule: output
  `STATUS: DEGRADED: campaign re-eligibility not queryable`, point to the
  campaign page terms / human support, and never promise the price.
- A "no matching order found" result is MOST often the wrong account -- run
  the identity echo and have the customer re-check the order list page in
  every account they own before any other conclusion.

## 4. Downgrade / spec-change orders

- A downgrade order that has taken effect is irreversible: no cancel, no
  undo. Restoring the previous spec = upgrade again + pay the difference.
- The downgrade's partial refund is auto-computed from remaining duration
  and config price difference; the credited amount is the authority (dual
  caliber still applies when any figure is relayed).
- Questions about WHETHER a target spec can be purchased / how to resize
  are the instance-modify tier, not this one.

## 5. Purchase bundles without the expected capability

Mis-sku purchases (e.g. a compute-card GPU family bought for graphics
rendering) usually end in the five-day / non-full refund track, not a
config fix. This skill may relay the factual spec-family distinction and
then route to the refund tracks above; recommending or purchasing
replacement specs is out of scope.
