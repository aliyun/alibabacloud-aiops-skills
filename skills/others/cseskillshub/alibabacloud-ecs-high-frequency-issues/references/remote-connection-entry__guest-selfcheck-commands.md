# Guest and Local Self-Check Commands (run by the CUSTOMER)

Cloud APIs can prove the network path and the instance state, but they **cannot** see what
is running inside the operating system. Every check on this page exists to close exactly
that gap, and every one of them is executed **by the customer, in their own session**, with
the output pasted back for interpretation.

> **Execution boundary.** This skill is read-only and never sends commands to an instance,
> never runs anything on the customer's computer, and never asks for a password or private
> key. The commands below are *guidance text*: present them as a list, explain what each
> one is looking for, and read the pasted result. Nothing here is executed by the entry
> script.
>
> The embedded mirror of these lists lives in `GUEST_SELFCHECK_COMMANDS` and
> `LOCAL_SELFCHECK_COMMANDS` in [`../scripts/areas/remote_connection_entry/_constants.py`](../scripts/areas/remote_connection_entry/_constants.py).

---

## Before anything: get into the instance by VNC

VNC is the only channel that is **not** gated by the security group or by software running
in the guest, which is precisely why it is the place to run these checks when SSH or RDP is
the thing that is broken. Ask the customer for the VNC link produced by the report
(`ecs:DescribeInstanceVncUrl`), and do not assume they know how to use it — walk them
through the browser connection step and note that the password can be pasted rather than
typed. The console VNC guide is in [help-links.md](remote-connection-entry__help-links.md).

If the customer's console channel is a passwordless one (Workbench or session manager) and
it is unavailable, that is usually because the Cloud Assistant agent is offline. Report it
as "use VNC instead" rather than as an agent error, and remember that the same offline
agent is also why an online password reset would fail.

## Checks on the customer's own computer

| Command | What to look for |
|---|---|
| `curl cip.cc` | Prints the local egress public IP. Compare it with the security-group authorized source CIDRs. Run it on the machine and network that actually fails: a VPN, a proxy or a phone hotspot changes the answer. |
| `telnet <public-ip> <port>` | `Connected to ...` means the path is open, so look inside the guest. A silent timeout means packets are dropped (cloud rule, guest firewall, or no public path). `Connection refused` means the packet arrived and nothing was listening. |
| `ssh -v root@<public-ip> -p <port>` | The verbose stages tell you *where* it dies: connect (network), identification and handshake (service or environment), then authentication (credentials). This is the fastest way to separate the three families. |
| `ping <public-ip>` then `tracert` / `mtr` | Route diagnosis only. A failed ping is **weak** evidence on its own, because ICMP is commonly blocked while TCP works fine — never conclude "the server is down" from a ping alone. |
| `ssh root@<public-ip> -i <key-file>` | Forcing one specific key avoids the "too many authentication failures" case, where the client exhausts the server's attempt limit by offering other keys first. |

## Checks inside the instance

| # | Command | What to look for |
|---|---|---|
| 1 | `systemctl status sshd` | `active (running)`, with the listen port in the trailing lines. Failed or inactive means the service itself is down. **On Ubuntu and Debian the unit is named `ssh`**, so run `systemctl status ssh` there — "Unit sshd.service could not be found" is the wrong unit name, not a dead service. Windows instances have no sshd at all: check the Remote Desktop listener on 3389 in the Remote Desktop settings page instead. |
| 2 | `ss -lnt` | A socket listening on `0.0.0.0:22`, or on the custom port. A listener on `127.0.0.1:22` only will never answer a remote connection no matter how open the security group is. |
| 3 | `sshd -t` | Silence means `/etc/ssh/sshd_config` parses; any complaint names the offending line. This validates the configuration and changes nothing. |
| 4 | `iptables -L -n` and `systemctl status firewalld` | Any `DROP`/`REJECT` touching the SSH or RDP port, remembering that **rule order matters**. An open security group plus a guest `DROP` is still unreachable, and this is the check no cloud API can replace. |
| 5 | `cat /var/log/secure` | The decisive evidence for handshake-stage failures: `error: fork: Cannot allocate memory` means process slots or memory are exhausted (which presents to the client as `Connection reset by peer`), and the log also shows authentication rejections and unknown source IPs. On Debian-family systems the equivalent log is `/var/log/auth.log`. |
| 6 | `df -h` | A root filesystem at 100% breaks sshd and logins silently. If disk or inode usage is the real story, hand off to the capacity skill — this skill does not diagnose it. |

## Interpreting the pasted output

| Result | Conclusion | Who fixes it, and how |
|---|---|---|
| Service inactive or failed | The remote service is down | Customer starts it from the VNC session; guidance only |
| Nothing listening on the expected port | Port changed, or listener bound to loopback | Customer corrects `Port` in `/etc/ssh/sshd_config`, then restarts the SSH service |
| Guest firewall shows a `DROP`/`REJECT` on the port | Guest firewall overrides an open security group | Customer adjusts the guest firewall |
| `sshd -t` reports a bad option or unbindable address | sshd cannot start | Customer corrects the named line, then restarts the SSH service |
| Log shows a fork / memory failure | Process or memory exhaustion | Hand off to the documented process-limit guide; then the atop guidance for the next occurrence |
| Disk or inode at 100% | Filesystem full | Hand off to the capacity skill |
| Everything healthy, security group healthy | The failing layer is the client or its network | Run the comparison matrix in [triage-tree.md](remote-connection-entry__triage-tree.md) S4 |

## Applying a fix that the customer performs

Changing `sshd_config` only takes effect after the **SSH service** is restarted — which is a
different action from restarting the instance, and confusing the two is a common dead end
("I changed it and nothing happened"). Warn explicitly that **restarting the SSH service
while connected over SSH can drop the current session**, so the customer should keep the VNC
session open as the fallback path.

Keepalive template for idle disconnects, three places at once:

- server side, in `sshd_config`: `ClientAliveInterval 60` and `ClientAliveCountMax 10`,
  then restart the SSH service to apply;
- client side, in the client's own config: `ServerAliveInterval 60` and
  `ServerAliveCountMax 10`;
- any intermediate NAT gateway or firewall, whose idle TCP timeout is outside both configs
  and outside anyone's view — if the disconnect interval is suspiciously round, that device
  is the prime suspect.

If only one of the three is changed, the symptom usually survives, and the customer will
reasonably conclude nothing was done. Say which of the three each change belongs to.
