---
name: alibabacloud-ecs-high-frequency-issues
area: disk-expand-diagnosis
description: |
  Diagnose ECS cloud disk expansion that did not take effect in the guest, and partition or filesystem adjustment failures. Queries disk and instance facts, interprets pasted guest output, and emits exact commands for a human to run. Snapshot and resize orders are gated.
  Use when a disk was expanded but the size is unchanged, or a partition merge, shrink or accidental volume deletion left capacity unusable.
  Triggers: disk expanded but df still shows the old size; growpart or resize2fs did not work; Permission denied to resize filesystem; GPT PMBR size mismatch; Extend Volume greyed out; filesystem remount-ro or bad superblock.
  Do NOT use: disk full or inode exhausted, instance will not boot, disk IO saturation, backup strategy - see area:instance-state-diagnosis, area:resource-bottleneck, alibabacloud-ecs-disaster-recovery-snapshot.
---

# ECS Cloud Disk Expand Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Explains why a cloud disk that was paid for and enlarged in the console still shows
the old capacity inside the operating system, and why partition adjustment work
(merge, shrink, accidental volume deletion, drive letter and logical partition
changes) leaves capacity unusable. It separates three states that customers
routinely confuse: the capacity change never landed on the cloud side, it landed and
the guest partition or filesystem is the outstanding step, or a blocker such as
filesystem damage, exhausted inodes or partition table metadata inconsistency is
standing in the way.

## Scope

In scope:

* Cloud side facts for one disk or one instance: size, category, status, attachment,
  operating system family, instance power state.
* Interpretation of guest output the customer pastes: partition table type, device
  naming form, filesystem type, mount points, space and inode usage.
* Generating the exact partition command plus the matching filesystem command for a
  human to execute, with the device name and the partition number written out.
* Feasibility verdicts for partition adjustment requests, including the cases where
  the honest answer is that the platform cannot do it.
* Pre change snapshot checking, and a gated snapshot or resize order.

Out of scope, recognised and handed off rather than attempted: freeing space or
inodes, instance startup failures, disk IO performance, backup and snapshot
strategy, data recovery, billing and refunds. See
[references/disk-expand-diagnosis__handoff-matrix.md](references/disk-expand-diagnosis__handoff-matrix.md).

## Execution Principle

The agent runs `scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py` and nothing else. It never
assembles an `aliyun` command by hand, never calls an OpenAPI action directly, and
never bypasses the entry point to reach a helper module. Every cloud fact in a
report comes from a call the script made; every judgement comes from the tables in
`scripts/areas/disk_expand_diagnosis/_constants.py` or from output the customer pasted in. If a value was not
returned, the report says so instead of supplying one from memory.

Subcommands:

| Subcommand | Purpose | Cloud calls |
| --- | --- | --- |
| `check-auth` | Credential preflight and account label | `GetCallerIdentity` |
| `diagnose` | Full decision tree | `DescribeDisks`, `DescribeInstances` |
| `explain` | Interpret pasted guest output, no cloud access | none |
| `run-command` | Dispatch ONE approved non-mutating guest command | `RunCommand` (gated) |
| `create-snapshot` | Pre change snapshot of the target disk | `CreateSnapshot` (gated) |
| `resize-disk` | Cloud side capacity change order | `ResizeDisk` (gated) |

Typical invocations, run from the skill directory:

```bash
python3 scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py check-auth

python3 scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py diagnose \
  --region-id cn-hangzhou --instance-id i-example0123456789 \
  --expected-size-gib 100

python3 scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py diagnose \
  --region-id cn-hangzhou --disk-id d-example0123456789 \
  --expected-size-gib 300 --os-type linux --mount / \
  --paste customer-paste.txt

python3 scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py explain --paste -

python3 scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py run-command \
  --region-id cn-hangzhou --instance-id i-example0123456789 \
  --command "df -i"
```

`--region-id` plus `--instance-id` or `--disk-id` are required for `diagnose`. The
API is regional; sweeping every region to guess one is deliberately not done, so
when the customer gives only a public IP address, ask for the region and the
resource identifier.

## Permission Model

This skill is **not** an inspection-only package. It uses three classes of action
and each class has its own gate.

1. **Cloud queries, no per call confirmation.** `GetCallerIdentity`,
   `DescribeDisks`, `DescribeInstances`. These retrieve state and change nothing.
2. **Guest commands, one at a time, confirmation per call.** `RunCommand` is a
   write class action. Here it carries only a non-mutating inspection command drawn
   from the approved list in `scripts/areas/disk_expand_diagnosis/_constants.py`. One command per invocation,
   and the acknowledgement covers that command only, not the rest of the session.
3. **Low risk reversible writes, confirmation per call.** `CreateSnapshot` before
   any change, and `ResizeDisk` for the cloud side capacity order.

Declared write actions and their permission points, each formed by the RAM code
`ecs`, a colon, then the action name: `RunCommand`, `CreateSnapshot` and
`ResizeDisk`. Full list, including the query actions, in
[references/ram-policies.md](references/ram-policies.md). No wildcard is used
anywhere in this package.

### Confirm gate (mandatory)

Before any guest command is dispatched or any write action is called, the agent
MUST state, in the same turn and before acting:

* exactly what will be executed, with the literal command or the literal API
  parameters;
* the single resource it targets, by identifier;
* whether it mutates anything, and whether it can be undone;
* the cost consequence, if any;
* what happens if it fails.

Then the agent MUST wait for an explicit affirmative answer. Silence, ambiguity, or
a general "go ahead and fix it" earlier in the conversation is not confirmation for
a later call. `ResizeDisk` additionally requires the customer to restate the exact
target size after being told the capacity cannot be given back.

If the gate is not satisfied the script itself refuses and prints what still has to
be disclosed, so the gate does not depend on the agent remembering it.

### Guest command whitelist

Only the non-mutating commands listed under `AUTO_GUEST_COMMAND_EXACT`,
`AUTO_GUEST_COMMAND_FAMILIES` and `AUTO_FSUTIL_QUERY_PREFIXES` in
`scripts/areas/disk_expand_diagnosis/_constants.py` may be dispatched. Anything containing shell composition
(`;`, `&&`, `||`, `|`, backticks, `$( )`, redirection) is refused outright, so no
mutating step can ride along inside a listing command.

**Device level listing commands are refused by this skill and MUST NOT be
auto-executed**: `lsblk`, `lsblk -f`, `blkid`, `fdisk -l`, `fdisk -lu`, `df -Th`,
`mount`, `dmesg`, `Get-Partition`, `Get-Disk`. They are not on the approved list
for this tier. When the diagnosis needs them, the agent asks the customer to run
them inside the instance and paste the raw output back, then continues from that
text. This is a hard constraint, not a preference.

## ABSOLUTE PROHIBITION

This skill MUST NOT generate, write, execute, schedule or hand over as a
copy-paste-ready automated step any of the following. For each one it outputs a
human procedure, the risk, and the rollback path, and stops there.

* Guest partition and filesystem writers: `growpart`, `resize2fs`, `xfs_growfs`,
  `parted`, `fdisk` in write mode, `cfdisk`, `sfdisk`, `sgdisk`, `pvresize`,
  `vgextend`, `lvextend`, `partprobe`, `kpartx`, `blockdev`, `wipefs`.
* Filesystem repair: `fsck`, `e2fsck`, `xfs_repair`, including from a detached or
  rescue disk.
* Formatting and volume deletion: `mkfs`, `mkswap`, Disk Management "Delete
  Volume", third party partition software.
* Instance power actions: start, stop, reboot, force restart.
* `fstab` edits, and any mount or unmount change.
* Snapshot deletion, disk release or detach, shrink, refunds, unsubscription and
  any other commercial action.
* Any ECS action outside the whitelist above. In particular the `Modify*`,
  `Delete*`, `Release*`, `Reset*`, `Replace*`, `Attach*`, `Detach*`, `Reboot*`,
  `Start*`, `Stop*`, `Import*`, `Export*`, `Revoke*`, `Bind*` and `Unbind*`
  families are never called, not even after a customer confirmation.

The script enforces this through `NEVER_ALLOWED_ACTION_PREFIXES` and
`NEVER_AUTO_GUEST_COMMANDS`. Emitting the growpart and resize pair as **text for a
human to run** is the intended output of this skill and is not a violation; running
it, or wrapping it so something else runs it, is.

## Snapshot First

No partition, filesystem or cleanup guidance is issued without a snapshot status
field in the report. A fresh snapshot of the target disk is a precondition for
every change step. Two facts must be stated to the customer every time, because
both are widely misunderstood: snapshots are stored in cloud storage and never
consume space on the disk being resized, and they bill separately by stored
capacity and retention time, so old ones should be deleted after the change is
verified. A snapshot the service side cannot create on the customer's behalf has to
be created in the customer's own account context. Details and the retention
recommendation are in [references/disk-expand-diagnosis__snapshot-first.md](references/disk-expand-diagnosis__snapshot-first.md).

## Workflow

```text
Step 0  Identity and inputs. GetCallerIdentity. Ask for the region plus an
        instance or disk ID when either is missing. Resolve the two ambiguities
        that produce whole wasted conversations: is the capacity that was extended
        the disk or the instance memory, and was an existing disk grown or an
        additional disk bought. A resize request that is not about an ECS cloud
        disk at all stops here with a clarification.
Step 1  Cloud side facts. DescribeDisks and DescribeInstances, no confirmation
        needed.
Step 2  Branch on the cloud side verdict.
        2a  Size below the expected value: the capacity change never landed.
            Disclose cost and irreversibility, then either take the gated
            ResizeDisk order or emit the parameterized console procedure.
        2b  Size at or above the expected value: the change landed and the guest
            is the outstanding step. State explicitly that no longer finding a
            resize entry point in the console is the expected condition here, not
            evidence of a failed order. Continue to Step 3.
        2c  A data disk in status Available, or more disks than the customer
            expects: an additional disk was bought instead of the original being
            grown, or a new disk was never attached. Hand over the attach and
            initialize documentation. Never emit a format command.
        2d  Instance in an intermediate power state, or the complaint is that it
            will not boot: stop and hand off to the instance state diagnosis.
Step 3  Guest evidence. Once the target machine is confirmed, ask the customer to
        run and paste df -Th, lsblk -f, blkid, fdisk -lu and df -i on that machine.
        While the target itself is still unidentified, the answer settles the target
        first and keeps these commands as the step after it. Optionally dispatch one
        approved non-mutating command through the confirm gate. If neither is
        available the run reports STATUS: DEGRADED and every conclusion is marked as
        resting on cloud facts alone.
Step 4  Blocker evaluation, in this order.
        Filesystem health error, including a refused online resize: repair first,
        by a human, after a snapshot. Pause the resize.
        Space or inode usage at the limit: hand off to the disk capacity diagnosis.
        Partition table metadata inconsistent with the device size: identify and
        escalate; published walkthroughs do not cover reconciling it.
        LVM, or an extended partition carrying logical partitions: dedicated
        procedure, never the generic command pair.
        No blocker: emit the command pair for the detected device and filesystem
        type.
Step 5  Snapshot precondition check before any change step is handed over.
Step 6  Report: verdict, evidence, manual steps, handoffs, assumptions, limits,
        STATUS and NEXT_ACTION.
```

Command pair rules that are acceptance criteria, not style:

* The partition command names the disk device and the partition number as two
  separate arguments, with the space between them called out, because writing them
  together is the most common failure at that step.
* The filesystem command is chosen by the filesystem type actually observed for
  that device: `resize2fs` for ext4, ext3 and ext2, `xfs_growfs` against the mount
  point for xfs. `resize2fs` is never emitted for xfs.
* When the filesystem type is undetermined, no filesystem command is emitted. The
  report asks for the readings that would determine it.
* On Linux the verification step is `df -h`. Windows Disk Management wording is
  never used as the verification step for a Linux instance.
* Windows conclusions about file count or metadata exhaustion carry an explicit
  confidence caveat, because NTFS has no `df -i` equivalent.

Error strings, symptom phrases and the verdict each one maps to are in
[references/disk-expand-diagnosis__error-signals.md](references/disk-expand-diagnosis__error-signals.md). Device form matrices
are in [references/disk-expand-diagnosis__linux-expand-paths.md](references/disk-expand-diagnosis__linux-expand-paths.md) and
[references/disk-expand-diagnosis__windows-expand-paths.md](references/disk-expand-diagnosis__windows-expand-paths.md).

## Observability

Every single CLI invocation carries a User-Agent built from a per run session
identifier, so all calls belonging to one diagnosis can be attributed and counted
together.

* Template: `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`, defined as
  `USER_AGENT_TEMPLATE` in `scripts/areas/disk_expand_diagnosis/_constants.py` with the format fields
  `skill_name` and `session_id`.
* Flag: `--user-agent`, appended by `run_cli` in `scripts/areas/disk_expand_diagnosis/_cli.py` to every call
  without exception.
* Session identifier: 32 hex characters from `uuid.uuid4().hex`, generated once
  per run by `new_session_id` and printed in the report header as `session_id` and
  `user_agent`.

Every call also has an explicit timeout (30 seconds for queries, 90 for gated
writes), a bounded exponential backoff retry for transient failures only, and
`stdin` detached so no call can hang on input. Non transient failures raise
immediately instead of being retried.

## Credentials

Authentication uses the aliyun CLI default credential chain only. This package
never asks for, reads, stores, prints or forwards an AccessKey pair or a security
token. If the preflight fails the remedy is `aliyun sts get-caller-identity`, or the role the
environment already provides. Credential shaped values are masked in anything the
CLI writes to stderr before it is echoed. When a customer pastes a password or
other secret into the conversation, do not repeat it, do not write it to any file,
and advise changing it afterwards.

A denied call is reported with the code the platform returns, `NoPermission` or
`ImplicitDeny`, together with the specific missing action and a pointer to
[references/ram-policies.md](references/ram-policies.md) for the minimal policy
fragment.

## Output Contract

Every run of this entry script ends with the two contract lines. They are the
machine channel: an automation reading this script's stdout parses them, and the
dispatcher copies their meaning into the answer. They are not customer text -
`SKILL.md` 3h forbids them in a delivered reply, so relay the verdict and the
customer step instead of the tokens:

```text
STATUS: OK | DEGRADED | FAILED
NEXT_ACTION: <code>
```

`STATUS: OK` means the tree reached a verdict on cloud facts plus guest evidence.
`STATUS: DEGRADED` means a call failed, an input was missing, or the guest side is
unverified, and the report states which. `STATUS: FAILED` means the run could not
produce a judgement. Exit codes mirror this: 0, 1 and 2.

The report body always contains: the verdict list, the evidence actually collected,
matched error signals with their confidence, the snapshot status, manual steps for
a human, handoffs, assumptions and auto-filled inputs, and the limits on
confidence. The agent quotes only values that were returned, names every parameter
it filled in itself, and never presents a guidance step as something it performed.

When a request falls outside this skill, the reply states the boundary, gives the
console entry point, and uses the matching handoff wording from
[references/disk-expand-diagnosis__handoff-matrix.md](references/disk-expand-diagnosis__handoff-matrix.md).

## References

* [references/ram-policies.md](references/ram-policies.md) - every action used,
  its permission point, and the minimal policy fragments.
* [references/disk-expand-diagnosis__error-signals.md](references/disk-expand-diagnosis__error-signals.md) - error strings and
  symptoms mapped to a verdict, a disposition and a confidence level.
* [references/disk-expand-diagnosis__linux-expand-paths.md](references/disk-expand-diagnosis__linux-expand-paths.md) - device
  form and filesystem matrices for Linux.
* [references/disk-expand-diagnosis__windows-expand-paths.md](references/disk-expand-diagnosis__windows-expand-paths.md) - Disk
  Management paths and the adjacency constraint.
* [references/disk-expand-diagnosis__snapshot-first.md](references/disk-expand-diagnosis__snapshot-first.md) - the pre change
  snapshot checklist, billing wording and retention guidance.
* [references/disk-expand-diagnosis__handoff-matrix.md](references/disk-expand-diagnosis__handoff-matrix.md) - what belongs to
  another diagnosis, and the wording to use when moving it there.
