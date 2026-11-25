# Triage decision tree — SSL certificate application and deployment on ECS

The customer states a symptom; the entry script collects evidence and routes.
This module mirrors the branch tables embedded in `scripts/axes/ssl_cert_deployment/_constants.py`
and adds the self-check lists no OpenAPI covers yet. Trigger discipline:
this skill activates only when the wording co-occurs with certificate / SSL /
HTTPS / port 443 / ACME vocabulary; a bare "network unreachable" or "the
website will not open" without any certificate signal belongs to
`alibabacloud-ecs-diagnose` (dedup boundary, overlap measured at 0.41).

## Inputs to collect first (tier spec section 6.3)

| Input | Required | Notes |
| --- | --- | --- |
| Instance id or public IP | yes | first question support always asks; never guess |
| Region id | yes | never guessed; decides the mainland-versus-overseas network lens |
| Domain name(s) | yes for any effectiveness check | batch-friendly: several hosts in one run |
| Web server type | yes for deployment branches | nginx, IIS, Apache, BaoTa panel, 1Panel, containerized nginx |
| Certificate source | helpful | Alibaba Cloud free or purchased certificate, acme.sh, certbot, Posh-ACME, other CA |
| Purpose | yes | issuance failure / deployment not effective / expiry or mismatch / HTTPS unreachable / product rules |

## Tree

```
Entry symptom
+-- issuance or renewal failure (tool text: context deadline exceeded,
|   connection reset, validation timeout)
|   +-- region inside mainland China AND endpoint address overseas
|   |   (Let's Encrypt answers inside 172.65.0.0/16, the Cloudflare edge)
|   |       -> cross-border path branch: NOT a platform block; alternatives:
|   |          Alibaba Cloud free certificate, another CA, a working proxy,
|   |          off-peak retry, test from another region
|   +-- domestic validation endpoint (alidns.aliyuncs.com) unreachable
|   |       -> instance egress branch: security group OUTBOUND rules, guest
|   |          firewall, proxy env vars (inbound acceptance proves nothing
|   |          about outbound, ticket T-233E37E1)
|   +-- DNS-01 validation times out on A/AAAA lookup (.cn domains)
|   |       -> CA-side resolver cache branch: wait or swap validation method
|   +-- toolchain fault (BaoTa / 1Panel / Posh-ACME config)
|           -> keep the panel, change only the CA
+-- deployed but still not secure / visitors still see the old certificate
|   +-- outside-in TLS view serves a certificate whose CN/SAN does not
|   |   include the requested host, and it belongs to another site on the
|   |   same server (domain/certificate mismatch)
|   |       -> SNI fallback branch: the `server` block whose `server_name`
|   |          covers the requested host has no ssl_certificate /
|   |          ssl_certificate_key (or no `listen 443 ssl`), so the default
|   |          server block answers with ITS certificate. This is the FIRST
|   |          ruling; add the pair on the matching block (ticket
|   |          T-F9AA3466). Certificate SAN coverage and DNS/CDN copies come
|   |          after this check.
|   +-- outside-in TLS view still shows old issuer or serial
|   |       -> load branch: walk the web-server checklist (import is not
|   |          load); reload is a manual step after a snapshot
|   +-- outside-in view shows a cert whose window misses now
|   |       -> err_cert_date_invalid branch (see references/ssl-cert-deployment__error-codes.md)
|   +-- nginx or panel reports a permission error on the key file
|           -> metadata branch: ONE confirmed `stat` / `ls -l` reading
|              (approved whitelist; ticket T-B5F37974 path)
+-- whole site down including plain HTTP after a renewal failure
|       -> forced-HTTPS redirect amplification (ticket T-411B8BA7):
|          disabling the redirect is a MANUAL customer step
+-- port 443 unreachable from outside
|   +-- public DNS answer differs from the instance public address
|   |       -> stale A record branch: traffic never arrives (ticket
|   |          T-BF6A05D6); customer fixes the record, then re-verify
|   +-- handshake reset or closed -> err_connection_closed branch:
|   |       security group inbound 443, plus the hidden deny rule that
|   |       blocks the server's own address (ticket T-438814FA)
|   +-- TCP timeout with correct resolution
|   |       -> nothing listening or inbound gap: listener and firewall
|   |          readings are customer-run until the whitelist extension
|   +-- everything consistent and still broken
|           -> escalate to a human session (snapshot plus authorization)
+-- product-rule question (free certificate entry, quota, domain levels,
|   DV phone validation)
|       -> references/ssl-cert-deployment__aliyun-cert-service-faq.md, with the confidence tag
+-- non-certificate symptom co-occurring in the ticket
        -> references/ssl-cert-deployment__handoffs.md (SMTP ports, filing checks, qualification
           documents, moved remote-login ports, disk tiers, deployment
           service disputes)
```

## Security group self-check list (console; rule edits stay manual)

No verified security-group query API exists for this tier, so the customer
(or a human session) reads the console:

1. Inbound: an `Accept` rule allowing TCP 443 from the intended sources.
2. Inbound: scan for a higher-priority `Drop` rule that covers 443 —
   including rules that deny the server's OWN public address (the hidden
   trap in ticket T-438814FA that breaks self-tests and same-box calls).
3. Outbound: the default is accept-all; if custom rules exist, issuance
   needs TCP 443 egress to the CA endpoint and TCP 443 egress to the DNS
   provider API when DNS-01 is used.
4. Guest firewall (firewalld / iptables / Windows Firewall) is a second,
   independent layer: use the readings printed by
   `references/ssl-cert-deployment__guest-diagnostics-runbook.md`.
5. Closing a port inbound affects outside visitors only; local processes
   keep working (support wording).

## Verdict vocabulary used by the report

| Verdict | Means | Typical customer wording |
| --- | --- | --- |
| `resolved` + `MISMATCH` drift | DNS answers differ from the instance address | "the site is down but my server is fine" |
| `valid` | verified handshake and current window | "is my new certificate live?" |
| `cert-window-invalid` | expired or not yet valid (err_cert_date_invalid) | "browser says the certificate expired" |
| `cert-expiring-soon` | valid now, inside the warning window | "it still works but says expiring" |
| `cert-window-unparsable` | handshake verified, served validity dates unreadable | state "expiry not returned"; never guess a date |
| `cert-verify-failed` | the chain itself is rejected (unknown issuer, self-signed) | "your browser shows a security warning" |
| `cert-name-mismatch` | served certificate does not cover the host (often the default server block answering after SNI fallback) | "certificate is not valid for this site" |
| `non-tls-response` | port answers without TLS | "https returns a 400 Bad Request page" |
| `connection-reset` / `connection-refused` / `handshake-failed` | err_connection_closed shapes | "the connection was reset" |
| `connect-timeout` | no TCP answer | "it just spins until it fails" |
| `handshake-timeout` | TCP opened, TLS never completed | "opens then hangs on the lock icon" |
| `dns-empty` / `dns-error` / `dns-failed` | no usable answer for the host name | "the domain does not resolve" |
| `blocked` | the probe host itself cannot egress | report honestly, fall back to customer-run checks |

## Misconceptions this tier must correct in every reply (ticket wording)

1. Inbound acceptance means outbound works — directions are evaluated
   separately.
2. Alibaba Cloud blocks Let's Encrypt — it does not; mainland-to-overseas
   edge paths degrade on their own (verified by engineers from several
   machines, ticket T-75A1E320).
3. Other overseas sites load, so the cloud must be at fault — per-endpoint
   probing is required.
4. Importing a certificate file makes it effective — binding plus reload
   are separate steps (tickets T-382FDB28, T-08D625D0).
5. The certificate still has weeks of validity, so it is innocent —
   expiry and key pairing are independent (ticket T-B5F37974).
6. The certificate changed, so we were breached — support wording:
   intruders plant processes or deface pages, they do not rotate
   certificates.
7. The served certificate does not list my domain, so the certificate must
   be wrong — when the certificate belongs to another site on the same
   server, the usual cause is SNI fallback: the matching `server` block has
   no TLS pair and the default server answers. Check the block first;
   reissuing the certificate fixes nothing (ticket T-F9AA3466).
