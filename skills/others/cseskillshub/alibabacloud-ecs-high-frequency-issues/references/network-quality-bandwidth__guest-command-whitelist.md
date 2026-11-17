# Guest command whitelist: what may be suggested, and what is refused

This skill is read-only and has no channel into the operating system, so nothing on this page is
ever executed by the skill. The whitelist governs which measurement commands `guide` is allowed to
**print** for the customer to run themselves. For how to request the reading and how to record where
it came from, see [customer-side-probes.md](network-quality-bandwidth__customer-side-probes.md).

## Hard rules

1. Nothing is executed. The `guide` subcommand prints command text and exits; it makes no cloud call
   and opens no session.
2. Only `ping` and `mtr` may be printed, and only in the shapes below, assembled by
   `scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py` from validated numbers and a filtered destination string.
   There is no free-form option, so a whitelisted tool cannot be turned into something else.
3. A command outside the whitelist is never printed for the customer to copy, and never "just this
   once". The answer becomes manual guidance in the customer's own console or shell, with the risk
   named.
4. Installing anything is a human action, always. No package, archive, compiler, or agent is fetched,
   built, or recommended as something this skill performs, even when a ticket shows an engineer doing
   exactly that.
5. No credentials are involved. Never ask for, accept, store, or echo a password, key, token, or
   control panel login. If the customer already pasted one, advise once that they change it outside
   the ticket and stop quoting it.
6. Every pasted reading must carry the wall clock time it was taken, to the minute. A reading that
   cannot be placed in the incident window cannot be compared with a cloud-side series.

## Whitelisted shapes

| Tool | Printed as | Options the script accepts | Bounds |
| --- | --- | --- | --- |
| `ping` | `ping -n -c <count> [-i <interval>] [-s <size>] <target>` | `--count`, `--interval`, `--packet-size` | count 1 to 50, interval 1 to 5 s, size 56 to 1472, at most 4 sizes, each printed as its own command |
| `mtr` | `mtr -r -n -c <count> [--tcp -P <port> \| --udp] <target>` | `--count`, `--tcp-port`, `--udp` | count 1 to 100, port 1 to 65535 |

The target must be one hostname or address matching a conservative pattern; spaces, shell
metacharacters, redirection, command separators, and extra arguments are rejected before anything is
printed. Both tools report and exit; neither writes a file.

Typical uses that fit these shapes:

- reverse path from the instance to the customer's public IP, printed once instead of asking twice
  for a screenshot of the same server-side test;
- `--tcp-port 443` when only HTTPS fails, contrasted with the ICMP default;
- `--packet-size 80,200,1400` to find the size at which transfers start failing.

## Refused, with the replacement answer

| Requested | Why it is not printed | What this skill outputs instead |
| --- | --- | --- |
| `iftop`, `nload`, `vnstat`, `nettop` | not whitelisted, and most need installation | manual steps: the customer logs in and runs it during the high bandwidth moment; the Linux traffic load guide and the Windows high bandwidth guide in [bandwidth-facts.md](network-quality-bandwidth__bandwidth-facts.md); plus the standing fact that historical traffic cannot be attributed afterwards |
| `ss`, `netstat` | not whitelisted | manual step, and the note that a connection count is not the same as a bandwidth saturation reading |
| `ip link show`, `ip addr`, changing MTU | reading is not whitelisted, changing is a configuration write | ask the customer to paste the interface dump; state that adjusting MTU is their configuration decision, with the risk to tunnel interfaces named |
| `traceroute` | not whitelisted, and `mtr` covers the need | the whitelisted `mtr` form, or the customer's own traceroute pasted back |
| `tcpdump`, any capture to a file | writes to disk and can capture payload, so it is not a measurement-only command | a manual step with an explicit scope, or a handoff; never automated |
| `top`, `free`, `atop`, `iostat` | compute, memory, or storage areas | hand off per [handoff-map.md](network-quality-bandwidth__handoff-map.md); the customer runs them if the other area needs evidence |
| `curl`, per-resolved-address comparison | issues requests with side effects and payload | describe the test and let the customer run it; record that this is why the per-node comparison is not automated |
| `kill`, `systemctl`, `reboot`, service restart | state changing | console steps plus the risk, and a backup recommendation as a human action; never executed |
| `iptables`, `nft`, `tc`, `sysctl` | configuration or rate limiting changes | the security or system administration owner, as a human action |
| `rm`, `mv`, `>`, `truncate`, `dd`, log trimming | destructive or data writing | refused outright; guidance only |
| `wget`, `yum`, `apt`, `dnf`, `make install` | installation, which is a write | documented manual steps, including for the historical profiler mentioned in tickets |
| Database or panel introspection, such as a process list query | application state, out of scope | application operations handoff |
| Shell history or access log parsing | reads customer data files, out of scope | ask the customer to paste the specific lines that matter |

## Windows

No Windows in-guest command was verified for this tier, so nothing is printed for it. The supported
answer is the graphical one: the customer opens the performance view or resource monitor, sorts
network usage per process during the incident, and shares the screenshot. Say plainly that the
command path is Linux only in this version rather than improvising a PowerShell command.
