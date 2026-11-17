# Security Group Verification Checklist

The security group is the **most frequent cloud-side cause** of a remote-connection
failure, and simultaneously the most frequently misdiagnosed by customers, who usually
report "the firewall is not allowing it" when the actual gate is a cloud rule that is
either missing or narrower than expected.

Evidence call: `ecs:DescribeSecurityGroupAttribute` per bound group, issued by
[`../scripts/areas/remote_connection_entry/ecs_remote_connection_triage.py`](../scripts/areas/remote_connection_entry/ecs_remote_connection_triage.py).
Concept background: the security-group quick-start guide in [help-links.md](remote-connection-entry__help-links.md).

---

## The four things that must all be true

A customer can honestly say "port 22 is open" and still be unreachable, because
reachability needs **all** of these:

1. **An ingress rule exists** for the target protocol and port.
2. **The port range covers the actual port** — and the actual port is the one the guest
   listens on, which may be custom (for example `10022`).
3. **The authorized source CIDR contains the customer's current egress IP.** This is the
   single most common miss. A rule scoped to one IP or one narrow /24 stops working the
   moment the customer's ISP reassigns them, or when they try from a different network.
4. **No higher-precedence deny matches first.** A `Drop` rule at a lower priority number
   silently overrides a later `Accept`, so the allow the customer is pointing at may never
   be evaluated.

Only after all four hold on the cloud side does the guest's own iptables/firewalld get a
turn — and no cloud API can see it.

## How to read the evidence

The report lists, per checked group, each matching `Accept` rule as:

```
allow tcp <port_range> from <source_cidr> (sg <id>, prio <priority>)
```

- `NO ingress allow rule covers the target port` → verdict `SG_PORT_CLOSED`.
- `customer egress IP is NOT covered by any allow rule` → verdict `SG_SOURCE_MISMATCH`.
  Compare the printed CIDRs with the egress IP from `curl cip.cc` and show both to the
  customer; the mismatch is the evidence, not an assumption.
- Nothing printed for a group, and the group id is in the checked list → that group simply
  has no rule for this port. If several groups are bound, a rule in any **one** of them is
  enough for an allow, but a deny in any one of them can still block.
- `N/A (not collected)` → the instance was not `Running`, or the call failed; check the
  degradation log rather than concluding anything about the rules.

The egress-IP comparison only runs when `--egress-ip` was supplied. Without it the report
says nothing about source matching — it does **not** say "source is fine".

## Correlation checks the customer runs locally

| Step | Command | Reading |
|---|---|---|
| Find the current egress IP | `curl cip.cc` | Must fall inside one of the authorized source CIDRs. Run it on the machine that fails, on the same network — a VPN or a phone hotspot has a different egress IP and therefore a different answer. |
| Test the port, not the host | `telnet <public-ip> <port>` | `Connected to ...` = path open, look inside the guest. Silent timeout = dropped by a rule (cloud or guest) or no public path. `Connection refused` = something answered and nothing was listening. |
| See which stage fails | `ssh -v root@<public-ip> -p <port>` | Distinguishes connect-stage (network), handshake-stage (service or environment), and authentication-stage (credentials). |

## Manual fix guidance (customer performs every change)

This skill **never** writes, modifies or deletes a security-group rule. Output the steps
and let the customer act in the console:

1. Open the ECS console, select the correct **region** and the instance, then the
   **Security Groups** tab and its **Inbound** rules.
2. Locate the rule for the target port. If none allows it, add one: `Allow`, protocol
   `Custom TCP`, port range the SSH/RDP port in use, source the customer's egress IP (or
   their organization's CIDR).
3. Check for a deny rule that would match first, and fix the precedence rather than adding
   yet another allow — stacking another allow does not outrank an existing deny.
4. Mirror the change in the guest firewall if one is enabled: a cloud allow plus a guest
   `DROP` is still unreachable.
5. Re-test with `telnet` before retrying the client tool, so the two changes are not
   conflated.

**Scope the source narrowly.** Widening the source to `0.0.0.0/0` to "make it work"
exposes the remote-service port to the entire internet, where it will be brute-forced. The
official documentation flags this as a security risk. Recommend the customer's own IP or
CIDR, and if a static egress IP is unavailable, recommend the passwordless console
channels or session manager instead of an open port. If the customer does open it broadly
as a temporary measure, say out loud that it must be narrowed again afterwards.

## Known blind spots

- **Rule precedence between multiple bound groups** depends on group type and priority;
  the report enumerates what each group contains and lets the customer see the whole set,
  which is more reliable than a verbal summary of one rule.
- **The guest's own firewall is invisible** to every cloud API used here.
- **Enterprise security groups** and prefix-list sources are reported as returned; when the
  `source` field shows a group reference instead of a CIDR, egress-IP matching is not
  meaningful and the report says so rather than guessing.
- **A custom port that only exists in two of the three places** (client, security group,
  guest listener) reproduces a generic timeout exactly. Always confirm the three agree.
