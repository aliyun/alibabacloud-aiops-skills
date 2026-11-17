# Error and Symptom Signature Catalog

Customer-quotable strings mapped to a triage branch. Match on what the customer (or their
tool) literally says — never on root-cause vocabulary, which customers do not use.

This catalog is the documentation mirror of `ERROR_SIGNATURES` in
[`../scripts/areas/remote_connection_entry/_constants.py`](../scripts/areas/remote_connection_entry/_constants.py); the two must stay identical. The
script performs case-insensitive substring matching and reports every signature that hits.

Verbatim client and daemon messages in the "explicit error" groups are the documented
error set for the SSH-connection troubleshooting guide
([help-links.md](remote-connection-entry__help-links.md), "Troubleshooting when you cannot SSH into a Linux
instance"). Generic-symptom wording in group 1 comes from customer phrasing.

---

## Group 1 — No explicit error (silent failure / timeout)

These give the least information and therefore need the most collected evidence.

| Signature (as the customer says it) | id | Branch | Meaning and next step |
|---|---|---|---|
| "cannot remotely connect to ECS", "remote connection failed", "can't connect to my server", "cannot log in to the instance" | `generic-entry` | S0/S1 entry | Protocol unknown — run the full split (state, OS, security group, channels, monitoring). Do not guess. |
| "SSH connection timed out", "operation timed out", "no route to host", "network is unreachable", "destination host unreachable" | `silent-drop` | S3 network path | Packets are being dropped silently: security-group port, source CIDR that excludes the customer egress IP, guest firewall, or no public path at all. Check the security-group evidence, then have the customer run `telnet` / `ssh -v`. |
| "ping works but the port does not", "ping fails too" | `silent-drop` | S3 + local path | Split local path from cloud path: `tracert` / `mtr` for the route, `telnet <ip> <port>` for the port. A failed ping alone is weak evidence, because ICMP may be blocked while TCP is fine. |
| "the console connects fine but my local tool cannot" | `generic-entry` | S3 / S4 fork | **Not a contradiction**: the console channel does not require the customer's egress IP to be authorized, a local client does. Compare the source CIDRs, and check whether public bandwidth has been stopped for an overdue balance. |
| "public bandwidth is 0 Mbps", "pay-by-traffic instance has no address" | `silent-drop` | S5 | A zero public bandwidth ceiling makes the instance unreachable from the internet although everything inside is healthy. Read the bandwidth charge type from the instance evidence. |

## Group 2 — Explicit error: authentication stage reached and refused

| Signature | id | Branch | Meaning and next step |
|---|---|---|---|
| "Permission denied, please try again", "Permission denied (publickey)", "authentication failed", "incorrect password" | `credential` | S4 credential exit | The path works, the secret does not. Console credential flow only. Never ask for or test the customer's password. |
| "Too many authentication failures for root" | `credential` | S4 credential exit | The client offered too many keys before the right one, or the secret is wrong. Guide an explicit `-i <key>` and the console credential flow. |
| "Disconnected: No supported authentication methods available" | `credential` | S4 credential exit | Client offered no acceptable method: `PasswordAuthentication` / `PubkeyAuthentication` is off, or the key was not supplied. Guest-side `sshd_config` check, then restart the SSH service. |
| "requirement for uid >= 1000 not met by user root", "user locked due to consecutive incorrect passwords", "PAM ... authentication error" | `pam` | S4 credential exit | A PAM policy in the guest rejects the login even with the correct password. VNC in (VNC is not gated by PAM), then follow the documented PAM adjustment / unlock guidance. |
| "Host key verification failed", "possible attack on your network at this point", "man in the middle attack", "REMOTE HOST IDENTIFICATION HAS CHANGED" | `host-key` | S4 tool exit | The instance was reinstalled or its key changed, so the client's stored host key no longer matches. After the customer confirms the change was expected, remove the stale `known_hosts` entry on the **client**. This is not a server fault. |
| "no supported key exchange algorithms", "must be owned by root and not group or world-writable", "unprotected private key file" | `file-permission` | S4 guest exit | SSH refuses to run because of ownership/permission on `~/.ssh`, `authorized_keys` or host keys. Guide the documented `chmod`/`chown` corrections — the customer runs them in VNC. |

## Group 3 — Explicit error: service or environment anomaly

| Signature | id | Branch | Meaning and next step |
|---|---|---|---|
| "ssh_exchange_identification: read: Connection reset by peer", "fatal: mm_request_send: write: Broken pipe", "error: fork: Cannot allocate memory", "resource temporarily unavailable" | `resource-limit` | S4 guest exit | Process-slot or memory exhaustion (or malware interference) breaks the handshake before authentication. The decisive evidence is in `/var/log/secure` (Debian-family: `/var/log/auth.log`), which no cloud API can read. VNC in, read the log, then follow the documented process-limit guide. |
| "Bad configuration options", "fatal: Cannot bind any address", "main process exited, code=exited", "error while loading shared libraries" | `sshd-config` | S4 guest exit | sshd cannot start: a syntax error in `/etc/ssh/sshd_config`, an unavailable listen address, or damaged libraries. Validate the config from a VNC session; a service restart is needed to apply any fix. |
| "Connection refused", "port unreachable" | `refused-or-service` | S4 guest-listener exit | The packet reached the host and nothing answered: the service is down or listening on another port. Customer runs `systemctl status sshd` (on Ubuntu/Debian the unit is `ssh`) and `ss -lnt`. |
| "Could not connect to '<ip>' (port 22): Connection failed" | `protocol-mismatch` | S2/S3 split | Two candidates, in this order: an SSH client pointed at a **Windows** image (no SSH listener by default — use RDP 3389), or a custom SSH port not reflected in client and security group. |
| "error reason: WebSocket connection closed unexpectedly" (console-side tools), "the tool disconnects but cmd `ssh` works" | `tool-local` | S4 tool/local exit | Tool-side WebSocket or proxy compatibility, **not** a server fault, once the plain command line and VNC both succeed. Run the comparison matrix, then disable the local proxy/VPN, retry over a phone hotspot, or swap the client. |
| "session drops after a couple of minutes idle", "automatically exits", "disconnected after ...", "session closed" | `keepalive` | S4 tool/local exit | Idle-timeout teardown. Three places to fix, in order: server-side sshd `ClientAliveInterval 60` / `ClientAliveCountMax 10` (then restart the SSH service, or it does not take effect), client-side `ServerAliveInterval 60` / `ServerAliveCountMax 10`, and the idle timeout of any intermediate NAT or firewall. |
| "the whole instance stopped answering, every panel is dead" | `resource-limit` | S5 saturation | Whole-system wedge, not a connection-path problem. Go to the monitoring pre-screen and the snapshot-first restart guidance, then hand off `area:resource-bottleneck`. |

---

## Using the catalog

1. Feed the customer's literal error text to `--error-text`; the script reports every hit
   and appends the matching guidance to the report.
2. Where several ids hit, prefer the **most specific** group (2 or 3) over
   `generic-entry`, and let the channel comparison in
   [triage-tree.md](remote-connection-entry__triage-tree.md) S4 break the tie.
3. A signature narrows the search; it never proves the cause on its own. Pair it with the
   collected evidence, or with guest output the customer pasted back.
4. If no signature matches and no evidence discriminates, report `INSUFFICIENT` with the
   concrete missing facts. An honest "not yet determined" beats an invented cause.
