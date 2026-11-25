# Hand-off map

This skill owns one axis: disk throughput, IOPS, latency and the system stall they cause.
Four look-alike axes belong elsewhere, and answering them here produces the wrong fix, so
recognise them first and hand them over with the wording below.

## Routing table

| Customer wording that triggers this route | Real axis | Hand off to | What this skill still does |
|---|---|---|---|
| "the disk is full", "no space left on device", "cannot upload, the disk says full", "inodes are exhausted", "help me clean up the disk" | capacity and inode usage | `alibabacloud-ecs-disk-capacity-diagnosis` | runs the capacity-versus-performance check, then routes |
| "I extended the disk in the console but `df` still shows the old size", "the partition is smaller than the disk", "the volume group grew and the file system command hangs" | partition and file system growth | `alibabacloud-ecs-disk-expand-diagnosis` | none; the device is visible and healthy here |
| "the instance will not come up", "it has been stuck going down for ten minutes", "I clicked restart and nothing happened", "after a reboot the mount entries fail" | instance lifecycle and boot configuration | `alibabacloud-ecs-instance-state-diagnosis` | judges only whether a wedge caused it |
| "SSH is refused", "port 22 does not answer", "the control panel login fails", "I do not know the root password" | connectivity, credentials, security group | manual connectivity handling | states whether VNC is also unusable, which distinguishes a wedge from a login problem |
| "the backup job has been running for hours", "the anti-ransomware client", "why was I billed for a performance burst", "I want a refund", "is this a mining attack" | another product's task, or a commercial or security process | manual support with the owning console | names the correlation it can prove, then routes |

## Wording for each route

Capacity:

> What you are describing is free space rather than speed. The symptoms and the fix sit in
> disk capacity handling, so I am routing this there. I am keeping one note from this side:
> a full file system and a saturated disk are different failures, and the check that tells
> them apart is included below.

Expansion:

> The disk itself was extended successfully and is visible; what did not follow is the
> partition or the file system. That is the disk expansion path, not an I/O problem, and it
> is handled by `alibabacloud-ecs-disk-expand-diagnosis`.

Instance state:

> The instance is not answering because of where it is in its lifecycle, not because of the
> disk. Restart and stop behaviour, including the normal several-minute window before an
> instance is usable again, is handled by `alibabacloud-ecs-instance-state-diagnosis`.

Remote connectivity:

> Before touching SSH or the panel, establish whether the console VNC session is also
> unusable. If nothing answers, the instance is wedged and the recovery sequence is the one
> above. If VNC works, this is a connectivity problem and it is outside this diagnosis.

Per-process attribution, when the customer asks "which process did it":

> Neither the cloud side nor the commands available to me record which process issued the
> I/O after the fact, because Linux keeps no historical per-process resource record. The
> working method is to install a history recorder such as atop, wait for the next
> occurrence, then read its log for that time window. The installation and usage steps are
> documented; I can also hand the in-guest work to manual support if you prefer.

Stall recovery, when SSH and VNC are both dead:

> The instance is wedged, so no diagnosis can be collected from it while it stays in this
> state. Recovery is yours to perform, and it is destructive if the order is wrong: take a
> snapshot, stop the database or any write-heavy service so buffered data reaches the disk,
> then restart from the console. Expect several minutes before the instance answers again,
> and treat a forced stop as a harsher operation than a normal restart.

Performance upgrade requests, when the evidence does not support one:

> Your disk never reached the ceiling computed for its own class and size, so a larger disk
> would not change what you are seeing. What the readings do show is close to its memory
> limit, which turns into disk I/O. Let us settle that first, then re-read the numbers
> before any purchase.

## Boundary with the health inspection skill

Both skills can be reached from "the disk alarm fired". The dividing line:

| Signal | Goes to |
|---|---|
| a general "check this instance", or a multi-item report where disk is one of thirteen checks | `alibabacloud-ecs-health-inspection` |
| one symptom axis - slow disk, saturated I/O, rising latency - and the question "which disk, which metric, by how much, and why" | this skill |

When a health report already flagged `cloud disk read/write limited` and the customer wants
the named disk measured against its own ceiling, that continuation is this skill's job.
When the customer only wants a broad multi-item check of the whole instance, route it away.

## Evidence gaps that must be said out loud on a hand-off

- The alarm text does not name the disk; only the per-disk comparison does. Never leave the
  customer with "a disk was limited".
- An empty monitoring series is a collection gap until the host agent is confirmed.
- A chart that shows no peak does not disprove an alert, because of the 15 second
  granularity floor.
- Anything that changes state - stopping a service, killing a process, restarting the
  instance, changing a performance level, running a benchmark - is presented as a manual
  step with its impact and its rollback, never executed here.
