# Disk DR Capability Boundary (what ECS does and does not provide)

Use this file to answer DR capability questions with one consistent voice.
Every statement below is a capability-boundary statement, not a live check:
combine it with the per-region evidence inventory from
`scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py` before concluding anything about a specific
account.

## 1. A single ECS instance has no automatic failover

- A single ECS instance runs in ONE zone. If the instance or its zone fails,
  Alibaba Cloud does NOT automatically switch the business to another server
  and there is no built-in "standby server" behind one instance.
- Automatic takeover requires an architecture the customer designs and
  operates (for example load balancing plus auto scaling across zones, or a
  standby instance the customer maintains). Those products are outside this
  skill; explain the difference and hand off per
  [handoff-map.md](handoff-map.md).
- Consequence for filing/registration questions ("which server does my
  business fail over to"): with a single instance and no customer-built
  redundancy, the honest answer is "none -- failover is not automatic".

## 2. Snapshots are region-local; no automatic cross-region backup

- A snapshot is stored in the region where it was created. There is no automatic mechanism that
  copies snapshots to another region; a cross-region copy is an operation the customer starts (from
  the snapshot page or programmatically).
- Verified facts about a snapshot copy (read from the official page on 2026-09-18,
  `https://help.aliyun.com/en/ecs/user-guide/copy-a-snapshot.md`):
  - a standard cross-region copy must target a different region; an encrypted copy may stay in the
    same region;
  - the first copy of a snapshot is full size, later copies to the same region are incremental;
  - a copy is billed as snapshot storage **in the destination region** plus a data transfer fee (and
    a KMS fee when a customer-managed key is used);
  - the copy gets a **new snapshot id**, so it cannot be used to roll back the source disk; the
    retention period and the tags of the source snapshot are not carried over, and copies do not
    support instant access.
- Ownership split: this skill states the boundary and points at that page. The step-by-step copy
  procedure, the policy and quota questions, and snapshot cost clean-up belong to the snapshot
  management domain (`alibabacloud-ebs-disk-snapshot-management`, name pending alignment) -- see
  [handoff-map.md](handoff-map.md).

## 3. Disk-level DR options (the product axis of this skill)

| Option | What it does | Redundancy scope | Who operates it | Official doc (cite this URL) |
|---|---|---|---|---|
| Disk async replication (replication pair) | Asynchronous block-level replication from a primary cloud disk to a secondary cloud disk; failover is initiated manually | Cross-region (or cross-zone) at the disk layer | Customer, in the console | `create-replication-pair` URL in the guidance docs |
| Replication-pair consistency group | Replicates MULTIPLE disks together with crash consistency, for multi-disk applications such as databases | Same as replication pair, multi-disk | Customer, in the console | `create-consistency-group` URL in the guidance docs |
| Zone-redundant ESSD (regional ESSD) | Disk data is replicated across multiple zones of the SAME region by the platform at creation time | Cross-zone within one region | Platform, once the disk type is chosen at creation | `regional-essd` URL in the guidance docs |
| DR failover of a replication pair | Switches the business to the secondary disk when the primary site fails | n/a (recovery procedure) | Customer, in the console | `dr-failover` URL in the guidance docs |
| Deleting a replication pair | Stops replication and releases the pair ("stop the DR feature" requests) | n/a (teardown procedure) | Customer, in the console | `delete-replication-pair` URL in the guidance docs |

Instance-level rebuild paths (clone instance, create from custom image,
purchase same configuration) are NOT continuous DR: they rebuild a copy at a
point in time and are useful as a "quick standby server" workaround only.
Explain the difference and hand off; the doc URLs are in the guidance docs
(`clone-instance`, `create-from-custom-image`, `same-config-instance`,
`custom-image-overview`).

The exact console navigation for every customer-executed step lives in the
official doc above that step -- cite the URL, walk the customer through the
doc's own console path, and never invent menu names.

## 4. Verified specification figures and quoting discipline

The figures below were read from the official pages of this product axis on 2026-09-18 (page names
match the `guidance_docs` keys in the script report). Quote from this table, and cite the page you
are quoting. Anything not in this table and not in front of you is not quotable.

| Item | Published value | Source page |
|---|---|---|
| Async replication cycle | data is replicated automatically every 15 minutes | `dr-overview` |
| Default RPO of a replication pair | 15 minutes, i.e. writes after the last completed cycle can be lost when the primary disk fails | `dr-overview`, `create-replication-pair` |
| RPO with RTC enabled | 10 minutes or less, with an SLA commitment | `dr-overview`, `create-replication-pair` |
| Replication speed | up to 100 MB/s, varying with load | `dr-overview` |
| RTO | defined as the time from the primary disk failing until the disk is back in service; the spec page illustrates it with a 1-hour example and publishes no RTO commitment | `dr-overview` |
| Replication relations per disk | 1 | `dr-overview` |
| Replication pairs per consistent group | 17 | `dr-overview`, `create-consistency-group` |
| Primary disk category | ESSD or ESSD AutoPL | `dr-overview` |
| Secondary disk category | same category, same performance level, same capacity as the primary disk | `dr-overview` |
| Secondary disk during replication | read-only: cannot be attached or written to; no rollback from snapshot on the secondary side | `dr-overview`, `create-replication-pair` |
| Consistency of same-timestamp snapshots | primary and secondary snapshots created at the same point are not guaranteed consistent (RPO effect) | `dr-overview` |
| Regional (zone-redundant) ESSD RPO | 0 for zone failures -- writes are synchronous across the zones of one region | `regional-essd` |
| Regional ESSD form factor | data disk only, never a system disk; capacity 10 to 65,536 GiB; up to 50,000 IOPS and 350 MB/s per disk | `regional-essd` |
| Regional ESSD and async replication | not combinable: cross-zone async replication is N/A, cross-region is not supported | `regional-essd` |
| Regional ESSD write latency trade-off | synchronous cross-zone writes raise average write latency slightly versus a PL1 ESSD; no performance provisions or burst performance | `regional-essd` |
| Regional ESSD supported regions | China (Hangzhou, Shanghai, Beijing, Zhangjiakou, Shenzhen, Ulanqab, Hong Kong), Singapore, Kuala Lumpur, Jakarta, Tokyo | `regional-essd` |

### Billing model (state the model, never a number)

- Async replication: pay-as-you-go. The spec page describes the fee as based on the **volume of
  replicated data** and states that cross-region replication is charged while same-region cross-zone
  replication is not charged at present; enabling RTC adds a separate charge for cross-region pairs.
  A separate official page describes the pair service fee as **capacity-based**. The two wordings do
  not agree, so present it as: "billable, pay-as-you-go; the exact basis and unit price are shown on
  the pricing page of the order screen -- confirm there". **Never quote a unit price or a total.**
- A consistent group bills through its pairs, same model.
- A DR drill creates a real pay-as-you-go disk that keeps billing until released.
- Regional ESSD is billed by capacity, pay-as-you-go or subscription.
- Snapshots (including copies) are billed as snapshot storage in the region where they are stored,
  plus a data transfer fee for cross-region copies and a KMS fee for customer-managed keys.

### Discipline

1. Cite the official doc URL you used.
2. Quote only numbers from the table above, or numbers the customer or the open console page shows.
3. Never state an RPO/RTO, a limit or a price from memory: these are spec commitments, and an
   invented number is a factual error.
4. If the customer's console or a freshly opened page disagrees with this table, the page wins --
   say which value differs and continue from the page.

## 5. Charges and risk notice (must accompany every guidance step)

- Disk async replication and zone-redundant ESSD are billable capabilities
  (replication traffic, secondary-disk storage, or the zone-redundant disk
  price). Before the customer creates anything, tell them: what will be
  created, that charges will accrue while it exists, and where the official
  price documentation is (pricing page linked from the console order page).
- Creating a replication pair, failing over, and deleting a pair are WRITE
  operations on the customer side. This skill is read-only: it outputs the
  steps, the risk notice, the expected result and the verification method,
  and the customer executes them in their own console.
- A DR failover changes which disk/region serves the business. After a
  failover the customer must verify application configuration (mount points,
  connection strings, DNS) before declaring recovery complete.
- Deleting a replication pair stops protection immediately; the secondary
  disk no longer receives updates. Confirm the customer understands this
  before guiding the deletion.

## 6. Reading the inventory output

- `category` is echoed verbatim from the disk query; the accompanying
  `category_note` marks zone-redundant categories. An unknown category value
  is echoed without a note -- report it as-is and check the official disk
  category table instead of guessing.
- `enable_auto_snapshot` true means an automatic snapshot policy applies to
  that disk (snapshot lifecycle questions hand off to snapshot management).
- Snapshot rows prove snapshot-based backup exists IN THAT REGION ONLY
  (see section 2).
- Replication pairs and consistency groups are NOT part of the read-only
  surface; the inventory says so explicitly. Verification of replication
  state is a customer console self-check (paste back the pair status or a
  screenshot) -- see [self-check-commands.md](self-check-commands.md).
