# Encryption along the snapshot and image chain

The rules that decide whether a snapshot, a disk made from it, or a custom image comes out
encrypted. This is where the second-largest expectation gap in this tier sits: customers
expect an encryption option on a snapshot of an unencrypted disk.

## 1. Inheritance, the core rule

| Object | Encryption outcome | Confidence |
|---|---|---|
| Snapshot of an **encrypted** disk | Encrypted; it inherits the source disk's encryption property | **high** - and re-checkable with the read in section 4 |
| Snapshot of an **unencrypted** disk | Unencrypted. There is no way to tick encryption onto that snapshot directly | **high** for the rule as stated in this tier's evidence; the exact wording of the source topic is **not re-fetched**, so present the rule and then verify the customer's objects with a read |
| Disk made **from an encrypted snapshot** | Encrypted, following the snapshot | **high** |
| Disk made **from an unencrypted snapshot** | Unencrypted, unless the encryption option is selected while the disk is provisioned - and then the result depends on the key path in `encryption-permissions.md` | **medium**; show the console selection to the customer rather than asserting it |
| Custom image built from an encrypted snapshot | Follows the encrypted chain; encrypted custom images are a supported topic | **high** that the topic exists, see the URL below |
| Copy of an unencrypted snapshot with the encryption option selected | Encrypted copy - this is the normal way to turn "I need an encrypted copy" into reality | **high** as a route; the customer performs it |

**Say it this way to a customer who asks why the option is unavailable**:
*"A snapshot inherits the encryption property of the disk it was taken from. Your source disk
is not encrypted, so its snapshots cannot be encrypted either. What you can do is copy that
snapshot with the encryption option selected, which gives you an encrypted snapshot you can
then use - or provision a new encrypted disk and move the data. I can read back either result
to confirm it worked."*

## 2. Customer-side steps, with the risk block in front

| Step | Where | What the customer does | Expected result | If it fails |
|---|---|---|---|---|
| S1 | ECS console -> Storage & Snapshots -> Snapshots | Pick the source snapshot, open its detail, and note whether an encryption row is present | A fact, not a guess | No encryption row in the panel - use the read in section 4 and then the console check in `query-recipes.md` |
| S2 | Same list, the copy action | Copy the snapshot, selecting the encryption option and, if needed, a key that exists **in the destination region** | A new snapshot, encrypted, in the destination | Key not in the destination region - that is the same failure class as `encryption-permissions.md` step 1 and 3 |
| S3 | This skill re-reads | `--snapshot-id <new-id> --include-snapshots` on the copy | The copy reports encrypted | `DEGRADED`, name the field that came back empty |
| S4 | ECS console -> Images | Build a custom image from the encrypted snapshot when the goal is an encrypted system disk | An encrypted custom image | If the source snapshot is unencrypted, go back to S2 - an image cannot be more encrypted than its chain |
| S5 | Use the image where it is needed (same instance rebuild, another instance, another region) | Follow the image-copy topic below | The intended object now sits on an encrypted chain | Region or encryption-copy restrictions: verify in the console with the customer, confidence **medium** below |

## 3. Export and cross-region limits

- **Exporting an image whose chain is encrypted is restricted.** A customer stated this
  plainly in the ticket evidence behind this tier ("my disk is encrypted, so I cannot export
  the image"), and it is consistent with how the chain works - but the authoritative source
  topic for the export path was **not** found by this tier's document search, and the support
  conversation did not contain a formal answer on it.
  Handle it as: *"Encrypted image chains are not exported the same way as plain ones. I will
  confirm the exact limitation for your case rather than guess."* Confidence **medium**,
  always with a human verification step. Never state a specific reason or workaround for an
  export failure that has not been read.
- **Cross-region image copy** carries the encryption question with it: the destination region
  needs a key that exists there. Topic:
  `https://help.aliyun.com/zh/ecs/user-guide/copy-an-image.md`
  (from this tier's search hits, **not re-fetched**).
- **Encrypted custom images** topic, the authoritative entry for this sub-question:
  `https://help.aliyun.com/zh/ecs/user-guide/encrypt-custom-images-1.md`
  (from this tier's search hits, **not re-fetched**).

## 4. Verifying with the read

```bash
# Snapshots behind one disk
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --disk-id <disk-id> --include-snapshots

# One snapshot, seen together with the disks made from it
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --snapshot-id <snapshot-id>

# Whole-region sweep to find snapshots that are not encrypted
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id <region> --all-disks --include-snapshots
```

Read-back rules:

- Report `SnapshotId`, `SourceDiskId`, `SourceDiskType` and the encryption fields exactly as
  returned. Never state a snapshot's encryption by looking at its name or its age.
- An **empty** snapshot list is not "no snapshots exist"; it is "nothing visible to this
  profile in this region". Say which it is.
- The inheritance claim is only useful once both ends have been read: the source disk and the
  snapshot. Read both, then show them side by side.

## 5. Two limits customers blame on encryption

- **Overdue account.** Snapshots are post-paid, and an overdue account has its snapshots
  automatically removed after 15 days, with no removal record to recover them from. Encrypted
  snapshots are subject to the same rule as any other. When a customer reports "my snapshots
  are gone", read the facts, then hand the billing question off per `handoff-matrix.md`; this
  skill cannot read a balance. Billing topics to verify:
  `https://help.aliyun.com/document_detail/25455.html` and
  `https://help.aliyun.com/document_detail/56159.html` (quoted inside support conversations in
  this tier's evidence, **not re-fetched here**).
- **A snapshot is a point-in-time copy.** If ransomware encrypted the data before the newest
  snapshot, the snapshot holds the encrypted data too. Recovery questions belong to the
  snapshot and ransomware-protection tier - see `handoff-matrix.md` for the wording, including
  the fact that no cloud-side service can undo strong ransomware encryption.

## 6. Restoring data with the snapshot chain

A snapshot can be turned into a new disk that is then mounted on an instance to copy files out
(topic to verify: `https://help.aliyun.com/document_detail/32317.html`). The encryption angle
this skill owns: **the new disk's encryption follows that chain**, so a restore of an
encrypted source lands on an encrypted disk, and a restore of an unencrypted source does not -
which matters when the customer's real requirement is a compliance record. The mounting and
the file copy themselves are guest-side work the customer performs, or belongs to the
disk-capacity and remote-access tiers.
