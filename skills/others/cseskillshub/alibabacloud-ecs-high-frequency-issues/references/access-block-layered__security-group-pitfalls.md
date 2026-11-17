# Security-Group Pitfalls (the L4 trap catalog)

Every pattern below was distilled from resolved or analyzed real tickets
(identifiers are kept in the `source` fields of the script constants so the
customer-facing text stays clean).

1. **Only inbound is checked, outbound forgotten.** Enterprise security
   groups DENY OUTBOUND by default. Symptom shapes that are really an
   egress problem: console-side file transfer failing with "cannot connect
   to the remote server" (the flow uploads via an OSS temporary endpoint and
   downloads inside the instance over 443), instance cannot reach an
   external API, web panel update failures. Rule: for any
   outbound/instance-initiated failure, read the egress side and the group
   TYPE first. Widest sane fix for Alibaba service endpoints: allow the
   needed port to `100.64.0.0/10` (internal service range) instead of
   opening everything.

2. **Authorization object filled with a wrong IP.** The customer puts the
   LAN address of their modem/office NAT (100.96.x.x, 10.x, 192.168.x) into
   the source field, or fills yesterday's dynamic egress IP. The only truth
   sources: a live lookup page on the customer side, or the source IP that
   actually reached the instance in the OS log (gated `last -i` check).
   VPN/proxy users must re-check per colleague — different colleagues can
   exit different IPs.

3. **"I opened the port" vs "the port is covered".** A rule may exist and
   still not cover the flow: wrong port range, wrong protocol (ICMP test
   passes while TCP is filtered), wrong direction, higher-priority Drop,
   or a source CIDR narrower than the real client. The evaluator uses
   first-match semantics: ascending priority, Drop before Accept at equal
   priority; unmatched inbound denies, unmatched outbound allows for NORMAL
   groups and DENIES for ENTERPRISE groups.

4. **Rules authorizing other security groups or prefix lists** cannot be
   expanded by a single-group read: the report marks the layer UNKNOWN and
   asks for a console check of the referenced group's own rules and member
   instances.

5. **Multiple bound groups stack.** All bound groups' rules are evaluated
   together under the same first-match precedence; an Allow in one group can
   be shadowed by a priority-1 Drop in another. Never conclude from the
   first group alone.

6. **Same-VPC != automatically reachable.** Intra-VPC traffic still crosses
   security-group ingress (and, if the groups differ, needs an explicit
   mutual allow or group-to-group authorization) plus the peer's guest
   firewall. `No route to host` inside a VPC is usually the peer's local
   firewall REJECT, not a routing failure.

7. **ICMP passing proves little.** Security groups often allow ICMP while
   the TCP port is filtered; ping-OK + TCP-timeout is the classic partial
   opening. Conversely ping-OK + ALL-TCP-failing (one direction only, both
   sides "firewalls disabled") points past the group at guest kernel
   parameters (see the tcp_tw_recycle pattern).

8. **Least privilege with a moving target.** Customers refuse 0.0.0.0/0 on
   admin ports (rightly: brute force), then cannot connect because their
   home egress IP changes. Guidance: per-colleague /32 entries, a small
   office CIDR, or an IP-update workflow; keep ICMP and 22/3389 ranges
   minimal; never open a database port (1433/3306/5432/6379/9200/27017...)
   to the whole internet — bind to intranet ranges plus a jump IP.

9. **Product-capability boundaries (knowledge answers, not diagnosis).**
   Scheduled port opening is not a security-group feature; rule reuse across
   instances/console ports works via clone/export/template flows; special
   managed environments route port changes through their own approval
   workflow — detect such an environment from the customer's wording and
   answer with the process pointer instead of adding rules.

10. **Change discipline.** Any rule edit stays manual, is quoted with exact
    five-tuple parameters and console path, is preceded by the snapshot
    reminder (with its cost note), and — for admin-port changes — paired
    with the out-of-band logon fallback (VNC-family) so a customer cannot
    lock themselves out.

Official conceptual anchors: security-group overview and the precise
authorization quick guide listed under "Documentation index" in SKILL.md.
