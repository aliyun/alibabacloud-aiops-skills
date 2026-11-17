# Root Causes and Decision Knowledge -- ECS Custom Image Lifecycle

Knowledge distilled from real support tickets for this tier, rewritten in
customer-facing English. Every conclusion in a report must cite either a
field returned by `scripts/areas/custom_image_lifecycle/image_lifecycle_check.py` or a rule from this
file. Never invent values, never conclude from a failed query.

## Scenario S1 -- "cannot create a custom image" / creation failures

| Root cause | Recognizing signal (evidence) | Resolution guidance |
|---|---|---|
| Instance locked by expiry / overdue (stopped for that reason) | `precheck` mode: Status=Stopped plus non-empty OperationLocks (financial/security) or an ExpiredTime in the past; API rejects with `IncorrectInstanceStatus` | Renew / clear the lock first (renewal itself is a console commercial action, this skill never performs it). Ticket pattern "renew briefly -> create image -> then request refund" is a customer's own commercial decision; the image can only be made while the instance is unlocked |
| Account in arrears beyond the retention window | Snapshots gone, images gone; `report` shows empty snapshot/image inventory in every swept region | Mechanism: an image is a view over snapshots; arrears beyond the window (ticket wording: 15+ days) auto-releases pay-as-you-go snapshots and dependent images. Released data is NOT recoverable. State it plainly with the mechanism quote from the script findings |
| No snapshot/image history exists at all | `report` + `--all-regions`: zero records everywhere | "The platform does not auto-back-up your disks" (shared-responsibility note). Nothing can be rolled back; only in-guest recovery or the file-backup console path if the customer had enabled it |
| Wrong console entry / region view | Resources exist under `report --all-regions` in another region, or under another account | Give the console entry + region selector note; identity line from `GetCallerIdentity` proves which account view was checked |
| Quota exhausted | `QuotaExceeded.Snapshot` error text on a creation attempt | List current snapshots (`report` with `--instance-id` or region-wide); cleanup of old snapshots is a manual, human-approved action with risk notice (deleting them can invalidate images built on them) |
| Marketplace image at the origin | `report` item field owner alias = marketplace | Compatibility/repair is the image vendor's responsibility; hand off to the vendor, do not attempt in-skill fixes |

Cross-account sharing receive flow ("receiver cannot see the shared
image"): run `report --image-id <id> --image-owner-alias others` under the
RECEIVER credential, plus `DescribeImageSharePermission` evidence under the
SHARE owner. Most non-issues are (a) wrong region selector on the receiver
side, (b) share submitted for another region, (c) typo in the account id.
The console receive-side UX itself is outside this skill.

## Scenario S2 -- image / system-disk size limits

Hard rules (all ticket-confirmed):

1. `target system disk >= image system disk size` -- no exceptions. A 100 GB
   image can never land on a 60 GB system disk. `capacity` mode prints the
   exact delta in GB.
2. Cloud disks never shrink. To go smaller: a migration path (SMC or new
   purchase with a smaller disk). Uninstalling a system disk and inserting a
   smaller one leaves the instance WITHOUT a system disk -- block this idea
   when customers propose it.
3. Replace-OS with a custom image replaces the SYSTEM disk content only.
   Data disks are untouched and must be remounted inside the guest after
   the operation; old system-disk data is overwritten and unrecoverable --
   back it up first (snapshot before, human action).
4. Creating a NEW instance from an image DOES carry the data disks that
   were checked at image creation. The image list shows only the
   system-disk size until creation reaches completion; the image detail
   page then lists associated data disks -- this display rule resolves
   many "the image lost my data disk" complaints.
5. Cross-region restore needs the image (or its snapshots) copied to the
   target region FIRST; replace-OS cannot cross regions.

Typical customer phrasing: "the image is bigger than the new disk",
"40g minimum?", "I bought 60G but the image says 100G", "expansion and
initialization at the same time" (they cannot be combined in one step:
initialize/replace first, boot, then expand -- and expansion beyond the
partition belongs to the disk-expand area, see handoffs).

## Scenario S3 -- using a custom image to create instances fails / is restricted

| Root cause | Recognizing signal | Resolution guidance |
|---|---|---|
| Region does not sell the wanted instance type | No in-scope stock/offer API exists; the official region-based type page is the authority (see console-guides) | Honest DEGRADED: give the buy-page path + suggest copying the image to a region that sells the type (plan `--op copy-image`) |
| Image missing NVMe drivers, target uses NVMe system disks (some newer type families) | Instance created but hangs at boot; ticket-proven root cause class; cloud API does not see guest drivers | Pre-check list below; repair requires in-guest/offline work -> manual steps + the NVMe adaptation doc; if the image is Linux and the family supports it, switch boot mode/type per startup-mode doc guidance |
| Boot mode mismatch (BIOS vs UEFI) on imported images | Image stuck at boot screen on bare-metal/UEFI-only types | Ask the customer how the image was built (boot-mode question is the ticket-proven discriminator); fix by rebuilding the image with the matching boot mode or choosing a BIOS-compatible type; doc: instance startup mode |
| sshd forbids password login / root password unset inside the image | New instance: SSH reports `permission denied`, VNC also refuses | Cloud-side invisible by design; give the VNC login + sshd-config manual path (doc link in console-guides). The open-ended variant "even VNC is refused" is NOT solvable in this skill: collect evidence and escalate to a human ticket -- do not pretend a fix |
| Public/marketplace image selection rules | Windows 10 requested; Linux<->Windows replacement planned cross-family; Simple Application Server involved | Public images ship Windows Server only; Windows needs >=1 GiB RAM (2+ recommended); ECS images do not run on Simple Application Server; state the rule, stop there |
| Commercial constraints (campaign-priced instance cannot transfer account) | Instance transfer blocked by activity rules | Transfer/refund are commercial flows: image-based migration plan (create image -> copy -> share -> create/replace) is in scope; the transfer itself is not |

Compatibility pre-check list (print before creating instances or importing
from a customer-built image):

- [ ] NVMe: does the target type family require NVMe; is the driver
      installed in the image (Linux adapt doc).
- [ ] Boot mode: BIOS vs UEFI consistent between image and target types.
- [ ] cloud-init present/enabled so password/SSH key injection works.
- [ ] sshd allows the intended auth method; root not locked.
- [ ] Data disks selected at image creation if they must come along.
- [ ] SELinux/grub customizations that block first boot (manual review).

## Scenario S4 -- creation is slow / progress stuck at 0%

Evidence stack (the strongest automation value of this skill -- the console
hides these layers from the customer):

1. `report` image status: Creating / Available / Unavailable + progress
   field when the API returns one.
2. `report --instance-id` snapshots: Progressing vs accomplished, with the
   per-snapshot progress string -- image creation rides on this pipeline.
3. `report` tasks: in-progress task rows (task id / action / status /
   creation time).

Facts and phrasing rules for the answer:

- Duration depends on data volume, concurrent snapshot tasks in the region
  and regional peak load; NO SLA can be promised ("a few minutes" is not a
  guarantee). Never promise a completion time.
- An in-progress image is not fully visible/usable until done; the listing
  shows the system-disk size only (display rule from S2 #4).
- Same-source copy uniqueness: exactly ONE in-progress copy task per source
  image; the account-level concurrency (ticket wording: 5) counts DIFFERENT
  images. A second copy submitted early fails instantly and failed tasks
  may not appear in the console list at all. `plan --op copy-image`
  pre-checks this BEFORE submitting.
- "Stuck" that is actually a boot failure: if the image reached Available
  but the new instance hangs, this is S3 (drivers/boot mode), not S4.
  Route by the image status FIRST.
- Fresh-instance tip (operations field experience, present as a suggestion):
  create images from instances at least ~20 minutes old.
- Noise guard: "pull from ghcr.io returns 401" and "push to an image
  registry is slow" are CONTAINER image issues -- different product line,
  hand off; do not treat as ECS custom images.

## Error-string quick table (customer-visible)

| String / code | Where it appears | Meaning & first move |
|---|---|---|
| `IncorrectInstanceStatus` | console/OpenAPI on create-image or operations | Instance expired/locked or mid-transition -> `precheck` mode reads Status + OperationLocks |
| `QuotaExceeded.Snapshot` | create-image / create-snapshot | Snapshot quota reached -> inventory via `report`, manual cleanup guidance with dependency risk |
| `InvalidDiskId.NotFound` | disk-anchored flows | Wrong id or wrong region/account view -> re-check view, sweep regions |
| `permission denied` | SSH/VNC login on a new instance from a custom image | Guest sshd/credential config -> VNC manual path + doc; escalate if VNC also fails |
| `401 Unauthorized` (registry) | docker / ACR / ghcr pull-push | NOT an ECS custom image -- container product line handoff |
| "copy failed but no task visible" | console task list | Same-source uniqueness rule (S4); pre-check before resubmit |
| `NoPermission` / `ImplicitDeny` | any call | Missing RAM action -> name it + point to references/ram-policies.md minimal snippet; continue other legs |

## Anti-fabrication rules (apply to every report)

1. Only quote numbers/ids/statuses that appear in the script output.
2. An empty list means "not visible under THIS account+region view", not
   "never existed" -- until the view guards (identity + sweep) have run.
3. A failed query is a limitation line in the report, never a conclusion.
4. Mechanism statements come from this file or from `references/` docs;
   model memory is not an acceptable source.
5. Windows in-guest file-count conclusions carry the low-confidence note
   (NTFS has no direct inode meter).
