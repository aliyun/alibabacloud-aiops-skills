# Disk encryption basics, key types, and the four meanings of "key"

Read-only knowledge for `alibabacloud-ecs-disk-encryption-kms-guide`. Every factual claim
here is either a cloud read, a console path, or a statement tied to a source below with its
confidence level. Anything without a source is marked `unverified` and must not be quoted as
authoritative.

## 1. What "encrypted disk" means on ECS

Server-side encryption protects a disk's data **at rest** in the storage layer. It is
transparent to the guest operating system: the customer sees an ordinary disk inside Windows
or Linux, and nothing about the guest filesystem, its layout, or any operating-system-level
encryption is revealed by the cloud-side encryption attribute. Session encryption for the
remote-control channel is a different feature and must never be conflated with disk
encryption (see the disambiguation note in section 4).

## 2. The constraint that drives every answer in this tier

**Encryption is declared while a disk is being provisioned. A disk that already exists -
including a system disk of a running instance - cannot have server-side encryption switched
on in place.** There is no read-only or customer-clickable "turn encryption on for this disk"
control on an existing disk.

- Confidence: **high** for the standard ECS disk path. This is the single most common
  expectation gap in this tier: the customer asks for a button that does not exist.
- Consequence for the answer: state the constraint, name the two paths in section 3, and
  never imply that a partial step will make an existing disk encrypted.
- Source topic (needs a fetch to re-verify before quoting as authoritative):
  `https://help.aliyun.com/zh/ecs/user-guide/encryption-overview.md` and
  `https://help.aliyun.com/zh/ecs/user-guide/use-encrypted-cloud-disks.md`.

## 3. The two paths the customer performs

Both are console operations the customer runs. This skill guides and then re-reads; it does
not perform either. Show the mandatory risk block from `../SKILL.md` before these steps.

### Path A - new encrypted disk, data moved over (keeps the instance running)

| Step | Where | What the customer does | Expected result | If it fails |
|---|---|---|---|---|
| A1 | ECS console -> Storage & Snapshots -> Snapshots | Take a snapshot of the source disk and wait until it is usable | A snapshot in the list, at the newest point in time | A snapshot that is still in progress is not a backup; do not continue |
| A2 | ECS console -> Storage & Snapshots -> Disks | Provision a new disk in the **same zone** as the target instance, with the encryption option selected and the key chosen deliberately (section 5) | The new disk appears, encrypted, unmounted | If the order fails with the encryption option ticked, go to `encryption-permissions.md`; the proven fallback is to finish the order unencrypted and then use Path A again later |
| A3 | ECS console -> the instance's disk list | Mount the new disk on the instance | The disk shows as in use | A zone mismatch makes the target instance unselectable |
| A4 | Inside the guest (customer runs this) | Initialise the new volume in Windows Disk Management, or partition it and prepare a filesystem in Linux, then copy the data and **verify** the copy | The new volume is readable and the copied data checks out | A fresh disk is invisible until it is initialised - this is normal, not a fault; several customers pause here believing the disk was lost |
| A5 | This skill re-reads | Re-run `scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --instance-id <id> --include-snapshots` | The new disk reports encrypted | If no encryption field comes back, use the console check in `query-recipes.md`; do not guess |
| A6 | Customer decision | Keep the old disk until the application is confirmed healthy, then handle it separately | Nothing is lost before the copy is proven | Removing the old disk early is the one irreversible mistake in this path |

### Path B - rebuild the system disk on an encrypted image

Used when the requirement is about the **system** disk, which cannot be swapped for another
one in place.

| Step | Where | What the customer does | Expected result | If it fails |
|---|---|---|---|---|
| B1 | ECS console -> the instance's system disk row | Take a snapshot of the current system disk | A restore point exists | No snapshot, no way back |
| B2 | ECS console -> Images | Build or select a custom image, with encryption selected (see `snapshot-image-encryption.md`) | An encrypted image is available | Exporting an image built from an encrypted disk is constrained - confidence **medium**, verify with the customer's console before stating it |
| B3 | ECS console -> the system disk row -> the operating-system swap entry | Perform the swap, ticking the encryption option | The system disk is rebuilt as an encrypted disk | **The swap re-initialises the system disk: everything on it is gone and cannot be recovered afterwards.** Business hours, not ad hoc |
| B4 | Guest | Restore the application and data from the B1 snapshot or from backups, then re-configure the service | Service back up on an encrypted system disk | The instance is unreachable while the swap runs; login and key-pair questions belong to the remote-access tier, not here |
| B5 | This skill re-reads | Re-run the audit against the instance id | System disk row reports encrypted | See A5 |

## 4. Four different things customers call "key"

This is the first branch of the decision tree. Choosing wrong is the main cause of a wasted
exchange in this tier.

| Customer wording | What it actually is | Owner |
|---|---|---|
| "encrypt my disk with a key", "KMS key", "which key is used" | A key-management encryption key | **this skill** |
| "my key pair no longer works", "ssh key", "I cannot log in" | A login credential | remote-access tier - hand off |
| "Windows asks for a 48-digit recovery key", "the drive is locked" | Guest-OS volume encryption (BitLocker and friends), a Microsoft-side mechanism bound to the customer's own Microsoft account, not to Alibaba Cloud KMS | guest-OS tier - hand off; the cloud cannot fetch that key |
| "I forgot the login password", "the login is locked" | A login credential; note this skill never performs that action | remote-access tier - hand off |

Handoff wording: *"That is a login credential / a Windows-side volume key, not an Alibaba
Cloud disk encryption key. This skill only reads disk encryption state, and it does not run
anything inside your instance."*

## 5. Service key versus a customer-managed key

| Question | Service key | Customer-managed KMS key |
|---|---|---|
| Who owns it | The block-storage service on the customer's behalf | The customer, in the KMS console |
| What the customer must do first | Tick the encryption option, no key choice needed | A usable key must already exist in the region, and the identity placing the order must be allowed to use it |
| Typical failure | rare | The order fails or the key cannot be picked - `encryption-permissions.md` |
| Rotation, removal, policy | Not customer-managed | Customer-managed, in KMS - outside this skill's reads |

When the read shows a key reference, name it as returned. When the read shows the disk is
encrypted but exposes no key reference, say **"encrypted, key type not confirmed by the
cloud read"** and give the console check. Never pick one of the two because it is the more
likely answer.

## 6. What the cloud read can never tell you

- Whether the guest has its own volume encryption on top, and whether a fresh disk was
  initialised - ask the customer to run the read-only commands in `query-recipes.md` and
  paste the output.
- Anything about the key object itself: its policy, its state, whether it is enabled.
- Order, invoice and balance state.
- Resources of another product line, for example a simple application server, whose disk
  encryption question cannot be answered by these ECS reads at all - hand off, and say so
  plainly instead of transferring into silence.

## 7. Sources

| Topic | Where | Status |
|---|---|---|
| Encryption overview, service key versus KMS key | `https://help.aliyun.com/zh/ecs/user-guide/encryption-overview.md` | from this tier's search hits; not re-fetched |
| Working with encrypted disks | `https://help.aliyun.com/zh/ecs/user-guide/use-encrypted-cloud-disks.md` | from this tier's search hits; not re-fetched |
| Encryption-related permissions | `https://help.aliyun.com/zh/ecs/user-guide/encryption-related-permissions.md` | from this tier's search hits; not re-fetched |
| Encrypted custom images | `https://help.aliyun.com/zh/ecs/user-guide/encrypt-custom-images-1.md` | from this tier's search hits; not re-fetched |
| Session encryption (**not** disk encryption) | `https://help.aliyun.com/zh/ecs/user-guide/turn-on-session-encryption-for-session-management.md` | from this tier's search hits; cited for disambiguation only |
| Snapshot and image encryption chain | see `snapshot-image-encryption.md` | mixed confidence, marked per claim |
| BitLocker recovery key retrieval | Microsoft-side guidance, no URL carried here | **needs a human to supply the link**; never invent one |
