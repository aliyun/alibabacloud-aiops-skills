# In-instance inspection (capability C7) - guided, one command at a time

Cloud APIs answer "what does the platform see". Only the instance itself answers "how
much was being written while the snapshot ran". That second half is guest evidence,
and in this skill it is **auxiliary**: the primary readings stay in the snapshot, disk
and policy queries.

Entry point: `python3 scripts/snapshot_policy_check.py guest-commands [--candidate "df -h"]`

## Hard rules

1. Every command below is side-effect free: it reads and prints, it never writes,
   deletes, formats, restarts or re-registers anything.
2. One command per request. No chaining, no redirection, no substitution, no
   loops - the validator refuses any of those characters even around an allowlisted
   name.
3. Before running anything, tell the customer what the command does, what it can and
   cannot prove, and that it changes nothing. Take their confirmation for that single
   call; a prior yes does not carry over.
4. Anything not on the list is refused and printed as a manual step instead. This
   includes the tempting ones: `vssadmin list writers`, service restarts, `regsvr32`,
   disk cleanup, package installs, and anything touching antivirus.
5. If the agent is offline, the channel is unavailable, or the customer declines,
   report `STATUS: DEGRADED`, name the reading still missing, and ask them to run it
   and paste the output. Pasted output is legitimate evidence; inventing a reading is
   not.

## Delivery status in this version

This package does **not** dispatch commands into the instance. The execution channel
(workbench against Cloud Assistant `RunCommand`) and that channel's permission point
are still open items in the requirements document, and the rule is that an
unverified action may not be wired or declared. So the commands are handed to the
customer, which is the documented degraded path rather than a shortcut.

## Allowlist

Linux:

| Command | What it shows | Use it for |
|---|---|---|
| `df -h` | file system usage | capacity context, whether a fill-up explains a stall |
| `df -i` | inode usage | "no space left" while bytes look free |
| `du -x --max-depth=1` | largest immediate children, one file system | locating write volume |
| `lsof +L1` | open deleted files still held | space not returning after cleanup |
| `findmnt` | mount topology | confirming which disk a path lives on |
| `stat` | single inode timestamps and size | when a file last changed |
| `ls -l` | listing one directory | spot checks the customer named |

Windows:

| Command | What it shows | Caveat |
|---|---|---|
| `Get-Volume` | per-volume size and free space | primary capacity reading |
| `Get-PSDrive` | drive usage | overlaps Get-Volume |
| `Get-ChildItem` | directory listing | listing only, never piped to a removal |
| `fsutil volume diskfree` | free space on one volume | single-volume scope |

NTFS has no `df -i` equivalent. When an inode-style question comes in on Windows, say
the reading does not exist in that form and mark the capacity conclusion as lower
confidence, rather than substituting a Linux-shaped answer.

## How guest readings connect to snapshot findings

| Observation in the guest | Bearing on the snapshot question |
|---|---|
| heavy writes in the creation window | larger increment, longer creation - explains a slow percentage |
| volume near full | a full file system often coincides with an unresponsive instance (ticket 0001FS004N) |
| `lsof +L1` showing held deleted files | space the customer believes is free; context for cleanup requests, which route out |
| application quiescing unavailable | application-consistent flow will fail even when the platform side is healthy |

Capacity cleanup itself is a different axis: route it per
`references/handoff-boundaries.md`, and take the pre-change backup first.
