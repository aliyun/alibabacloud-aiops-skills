# Instance state machine: what the console status actually means

Most tickets in this tier are not failures. They are a customer reading a
**transition** as a **hang**. Establish the state and the dwell time before
anything else, because that single fact decides whether the correct answer is
"wait, and here is how to do it faster next time" or "this is a real anomaly,
escalate with evidence".

## States

`Status` values returned by `DescribeInstances`:

| Value | Console label | Meaning |
| --- | --- | --- |
| Pending | Creating / preparing | Instance is being created or has just been created |
| Starting | Starting, then "operating system starting" | Hypervisor is up and the guest is booting; the phase label reflects guest boot progress |
| Running | Running | Hypervisor is running; says nothing about whether a login prompt was reached or a service came up |
| Stopping | Stopping | Guest is shutting down in an ordered way |
| Stopped | Stopped | Powered off; the disk and configuration remain |

The console shows localized labels for these. Whatever the customer calls them,
map the wording onto one of the five values above; the script reports the API
value.

## Normal transition order

    Running -> Stopping -> Starting -> Running

A console reboot traverses all four labels. A customer watching only the middle
of that sequence will report "stuck".

## Why Stopping takes minutes, and why nobody can shorten it

A normal stop or reboot is an ordered shutdown, not a power cut:

1. the operating system terminates processes and releases CPU and memory;
2. dirty pages are written back to the cloud disk;
3. filesystems are unmounted;
4. the kernel shuts down, and the instance is then started again.

While the instance is in **Stopping there is no intervention point** — not for
the customer, not for support, not for this skill. The forced-stop choice is a
checkbox offered **before** the operation starts; after the transition has begun
it is no longer available.

**Time window (the consolidated figure to quote):**

- 5 to 10 minutes is typical;
- 15 minutes is the ceiling;
- beyond 15 minutes, stop explaining and start escalating.

Load is the main variable, not a defect: an instance with saturated disk IO or
memory pressure takes materially longer to flush and unmount, because step 2 has
to wait for the disk. Say this with the CloudMonitor readings attached rather
than as an apology.

The script bands the dwell time automatically: `within-normal` (up to 10 min),
`within-ceiling` (10 to 15 min), `exceeded` (beyond 15 min), and
`unknown-elapsed` when no operation timestamp was supplied — in which case ask
the customer when the operation was issued rather than assuming.

## Normal stop vs forced stop

| | Normal stop | Forced stop |
| --- | --- | --- |
| What it does | Asks the OS to shut down in order | Cuts power at the hypervisor, equivalent to pulling the plug |
| Data still in memory | Flushed to disk | Lost |
| Filesystem | Unmounted cleanly | May need repair on next boot |
| Duration visible | Minutes (see window above) | Near immediate |
| Available during a running transition | Yes | **No** — must be chosen before |
| When to recommend | Default choice | The OS is already unresponsive and the customer accepts the data risk |

Always attach the four-point risk notice (`references/instance-start-stop-anomaly__risk-scripts-and-manual-steps.md`)
before recommending either, and create a snapshot first.

## Running does not mean usable

`Running` is a hypervisor fact. Three distinct layers sit above it, and confusing
them produces the wrong ticket:

- **Instance state** — this skill's scope.
- **Boot completed, login reachable** — VNC is the discriminator. If VNC shows a
  login prompt, the boot finished and the complaint belongs to the login or OS
  tier.
- **Service up** — entirely guest-side; route it away.

A useful rebuttal when a customer insists "the server is down": if the state is
`Running` and CPU activity is being reported, the instance is up and something
inside it is not. Conversely, "SSH does not work" is never evidence that the
instance failed to start.

## Stopped, but it will not come up

Check these in order; the first three make boot diagnosis pointless:

1. **Operation locks** on the instance (billing, security, recycling). A locked
   instance cannot be started by anyone until the owning account resolves the
   lock reason. Not a boot problem.
2. **`StoppedMode` = economical mode** (the no-charge stop option). Computing
   resources were released back to the pool, so a later start can fail when the
   zone is short of that instance type's capacity. A start failure on such an
   instance is a capacity question, not a guest question.
3. **Whether the start was ever issued successfully** — a failed console start
   returns an error message; capture its exact text, it discriminates faster than
   any query here.
4. Then the boot-failure families in `references/instance-start-stop-anomaly__boot-failure-root-causes.md`.

Related, distinct state: a **preemptible instance reclaimed** by the platform
looks like "the server stopped and never came back". Check the platform events
before treating it as a boot failure.

## Platform-side causes must be ruled in or out explicitly

The distinction that changes the answer from "wait" to "escalate":

| Query | What it proves |
| --- | --- |
| `DescribeInstancesFullStatus` | Health status of the instance and any scheduled event affecting it |
| `DescribeInstanceHistoryEvents` | Whether a downtime restart, planned maintenance, or instance-failure event coincides with the customer's operation time |

No platform event is a **finding**, not a gap: it means the stalled transition is
not explained by the platform and the cause is on the guest or configuration
side. Report the checked window alongside the negative.

Both responses carry event type and cycle-status fields whose exact enumeration
is environment-specific; quote what the API returned rather than mapping it onto
a remembered label.

## What history the platform does not keep

There is **no per-process history** of CPU, memory or IO on the cloud side. Once
an instance has rebooted, the process that caused a hang cannot be recovered from
Alibaba Cloud data — it can only be recovered if a sampler such as `atop` was
installed and enabled **before** the incident. Say this plainly when a customer
asks "which process killed my server yesterday", and give the pre-deployment
guidance instead of a promise.

Historical block and file data that must survive an incident comes from snapshots;
see `references/instance-start-stop-anomaly__risk-scripts-and-manual-steps.md`.
