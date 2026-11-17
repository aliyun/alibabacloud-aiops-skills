# Guest-side readings: whitelist, gate, refusals and fallbacks

This file exists because one number cannot be obtained from the cloud API:
what the customer sees as "how much I actually use" inside the file system.
Cloud-side calls report snapshot entries and provisioned disk sizes; neither is
the file-system view. When the customer contests a snapshot size against their
own usage figure, the comparison needs a third column, and that column comes
from one information-only reading executed inside the customer instance.

Every rule here is enforced in code, not by convention:
`validate_guest_request()` in `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` refuses
anything outside the whitelist **before** any dispatch, and the transport layer
in `scripts/areas/snapshot_billing_cleanup/_cli.py` refuses any action outside the declared set.

## 1. Whitelist (exactly one reading per gated call)

Linux - dispatched as `RunShellScript`:

| Reading | What it answers | Needs a path argument |
| --- | --- | --- |
| `df -h` | File-system visible usage versus size per mount | no |
| `df -i` | Free file slots on the file system | no |
| `lsof +L1` | Files still held open after unlink - space counted as used but already deleted | no |
| `findmnt` | What is mounted where, including whether the customer really mounted a disk they think they did | no |
| `du -x --max-depth=1 <path>` | Where the bytes sit, one level, without crossing into other file systems | yes |
| `du -sh --inodes <path>` | File-count distribution per directory in the path | yes |
| `stat <path>` | Attributes of one named object | yes |
| `ls -l <path>` | Listing of one named directory | yes |
| `wc -l <path>` | Line count of one named text file | yes |

Windows - dispatched as `RunPowerShellScript`:

| Reading | What it answers | Needs a path argument |
| --- | --- | --- |
| `Get-Volume` | Per-volume used and free space | no |
| `Get-PSDrive` | Per-drive used and free space | no |
| `Get-ChildItem <path>` | Listing of one named directory | yes |
| `fsutil volume diskfree <path>` | Free bytes on one named volume | yes |

A path argument must be a simple absolute Linux path or a Windows drive path,
matched against a strict pattern. Anything else is refused.

## 2. Automatic refusals

The request is rejected, with the reason printed, when it:

* is not one of the entries above, verbatim;
* packs more than one reading into a single call;
* contains chaining, redirection, quoting or globbing - `;`, `|`, `&`, `>`,
  `<`, backtick, `$`, `*`, `?`, newline, backslash, single or double quote;
* contains a destructive or state-changing verb, including removal, move,
  copy, raw write, truncate, kill, shutdown, reboot, format, partitioning,
  mount or unmount change, service control, permission or account change,
  download helpers, or shell evaluation;
* asks a path-taking reading without a valid path, or a non-path reading with
  one.

Refusal is a `STATUS: FAIL` with a `NEXT_ACTION` naming the whitelist file; the
agent relays it and stops. It is never worked around by a different quoting
trick.

## 3. The gate, in order

1. The agent asks the customer to confirm the notice **before** any dispatch.
   The script prints it whenever a gated mode is invoked without the
   confirmation flags, and nothing at all is executed at that point.
2. The notice states: the exact single command, the target instance, the
   region, that the reading only reports information, that it modifies nothing
   inside the guest, and therefore that there is no data-change risk to undo.
3. The customer approves that notice. Only then is the identical command line
   re-run with `--user-confirmed` plus a `--confirmation-scope` that names this
   run's region, instance and command; the script verifies the scope text
   actually covers them.
4. One approval authorizes exactly one reading. Approvals are not cached, not
   reused for a second reading, and not broadened to other instances or
   regions. Silence or a decline means the degraded path.

The same discipline covers the optional candidate file under `/tmp` and the
gated pre-cleanup snapshot backup: notice, approval, then one action.

## 4. Which reading answers which claim

| Customer claim | Reading that bears on it |
| --- | --- |
| "I only use X GB, the snapshot says many times more" | `df -h` for the file-system column, next to the cloud and billed columns |
| "I deleted a lot of data and nothing shrank" | `df -h` plus `lsof +L1` (deleted-but-open files) - and the block-level explanation, because snapshot size does not follow later deletions anyway |
| "It says no space left but there is free space" | `df -i` for file-slot exhaustion, then route the cleanup itself to `area:disk-expand-diagnosis` |
| "My server has a snapshot mounted" | `findmnt` plus `df -h`: a snapshot is not a mountable object; mounting is about a disk |
| "Which directory holds it" | `du -x --max-depth=1 <path>`, one level at a time |

The guest column is a file-system lens. It is never presented as the billed
chain capacity or as the provisioned disk size, and the gap between the three
is explained only with the documented reasons in
[snapshot-billing-decision-tree.md](snapshot-billing-cleanup__snapshot-billing-decision-tree.md).

## 5. Windows confidence statement

NTFS has no `df -i` equivalent, and its metadata structure is not a fixed inode
table. On Windows:

* report volume and drive free space from `Get-Volume` or `Get-PSDrive` only;
* state file-slot exhaustion as **not applicable / low confidence** rather than
  mapping it to an NTFS concept;
* do not infer file-count problems from byte usage.

Windows support in this skill is deliberately shallow: the readings above are
the whole surface, and anything requiring a change inside the guest stays with
a human.

## 6. Degraded paths, and what may be claimed in each

| Situation | Report behavior |
| --- | --- |
| Cloud Assistant not available, agent offline, or the dispatch failed | `STATUS: DEGRADED`, `[WARN]` naming the failure, plus the fallback of section 7 |
| The invocation has not reached a terminal state within the polling bound | `DEGRADED`; the reading is reported as pending, never as a value |
| Output empty or absent | `DEGRADED`; the guest column says `not returned` |
| Permission denied on the dispatch | literal `NoPermission` or `ImplicitDeny` plus the action name; recovery via [ram-policies.md](ram-policies.md) |
| The customer declines the notice | `DEGRADED`; the report is produced with two lenses and the missing one named |

Invocation history calls return past executions, not a current measurement. A
historical record is never used as this run's guest reading.

## 7. Fallback when no reading can be dispatched

Ask the operator to run the reading inside the instance themselves and paste
the output:

* Linux: `df -h`, and `du -x --max-depth=1 /` for the top-level breakdown.
* Windows: `Get-Volume`.

Mark that column as operator-supplied in the report. A pasted output is
evidence of the same file-system lens; the difference in trust is only about
who executed it, and that is stated.
