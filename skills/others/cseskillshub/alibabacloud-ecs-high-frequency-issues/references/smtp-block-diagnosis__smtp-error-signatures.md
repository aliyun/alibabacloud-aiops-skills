# SMTP Error Signatures -- Customer-Visible Text -> Layer -> Handling

Every signature below was taken VERBATIM from a reviewed support-ticket
conversation (biz id cited). The engine in `scripts/areas/smtp_block_diagnosis/_constants.py` carries
the matching regular expressions; this file is the readable version with the
handling detail. The golden rule first:

> **A 4xx/5xx SMTP reply (or any banner) means the TCP session was
> established.** Anything that got an application-layer answer CANNOT be the
> platform port-25 block -- the block is silent (timeout / no response). A
> real ticket shows a 25-port answer given to a 587 application-layer
> failure; do not repeat that mistake. Conversely, a bare silent timeout
> carries no application information at all -- it is a reachability symptom,
> not a verdict.

## 1. `550 Bad HELO - Host impersonating domain name [<domain>]`

- Source: ticket T-BFFFC987 (customer-quoted session with an Exim peer).
- Layer: **peer mail server, application layer** (anti-impersonation policy).
- Cause: the client's HELO/EHLO announces a hostname that looks like a
  domain the sending host does not own (library default, misconfigured
  mail client, or a web host name colliding with a registered domain).
- Handling (manual, customer side):
  1. Set the sending application's HELO/EHLO identity to a proper FQDN that
     the sending IP legitimately owns (PTR alignment helps; note custom PTR
     is not self-service on ECS IPs -- see unblock-application-path.md).
  2. Align SPF/DNS for the announced name, retry.
  3. If it persists, the receiving provider's postmaster must confirm the
     exact policy element -- this is their side.
- Explicitly NOT: a reason to apply for a port-25 unblock.

## 2. `503 STARTTLS command used when not advertised`

- Source: ticket T-BFFFC987 (same session).
- Layer: **peer application layer / TLS negotiation mismatch.**
- Cause: the client issues STARTTLS although the server's EHLO extensions
  do not advertise it (wrong security mode for the port/provider).
- Handling: switch to implicit TLS (SSL) on 465, or match the client's
  encryption mode (`SMTPSecure`-style settings) to what the server
  advertises on 587. Customer-side configuration change only.
- Note the companion failure in the same ticket: `STARTTLS command failed`
  / "Could not connect ... STARTTLS" -- same layer, same handling.

## 3. `451 Timeout.` (after a `220 ... ESMTP` banner)

- Source: ticket T-8E8AD7A5 (overseas-region instance, domestic provider).
- Layer: **peer application layer / provider policy or link quality.**
- Cause: provider-side greylisting/throttling, or degraded cross-border
  path; the server greets then stalls the session.
- Handling: capture the full transcript; retry with delay; ask the
  provider whether the source IP is throttled; when the instance region
  and provider are on opposite sides of a national border, hand the link
  leg to the cross-border diagnosis flow (see
  references/smtp-block-diagnosis__handoff-boundaries.md), or send via a same-side host/provider
  (that ticket resolved by moving to a domestic provider endpoint).
- Key inference guard: `Connected` + `451` on the SAME target proves TCP
  reachability -- never loop back to "the port is blocked".

## 4. `javax.mail.internet.AddressException: Illegal address`

- Source: ticket T-E561A8DF.
- Layer: **customer code / mail-product usage**, not the network.
- Cause: malformed recipient/sender address string rejected by the client
  library before any SMTP conversation.
- Handling: fix address formatting in the sending code (manual). If a
  managed mail product is involved, route to that product's support.
- Out of this skill's diagnosis; recognize and hand off.

## 5. `no permission to use this IP address` (unblock-application error
text; the console localizes this wording)

- Source: ticket T-384967AE (customer applied as the main account and the
  form rejected the IP; agent's whole fix was "use the VPC public IP
  address" -- it then worked).
- Layer: **unblock-application eligibility** (IP form), not connectivity.
- Handling:
  1. Run the entry script: its `DescribeInstances` pre-check reports the
     public-IP form (fixed VPC public IPv4 / EIP / classic / none).
  2. Reference the VPC-mode public IPv4 in the application.
  3. If an EIP is involved, verify its association with the instance at
     application time.
- The definitive list of eligibility constraints lives in
  references/smtp-block-diagnosis__unblock-application-path.md.

## 6. Silent patterns (no application text at all)

- `Connection timed out` / telnet hangs on :25 only -> platform block
  candidate; needs the 465/587/443 control readings (port-policy-matrix.md).
- `Connection refused` on a SEND test to :25 -> the remote provider refused
  (their policy) -- reachable, not blocked by us.
- `Connection reset` mid-session on 465/587, intermittent -> possible link
  or peer behavior; packet-level work is explicitly out of scope -- hand a
  material list to human support (failure window, transcript, customer
  capture, port matrix).
- Receive-side `refused` + nothing listening on the host -> guest MTA not
  bound, or container port never published (ticket T-065FBFCF: root cause
  was a Docker container not exposed to the host).

## Signature quick table

| Text (customer-visible) | Layer | One-line handling |
|--------------------------|-------|-------------------|
| `550 Bad HELO - Host impersonating domain name` | peer app | fix HELO identity, then provider |
| `503 STARTTLS command used when not advertised` | peer app | match TLS mode to port/provider (465 implicit) |
| `451 Timeout.` after banner | peer app / link | transcript, provider, cross-border handoff |
| `Illegal address` / AddressException | customer code/product | fix address string |
| `no permission to use this IP address` (apply form) | eligibility | VPC public IPv4 pre-check + re-apply |
| silent timeout on 25 only | platform block (probable) | control-port readings, then policy + application |
| timeout on 25 AND 465/587, 443 fine | customer config | SG egress + guest firewall self-check |
| banner then close on 465/587 | reachable; session refused | provider side / cross-border |
