# Handoff Boundaries -- Recognize, One-line Verdict, Route (do not diagnose)

This skill is deliberately narrow: mail ports (25/465/587/993/995) and the
port-25 unblock workflow on ECS. Ticket history shows a measurable share of
false hits ("smtp", "email", "port" mentioned in problems that are not mail
path failures) and a classic misdiagnosis pattern: any send failure being
auto-answered with "port 25 is blocked". The routing table exists to kill
both. When a row matches: give the one-line verdict, name the target, and
STOP -- do not run this skill's diagnosis on someone else's symptom.

| Symptom seen (customer wording) | Verdict sentence (relay, then stop) | Route to |
|---------------------------------|--------------------------------------|----------|
| Ports 22 (SSH) or 3389 (RDP) unreachable / reset | "This is not a mail-port issue; the mail diagnosis path does not apply." | `area:ssh-connection` (22) / `area:windows-rdp` (3389); false-hit evidence: ticket T-96D455C4 (SSH reset, platform never involved) |
| 80/443 website unreachable, no mail involved | "General web/public-network reachability belongs to the network skill." | `area:web-inaccessible-slow`, or the online `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` for general public-network connectivity |
| Mail ports fine, but overseas<->domestic paths are slow/dropped/unstable | "TCP is established; the remaining leg is link quality." | `area:cross-border-link-diagnosis`, `area:network-quality-bandwidth` (evidence: ticket T-8E8AD7A5 resolved via provider switch) |
| How to WRITE security-group rules / minimal egress sets (a change request) | "Rule design and edits are manual changes; this skill only reads and guides." | access-interception layering flow / human; guide reading with the security-group quickstart doc |
| Website/content blocked for violation, regulatory URL shielding | "That block stems from content enforcement, not the mail-port policy." | `area:punishment-appeal-guide` / security-center flows (false-hit evidence: ticket T-9A3FFD1E) |
| "I got an email from Alibaba Cloud about resources I cannot see" | "Notification/resource visibility, unrelated to SMTP sending." | `area:console-resource-lookup` (false-hit evidence: ticket T-9B7E25B8) |
| Alibaba Mail / DirectMail product settings, SPF/DKIM/DMARC records, mail landing in junk folders | "Product-level mail configuration is outside the ECS network path." | the mail product's console/support (tickets hand these to the product team, e.g. T-0DC2E989 end of thread) |
| Sub-account cannot VIEW block state or SUBMIT the unblock application | "The gap is RAM authorization, first confirm the caller with sts_token.py." | `area:ram-policy-diagnosis` (evidence: ticket T-F418FAF1) |
| Refund / order / purchase questions mentioning 'email' | "Commercial processing; not a diagnosis." | `area:unsubscribe-refund` / human commerce (false-hit evidence: ticket T-832BA1FF) |
| Intermittent session resets / flapping after every layer is eliminated | "This needs packet-level work; material list for human support: failure window, transcript, customer capture, port matrix, listener/firewall readings." | human ticket (evidence form: ticket T-E924B5F6 resolved by capture; capture is explicitly NOT performed by this skill) |

## Anti-pattern this table prevents

Ticket T-BFFFC987: customer's actual failure was `550 Bad HELO` on 587 with
an already-granted unblock -- the handling answered the port-25 policy
question instead and had to escalate offline. The one-line verdict + routing
above is exactly the step that ticket missed: attribute first, then speak.

## Trigger narrowing (why false hits happen and how the description prevents it)

Generic words ("smtp", "email", "diagnose", "config", "port") never trigger
this skill alone; the description only advertises mail-port-specific
phrases. When the customer text matches a routing row above MORE than the
mail-port semantics, route -- even if "port 25" appears incidentally (for
example in "the email notification said my 25 GB disk").
