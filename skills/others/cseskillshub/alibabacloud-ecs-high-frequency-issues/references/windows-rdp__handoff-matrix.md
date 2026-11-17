# Hand-off matrix — recognize, route, do not implement

This tier covers **only** the three Windows RDP symptom areas: cannot connect,
black screen / freeze / resolution, and authentication / certificate / NLA
errors. Many tickets that open on "remote desktop" actually belong to another
area, and several "fixes" seen in tickets are write operations this RO+G skill
must never run. The rule is the same in every row: **recognize the trigger,
state the boundary, hand off; do not diagnose or repair the other area here.**

## Product / OS mis-routing (catch at Layer 0)

| Customer wording | Real area | Route to |
| --- | --- | --- |
| "my cloud desktop / Wuying / cloud-desktop personal edition" (one ticket was mis-filed here three times across products) | different product | the matching product's console / support, after confirming it is not an ECS instance |
| "lightweight / Simple Application Server" firewall pages come up | different product | Simple Application Server console; its firewall, not an ECS security group |
| "the RDP client cannot connect, but it's a Linux server" | wrong protocol for the OS | Linux SSH / Workbench diagnosis (that skill's name is still being fixed in this batch) |

## Other-symptom areas (recognize after RDP is cleared or while routing)

| Customer wording | Real area | Route to |
| --- | --- | --- |
| "data disk is full", "No space left on device", "OOM", "inodes", "too many small files" | capacity / inode | the disk capacity & inode diagnosis skill |
| "I expanded the disk but the partition is still small" | expand effectiveness | area:disk-expand-diagnosis |
| "the instance won't start / stuck restarting / a reboot never finished" | instance lifecycle state | area:instance-state-diagnosis |
| "the disk is slow, IO is high" | block storage IO | area:resource-bottleneck |
| "instance is fine, my website/app is wrong" | workload / application | out of ECS connectivity scope |

For any of these, run the hand-off sentence from `scripts/`'s report; add the
one thing that is still this skill's job: confirm whether the RDP failure was
its own problem or just a side effect of the other area (for example a full
data disk causing OOM that then makes RDP/VNC black — the fix is on the
capacity area, plus a manual restart).

## Final fixes that are all write operations (never executed here)

The tickets usually close with an action this skill only *describes* with the
console entry + risk + "snapshot first" advisory:

| Ticket's final fix | Why this skill does not do it |
| --- | --- |
| unlock the account / reset the password | credential write; see [account-lockout-and-hardening.md](windows-rdp__account-lockout-and-hardening.md) |
| open 3389 / a custom port in the security group or guest firewall | network write; see [security-group-and-port.md](windows-rdp__security-group-and-port.md) |
| restart the instance (recover a wedged host, apply a reset password) | lifecycle write; see [black-screen-resource-exhaustion.md](windows-rdp__black-screen-resource-exhaustion.md) |
| increase memory via a spec change / add a paging file / change the OS image | spec or OS change; destructive or requires restart |
| apply Windows updates / fix a driver | guest write |

## Cloud-side-uncontrollable (explain, do not chase)

* Mainland <-> overseas public path quality —
  [cross-border-network.md](windows-rdp__cross-border-network.md).
* The customer's own device, local network, browser, or third-party RDP client —
  the skill proves the server side is healthy and returns the client evidence
  checklist; it cannot reach the customer's laptop.

## Billing / commercial

Snapshot charges, per-usage switch-off, refund, downgrade: hand to the billing
flow / human. Record a RequestId (e.g. an "instance sign-in failed, RequestId
..." console error) for platform follow-up rather than trying to resolve it.
