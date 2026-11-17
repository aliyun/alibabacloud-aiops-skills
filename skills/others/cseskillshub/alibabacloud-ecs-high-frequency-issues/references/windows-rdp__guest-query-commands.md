# In-guest query commands: whitelist, confirmation gate, refusal rules

Cloud APIs cannot see what is inside the guest: the internal firewall state,
the actual RDP listener port, whether the local account is locked, the current
session count, and the TerminalServices error log all live only in the
instance. This skill reaches them over Cloud Assistant, but the transport used
to run something inside a customer machine is a **write-class** capability, so
it is fenced by hard rules.

## The permission model in one line

Cloud query reads run automatically. Executing anything inside the guest goes
through exactly one gated action — the ECS Cloud Assistant command dispatch
(product `ecs`, action `RunCommand`) — whose **payload is always a query, never
a change**. Read-back uses `DescribeInvocations`, which only returns past
execution output, so a fresh command must be dispatched for a current reading.

## Confirmation gate (enforced in code, not just prose)

For every guest item the operator asks for, `scripts/areas/windows_rdp/rdp_diagnose.py`:

1. Prints the disclosure **before** running anything: the command name, its
   full text, the target instance, that it is non-mutating, and that there is
   nothing to reverse because it writes nothing.
2. Does **not** dispatch until the operator passes `--confirm confirm:<name>`.
   Without the token the script returns the command as a proposal and a
   `STATUS: DEGRADED` with the exact confirmation string to use.
3. Accepts **only** one of the whitelisted command names below and **one at a
   time**. A name outside the whitelist is refused outright with `CommandNotWhitelisted`.
4. Refuses to dispatch at all when Cloud Assistant is not ready, or when only a
   bare public IP (not an instance id) was supplied, instead of silently
   degrading into an unusable call.

This is why the confirmation token must equal the specific command name: it
proves the operator acknowledged *that* command for *that* instance, and it
keeps a broad standing approval from being reused for a different read.

## The whitelist (non-mutating only)

| Name | What it reads | Payload type |
| --- | --- | --- |
| `rdp-services` | TermService / UmRdpService / SessionEnv / RemoteRegistry state and startup type | PowerShell |
| `rdp-listeners` | Local TCP ports in the Listen state (find the real RDP port) | PowerShell |
| `rdp-port-registry` | Configured RDP listener port (PortNumber, read-only registry query) | PowerShell |
| `rdp-firewall` | Internal firewall profile state and the Remote Desktop rule group (show only) | PowerShell |
| `rdp-account` | Local account enabled state and the local lockout policy | PowerShell |
| `rdp-lockout-events` | Recent account-lockout security events (id 4740) | PowerShell |
| `rdp-sessions` | Current console and RDP sessions | PowerShell |
| `rdp-eventlog` | Recent TerminalServices-LocalSessionManager entries | PowerShell |
| `rdp-nla` | RDP-Tcp security layer and NLA values (read-only registry query) | PowerShell |
| `resource-top` | OS memory watermark and the top processes by working set | PowerShell |

The exact command text for each name is defined once, as constants, in
[../scripts/areas/windows_rdp/_constants.py](../scripts/areas/windows_rdp/_constants.py) (`GUEST_QUERY_WHITELIST`),
and is what the disclosure prints and the dispatch sends. Every payload uses
`Get-*`, `Format-Table`, `Format-List`, `Select-Object`, `Sort-Object`,
`netsh advfirewall show`, `net accounts`, `query session`, or `Get-WinEvent` —
list and read verbs only.

## Commands that are refused (and given as manual steps instead)

Anything that changes guest state is out of the whitelist and is never
dispatched, even with confirmation. When a fix needs one of these, the skill
outputs the console step + risk + snapshot advisory instead:

* unlock an account, change a password, or edit the lockout policy;
* enable/disable a firewall rule or open a port inside the guest;
* change the RDP port (writing the registry `PortNumber`), or the NLA /
  SecurityLayer values;
* stop or start a service (TermService and friends), or restart the instance;
* kill a process, install an agent, apply Windows updates, or add paging file.

## Manual fallback when the automated channel is unavailable

If Cloud Assistant is not ready, the dispatch permission is not granted, or the
guest is wedged so even a query cannot return, the skill stops collecting
guest-side facts and hands the operator a checklist to run themselves and paste
back. It never reports a guest-side conclusion without a real reading behind it.

Client-side evidence to request (the customer runs these on their own machine;
the skill never runs them):

* the exact `mstsc` error text / code and a screenshot;
* `telnet <ip> <port>` and a `tracetcp` port probe (the probe method the
  engineers used is documented at https://developer.aliyun.com/article/59067 );
* `tracert <ip>` from the failing network and from a phone hotspot;
* their own public IP from `https://cip.cc` or `https://ip.elisky.cn`.
