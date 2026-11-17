# Unblock Runbook

What to do when an unsubscription or a billing-method conversion is refused
because of the instance's image. Diagnose with the entry script, then walk the
fixed chain with the customer. Every step of the chain is a manual console action
performed by the customer; this skill only diagnoses and prints.

## Step 1 - get the evidence

```
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py unblock-check --region <RegionId> --instance-id <InstanceId>
```

Add the refusal text the customer quoted:

- `--message "<quoted text>"` when the quote is in English;
- `--message-branch <KEY>` when it is in another language. Do not machine-translate
  a console message into `--message`; pick the branch whose meaning matches.

The script reports the instance state, its billing method, the image it runs,
the image source (public, custom, shared or marketplace), the image status and
the snapshot IDs behind it, then states whether the image association is the
blocker.

## Step 2 - match the refusal text

| Console refusal (English rendering) | Branch key | Meaning | Route |
| --- | --- | --- | --- |
| "please replace with a public image" | `REPLACE_PUBLIC_IMAGE_FIRST` | Unsubscription requires a free public image; a custom, shared or marketplace image must be replaced first | the chain below |
| "the image of this instance is a marketplace image, conversion is not supported" | `MARKETPLACE_CONVERSION_BLOCKED` | Subscription-to-pay-as-you-go conversion is blocked by product policy while a marketplace image is attached | the chain below |
| "the instance is associated with a paid image, automatic unsubscription is not supported, contact human service" | `PAID_IMAGE_HUMAN_REQUIRED` | Automatic unsubscription is unavailable; the chain below may still be required, and human support stays involved | the chain below, then human support |
| "the disk has been released, cannot roll back" | `SNAPSHOT_SOURCE_DISK_RELEASED` | The snapshot's source disk no longer exists, so rollback is impossible; the snapshot can still create disks or images | hand off to `alibabacloud-ecs-disaster-recovery-image` for the recovery question, answer the billing question here |
| "the instance has no system disk, the system disk cannot be replaced" | `NO_SYSTEM_DISK` | The operating system cannot be replaced from the console because there is no system disk | hand off to `area:instance-state-diagnosis` |

An unmatched quote is reported as unmatched. Do not pretend it matched: print the
chain as the most likely path, tell the customer that the exact wording was not
recognised, and ask them to quote it verbatim to human support if the chain does
not fit.

## Step 3 - clarify what is being converted

Two different console operations are routinely confused:

- converting the INSTANCE billing method (subscription to pay-as-you-go) - this
  is the one an image can block;
- converting the BANDWIDTH billing method (pay-by-bandwidth to pay-by-traffic) -
  an image does not block this.

Ask which one the customer means before printing the chain. Also check the
billing method the script reported: a pay-as-you-go instance is released, not
unsubscribed, and releasing it does not delete its custom images or snapshots.

## Step 4 - the fixed chain

Print these steps in this order. Do not reorder them and do not skip the backup.

1. BACKUP FIRST, before anything else. Create a snapshot of the system disk, and
   of any data disk whose content matters. The customer can do it in the console,
   or this skill can do it through the gated `snapshot-backup` mode after the
   customer approved that specific snapshot. Guide:
   https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot
2. Replace the operating system with a free public image (manual, console):
   Instances, open the target instance, then the disk and image actions, then
   replace operating system, and choose a free public image. HIGH RISK: replacing
   the operating system WIPES the system disk. Data disks are not touched. The
   backup from step 1 must already exist.
3. Retry the blocked operation (manual): start the unsubscription again, or run
   the subscription-to-pay-as-you-go conversion again.
4. Handle attached resources separately (manual): an elastic public IP or a
   bandwidth plan bound to the instance is unsubscribed or changed on its own
   console page. Instance unsubscription does not cover them, and customers are
   regularly surprised by a leftover public IP charge.
5. If the console still asks for human service, submit the case to human support.
   Refund amounts, vouchers and compensation are commercial decisions; this skill
   never promises an outcome and never submits on the customer's behalf.

No official document URL for the replace-operating-system page and for the
unsubscription rules is bundled in this package. Describe the console path and
let the customer confirm the exact labels in their console version rather than
inventing a link.

## Step 5 - what to say about cost and risk

- Replacing the operating system with a free public image does not itself create
  an image charge; a public image carries no image fee. See
  [billing-facts.md](image-billing-cleanup__billing-facts.md).
- The backup snapshot from step 1 is billable storage. Tell the customer it can
  be deleted later in the console, and that deleting it is irreversible.
- After the replacement, the previous custom or marketplace image and its
  snapshots are still in the account and still billed. Run
  `inventory` to list what can now be cleaned up, and follow
  [cleanup-checklist.md](image-billing-cleanup__cleanup-checklist.md).
- A marketplace image whose product was withdrawn from sale can make a
  configuration change or a renewal fail as well. The path is the same chain;
  if the customer objects that replacing the image is equivalent to buying a new
  server, that objection is a commercial conversation for human support.

## When to stop and hand off

| Situation | Action |
| --- | --- |
| The console demands human service, or the customer asks for a refund, a voucher or compensation | Human support; print the chain first so the case is actionable |
| The image is fine (a free public image) but the operation is still refused | Not an image problem: report the billing method, the instance state and any attached public IP, and hand the exact quote to human support |
| The instance has no system disk, or will not start | `area:instance-state-diagnosis` |
| The customer wants to restore, copy or share an image rather than unblock a charge | `alibabacloud-ecs-disaster-recovery-image` |

Handoff wording and boundaries: [handoff-map.md](image-billing-cleanup__handoff-map.md).
