# Error-code guide (tier-quotable codes and literal tool strings)

Two codes are quotable for this tier; two literal tool outputs complete the
set. The report quotes the matching row verbatim; the agent relays it, and
never invents codes beyond this list.

## err_cert_date_invalid

**Shape.** The certificate's validity window
(notBefore / notAfter) does not cover the current time — the browser says
expired, not yet valid, or refuses the date outright.

**Three-way split before acting.**

1. *Genuinely expired or not yet renewed* — renew and redeploy per the
   deployment checklist. The outside-in TLS check states the exact
   `valid until` date and `days left` count from the served certificate.
2. *Not yet valid* — a certificate issued for a future window, or clock
   skew. Compare the served dates with the local time shown in the report.
3. *Server clock wrong* — dates can look invalid from the box while the
   outside-in view is clean. If the two disagree, the instance clock is the
   suspect, not the certificate.

**The paired misconception (ticket T-B5F37974 customer wording).**
"the certificate has another month of validity, so it cannot be the
problem" — expiry and key pairing are INDEPENDENT faults: a certificate
with months left fails identically when its private key is the wrong one.
A clean date window never clears the certificate; run the modulus
comparison from the runbook before pointing elsewhere.

## err_connection_closed

**Shape.** The TCP or TLS session is reset or closed mid-handshake — the
browser or client reports the connection was reset, not that it timed out.

**The split that decides the branch.**

| Evidence | Meaning | Branch |
| --- | --- | --- |
| immediate reset, both from the box and from outside | a firewall or security software, or the endpoint is dropping the session | guest firewall readings (manual, runbook), security-group rule scan |
| reset from outside but the box itself completes the handshake | an inbound path problem: a deny rule (including a rule denying the server's own address — ticket T-438814FA) or an intermediate service | security group self-check list |
| timeout instead of reset | a path problem: routing, cross-border congestion, or nothing listening | egress or listener branches of the decision tree |

The same reset-versus-timeout method was used by support for the outbound
mail-port question in ticket T-3E637B73 — the method transfers; the
symptom does not (it hands off).

## context deadline exceeded (literal tool output)

Go-based toolchains (1Panel and others) print this when their HTTP call to
the CA or a DNS-provider API never completes. Treat as the issuance egress
branch: region lens first (mainland versus overseas), endpoint ownership
next (172.65.0.0/16 equals the Cloudflare edge for Let's Encrypt), then
the alternative-path menu (references/ssl-cert-deployment__acme-network-egress.md). Ticket
T-6A73F6B0 evidence.

## query timed out looking up A/AAAA (literal tool output)

ACME DNS-01 validation failing on the CA's own resolver lookup, observed
for `.cn` domains when the CA-side DNSSEC cache was stale (ticket
T-4AC3F65A). The cause sits at the CA resolver: wait for the cache window
or change validation method. Instance-side changes cannot fix this.
