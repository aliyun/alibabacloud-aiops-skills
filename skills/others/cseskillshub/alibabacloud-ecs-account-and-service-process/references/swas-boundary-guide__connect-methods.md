# Connection Methods: OS-to-Tool Matrix and OS-Change Warnings

Decision support for `scripts/axes/swas_boundary_guide/swas_boundary_guide.py --connect-check`.
Most "cannot connect" tickets in this tier are connection-method/OS
mismatches (customer uses Remote Desktop against a Linux server), not
cloud-side faults. Establish the OS type first -- from
`--identify` output (ECS instances expose `OSType`/`OSName`) or from the
SWAS console overview -- then apply the matrix. Sources:
[references/swas-boundary-guide__boundary-rules.md](boundary-rules.md) topic `connection`.

## 1. Matrix

| OS type | Correct methods | Cannot work | Default port |
|---|---|---|---|
| Linux | Workbench one-click login (console), any SSH client (`ssh user@<public-ip>`), Alibaba Cloud client | Remote Desktop (RDP/mstsc) -- requires a Windows image | SSH 22 |
| Windows | Remote Desktop (RDP/mstsc), Workbench (console), Alibaba Cloud client, console VNC | Plain SSH by default (only with a manually installed SSH server inside Windows) | RDP 3389 |

Mismatch verdicts printed by `--connect-check --attempted <method>`:

- `rdp` against `linux` -> expected product behavior, not a fault. Use
  SSH/Workbench, or switch to a Windows image first (data-erasing, see
  section 2).
- `ssh` against `windows` -> use RDP or console Workbench/VNC instead.
- matching method that still fails -> check firewall/security rules for the
  port and the customer's local network, then escalate with evidence (this
  skill performs no in-guest or network probing).

## 2. Switching the OS: two different products, two different entries

| Product | Console operation | Effect |
|---|---|---|
| Simple Application Server | "Reset System" (SWAS console -> Servers -> target server) | Reinstalls/replaces the system with the chosen image |
| ECS | "Replace Operating System" (ECS console -> Instances -> target instance) | Replaces the system disk with the new image |

Mandatory warnings -- state ALL THREE before the customer proceeds (the
operations themselves are performed by the customer; this read-only skill
never triggers them):

1. **All data on the system disk is erased and cannot be recovered by the
   platform.** Back up first (or confirm the server is empty, e.g. a fresh
   purchase).
2. **The public IP address does not change.**
3. **A fresh Windows image can take about 5-10 minutes on first boot before
   RDP accepts connections** (ticket wording, summary evidence) -- wait
   instead of repeatedly resetting.

Official docs (verified):

- Reset a Simple Application Server:
  <https://help.aliyun.com/zh/simple-application-server/user-guide/reset-a-simple-application-server>
- Replace the operating system of an ECS instance:
  <https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance-1>

## 3. RDP file transfer (Windows)

- To upload/download files over Remote Desktop, enable drive redirection in
  the client: mstsc -> Show Options -> Local Resources -> More -> Drives.
- The message that the current connection cannot use the file-transfer
  function indicates a client-side or local-network restriction (local
  policy or network); in a real ticket, switching the customer's local
  network resolved it. This is NOT a cloud-side configuration item -- do
  not probe the instance for it. **[summary evidence]**

## 4. Control panels (e.g. BT/BaoTa panel)

- Panel availability follows the OS: Windows images need the Windows
  edition of the panel (ticket wording: a Windows edition exists).
- A panel URL that will not load while the hosted site still works can be a
  peak-hour public-bandwidth throttling symptom on SWAS (shared-bandwidth
  QoS). Explain the product positioning (see
  [references/swas-boundary-guide__boundary-rules.md](boundary-rules.md) topic `network-access`)
  and hand in-guest panel faults to human support via `--refer`. This skill
  reads no bandwidth metrics and logs into nothing.

## 5. What this skill cannot see (honest limits)

- The customer's local network, ISP restrictions and local security policy
  (ticket-proven cause of "file function unavailable").
- In-guest state: firewall rules inside the OS, input-method/driver issues
  in a remote session, panel processes. Classify via `--refer` and hand
  off; never claim an in-guest root cause without evidence.
- SWAS instance attributes via API (no verified SWAS-side read action):
  OS type of a SWAS server comes from the customer or the SWAS console
  overview.
