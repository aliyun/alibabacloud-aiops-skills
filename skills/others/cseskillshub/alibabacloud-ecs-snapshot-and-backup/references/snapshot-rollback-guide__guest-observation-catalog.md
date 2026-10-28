# Guest Observation Catalog (confirmation-gated, non-mutating)

Cloud APIs cannot see inside a disk: there is no query that returns the live
mount table, the files actually present, or whether a rollback took effect
on the filesystem. Those facts live inside the instance. This catalog is the
complete, frozen set of commands the `guest-check` mode may dispatch through
Cloud Assistant (the gated `RunCommand` dispatch). The command text is
validated against `GUEST_COMMAND_WHITELIST` in `scripts/_constants.py`;
anything else is refused outright.

## Hard rules

1. **One command per call, confirmation per call.** Before every dispatch
   the agent must tell the user: the exact command string, which instance it
   runs on, that it only observes state and changes nothing, and that the
   approval covers only this one execution. Then run `guest-check` with
   `--confirm yes`. An approval given minutes ago for a different command is
   not approval for this one.
2. **The catalog is the ceiling.** No combined statements, no redirection,
   no pipes, no variable expansion, no "just this once" variants. Service
   control (start/stop/restart), process control, package installs, file
   edits, `fsck`-class repairs and anything with side effects are NOT on the
   list and are answered with manual guidance instead.
3. **Degradation path.** If Cloud Assistant is unreachable (agent offline,
   permission gap, no confirmation), the mode returns `STATUS: DEGRADED`
   and the workflow falls back to asking the customer to run the same
   catalog command in the console session (Workbench / VNC) and paste the
   output. Never improvise a different command to "get around" it.
4. **Reuse over reinvention.** Where the environment provides the
   `alibabacloud-workbench-cli` skill, its login/execution channel takes
   precedence for reaching the guest; this catalog then supplies the same
   frozen commands through that channel. This skill never implements its own
   login or credential handling.

## Linux catalog

| Command (exact) | Reading it gives | Rollback workflow use |
|---|---|---|
| `df -h` | Per-filesystem capacity | Before/after comparison; "capacity reverted after rollback" |
| `df -hT` | Same, plus filesystem types | Detect a filesystem that reverted to the snapshot's older type/state |
| `findmnt` | The live mount table | Verify which disks/partitions are actually mounted where |
| `findmnt /path` | Mount state of one path | Confirm the business directory really sits on the disk being rolled back |
| `ls` / `ls -l /path` | Directory listing | Spot-check the paths the customer cares about before AND after |
| `stat /path` | Timestamps, size, type of one path | Prove whether a file postdates the restore point (would be lost) |
| `lsof +L1` | Deleted-but-still-open files | The "capacity grew but nothing changed" ghost; also explains stale state until reboot |

Paths are arguments of the listed verbs only; the validator rejects
metacharacters. A path that contains spaces is not accepted — relay it as a
manual Workbench step instead.

## Windows catalog

| Command (exact) | Reading it gives |
|---|---|
| `Get-Volume` | Per-volume capacity snapshot |
| `Get-Volume -DriveLetter C` | One volume's state |
| `Get-PSDrive` | Drive usage snapshot |
| `Get-PSDrive C` | One drive's usage |
| `Get-ChildItem C:\\path` | Directory listing |
| `Get-Item C:\\path` | Metadata of one path |

**Confidence note (state it in the report):** NTFS has no direct
inode-count equivalent, and filesystem-level detail beyond volume capacity
is thinner than the Linux catalog; Windows verdicts drawn from these
readings carry an explicit "lower precision" label. Windows patch/update
services that hang boot after rolling back to an old point are NOT
inspectable through this catalog — that symptom transfers to the
boot-repair workflow per [transfer-matrix.md](transfer-matrix.md).

## Evidence pairing (how to interpret)

- Pre-rollback: `ls`/`stat` on the critical paths proves the data that the
  rollback WILL destroy — pair it with the fallback-snapshot offer so the
  customer sees exactly what is at stake.
- Post-rollback: rerun the same commands for the same paths; differences are
  the rollback's real effect, not an assumption.
- Capacity reverting after rollback is expected behavior (the partition and
  filesystem return to the snapshot-time state); the grow-partition follow-up
  belongs to the disk-expansion workflow, never to this skill.
