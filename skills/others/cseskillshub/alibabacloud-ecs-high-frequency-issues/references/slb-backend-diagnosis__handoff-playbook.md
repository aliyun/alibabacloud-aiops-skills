# Boundary Recognition and Handoff Playbook (Scenario E)

Scope: tickets that MENTION a load balancer but whose main demand belongs to
a neighboring tier. This skill's value here is fast recognition, the limited
read-only facts it can still contribute, and a clean handoff -- not
diagnosing the neighbor's domain.

Handoff target names below are CANDIDATE tier names that follow the ECS
naming family; the batch tier list was not available for verification when
this module was written, so treat each identifier as unconfirmed. State the
handoff DIRECTION (the capability the next owner provides) rather than
asserting an unconfirmed skill identifier to a customer. When a named sibling
is unavailable or unconfirmed, hand off to a human ticket with the same
evidence bundle.

## Recognition table

| If the main demand is... | Signals in the customer wording | Hand off to (candidate tier name, unconfirmed) | Facts this skill may still contribute (read-only) |
|---|---|---|---|
| Port reachable / blocked from outside, security-group or firewall effect, "who answered my probe" | "nc says connected but tcpdump shows nothing", deny rules, exposure concerns | `area:access-block-layered` | `ecs DescribeInstances`: instance state + which security groups are bound (initial screen only) |
| Website unreachable / slow with NO load-balancer link involved | no LB in the path, domain/DNS/backend app issues | `area:web-inaccessible-slow` | none needed; state the boundary |
| Public bandwidth / traffic volume attribution | "outbound traffic spiked", "is a script uploading?" | `area:network-quality-bandwidth` | `cms DescribeMetricLast` latest datapoints as a CLUE only (no attribution conclusion); `vpc DescribeEipAddresses` EIP bandwidth/status |
| Bill growth / EIP retention fees / billing attribution | "why was I charged", "bill grew this month" | `area:billing-attribution-bill-check` | `vpc DescribeEipAddresses`: is the EIP bound to a load balancer (binding fact behind rule `EIP-ON-SLB-FEE`) |
| Instance CPU/memory performance, burstable credits | "CPU 100%", "one instance busier than the others" | `area:resource-bottleneck` | `ecs DescribeInstanceTypes` ceilings (best-effort); instance type/state |
| SSH / remote connection stability | disconnects, login failures (LB already ruled out) | `area:ssh-connection` | none; state that this tier has no LB-related finding |
| Instance spec change / purchase restrictions | "cannot select target family" | `area:spec-change-purchase` | zone spread fact when the ticket also asks about multi-zone LB architecture (that sub-question stays here) |
| RAM permission errors on a separately managed platform's resources | `NoPermission.RAM`, resources invisible to the current account | `area:ram-policy-diagnosis` (and the platform's own ticket channel when the resources belong to a separately managed e-commerce cloud platform) | none; cross-account resources are invisible to this skill's queries -- say so honestly |
| Container / DNS resolution behavior pointing at an ALB private IP | container reuses host DNS, unexpected source IP ranges | `area:vpc-connectivity-check` | none; the ALB is only the resolution target, not the problem owner |
| Scaling group configuration itself (rules, images, schedules) | scaling group mechanics | `the Auto Scaling (ESS) console and its own product support` | see `references/slb-backend-diagnosis__ess-lb-integration.md` for the LB-attachment boundary |
| Host-side certificate installation with no LB involved | install/renew on the server itself | `area:ssl-cert-deployment` | see `references/slb-backend-diagnosis__listener-cert-placement.md` when a listener exists |

## Fixed calibers (all ticket-sourced; safe to relay verbatim)

- Host-machine (hypervisor) monitoring is NOT exposed to customers; platform
  hardware checks require human/backend confirmation (ticket T-7D518A67).
- `nc` completing a connection only proves the TCP three-way handshake
  finished; it does NOT prove any service answered. With zero packets in a
  simultaneous capture and no listening process, escalate the
  who-answered-my-SYN question to humans (ticket T-3C6E3D78).
- An EIP bound to a load balancer still incurs the EIP configuration fee;
  the fee is waived only for an EIP directly bound to a VPC-type ECS/ECI
  instance within the account quota of 2000. Rule reference:
  https://help.aliyun.com/document_detail/197103.html#cde7d1a2df7z4
  (FAQ link quoted from a real ticket conversation; re-verify the anchor
  before citing it to a customer.)
- ECS public traffic cannot be capped platform-side; advise monitoring
  alarms instead (ticket T-1D4D04B3).
- Resources of a separately managed platform (its own accounts, its own
  permission checks) are invisible to this account's queries; route the
  customer to that platform's own ticket channel (ticket T-1D79BB54).

## Handoff output format (MANDATORY)

When handing off, the reply MUST contain, in order:

1. The read-only checks already completed and their results (evidence
   list, including `[WARN]` degradations -- the entry script prints it).
2. The recognized main demand and the target tier from the table above.
3. The exit: the handoff direction described by the capability the next owner
   provides, plus a human ticket when no confirmed sibling applies or the
   platform side must confirm. Quote a sibling skill identifier only when it
   has been confirmed to exist for this deployment.
4. What this tier concluded (if anything) about the LB<->backend link, so
   the next handler does not repeat it.

## Security notes

- Never ask the customer to authorize remote login for this skill, and never
  accept panel/instance passwords; if secrets were already sent in the
  ticket, advise immediate rotation (ticket T-46370FEF).
- Port-exposure hardening advice (converge public exposure) has a verified
  doc: https://help.aliyun.com/zh/ecs/user-guide/public-network-exposure-risk-of-converged-ecs-instances-v1.md
- Public bandwidth configuration background (verified doc):
  https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-configuring-public-bandwidth.md
- EIP association facts background (verified doc):
  https://help.aliyun.com/zh/ecs/user-guide/associate-or-disassociate-an-eip.md
