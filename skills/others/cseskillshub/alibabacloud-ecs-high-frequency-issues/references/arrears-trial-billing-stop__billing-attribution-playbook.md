# M5 — Billing Attribution Playbook (region x product x item; notification subjects)

Purpose: answer the one question behind all three areas — **"who exactly is
taking my money?"** — from machine evidence where possible, from disciplined
console self-checks where not, and never from vibes.

## 1. The attribution ladder

1. **Account level** — `QueryAccountBalance`: is there arrears and how big.
2. **Cycle level** — `QueryBillOverview` with `--billing-cycle YYYY-MM`: per-product
   pretax and outstanding totals plus the billing-item names of each product's
   rows. Measured behavior on the verified contract: the overview rows carry
   NO region field — region attribution is done from the instance sweep and
   from the customer's console bill-statement drill-down, never by guessing a
   region out of a product row. Current month by default (declared), earlier
   cycles with the look-back flag: arrears can be booked in one cycle and
   surface later, and cleanup verification needs the NEXT cycle too.
3. **Resource level** — the instance sweep maps instance spend back to
   concrete `InstanceId` rows; everything the bill shows that the sweep does
   NOT explain is attached-resource residue (snapshot products, EIP, images,
   other-region leftovers).
4. **Item level** — beyond the product row (e.g. which disk, which snapshot
   id): NOT covered by the authorized action set (bill-overview is the
   coarsest-verified billing read here). Console path: the bill-statement
   detail page lets the customer drill to per-instance billing items;
   cross-check the named regions by switching the console region selector.
   Label all such drill-downs CONSOLE-CHECK in the answer.

## 2. Why the default view always misleads

`DescribeInstances` requires an explicit RegionId, and customers — like the
instances in this tier's tickets — keep billable residue in regions they
forgot they touched. Therefore:

- Sweep the built-in region list by default (script constant; state that it
  is a fixed list, not an enumeration guarantee).
- Whenever bill rows name a region, force the sweep through that region.
- "No instances found" answers only "…in the swept regions".

## 3. "Instance gone, money still flowing" decision table

| Bill says | Instance sweep says | Conclusion | Next action for the customer |
|---|---|---|---|
| ECS-family product still billed | instance absent | system-disk/image/traffic settlement tail for the final hours before release, or a still-live instance in a non-swept region | rerun with the missing region; check the statement's usage period vs release date |
| Snapshot product billed, any cycle | anything | snapshots exist somewhere (very often NOT in the default region) | console snapshot list per region; delete residue AND its auto policy (M4 steps 6–7) |
| EIP / network product billed | instance absent | unattached EIP retained | VPC console per region; decide keep vs release |
| Disk product billed | instance absent | standalone detached disk | Block Storage console; detach is not release |
| Other product (not ECS at all) | n/a | wrong product entirely — this skill only proves the ECS side is clean | route to that product's billing channel (handoff-map) |

## 4. Notification / SMS subject attribution

Customers paste (or paraphrase) expiring-soon SMS text. The message subject
is frequently NOT what the customer fears:

1. Read the product name in the message itself; treat the customer's
   interpretation as a hypothesis.
2. Machine-verify the ECS side: any instance nearing `ExpiredTime`?
   (`DescribeInstances`) Is the account in arrears?
   (`QueryAccountBalance`) Is there any ECS instance at all?
3. Outcomes:
   - **ECS subject matches data** → Area A or B flow.
   - **ECS side provably clean** (no such instance / not near expiry / no
     arrears) while the message names "security" / "protection" wording → the
     subject is a different product's trial entitlement (Security Center
     pay-as-you-go resource packages produce such notices); hand off with the
     proven ECS-side exclusion, and note that closing such a package does not
     affect the ECS instance itself. Entry:
     `https://yundun.console.aliyun.com/?p=sas` (Security Center console;
     tracking parameters stripped from the ticket-cited URL).
   - **Subject machine already released** → system-generated delayed trial
     notifications continue for a while; with the release confirmed by the
     sweep + bill rows, no new charges can originate from it. Explain, don't
     re-panic the customer.
4. Notification send-logs are not queryable from the authorized read set:
   never claim to have "found the SMS".

## 5. ID-type triage (saves whole ticket rounds)

| Shape | It is | Do |
|---|---|---|
| `i-xxxxxxxx...` | ECS instance ID | instance queries/filters |
| all digits, ~16 long | account UID | compare against the Step 0 identity, not against instances |
| order-shaped strings from a domain console | domain order number | not an ECS order; check the orders list page |
| anything else quoted as "the server number" | likely wrong artifact | ask for the console URL of the instance page instead |

The orders list (`https://billing-cost.console.aliyun.com/order/list`) plus
ECS console home (`https://ecs.console.aliyun.com/home`) resolve most
confusions; real tickets show hours lost to an all-digit account UID offered
"as the server order".

## 6. Statement-latency phrasing (use verbatim-ish)

> "After a release, billing stops accumulating at the release moment, but the
> statement itself is issued with delay — one more small bill can arrive for
> the pre-release usage window. That is settlement, not continued charging.
> Verify by comparing the bill's usage period with your release time, and by
> re-checking the next billing cycle."

Exact last-settlement timestamps are back-office data the authorized APIs do
not expose: quote the bill statement page, never an invented time.

## 7. Free quota / price wording discipline

This tier's tickets mention small periodic fees (public-IP retention fees,
per-GB snapshot storage math, free traffic allowances). None of those figures
was re-verified against authoritative documents during skill preparation —
the playbook therefore carries only the STRUCTURE ("retention while
unreleased", "volume-proportional snapshot storage"), and points at the
official billing documents in M1/M4 for numbers. Quoting a price or allowance
requires a live document citation in the same answer.
