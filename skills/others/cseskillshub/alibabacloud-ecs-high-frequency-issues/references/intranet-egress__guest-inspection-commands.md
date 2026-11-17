# In-Guest State Inspection Commands

The evidence that decides most connectivity cases lives inside the instance. No
cloud query exposes the host firewall state, the address a service binds to,
guest routes and DNS, proxy configuration, live probe results, or whether a
request arrived in the service log.

Two ways to obtain it:

| Path | Availability | Mechanism |
| --- | --- | --- |
| Manual checklist | Always | Print the commands; the customer runs them and pastes back **plain text** |
| Gated dispatch | Closed by default | `scripts/areas/intranet_egress/guest_command_gate.py` sends one command through Cloud Assistant and reads the output back |

Ask for plain text, never screenshots. Text is interpretable and quotable; a
screenshot is neither, and cases stall when the only evidence is an image.

Never ask for a password, a control-panel login or a private key in order to
obtain this evidence. If a customer volunteers one, do not use it, do not repeat
it, and advise them to rotate it.

## Why the automatic path ships closed

The dispatch gate requires the command's check group to appear in
`APPROVED_COMMAND_CLASSES` in `scripts/areas/intranet_egress/_constants.py`. That tuple is **empty**,
because the network inspection commands this tier needs are not covered by the
low-risk command list this program follows, which addresses a different
inspection domain. Until that list formally covers network inspection, the
correct behavior is to print the command and accept pasted text.

This is a deliberate capability limit, not a bug. With the gate closed, the
skill matches what a human operator does - ask the customer to run the command -
and loses nothing but latency.

## The four gate conditions

`scripts/areas/intranet_egress/guest_command_gate.py` dispatches only when **all** hold. Any unmet
condition prints the refusal reasons plus the manual checklist and exits `3`.

1. The check group is listed in `APPROVED_COMMAND_CLASSES`.
2. `--acknowledge-approval` was passed, declaring that a written low-risk
   approval covers that class.
3. `--confirm` echoes the exact `--command` text. Consent is scoped to one
   command for one run and never carries over.
4. The command text passes the guards below.

Before dispatching, the gate prints a disclosure of record: which command, on
which instance, in which region, through which Cloud Assistant command type,
what it is for, that it changes nothing, that probe commands do send packets
toward the named target, the blast radius, and the consent scope. Show that
disclosure to the operator and obtain confirmation.

## Text guards

### Side-effect and chaining veto

Any occurrence of a mutation or chaining fragment refuses the dispatch,
regardless of what else the command contains. The veto covers, among others:
file removal, moving, truncation, raw writes, filesystem creation, permission
and ownership changes, process termination, reboot and shutdown, partitioning;
service start, stop, restart, enable and disable; firewall rule insertion,
deletion, flushing and policy reset; route and policy-rule addition or deletion;
interface up and down; PowerShell state-changing cmdlets and remote or
expression invocation; shell redirection in either direction; command chaining
with `&&`, `||`, `;`, backticks, command substitution and pipes; and downloading
to a file.

The veto applies to the lowercased whole-command text, so a fragment cannot be
hidden by case.

### Leading binary

The first token must be in the accepted inspection set. Anything else is
refused. The set covers address, route and rule reporting; firewall state
listing; socket and connection listing; DNS and name resolution reporting; probe
utilities; environment reporting; and the Windows equivalents.

### Two argument policies

Which policy applies depends on the binary, via `veto_mode()`:

**Positional policy.** Every remaining token must appear in that binary's
allowlist. An unlisted token refuses the dispatch even when a listing flag is
also present. This closes the obvious bypass: a listing flag does not vouch for
a flush argument on the same command line.

Positionally interpreted binaries and what they accept:

| Binary | Accepted arguments |
| --- | --- |
| `ip` | `route`, `rule`, `addr`, `address`, `link`, `neigh`, `show`, `list`, `-4`, `-6`, `-s` |
| `nft` | `list`, `ruleset`, `table`, `tables`, `chain`, `chains` |
| `route` | `print`, `-n` |
| `netsh` | `winhttp`, `show`, `proxy` |
| `systemctl` | `is-active`, `is-enabled`, `status`, `list-units`, `show`, `--no-pager`, `--full`, `--all`, `--plain`, `-l`, `-a`, and the three firewall unit names |
| `cat` | `/etc/resolv.conf`, `/etc/hosts`, `/etc/nsswitch.conf` - nothing else |
| `iptables`, `ip6tables` | Listing and verbosity flags, `--line-numbers`, `--numeric`, `--exact`, and the table names `filter`, `security`, `nat`, `mangle`, `raw` |
| `firewall-cmd` | `--state`, the `--list-*` family, the `--get-*` family, `--zone`, `--all-zones` |

Note that `cat` is restricted to three specific files. Reading anything else,
including credential-bearing files, is refused.

**Flag policy.** Every flag of these binaries is informational, so flags are not
individually allowlisted; the whole-text veto and the high-risk flag check still
apply. This covers the socket and connection listing tools, the probe utilities
(`curl`, `ping`, `telnet`, `traceroute`, `tracert`), the name-resolution tools,
`env`, `printenv`, `hostname`, `id`, `date`, `ls`, and the Windows reporting
cmdlets.

### High-risk argument flags

Flag-policy binaries accept arbitrary arguments, so a few flags are rejected
token by token. They are not state mutations inside the guest, but they are not
state inspection either: flood mode, writing output to a file, uploading or
posting a body, remote-name fetching, and loading a configuration file.

### Bundled short-flag clusters

A denied letter bundled into a short-flag cluster would slip past an exact-token
check - an output-to-file letter hidden inside a cluster of harmless letters, or
flood mode inside a cluster. For the binaries where a short letter carries write
or traffic-shaping semantics, every cluster is decomposed and each letter
checked.

## Check groups and commands

The groups below are what `--list-accepted` prints and what the diagnosis script
attaches to a report, selected by direction. Placeholders such as a target URL,
target address or port are substituted from the probe when known.

### Linux

**listeners** - ingress and internal directions:

- `ss -antlp` - the full listener table. Confirm the port is listed **and**
  bound to `0.0.0.0`, not to the loopback address only. A loopback-only bind is
  unreachable from outside regardless of any firewall or security group rule.
- `ss -s` - socket summary.

**guest-firewall** - all directions:

- `iptables -nL -v --line-numbers`
- `ip6tables -nL -v`
- `nft list ruleset`
- `firewall-cmd --state`
- `firewall-cmd --list-all`
- `systemctl is-active firewalld nftables ufw`
- `ls -l /etc/ufw /etc/firewalld` - also look for third-party host security
  agents, which maintain their own rule sets outside the standard tools.

**routes-dns-proxy** - egress and internal directions:

- `ip route show`
- `ip rule show`
- `cat /etc/resolv.conf`
- `cat /etc/hosts`
- `env` - look for proxy variables in both cases, and for a no-proxy list.

A stale entry in the hosts file is a common and easily missed cause of a name
resolving to the wrong address or to loopback.

**live-probes-egress** - egress direction:

- `curl -v --connect-timeout 8 <TARGET_URL>` - verbose output shows whether DNS
  resolved, which address was dialed, and where the attempt stopped.
- `curl -s --connect-timeout 8 http://cip.cc` - the instance's own egress public
  address and carrier, as seen from outside.
- `ping -c 4 <TARGET_IP>`
- `telnet <TARGET_IP> <PORT>`
- `traceroute -T -p <PORT> <TARGET_IP>` - TCP traceroute, because ICMP-based
  traceroute is often filtered and misleading.

Always bound a probe with a connect timeout. An unbounded probe hangs and
produces no evidence.

**reach-arrival** - ingress direction, and the single most valuable item:

- Search the web or application access log for the customer's request. **If the
  request appears in the log, the packet reached the instance and the fault sits
  above the network layer.** That one observation ends more investigations than
  any rule read-back, and it converts an open-ended network case into a precise
  application question.

### Windows

**listeners**: `netstat -ano` (note the owning PID and check for a loopback-only
bind), `Get-NetTCPConnection -State Listen`.

**guest-firewall**: `Get-NetFirewallProfile`,
`Get-NetFirewallRule -Direction Inbound -Action Block`.

**routes-dns-proxy**: `route print`, `ipconfig /all`,
`netsh winhttp show proxy`. Note that the WinHTTP proxy and the per-user browser
proxy are configured separately and can disagree.

**live-probes-egress**: `Test-NetConnection <TARGET_IP> -Port <PORT>`,
`curl.exe -v --connect-timeout 8 <TARGET_URL>`,
`curl.exe -s --connect-timeout 8 http://cip.cc`.

**reach-arrival**: check the IIS or application log for the customer's request,
same logic as Linux.

Windows support here is limited on purpose: the cloud-side queries and the
decision tree apply unchanged, but the in-guest evidence is best collected by
the customer pasting text back.

## Dispatch and read-back mechanics

- One command per invocation. Cloud Assistant command type is selected from the
  guest operating system: a shell script type for Linux, a PowerShell script
  type for Windows. If the OS type cannot be determined, pass it explicitly.
- The command content is sent Base64-encoded with the encoding declared
  explicitly, so no default-encoding assumption can corrupt it.
- The guest-side execution has an explicit timeout.
- Read-back polls the invocation until it reports a terminal state, within a
  bounded poll budget. Output is Base64-decoded and passed through the
  credential mask before display.
- Output is truncated for display. If a listing is long, ask the customer for
  the section that matters rather than raising the cap blindly.

## Degradation

When the Cloud Assistant agent is offline, the invocation never reaches a
terminal state, permission is missing, or the customer declines, the gate
reports `STATUS: DEGRADED`, explains why, and prints the manual checklist. The
diagnosis continues from pasted text.

Name the specific missing item. "Guest evidence unavailable" is not actionable;
"the listener table for port 443 is missing, so a loopback-only bind cannot be
ruled out" is.

Do not retry with looser flags, a wider command, or a different check group in
order to get past a refusal. A refusal is the gate working.
