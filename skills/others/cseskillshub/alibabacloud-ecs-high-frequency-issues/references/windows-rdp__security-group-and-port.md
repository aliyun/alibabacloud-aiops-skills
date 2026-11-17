# Security group, port, and the cloud-vs-guest allow path

RDP reaches a Windows instance only when **both** halves of the inbound path
accept the port: the ECS security group (cloud side) **and** the Windows
internal firewall (guest side). A ticket's "port is open but still cannot
connect" almost always means one half was checked and the other was not. This
skill reads the cloud half directly and the guest half only through the gated
query in [guest-query-commands.md](windows-rdp__guest-query-commands.md).

## What the cloud read gives you

`DescribeSecurityGroupAttribute` (ingress) is evaluated for the exact port the
customer dialed. The script reports, per security group:

* whether TCP <port> has an **Accept** rule at all;
* the **source** of that accept — a customer public IP, a subnet, or the whole
  internet (`0.0.0.0/0`).

Rules are matched with the first-match-wins semantics of the console: lower
Priority number first, and a Drop beats an Accept at equal priority. An accept
is not the same as a good posture: an accept from `0.0.0.0/0` on 3389 is exactly
what lets the internet brute-force the account (see
[account-lockout-and-hardening.md](windows-rdp__account-lockout-and-hardening.md)).

## Port is not always 3389

The dialed port defaults to 3389, but non-default ports are common in this tier
(tickets used 33890 and 16909, and one instance had the RDP listener moved
entirely). Two distinct problems hide here:

* the **security group** allows 3389 but the customer connects on a custom
  port, or vice versa;
* the **Windows listener** was moved (registry `PortNumber`) to a new port while
  the security group and the internal firewall still reference 3389.

So the cloud allow for the *actual* port and the *actual* guest listener must be
reconciled. `rdp-listeners` and `rdp-port-registry` (gated reads) give the guest
truth; `DescribeSecurityGroupAttribute` gives the cloud truth.

## Manual remediation (console; the skill never applies it)

Present these as operator steps with the console entry and the risk; do not run
any of them.

1. **Narrow the source.** Replace an over-broad `0.0.0.0/0` accept on the RDP
   port with the customer's own public IP (obtain it from `https://cip.cc` /
   `https://ip.elisky.cn`). Console: ECS instance → Security Groups → Manage
   Rules → Inbound → edit the allow rule's authorization object. Reference:
   https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md
2. **Open a custom port safely.** When moving off 3389, keep 3389 allowed until
   the new port is proven reachable, then remove the old allow. In the guest,
   the RDP-Tcp / rdp-tcp `PortNumber` change requires a restart to take effect,
   and the internal firewall and the security group must both allow the new
   port. Do not change the port through this skill.
3. **Guest firewall.** If the internal firewall blocks the port (a common
   outcome after a panel such as BaoTa hardened it), the fix is an inbound allow
   inside Windows — a guest write this skill does not perform; it reports the
   read state and hands off.

## Misconceptions to correct in the reply

* "ping works, so the path is fine": ICMP reachability says nothing about TCP
  3389; a port probe is required.
* "I opened it in the console, so it must work": the console opens the security
  group only; the guest firewall and the listener are separate.
* "changing the port makes me safe": a non-default port does not replace a
  narrowed source and a strong password; brute force still finds open ports.
