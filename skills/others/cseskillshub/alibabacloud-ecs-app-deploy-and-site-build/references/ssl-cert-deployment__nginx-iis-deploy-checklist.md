# Deployment-effectiveness checklists per web server (manual steps only)

The single root cause behind this branch family: **"the certificate file is
in place" is not the same fact as "the web service is serving it"**. Every
checklist below ends the same way — a rerun of this skill's outside-in TLS
check, which is the visitor's view and the only proof that counts. File
edits, binding changes, reloads and restarts are customer actions taken
AFTER a backup snapshot (the snapshot-first rule in SKILL.md).

## nginx (including panel-managed nginx)

1. When the served certificate belongs to another site on the same server
   (or the browser reports a name mismatch), start with SNI selection, not
   the certificate files: in the `nginx -T` dump find the `server` block
   whose `server_name` covers the requested host. That block MUST carry both
   `ssl_certificate` (fullchain) and `ssl_certificate_key` and must
   `listen 443 ssl`. If it carries neither, nginx hands the handshake to the
   default server block (the first `listen 443` block or the explicit
   `default_server`) and serves THAT block's certificate — the exact
   mechanism of ticket T-F9AA3466, where the requested subdomain had no TLS
   pair and the main domain's certificate was served. Fix this block first;
   reissuing or re-purchasing the certificate does not help.
2. Find every config actually loaded: `nginx -T` (effective dump — manual
   reading per the runbook) and note each `server` block with `listen 443`.
3. In EACH such block check the pair: `ssl_certificate` must point at the
   FULLCHAIN file (server certificate first, then intermediates), and
   `ssl_certificate_key` at the matching key. A correct main config with a
   stale include under `conf.d/` reproduces ticket T-08D625D0 exactly —
   the customer uploaded the right files at the right paths and nginx was
   still reading an old sub-config.
4. Verify the pair matches before touching the service: run the modulus
   comparison from the runbook; a mismatch is certificate-body territory
   (references/ssl-cert-deployment__triage-decision-tree.md, T3).
5. `nginx -t` must pass. Only then reload: `nginx -s reload` or the
   service-level reload — MANUAL customer step after the snapshot; state
   that a reload does not drop existing connections but a broken config
   would break the next restart.
6. Re-run the report; the served fingerprint and window must match the new
   certificate.

## IIS (Windows Server — ticket T-382FDB28)

1. Importing a PFX into the certificate store changes nothing on its own.
   Site, Edit Bindings, the HTTPS entry, Edit: the new certificate must be
   SELECTED in the SSL certificate list. This is the exact missed step of
   the source ticket.
2. Binding field format: the host name field takes the bare host, e.g.
   `www.example.com` — no trailing slash, no scheme. The same ticket shows
   the site going dark right after a malformed binding value was entered.
3. If two certificates share port 443 on one IP, Server Name Indication
   requires the per-site hostname field to be filled as above.
4. Applying: recycling the application pool or restarting the site is a
   MANUAL step after the snapshot.
5. Information-only store and binding views (`Get-ChildItem Cert:\...`,
   `Get-WebBinding`) are printed for the customer per the runbook; they
   are not dispatchable yet.

## Containerized nginx (acme.sh plus docker — ticket T-B5F37974)

1. The paths in `acme.sh --install-cert --key-file ... --fullchain-file ...`
   must be inside the mounted volume the container actually reads; a host
   path the container does not mount leaves nginx serving yesterday's pair.
2. The paired `--reloadcmd` (for example a `docker exec ... nginx -s
   reload`) is a SERVICE CHANGE: snapshot first, customer runs it.
3. On any renewed-cert outage, back the current files up to another
   directory and reissue before deeper digging — the working repair order
   of the source ticket; the modulus test names mismatch as the reason.
4. A certificate change is NOT itself evidence of intrusion: the ticket's
   closing support wording — intrusions plant processes or deface pages,
   they do not quietly rotate certificates. Suspected-compromise questions
   hand off to the security tiers.

## BaoTa panel

1. Site settings, SSL tab: confirm the panel shows the new issuer and
   expiry, then SAVE so the panel rewrites the vhost include.
2. If issuance inside the panel fails on the cross-border branch, keep the
   panel and paste an Alibaba Cloud free certificate into the custom
   certificate boxes (issuer swap, not toolchain surgery).
3. The Force-HTTPS switch interacts with renewal failure: with the switch
   on and 443 broken, the ENTIRE site fails, HTTP included — disabling the
   switch is a manual panel click, first aid per ticket T-411B8BA7.

## 1Panel

1. Website, certificate settings: note which CA and which DNS account the
   ACME profile uses; cross-account zones need a token valid in the zone's
   owning account (the timeout in ticket T-6A73F6B0 came from exactly this
   combination: instance in account A, sub-domain zone in account B).
2. Switch the CA inside the panel when the path branch fired; keep the
   panel configuration otherwise.

## Apache

1. `apachectl -S` lists vhosts and config files; check
   `SSLCertificateFile`, `SSLCertificateKeyFile`, `SSLCertificateChainFile`
   in every `VirtualHost *:443`.
2. `apachectl configtest` before loading; graceful restart stays manual
   after the snapshot.

## Closing every branch

The verification line is always the same: rerun
`python3 scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py --region-id <r>
--instance-id <i> --domain <host>` and compare the served `issuer`,
`valid until` and `days left` against the new certificate. "Deployed" is
something the outside-in view proves, never something inferred from a
successful file upload.
