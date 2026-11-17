# Customer Self-Check List (backup-asset inventory, four-element guidance)

The skill has **no verified read-only API** for snapshot / image / backup
history in this tier, so the inventory is collected by the customer in the
console and pasted back (text or screenshots). Every item below is written
with the four elements that make it followable by a non-technical customer:
**entry -> object -> expected result -> fallback**.

Run `python3 scripts/areas/data_recovery_assessment/ecs_data_recovery_assessment.py --self-check` to print
this list for delivery; relay its items one at a time and wait for answers.

## Item 1 -- Manual snapshots

- **Entry**: ECS console -> Storage & Snapshots -> Snapshots. **Switch to the
  region of the lost disk first** (the region selector is at the top of the
  console; a wrong region shows an empty list, not an absent backup).
- **Object**: the snapshot list, filtered by the disk id of the lost volume.
- **Expected result**: one or more snapshots created BEFORE the loss moment;
  record for each whether its source disk was the SYSTEM disk or a DATA disk
  (the list shows the source disk id; system-disk snapshots are bound to the
  instance's system disk, data-disk snapshots to an attached data disk).
- **Fallback**: empty list -> re-check the region, then record the confirmed
  negative "no manual snapshot" in the assessment inputs.

## Item 2 -- Automatic snapshot policies

- **Entry**: ECS console -> Storage & Snapshots -> Auto Snapshot Policy.
- **Object**: the policy list and the disks each policy is bound to.
- **Expected result**: either a bound policy with snapshots it produced
  (those appear under Item 1), or confirmation that no policy was ever
  attached.
- **Fallback**: none found -> confirmed negative "no auto snapshots".

## Item 3 -- Custom images

- **Entry**: ECS console -> Images -> Custom Images.
- **Object**: images in the region of the instance.
- **Expected result**: an image created before the loss. Only a custom image
  can rebuild a full system environment; a data-disk snapshot cannot be
  converted into one (a judgement repeatedly confirmed in support practice).
- **Fallback**: none -> confirmed negative "no custom image".

## Item 4 -- ECS file backup (essential edition)

- **Entry**: ECS console -> Backup -> ECS File Backup (per-region backup
  history page).
- **Object**: the backup history of the affected instance.
- **Expected result**: records predating the loss with retained versions.
- **Fallback**: empty -> confirmed negative "no file backup". Product-side
  restore operations are routed to
  `alibabacloud-cloudbackup-ecs-file-backup-essential-edition`.

## Item 5 -- Cloud Backup, database dumps, binlog, local copies

- **Entry**: the customer's own environment: database server configuration
  (dump directories, binary-log retention), NAS / workstation copies, any
  third-party backup tool.
- **Object**: newest surviving dump or log file and its timestamp.
- **Expected result**: a logical backup whose dump time plus (if available)
  replayable logs reach the needed moment.
- **Fallback**: nothing kept -> confirmed negative "no logical backup, no
  binlog, no local copy".

## Item 6 -- Post-loss write activity (overwrite risk)

- **Entry**: customer judgement plus read-only guest checks the CUSTOMER
  runs themselves (for example `df -h`, `lsblk`, application logs).
- **Object**: whether the affected disk kept serving traffic after the loss.
- **Expected result**: ideally zero new writes since the incident.
- **Fallback**: writes continued -> mark overwrite risk as `possible` (or
  `confirmed` when heavy writes are certain), and take a safety-net snapshot
  of the CURRENT state before any recovery attempt; recovery-tool success
  odds drop from here on.

## Rules of engagement

- Ask one item at a time; keep the answers as the evidence record.
- Until every item is answered, the only permitted verdict is
  `INSUFFICIENT-EVIDENCE`. Do not soften it into encouragement, and do not
  harden it into `NOT-RECOVERABLE` without the explicit confirmation.
- If the customer cannot access the console at all (for example a sub-account
  without rights), recognise that as a RAM-permission topic: hand off to the
  account/RAM tier and note that the assessment pauses until someone with
  read access checks the inventory.
