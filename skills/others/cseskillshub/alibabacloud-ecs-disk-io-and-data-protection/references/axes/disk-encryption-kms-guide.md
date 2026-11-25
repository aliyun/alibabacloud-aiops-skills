---
name: alibabacloud-ecs-disk-encryption-kms-guide
description: |
  Read-only guide to Alibaba Cloud ECS disk encryption and KMS keys: audits whether a system disk, data disk, snapshot or image is encrypted, which key is referenced, and why encryption is only set when a disk is provisioned.
  Use when the customer asks about disk or snapshot encryption state, key type, or an encryption order failure.
  Triggers: is my cloud disk encrypted | encrypt a disk with a KMS key | cannot enable encryption on an existing system disk | Encryption at Rest missing in the console | snapshot is not encrypted | order fails when the encryption option is ticked | NoPermission or ImplicitDeny when a KMS key is chosen | service key versus customer managed key
  Do NOT use for ransomware recovery, snapshot rollback, disk-full expansion, SSH key pair login, guest OS BitLocker or billing; route to the snapshot, disk capacity, remote access or cost skills.
---

# ECS Disk Encryption and KMS Key Guide

Confirm the encryption state of ECS disks, snapshots and images from read-only cloud
facts, explain the rules that govern them, and hand the customer console steps they
run themselves. This skill answers "is it encrypted and with which key" and "how do I
get an encrypted disk"; it never changes anything.

## Read-only boundary (absolute prohibition)

- This skill reads cloud facts **only** through the three read actions listed in
  [references/ram-policies.md](references/ram-policies.md). That list is the whitelist.
- **ABSOLUTE PROHIBITION**: never generate, print, or execute a mutating OpenAPI action,
  an SDK call, or a console mutation - not on the skill's own behalf, and not as a
  command line for the customer to paste. Anything outside the whitelist is refused.
- Mutating steps exist in this skill **only** as console guidance the customer performs
  themselves (provisioning an encrypted disk, taking a snapshot, copying a snapshot with
  encryption, swapping the operating system), and every such step is preceded by the
  mandatory risk block below.
- This skill **never runs commands inside a customer instance**. When a guest-side fact is
  required (volume encryption such as BitLocker or LUKS, filesystem layout, whether a new
  disk was initialised), say so explicitly and ask the customer to run the read-only
  command listed in [references/disk-encryption-kms-guide__query-recipes.md](references/disk-encryption-kms-guide__query-recipes.md) and paste
  the output back, or hand the case off per
  [references/disk-encryption-kms-guide__handoff-matrix.md](references/disk-encryption-kms-guide__handoff-matrix.md).
- Commercial or offline actions (written compliance attestations, order and overdue-bill
  lookups, compensation) are answered with the process and the document checklist only,
  never submitted on the customer's behalf.

## Prerequisites

- The customer's own `aliyun` CLI, already configured with the default credential chain.
  The skill does not collect, read, print or store any credential and never asks for an
  access key pair.
- `python3` with the standard library only - see [scripts/requirements.txt](scripts/requirements.txt).
- Confirm which account and region is being inspected before quoting any result:
  `python3 scripts/axes/disk_encryption_kms_guide/sts_token.py` (plugin-mode caller-identity read).

## How to run (execution principle)

Run the single entry point and read its evidence table. Do not hand-assemble cloud CLI
queries for your own fact gathering; the commands in
[references/disk-encryption-kms-guide__query-recipes.md](references/disk-encryption-kms-guide__query-recipes.md) are the audit trail of what the
script issues and the self-check recipes the customer can run with their own credentials.

```bash
# One instance and everything mounted on it
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id cn-hangzhou --instance-id i-2ze8xxxxxxxxxxxxxxx

# One disk plus the snapshots that came from it
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id cn-beijing --disk-id d-2zeeop9jdn4n6e2zjzx3 --include-snapshots

# Whole-region sweep, encrypted disks only, machine-readable
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id cn-beijing --all-disks --encrypted-only --format json

# Read a snapshot to see which source disk and encryption property it came from
python3 scripts/axes/disk_encryption_kms_guide/ecs_encryption_audit.py --region-id cn-hangzhou --snapshot-id s-2ze0xxxxxxxxxxxxxx
```

Scope is deliberately narrow: `--region-id` is always required, and at least one of
`--instance-id`, `--disk-id`, `--snapshot-id` or `--all-disks` selects the objects to read.
One run covers one account in one region; for several regions, run it once per region.

## Decision tree

1. **Disambiguate the word "key" first** - it is the single largest cause of misrouted
   cases. Four different things get called "key":
   - KMS encryption key for a disk -> **this skill**;
   - SSH key pair used to log in -> remote-access skill (login credential, not encryption);
   - BitLocker recovery key shown by Windows -> guest-OS volume encryption, not Alibaba
     Cloud disk encryption -> hand off (see [references/disk-encryption-kms-guide__encryption-basics.md](references/disk-encryption-kms-guide__encryption-basics.md));
   - the login password -> remote-access skill.
2. **Confirm the product line.** A resource id that is not `i-` / `d-` / `s-` shaped is not
   an ECS object (for example a simple application server), and the ECS reads in this skill
   cannot see it. Report the boundary and hand off; do not infer an encryption answer from
   another product line.
3. **Route the ask**: state of a disk or its key -> `E1`; wants encryption on something that
   already exists -> `E2`; snapshot or image encryption -> `E3`; an order or permission
   failure while selecting encryption -> `E4`; anything else -> `E5`.
4. **Close every branch with re-verification**: after the customer performs the guided step,
   re-read with the same entry script and show the before/after evidence.

## Capabilities

- **E1 Encryption state and key type (read-only).** Collect `RegionId` plus an instance or
  disk id, read instances, disks and (on request) snapshots, and output a per-object
  evidence table of the encryption fields actually returned. If a disk reads as encrypted
  but no key identifier is exposed, the answer degrades to "encrypted, key type
  unconfirmed" plus the console check to confirm whether it is the service key or a
  customer-managed KMS key - never a coin-flip between the two.
- **E2 Enabling encryption (customer performs it).** State the constraint plainly:
  encryption is declared as a disk is provisioned, and an existing disk or existing system
  disk cannot have it switched on in place. Then give the two real paths - provision a new
  encrypted disk and copy the data over, or rebuild the system disk through an encrypted
  image or an operating-system swap - each with entry point, object, expected result and
  fallback, behind the mandatory risk block.
- **E3 Snapshot and image chain.** Explain inheritance: a snapshot inherits the encryption
  property of its source disk, so an unencrypted disk yields an unencrypted snapshot; an
  encrypted snapshot can be obtained by copying the snapshot with encryption selected.
  Then guide the customer-side steps and re-verify with `DescribeSnapshots` / `DescribeDisks`.
- **E4 Order or permission failure when encryption is ticked.** Ask the customer to paste
  the error text and a console screenshot, read the object facts that are readable, then
  walk the permission checklist in [references/disk-encryption-kms-guide__encryption-permissions.md](references/disk-encryption-kms-guide__encryption-permissions.md)
  (service key versus a customer-managed key that must already exist and be usable).
  Fallback proven in tickets: provision without encryption first, then migrate per `E2`.
- **E5 Identify and hand off.** BitLocker, ransomware recovery, snapshot rollback,
  disk-full and partition growth, key-pair or password login, operating-system swap,
  simple application server, billing. Identify the symptom, state the boundary in one
  sentence including "this skill does not run commands inside your instance", and route.

## Mandatory risk block for guided customer steps

Emit this before any guided step that changes something, and do not summarise it away:

1. **Backup first**: take a snapshot of every disk involved and wait until it is usable,
   at the newest possible point in time.
2. **Irreversibility**: an operating-system swap re-initialises the system disk; the data
   on it is gone and cannot be recovered afterwards.
3. **Cost and expiry**: snapshots are post-paid, and an overdue account has its snapshots
   automatically removed after 15 days, with no removal record to recover them from.
4. **Who performs it**: the customer clicks and confirms in the console; the skill neither
   performs nor submits the step.
5. Ask the customer to confirm they have the backup before continuing.

## Evidence and honesty rules

- Quote only field values the script actually returned; name the action and the parameters
  used so the read can be replayed.
- If a query fails, report the failure reason as returned (wrong region, missing
  permission such as `NoPermission` or `ImplicitDeny`, empty result) and give the customer
  self-check path. Never fill a gap with a guess.
- Do not assert error codes. Handle an order failure by comparing the customer's pasted
  error text with the referenced help documentation, and say which step you could not
  verify.
- Mark anything the cloud API cannot see as "customer-paste required": guest volume
  encryption, filesystem state, whether a new disk was initialised, KMS authorisation
  inside the account, order and billing records, and other product lines.
- Doc links and their confidence level are listed per topic in
  [references/disk-encryption-kms-guide__encryption-basics.md](references/disk-encryption-kms-guide__encryption-basics.md),
  [references/disk-encryption-kms-guide__encryption-permissions.md](references/disk-encryption-kms-guide__encryption-permissions.md) and
  [references/disk-encryption-kms-guide__snapshot-image-encryption.md](references/disk-encryption-kms-guide__snapshot-image-encryption.md).
  Items marked "not re-verified" must be re-checked before being quoted as authoritative.

## Output contract

Report the script's `Summary` and its final two lines as-is:

```text
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <single next step, customer-side unless the case must be handed off>
```

`DEGRADED` means some facts were readable and some are waiting on a customer paste-back or
a console check - name both halves. `FAIL` means no usable read; give the reason and the
self-check path.

## Observability

Each run mints one session-id - a 32-character lowercase hex string generated once
with `uuid.uuid4().hex` and shared by every cloud call - and every call carries it
as the User-Agent. The UA template is:

```text
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

where `{skill}` is this skill's name, so each call sends:

```text
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disk-encryption-kms-guide/<32-hex session-id>
```

The session-id is echoed in the report header so a customer can tie a console request log
to the same run. All calls use list-form arguments, a per-call timeout, no shell, and all
stderr and error text is masked before it is printed or returned, so credential material
never reaches the transcript.

## Handoffs

See [references/disk-encryption-kms-guide__handoff-matrix.md](references/disk-encryption-kms-guide__handoff-matrix.md) for the symptom-to-owner
table and the three canned handoff scripts (ransomware data, in-instance repair, overdue
billing). Neighbour-skill names there are provisional and need alignment with the batch's
final tier list.

## References

| File | Content |
|---|---|
| [references/ram-policies.md](references/ram-policies.md) | The three read actions this skill declares, minimal policy, auth-failure reply |
| [references/disk-encryption-kms-guide__encryption-basics.md](references/disk-encryption-kms-guide__encryption-basics.md) | What disk encryption covers, provisioning-time constraint, service key versus KMS key, the four "keys" |
| [references/disk-encryption-kms-guide__encryption-permissions.md](references/disk-encryption-kms-guide__encryption-permissions.md) | Order and permission failure checklist for the encryption option |
| [references/disk-encryption-kms-guide__snapshot-image-encryption.md](references/disk-encryption-kms-guide__snapshot-image-encryption.md) | Inheritance rules, encrypted snapshot via copy, encrypted custom image, export limits |
| [references/disk-encryption-kms-guide__query-recipes.md](references/disk-encryption-kms-guide__query-recipes.md) | Read-only query recipes, console check paths, customer paste-back commands |
| [references/disk-encryption-kms-guide__handoff-matrix.md](references/disk-encryption-kms-guide__handoff-matrix.md) | Boundary and handoff table with customer-facing wording |
