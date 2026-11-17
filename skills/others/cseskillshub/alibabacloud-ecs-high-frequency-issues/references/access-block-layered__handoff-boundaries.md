# Handoff Boundaries — where this skill stops

This tier deliberately shares the "cannot connect" symptom space with other
skills. The rule is simple: **this skill owns attribution across the block
layers; it does not own diagnosis inside another skill's layer, and it never
owns the change itself.** Recognizing a boundary and naming it early is a
correct outcome, not a failure.

## What this skill owns

Attribution of a blocked or reset connection across the layers defined in
[layer-model.md](access-block-layered__layer-model.md): client side, DNS and domain compliance,
platform protection (Cloud Firewall policy, WAF presence), security group
(ingress and egress, normal versus enterprise defaults), guest firewall and
security software, kernel network parameters, service listener, and finally
the judgement that responsibility sits outside the platform.

It also owns the evidence package that a handoff is built on: the per-layer
verdict table, and the exact manual steps for the layer that was hit.

## What this skill hands off (recognize, do not diagnose)

| Handoff key (script constant) | Recognition cues in the customer's own words or in the evidence | Owner | Suggested wording |
|---|---|---|---|
| `vpc_route_link` | custom route table, vswitch route, traffic diverted to a third-party firewall appliance, EIP quality, cross-border path, carrier routing, SNAT or NAT gateway, "works from one region or carrier only" | `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` | "The security group, guest firewall and listener layers are excluded with evidence; the remaining symptom sits in VPC routing and public-path quality, which the network-path skill covers. Hand off with this layer table attached." |
| `disk_io` | system frozen, disk IO or iowait saturated, remote session unresponsive while the network path tests fine | disk-IO diagnosis skill | "Network-layer evidence is clean; unresponsiveness tracks resource saturation. Route to disk-IO diagnosis." |
| `instance_state` | instance will not boot, stuck in an intermediate state, "a reboot recovered it" | instance-state diagnosis skill | "TCP reaches the login screen, so the block is not a filter; boot or service state is the next owner." |
| `waf_product_side` | WAF rule tuning, CC-protection thresholds, bot management, back-to-origin address ranges, why a malicious request was not blocked | WAF product console and support | "This skill can only confirm whether a WAF instance exists and whether a Cloud Firewall policy could match; protection-rule design belongs to the WAF product side." |
| `security_incident` | intrusion, trojan, miner, defacement, exposed admin port exploited, security agent offline | Security Center plus manual incident response | "Suspected compromise is an incident-response case. Do not treat it as a firewall misconfiguration, and do not change rules before the incident is triaged." |
| `icp_filing` | domain resolves to a Chinese-mainland endpoint with RST-style failure and no server-side request log | ICP filing process guide (manual) | "Unfiled-domain interception is the leading hypothesis; it cannot be confirmed from cloud data here. Verify filing status on the filing console, use direct-IP access as a temporary path, and follow the filing guide." |
| `commercial` | billing dispute, refund, unsubscription, compensation | Billing and commercial support | "This is a commercial process, outside technical attribution." |

Two further cases are answered as knowledge rather than diagnosis: product
capability limits (for example scheduled port opening is not a security-group
feature, and rule reuse across instances uses clone, export, or template
flows), and managed environments whose port changes go through their own
approval workflow instead of the security-group console. Detect those from the
customer's wording, answer directly, and stop the layer walk.

## Boundary discipline when talking to a neighbor skill

The overlap partner above is a real, already-published skill, so:

1. Never claim the routing or public-path conclusion yourself. Route tables,
   network ACLs and link quality are read and judged there; here L3 is
   reported as `NOT_APPLICABLE` with the reason.
2. When the customer's wording is generic ("the server is unreachable",
   "ping does not work") and contains no blocking semantics, ask one
   clarifying question before starting: does the connection time out, refuse,
   or reset, and is a security group, firewall or WAF suspected? This keeps
   this skill on interception cases and lets path or routing cases go to their
   owner directly.
3. A handoff is only useful with evidence attached. Never hand off an empty
   conclusion: include which layers were excluded, with what reading, and
   which readings are still missing (see
   [evidence-collection.md](access-block-layered__evidence-collection.md)).

## Escalation that this skill cannot perform

Contacting a carrier to release a blocked line, obtaining a senior human
review of platform-side interception, running a platform-side dial test from
another network, logging into the instance beyond the gated non-mutating
checks, or applying any change. Each of these appears in the report as a
named human action, not as a promise from the skill.
