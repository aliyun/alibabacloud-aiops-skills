# Snapshot dependencies, deletion blockers and cleanup preparation

Everything in this file ends as **manual guidance for a human operator**. The
skill never removes a snapshot, an image or a policy, never cancels a share,
never detaches or releases a disk, and never changes a file. That boundary is
deliberate: it matches how these cases are actually handled, where the removal
is always performed by the account holder in the console. The deliverable of
this skill is a checkable evidence list plus the correct order, not an
executable change.

## 1. Why a snapshot cannot be deleted

| Blocker | How this skill sees it | What the human must do first |
| --- | --- | --- |
| A custom image references the snapshot | The entry's `Usage` reports an image dependency, and the probe of `DescribeImages` filtered by that snapshot names the image id | Cancel any image share, then delete the custom image |
| The snapshot is shared with other accounts | Not provable from the fields this skill calls - state it as a possibility and point at the image share page | Cancel the share |
| A data disk was created from the snapshot | `Usage` reports a disk dependency; the disk listing may show a disk whose origin is that snapshot | Release/remove that disk, in the console, after confirming the data is not needed |
| The console delete control is inactive | Usually the image dependency above; the console shows the related-image information per entry | Resolve the dependency named in the report |
| The entry is still being created or is otherwise locked | Status returned by the enumeration | Wait, or hand off if the instance is in a transitional state |

### How the reverse map is built, and where it degrades

1. `DescribeSnapshots` per region gives entries with `SourceDiskId`,
   `SnapshotLinkId`, `Usage`, `SnapshotType`, `RetentionDays`,
   `CreationTime`, `SourceDiskSize`.
2. `DescribeImages` with the owner filter gives self-owned custom images, each
   carrying its disk device mappings and the source snapshot ids behind them.
   Joining those gives snapshot id to referencing image id without any extra
   call.
3. Where the join produced no name but `Usage` still says the entry is image
   bound, the script probes `DescribeImages` filtered by that snapshot id,
   capped per run. If even that fails, the row is rendered as
   `unconfirmed: use the Related Images column in the console` - an explicit
   evidence gap, never a guessed image id.

Because a custom image sits on top of snapshots, two facts follow and are
stated wherever relevant: creating an image adds snapshot entries the customer
did not create by hand, and removing an image *without* also removing its
linked snapshots leaves that capacity billing on.

## 2. Manual unblocking order (the human's checklist)

Relay this order verbatim; do not collapse it or reorder it:

1. If the image is shared, cancel the share first.
2. Delete the custom image(s) that reference the snapshot. Risk to state:
   afterwards a system-disk reset from that image is no longer possible, and
   skipping the linked-snapshot option while deleting the image keeps the
   snapshot charging.
3. Delete any data disk created from the snapshot (unmount inside the guest
   and release the disk are both operator actions this skill only describes).
4. Only then delete the source snapshot itself, in the console, region by
   region.
5. Before deleting anything, confirm no other resource depends on that
   snapshot; deletion is irreversible.

Region note that answers most "I deleted them but the charge is back" cases:
deleting in one region changes only that region's charges. The region list to
work through comes from the ECS overview page, which shows every region
holding snapshot capacity.

Anchors: delete a snapshot
<https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1> and
<https://help.aliyun.com/document_detail/128131.html>, delete a custom image
<https://help.aliyun.com/zh/ecs/user-guide/delete-a-custom-image>, create a
snapshot <https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot> and
<https://help.aliyun.com/document_detail/25455.html>, snapshot working
principles <https://help.aliyun.com/zh/ecs/user-guide/how-do-snapshots-work>
and <https://help.aliyun.com/document_detail/25392.html>.

## 3. The four "still charged after deleting" causes

Investigate in this order; the report says which one the evidence supports and
marks the ones it could not check.

| # | Cause | Check performed here | If it cannot be checked |
| --- | --- | --- | --- |
| 1 | Another region still holds snapshots | Repeat the enumeration per region; the sweep is explicit about which regions were covered | Name the covered regions and point at the ECS overview page for the rest |
| 2 | A policy or job keeps producing new entries | Entries with `SnapshotType` of `auto` in the sweep, plus the policy's existence, disk attachment and retention read on the console policy page | Say the generating source is unverified and ask the operator to check scheduled jobs, including any orchestration or crontab-driven creation |
| 3 | Charges settle late | Billing-period wording only: usage closes, then the line appears | Direct the operator to the bill detail page for the period, never a promise about a date |
| 4 | Nothing was actually deleted | Empty versus non-empty enumeration for the named region and account | Report the enumeration result as-is; account-ownership doubt goes to the handoff list |

Related facts that keep capacity alive without any snapshot being "in use":
releasing or stopping an instance does not delete its snapshots, a pay-as-you-go
data disk that was not set to release with the instance keeps existing and
keeps charging on its own, and a service-recovery notice after settled
arrears means the feature works again - it does not mean a snapshot exists.

Policy anchors: automatic snapshot policy
<https://help.aliyun.com/zh/ecs/user-guide/automatic-snapshot-policy>, create
one <https://help.aliyun.com/zh/ecs/user-guide/create-an-automatic-snapshot-policy-1>,
enable or disable
<https://help.aliyun.com/zh/ecs/user-guide/enable-or-disable-an-automatic-snapshot-policy>,
delete one <https://help.aliyun.com/zh/ecs/user-guide/delete-an-automatic-snapshot-policy>.
This skill reads none of those pages programmatically and changes none of
them: it only judges whether deleted capacity is going to grow back.

## 4. The snapshot-first rule, in its two meanings

Cleanup always means one of two things, and the rule reads differently:

* **Cleanup inside the disk** (removing files to shrink what later snapshots
  and the disk itself will occupy): back up that disk first. Run the entry
  script in `prepare-snapshot` mode, which creates exactly one snapshot of
  exactly one named disk after the customer approved the printed notice. Only
  after the backup is in the accomplished state should a human perform the
  file-level work; the file work itself is out of scope here
  (`area:disk-expand-diagnosis`).
* **Deleting snapshots themselves**: no backup is created - the object of the
  removal *is* the snapshot data, so "back up before deleting snapshots" would
  be circular. Instead deliver the delete and keep lists below plus an
  explicit human double-check, and repeat that removal cannot be undone.

Pure diagnosis needs neither.

## 5. Delete and keep list templates

Both lists are rendered by the report; the same content can optionally be
written to a file (section 6). Keep both lists, never only the delete one -
an operator who sees only candidates cannot tell what was deliberately kept.

```
KEEP list
  region | disk | entries kept | why kept
  <region> | <disk-id> | <n> | newest restore point / referenced by image <image-id> / retention not returned

DELETE candidate list  (candidate only - not permission to delete)
  region | snapshot-id | type | created | source disk | size at creation | blocker
  <region> | <snapshot-id> | auto|user | <CreationTime> | <SourceDiskId> | <SourceDiskSize> | none | image <image-id> | unconfirmed

MANUAL order
  1 cancel share -> 2 delete image -> 3 delete disk built from snapshot -> 4 delete snapshot, per region

RISK line to repeat back to the operator
  Snapshot removal is irreversible. Verify each row. Confirm no other resource
  depends on it. Deleting an image also removes the system-disk reset path
  built on it.
```

Fields the API did not return render as `not returned`. A size column is always
labelled with its lens; the sum of entry sizes is never presented as the billed
chain capacity.

## 6. Optional candidate file

* Path shape: `/tmp/snapshot-cleanup-candidates-<name>.json`.
* A fresh file only. If the path already exists the write is refused and the
  lists stay in the report body; no existing file is ever modified or replaced.
* Written only when the operator passed the confirmation flag for that exact
  path, after seeing the notice.
* Contents: the chain candidates, the image-blocked rows, the billing item
  label, the skill name and the session id, plus a standing warning that
  appearing on the list is not authorization to delete.
* Nothing outside that path is written by this skill.

## 7. What is never offered here

* Any runnable form of a removal, unmount, detach, release, rollback,
  reformat, repartition or file deletion - including "run this yourself"
  command lines. Manual steps are prose with console entry points.
* Back-office or bulk removal on the customer's behalf, and any wrapper that
  would script it.
* Judgements about whether the data is still needed: the skill lists evidence
  and blockers, the operator decides.
