# What deducts snapshot storage, in which order, and with which limits

Answers the family of claims: "I bought a 1 TB OSS package, why is there still
a snapshot charge", "my savings plan should cover this", "is there a free
quota", "which package should I buy". The last one is a purchase decision and
goes to human staff; this file only fixes the facts.

Authority for every statement below: OSS resource package deduction for
snapshots <https://help.aliyun.com/zh/ecs/oss-storage-bag.md>, the snapshot
billing rules <https://help.aliyun.com/document_detail/56159.html>, the data
protection and recovery FAQ
<https://help.aliyun.com/zh/ecs/data-protection-and-recovery-faqs.md>, the
stop-charging note <https://help.aliyun.com/document_detail/308385.html>, the
OSS resource plan pages
<https://help.aliyun.com/zh/oss/purchase-resource-plans> and
<https://help.aliyun.com/zh/oss/resource-plan-overview>, and the OSS storage
fee page <https://help.aliyun.com/zh/oss/storage-fees>.

## 1. Deduction order for snapshot storage

```
OSS storage package (standard locally redundant storage plan)
  -> storage capacity unit (SCU)
    -> pay-as-you-go for whatever remains
```

Deduction is automatic once a matching package exists; no switch has to be
turned on for it.

## 2. The four limits that explain almost every "package did not cover it"

| Limit | Consequence to state |
| --- | --- |
| Same region only | A package bought for one region does not absorb snapshot capacity in another region |
| Standard snapshot storage only | Only the standard snapshot storage fee is deductible; see the archive note below |
| Covers usage generated after purchase | Capacity produced before the package was bought is not retroactively absorbed; a gap between a trial ending and a package starting is billed |
| Capacity above the package size | The excess is billed pay-as-you-go; the package is not a cap that stops charging or stops snapshots from being created |

The matching rule for "my package is 1 TB but I still got charged": compare the
package size against the snapshot capacity **over the billed period**, not
against a single point in time. Capacity is cumulative within a period, so the
peak inside that window is what exceeded the package. The place to prove it is
the resource package deduction detail page, filtered to the billing period:
`billing-cost.console.aliyun.com/ri/detail?commodityCode=all`, with usage
summary at `billing-cost.console.aliyun.com/ri/summary`. This skill names that
page and the filter to apply; it calls no billing API and never reads the page
for the customer.

## 3. What does NOT deduct snapshots

* **ECS savings plan** - covers the instance and system-disk fees of the
  matching specification. Snapshot storage is billed separately and is never
  absorbed by a savings plan. This is the single most common wrong expectation
  and is stated first whenever a customer cites a savings plan balance.
* **Cloud Backup / file backup fees** - a backup plan produces its own charges.
  The snapshots a backup flow creates still bill as snapshot storage; the
  service fee bills as that service. Removing the plan is a console action in
  the backup product, not here.
* **Anything bought for another product line** - model or knowledge-base
  storage, security centre capacity, traffic packages. If the invoice line is
  not the snapshot billing item, this skill says so and routes it
  ([handoffs.md](snapshot-billing-cleanup__handoffs.md)).

## 4. Free quota statements, per product

* The long-term **100 GiB** free quota belongs to the ECS file backup
  essential edition and is measured by that product
  (<https://help.aliyun.com/zh/cloud-backup/user-guide/ecs-file-backup-essential-edition>).
  It is **not** a snapshot quota, and file backup stores its data in its own
  storage space rather than inside the customer's visible OSS capacity.
* Snapshot storage itself is charged from the first byte created by the
  standard billing model unless the billing page documents otherwise for the
  account. Where a trial period is involved, the question "does the window
  between trial end and package start cost anything" is answered by the billing
  page and the bill detail for that period - not by assumption. Whether a
  snapshot-specific trial quota applies to an account is an open item: see the
  evidence gap list in
  [snapshot-billing-decision-tree.md](snapshot-billing-cleanup__snapshot-billing-decision-tree.md).
* Archive or cold snapshot classes: the deduction document excludes archived
  snapshots, while support answers have also stated that no cold snapshot type
  exists for ECS. The product documentation governs; this skill does not assert
  either way, and never quotes a price for it.

## 5. Package versus reserved capacity, when the customer asks

* A resource package is a prepaid allowance for a measured quantity of storage;
  it absorbs matching usage until it is exhausted.
* Reserved capacity commits to holding a minimum amount of a specific storage
  type, priced on that commitment.
* Size selection needs the account's actual capacity curve. The snapshot
  console shows capacity growth per region, and the ECS overview shows capacity
  per region. Point at those pages plus the OSS price calculator
  <https://www.aliyun.com/price/detail/oss>, and stop: recommending a size or a
  SKU is a commercial decision routed to human staff.
* There is no "remaining snapshot capacity" concept to read out: snapshots have
  no independent allowance that can run out. Capacity above a package is simply
  billed, and nothing automatically blocks further snapshots from being
  created. A spending alert is the only guard.

## 6. Stopping the charge

* There is no service switch to close. The snapshot charge stops once no
  snapshot capacity remains in the region - which is why the region-by-region
  enumeration in [snapshot-dependency-and-deletion.md](snapshot-billing-cleanup__snapshot-dependency-and-deletion.md)
  comes before any claim that the charge will stop.
* A zero-balance or arrears notice that says snapshot service was restored does
  not by itself prove a snapshot exists; the enumeration decides that.
* After the last deletion, expect settlement lag before the next bill reflects
  it. Say "the line for the closed period may still appear", never a date.
* Backup plans created by another product must be removed in that product, and
  any snapshots they produced then follow the deletion order in this package.
