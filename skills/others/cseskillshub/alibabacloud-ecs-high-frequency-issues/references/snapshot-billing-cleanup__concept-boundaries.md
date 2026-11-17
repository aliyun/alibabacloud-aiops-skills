# Concept and fee-ownership boundaries: snapshot, image, backup, file backup, OSS

Customers use one word - "backup" - for five different products, and the fee
questions that follow are usually ownership mistakes rather than billing
mistakes. This file fixes what each mechanism is, what it bills as, and where
the boundary of this skill stops. Every statement is anchored to a document;
where the documents do not settle a point, say so and hand off rather than
picking a side.

## 1. The fact table

| Mechanism | Granularity | Real-time? | Where data lives | What the fee line is | Owned by |
| --- | --- | --- | --- | --- | --- |
| Manual snapshot | Cloud disk, block level | No - a point in time | A snapshot storage space managed by the service, not browsable by the customer, not the disk's own space | Snapshot storage, per region, by capacity and duration | ECS snapshots (this skill's evidence side) |
| Automatic snapshot policy | Cloud disk, block level, incremental | Scheduled, not continuous | Same as above | Snapshot storage; the policy itself is not a separate charge | ECS snapshot policies - **configuration is not this skill** |
| Custom image | Instance or disk set, built **on top of** snapshots | No - point in time | Snapshots under the hood, plus image metadata | The snapshot storage its constituent snapshots occupy | ECS images (image lifecycle is not this skill) |
| Cloud Backup, whole-machine edition | Instance level, orchestrates snapshots | No | Snapshots it creates plus its own backup data | Its own service fee **plus** the snapshots it produces | Cloud Backup |
| ECS file backup, essential edition | File level, daily automatic | No - daily, with a fine-grained restore window for recent deletions | Its own storage space, **not** the customer's visible OSS capacity | That product's own fee; excluded system directories are not covered | Cloud Backup file backup |
| OSS object storage / manual upload | Object or file level | Only as often as the customer uploads | The customer's own bucket | OSS storage, plus request and outbound traffic fees | OSS |

Anchor documents: whole-machine backup versus the snapshot service
<https://help.aliyun.com/document_detail/465763.html>, ECS file backup
essential edition
<https://help.aliyun.com/zh/cloud-backup/user-guide/ecs-file-backup-essential-edition>,
creating a custom image from an instance
<https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance>
and <https://help.aliyun.com/document_detail/35109.html>, snapshot working
principles <https://help.aliyun.com/zh/ecs/user-guide/how-do-snapshots-work>
and <https://help.aliyun.com/document_detail/25392.html>, the data protection
and recovery FAQ
<https://help.aliyun.com/zh/ecs/data-protection-and-recovery-faqs.md>, and the
OSS storage fee page <https://help.aliyun.com/zh/oss/storage-fees>.

## 2. Mechanics this skill may state

* **Incremental, block level.** The first snapshot of a chain captures the
  blocks in full; each later snapshot stores only the blocks that changed since
  the previous one. Nothing overwrites an earlier snapshot, so an untouched
  first snapshot stays exactly as it was until it is deleted or expires.
* **Displayed size is restore size.** What the console shows per entry is the
  data needed to restore from that entry, not the marginal bytes that entry
  added to the chain. This is why entries look "too big" and why the chain
  total is smaller than the sum of the entries.
* **Point in time, not live.** A snapshot reproduces the state at the moment it
  was created. A database that keeps writing is not covered between snapshots;
  continuous protection is a different product's job.
* **Manual and automatic entries coexist.** Automatic snapshots do not replace
  manual ones and each survives on its own retention. An automatic entry with no
  retention value returned must be treated as retained indefinitely, which is
  how unbounded accumulation happens.
* **Images silently add snapshots.** Creating a custom image, including from a
  running instance, makes the service create the snapshots behind it for the
  attached disks; no manual snapshot step is required, and stopping the
  instance is not either. So "I never created any snapshot myself, why is the
  capacity growing" has a normal explanation, and the enumeration names the
  images involved.
* **Snapshots are not mountable, not a disk, not an OSS object.** They are a
  backup record; restoring means creating or rolling back a disk, which is a
  different tier's flow ([handoffs.md](snapshot-billing-cleanup__handoffs.md)).

## 3. Fee-ownership statements, phrased so they do not mix products

* Snapshot storage bills by capacity and duration, per region, and continues
  while entries exist - independent of whether the instance still runs, and
  independent of whether the disk was released.
* A backup plan in another product can produce a service fee **and** snapshot
  capacity. Removing the plan and removing the snapshots are two separate human
  actions; skipping the second leaves the capacity billing.
* File backup uses its own storage: it neither consumes the customer's visible
  OSS capacity nor is it covered by an OSS storage package, and the long-term
  free quota of that edition belongs to that edition, not to snapshots.
* An ECS savings plan does not touch snapshot fees
  ([resource-package-deduction.md](snapshot-billing-cleanup__resource-package-deduction.md)).
* Public egress traffic, the disk itself, disk performance, security products
  and model-platform storage are all separate lines. When the invoice line is
  not the snapshot billing item, this skill identifies that and routes it.

## 4. Quotas and limits, only where the facts are settled

| Question | What may be said |
| --- | --- |
| "Is every one of my snapshots billed?" | Yes, in the sense that every existing entry carries capacity and capacity is billed; not only the newest few |
| "Is there a snapshot count limit?" | Per-disk entry limits exist as a quota, but the authoritative value and the raise flow are documented elsewhere; report observed counts and route the raise request |
| "Can I cap snapshot capacity or block overspend?" | There is no independent remaining-capacity allowance for snapshots and no automatic block; a spending alert is the only guard |
| "Can a policy back up once a month?" | Policy schedules are set on the policy page; if a requested cadence is not offered there, that is a policy-configuration question and goes to the snapshot management tier |
| "Do snapshots expire automatically?" | Only what retention says. An automatic entry without a returned retention value is treated as permanent until the policy page proves otherwise |
| "Is there a cold or archive snapshot class that is cheaper?" | An open point where answers have conflicted; the documents govern and this skill does not assert it either way |

## 5. Selection questions: facts, then stop

"Should I keep snapshots only, or also buy backup or images?" is a management
decision. The honest answer shape is: what each mechanism protects, how far
back it can go, how granular a restore it allows, what it costs per the billing
page, and what the account already has. Then stop - no purchase recommendation,
no bundle advice, no price forecast, no commitment about savings. Renewal
discounts, coupons, arrears waivers and cancellation feasibility go to human
staff, and the technical facts already collected are handed over with the rest.

## 6. Boundary answers this skill does not give

Rollback and system-disk restoration, building instances from images,
cross-account image sharing and copying, OS replacement, server migration,
database-level backup design, and OSS upload tooling are each other tiers'
work: identify them, state which one, and use the handoff sentences in
[handoffs.md](snapshot-billing-cleanup__handoffs.md) together with the evidence already gathered.
