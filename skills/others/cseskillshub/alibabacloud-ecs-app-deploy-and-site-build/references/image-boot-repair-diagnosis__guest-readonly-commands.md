# Guest read-only command whitelist and consent discipline

What lives here is the entire surface this skill may cause to execute inside
a customer instance: **one command per confirmation, chosen only from the
table below, only while the instance is Running** (a Cloud Assistant agent
answers only from a booted guest; there is no way — and no claim — to read
a boot sector or a stopped guest from here).

## Why a guest look is needed at all

Two readings exist nowhere in the cloud API surface for this tier: whether
an fstab-declared mount target directory actually exists, and whether the
detection report's "agent not installed" matches the image that is running
now. Cloud-side reads (images, instances, invocation history) cannot see
inside the guest OS; without this axis the diagnosis would mislabel
"ignorable leftover line" as "boot-blocking" or vice versa. Everything else
stays on the API side.

## Whitelist (class B, side-effect-free)

| Command (exactly one per dispatch) | Settles | Matches ticket evidence |
| --- | --- | --- |
| `findmnt` | live mount set, to diff against the fstab the customer pasted | mount-target detections |
| `stat <absolute-path>` | existence and type of ONE declared mount target or ONE documented component directory | mount-target and agent-presence questions |
| `ls <absolute-path>` | listing of ONE such directory (names only) | same |

Hard rules enforced by `classify_guest_command()` in the entry script before
any dispatch, and re-checked immediately after substitution:

- no shell metacharacters anywhere (`; & | < > $ ( ) { } quotes, globs,
  newlines): one plain command string, never a chain;
- `findmnt` bare only; `stat`/`ls` take exactly one absolute path argument
  without `..`;
- paths under config/home/root/proc/sys areas are refused — the allowed
  targets are mount points and component directories **as printed in the
  official install docs**; no such directory path is hardcoded in this
  skill for that reason.

## Explicitly refused (examples the customer will propose)

| Request | Why refused | Instead |
| --- | --- | --- |
| `cat`/`grep`/`sed` on the fstab file | reading file contents is outside the low-risk list | ask the customer to paste the fstab file |
| `systemctl status <svc>` | service state/control is outside the list | customer pastes it, or handoff |
| `lsblk`, `blkid`, `fdisk -l` | block/partition probing is outside the list | customer runs it in their session |
| `mount`/`umount` | changes mount state: a write | never; manual guidance only |
| anything `grub` (status or regeneration) | bootloader work is repair-class | the guided self-repair paths in [handoff.md](handoff.md) |
| `apt` / `yum` / `dnf` (any subcommand) | package management is a write | customer installs per official doc |
| any output redirection / command chaining | smuggles a second, unvetted action | refused, not softened |

A refusal is printed with its reason and converted into a customer-run
step. The skill never rewrites a refused request into a lookalike that
passes the gate.

## Channels

1. **Guided (default, always available)** — the customer opens their own
   console session (Workbench) or runs the command locally, and pastes the
   output. The skill interprets pasted readings on exactly the same code
   path as dispatched ones.
2. **Dispatched (`probe` mode)** — the entry script sends ONE whitelisted
   command through the Cloud Assistant channel under the **customer's own
   credentials** (this skill carries no standing grant for it; see
   [ram-policies.md](ram-policies.md)). The read-back uses the class A
   invocation-history query.

## Confirmation protocol (mechanically enforced)

Before a dispatch, all four lines must reach the customer, then the
customer agrees to **this one operation**:

1. the exact command string that will run (never a paraphrase);
2. scope: one instance in one named region; nothing else is touched;
3. read-only nature: it lists/stats paths; it writes nothing, installs
   nothing, reads no file contents; and reversibility: no state to undo;
4. that the confirmation covers exactly this region + instance + command
   and expires with the run.

The script implements this as a two-pass gate: the first run prints the
disclosure and a **single-use token** bound to the
`region|instance|command` triple and exits `STATUS: FAIL` without
dispatching; only a re-run carrying that exact token dispatches. A changed
command, instance or region yields a different token and forces a fresh
confirmation.

## When the probe cannot happen (always leave a trace)

Instance not Running, agent offline, dispatch refused by authorization, or
the poll window elapses: the run reports `STATUS: DEGRADED`, records the
reason in the degradation log, and falls back to the guided channel —
"run this exact command yourself and paste the output". An offline agent
is itself the Cloud Assistant axis and hands off per
[handoff.md](handoff.md). The skill never claims a reading it did not get.

## Windows

Not supported by this release: every ticket in the evidence pool for this
tier is a Linux guest, so no Windows equivalent of this table is claimed or
offered. A Windows request is answered with the boundary statement plus a
human ticket.
