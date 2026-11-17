# Boundary recognition and handoffs (identify, transfer, never treat here)

These symptoms co-occur with certificate tickets in real support work. The
skill's duty is a fast, confident identification plus the exact transfer
wording — running them down here is out of scope by design. Before any
handoff, run one certificate-relevance check so nothing is misrouted (a
customer who calls SMTP port 465 "the HTTPS port" still means mail).

## Handoff table

| Recognize when the customer says | Handoff sentence (relay, then stop) |
| --- | --- |
| mail sending fails on port 25, 465 or 587; "outbound mail blocked" | "Mail egress on those ports is outside certificate scope. The platform limits port 25 by default and does not restrict 465 or 587, so suspected local interception needs the network and mail diagnosis tier; the same reset-versus-timeout probe method applies there." (method borrowed from ticket T-3E637B73) |
| ICP filing verification notices, rectification deadlines, "keep the domain's access records alive" | "That is a filing-compliance topic, not TLS: it goes to the filing channel. I am recording the certificate part of the case separately." (the second half of ticket T-B5F37974) |
| "download my domain certificate", data center address proof, service provider unit wording, graded-protection or telecom-license material packages | "Those are qualification and registration documents; the domain-name certificate for registration is a different object from a TLS certificate. Use the self-service center paths listed in references/ssl-cert-deployment__help-links.md." (tickets T-231D5C7C, T-B0AD7067 — the keyword collides, the subject does not) |
| remote desktop or SSH will not connect, especially after the port was moved (for example 5562) | "Connection failure on the administration port is not a certificate fault even when HTTPS also broke; it belongs to the instance-connectivity tiers." (ticket T-1F44C122 opened with both, only one was certificates) |
| disk full, inode exhaustion, expansion not visible, slow IO | "Capacity and IO belong to the disk tiers: area:disk-expand-diagnosis, area:disk-expand-diagnosis, area:resource-bottleneck." |
| a purchased certificate deployment service was performed wrongly | "Delivery disputes on a paid service go back to that service's order and a human agent; this skill only verifies what is currently served, which the report does." (ticket T-1F44C122 second half) |
| instance will not start, stuck states | "Instance lifecycle belongs to area:instance-state-diagnosis." |
| website down with 502, 504 or 404 and no certificate or HTTPS wording at all | "No certificate signal here; the general connectivity and web-access tiers cover this." (dedup boundary versus alibabacloud-ecs-diagnose) |

## The reverse check: when NOT to hand off

Panel and toolchain words stay HERE whenever the failing object is a
certificate: BaoTa or 1Panel certificate requests, acme.sh, certbot,
Posh-ACME renewal — the panel is context, the certificate is the symptom.

## D-class human-only operations (recognized anywhere, never executed)

Restarting or reloading any web service or the instance, editing security
group or guest firewall rules, deleting or overwriting certificate files,
toggling forced HTTPS, deleting snapshots, refunds or commercial
adjustments. Each gets: risk statement, exact manual steps or console
entry, and — where a server change follows — the snapshot-first notice
first.
