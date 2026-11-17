# Security Group Rule Read-Back

How to interpret `ecs:DescribeSecurityGroupAttribute` output for a connectivity
probe. The point of reading the rules back is to establish **what is in effect
right now**, because customer recollection of their own rules is unreliable in
both directions: "I already deleted it" and "I set it to allow everything" are
both frequently wrong.

## Rule fields that matter

| Field | Values seen | Why it matters |
| --- | --- | --- |
| `Direction` | `ingress`, `egress` | Selects which probe the rule belongs to. A rule in the wrong direction is invisible to that probe. |
| `Policy` | `Accept`, `Drop` | Drop is silent: no rejection is sent, the packet just disappears. |
| `IpProtocol` | `tcp`, `udp`, `icmp`, `all`, `-1` | `-1` and `all` mean every protocol, so such a rule matches any probe. |
| `PortRange` | `443/443`, `1/65535`, `-1/-1` | `-1/-1` means every port. `1/65535` also spans every port. |
| `SourceCidrIp` / `DestCidrIp` | CIDR or `0.0.0.0/0` | Ingress rules carry the source; egress rules carry the destination. |
| `Priority` | `1` (highest) to `100` | A lower number wins. Priority is what makes one rule shadow another. |

## Evaluation model

First match wins, ordered by priority; on equal priority an explicit `Drop` is
evaluated before an `Accept`. The script sorts candidate rules by
`(priority, drop-before-accept)` and reports the first one as the matched rule.

When no rule matches:

- **Ingress defaults to deny.** Unmatched inbound traffic is dropped silently.
  This produces a timeout, and never an immediate connection reset.
- **Egress defaults to allow** for a normal-type security group.
- **Enterprise-type groups differ in both directions.** The group type is
  surfaced in the report for this reason. Never declare the cloud side clean
  without checking the type.

## Matching a probe to a rule

A rule matches a probe when direction, protocol and port all agree, and the
remote CIDR either spans the whole space or contains the concrete remote
address.

Three-way classification, because a two-way answer overclaims:

| Class | Condition | Use |
| --- | --- | --- |
| `match` | Direction, protocol and port agree, and the remote CIDR is `0.0.0.0/0`, `::/0`, empty, or contains the known remote address | Drives the verdict |
| `maybe` | Protocol and port agree, but the rule pins a specific remote CIDR and the concrete remote address was not supplied | Reported as a candidate. **Never drives the verdict.** |
| `no` | Anything else | Ignored |

The `maybe` class is the honest answer when `--client-ip` or `--target-ip` is
missing. A rule pinned to `203.0.113.0/24` might be the reason, or might be
irrelevant; without the remote address there is no way to tell. Report the
candidate and ask for the address.

Port normalization: an any-port range collapses to the probed port when one is
given, so a wildcard rule can be compared directly. A malformed or absent range
is treated as spanning every port, which is the conservative reading.

## Finding 1 - The blanket egress drop

The shape to look for:

```
Direction  : egress
Policy     : Drop
IpProtocol : -1        (or all)
PortRange  : -1/-1     (or 1/65535)
DestCidrIp : 0.0.0.0/0 (or empty)
```

One rule of this shape blocks every outbound connection from every instance in
the group. At priority `1` it also shadows every other egress rule, so a
customer who later adds allow rules sees no effect and concludes there is a
propagation delay. **There is no propagation delay**: a rule takes effect once
it is added. When a customer reports "I set it to allow everything and it still
fails", look for a higher-priority blanket drop before anything else.

This shape arrives in practice from copy-paste and from tool-generated rules.
The fix is a console change owned by the resource holder; this skill reports the
rule and never edits it.

Because one security group can be attached to many instances, a blanket drop
explains a fleet-wide outage. When the customer says every instance in a region
lost internet access at once, read back the shared group first - one query
covers the whole fleet.

## Finding 2 - Missing ingress accept

No ingress rule accepts the probed protocol and port. Unmatched inbound traffic
is dropped silently, so the client sees a timeout rather than a refusal.

Distinguish this from a refusal, because they point at different layers:

| Client observes | What it means |
| --- | --- |
| Timeout, no answer | Dropped somewhere on the path: security group, host firewall, or a dead far end |
| Immediate reset | Something answered with a RST: a middlebox, or a host that rejected the connection |
| Connection refused | The host was reached and no service accepted that port - application layer |

## Finding 3 - The ICMP false negative

ICMP is very often not permitted, so **a failed ping is normal and proves
nothing about TCP reachability**. Two misdiagnoses follow from ignoring this:

- "Ping fails, therefore the instance has no network." Wrong: the port may work
  fine.
- "Ping works, therefore the port works." Wrong: ICMP and TCP are separate
  rules, and an ICMP accept says nothing about port 443.

The script reports ICMP acceptance in both directions for every group so the
question can be settled from evidence instead of from a ping. When the error
class is a timeout and no group accepts ICMP, say explicitly that the failed
ping was expected.

Conversely, permitting ICMP is sometimes needed so that path measurement tools
can work at all. Recommending that is a console change for the resource holder.

## Finding 4 - Priority shadowing

Rules are evaluated by priority, so a permissive rule at priority `100` is
meaningless in the presence of a Drop at priority `1`. When a customer insists a
rule is correct, check what outranks it.

Report the matched rule's priority alongside its text, so the shadowing is
visible rather than implied.

## Finding 5 - Rules pinned to a stale CIDR

An ingress rule pinned to a specific source CIDR silently stops working when the
client's address changes: a different office, a different carrier, a mobile
network. The rule is "correct" and the traffic still fails. This is why
`--client-ip` matters, and why a `maybe` classification should prompt for it
rather than being reported as a pass.

## What rule read-back cannot tell you

State these limits instead of papering over them:

- Whether the customer's **host** firewall permits the traffic. The security
  group and the guest firewall are independent layers, and either can drop the
  packet. Guest evidence comes from the inspection checklist.
- Whether a service is actually listening, and on which address. A service bound
  to the loopback address only is unreachable from outside no matter what the
  rules say.
- Whether the group type changes the default verdict. Confirm the type in the
  console.
- Why a correct configuration still fails. When the rules are clean, say so and
  move to guest-side and external evidence rather than inventing a rule problem.

## Reporting rules to a customer

Quote the rule as read back, including direction, policy, protocol, port range,
remote CIDR and priority. Name the security group ID. State what the rule does
to the specific probe, not what it does in general. Then give the console path
for the change and stop - this skill never modifies a rule.
