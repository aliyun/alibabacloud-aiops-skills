# Channel choice and the VNC rescue path (and using them to split the problem)

A huge share of these tickets is really a *channel* question: which way are you
getting into the machine, and what does each way prove? Picking the right
channel is also the fastest way to separate "the instance is broken" from "your
client / network is broken".

## The channels, and what each one is for

| Channel | Protocol / basis | Correct use | What a success or failure proves |
| --- | --- | --- | --- |
| **RDP (mstsc)** | Windows RDP, TCP 3389 (or a custom port) | Daily remote desktop | Client-side failure here, with console access working, points at the client / local network / security layer, not the OS. |
| **Workbench (console)** | Browser-based remote desktop | Daily or emergency; no local client needed | If Workbench reaches the desktop but mstsc does not, the instance and listener are alive and the problem is on the customer side. |
| **Session Manager** | Cloud Assistant, passwordless, no open port | Emergency access without exposing 3389 | Works even when the RDP port is closed, as long as Cloud Assistant is healthy. |
| **VNC** | Direct console to the VM, independent of RDP | **Rescue login only**, not a desktop | Proves the OS/console is up regardless of RDP; a successful VNC login while RDP fails isolates the failure to the RDP stack. |

The support engineers' own line, captured in the tickets, was: **VNC is an
emergency rescue console, not a daily desktop — for normal use prefer the RDP
client or console Workbench.** VNC's low fixed resolution (customers complained
about 800x600) is a property of the rescue console, not a defect to chase.

## Using a bypass as a diagnostic

The single most useful disambiguation in this tier:

* **Console (Workbench / VNC) can enter, mstsc cannot** → the instance and the
  RDP listener are fine; focus on the client, its network, or the NLA / security
  layer. (Seen directly in tickets where the customer's third-party client hung
  at "Please wait" while the console worked.)
* **Console also cannot enter** → the instance itself is unhealthy (wedged,
  out of resources, service down). Try the gated query channel; if even that
  fails, treat it as a resource-exhaustion / manual-restart situation
  ([black-screen-resource-exhaustion.md](windows-rdp__black-screen-resource-exhaustion.md)).

## Getting the VNC entry point (the skill only fetches the URL)

`DescribeInstanceVncUrl` returns the console VNC entry for the instance. The
skill surfaces it as a manual rescue link; it does not log in, unlock an
account, or restart anything on the customer's behalf. Reference for choosing a
connection method: https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md
Workbench overview: https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md
Session Manager: https://help.aliyun.com/zh/ecs/user-guide/connect-to-an-instance-by-using-session-manager-2.md

## Workbench timeout is expected behavior, not a fault

A long-running command launched from a browser Workbench page stops when that
session times out — the page disconnecting does not mean the instance broke.
This is the explanation the tickets needed ("the workbench page does time out;
use an RDP client or run the task so it survives disconnection"). Distinguishing
"session timeout" from "cannot connect at all" keeps the operator off a false
investigation.

## Misconceptions to correct

* "VNC is broken because the picture is small / garbled" → VNC is a rescue
  console; a garbled or tiny picture is often a display-layer or client thing,
  and a plain window switch resolves some of it before assuming a fault.
* "VNC cannot connect means the instance is down" → if the console button does
  nothing but a browser/device swap fixes it, the fault was local browser /
  device, not the instance.
* "RDP client cannot connect to my Linux box" → wrong tool for the OS; that is
  an SSH area, not this skill.
