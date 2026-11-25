# In-guest inspection commands

## 1. What this set can and cannot answer

The callable set below comes from the batch low-risk operation list. That list was written
for capacity and mount evidence, so this skill can separate "the file system is full" from
"I/O is slow", confirm which device backs a mount point, and size a log directory.

It **cannot** attribute I/O to a process. Tools that would do so are outside the callable
set and are refused, not improvised. When the customer needs the answer "which process was
writing", the correct output of this skill is a manual instruction to install a history
recorder such as atop on their own instance, wait for the next occurrence, and read the
recorded log. That matches how these cases are actually closed; claiming otherwise would be
a guess.

## 2. Callable set

Exactly one key per invocation. `guest-cmd --command-key <key>`.

| Key | OS | Command delivered | Needs `--path` | What it answers |
|---|---|---|---|---|
| `disk-usage` | linux | `df -h` | no | is a file system full, which separates capacity from performance |
| `inode-usage` | linux | `df -i` | no | is the inode table exhausted while bytes are free |
| `mount-map` | linux | `findmnt` | no | which device backs which mount point, so a disk id maps to a path |
| `deleted-open-files` | linux | `lsof +L1` | no | space held by files already removed but still open |
| `path-stat` | linux | `stat <path>` | yes | metadata of one path, contents untouched |
| `directory-volume` | linux | `du -h -d 1 <path>` | yes | how much one directory level holds, e.g. a log directory |
| `line-count` | linux | `wc -l <path>` | yes | how many lines one file has |
| `directory-listing` | linux | `ls -l <path>` | yes | contents of one directory |
| `windows-volumes` | windows | `Get-Volume` | no | volume health and free space |
| `windows-drives` | windows | `Get-PSDrive` | no | used and free space per drive |
| `windows-listing` | windows | `Get-ChildItem -Path <path>` | yes | contents of one directory |

Windows note: NTFS has no equivalent of `df -i`, so inode exhaustion cannot be confirmed on
Windows with this set; report that gap with the reading instead of implying the file system
is fine.

## 3. Refused, on purpose

Anything not in the table above is refused. The refusal is explicit and repeated verbatim
each time, so a weaker run cannot drift into "just this once".

| Refused | Why |
|---|---|
| `atop`, `iotop`, `iftop`, `pidstat`, `sar`, `vmstat`, `iostat`, `dmesg`, `journalctl` | not in the batch command list, and several of them only work when started in advance; installing or driving an agent from the skill is a change to the instance |
| `systemctl`, `service`, `kill`, `pkill` | stops or restarts customer workloads; recovery only, never from this skill |
| `mount`, `umount`, `mkfs`, `fsck`, `xfs_repair`, `tune2fs`, partitioning | can destroy data or make a volume unbootable |
| `fio`, `dd`, `truncate`, `rm`, `mv`, output redirection | write or destroy data; a wrong device name in a benchmark is a known data-loss path |
| `reboot`, `shutdown` | instance lifecycle, belongs to the customer and the console |
| `fsutil` subcommands | the batch list allows non-mutating `fsutil` subcommands, but no concrete one was verified, so none is exposed |

When the request is refused, the reply says: what is refused, why, and what the customer can
do instead in their own console or shell.

## 4. Confirmation gate

`RunCommand` is a state-changing API even when the command delivered only prints
information, so nothing is delivered before the customer has been shown, in one block:

```
- Target instance: i-... in <region>
- Command that would run: <exact command line>
- What it returns: <purpose>
- State change: none, the command only prints information
- Reversibility: nothing is written, so no rollback is required
- Blast radius: one inspection command inside this single instance; it adds a small
  amount of load while the instance is already saturated
```

Then wait for an explicit yes for **that one command**. A yes covering a batch, or a yes
given one hour earlier for a different key, does not carry over. Without the confirmation
the script prints the block, delivers nothing, and returns `STATUS: DEGRADED` with the
instruction to obtain the confirmation and re-run.

Delivery details the scripts apply:

- one `InstanceId` and one command per call, never a loop over instances
- Linux uses command type `RunShellScript`, Windows uses `RunPowerShellScript`, chosen from
  the OS family of the instance record rather than from what the customer implies
- a fixed short execution timeout, so a wedged guest cannot hang the session
- the command line is assembled from a constant in this table plus, at most, one validated
  path; customer prose never becomes shell text
- accepted path characters are letters, digits, `. _ + @ : , % -`, no spaces, no `..`, no
  newline; anything else is rejected before the call
- results read back through the invocation record are recorded output, not live usage, and
  are scrubbed for credential-shaped text before being printed

## 5. Snapshot rule

- Taking inspection readings requires no snapshot: nothing is written.
- A snapshot is expected **before any modification the customer performs** - a restart to
  recover from a wedge, a performance level change, a resize. State the billing consequence,
  wait until the snapshot has finished, and mention cleaning up unused snapshots afterwards.
- The `snapshot` subcommand is gated the same way as `guest-cmd`: it refuses to act until the
  confirmation flag for that one disk is present.

## 6. Degradation wording

Use these outcomes so the report never looks silently complete:

| Condition | Report |
|---|---|
| Cloud Assistant agent missing or offline | `STATUS: DEGRADED`; ask the customer to run the listed command themselves and paste the output |
| call delivered, no output returned | `STATUS: DEGRADED`; state that the invocation was accepted and what is missing |
| permission error on `run-command` | `STATUS: FAIL`; name the missing action and the minimal policy fragment in `ram-policies.md` |
| invocation still running at timeout | `STATUS: DEGRADED`; the instance may be too loaded to answer, which is itself a data point about the wedge |
| customer declines confirmation | proceed with cloud-side evidence only, and say that the guest-side gap remains open |

A wedged instance frequently cannot answer an inspection command at all. That outcome is
expected, and the honest report is "the guest did not respond, which is consistent with the
wedge" rather than a retry loop.
