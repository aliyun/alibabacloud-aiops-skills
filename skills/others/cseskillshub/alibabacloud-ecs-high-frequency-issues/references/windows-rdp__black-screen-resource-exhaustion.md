# Black screen / freeze / disconnect — the resource-exhaustion area

"Remote desktop shows a black screen", "it connects then hangs on a black
frame", "it disconnects randomly", "the desktop is a slideshow" — in this tier
these overwhelmingly resolve to **memory (and sometimes CPU) saturation of the
Windows desktop stack**, not to a network fault and not to a platform defect.
The evidence is the memory watermark and the process list; the repair is a
manual restart / spec / paging change the skill never performs.

## The pattern the reads confirm

* Sustained physical memory at roughly **85% and up**, spiking to **90%+** at
  the black-screen moments. One well-documented ticket pinned two processes —
  `explorer.exe` and an `svchost.exe` — each over 10% of RAM during the black
  window.
* A low-RAM instance running a heavy desktop OS. Windows 2025 / 11-class images
  are recommended **at least 4 GiB** just for the desktop; on a smaller
  instance the system processes alone can consume most of it, which is exactly
  the "connects then freezes" ticket.
* The same black screen is visible even through the **VNC rescue console** —
  because the problem is the OS having no memory to render, not the transport.
  That is the tell that separates this branch from a client/network issue.

## Reading the watermark

Preferred (gated, in-guest, current): `resource-top` returns the OS total/free
memory and the top processes by working set — see
[guest-query-commands.md](windows-rdp__guest-query-commands.md).

Cross-check (cloud, periodic): the CloudMonitor memory curve. CloudMonitor data
is an agent-sampled series, not an instant value; if it disagrees with the guest
reading, trust the guest and say so. Installing the monitoring agent is a guest
change (manual): https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/install-and-uninstall-the-cloudmonitor-agent-for-cpp

## The hard degrade: the guest is wedged

When the instance is exhausted enough that it is effectively unresponsive,
**even the query channel cannot return** — the same situation the engineers hit
("VNC is also stuck black, I cannot get in to inspect"). This skill then reports
`STATUS: DEGRADED` with an explicit missing-reading note rather than concluding
a cause it cannot see. The recovery is a **manual restart by the operator**,
and only after the restart can the post-hoc log reading tell you what filled
memory.

## Manual remediation (operator; never run by this skill)

State each with its risk and the snapshot-first advisory.

1. **Free memory now**: close the offending application / stop the runaway
   service from inside the desktop (Task Manager). A process kill is a guest
   write; the skill only names the top consumers it read.
2. **Restore a wedged host**: restart the instance. Full risk line to repeat to
   the customer — running work is interrupted, unsaved in-memory data can be
   lost, and **create a snapshot of every disk and wait for 100% first** (a
   restart and a snapshot are both console actions this skill does not call):
   https://help.aliyun.com/zh/ecs/user-guide/restart-instances
3. **Give the desktop headroom**: more RAM means changing the instance
   **spec** (ECS cannot upgrade only memory in place); alternatively a
   **paging file / virtual memory** increase is a guest configuration change.
   Spec change needs a restart and a prior snapshot; OS change clears the disk.
4. **Right-size the OS to the RAM**: on a genuinely small instance, a lighter
   Windows image reduces the baseline memory the desktop itself consumes;
   swapping the OS image wipes the system disk and is fully manual.

## Rules that keep the reply honest

* If the memory reading is below the threshold, do **not** blame resources for a
  black screen — fall back to the display-layer branch first.
* A black or garbled screen that clears by switching windows, or that only the
  customer's console shows while a test connection is clean, is a **display /
  channel** matter, not exhaustion
  ([vnc-rescue-and-channel-choice.md](windows-rdp__vnc-rescue-and-channel-choice.md)).
* Instance-generation / display-driver compatibility (a GPU-class ticket that
  ended in "try a 7th-generation spec" over a chat group) has **no cloud-side
  query evidence** — say it is a possibility to verify manually, never a finding.
