# Issuance egress facts — reaching ACME and validation endpoints

Every statement here carries its ticket source; ticket-derived numbers are
tagged and must be relayed with the confidence tag. This is the evidence
sheet behind the cross-border branch of the decision tree.

## What the tickets actually observed

1. **The dominant root cause of issuance failure on mainland instances is
   the public path to overseas CA edge nodes, not any cloud policy.**
   Support confirmed, from several test machines at the time, that the
   Let's Encrypt endpoints were unreachable for everyone on that route,
   and explicitly: this "does not look like an Alibaba Cloud restriction";
   the trace had already left the cloud network (tickets T-75A1E320,
   T-BAA897DB, T-C3B1F4A7, T-A49EBFF0, T-6A73F6B0 — the latter four
   resolved with the same explanation plus an alternative path).
2. **Let's Encrypt fronts ACME behind Cloudflare edge space**:
   `acme-v02.api.letsencrypt.org` and the staging endpoint answer with
   addresses inside `172.65.0.0/16` — geographically overseas edge
   addresses even though the service name is American. The entry script
   resolves the endpoints and applies this range automatically.
3. **Domestic validation endpoints behave differently.** `alidns.aliyuncs.com`
   sits in Alibaba Cloud network space: if it is unreachable from the
   instance, the fault is the instance's own egress path — security group
   OUTBOUND rules, guest firewall, or proxy environment — not a
   cross-border issue (the T-233E37E1 family of symptoms).
4. **Inbound acceptance proves nothing about outbound reachability.** In
   ticket T-233E37E1 the customer had opened 80, 443 and the panel port
   inbound and still could not reach the CA. The two directions are
   separate rule sets.
5. **A reset is not a timeout.** err_connection_closed (immediate reset or
   handshake death) points to a local firewall, security software or an
   endpoint-side drop; a timeout points to the path. The telnet-style
   connect test versus curl split is the same method support used for the
   outbound direction in ticket T-3E637B73.
6. **CA-side factors exist beyond the network.** For `.cn` domains,
   "query timed out looking up A/AAAA" during DNS-01 validation was
   attributed to the CA's DNSSEC validation cache (ticket T-4AC3F65A):
   the fix is waiting or changing the validation method, never touching
   the instance.
7. **Panel toolchains inherit the same path.** BaoTa, 1Panel and Posh-ACME
   failures in these tickets were the same cross-border fault under a
   different GUI; support advice: keep the panel, switch the CA (apply an
   Alibaba Cloud free certificate and paste it into the panel), or retry
   off-peak.
8. **The platform does not block mail ports it is accused of**: outbound
   port 25 is limited by default while 465 and 587 are not platform-
   restricted (ticket T-3E637B73). That symptom itself is out of scope and
   hands off to the network and mail tiers — only the probing method is
   shared.

## Customer-facing conclusion wording for this branch

"Your region reaches the certificate authority's overseas edge nodes over
the public internet. That path is congested at times and no cloud-side
setting caused it; we verified the same timeout from independent machines.
Options that restore business immediately: apply a free certificate in the
SSL certificates console and deploy it, or use a CA whose endpoint is
reachable from your region, or (advanced) route the ACME client through a
working proxy. Panels such as BaoTa and 1Panel keep working — only the
issuing source changes."

## What this file does NOT claim

* No throughput numbers, no congestion models — none in evidence.
* No statement about specific third-party networks.
* The reachability verdict for a given moment always comes from a FRESH
  resolution and handshake (report mode), not from this sheet: edge
  addresses rotate.
