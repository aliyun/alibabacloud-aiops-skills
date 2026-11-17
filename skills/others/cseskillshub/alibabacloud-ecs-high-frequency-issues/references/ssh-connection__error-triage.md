# Error string triage

Customers describe SSH failures by what their terminal printed. The tables below
map that text onto a failure branch, and each branch then drives the phases in
[decision-tree.md](ssh-connection__decision-tree.md). The mapping lives in code as
`ERROR_SIGNATURES` inside [`../scripts/areas/ssh_connection/_constants.py`](../scripts/areas/ssh_connection/_constants.py);
this page is the human-readable copy of the same table.

## Quotable strings

These six strings are the ones this skill may echo back to the customer verbatim,
because they are the wording the customer's own terminal produces:

* `Connection timed out`
* `timed out`
* `Connection refused`
* `Connection reset`
* `Permission denied`
* `permission denied`

Any other string in the tables below is a **triage input only**. Use it to pick a
branch and to ask the customer to confirm what they see; do not present it as if
the customer had said it.

## Branch table

| Branch | Signatures that select it | What it actually means | First evidence to collect |
| --- | --- | --- | --- |
| `tcp-unreachable` | `Connection timed out`, `timed out`, `Operation timed out`, `timeout` | No answer came back at all. Either something dropped the packet (security group, guest firewall, an address that is not the instance) or the guest was too busy to answer. | `ecs:DescribeSecurityGroupAttribute` ingress rule for the port, then the guest firewall and socket table |
| `no-listener` | `Connection refused`, `refused` | The address was reached and a port was closed: nothing is listening there, or the service listens on a different port than the customer targets. Note: this branch is a **semantic mapping**, produced from Chinese wording such as "port 22 refuses the connection" and from instances whose SSH daemon serves a custom port. No verbatim `Connection refused` text was captured in the source conversations, so never quote it as customer input. | `ss -tlnp` inside the guest, which also reveals a custom port |
| `connection-reset` | `Connection reset`, `reset by peer`, `kex_exchange_identification`, `ssh_dispatch_run_fatal`, `DefaultAuthFuture ... IOException` | A TCP session formed and was then torn down. Typical causes: the daemon died mid-handshake, a required runtime file was removed during a security clean-up, an interception device, or a client that gives up. | guest socket table plus the presence of the login shell, the daemon binary and its helper library |
| `authentication` | `Permission denied`, `permission denied`, `Permission denied (publickey)`, `Server refused our key`, `No supported authentication methods available (server sent: publickey,gssapi-keyex,gssapi-with-mic)`, `invalid user`, `Too many authentication failures`, `Host key verification failed` | The port answered and refused the credentials or the method. This is never a network problem, and re-reading the security group wastes the session. | the four daemon options (`Port`, `PasswordAuthentication`, `PubkeyAuthentication`, `PermitRootLogin`) and the mode of `authorized_keys` |
| `session-drop` | `client_loop: send disconnect`, `Broken pipe`, "drops after a few seconds", "disconnects when idle", "every ten minutes" | Login succeeds and the link dies later. Splits into: the guest wedging under load, an idle timeout on a browser or proxy path, or client keepalive being absent. | load and memory reading inside the guest, plus the timeline against the console monitoring charts |

## Signature to configuration option, in the authentication branch

| What the customer pastes | Option behind it | Where it is confirmed |
| --- | --- | --- |
| `No supported authentication methods available (server sent: publickey, gssapi...)` | `PasswordAuthentication no` | `cat /etc/ssh/sshd_config` |
| `Permission denied (publickey)` | key-only authorisation, and the customer's key is not in `authorized_keys` | the same file, plus `ls -ld /root/.ssh /root/.ssh/authorized_keys` |
| `Server refused our key` | `PubkeyAuthentication no`, or a wrong private key, or a path SSH refuses to trust because of its mode | the same file plus the listing |
| `Permission denied, please try again` with a password the customer is sure of | `PermitRootLogin` restricting root, someone else changed the password, or the password belongs to the Alibaba Cloud account rather than the instance | the same file, then a human confirmation with the customer |
| `Connection refused` while the daemon is running | SSH listens on a custom port such as 4522 | the socket table, which shows the real port |

## Strings that must not be over-read

* `Operation timed out` on macOS and Linux is the same branch as
  `Connection timed out`; do not treat it as a DNS or client problem.
* A browser console session that ends on a regular timer is an idle WebSocket
  timeout in the browser path, not an instance fault.
* An overlay address (`100.x` from Tailscale, or a VPN pool) that times out says
  nothing about the instance; test the public address before believing the
  symptom.
* A "no response" complaint with no error text at all defaults to
  `tcp-unreachable` and requires a re-run once `--error-text` is supplied.
