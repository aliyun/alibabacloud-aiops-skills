# Guest command whitelist (class B)

These commands run inside the customer instance to obtain what no cloud API
exposes in this scenario: whether a volume is so full that the agent cannot write
its task files, whether inodes are exhausted while bytes are free, whether a
mount is missing, how large one directory actually is. The control plane reports
dispatch status and nothing about the guest's own state, so without these
readings the environment-exclusion branch of the tree cannot close.

They are delivered by the Cloud Assistant dispatch operation, in CLI plugin
mode `run-command` - a write-class operation even when the command it carries
only inspects, and not part of this skill's declared read-only permission
surface (it runs under the customer's own credentials, which is why a strictly
read-only session degrades to the customer-run steps at the end of this file).
That same framing is why every execution sits behind the disclosure-and-confirm
gate in `SKILL.md`, why exactly one command goes out per consent, and why the
assembled string is re-validated after parameter substitution.

## The whitelist

The script takes a probe key, never a raw command line. `--target` applies only
where the table says so, is validated (absolute POSIX path or drive-rooted
Windows path, no spaces, no `..`, no metacharacters) and then appended.

### Linux (Type RunShellScript)

| Key | Command | Purpose | What it reports for this scenario |
| --- | --- | --- | --- |
| `df_h` | `df -h` | Byte usage and free space per mounted volume | A volume so full the agent cannot create its task files - a confirmed timeout cause |
| `df_i` | `df -i` | inode usage per mounted volume | "cannot create new file" / "file count limit" failures with bytes still free |
| `findmnt` | `findmnt` | The mount table | A missing or unexpected mount the failed task wrote to |
| `du_top` | `du -x --max-depth=1 <target>` | Size of each direct child of one directory, without crossing mounts | Candidate directories for a customer-run cleanup (the skill only lists) |
| `lsof_deleted` | `lsof +L1` | Deleted-but-still-open files | Space logically freed but not returned to the volume while a process holds the handle |
| `stat` | `stat <path>` | Metadata, size and block count of one path | Whether a named file is the space or activity in question |
| `ls_dir` | `ls -lh <dir>` | Long listing of one directory | Unexpected entries (tmp sprawl, leftovers) in one place |
| `wc_lines` | `wc -l <file>` | Line count of one text file | Log volume before a customer truncation decision |

### Windows (Type RunPowerShellScript)

| Key | Command | Purpose | What it reports for this scenario |
| --- | --- | --- | --- |
| `get_volume` | `Get-Volume` | Health, size, free space per volume | Which Windows volume is full |
| `get_psdrive` | `Get-PSDrive` | Used and free bytes per drive letter | The same reading in drive-letter terms |
| `get_childitem` | `Get-ChildItem -Force <path>` | Directory listing including hidden entries | Large or hidden consumers under one path |
| `fsutil_diskfree` | `fsutil volume diskfree <drive>` | Total, free and available bytes for one volume (reports only, changes nothing) | Precise free-space figures for the system volume |

Windows caveat carried from the case history (T-478C2A19): NTFS has no `df -i`
equivalent, so any file-count conclusion on Windows is stated with explicitly
reduced confidence.

## What is refused, and why it stays refused

The most useful guest checks for this scenario's subject would be the agent's own
state: `systemctl status aliyun.service`, the agent's log files under its
install directory, `ps`, and the partition readers `lsblk` / `fdisk -l` /
`blkid` that the support engineers of cases T-99046C78 and T-79753A0F used by
the customer's hand. **None of them is whitelisted**: the low-risk command list
this skill is built against bans service-control binaries outright, and the
rest were not carried into the verified whitelist. Extending the whitelist
requires a policy-level change to that command list plus fresh API
verification - the skill must not make that decision inside a session.

So those checks are printed as customer-run steps (the degraded-mode list
below), which is also the ceiling the human support process had. Refusals state
their reason and name the whitelist; a request is never rewritten into a
different command that happens to pass.

Rejected regardless of what the caller claims, re-checked against the assembled
string (non-exhaustive, the full token list lives in `scripts/areas/cloud_assistant_diagnosis/_constants.py`):
`rm`, `rmdir`, `mv`, `cp`, `dd`, `truncate`, `mkfs`, `format`, `fdisk`,
`parted`, `lsblk`, `blkid`, `kill`, `pkill`, `systemctl`, `service`, `reboot`,
`shutdown`, `mount`, `umount`, `echo`, `sed`, `awk`, `curl`, `wget`, `yum`,
`apt`, `tail`, `cat`, `head`, `ps`, `journalctl`, `reg`, `sc`, `net`, `wmic`,
`taskkill`, the PowerShell `Set-`, `Remove-`, `New-`, `Add-`, `Stop-`,
`Restart-` verb families, and any shell metacharacter (`;` `|` `&` `$` `` ` ``
`>` `<` and friends).

## Consent-gated execution, end to end

1. `guest-probe --region-id ... --instance-id ... --command <key> [--target <path>]`
   - the script prints the full disclosure block and executes nothing:
   exact command string, guest OS dialect, delivery mechanism, blast radius
   (one instance), side effects (none), reversibility (nothing modified), cost
   (the probe itself is not billed), precondition (the agent must be reachable
   - often exactly what is failing), purpose, and the single-use scope of the
   token.
2. Relay those lines to the customer and obtain agreement to that one command.
3. Re-run with `--confirm <token>`. A second probe, another instance, the same
   probe an hour later: all need a fresh disclosure and a fresh token; the
   script rejects a token that does not match the operation.
4. The result is read back through the invocation history with its exit code
   and output; a guest command that fails to complete cleanly is itself a
   finding about the environment, and the run degrades honestly.

## Degraded mode: the agent channel is down, or the customer declines

This scenario's special failure: the delivery mechanism under discussion is the
mechanism being diagnosed. When dispatch fails, when the customer declines
instance operations (a real workflow - case T-FA7FC9EE), or when the console
shows the agent offline, the report sets `STATUS: DEGRADED`, names the missing
piece, and hands over the list the customer runs and pastes back verbatim:

- Linux: `df -h` ; `df -i` ; `findmnt` ; `systemctl status aliyun.service` ;
  the agent log under its install directory, the lines around the failure time.
- Windows: `Get-Volume` ; `Get-PSDrive` ; the services-manager status of
  "Aliyun Assist Service" ; the agent's log files likewise.
- Plus, for any command that failed: the invoke id and the full console error
  text of that task.

Raw output pasted, not summarized; the readings feed the same classification as
a successful probe would. The customer running a step is the human-authorised
path the source cases followed - the skill's boundary is that it never runs
anything beyond the whitelist itself, and never claims a reading it was not
given.
