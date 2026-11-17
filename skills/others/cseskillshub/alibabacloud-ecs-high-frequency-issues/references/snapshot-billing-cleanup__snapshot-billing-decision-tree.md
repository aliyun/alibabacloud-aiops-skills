# Snapshot billing decision tree (S0-S5)

This file is the knowledge behind the branches that
`scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` walks. The agent maps the customer
sentence onto parameters, runs the script, and relays what it rendered; the
branch judgements below explain *why* a branch fires and what may be claimed
from it. Never state a conclusion the script did not evidence.

## S0 - identity and scope (always first)

* `sts:GetCallerIdentity` settles which account the run looks at. This is the
  cheapest way to end a "the bill says snapshots but I see none" investigation
  that is really about the wrong account, the wrong region, or a service
  recovery notice that does not mean "a snapshot exists".
* Region is an input, never a guess. Snapshots are regional objects and are
  billed per region, so a single-region answer can only ever be a
  single-region claim. When the customer asks for "all regions", first point
  at the ECS overview page, which lists every region holding snapshot
  capacity, then re-run with each region named.
* Every parameter the run auto-filled is declared in the report's
  `Collected parameters` block. An empty enumeration is a finding
  (`no_snapshots_anywhere`), not a failure, and is rendered as a proof section
  rather than as "you pay nothing".

Evidence entry points for the money side (manual pages, this skill calls no
billing API):

| What to confirm | Console page |
| --- | --- |
| Charge per instance and per billing item | `billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance` |
| Resource package deduction detail, filtered by the billed period | `billing-cost.console.aliyun.com/ri/detail?commodityCode=all` |
| Resource package usage summary | `billing-cost.console.aliyun.com/ri/summary` |
| Savings plan coverage | `billing-cost.console.aliyun.com/resource/spn/overview` |
| Snapshots of one region | `ecs.console.aliyun.com/snapshot/region/<region>` |

## S1 - billing attribution

Fires on: "charged every month", "how is the fee calculated", "the bill says
snapshot chain capacity", "the package does not cover it".

1. Read the billing item label on the invoice. The snapshot line carries the
   label `SnapshotLink Capacity (Size)` (customers also read it as "snapshot
   chain capacity"). If the line is something else - the disk itself, disk
   performance, public bandwidth / egress traffic, an Elastic IP, another
   product entirely - the claim is out of scope for this skill: name the
   observed item and hand off per [handoffs.md](snapshot-billing-cleanup__handoffs.md).
2. Map the label onto evidence: region, source disk, snapshot entries,
   creation window. The chain grouping in the report is built from the
   `SourceDiskId` of each returned entry.
3. State the billing model facts (see the table below): capacity and duration,
   per region, existence-driven.
4. Only then discuss deduction, and only with the facts in
   [resource-package-deduction.md](snapshot-billing-cleanup__resource-package-deduction.md).

Claim limits in this branch: existence, region, owner, entry count, recorded
source-disk size. Amounts, periods and settled totals stay on the billing
pages above; the report never invents them.

## S2 - capacity lens reconciliation

Fires on: "my disk only holds X GB, why does the snapshot take many times
more", "the size does not add up", "how much do I actually use".

The three lenses, always named on any line that uses one:

| Lens | What it is | Where it comes from | Typical confusion |
| --- | --- | --- | --- |
| billed | Snapshot chain capacity per region and per disk chain - the invoiced figure | the billing item label plus the console chain view | read as "the size of my files" |
| cloud | Provisioned disk size, i.e. the capacity of the disk **at snapshot creation time** | `DescribeDisks`, `SourceDiskSize` on each entry | read as "how much I used" |
| guest | File-system visible usage | one confirmed guest reading, see [guest-diagnostics.md](snapshot-billing-cleanup__guest-diagnostics.md) | read as "what the snapshot should cost" |

The lenses are not equal, and the reasons are documented facts, not
speculation:

* Snapshots record data blocks. Freeing a file inside the guest marks blocks
  as available; it does not erase the blocks an existing snapshot already
  captured, so removing data after a snapshot does not shrink that snapshot.
* Incremental chains share blocks. The chain total is therefore not the sum of
  the individual entries, and each entry's displayed size reflects what is
  needed to restore from that entry.
* Metadata, file-system structures and formatting overhead occupy blocks that
  `df` never shows as "used by files".

Present the three columns and the gap; explain the gap only with the four
points above. Do not extrapolate to what a physical layer "could" compress,
and do not promise that a smaller disk can be built from the actual usage:
migrating to a smaller volume is a disk expansion/reshaping matter and is
handed off per [handoffs.md](snapshot-billing-cleanup__handoffs.md).

## S3 - deletability, blockers and regrowth

Fires on: "can't delete", "the delete button is greyed out", "deleted but the
charge came back". Detailed in
[snapshot-dependency-and-deletion.md](snapshot-billing-cleanup__snapshot-dependency-and-deletion.md).
The snapshot-first rule and its two meanings are defined there; both gated
modes of the script implement it.

## S4 - counts and quota facts

Fires on: "one disk has 1200 snapshots", "is every one of them billed", "is
there a limit", "can I cap the cost".

* Fees follow capacity, not entry count - but every existing entry carries
  capacity, so all of them contribute. Deleting the newest entries is not
  automatically cheaper than deleting the oldest.
* There is no per-account snapshot capacity ceiling and no automatic stop at a
  threshold; a spending alert is the only guard. Say so plainly rather than
  implying a cap exists.
* Counts and per-chain counts come from the enumeration. The per-disk entry
  quota and any quota raise are not decided here: report the observed counts
  and route the raise request to the quota console path.
* Batch removal is a human console action, page by page. The skill outputs
  lists; it never removes and never scripts the removal on the customer's
  behalf.

## S5 - concept and ownership boundaries

Fires on: "is a snapshot a backup", "how is this different from an image /
file backup / OSS copy", "do I need to buy both". Detailed in
[concept-boundaries.md](snapshot-billing-cleanup__concept-boundaries.md). Enumerate what the account
already has - snapshot entries, auto-type entries, custom images - and label
which product each fee belongs to. Whether to combine products is the
customer's decision: give facts and applicable scenarios, never a purchase
recommendation.

## Billing vocabulary the report uses

| Term | Meaning as used here |
| --- | --- |
| Snapshot chain | The snapshots of one disk in one region; the billed unit behind the label above |
| Entry | One snapshot record returned by `DescribeSnapshots` |
| `auto` type | An entry created by a policy-driven flow rather than manually; the regrowth signal in S3 |
| Retention | Days an auto entry survives; absent or not returned means treat it as permanent until the policy page proves otherwise |
| Usage | Per-entry field naming the kind of dependency on that snapshot; drives the blocker table |
| Settlement lag | Charges appear after the usage window closes, so a fresh deletion can still be followed by one last invoice line |

## Unit price citation policy

* This skill does not compute, estimate, forecast or quote a price - not in
  the report, not when asked directly. Support answers that quote a per-hour
  or per-day example are relayed as "an illustrative example", always with the
  authoritative sources below, and the current rate is confirmed on those
  pages rather than repeated from memory.
* Authoritative sources: the snapshot billing rules page
  <https://help.aliyun.com/document_detail/56159.html>, the snapshot billing
  overview <https://help.aliyun.com/zh/ecs/product-overview/snapshots-1>, the
  stop-charging note <https://help.aliyun.com/document_detail/308385.html>,
  and the price calculators for
  ECS <https://www.aliyun.com/price/detail?saleProductCode=ecs> and OSS
  <https://www.aliyun.com/price/detail/oss>.
* Capacity cannot be predicted: a snapshot's size depends on which blocks
  changed, so "how much will this cost per month" has no honest answer before
  the entries exist. Say this instead of producing a number.
* Commercial asks found in the same conversation - arrears waiver, coupons,
  renewal discount, cancellation - are separated from the technical question,
  answered as facts only, and routed to human staff.

## Documented evidence gaps (never auto-answered)

These remain open items; the skill states what the references prove and hands
the rest off instead of picking a side:

1. Whether an automatic snapshot policy can replicate to another region - the
   product documentation governs; route to
   `alibabacloud-ebs-disk-snapshot-management`.
2. Whether an archive or cold snapshot class exists for ECS snapshots, and how
   it is billed or deducted - unresolved between an answer saying no such type
   exists and deduction wording that excludes archived snapshots; cite
   <https://help.aliyun.com/zh/ecs/oss-storage-bag.md> and the billing page
   rather than asserting.
3. The per-disk snapshot count limit and the quota raise flow - no document
   verified here; report observed counts only.
4. The per-page batch limit in the console snapshot list - a console behavior
   to be seen on the page, not asserted here.
5. The unit price of cross-region snapshot replication traffic - confirm on
   the billing page; do not quote a verbal figure.
6. Whether a free trial quota applies to snapshot storage - confirm on the
   billing page; the 100 GiB long-term free quota belongs to the ECS file
   backup essential edition, a different product
   ([concept-boundaries.md](snapshot-billing-cleanup__concept-boundaries.md)).
