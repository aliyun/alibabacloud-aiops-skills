# Certificate service product rules (FAQ) — with confidence tags

These are the rule questions that arrive as tickets even though nothing is
broken. The certificate service DOES expose read-only OpenAPI actions, and
this skill uses one of them: `cas ListUserCertificateOrder` (api version
2020-04-07) returns the certificates and orders the account owns with their
status (`PAYED` / `CHECKING` / `CHECKED_FAIL` / `ISSUED` / `WILLEXPIRED` /
`EXPIRED`) and, where the product returns it, the validity window. The
sibling read actions `ListCertificates`, `GetUserCertificateDetail` and
`DescribeCertificateState` exist but are not called by this area. The
remaining free quota and the review progress are NOT returned by the call
this area makes, so those two stay console-side; every figure below still
carries the confidence tag. Relay answers with the tag.

Confidence tag to append verbatim (batch policy for single-ticket wording):

> Confidence: ticket-derived wording only. Treat the official console and
> help documentation as authoritative before quoting numbers or deadlines
> to the customer.

## Where the free certificate application entry is now

The legacy free-certificate flow stopped taking new orders; clicking create
in the old view routes into the current certificate version's flow. The
free quota and its yearly clearing date quoted in support tickets
(twenty certificates a year, cleared at the end of the calendar year) come
from one phone-call ticket only — tag required, console authoritative.
Application, domain validation and download stay manual console steps for
the customer. (Ticket T-9A27862F, phone record: the text carries no
substance beyond the summary — flagged for re-verification.)

## Which name a certificate covers (domain levels)

Count labels from the right: `example.com` is the registrable domain,
`api.example.com` is one host below it, `www.api.example.com` two. A
wildcard `*.example.com` covers one level of subdomain only — it never
matches the deeper `www.api` style names. When a panel or a user says "the
second-level domain certificate", ask which exact host the browser
visits and certify that name; DV issuance only proves control of the
domain, it does not grade the business behind it.

## DV validation by phone, and the expedite request

For the phone-based domain validation path, the verification call goes to
the enterprise phone number registered at public business-registry
sources — which may differ from the contact typed into the console form.
If the customer will not answer that number, the fix is updating the
registry-side contact data (or arranging to answer it). Review order
cannot be expedited: neither this skill nor a support agent can advance a
validation queue. Set that expectation early; ticket T-14495C53 shows how
much ticket time the wrong expectation burns.

## Renewal window and expiry communication

Renew before the served certificate leaves its window; the outside-in TLS
check in report mode prints `valid until` and `days left` from the live
served certificate, which is the number to discuss, not the console order
state. Remember the amplifier fault: renewal failure plus a live
Force-HTTPS switch takes the whole site down (ticket T-411B8BA7) — the
redirect switch is the first-aid lever, and toggling it is a manual step
after a snapshot.

## Network failures that masquerade as product problems

"the console let me apply but my certbot cannot" is usually the issuance
egress branch, not a quota problem: `context deadline exceeded` during a
panel request maps to references/ssl-cert-deployment__acme-network-egress.md, not to this file.

## What the skill can and cannot automate here

| Question | Automated? | Why |
| --- | --- | --- |
| which certificates/orders the account owns, their status and validity window | yes | read-only `cas ListUserCertificateOrder` (OrderType `CERT` and `CPACK`) |
| remaining free quota / review stage | no | not returned by that action; console only |
| which host name to certify | answered from the rule above | pure knowledge |
| whether the served certificate matches expectations | yes | outside-in TLS check, no authorization needed |
| expediting review | no, for anyone | human support cannot either |
