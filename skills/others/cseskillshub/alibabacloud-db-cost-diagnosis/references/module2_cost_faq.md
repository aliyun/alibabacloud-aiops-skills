# Module 2: Customer-Facing Cost FAQ

Distilled, high-frequency billing questions for Alibaba Cloud database products
(RDS, MongoDB, PolarDB, Tair/Redis, DTS, DBS, CDT, DMS, DAS). All answers are
written from the customer's perspective and contain only publicly available
billing knowledge. Pair with the cost query orchestration module listed in the
SKILL.md Module Index to verify each answer against real bill data.

## 1. Deleted / released instance still billed (most frequent)

**Q: My instance was deleted/released. Why am I still being charged?**
A: Releasing an instance does not automatically delete its backups. The three
most common causes:

1. **Backup retention policy of the deleted instance** -- "keep last
   backup"/"keep all" policies keep accruing DBS charges.
2. **Cross-region backup not closed** -- copies bill until they expire.
3. **Surviving DBS backup plans** -- pay-as-you-go plans bill as long as the
   plan exists, even if the source database is gone.

**Q: How do I stop the billing of a released instance's backups?**
A: RDS console -> Backups -> **Deleted Instance Backups**: select the correct
region and a wide time range (each region lists its own instances; wrong
region or a narrow range is why an instance seems missing), expand the
data / log / cross-region tabs, and set retention to "keep none". Billing
stops the next day. Deleted backups are unrecoverable -- confirm the data is
no longer needed, and check every region on the same page.

**Q: My subscription instance expired, or I closed cross-region backup.
Why is backup still billed?**
A: Expiry/release does not clean up backups: a "keep" retention policy keeps
charging pay-as-you-go, and closed cross-region sets keep billing until their
retention (at least 7 days) expires. Set retention to "keep none".

**Q: The bill shows DBS charges but I can't find any DBS instance in the
console. What is it?**
A: DBS charges frequently come from backup storage of *other* products (RDS
deleted-instance backups, DMS data archiving auto-creating a pay-as-you-go
DBS plan, or sandbox/restore features). Check the billing item names in Bill
Details (filter by product `dbs`), then follow the matching path above.

**Q: How do I release a pay-as-you-go DBS backup plan? I cannot find any
unsubscribe button.**
A: Pay-as-you-go plans are not "unsubscribed" -- they are **released**, and
they keep billing as long as the plan exists:

1. DBS console -> Backup Plans. **Switch regions one by one**: each region
   lists its own plans, and the wrong region is the usual reason the plan
   seems missing.
2. Find the target plan -> More -> **Release** (subscription plans use
   Unsubscribe at the same position). Billing stops afterwards; the backup
   data becomes unrecoverable. If the charge actually comes from a deleted
   instance's backups, use the Deleted Instance Backups path above instead.

If the plan appears nowhere after checking every region, submit a support
ticket -- occasionally the console entry is inconsistent with the billing
record.

**Q: PolarDB: I deleted the cluster, why is it still charged?**
A: After deletion, second-level backups may be retained (including in the
recycle bin) and keep billing until manually removed. Check PolarDB console ->
Recycle Bin and delete any retained backups.

## 2. Backup free quota and backup billing

**Q: What is the free backup quota?**
A:

| Product | Free backup quota |
|---|---|
| RDS / MongoDB, cloud-disk instances | 200% of the purchased storage |
| RDS / MongoDB, local-disk instances | 50% of the purchased storage |
| Tair / Redis | Equal to instance memory size |
| PolarDB MySQL | Equal to instance memory size |

Backup storage beyond the quota is billed pay-as-you-go (roughly
0.0075 CNY/GB/day for RDS-class backup storage), metered and billed daily.

**Q: PolarDB: how are level-1 and level-2 backups billed?**
A: Both are metered by the **data change volume** captured within the
retention period, not by the live data size:

- Level-1 backup: fast restore, higher unit price; each snapshot stops
  billing once its retention (e.g. 14 days) expires and it is released.
- With level-2 enabled, an expired level-1 snapshot is automatically
  **transferred to level-2**: much lower unit price (compressed data,
  cheaper media) but longer retention (e.g. 30 days), billed until expiry.

**Q: PolarDB: after I cleaned up binlog / deleted data, why does my backup
bill rise first and only drop later?**
A: Bulk cleanup sharply increases the data change volume that backups
record. The transferred level-2 sets carry the *same* change volume as the
level-1 originals -- transfer does not shrink it. When the level-1 sets
expire they stop billing ("level-1 decreases"), but the corresponding
level-2 sets keep billing for their longer retention ("level-2 increases"),
so the two effects overlap; the total only falls after those transferred
level-2 sets expire in turn.

**Q: My backups look within the free quota, yet I got a tiny backup overage
charge (e.g. 0.42 CNY). Why?**
A: The quota is measured against the **actual usage of backup sets at each
metering point**, not live data size or a month-end average. Usage counts
every retained set (data + log + cross-region copies) at metering time, so a
brief spike -- e.g. the full backup triggered right after a policy change --
can push it over the quota; cross-region copies are metered separately and
often leave small residual charges. Locate the charge in Bill Details: filter
by product (`rds` / `dbs`) and find the **backup_storage** billing item.

**Q: How do I reduce backup cost?**
A: Lower frequency (e.g. twice a week), shorten retention (e.g. 7 days; log
backup minimum), set deleted-instance backups to "keep none", close
cross-region backup, or buy a storage plan to offset backup storage.

**Q: Backup exceeds the free quota. Can I delete backups manually right now?**
A: Automatic backups expire per the retention policy and cannot be
force-deleted; adjust the policy and wait. Manual backups can be deleted by
hand. At least 3 backup sets are always kept -- expired-but-kept sets are
still billed.

**Q: Why is my snapshot backup far larger than my data, and why did usage
spike after a policy change?**
A: Snapshots count every non-empty disk block, not the file-system data
size (hence the 200% quota for cloud-disk instances); size is capped by disk
size. Each policy change triggers one immediate full backup that can push
usage briefly above the quota -- wait ~7 days for old sets to expire. Manual
backups are retained permanently by default; delete them by hand.

**Q: Can I disable backup entirely? Can log backup run once a week?**
A: No to both; backup is a data-safety core feature. You can only lower
frequency/retention, or disable log backup entirely (losing point-in-time
restore); log backup backs up continuously with only retention days
configurable.

## 3. Subscription vs pay-as-you-go; split of billing items

**Q: My instance is subscription. Why are there extra charges?**
A: Subscription covers only the instance (compute) fee and the storage fee.
These items are billed separately, pay-as-you-go:

- Read-only instances (independently billed)
- Backup storage beyond the free quota
- Database proxy of dedicated specification (hourly; general spec is free)
- SQL audit / SQL Explorer (billed by storage volume)
- Cross-region backup (storage + traffic)

Use the split-item bill query (`DescribeSplitItemBill`) to see exactly which
component is charging.

**Q: PolarDB is subscription, yet I see monthly pay-as-you-go charges. Why?**
A: PolarDB bills **compute and storage separately**: compute nodes can be
subscription (prepaid) while storage is independently metered by capacity,
pay-as-you-go. They appear as different rows / billing modes on the bill,
so a "subscription" cluster still produces a monthly storage charge. Use the
split-item query to separate the two.

**Q: Can I switch PolarDB storage from pay-as-you-go to subscription?**
A: No -- storage billed by capacity cannot be converted to subscription on
its own. Either buy a storage plan to offset the storage bill, or
self-service unsubscribe the whole cluster in the expense center and
repurchase it with subscription storage; the refund is subject to the
unsubscribe quota and platform review.

**Q: A subscription charge suddenly tripled in one month (e.g. 22 -> 66 CNY).
Is it a price increase?**
A: Subscription lines on the bill are **renewal payments**: amount = spec
price x renewed duration. A jump by a whole multiple usually means the
renewal duration changed (e.g. 1 month -> 3 months), not the unit price.
Billing APIs carry no order/renewal-duration data -- confirm in the expense
center under Orders / Renewal records.

**Q: I bought a storage plan, but pay-as-you-go charges still appear. Why?**
A: A storage plan only offsets the eligible storage usage that matches its
scope (product, region, capacity); usage beyond the plan capacity keeps
billing pay-as-you-go, and out-of-scope items stay visible. Compare the
billing items in Bill Details and check each item's deduction column to see
which charges the plan actually offset.

**Q: How large a storage plan should I buy?**
A: Locate the overage in Bill Details (e.g. 351 GB beyond the free quota),
then buy a plan sized for that excess times the **deduction coefficient** --
1 GB of plan capacity does not always offset 1 GB of usage (the coefficient
differs by storage type; see the storage-plan docs). Keep headroom and
verify via the deduction column in Bill Details.

**Q: I converted pay-as-you-go to subscription and got one large charge. Is
it wrong?**
A: No. Conversion prepays the entire chosen duration at once (choosing 1 year
charges 12 months immediately). It is prepayment, not overcharging.

**Q: Pay-as-you-go instance: do I pay even when idle?**
A: Yes. A pay-as-you-go instance bills for every hour it exists, regardless
of workload. Releasing is the only way to stop all billing; stopping an
upstream application does NOT stop database charges -- the instance is an
independent resource.

**Q: If I suspend (pause) the RDS instance instead of releasing it, what is
billed?**
A: While suspended, only **storage** keeps billing; the compute fee pauses.
Suspension is capped at **15 days** -- if you do not start the instance by
then, it starts automatically for maintenance and compute billing resumes
from that moment. Suspend for short pauses; release to stop billing for
good.

**Q: My read-only instance still costs the same after I downgraded the
primary. Why?**
A: Read-only instances are billed independently; spec changes of the primary
are never synchronized to them.

## 4. Renewal and order charges (auto-renewal, price jumps)

**Q: An auto-renewal charge appeared on my account. How do I trace where it
came from?**
A: The bill only shows the payment; the chain of events lives in the orders.
Trace it in the expense center: **Orders -> Order Management**, filter
Renew-type orders and reconstruct the renewal sequence of the instance by
creation time, then compare it with the instance's renewal setting
(auto-renewal on/off and period). `scripts/audit_renewal_orders.py`
reconstructs exactly this sequence (renewals grouped per commodity, refund /
cancelled orders flagged as anomalies).

**Q: A renewal cost far more than the previous one. Is it a price change?**
A: The renewal price is set at the **order** level by duration x list price
x applicable discount, so a gap between two adjacent renewals usually means
a longer renewal term, a spec change before renewal, or a discount that no
longer applies. The billing APIs carry **no duration/discount dimension**,
so this must be attributed order by order in the expense center; the audit
script flags adjacent renewals whose price ratio exceeds 3x as candidates.

## 5. Billing delay and statement timing

**Q: I stopped/closed something yesterday, but today's bill still shows it.**
A: Pay-as-you-go items bill with a delay (roughly t+1): daily-metered items
settle one day later. Charges dated before your change are normal; no new
charges should appear from the day after.

**Q: New billing items suddenly appeared that never showed before. Why?**
A: Tiny hourly amounts used to be rounded away; under monthly settlement
they accumulate and become visible -- close the ones you do not need.

**Q: When does the current month's bill become complete?**
A: Pay-as-you-go data keeps settling for a few days after month end; treat
the current cycle as provisional and the previous closed cycle as final.

## 6. Serverless: pause vs release

**Q: I paused my Serverless instance. Why is it still charged?**
A: Pause removes only the **compute** charge; **storage keeps billing** while
data is retained. To stop all charges you must release the instance -- which
permanently deletes the data.

**Q: How is Serverless compute billed per hour?**
A: Each hour bills at the peak RCU used within that hour. Even a few minutes
at a high RCU makes the whole hour bill at that level.

**Q: Why doesn't my Serverless instance scale down?**
A: Scale-down requires both CPU and memory utilization below the threshold
(commonly 50%); cache-backed memory blocks it -- an off-peak restart
releases the cache (short interruption; clients reconnect). If configuration
and workload are normal yet it never pauses, suspect a product-side issue
and submit a support ticket.

## 7. DTS: when billing starts and how to stop it

**Q: I paused my DTS synchronization task, or it failed. Why still charged?**
A: Data **synchronization** and data **subscription** tasks bill while paused
or failed as long as they are unreleased (link resources stay reserved). Only
incremental data **migration** stops billing when paused. A paused Serverless
sync still bills a minimum of 1 DU. To stop billing completely, release the
task.

**Q: When exactly does DTS billing start?**
A: For synchronization, billing starts once the **incremental data collection
module starts** -- i.e. after the precheck passes and the purchase completes
-- and continues while the task exists, including paused periods.

**Q: Is data verification included in the DTS fee?**
A: No. If you tick **data verification** when configuring the task, it is
billed separately; uncheck it if it is not needed.

**Q: Is a subscription (monthly) DTS task charged repeatedly?**
A: It pays once, upfront, for the chosen configuration and duration. The risk
is auto-renewal: for any subscription task no longer in use, cancel
auto-renewal or release the task instance.

## 8. CDT: Cloud Data Transfer charges

**Q: What is the CDT charge on my bill?**
A: CDT (Cloud Data Transfer) aggregates the public-network transfer fees
(mainly internet outbound traffic) of your resources. Every account gets a
monthly free quota; usage beyond it bills pay-as-you-go, or is offset by an
active CDT resource plan / savings plan.

**Q: I have a CDT resource plan / savings plan. Why still pay-as-you-go?**
A: Plans offset only the matching transfer type and region within their
capacity; everything else keeps billing pay-as-you-go, and an expired plan
converts remaining usage automatically. Check plan validity in the expense
center, then compare the per-billing-item deduction columns in Bill Details.

## 9. DMS billing clarifications

**Q: The price says 6.4 CNY but my monthly bill is around 198 CNY. Why?**
A: 6.4 CNY is a **per-day** unit price (CNY/instance/day), not monthly.
6.4 x 31 days = 198.4 CNY/month.

**Q: I don't run any DMS tasks / never bought DMS on purpose. Why charged?**
A: Pay-as-you-go DMS compute resources bill from the moment the instance is
created, regardless of task execution. DMS control modes (protected /
security-collaboration) are also billed per instance per day, and some flows
switch paid components on automatically -- most commonly **sensitive data
protection** (about 10 CNY/instance/day). Check DMS console -> Order
Management and release / unsubscribe what you do not need.

**Q: I released my database. Does the DMS control mode stop automatically?**
A: No. It is billed independently and does not follow the database instance.
Unsubscribe in DMS console -> Order Management; expect one more day of
billing (daily settlement, see section 5).

## 10. DAS billing

**Q: A DAS charge appears on my bill. How do I stop it?**
A: Paid DAS features (e.g. data ingestion of the advanced professional
edition) bill independently of the database instance, so releasing the
instance does not stop them. Disable/downgrade the feature in the DAS
console or unsubscribe via the expense center; expect one final day of
daily-settled billing.

## 11. Storage cost and auto scaling

**Q: Storage cost grew suddenly. What should I check?**
A: In order:

1. **Auto storage scaling threshold** -- a very low threshold (e.g. 10% free
   space) triggers frequent expansions, especially when temporary files or
   binlog grow. Set the threshold to 80%-90% and shrink manually off-peak.
2. **Temporary files** -- heavy sorts / GROUP BY from slow SQL create
   temporary files that only release on instance restart. Optimize the SQL
   and restart off-peak if needed.
3. **Binlog / log growth** -- a write spike raises backup and cross-region
   traffic cost.

**Q: How does storage auto expansion work, and what does it cost?**
A: When enabled, storage grows automatically once free space drops below
the threshold. Each expansion adds the larger of:

1. 5 GB (adjusted to 10 GB when total storage is under 50 GB and free space
   below 10%);
2. 15% of the current storage, rounded to the nearest multiple of 5 GB
   (e.g. 100 GB total -> +15 GB -> 115 GB).

Each expansion bills at the same price as a manual spec change -- preview
the amount in Change Configuration without paying; keep enough account
balance so the expansion cannot fail. A full-storage alert is often caused
by temporary files from slow queries (see below), so check the root cause
first.

**Q: Auto performance scaling: how is it billed?**
A: It steps up within the same spec family (e.g. 2C4G -> 2C8G), billed by
the second at the higher spec while active, and scales back automatically
when load drops (the scale-back is not refunded).

**Q: DAS elastic scaling: is it free?**
A: The DAS feature is free, but each triggered spec change produces normal
RDS/PolarDB charges at the new spec.

## 12. Reading and lowering your bill

**Q: Where do I see the cost breakdown?**
A: Console -> Expenses and Costs -> Bill Details; filter by product
(rds / dds / polardb / kvstore / dbs / dms / cdt) and billing item; the
split-item view separates instance, storage, and backup fees.

**Q: Some charges look like database fees but are not. What usually confuses
people?**
A: ECS snapshots, SLS (can be produced by SQL Explorer/audit), NAT/SLB
network fees, and security products -- filter the bill by product code.

**Q: Give me the standard cost-optimization checklist.**
A: Release idle instances (including read-only and DTS tasks); set
deleted-instance backups to "keep none" with ~2x/week frequency and 7-day
retention; close unused cross-region backup and SQL audit; move long-lived
pay-as-you-go workloads to subscription (typically 30%-60% cheaper) or buy
storage/savings plans.

## 13. References (official documentation)

- RDS billing overview: https://help.aliyun.com/zh/rds/product-overview/billing-overview
- RDS billing FAQ: https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/billing-faq
- RDS storage plans: https://help.aliyun.com/zh/rds/product-overview/storage-plans
- PolarDB billing items: https://help.aliyun.com/zh/polardb/polardb-for-mysql/billing-item/
- DBS backup fees: https://help.aliyun.com/zh/dms/product-overview/backup-fees

**Other products**: SelectDB, ClickHouse, and Lindorm are not covered by
this FAQ -- refer to each product's official billing documentation.
