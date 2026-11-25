---
name: alibabacloud-ecs-boot-repair-guide
description: |
  Guides ECS boot-failure triage and manual repair when the instance operating system will not boot or cannot be entered; it uses query-only cloud calls and changes no resource.
  Use when the OS fails to start after a GRUB, EFI, fstab, filesystem, kernel or Windows update change.
  Triggers: instance won't boot; stuck at grub rescue; error: unknown filesystem; normal.mod not found; fstab mount point does not exist; entered emergency mode; won't boot after kernel upgrade; blue screen stop code INACCESSIBLE_BOOT_DEVICE; mount repair disk to fix boot; cannot enter system after reboot.
  Do NOT use for: patch scanning or installation (alibabacloud-ecs-patch-management); disk capacity, expansion or GPT/LVM; instance stuck in Starting; disk IO or CPU performance; SSH or RDP login while the OS is up; ransomware or DDoS cleanup; billing or refunds.
---

# Alibaba Cloud ECS boot repair guide (GRUB / EFI / fstab / filesystem / post-update / BSOD)

This skill answers one question: **why will the operating system on an ECS instance not come up,
and what is the next safe path — repair, or data rescue?** It classifies the failure into a root-cause
layer (boot loader, EFI boot entry, fstab/mount, filesystem state, kernel or patch update side effect,
Windows start-time crash, or "this is normal, keep waiting"), then emits an evidence-backed report with
**manually executed repair steps** and the two risk gates (snapshot backup, downtime window) that must be
settled before anyone touches the instance.

It is an advisory skill in the RO+G class: query-only cloud calls, plus manual guidance. It is
deliberately **not** declared as a strictly non-changing skill, because most of its value is guiding
changes such as mounting a repair disk, rebuilding a boot loader, or rolling back a snapshot. Those
operations are **always performed by the customer** in the console or inside the guest, never by this
skill. In this release no change-level API is invoked at all: the contracts for snapshot creation,
command dispatch, disk attach, and system-disk replacement were not verified for this tier, so those
capabilities stay as guidance only, and the cloud surface is limited to the query actions below.

## ABSOLUTE PROHIBITION

Never generate, print for execution, or invoke any cloud **change** API. Banned verb prefixes on any
action, in any output, in any order: `Create*`, `Modify*`, `Delete*`, `Release*`, `Reset*`, `Replace*`,
`Attach*`, `Detach*`, `Rebind*`, `Import*`, `Revoke*`, `Bind*`, `Unbind*`, `ReInit*`, `Reboot*`,
`Start*`, `Stop*`, `Put*`, `Authorize*`.

In particular this skill never:
- stops, restarts, force-restarts, or re-initializes an instance or disk;
- attaches, detaches, resizes, or replaces a system or data disk;
- creates, shares, deletes, or rolls back a snapshot or image;
- rebuilds a boot loader, edits `/etc/fstab`, repairs a Windows boot configuration, or disables a driver.

For each of those the skill outputs **the manual step list, its prerequisites, its blast radius, and
whether it is reversible**, and stops there. Never hand the customer a change command to paste and run
without the risk statement that accompanies it.

If the customer asks for any of the above, refuse the execution, explain why, and name the console or
OpenAPI entry point where they perform it themselves.

## Cloud API allowlist (hard)

Only these actions may be invoked, and only through `scripts/axes/boot_repair_guide/boot_repair_guide.py`. The agent MUST NOT
compose `aliyun` commands by hand or call any other action, even if it looks harmless:

| product | action | version | why |
|---|---|---|---|
| sts | `GetCallerIdentity` (CLI token `aliyun sts get-caller-identity`) | 2015-04-01 | verify the credential chain and derive the report provenance tag |
| ecs | `DescribeInstances` | 2014-05-26 | OS name/version, image id, instance type and family, zone, private IP, status |
| ecs | `DescribeInstanceStatus` | 2014-05-26 | Running / Stopped, which gates repair-disk work and proves whether a reboot took effect |
| ecs | `DescribeAvailableResource` | 2014-05-26 | stock check for the temporary pay-as-you-go instance in the data-rescue path |
| ecs | `DescribeInvocations` | 2014-05-26 | historical Cloud Assistant records: did the guest ever execute a command after the failure |
| ecs | `DescribeDisks` | 2014-05-26 | identify the system disk (id, category, size, status) so repair and rollback guidance targets the real volume |
| ecs | `DescribeSnapshots` | 2014-05-26 | check whether an accomplished rollback-point snapshot already exists on the system disk (read only; never creates or rolls back) |

Anything outside this table is refused at code level by `_cli.py`, not merely discouraged in prose.

### Permission and confirmation gates

1. **Query calls run automatically.** No per-call confirmation, but every report line records the action,
   the declared parameters, and the call time, so the customer can audit where each number came from.
2. **In-guest evidence is collected by the customer, not by this skill.** The current release does not
   dispatch commands into the instance. `scripts/axes/boot_repair_guide/boot_repair_guide.py evidence-plan` prints one
   non-mutating command at a time (what it does, that it changes nothing, what it returns); the customer
   runs it in VNC, SSH, or the mounted repair environment and pastes the output back.
   If the customer declines, report `STATUS: DEGRADED` and continue with cloud evidence only.
3. **Before any repair guidance** (boot-loader rebuild, fstab edit, repair-disk mount, snapshot rollback,
   OS replacement, chroot rescue): state that it is a change, what it can destroy, how to reverse it, and
   the downtime window required — then require an explicit customer confirmation. Guidance is withheld
   until the snapshot gate is settled (see workflow step 1); pure evidence gathering is never withheld.
4. **Snapshot first.** No repair, cleanup, disk-detach, or rollback guidance is issued until a usable
   snapshot is confirmed by the customer, or the customer explicitly accepts the data-loss risk in
   writing. A snapshot that is not 100% complete cannot be used as the rollback point, and a repair disk
   cannot be attached to a running instance.
5. **Never** request, echo, store, or infer a guest password, private key, or access credential. Only the
   last four digits of the account id appear in reports, as a provenance tag.
6. Authentication failures are reported with the exact missing action and the minimal policy snippet from
   `references/ram-policies.md`, and the literals `NoPermission` or `ImplicitDeny`. Do not invent other
   auth error names.

## Prerequisites

- Alibaba Cloud CLI installed and configured with the default credential chain
  (`aliyun configure`); never pass credentials on the command line or in files.
- RAM permissions listed in `references/ram-policies.md` (all enumerated, no wildcards).
- Python 3.8+ standard library only. See `scripts/requirements.txt`.

## Execution: run the entry script, nothing else

```
python3 scripts/axes/boot_repair_guide/sts_token.py
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py profile        --region-id <region> --instance-id <i-xxx> [--check-invocations]
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py classify       --region-id <region> --instance-id <i-xxx> --text "<screen or VNC text>"
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py preflight      --region-id <region> --instance-id <i-xxx> [--rescue-instance-id <i-yyy>] [--snapshot-progress <0-100>] [--downtime-approved] [--credential-ready]
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py rescue-stock   --region-id <region> [--zone-id <zone>] [--instance-type <type>] [--network-category vpc|classic]
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py evidence-plan  --branch <branch-id> [--os-family linux|windows]
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py fstab-compare  --fstab-file <path> --blkid-file <path>
python3 scripts/axes/boot_repair_guide/boot_repair_guide.py handoff        --text "<symptom text>"
```

Run `scripts/axes/boot_repair_guide/sts_token.py` first: it verifies the default credential chain and prints the provenance tag
that the report header carries. Add `--instance-id` more than once to triage a batch, and `--json` to any
subcommand for one machine-readable object instead of text. `classify` prints the gate verdict first, then
the ranked branches; an empty match set is reported as the `unknown` branch, never as a guessed root cause.
`evidence-plan --branch` accepts exactly `boot-files-lost`, `efi-boot-entry`, `filesystem-state`,
`fstab-mount`, `grub-loader`, `post-update-kernel`, and `windows-bsod`; `post-update-normal` and `unknown`
have no evidence plan by design, because waiting and missing evidence are not command lists.

## Workflow

```
Step 0  Gate: is this a boot failure at all?
        Running + VNC reaches a login prompt or desktop -> not this skill -> handoff (connection /
        security / IO). Patch or vulnerability action failed while the OS still boots -> patch skill.
        Disk full, inode full, expansion / GPT / LVM -> capacity or expansion skill. Instance parked in
        Starting / Stopping, or a downgrade that never finished booting -> instance-state skill.
        Confirm boot failure -> Step 1.
Step 1  Snapshot gate: `profile` and `preflight` query the system disk and its accomplished snapshots
        (`DescribeDisks` / `DescribeSnapshots`), so a rollback point is detected from the account rather
        than assumed; the customer confirms only what the query cannot see. No accomplished snapshot ->
        stop before any change guidance; explain the rollback point and the retention/billing consequence.
Step 2  Evidence: customer-supplied screen text, VNC screenshot transcription, console diagnosis verdict,
        plus the non-mutating in-guest commands the customer pastes back. Classify by evidence, never by
        the customer's own attribution.
Step 3  Branch: boot loader / EFI boot entry / fstab and mount / filesystem state / post-update side
        effect / Windows start-time crash / normal post-update duration that is not a fault at all.
Step 4  Exit: repairable -> manual step list with prerequisites, downtime, reversibility.
        Not repairable -> data rescue: roll back to an earlier snapshot, or build a disk from a snapshot,
        attach it to a temporary instance in the same zone, copy the data, then rebuild the instance.
```

Read `references/boot-repair-guide__boot-failure-decision-tree.md` before Step 2 and `references/boot-repair-guide__evidence-checklist.md` for
the minimum evidence set each branch requires.

## Anti-hallucination contract

- Every factual statement comes from a script result or from `references/`; never from model memory.
- Never state a root cause without the artifact that supports it. "Blue screen after an update" supports a
  category, not a specific driver; say so.
- Never claim the instance is broken in a specific way from a single cloud query: the boot loader, EFI
  partition, `/etc/fstab`, update history, and crash dumps are invisible to the cloud API and live inside
  the guest or the offline disk. Say which evidence is missing and how to obtain it.
- Empty or failed queries are logged as limitations, not filled with plausible values.
- Downtime and post-update waiting figures are quoted as customer-observed ranges, never as guarantees.

## Output contract

Every run ends with the machine-readable tail:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step, and who performs it>
```

`OK` = cloud evidence plus customer-supplied artifacts support a branch. `DEGRADED` = a required evidence
channel was unavailable (CLI missing, `NoPermission`, customer declined to paste output) and the report is
partial. `FAIL` = no usable evidence; report the gap, do not classify. The agent MUST relay `Summary`,
`STATUS`, and `NEXT_ACTION` as produced, and MUST NOT add resources, error codes, or documentation links
that the script did not output.

## Observability

Every cloud call carries a per-run session id so the customer can trace the traffic in action trail:

- Template: `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`, where `{skill}` is this skill's name
  (`alibabacloud-ecs-boot-repair-guide`) and `{session-id}` is the per-run id defined in
  `USER_AGENT_TEMPLATE` in `scripts/axes/boot_repair_guide/_constants.py`.
- The id is a 32-character lowercase hex string (`uuid.uuid4().hex`), generated once per script run
  and reused for every call in that run.
- It is attached to each invocation as `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-boot-repair-guide/<id>`.
- The id is echoed in the report header as `session_id`. It contains no customer identifier.

Implemented in `scripts/axes/boot_repair_guide/_cli.py`; see also `scripts/axes/boot_repair_guide/_constants.py` for the template constant.

## Scope boundaries and handoffs

`references/boot-repair-guide__handoff-map.md` holds the routing table and the wording for each handoff. The most common,
in order of frequency in this tier: patch or vulnerability installation actions belong to
`alibabacloud-ecs-patch-management` (this skill only handles "it broke after the update"); disk space and
inode exhaustion belong to the capacity skill; partition, GPT conversion, and LVM damage belong to
`alibabacloud-ecs-disk-expand-diagnosis`; an instance parked in `Starting` after a specification change
belongs to `alibabacloud-ecs-instance-state-diagnosis`; saturated disk IO and credential or remote-login
problems that occur while the OS is already up belong to `alibabacloud-ecs-disk-io-diagnosis` and the
connection flow; blackhole, DDoS, account lockout, and ransomware belong to security handling, where this
skill contributes only the data-rescue path.

## References

| file | content |
|---|---|
| `references/ram-policies.md` | enumerated actions, minimal policy, auth-failure wording |
| `references/boot-repair-guide__boot-failure-decision-tree.md` | gate rules, branch table, exit criteria, noise filter |
| `references/boot-repair-guide__boot-error-catalog.md` | observed boot error strings mapped to root-cause layer and next step |
| `references/boot-repair-guide__fstab-and-devices.md` | UUID vs device name, virtio vs NVMe naming, which line to comment out, false-positive detection |
| `references/boot-repair-guide__grub-efi-repair-guidance.md` | BIOS vs UEFI, primary vs fallback boot path, manual repair step lists |
| `references/boot-repair-guide__offline-repair-channel.md` | stopped / snapshot / same-zone / credential / IOPS prerequisites |
| `references/boot-repair-guide__windows-bsod-triage.md` | stop-code triage, dump evidence, safe mode, end-of-support images |
| `references/boot-repair-guide__post-update-boot-failure.md` | normal vs fault after updates, kernel upgrade side effects, patch handoff |
| `references/boot-repair-guide__data-rescue-and-reinstall.md` | rollback vs snapshot-to-disk rescue orchestration, irreversible warnings |
| `references/boot-repair-guide__evidence-checklist.md` | per-branch minimum evidence set and paste-back formats |
| `references/boot-repair-guide__doc-sources.md` | documentation index with provenance (verified search hit vs quoted from ticket) |
