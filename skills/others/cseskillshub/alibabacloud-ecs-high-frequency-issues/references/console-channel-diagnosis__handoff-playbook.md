# Handoff Playbook: Recognise, Stop, Transfer With Evidence

Most tickets on this area do not end with this skill fixing anything. The
console channel is usually the messenger: the fault lands on a different
area, and the value delivered is a clean layer determination plus the
evidence, so nobody repeats the "click VNC again" loop.

A handoff is not a failure state. Reporting `no fault found on the cloud
side` and naming the next owner is a complete answer.

## The three-part handoff, always

Every handoff message has the same three parts. Skipping the first two is
how a handoff turns into "the bot passed me around".

1. **What was collected** - the concrete readings this skill already took,
   with their values and timestamps.
2. **What is still open** - the question the evidence could not answer, and
   why not (out of the verified action set, needs an in-guest surface this
   tier does not touch, or the incident window has already passed).
3. **What needs human authority** - the operations that are never performed
   here, so the receiving owner can ask for the right thing up front.

Prefix any suggested restart, stop, disk detach/attach or offline repair
with the snapshot warning: create a snapshot of the affected disks in the
console first, snapshots bill by stored capacity, and creating and deleting
them stay the customer's own actions. This skill never creates one.

## Where each determination goes

| Determination reached here | Goes to | Why it is not this skill's |
| --- | --- | --- |
| Guest never finishes booting; damaged system libraries; a lost core-directory symlink chain; a stuck initialization service; a detached system disk | `alibabacloud-ecs-linux-os-troubleshooting` | the repair is file- and boot-level inside the guest |
| Instance stuck in a start/stop transition; a lifecycle state that blocks every operation; a pending platform event | `area:instance-state-diagnosis` | the fault is the lifecycle, the channel symptom is downstream of it |
| Logged in successfully, but nothing can be written; filesystem or inode exhaustion | the disk-capacity diagnosis skill | identification only happens here; capacity work is another tier |
| Disk throughput or latency below the instance specification | `area:resource-bottleneck` | performance is a different symptom area |
| A volume or partition change that did not take effect | `area:disk-expand-diagnosis` | expansion is its own area |
| VNC reaches the desktop but Remote Desktop refuses, or the desktop session is black | the Windows remote-desktop diagnosis skill | remote-desktop service internals are not a console-channel question |
| Anything requiring a state change: restart, stop, disk repair, offline password reset execution, filesystem check, lockout clearing, security-group edits, tunnel-software configuration, releasing a grant chain | human support, with the console path spelled out | never executed here, not even after a confirmation |

For the last two rows of an online skill name that this tier's specification
did not supply, describe the target by what it owns rather than inventing an
identifier.

## Template: boot or system-file fault (the common one)

> Layered check complete. The instance reports `Running` and its power state
> allows a console session, so the channel is not the broken part: the
> terminal opens, and the system behind it never completes start-up.
>
> Collected: power state and health status, Cloud Assistant agent presence
> and heartbeat age, CloudMonitor readings at the time of the check, your
> answers on what changed before this began, and the output you pasted from
> the console where you could reach one.
>
> Still open: which file, library or boot stage fails. That needs in-guest
> inspection and repair permissions this skill does not have.
>
> Needs a human: authorised access to the instance, and very likely offline
> repair by attaching the system disk to another instance. Before that,
> create a snapshot of the affected disks in the console - snapshots bill by
> stored capacity, and creating and deleting them stays your own action.
>
> Routing to the guest-OS troubleshooting path with the above attached.

Ask the change-history question before recommending it, not after: the two
recurring root causes in this family were both introduced by the customer
(own libraries copied into a system library directory; core directories
missing with no explanation given). Knowing what changed is often the whole
diagnosis.

## Template: lifecycle state, not a channel fault

> The console refused with a state-support message, which is the instance's
> lifecycle rejecting the operation rather than the remote-access feature
> failing. Collected: `Status` at check time, health status, and any
> scheduled platform event with its not-before time. Still open: whether the
> transition completes on its own. Needs a human if it stays stuck; a
> guest under heavy input/output load can hold a stop open for a long time,
> and forcing it is a decision for the instance-state owner, not for this
> skill.

## Template: capacity identified, cleanup elsewhere

> A session did open, so the channel worked. Collected: [the gated reading or
> the pasted output] showing the filesystem at exhaustion. Still open: what
> to remove, which is a capacity decision. Handing off to the disk-capacity
> path; nothing here deletes anything.

## Template: to human support, when the ceiling is reached

> What this skill established: [layered verdicts with their evidence and
> confidence]. What it could not: [the specific in-guest surfaces that are
> out of scope, named one by one]. What needs your authority: [restart /
> disk attach / offline reset / configuration change]. Evidence to carry
> forward: session id [value], readings at [timestamps], and the customer's
> own pasted output.

## The evidence to attach, every time

The point of handing off is that the next owner does not start from zero, so
include what this skill actually saw:

* `session_id` from the report, plus the power state, health status and any
  scheduled event with its times.
* Cloud Assistant presence, version, heartbeat age - and say explicitly when
  it was absent, because that absence is itself the strongest single clue in
  the hang family.
* Every CloudMonitor value returned with its timestamp, and an explicit list
  of the metrics that returned nothing.
* The customer's verbatim error wording, and any pasted command output,
  reproduced rather than paraphrased.
* Which conclusions are cloud evidence and which are readings of what the
  customer reported. Keep those two categories separate in the handoff text;
  "security groups were reviewed" is never true of this skill and must not be
  written.

## After the handoff

Handing off does not end the conversation. Offer the two things that make
the next incident diagnosable instead of guessed at:

* A monitoring recording that survives restarts, so a hang happening once a
  week can be attributed afterwards - a boot-time recorder is the only way to
  see a process that is gone by the time anyone looks.
* The keep-alive pattern for long jobs (see
  [channel-matrix.md](console-channel-diagnosis__channel-matrix.md)), so a dropped web session stops
  destroying work and stops being reported as a server fault.

If a restart already happened before this skill was consulted, say plainly
that the hang evidence is gone and the remaining verdicts are weaker, then
proceed. That is exactly the situation in which "check it next time it
happens, with a recorder in place" is the honest answer.
