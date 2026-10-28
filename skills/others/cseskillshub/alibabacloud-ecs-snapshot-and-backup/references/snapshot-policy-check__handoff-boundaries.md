# Boundaries: what this skill hands off, and the words to use (capability C6)

Entry point: `python3 scripts/snapshot_policy_check.py handoff <customer wording>`.

In a large share of snapshot tickets the snapshot is only the first act of a
different problem. Recognising the axis change is the useful move; diagnosing across
the boundary is not this skill's job.

## Handoff table

| Main complaint, in customer words | Owner | What this skill still does |
|---|---|---|
| "partition and file system did not grow after the resize" | `alibabacloud-ecs-disk-expand-diagnosis` | create and verify the prerequisite snapshot, then stop |
| "instance stuck starting / GRUB failure / will not boot" | `alibabacloud-ecs-instance-state-diagnosis` | offer the backup; do not diagnose boot |
| "disk IO is far below the specification" | `alibabacloud-ecs-disk-io-diagnosis` | note write load as background for slow creation only |
| "roll the disk back to that snapshot" / "rollback made it worse" | customer, in the console (irreversible) | pre-change backup, documented steps, and the honest note that a snapshot can carry the broken state with it (evidence: ticket 0002HRW3LX) |
| "delete these snapshots / free capacity" | `alibabacloud-ebs-disk-snapshot-management` | produce the inventory and the billing consequence; never delete |
| "why is my snapshot bill this amount / buy a storage package / refund" | Billing and Cost Center | evidence list: which snapshots, which disks, which region, which retention |
| "Security Center cannot fix the vulnerability, the script was blocked" | Security Center support | cross-product; route with the invocation evidence |
| "whole-instance backup plan failed / its billing" | Cloud Backup (HBR) | facts about the snapshot side only |
| "account has an anomaly / overdue / real-name change" | account appeal, Billing and Cost Center | identify and route; never act on commercial steps |

## Ready messages

Replace the bracketed placeholders; keep the structure.

**Resize or expansion**

> I checked the snapshot side of this. Disk [d-xxx] in [region] now has a completed
> snapshot [s-xxx], created [time], so you have a restore point. The partition and
> file system extension is a separate check, handled by the disk expansion
> diagnostics; ask for that once the snapshot is confirmed, because an unfinished
> snapshot is what blocked this customer's expansion (ticket 000ACRF8K2). I do not
> perform the extension here.

**Rollback**

> Rollback overwrites the disk and cannot be undone, so it is something you run in
> the console yourself, not something I trigger for you. Before you do it: create the
> newest snapshot of that disk and wait until its status is accomplished. Note that
> if the disk was already broken when the older snapshot was taken, rolling back
> restores the broken state too (ticket 0002HRW3LX). The documented steps are in
> `references/help-documents.md`.

**Billing**

> Here is what is generating snapshot storage in [region]: [list from
> lifecycle-inventory], each with its retention and expiry. Automatic policies are
> free, snapshots are billed, and deleting a policy does not delete the snapshots it
> already produced (tickets 000AWRLY1J, 000G2RJ8LG). The order that actually stops the
> charge is in `references/snapshot-billing-facts.md`. Purchases, refunds and package
> offsets go through the Billing and Cost Center; I cannot do those in your account.

**Export to local disk**

> Snapshots cannot be downloaded directly, and the export API sits behind a whitelist
> that is not opened on request, so `InvalidUser.NotInWhiteList` is final, not a form
> to submit (ticket 000CARSFMA). The supported route is snapshot, then custom image,
> then export the image to OSS, then download from OSS. Two conditions decide whether
> that path exists for you: the snapshot must belong to a system disk, and the image
> must be a non-encrypted Linux image. If you only need files, mounting a temporary
> disk created from the snapshot is usually cheaper than the image route.

**Copy anxiety**

> The copy is billed twice - traffic plus storage in the destination region - and each
> snapshot copies separately, so an automatic policy creating two a day produces two
> copies a day (ticket 0001ZS3DD6). I cannot give you a completion time; duration
> depends on shared cross-region capacity and queue depth. What I can do is re-read
> the inventory in the destination region and tell you whether the copy exists yet.

**Peak-hour slowness**

> Your snapshot is queueing, not stuck: the percentage is unchanged between samples and
> the region is at capacity. Nobody can raise that throughput, including the service
> side (ticket 000ACRF8K2). Deleting and recreating does not overtake the queue and
> destroys a completed snapshot if you pick the wrong one. If you need a support
> ticket, quote snapshot id [s-xxx], instance id [i-xxx] and creation time [time].

## Tone rules

Never promise to operate on the customer's behalf, to speed up a queue, or to
"apply for" a closed whitelist. The ticket record is explicit that agents themselves
said they could not act for the customer (tickets 000F4RWWW8, 00021RX22D), and a
skill that implies otherwise sets up the next ticket.
