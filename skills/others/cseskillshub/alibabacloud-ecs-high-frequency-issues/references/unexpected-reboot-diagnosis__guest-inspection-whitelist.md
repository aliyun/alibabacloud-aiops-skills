# Guest Command Whitelist (frozen) and Manual-Only Commands

This tier proves facts inside the guest but changes nothing. Two channels
exist: the scripts dispatch a frozen set of non-mutating commands through
Cloud Assistant AFTER per-call confirmation; everything else the customer
runs manually and pastes back into `explain`.

The command set below mirrors the batch low-risk operations list, section B.
`scripts/areas/unexpected_reboot_diagnosis/_constants.py` carries the same list as frozen constants; this file
is the human-readable contract. If the two ever disagree, the code wins and
this file must be corrected.

## Rules of engagement (enforced by the scripts, restated for the agent)

1. ONE command per invocation; the confirmation covers that call only.
   Before dispatching, tell the user: the exact command string, the target
   instance, that the command inspects and does not alter anything, and
   that its output is returned verbatim.
2. The submitted string must match the whitelist exactly (fixed form, or
   family plus ONE validated argument). Absolute paths only for path
   arguments; drive letters for Windows volume queries.
3. Any shell composition or quoting token fails closed: `;` `&&` `||` `|`
   backticks `$(` `${` `>` `<` `&` newline, quote characters.
4. Path arguments containing `crash`, `atop`, `dump`, `shadow`, `ssh`,
   `passwd` fragments are refused for auto-execution in this tier - those
   locations are handled as manual steps below (this includes listing the
   kernel crash directory).
5. A refusal is final: report the whitelisted alternative or the manual
   path. Never negotiate a "safe subset" of a refused command.
6. When Cloud Assistant is absent, offline, or the account lacks the gated
   write permission, degrade: the customer runs the whitelisted command
   themselves (console session or SSH) and pastes the output into
   `python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py explain --paste -`.

## Auto-executable whitelist (Linux)

| Command | What it proves here | Reversible? |
| --- | --- | --- |
| `df -h` | filesystem capacity - distinguishes "disk full" from "spec ceiling" | inspection only |
| `df -i` | inode exhaustion - "cannot create new file" with free space left | inspection only |
| `findmnt` | mount layout, which device backs which path | inspection only |
| `lsof +L1` | space held by deleted-but-open files (log churn after cleanup) | inspection only |
| `du -x -h --max-depth=1 <path>` | where the space sits, one level, no crossing mounts; evidence only, cleanup stays manual | inspection only |
| `ls -la <path>` | listing one directory (capacity evidence, e.g. a data or log directory) | inspection only |
| `stat <path>` | size, timestamps, link count of one file | inspection only |
| `wc -l <path>` | line count of one log file (growth-rate evidence) | inspection only |

## Auto-executable whitelist (Windows)

| Command | What it proves here | Reversible? |
| --- | --- | --- |
| `Get-Volume` | per-volume free space on NTFS/ReFS | inspection only |
| `Get-PSDrive` | drive-level used/free summary | inspection only |
| `Get-ChildItem <path>` | directory listing (capacity evidence) | inspection only |
| `fsutil fsinfo drives` | enumerate volumes | inspection only |
| `fsutil volume diskfree <drive>:` | free space for one volume | inspection only |

NTFS has no `df -i` equivalent: inode-style "too many files" symptoms on
Windows map to MFT or per-directory entry limits; mark that confidence
difference explicitly in the report rather than inventing a number.

## Fixed refusal wording for off-whitelist commands

> That command is outside the frozen inspection whitelist for this
> diagnosis. I will not execute it. Two options: (1) pick a whitelisted
> command that answers the same question, or (2) run it yourself in the
> console session or over SSH and paste the output back - I will fold it
> into the evidence report as customer-provided data.

## Manual-only commands for this tier (NOT auto-executed)

These carry the deepest reboot evidence but are deliberately outside the
batch low-risk list, so this skill guides, never runs them:

| Goal | Command (customer-run) | Guidance |
| --- | --- | --- |
| "which process ate the memory" (the 09:00 crash) | `atop -r /var/log/atop/atop_<YYYYMMDD> -b <HH:MM>` then press `C`/`M` for process views | deploy atop first (manual install; see playbook); replay only sees windows after deployment |
| kernel/panic ring buffer | `dmesg -T \| tail -n 200` (customer-run), or `journalctl -p 3 -b -1` | past-boot kernel messages survive a kdump-less crash only partially; say so |
| reboot history | `last -x reboot shutdown \| head` | separates forced reboots from platform reboots at minute granularity |
| crash dumps present? | `ls -la /var/crash` (customer-run) and `systemctl is-enabled kdump` | pair with the kdump guide below |
| Windows crash and system log events | `Get-WinEvent -LogName System -MaxEvents 200` filtered to Error/Critical (customer-run) | the Event Viewer "BugCheck" entries are the Windows counterpart of a vmcore |
| anything that mutates | restart service, delete file, change config | always manual; where the customer is about to clean or delete, run the snapshot-first guard first |

## Snapshot-first rule in this tier

Before the customer acts on any cleanup, space-release or risky handling
suggested by this diagnosis, the batch policy requires a guard snapshot of
the affected cloud disk: `python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py
create-snapshot` with the confirmation gate, or the console path
`ecs console -> Storage & Snapshots -> Snapshots -> Create Snapshot`. Pure
evidence gathering (this whitelist) is exempt. Local disks cannot be
snapshotted; the script refuses them and points to the in-guest backup
paths. Snapshot DELETION is never part of this skill.
