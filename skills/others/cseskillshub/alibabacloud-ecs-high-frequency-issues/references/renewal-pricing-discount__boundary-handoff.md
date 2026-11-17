# Boundary Map: out-of-scope symptoms -> handoff destination

This skill owns exactly one area: where an ECS renewal / configuration-change
price comes from, why it differs, which discount path applies, who can settle
it. Everything else gets ONE identification sentence + the destination below
(`handoff --channel other-skill` prints this map's package fields). Do not
diagnose other areas inside this skill.

| Customer symptom (their wording) | Why it is out of scope | Destination |
|---|---|---|
| "expanding the disk - the extra space is not visible" / partition or filesystem steps | expansion OPERATION area, not pricing | `area:disk-expand-diagnosis` (the price question about the expansion stays here, branch B10/B7) |
| "instance will not start after expiry" / stopped mid-way / recovery after payment | instance-state area; this skill only explains which item expired (B9) and where the renewal page is | `area:instance-state-diagnosis` |
| "the downgrade order was paid but bandwidth/IP still old" | execution/state sync area after the order | change-spec related skill + console order state check; the FEE side of it (refund possible 0) stays here (B7) |
| "my traffic cost exploded overnight, who used it" | traffic-forensics area; only the billing-rule reading (0.8 CNY/GB outbound, inbound free) is answered here (B6) | cost-anomaly / traffic troubleshooting channel |
| snapshot storage mechanics, redundancy, cross-region copy rules | snapshot area | snapshot / backup skill (the "snapshots are a separate billing item" fact stays here, B9) |
| "send me an invoice / corporate transfer / contract" | finance area | finance channel (identification + referral only) |
| "my resource package / savings plan did not deduct" | deduction area of other products | cost-optimization channel (this skill's whitelist has none of its APIs) |
| "just call me / give me the business manager's number" | service-process area; contact data is never collected | business lane package in discount-routing.md, customer supplies own contact |
| "forced migration / data-center retirement compensation" | account-migration area | human support ticket channel |
| "how much is the cheapest server for my 5 group-chat apps?" (no existing instance, sizing question) | pre-sales selection | pre-sales / business manager entry - give the correct door, never an "under review" stall with no output |
| "cloud web hosting / simple app server / RDS / domain pricing" | non-ECS products | that product's channel; domain vs ECS independence fact here (B9) |

## Identification sentences (relay, then stop or continue per table)

- Expansion: "The operation and the after-expand visibility issue belong to
  the disk-expansion diagnosis skill; the fee shown beside an expansion is a
  remaining-period difference - I can explain that part."
- Instance state: "Which item expired is a billing fact I can read; the boot
  and recovery of the instance belongs to the instance-state diagnosis
  skill."
- Traffic spike: "I can explain why outbound traffic bills per GB; tracing
  WHO consumed it belongs to the cost-anomaly troubleshooting channel."
- Commercial: "Discount approval and negotiated quotes are outside
  technical support authority; I will prepare the exact information package
  for the business manager."
- Pre-sales: "A configuration quote for a new purchase belongs to pre-sales;
  here is the correct entry. I do not run sales sizing here."

## Half-in / half-out rules

A ticket may straddle areas (e.g. an expansion with a fee complaint). The
pricing portion of it (B1, B7, B10 narratives, list-price composition) is
answered FIRST, then the remainder is referred - one sentence each, never a
diagnosis of the foreign area.
