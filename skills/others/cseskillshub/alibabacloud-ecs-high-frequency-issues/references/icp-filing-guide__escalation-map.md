# Escalation and Handoff Map (C4)

This read-only skill explains, checks and routes - it never performs
commercial, compliance, filing-side, DNS-side or guest-side actions. Use this
map whenever a request crosses the boundary.

## Route table

The six keys below are exactly the entries of `ESCALATION_ROUTES` in
`scripts/areas/icp_filing_guide/_constants.py`; `knowledge --query` prints a route only when its
`signals` match the customer's wording.

| Route key (real) | Recognize it by | What this skill may still do | Where it goes |
|---|---|---|---|
| `filing-progress-and-administration-review` | "how far is my filing review", "can it be expedited", "why rejected", "how many codes do I have", "is this code used", "bind it for me" | Explain the standard timeline (initial review 1-2 business days; administration review 1-20 business days; no expediting in the normal timeline) [verified T-2E81A6EC]; run the eligibility scan and explain the binding conditions | Alibaba Cloud ICP Filing console -> filing specialist; paid handling: filing concierge service. The code inventory is readable only there, and a binding failure despite an eligible instance goes to the filing specialist |
| `commercial-actions` | purchase, refund, renewal, extension, pricing, invoicing, "give me a discount" | Read instance state/expiry read-only so the customer understands the impact | Commercial/support specialist; refund rules document in `references/icp-filing-guide__help-links.md`. Never quote prices or promise outcomes |
| `in-guest-and-deployment-work` | IIS / .NET / web service deployment, OS password reset, "install it for me", remote-assistance authorization, "log into my server and look", listener checks inside the OS | Identify the request, print the cloud-side verdict, and hand off with the relevant official documents; also print the customer self-check commands (read-only, the customer runs them) from `references/icp-filing-guide__block-triage-tree.md` | `alibabacloud-ecs-diagnose` or a server specialist. This skill never runs guest commands, never logs into an instance and never accepts remote-control authorization |
| `dns-record-work` | "check my resolution", "add the @ record", domain transfer records | Print the DNS console entry and what to verify (apex "@" record -> the server's public IP printed by the report) | Alibaba Cloud DNS console (customer self-service). No DNS API is in this skill |
| `classified-protection-and-other-compliance` | MLPS test report, classified-protection certificate, "security compliance proof" | Disambiguate: this is NOT ICP domain filing | Official compliance-material application form (link in `references/icp-filing-guide__help-links.md`); specialist responds within 3 business days |
| `account-compliance-restriction` | account restricted from recharging/renewing, real-name status cancelled/revoked, whitelist request | Read instance expiry read-only; state the data-retention risk of release | Human compliance channel / account specialist. Known support wording: extension limited to once per account per calendar year, one day, one instance [partial transcript - specialist confirms case by case] |

## Handoff sentences (relay style)

- Filing progress: "The filing review status and administration progress must
  be verified by the filing service. Please check the Alibaba Cloud ICP
  Filing console or contact the filing specialist; the paid filing concierge
  service offers handled filing."
- Commercial: "Purchases, refunds, renewals and pricing are handled by the
  commercial specialist - I can show the current instance state read-only so
  you can decide, but I cannot place, change or price any order."
- Server side: "Website deployment and OS-level components are server-side
  work; I am handing this to the server diagnosis channel with the relevant
  official documents."
- MLPS: "A classified-protection (MLPS) certificate is not an ICP domain
  filing item. Please apply through the official compliance-material form;
  with the free security-architect guidance option ticked, a specialist
  responds within 3 business days."
- DNS: "Resolution records are managed in the Alibaba Cloud DNS console.
  Please verify that the apex '@' record of your domain points to the public
  IP shown in my report."
- Compliance: "The transaction restriction comes from the account compliance
  check and can only be handled by the compliance team; be aware that an
  instance released after expiry loses its data."

## Hard boundaries (never cross, whatever the customer asks)

1. Never execute or generate any mutating cloud API call, and never generate
   a mutating CLI command "for the user to run" - console navigation steps
   only.
2. Never run any command inside a guest instance; never accept remote-access
   authorization.
3. Never promise filing approval, refund amounts, expediting, whitelisting or
   promotion existence.
4. Never state filing status as fact without customer-provided console
   evidence - no filing API exists in this skill.
5. Summary-only wordings keep their "confirm with the specialist" caveat
   (see `references/icp-filing-guide__filing-rules-faq.md`).
