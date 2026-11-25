# Customer-Executed DR Operations Guidance (verified console paths)

Scope: the operations a customer performs **themselves** in their own console. This skill never
performs, triggers or automates any of them; it outputs the four-part protocol required by section 5
of `SKILL.md`: where and what, risk notice, expected result, verification.

Console labels, limits and statuses below were read from the official documents named at the end of
each section, fetched on 2026-09-18 (English versions). If the customer's console shows different
labels or fields, follow what the customer sees and re-open the document instead of inventing a path.

Prerequisite for all of them, once per account: the first-time prompt in the Elastic Block Storage
(EBS) console asks you to create the service-linked role the replication feature needs.

## 0. Console entry used by every flow

1. Open the **Elastic Block Storage (EBS) console**.
2. Left navigation pane: **Enterprise-level Features** and then
   - **Async Replication** for replication pairs (this menu is labelled
     **Asynchronous Block Storage Replication** on some console versions), or
   - **Consistent Replication** for replication pair-consistent groups (labelled
     **Replication Pair-consistent Group** on some versions).
3. Upper-left / top navigation bar: select the **region** (and resource group) of the object. This
   matters twice: a pair is listed under the region you select, and a failover is performed from the
   region of the **secondary** disk.

## 1. Create and activate a replication pair (one disk)

**When it fits**: one disk needs protection, in another zone of the same region or in another region.
For several related disks that must fail over to one consistent point, use section 2 instead.

**Preconditions (check with the customer; disk facts come from the read-only inventory)**

- Two **ESSD** or **ESSD AutoPL** disks: the primary (source) and a secondary of the **same category,
  same performance level and same capacity**.
- The two disks are in **different zones** (same region, or different regions).
- The secondary disk is **Unattached**; neither disk is being resized or modified.
- A snapshot of the secondary disk is taken (recommended, see risk below).
- Only one async replication relation can exist per disk.

**Risk notice before the customer executes**

- **Activating a replication pair overwrites all data on the secondary disk. The overwrite is not
  reversible.** Snapshot the secondary disk first.
- Encryption must match: only an encrypted disk can replicate to an encrypted disk.
- Cost: async replication is pay-as-you-go and is billed on the amount of replicated data; per the
  product spec page, cross-region replication is charged while same-region cross-zone replication is
  not charged at present, and enabling RTC on a cross-region pair adds a separate charge. Confirm the
  current price on the pricing page shown on the order screen before proceeding; this skill quotes no
  prices.
- While replication runs, the secondary disk is read-only: it cannot be attached to an instance or
  written to, and neither disk can be resized, have its category changed, or be released.

**Steps**

1. EBS console > **Enterprise-level Features** > **Async Replication**; select the primary disk's
   region; open the **Primary Site** tab.
2. Click **Create Replication Pair** and set:
   | Field | What the customer enters |
   |---|---|
   | **Region and Zone** | the primary disk's region and zone |
   | **Disk** | the primary disk id |
   | **Disaster Recovery Region and Zone** | destination zone: same region + other zone (cross-zone), or another region (cross-region) |
   | **Destination Disk** | the secondary disk id (same capacity and performance level) |
   | **Enable Replication Time Control (RTC)** | optional; **Yes** guarantees an RPO of 10 minutes or less |
   | **Risk Disclosure** | select **I am aware of the risks** (confirms the overwrite) |
   | **Replication Pair Name** / **Description** | name for operations, optional description |
3. Complete the payment step.
4. To start replication: in the pair list, click **Activate** in the **Actions** column. In the
   **Activate Replication Pair** dialog, optionally click **Create Snapshot** for the secondary disk,
   then choose the activation mode:
   - **Copy Now** -- one replication pass, then the pair becomes **Stopped** (testing / manual
     control).
   - **OK** -- continuous replication, 15-minute RPO (or 10 minutes or less with RTC). Use this for
     production protection.

**Expected result**: the pair shows **Initial Syncing** with a progress percentage, then **Normal**.
**Normal** means the initial full sync finished and changes are replicated every 15 minutes.

**Verification (read-only)**

- Ask the customer to read back the pair status and the primary/secondary disk ids and regions from
  the pair list.
- Re-run the disk facts: `python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id <secondary-region>
  --disk-id <secondary-disk-id>` and confirm the disk exists with the expected category and size.
- If the destination disk cannot be selected in step 2: the list only shows ESSD / ESSD AutoPL disks
  of matching capacity and performance level that are **unattached** in the destination zone.
- Caveat from the spec: snapshots taken at the same timestamp on the primary and the secondary are
  **not** guaranteed identical, because of the asynchronous RPO window.

Source: `https://help.aliyun.com/zh/ecs/user-guide/create-a-replication-pair.md` (async replication
spec and limits: `https://help.aliyun.com/zh/ecs/user-guide/overview-8.md`).

## 2. Create and start a replication pair-consistent group (several disks)

**When it fits**: an application spread over several disks (for example data disk plus log disk) that
must be recovered to the **same point in time**. A group manages those pairs together.

**Risk notice**

- Everything in section 1 applies, multiplied by the number of pairs.
- **Once a pair is inside a group it can no longer be started, stopped, failed over or
  reverse-replicated on its own** -- those actions must be taken on the group. Plan the operation
  window accordingly.
- Group and pair RTC settings must be consistent: enabling RTC on a group also enables it on the
  pairs added to it (a pair's RTC reverts to disabled when it leaves the group); a pair with RTC
  enabled cannot be added to a group without RTC until one of the two is changed.

**Steps**

1. EBS console > **Enterprise-level Features** > **Consistent Replication**; select region and
   resource group.
2. Open the **Primary Site** (or **Secondary Site**) tab and click
   **Create Replication Pair-consistent Group**. In the right-side panel set **Group Name**,
   **Production Region** (fixed to the current region), **Primary site availability zone**,
   **Disaster Recovery Region**, **Disaster Recovery Zone** and **Replication Time Control (RTC)**,
   then click **OK**. The **RPO (Minutes)** field is shown but is not configurable.
3. Add pairs: click the group id > **Add replication pair** > select the pairs > **OK**.
   Limits: the pair and the group must both be in **Created** or **Stopped** state; the pair must have
   exactly the same replication direction (primary region and zone, secondary region and zone) as the
   group; one group holds at most **17** replication pairs.
4. Start the group: in the **Actions** column click **Start**, then
   - **Copy Now** for a one-time sync (group ends in **Stopped**; available in **Created**,
     **One-time Syncing** or **Stopped** state), or
   - **OK** for automatic replication every 15 minutes (available in **Created**, **Syncing**,
     **Normal** or **Stopped** state).

**Expected result**: the group status reaches **Normal** once the initial replication is complete and
continuous async replication is active.

**Verification**: customer reads back group status and the pair list from the group detail page.
Remember that the pair-level status of a group member is governed by the group.

Source: `https://help.aliyun.com/zh/ecs/user-guide/create-a-replication-pair-consistent-group.md`.

## 3. Disaster recovery drill (verify without interrupting protection)

**What it does**: clones the secondary disk's data at the latest recovery point to a new
pay-as-you-go **drill disk**, so the customer can mount it and check the application. It does not
affect ongoing replication, and a primary-site failure does not affect a drill; a secondary-site
failure can make the drill abnormal.

**Risk notice**: the drill disk is a real billable pay-as-you-go disk. It must be deleted after the
drill, or charges keep accruing.

**Steps**: Async Replication list > select the pair's region and resource group > click the pair id >
in the **Walkthrough** section click **Create walkthroughs** > confirm the region, zone, category and
size of the drill disk > **OK**.

**Expected result**: a pay-as-you-go disk of the same category and size as the secondary disk appears
in the secondary disk's zone, holding data at the latest recovery point. Multiple drills capture
different recovery points.

**Verification and clean-up**: mount the drill disk on a temporary instance, confirm the data, record
observations, then delete the drill in the **Walkthrough** section and **release the drill disk**.

Source: `https://help.aliyun.com/zh/ecs/user-guide/implement-disaster-recovery.md`.

## 4. Failover and reverse replication (recovery after a real failure)

**Warning to deliver first**: a failover **suspends async replication**. Run it only when the primary
disk has actually failed; doing it otherwise loses the writes made on the primary side since the last
replication. If the pair belongs to a consistent group, the failover must be performed on the group,
not on the pair.

**Part 1 -- failover**

1. In the top navigation bar select the region **where the secondary disk resides**.
2. Find the pair whose primary disk failed; in the **Actions** column choose the more-actions icon >
   **Perform Failover**; read the notes and click **OK**.

Expected result: the pair status becomes **Failed Over**, which gives the secondary disk read-write
permission. The customer then attaches the secondary disk to a temporary or replacement instance to
resume service. Business-level verification (mount point, file system integrity, application
connection strings, DNS or endpoint change, service start-up) is performed by the customer; this
skill cannot verify it.

**Part 2 -- reverse replication, after the primary disk is repaired**

**Important**: reverse replication **overwrites all data on the primary disk** with data from the
secondary disk. Snapshot the primary disk first (the dialog offers **Create Snapshot**); if a snapshot
was already taken after the repair, skip it.

1. Select the region where the secondary disk resides.
2. On the failed-over pair: **Actions** > **Perform Reverse Replication** > read the notes >
   **Create Snapshot** for the primary disk > **OK**.

Expected result: status becomes **Stopped**, and the roles swap -- the original secondary becomes the
primary and the original primary becomes the secondary (visible in the **Primary
Disk/Region/Zone** and **Secondary Disk/Region/Zone** columns). Prerequisite for the swap: the primary
disk is **Unattached**, or the instance it is attached to is **Stopped**.

3. To resume protection, click **Activate** in the **Actions** column and then **OK**. When the status
   returns to **Normal**, all data is back on the repaired disk.

**Optional**: to restore the original primary/secondary assignment, run **Perform Failover** and then
**Perform Reverse Replication** again against the secondary disk's region, then **Activate**, and
re-read the two columns to confirm which disk is now primary.

Source: `https://help.aliyun.com/zh/ecs/user-guide/implement-disaster-recovery.md`.

## 5. Stop and delete a replication pair ("turn DR off")

Use this when a customer asks to stop or remove disk DR. Deleting releases the replication relation
only: **both disks and all their data are retained**.

**Risk notice**

- If replication is in progress when the pair is deleted, the secondary disk reverts to its last
  completed replication state and the in-flight data of that replication round is lost. Stop the pair
  first, and only delete after the customer accepts that the secondary copy stops being protected.
- After protection stops, the disk has no DR coverage: say so explicitly before guiding the deletion.
- A pair that belongs to a consistent group cannot be deleted until it has been removed from the
  group; group-level teardown is a group operation.
- Deleting the pair does not delete snapshots, automatic snapshot policies or the disks themselves,
  and those keep being billed separately. Snapshot cleanup belongs to the snapshot management domain
  (`references/disk-replication-dr-guide__handoff-map.md`).

**Steps**

1. EBS console > **Enterprise-level Features** > **Asynchronous Block Storage Replication**; select
   the region and resource group in the upper-left corner.
2. If the pair is not already **Stopped**, find it and click **Stop** in the **Actions** column.
3. Find the pair again, choose the more-actions icon > **Delete** in the **Actions** column, and
   confirm.

**Expected result**: the pair no longer appears in the list for that region; the secondary disk
becomes writable and can be attached to an instance.

**Verification**: customer confirms absence on the page (re-read it for the region the pair belonged
to), then `python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id <region> --disk-id <disk-id>` to confirm
the disk still exists with the expected category and size. Note that the pair itself is not visible
to this skill's read-only queries, so the console page is the authority for this check.

Source: `https://help.aliyun.com/zh/ecs/user-guide/delete-a-replication-pair.md`.

## 6. Zone-redundant (regional) ESSD instead of a replication pair

Offered as a comparison, not as a substitution this skill decides on.

- **What it is**: one disk whose data is replicated **synchronously across multiple zones of the same
  region**; the platform handles replication, with **RPO 0** for zone failures.
- **Recovery model**: if a zone fails or the instance cannot run, start or attach compute in another
  zone of the same region and attach the disk; regional ESSD additionally supports **force attach**
  (attach to another instance in the same region without detaching first -- available only for this
  category). Warn the customer that after a force attach, data still sitting in the previous
  instance's memory cache is lost and further I/O from that instance fails.
- **Limits that decide the question**: data disks only (never a system disk), supported in the
  regions listed on the official page, higher average write latency than a PL1 ESSD, no performance
  provisions or burst performance, and **it cannot be combined with async replication** (cross-zone
  N/A, cross-region not supported). So regional ESSD answers zone-level failures, not regional ones.
- **Cost model**: billed by disk capacity, pay-as-you-go or subscription. Point at the pricing page;
  quote no numbers.
- Console: ECS console > **Block Storage** > **Disks**, or the **Storage** section of the instance
  buy page (**Custom Launch** tab) -- set the data disk category to **Regional ESSD**, then attach and
  initialize the disk before use.

Source: `https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md`.

## 7. Choosing between the four paths (answer shape for group A)

| Need | Path | Section |
|---|---|---|
| Survive a zone failure with no data loss, single disk, no second copy to manage | Regional (zone-redundant) ESSD data disk | 6 |
| Protect one disk across zones or regions, controlled failover | Replication pair | 1 |
| Recover several related disks to one point in time | Replication pair-consistent group | 2 |
| Survive a region failure of the whole service | Cross-region replication pair or group, plus compute in the destination region (application layer decides how traffic moves) | 1 or 2 |
| "A standby server within 10 minutes" | Not disk DR: instance cloning, custom images, load balancing plus auto scaling -- explain the difference and hand off | `references/disk-replication-dr-guide__handoff-map.md` |
| Off-site copy of snapshots only | Snapshot cross-region copy is a manual customer operation; ownership is the snapshot domain | `references/disk-replication-dr-guide__handoff-map.md` |
