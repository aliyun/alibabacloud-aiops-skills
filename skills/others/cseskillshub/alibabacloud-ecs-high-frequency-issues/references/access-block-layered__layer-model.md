# Layer Model — how a blocked access is attributed

The tier's defining fact: one support ticket frequently spans several
scenario labels at once (a "security group rule does not take effect" ticket
is also a "remote connection blocked" ticket). Therefore this skill branches
on the LAYER at which traffic dies, never on the customer's scenario label
or on the port/direction the customer happened to mention first — ticket
evidence shows customers routinely name the wrong direction and the wrong
port (a "3389 problem" that was really an enterprise-group default-deny
OUTBOUND 443).

## Step 0 — fix the three coordinates before any layer walk

1. **Direction**: inbound (outside -> instance), outbound (instance ->
   outside), or internal (instance <-> instance, same or peered VPC).
2. **Exact symptom string**: the literal error text the customer sees
   (see [symptom-error-strings.md](access-block-layered__symptom-error-strings.md)).
3. **Scope**: ALL clients fail / only one client, line or region fails /
   only one port or domain fails. Scope differences are the strongest
   single pointer toward L0/L7 (client or path responsibility).

Missing coordinate -> the entry script records the affected layer as
UNKNOWN and `NEXT_ACTION` names exactly what to ask.

## Layer order (self-outside-in) and states

Every layer ends in one of three states: **EXCLUDED** (evidence shows
traffic is not dying here), **HIT** (evidence shows the block here),
**UNKNOWN** (insufficient evidence; says what is missing).

| Layer | Scope | Evidence sources | Typical hits |
|---|---|---|---|
| L0 client side | local network / VPN / corporate egress / proxy / browser cache / the egress IP the customer believes vs the real one | customer differential tests (second network, second device, second browser, IP-direct vs domain); server-side log source IPs vs authorized IP | corporate VPN changing the egress IP; browser cache; one carrier line only |
| L1 DNS / compliance | resolution correctness; unfiled-domain interception when the domain resolves to a Chinese-mainland endpoint | dig/nslookup by customer; RST-style symptoms + no server-side request log; filing has NO query API in this build -> assumption level only | compliance interception injecting RST mid-TLS |
| L2 platform protection | Cloud Firewall internet-boundary policy configuration; WAF instance presence | DescribeControlPolicy, DescribeInstance (both degradable). Hit LOGS are a declared capability gap: policy-match is not proof of interception | a drop policy matching the flow |
| L3 VPC network | custom route tables, vswitch routes, network ACLs, third-party firewall diversion | identified only; diagnosis belongs to the VPC/public-network skill (see handoff-boundaries.md) | diversion to a security appliance that is not configured |
| L4 security group | ingress AND egress five-tuples, priorities, authorization objects, normal vs enterprise defaults | DescribeInstances + DescribeSecurityGroups + DescribeSecurityGroupAttribute, first-match evaluation | missing covering allow; explicit Drop; enterprise egress default-deny; authorized IP != real egress IP |
| L5 guest OS | firewalld / ufw / iptables (and the two-mechanism conflict), security software, kernel network parameters (tcp_tw_recycle + timestamps under NAT) | gated non-mutating checks (guest-inspection-commands.md) | firewalld REJECT; ufw not allowing the port; recycle dropping NAT clients |
| L6 service / listener | process listening? bound to 0.0.0.0 or 127.0.0.1 only? container port published? application replying 401/403/404? | gated listener check; HTTP status codes distinguish L6 from L4/L5 | nothing listening on 80/443 despite "I opened everything" |
| L7 outside platform | intermediate network device interception, ISP regional blocking, cross-border path, peer-side egress policy | full exclusion of L0-L6 with evidence + directional symptoms (single-line failure, spoofed-source RST with TTL/TOS mismatch, server-side capture showing no locally generated RST) | path interception; needs ISP / senior human escalation |

## Termination rules

* A layer HIT with direct evidence stops the walk: report the hit, the
  evidence, and the exact manual remedy. Do not keep probing to "see what
  else is wrong" — but DO remind: snapshot before any change, smallest
  possible authorization.
* Two consecutive UNKNOWN layers with no further automatable evidence ->
  `STATUS: DEGRADED`; output precisely which evidence the customer must
  supply (evidence-collection.md) and which human action takes over.
* "The customer says the security group and the firewall are both fine"
  proves nothing: L4 is re-read from cloud state, L5 from gated reads.
  Customer self-report is a hypothesis, never an EXCLUDED verdict.

## The single most important behavioral rule

A one-dimension check that only reads the security-group rule text will, in
"rule edited but still failing" cases, keep re-emitting the same stale
conclusion (this failure mode is documented in the pattern library). The
value of this skill is the LAYERED verdict table with per-layer evidence, so
that "already excluded" layers are visible and the walk continues downward
every time.

## Non-blocking cross-cuts (hand off, do not diagnose here)

Disk-IO saturation freezing the OS, instance boot/state anomalies,
compromise/mining incidents, WAF rule tuning, ICP filing processing,
billing disputes, special-environment (e.g. proprietary hosting platforms)
port-approval workflows. See handoff-boundaries.md for wording.
