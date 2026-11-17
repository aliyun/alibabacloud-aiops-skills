# Listener Type and Certificate Placement (Scenario A)

Scope: "my SSL certificate does not take effect on the load balancer",
"the certificate console cannot see my CLB instance", "the site still shows
the old certificate". This module is knowledge for the agent; every
corrective step below is performed BY THE CUSTOMER in their own console or
on their own server. This skill never changes any configuration and never
logs into any instance or panel.

> Source discipline: the layer-4 / layer-7 placement rules and the
> certificate-service visibility behavior below are distilled from real
> support tickets of this tier. Official SLB/CLB documentation URLs for
> these topics are PENDING verification (this batch's doc search returned no
> load-balancer product docs) -- never invent a URL; cite only the links
> listed at the bottom of this file.

## Core rule: the listener protocol decides where the certificate lives

| Listener protocol | TLS termination point | Where the certificate is configured |
|---|---|---|
| TCP / UDP (layer 4) | The backend ECS application | On EVERY backend ECS server, inside the application that terminates TLS (Nginx, Tomcat, IIS, or a panel such as BT panel) |
| HTTP (layer 7, no TLS) | None | An HTTP listener has no certificate field; serve HTTPS by adding an HTTPS listener (customer action in the SLB console) |
| HTTPS (layer 7) | The load balancer | On the listener itself in the SLB/CLB console (select the certificate, save, verify) |

Why a layer-4 listener behaves this way: a TCP listener forwards raw TCP
segments and cannot read or terminate TLS, so the encrypted handshake reaches
the backend untouched -- only the backend application can hold the
certificate. (Ticket-sourced caliber; official doc link pending.)

## Why the certificate service "cannot see" a CLB instance

When the CLB listener for that port is TCP (layer 4), the CLB is not a valid
deployment target for the cloud certificate deployment flow, which is why
the instance does not appear in the deployable-instance list. This is not a
permissions bug and redeploying will not help; install the certificate on
the backend servers instead (rule `CERT-L4` / `CERT-DEPLOY-VISIBILITY`).

## Decision flow

1. Ask the customer (or read from their console self-check): the listener
   protocol and port of the affected entry point. Console path: SLB/CLB
   console -> Instances -> Listeners (read the Protocol column).
2. Protocol unknown -> run the entry script with `--symptom certificate` and
   no `--listener-protocol`: it prints BOTH branches without guessing.
3. TCP/UDP -> rules `CERT-L4` + `CERT-DEPLOY-VISIBILITY`: certificate goes
   to every backend ECS application; the cloud certificate deployment to the
   CLB will never take effect.
4. HTTPS -> rule `CERT-L7`: update/select the certificate on the listener in
   the SLB console (steps for the customer).
5. HTTP -> the listener cannot serve TLS at all; to serve HTTPS the customer
   adds an HTTPS listener, then step 4 applies.

## Customer-executed steps: replace the certificate on backend ECS

These steps are OUTPUT ONLY. The customer runs them; this skill then
evaluates what the customer returns.

- Nginx (Linux): copy the new certificate + private key to the server; point
  `ssl_certificate` / `ssl_certificate_key` at the new files in the server
  block that serves the domain; check syntax (`nginx -t`); reload Nginx.
  Repeat on EVERY backend server behind the listener.
- Tomcat: replace the keystore or update the connector certificate
  configuration, then restart the Tomcat service.
- IIS (Windows): import the new certificate in the IIS Manager (Server
  Certificates), then edit the HTTPS binding of the site to select it.
- BT panel: upload the new certificate for the site in the panel and apply;
  panel-managed Nginx/Apache then reloads with the new certificate.
  Background reading: https://help.aliyun.com/zh/ecs/user-guide/purchase-a-linux-instance-and-deploy-bt-panel-from-the-console.md

## Re-verification (customer-executed, read-only in nature)

- From a browser or CLI on the customer side: open `https://<domain>` and
  inspect the served certificate chain and validity dates, e.g.
  `openssl s_client -connect <domain>:443 -servername <domain>` and check
  the `notAfter` date; repeat several times because a layer-4 listener
  distributes connections across ALL backend servers -- every backend must
  serve the new certificate or clients intermittently see the old one.
- The customer returns the observed validity dates; the entry script records
  them; this skill never claims "the certificate is effective" without that
  returned evidence.

## Security notice (MANDATORY wording in customer-facing replies)

- This skill never asks for panel/instance account credentials and never
  accepts an authorization to log into a server on the customer's behalf.
- If the customer pasted a password or private key into the conversation or
  ticket: advise them to change/rotate it immediately and never send secrets
  in plaintext through support channels.

## Common customer misconceptions (call these out explicitly)

- "Uploading the certificate to the platform means it is effective" -- for a
  layer-4 listener it can never take effect at the LB layer.
- "One backend is enough" -- with multiple backends, every server must carry
  the new certificate.
- "The certificate service hiding my instance is a bug" -- it is the
  documented applicability boundary of the deployment flow.

## Cited documents (verified links only)

- BT panel deployment background: https://help.aliyun.com/zh/ecs/user-guide/purchase-a-linux-instance-and-deploy-bt-panel-from-the-console.md
- IIS on Windows background: https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-a-windows-instance-and-build-an-iis-service.md

All other calibers in this file are ticket-sourced; mark them as such when
relaying and do not attach unofficial URLs.
