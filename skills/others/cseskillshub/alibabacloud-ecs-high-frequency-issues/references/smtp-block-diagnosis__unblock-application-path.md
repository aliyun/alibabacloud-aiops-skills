# Port-25 Unblock Application Path -- Facts, Entry, Eligibility, Honesty

Scope: everything about the CONSOLE application workflow for outbound TCP 25.
This skill NEVER submits, tracks, or promises an application: there is no
public API to query application history or review state, and review decisions
belong entirely to the reviewing specialists. What this skill CAN do is
pre-check eligibility so a customer is not sent into a form that will reject
them, and set correct expectations about the outcome.

## 1. The unified statement to relay (identical for every customer)

1. By default, new ECS instances do not provide outbound TCP port 25; this is
   the platform anti-spam policy, and allowing 25 in a security group does
   NOT override it (ticket T-C0B877F2 pattern: customer had egress allowed
   and still failed).
2. An unblock application can be submitted from the console; a specialist
   reviews it. Review takes about 1 business day and the result is delivered
   **by email** to the account contact. Approval is NOT guaranteed
   (`[dialogue]` ticket T-BFFFC987 agent verbatim).
3. The Port-25 Usage Service Agreement limits an unblocked port 25 to
   **connecting to third-party SMTP servers**. Self-hosted MTA direct
   delivery to remote MX hosts is outside that scope: a compliant-looking,
   honestly-declared direct-MX application was refused with the reviewer
   note "unsupported for this host's port 25 unblock; use an external mail
   provider's 465 port; enterprise mail or mail-push services may use 80 or
   465" (`[dialogue]` ticket T-0DC2E989, verbatim review outcome).
4. Ports 465 (implicit TLS) and 587 (STARTTLS) are NOT restricted and need
   no application at all. The most common real fix is moving submission to
   465/587 with provider credentials.
5. IPv6: opening port 25 over IPv6 is **not supported**; IPv4 or 465 are the
   only paths (`[dialogue]` ticket T-F418FAF1).
6. PTR/rDNS: custom reverse DNS for an ECS public IP is not self-service
   (`[summary]` ticket T-043B7B7E) -- providers that require a matching PTR
   cannot be satisfied with an ECS IP alone; plan an external mail service.
7. Regions outside the Chinese mainland: policy and application behavior are
   **UNCONFIRMED** (conflicting ticket reports). Tell the customer to consult
   the official limits document and attempt an honest application; do not
   promise either way.

## 2. Eligibility pre-check list (before touching the console)

| Check | Source of truth in this skill | Pass condition |
|-------|-------------------------------|----------------|
| Instance exists and is Running | entry script (`DescribeInstances` / `DescribeInstanceStatus`) | Running |
| Public IP is a VPC-mode public IPv4 | entry script IP-form verdict (`DescribeInstances` fields: network type, fixed public IP / EIP) | VPC fixed public IPv4 or EIP; classic-network IP is a known rejection cause (ticket T-384967AE: applying with the VPC public IPv4 fixed the "no permission to use this IP address" error) |
| Target path is IPv4 | customer facts (an IPv6 target can never be unblocked) | IPv4 |
| Use case within the agreement (relay via third-party SMTP) | customer's own honest description | relaying, not direct-MX |
| Main account or a RAM principal that can see/submit | `sts_token.py` identity output | sub-accounts needing the flow may lack console permissions -- RAM authorization is a different problem (hand off per handoff-boundaries.md) |

Every "pass" above is a pre-check, not a guarantee: the reviewer decides.

## 3. Console entry (path description first, URL only as a hint)

- Navigation: sign in to the console -> the security-control section ->
  the "Port 25 unblock application" tool (found in the more-tools area).
- The previous-generation direct link (`yundun.console.aliyun.com` with the
  old `sc` page) was **verified broken** by a real customer: the root now
  lands on an unrelated product page (`[dialogue]` ticket T-0DC2E989).
- The new path `https://yundun.console.aliyun.com/?p=scnew#/moreTools` was
  given by the support agent and confirmed working **by that customer at
  that time** -- treat console deep links as volatile: prefer the navigation
  description and the official document, and verify before circulating.
- Official application document:
  https://help.aliyun.com/zh/document_detail/56130.html
- Policy basis documents:
  https://help.aliyun.com/zh/ecs/product-overview/limits
  https://help.aliyun.com/knowledge_detail/37353.html

## 4. Materials the customer needs for the form (manual submission)

1. Instance id and its **VPC-mode public IPv4**.
2. The REAL use case, stated exactly as it is.
3. Agreement consent (Port-25 Usage Service Agreement).
4. A contact email that will receive the review result.

**Honesty rule (mandatory wording when guiding):** never invent or inflate
the stated purpose to pass review; the agreement scope is enforced in
review, misdeclared use cases get refused (and can re-expose the account to
policy action). The correct move for an out-of-scope use case is an
alternative below, not a different story in the form.

## 5. While the application is pending -- what this skill cannot see

- Application history / review state: NO public query API (support agents
  read it from an internal console; that is not reproducible here). The
  customer checks their own console page and the result email.
- If a customer reports "approved but still cannot send": re-run the entry
  script with fresh port readings -- approved-but-still-failing is usually
  (a) provider-side rejection (application layer), (b) the guest MTA or
  container never listening/mapped, or (c) an egress rule change. Evidence
  T-065FBFCF (unblocked, inbound still down -- Docker port unmapped).

## 6. Alternatives when 25 stays blocked (the real unblock for most workloads)

| Path | Port | Notes |
|------|------|-------|
| Third-party SMTP submission with account credentials (any provider: enterprise mail, Gmail/163/QQ SMTP, etc.) | 465 implicit TLS / 587 STARTTLS | No application needed from the platform; sample + demo: https://help.aliyun.com/zh/cloud-web-hosting/use-cases/encrypted-using-ssl-port-465-to-send-email |
| Managed transactional mail service (e.g. the platform's mail-push product) | 80/465 | Product configuration is out of this skill's scope -- hand off |
| Corporate/enterprise mailbox relay | provider-specified | Same handoff rule |
| IPv6-only targets | -- | 25 impossible; 465 with IPv4/hostname path |

Do not turn these into promises: relay endpoints, quotas, and provider
policies belong to the respective products.
