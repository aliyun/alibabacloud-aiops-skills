# Out-of-scope signals and handoff discipline

This skill owns one symptom area: snapshot cost and capacity attribution,
deletability, and the preparation for a manual cleanup. Everything else that
appears in the same conversation is identified, evidenced and handed over -
never half-diagnosed here. Two rules apply to every row below:

1. Hand off WITH the evidence already collected (region, entries, blockers,
   account label, the exact refused error string), so the next owner does not
   repeat the sweep.
2. State the boundary in one sentence, then continue serving the part that IS
   in scope. A mixed conversation (commercial ask plus technical ask) is split,
   not abandoned: the technical facts stay, the commercial thread is routed.

## Signal-to-owner table

| Customer signal (their wording) | Owner | What this skill still does |
| --- | --- | --- |
| "Disk expansion did not take effect", `growpart` / `resize2fs`, Windows extend volume | `area:disk-expand-diagnosis` | none beyond noting the disk size lens |
| Instance stuck in `Stopping`, force stop or restart refused, snapshot writes locked by instance state (`IncorrectInstanceStatus`) | `area:instance-state-diagnosis` | reports the refusal verbatim and stops; never retries or reroutes the write |
| "Creating snapshots hurts my business IO", throughput or IOPS at the ceiling | `area:resource-bottleneck` | identifies the request as out of scope; no performance conclusion is given |
| Removing files, inodes, or otherwise shrinking used space inside the disk | `area:disk-expand-diagnosis` (human steps) | stops at the snapshot-first gate: one gated backup, then the file work stays manual |
| Rollback of a disk, restoring the system disk, building instances from a snapshot | `alibabacloud-ecs-disaster-recovery-snapshot` and the rollback guidance of `alibabacloud-ebs-disk-snapshot-management` | keeps listing which snapshots exist and what references them, because that feeds the billing story |
| Automatic snapshot policy create, enable, modify, delete; cross-region copy; archive or download of snapshots | `alibabacloud-ebs-disk-snapshot-management` | reads policy effects only as far as regrowth judgement needs (existence, attachment, retention as console facts) |
| "Deleting the image fails", image occupancy, image-side fees | image lifecycle and image billing tiers (`area:image-billing-cleanup`, `area:custom-image-lifecycle`) | names the image that blocks a snapshot and the snapshot capacity an image left behind; the image-side removal itself is theirs |
| Bill totals across products, arrears, stopping billing of other services, renewal pricing, coupons, refunds, cancellations | commercial and account billing paths (human staff) | proves only whether the observed line is the snapshot billing item; everything else it names and routes |
| Quota raise for per-disk snapshot counts, contractual capacity caps | quota console paths (human) | reports observed counts per disk chain only |
| Console shows nothing, "which account is this", message-recipient and credential recovery | account channel | renders the no-snapshot proof (identity label plus empty enumeration) and stops short of account-ownership judgements |
| Security groups, firewalls, malware, password or port hardening | the corresponding security tiers | no action; recognized and routed |

## Ready handoff sentences

Relay one of these verbatim (adjust only the bracketed evidence):

* Expansion: "This is the resize-not-applied family, owned by
  `area:disk-expand-diagnosis`. Snapshot-side evidence goes with
  you: [region, disk, chain rows, entry counts]. Nothing here was changed."
* Instance state: "The snapshot write was refused because the instance is in a
  transitional state (`IncorrectInstanceStatus`). This belongs to
  `area:instance-state-diagnosis`; this skill stops on any refused
  write and waits."
* IO or performance: "Snapshot load hurting business IO is a disk performance
  question (`area:resource-bottleneck`). We only confirm which disks
  and snapshots exist here."
* In-disk cleanup: "Shrinking used space inside the disk is capacity cleanup
  (`area:disk-expand-diagnosis`). This skill goes as far as the
  snapshot-first backup gate - one confirmed snapshot of the named disk - and
  the file-level work stays a manual operator action."
* Policy or copy or archive: "Policy creation, cross-region copy, archive and
  download are configured in `alibabacloud-ebs-disk-snapshot-management`. This
  skill only judged whether the policy would regrow the capacity you are about
  to delete."
* Image side: "The blocker is image [image-id]: cancel any share, then delete
  the image (optionally its linked snapshots), then the snapshot frees up. The
  image-side removal itself belongs to the image lifecycle tiers."
* Commercial: "Pricing, arrears waivers, coupons and cancellation are handled
  by commercial staff - the same path these cases always take. This skill
  outputs fee facts only: which billing item, which region, which entries."
* Account ownership: "Under the current credential (account label [label]) the
  enumerated regions hold no snapshots, so the billed line either lives in
  another region or belongs to another account. Ownership questions go to the
  account channel; this skill does not resolve them."

## What never leaves this skill as a conclusion

* A performance, security, migration or restoration verdict.
* A price, saving amount, forecast, or which package to buy.
* Any runnable form of a deletion, unmount, rollback or file removal.
* A claim about undocumented behavior (policy cross-region capability, archive
  snapshot classes, trial quotas): state the evidence gap instead, per
  [snapshot-billing-decision-tree.md](snapshot-billing-cleanup__snapshot-billing-decision-tree.md).
