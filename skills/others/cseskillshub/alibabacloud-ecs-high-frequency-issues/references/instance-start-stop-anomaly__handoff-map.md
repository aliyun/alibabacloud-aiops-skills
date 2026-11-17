# Handoff map: recognizing what this skill must not solve

A single incident report routinely contains both an instance-level symptom and a
guest-level symptom. The divider is the boot boundary: **below it, this skill
diagnoses; above it, this skill routes.** The order is fixed — confirm the
instance state first, because that fact either ends the conversation ("the
platform stopped nothing") or legitimately keeps it here.

Match wording against the anchor table in `scripts/areas/instance_start_stop_anomaly/_constants.py` (pass the
customer's verbatim text to `--symptom`). Anchors are short and deliberately
tolerant of garbled screenshot OCR.

## Where the line sits

| Situation | Owner |
| --- | --- |
| `Stopping` / `Starting` / `Pending` dwell, start failure, boot that never reaches login, disk or mount state that changed after a reboot, the reboot required by a spec change | **this skill** |
| Instance is `Running` and something inside it is wrong — nginx, MySQL, IIS, WinRM, Docker, a control panel, a systemd unit | OS troubleshooting tier |
| Instance is `Running` but you cannot get in — SSH or RDP refused, `Access denied`, a reset password that seems not to apply, a security group missing port 22 | Connection and credential tier |
| Disk or inode space full, including fullness that is the *reason* a boot or stop stalled | `area:disk-expand-diagnosis` |
| Disk IO slow or below spec (as opposed to IO saturated enough to hang a shutdown) | `area:resource-bottleneck` |
| A resized disk that did not take effect, partition not extended | `area:disk-expand-diagnosis` |
| Snapshot cannot be deleted, snapshot billing, image derived from a snapshot | Snapshot lifecycle and billing tier |
| Spec-change pricing, downgrade or refund questions | Configuration-change and billing tier |
| Account verification blocks the console button (a code that never arrives, a deactivated phone binding, a document review) | Account and security support flow — no ECS diagnostic can bypass it |
| Simple Application Server, cloud desktop, or any non-ECS product | Out of scope: say so, and point at the owning product |

## Signature to destination

| Customer-visible signature | Candidate family | Route |
| --- | --- | --- |
| `Address already in use`, `bind() to`, `could not bind`, `mysqld got signal 6`, InnoDB flag mismatch vs `ibdata1`, `(2002) Can't connect`, WinRM or .NET Framework feature install failure, IIS role errors | Guest service or component | OS troubleshooting tier (Windows component failures to the Windows equivalent) |
| `Access denied` from a terminal client, `Login incorrect` at the prompt, "SSH server refused my password", tunnel will not connect, port 22 no longer reachable | Credential or reachability behind a booted system | Connection and credential tier |
| "the disk is full", `No space left on device`, log directory filled the volume | Capacity | `area:disk-expand-diagnosis` |
| "cannot delete this snapshot", snapshot attached to a custom image | Snapshot lifecycle | Snapshot lifecycle and billing tier |
| "verification code never arrives so I cannot reboot" | Account-side block | Account and security support flow |
| "simple application server", "cloud desktop" | Not ECS | Declare unsupported |

## Legitimate exceptions: what stays here even though it looks like a handoff

1. **Service will not start because its data disk did not mount after a reboot.**
   The failure is above the boot boundary, the cause is below it. Run the disk
   inventory versus guest mount cross-check first; only route the service part
   afterwards. This is the most common misrouting in this tier.
2. **The customer's claim that Alibaba Cloud stopped their program.** Keep it here
   long enough to answer with a fact: the instance state, whether CPU activity was
   reported, and the platform event check. Then route the service question.
3. **Offline password reset.** The reset itself belongs to the credential tier,
   but the reboot needed to apply it is a start/stop event: if the reboot then
   stalls, that stall is this skill's question.
4. **IO or memory saturation.** Route the performance investigation, but keep the
   reading here when it is the *explanation* for a transition that took 20 minutes.

## Evidence to attach when handing off

Attach what the script already produced, so the receiving tier does not restart
from zero:

- Instance id, region, and the `Status` value at a stated time.
- The health and platform-event result, including the negative ("no platform
  maintenance event in the checked window").
- The resource readings collected, with the gap named if the memory area returned
  nothing.
- The disk inventory and snapshot availability if a mount or recovery question was
  in scope.
- The customer's own verbatim error text or screenshot lines.
- Which guest readings are still missing, and which channel was unavailable.
- For a boot that eventually recovered on its own: the timeline, so "it came back
  by itself" is recorded as a fact rather than a cure.

## Boundary wording to use

For the "your platform broke my service" claim:

> Alibaba Cloud does not stop, restart or modify programs running inside your
> server. The instance-level state machine is verified above, so the failure is
> inside the guest OS; that is a different support tier and we are routing it with
> the evidence already collected.

For a state change the customer wants performed for them:

> Starting, stopping, rebooting — including forced variants — and rolling back a
> disk can only be executed by the account holder in the console. We cannot do it
> on your behalf, and neither can a support agent. Here is the exact path, the
> prerequisites, and what can be lost; tell us when it is done and we will verify
> the result.

For a stalled transition the customer wants shortened:

> While the instance shows Stopping, the operating system is releasing processes,
> flushing data to the cloud disk and unmounting filesystems. Nothing can
> intervene at that point, from any side. The forced option has to be chosen
> before the operation. Expected duration is 5 to 10 minutes, ceiling 15; we have
> recorded the current dwell time and will escalate with the evidence package if
> it passes that.
