# Security groups: how the rules really resolve, and what to change by hand

Most "I am under attack" and "my port is blocked" tickets are settled here,
because rule evaluation is pure arithmetic and is invisible to the eye when a
group has dozens of rules. This skill reads the rules and prints the evaluation;
it never edits a rule.

## 1. Evaluation order

For one flow (direction, protocol, port, peer address) the platform walks the
matching rules in this order:

1. `Direction`: `ingress` for traffic arriving at the instance, `egress` for
   traffic the instance sends out. A rule in the wrong direction explains nothing
   about the other one.
2. `IpProtocol`: `TCP`, `UDP`, `ICMP`, `GRE` or `ALL`. `ALL` covers TCP checks.
3. `PortRange`: written `low/high`, for example `80/80` or `0/65535`; `-1/-1`
   means every port and belongs to an `ALL` or `ICMP` rule.
4. Authorisation object: a CIDR (`10.0.0.0/8`), a single address, another
   security group id, a prefix list, or an IPv6 CIDR in `Ipv6SourceCidrIp`.
5. `Priority`: **1 is the strongest, 100 the weakest.** The first matching rule
   in ascending priority decides the outcome; at equal priority a `Drop` wins
   over an `Accept`.
6. If nothing matches: ingress is denied, egress is allowed for a normal group.

Two consequences that produce wrong answers constantly:

* An `Accept` on 80 at priority 110 does nothing if a `Drop` from `0.0.0.0/0`
  covers 80 at priority 1. Customers see "the rule is there" and conclude the
  platform blocked them. Adding a stronger accept is not the fix; the overriding
  drop has to go, or its priority has to be raised above the deny.
* A missing accept is indistinguishable from a block at the client: both look
  like a reset or a timeout. So a non-standard service port (a game port, an
  admin panel port) with no ingress rule is a configuration gap, not an attack.

## 2. Known false-attack patterns

| Pattern | What the customer reports | What the rules show | Manual fix |
|---|---|---|---|
| Deny shadows allow | Site unreachable for everyone after someone "added a block rule" | `Drop` with a lower priority number than the `Accept` on the same port | Remove the broad drop, or narrow it to one address and keep its priority weaker than the business accepts |
| Missing business-port accept | "Port 7000 is blocked" | No ingress rule for that port at all | Add one accept for the exact port and protocol; add TCP and UDP separately if the service uses both |
| Console sign-in fails, SSH from elsewhere works | "Browser SSH closes immediately" | Port 22 accepted for the customer's own address but **not** for `100.104.0.0/16` | Add `100.104.0.0/16` on 22 if browser and Workbench access must keep working |
| Only one client is filtered | "Only I cannot open it, colleagues can" | Accepts exist but none authorises that client's egress address | Compare the client's current public address (it changes on VPN or mobile networks) and widen or re-point the authorisation object |
| Defence bypassed | "WAF is paid for and useless" | Traffic enters through an EIP bound straight to the instance while the proxied defence still references the old address | Make one entry point: put the traffic through the defence product and stop exposing the origin address |
| Uneditable rule | "I cannot fix the rule, the console refuses" | Service-managed rules carry an edit restriction (for example a floor below which they cannot be modified) | Add a new narrower rule as the immediate mitigation, and have the redundant rules cleaned up by a human with the owning role |
| Exposure inviting the abuse | "Someone is brute forcing me" | 22, 3389, 6379, 3306, 1433, 445, 5985 or 9200 accepted from `0.0.0.0/0` | Convert to an allow-list of your own egress address; a public datastore port is how a host ends up attacking others |

## 3. Blocking a specific abusive address, safely

Adding a `Drop` for one source address is legitimate and is what customers ask
for. Do it with these cautions stated out loud:

* Prefer an allow-list for administration ports over an ever-growing list of
  drops; per-address blocking never wins against many sources.
* Confirm the address is really the abuser, from access-log counts for the
  incident window, not from one error. Blocks placed on shared egress addresses
  or on search and AI crawlers take out real traffic.
* A `Drop` added at a strong priority can shadow the very accept that keeps the
  site up. Re-read the evaluation after the change.
* Blocking inside the guest's own firewall, or in a panel's security page, adds a
  second place where "why can I not connect" is answered, and is invisible to
  this skill's checks. Record any such change in the evidence pack.
* There is no malicious-address reputation feed exposed to this skill. A
  shortlist of top talkers is arithmetic on the customer's own log, and the
  decision to block stays with the customer.

## 4. Manual steps (guidance this skill prints, never runs)

1. Open the security group of the instance in the console of **that region**;
   the region in a copied URL is not necessarily the instance's region.
2. In the ingress tab, read rules in priority order and find the first one that
   matches the flow in question.
3. Add or correct one rule at a time, then retest from the client, before
   touching anything else.
4. Keep management ports off the public internet; publish only 80/443 (plus the
   mail submission port you actually use).

References: getting started with security groups, the per-scenario rule examples,
the Windows high-bandwidth investigation walkthrough, and the consolidated
hardening checklist. URLs are printed in the report header of every run and are
listed in `references/attack-blackhole-diagnosis__evidence-checklist.md`.
