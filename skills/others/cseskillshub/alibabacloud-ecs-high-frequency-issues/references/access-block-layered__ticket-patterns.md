# Ticket Pattern Library (maintainer reference)

Maintenance document: it records which real support tickets each rule in
`scripts/areas/access_block_layered/_constants.py` was distilled from, how often each layer actually
turned out to be the answer, and where the reasoning stayed unproven. Ticket
identifiers are internal. Nothing in this file is relayed to a customer; the
runtime report carries the pattern wording, never the identifier.

## Corpus shape, and the one design decision it forced

Four scenario labels contributed 38 deduplicated tickets: remote connection
blocked by security group or firewall, security-group rule configured but not
effective, in-guest firewall or security software interception, and
WAF or Cloud Firewall protection. The per-label hit counts add up to well more
than the deduplicated union, because one ticket routinely carries two labels: a
"security group rule not effective" ticket is also a "remote connection
blocked" ticket (`T-B091EED8`, `T-43258B49`).

That is the reason the skill branches on **layer**, not on scenario label, and
why the entry tool requires direction, protocol, port and symptom before it
will walk anything.

## Pattern table

| Layer | Pattern | Evidence tickets | Automatable from cloud or guest reads | Skill behaviour |
|---|---|---|---|---|
| L4 | Authorization object does not contain the client's real egress IP (modem LAN address entered, dynamic IP changed, per-colleague VPN) | `T-906AE19F`, `T-E7E749B0`, `T-45FF359B`, `T-780A08F3` | yes, once the egress IP is supplied: rule coverage matching | HIT on the missing coverage; emits the exact five-tuple to add, plus the lookup page |
| L4 | Only ingress examined, egress forgotten: enterprise group denies outbound by default, breaking console-driven file transfer | `T-B091EED8`, `T-66EC2709`, `T-CDE0D0D9` | yes: group type plus egress rule set | reports the enterprise egress default-deny verdict; suggests the narrow internal service range rather than a wide opening |
| L4 | Group already allows the flow, so the block is one layer deeper | `T-E26080DA`, `T-43258B49`, `T-024E447D` | yes: L4 excluded, then L5/L6 | marks L4 EXCLUDED with the matched rule quoted and keeps walking; this is the case single-check tooling gets wrong |
| L4 | Rules authorizing another group or a prefix list cannot be expanded | general | no | UNKNOWN with the console follow-up named |
| L5 | firewalld overrides hand-added iptables rules, so "I added the rule" is true and useless | `T-43258B49` | yes: `iptables -S` plus firewalld state and zone | HIT with the two-mechanism explanation; the add-port command stays manual |
| L5 | ufw or firewalld never allowed the remote or service port; the customer then disables the whole firewall | `T-9DE4F634`, `T-0AC34CB9` | yes: firewall state and rule reads | HIT; guidance pairs the port allow with the out-of-band logon path and warns against disabling |
| L5 | Allow list exists but does not cover the real source address | `T-0AC34CB9` | partially: needs the source IP that reached the box | gated source-IP read compared against the rule |
| L5 | Kernel parameters `tcp_tw_recycle` with timestamps drop new NAT'd connections: ping fine, every TCP fails | `T-9CA9D2E9` | yes, as a value read | HIT hypothesis with the parameter reading quoted; the sysctl change stays manual |
| L6 | Nothing listens on the port the customer believes is open | `T-024E447D`, `T-66EC2709` | yes: listener read | HIT at L6; stops the customer from editing rules pointlessly |
| L6 | Application answers with its own status (401, 403, 404), which is not a network block | `T-6A0B4417`, `T-97F39561` | no; needs the response itself | declares L4-L5 excluded and routes to the customer's own application config |
| L2 | Customer blames WAF or Cloud Firewall; policy side shows nothing matching | `T-F8CBF510`, `T-CDE0D0D9`, `T-ADBE7F0D` | partially: policy configuration only | EXCLUDED with the explicit caveat that hit records are not readable here |
| L1 | Domain resolves to a Chinese-mainland endpoint, is unfiled, and an RST with spoofed source and odd TTL arrives while the server logs nothing | `T-42055B69`, `T-FA4ECD2F` | no filing-status read; symptom plus server-log silence are the cues | assumption-level verdict with self-check steps and the filing guide |
| L0 | Client network, VPN or browser cache; server log shows the client side sending the reset from an unexpected IP | `T-04E91CE7`, `T-45FF359B`, `T-F3B3CF8D` | partially: differential tests are the customer's | L0 differential scripted as one complete list; source-IP mismatch reported |
| L7 | Intermediate network device or carrier line blocks the path; the platform side measures clean | `T-9E18757D`, `T-2BF2CB97`, `T-0AB7C175`, `T-1893ED21` | no; needs both-sides captures and third-party dial tests, all manual | attribution plus the evidence list and the handoff wording |
| L3 | Custom route or appliance diversion not taking effect | `T-443B19A6` | out of scope | identified and handed off to the network-path skill |
| cross-cut | Resource saturation or instance state, not a filter | `T-3681BE5D`, `T-C6F0FD7D`, `T-1CD9EE86` | partly | handed off to disk-IO or instance-state, or to incident response |
| knowledge | Product-capability limits and managed-environment approval flows | `T-CB2794EE`, `T-96AFD85F`, `T-AD23A62D` | no diagnosis needed | answered directly as a capability statement, layer walk not started |

## How the corpus actually closed

Of the 38 tickets: 16 ended with a conclusion confirmed inside the dialog, 15
ended inconclusive (dialog truncated, escalated onward, or customer stopped
replying), 5 carried a stated root cause that the dialog never proved, 1 was
explicitly not resolved, and 1 was phone-only with no text of the fix.

The stalls cluster into three causes, and each one is a design input:

1. **A reading was requested and never arrived.** The engineer asked for
   command output or a screenshot and the customer sent nothing, or declined
   access (`T-E26080DA`, `T-AF0E8446`, `T-F8CBF510`). This is the single
   strongest argument for the gated in-guest reads, and the reason
   [evidence-collection.md](access-block-layered__evidence-collection.md) demands one item at a time.
2. **The decisive step was a human reachability test the skill cannot
   reproduce** - a dial test from another network, or an interactive session
   from the operator's own machine (`T-024E447D`, `T-C6F0FD7D`,
   `T-F8CBF510`). Where such a test would decide the verdict, the report says
   so and asks for a customer-side comparison instead of implying it happened.
3. **The answer was outside the platform** and needed a carrier or a human
   escalation (`T-0AB7C175`, `T-2BF2CB97`, `T-9E18757D`).

## Negative evidence worth keeping

`T-C6F0FD7D` is the existence proof for this design. A templated single-check
diagnosis reissued the same "security group ingress ports not open" verdict
four times, while a human telnet and session test showed the port answering.
A verdict list that names each excluded layer, with the reading that excluded
it, is what lets the walk continue instead of looping.

## Attributions still unproven (do not harden these into rules)

* `T-FA4ECD2F`: filing-based interception was asserted, yet the customer's own
  evidence was a TLS-version difference, which filing interception does not
  explain. Treat the compliance branch as a hypothesis generator only.
* `T-AF0E8446`, `T-F3B3CF8D`: root cause recorded as a guess; access was
  declined or the fix happened offline.
* `T-F8CBF510`: the recorded conclusion contradicts the operator's own port
  test, which passed.
* `T-024E447D`: only "not listening on 80 or 443" was proven; the path and
  region explanations in the summary were speculation.

## Trigger calibration and noise

Three tickets are retained only as handoff examples and were deliberately kept
out of trigger selection, because their subject was billing, a shared hosting
plan, or a commercial dispute rather than interception: `T-3A3BC04D`,
`T-04976A2A`, `T-97F39561`.

The Chinese trigger vocabulary of the four member scenarios maps to the English
phrases carried in the skill description as follows: security-group terms plus
"not effective" and "authorized object" to the group-rule wording; the
iptables, firewalld, ufw and third-party agent names to the guest-firewall
wording; WAF, Cloud Firewall and protection-rule names to the platform
protection wording; and SSH, remote desktop, port numbers and "port not open"
to the remote-access wording. Generic reachability phrasing is intentionally
**not** claimed on its own: it must appear with an interception noun (a group,
a firewall, a protection rule, a blocked port) or one of the quotable error
strings, so that routing and public-path cases stay with the neighbor skill
that owns them.
