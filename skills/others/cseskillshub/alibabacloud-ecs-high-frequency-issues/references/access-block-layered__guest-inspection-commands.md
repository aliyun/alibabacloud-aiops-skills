# Guest Inspection Commands — whitelist, confirmation gate, fallbacks

Guest state (system firewall rules, listeners, kernel network parameters) is
invisible to cloud APIs: the cloud side only sees security groups and
platform POLICY configuration, while invocation readers return historical
execution records, not live state. So live guest facts come from ONE
mechanism: submitting a single whitelisted, non-mutating command through the
ECS Cloud Assistant execution action (the gated row in
[ram-policies.md](ram-policies.md)) and reading back
its output.

Ticket evidence for why this exists: in real dialogs the decisive step was
repeatedly "run these three commands inside and send screenshots" — and
customers either never pasted the output or refused access, so the diagnosis
stalled. Direct capture of the same readings removes that failure mode.

## Hard execution discipline (MUST)

1. The ONLY runnable commands are the exact command lines in
   `GUEST_CHECKS` in `scripts/areas/access_block_layered/_constants.py`. The entry tool accepts a check
   NAME, never raw command text, so nothing can be smuggled in; a check name
   outside the whitelist is refused with a non-zero exit.
2. Before ANY guest command: tell the user, in the conversation, (a) the
   exact command, (b) which instance runs it, (c) that it is a single
   non-mutating read (list state only — no rule, file, service or kernel
   change), (d) that no rollback is needed because nothing is modified. Only
   after an explicit yes, rerun with `--user-confirmed`.
3. One confirmation covers ONE command for THIS run. A new check needs a new
   confirmation. Never batch.
4. Anything mutating is class D — MANUAL guidance only, with risk warning
   and the snapshot-first reminder. This includes every one of: adding or
   deleting security-group rules, `firewall-cmd --add-port/--reload`,
   `ufw allow/disable`, raw `iptables` writes, disabling the firewall as a
   fix, `sysctl -w`, restarting instances/services, packet captures
   (`tcpdump -w`, `pktmon`), rebooting, rescue mounts, disk re-init.
5. If the Cloud Assistant agent is offline or the instance has no working
   egress, submission fails; the tool degrades and the operator switches to
   the paste-your-output fallback with the SAME single command handed to the
   customer verbatim.
6. Self-lock warning: when the failing service IS the remote channel
   (SSH/RDP blocked), first give the out-of-band console logon (VNC-family)
   fallback path BEFORE proposing in-guest work — fixing firewall rules from
   a session that cannot connect is impossible (documented lock-yourself-out
   pattern).

## Linux whitelist (all evidenced in real tickets unless noted)

| Check name | Command | Tells you |
|---|---|---|
| firewalld-state | `firewall-cmd --state` | whether firewalld runs at all |
| firewalld-rules | `firewall-cmd --list-all` | active zone; allowed services/ports/sources |
| iptables-rules | `iptables -S` | raw rule set; detects hand-added rules that firewalld overrides |
| iptables-counters | `iptables -L -n -v` | REJECT/DROP rules with packet counters (live evidence) |
| ufw-status | `ufw status verbose` | Ubuntu/Debian default policy + per-port allows and source coverage |
| listeners | `ss -lntp` | what is actually listening, incl. 127.0.0.1-only binds |
| listeners-netstat | `netstat -ntulp` | fallback listener read on old images |
| kernel-tcp-params | `sysctl net.ipv4.tcp_tw_recycle net.ipv4.tcp_timestamps` | the NAT packet-drop parameter pair (read values only) |
| recent-logins | `last -i` | real source IPs that reached the box (compare with the authorized egress IP) |

OS pick: CentOS/RedHat/Alibaba Cloud Linux family -> firewalld pair, plus
iptables pair when a conflict is suspected; Ubuntu/Debian -> ufw-status;
any -> listeners; NAT-and-ping-works-but-TCP-fails -> kernel-tcp-params;
"only some colleagues fail" -> recent-logins.

## Windows whitelist

| Check name | Command | Note |
|---|---|---|
| windows-listeners | `Get-NetTCPConnection -State Listen ...` | proposed read-side check (no direct ticket precedent) |
| windows-firewall-profiles | `Get-NetFirewallProfile ...` | per-profile default actions; mark confidence lower than Linux evidence base |

Ticket-side Windows evidence only ever reached `netstat -ano` style reads
and a class-D packet capture; when a check has no ticket precedent the
report says so instead of implying equal confidence.

## DEGRADED fallback wording

When the channel is unavailable or the user declines: state exactly which
reading is missing, why, and give the single command line for the customer
to run and paste (never screenshots of many windows — one command, one
output). Then continue every other layer; a blocked layer stays UNKNOWN,
not silently skipped.
