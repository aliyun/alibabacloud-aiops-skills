# Out-of-scope hand-offs

A hand-off is not a referral. Each one must carry three things, in this order, in the same
message:

1. **why** this is outside the scenario, phrased in terms the customer can check;
2. **what has already been excluded, with the evidence** (the actual readings, not "we checked");
3. **who picks it up next**, and what to ask for there.

If the conclusion is "not the cloud" - the customer's LAN, a VDI, a carrier path - the comparison
evidence goes in the same message. Without it the customer will not accept the conclusion and the
ticket reopens.

## Register

| # | Topic | Why it is out of scope | Goes to | What to say |
| --- | --- | --- | --- | --- |
| 1 | Cannot log in to the instance itself; instance hung or down | That is instance health, not an external access path | `alibabacloud-ecs-diagnose` / instance operations | Report the instance state that was read, then ask for a login-focused ticket |
| 2 | Disk full or inodes exhausted | Capacity hygiene; here it is at most a side cause of a 5xx | disk capacity scenario | Mention it as an L6 side observation; do not take over cleanup |
| 3 | Writing DNS records | DNS writes are outside this scenario; only the current records are listed | DNS scenario / the customer in the DNS console | Output the exact record that should exist, its value and where to change it |
| 4 | CDN, DCDN, ESA, WAF or GA origin and policy tuning | Cross-product edge configuration is neither visible nor changeable here | the matching product scenario | Show the origin-versus-edge comparison result from `../SKILL.md`, then hand over |
| 5 | ICP / access filing application, change, cancellation | The filing workflow belongs to the filing product | filing scenario / the customer | State the inference and its evidence, label it an inference, give the filing console entry |
| 6 | Blackhole unblocking, Anti-DDoS purchase and policy | Mitigation operations are not ECS operations | DDoS protection scenario | Hand over the attack evidence collected: connection count, source ranges, bandwidth peaks |
| 7 | Domain registration, transfer, real-name verification, redemption | Not an ECS access path | domain scenario | Say that the resolution content is correct but the domain lifecycle is handled elsewhere |
| 8 | Origin server outside Alibaba Cloud | The traffic may never enter this cloud network at all | the customer and their provider | Show the comparison test that isolates the peer side |
| 9 | JuShiTa / open-platform hosting | Different control plane and different network policy | that support channel | Report the asset type that L1 identified, then hand over |
| 10 | Simple Application Server firewall | It is not an ECS security group, so no rule read here applies to it | Simple Application Server scenario | Report the asset type and name the rule to check in its own console |
| 11 | Customer LAN, enterprise or campus network, VDI | Unobservable from the cloud | the customer's IT team or their carrier | Attach the retest-from-another-network evidence before making the claim |
| 12 | Disk I/O as the root cause of slowness | No ticket evidence in this batch; a branch would be invented | re-evaluate when evidence exists | Say explicitly that this cause was not tested |

## Phrasing rules

- Never say "this is not a cloud problem" as the first sentence. Lead with the evidence, then the
  conclusion, then the owner.
- Never drop a layer silently. If L3 stayed `INCONCLUSIVE`, the hand-off message says so and says
  what would have settled it.
- Name the level of the action you are recommending. Telling a customer to add a security group
  rule is a level C recommendation: include the snapshot note and the cost statement from
  `../SKILL.md`.
- Where a capability was not verified, hand off rather than improvise: blackhole state, filing
  state, CDN/WAF/GA configuration, arrears, multi-region dial tests, the Simple Application Server
  firewall, and the Windows in-guest command set. The full list with what the skill does instead
  is in `layered-decision-tree.md` and in the "Capability limits" table of `../SKILL.md`.

## Proven mis-recalls

Three real tickets were routed into this scenario and do not belong to it. Exclusion is on the
trigger words, before any layer is walked:

- "the **console** page will not open" - a control-plane or client-browser issue, not a customer
  website;
- "an **OS upgrade** cannot reach its mirror" - an outbound package-source issue;
- "everything fails on my **office VPN / VDI**" - topic 11 above; the instance is reachable from
  another network.
