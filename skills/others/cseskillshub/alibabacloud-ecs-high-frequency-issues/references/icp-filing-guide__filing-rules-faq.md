# Filing Rules FAQ (C3 + C4 wording bank)

Readable mirror of the knowledge embedded in `scripts/areas/icp_filing_guide/_constants.py`
(`ICP_FILING_KNOWLEDGE`). The script is the single source of truth at
runtime - run `python3 scripts/areas/icp_filing_guide/icp_filing_check.py knowledge --topic <key>`
(or `--query "<customer question>"`) and relay its output verbatim. This file
exists so a human reviewer can audit every wording and its evidence.

The heading of each section below is the real `--topic` key for that subject,
so any heading can be fed to the script directly. `--list-topics` prints the
same thirteen keys.

Confidence markers used below (printed by the script as well):

- **[transcript-verified]** - grounded in a support-ticket conversation that
  was retrieved and re-read.
- **[summary-only]** - grounded only in a ticket summary; the conversation
  could not be retrieved. MUST be presented with the caveat "confirm with the
  filing specialist before treating this as authoritative".
- **[partial-transcript]** - the conversation was retrieved but truncated
  (the phone segment is missing); the same caveat applies.

Never upgrade a summary-only wording to a verified claim.

## 1. `filing-server-conditions` - which server may carry a filing [transcript-verified]

A filing service code binds only to a server in the SAME account that is (a)
in a mainland China node, (b) subscription-billed with a term of at least 3
months, and (c) has public bandwidth enabled. Buying a qualifying subscription
ECS instance auto-generates a FREE filing service code, so a separately
purchased paid code is usually unnecessary. Evidence: T-C097A6CB, T-5A6AABCB.
The read-only scan and the exact per-condition judgement live in
`references/icp-filing-guide__icp-eligibility-checklist.md`.

## 2. `service-code-binding` - "no selectable instance" when binding [transcript-verified]

An empty binding list means no instance in the account meets all three
conditions - it is not a console defect. This is what the support engineer's
manual "we checked your account" step found, and exactly what the eligibility
scan reproduces. Order of operations for a customer who already paid for a
code: first obtain a compliant mainland subscription instance with public
bandwidth, then bind (or use the auto-generated free code), then submit.
Refunding an unused paid code and any purchase advice are commercial routes;
support wording is that an unused paid code can be refunded while a consumed
code cannot be reused, with the outcome decided by the commercial specialist
under the refund rules document - never promise an amount. A paid filing
concierge service exists for customers who want handled filing.
Evidence: T-C097A6CB, T-2E81A6EC.

## 3. `review-timelines` - how long the review takes [transcript-verified]

Provider first review: 1-2 working days. Provincial communications
administration review: 1-20 working days. Inside the normal window no expedite
is possible, so never promise a faster review. Review progress is filing-side
data this skill cannot read - point the customer to the ICP Filing console or
a filing agent. Evidence: T-2E81A6EC.

## 4. `deregister-and-refile` - what cancelling a filing really costs [transcript-verified]

Once the filing is cancelled, every domain under that record stops being
servable from a mainland server until a new filing passes. Re-filing requires
a NEW service code; a code already used by the cancelled record cannot be
reused. Two routes exist and only the customer chooses: a paid migration
service that keeps the site online, or the free cancel-and-reapply path that
interrupts access. The outage window is the difference between them - state it
explicitly rather than only listing steps. Evidence: T-2E81A6EC.

## 5. `cross-provider-access-transfer` - adding Alibaba Cloud access for an already-filed domain [summary-only]

Per the ticket summary: the filing number does NOT change and the original
provider's access does NOT need to be cancelled first. The conversation was
not retrievable - always attach the specialist-confirmation caveat.
Evidence: T-5A6AABCB.

## 6. `entity-change-and-instance-transfer` - subject change and moving an instance [transcript-verified]

Filing information must stay consistent with the domain registration
information; a mismatch is what forces the subject-change route. An ECS
instance cannot be transferred directly between two accounts whose enterprise
verification subjects differ. The documented alternative is: create a custom
image, share it with the target account, create a new instance from it - the
instance ID and the public IP both change, so DNS records and any IP-based
allow-lists must be updated afterwards. Image creation, sharing and instance
creation are write operations: this skill only explains them.
Evidence: T-2E81A6EC.

## 7. `subject-type-vs-site-purpose` - personal or enterprise subject [summary-only]

Support wording: site content that involves payment or transaction handling
needs an enterprise filing subject; a personal subject does not cover it. The
"individual developer" option on a purchase page is not a statement about what
a filing subject may publish. The exact subject rule for a specific business
scope must be answered by a filing specialist. Evidence: T-1F986C3F.

## 8. `unfiled-vs-port-blocked` - does a missing filing close ports? [summary-only]

No. Being unfiled does not shut a listening port down. A port that refuses
connections straight after an OS install (443 in the ticket) normally means
nothing is listening inside the guest, or the security-group ingress rule is
missing. Conversely, a browser symptom that tears down an established
connection mid-request (`err_connection_closed` / `err_connection_reset`) is
the classic shape of an inbound-rule interception, not of a filing
synchronisation delay - ticket T-63E5332F concluded exactly that and said it
was unrelated to filing. The order is always: prove the network path first
with read-only cloud queries, then discuss filing state.
Evidence: T-D9F63B3E, T-63E5332F. Tree: `references/icp-filing-guide__block-triage-tree.md`.

## 9. `pre-filing-testing` - testing the site before the filing passes [partial-transcript]

Before a filing passes, the site can be exercised through the server's public
IP address directly; that is the standard pre-launch smoke test. While a
filing is in progress the domain may be blocked on mainline HTTP/HTTPS access.
The evidence here is thin (phone-record tickets, plus one summary whose
filing-interception attribution was never confirmed in any retrieved
transcript), so present this as guidance to try, never as a verified filing
policy statement. Evidence: T-348424F9, T-FC32DAA3.

## 10. `renewal-and-filing-codes` - renewal, expiry and gifted-code rumours [transcript-verified + summary-only]

Renewing an instance does not change its specifications. The unified answer
for "does renewal come with a filing service code" is that no such promotion
could be verified for that order and the quoted price was already the activity
price - this is ONE ticket's evidence, so do not generalise it to every order.
Whether the website stays reachable depends on the server hosting it still
being in use, not on the filing itself: letting the instance lapse takes the
site down, and a released instance loses its data. Renewal, extension, pricing
and any whitelisting are commercial operations this skill never performs; it
only states the read-only instance status. For an account restricted by
compliance review, the extension allowance quoted in the transcript was one
day, one instance, once per calendar year; lifting the restriction itself is a
human action. Evidence: T-5E8C9693 [transcript-verified], T-25ADE062
[summary-only], T-8BE7BCE3 [partial-transcript].

## 11. `classified-protection-materials` - MLPS paperwork is NOT an ICP filing [transcript-verified]

Requests for a classified-protection (MLPS) assessment report or filing
certificate are a different compliance track from an ICP filing number; the
word "filing" in both makes customers merge them. Do not enter the ICP triage
tree for these. Those materials come from a fixed official request form; a
specialist answers within 3 working days, and the free security-architecture
consultation checkbox can be ticked on the same form. This skill only routes:
it neither submits the form nor tracks its approval.
Evidence: T-0631D05C, T-96F0322C.

## 12. `saas-to-self-hosted` - SaaS site builder to self-managed ECS [summary-only]

Content built on a SaaS website builder cannot be exported and deployed onto
an ECS instance; going self-hosted means rebuilding the site. Whether reusing
the already-filed domain on a mainland ECS instance needs an access filing
depends on the filing-side state, which no read-only cloud API in this skill
exposes - ask the customer for the ICP Filing console status, then route to
the filing specialist. Evidence: T-AAD67A7B. The site-rebuild guidance itself
is the build-a-website document listed in `references/icp-filing-guide__help-links.md`.

## 13. `website-served-elsewhere` - the filed domain is not served by this instance [partial-transcript]

A filed domain can be served by object storage plus a content delivery network
while the ECS instance bought for the filing code serves nothing; that is
legitimate, not a fault. Establish where the domain actually resolves BEFORE
diagnosing the instance - the answer is in the DNS records, which the customer
reads in the DNS console. The transcript was cut off at an attachment (the
clarification happened on the phone), so treat this as context, not policy.
Evidence: T-3A6324B3.

## Boundary reminders (C4)

- Filing progress/expediting, code inventory, subject status: filing console
  or filing specialist (no API here).
- Purchases, refunds, renewals, extensions, pricing: commercial specialist.
- Windows IIS/.NET deployment, OS passwords, guest repairs:
  `alibabacloud-ecs-diagnose` or server specialist.
- DNS record changes: Alibaba Cloud DNS console (customer self-service).
- Routes and handoff sentences: `references/icp-filing-guide__escalation-map.md`.
