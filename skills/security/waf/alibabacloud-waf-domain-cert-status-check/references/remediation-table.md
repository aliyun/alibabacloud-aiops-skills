# Remediation Table (finding → customer guidance)

Map each reported finding to guidance. **All write actions are executed by the customer** — this skill only
supplies the console path and never calls a write API. Console navigation paths keep their original Chinese
console wording so the customer can find them in the UI.

| Finding (status) | What it means | Guidance (console path only) |
|------------------|---------------|------------------------------|
| `expired` | The bound certificate's expiry is already past; HTTPS trust errors are happening now | Deploy a valid replacement immediately: renew in CAS (`SSL 证书续费`) or upload a CA certificate (`上传证书`), then `云产品部署` → WAF, or edit the domain in WAF (`接入管理` → `CNAME 接入` → `编辑` → `更新证书`) and select it |
| `expiring` (≤ warn_days) | The certificate expires within the window | Start renewal now (buying/issuing + domain validation + deployment takes days): CAS renew/upload → deploy to WAF; then re-run this check to confirm the new expiry |
| `healthy` | Expiry is beyond the window | No action; note the expiry date for planning. Optionally enable `证书托管` (hosting) for auto-renewal — preconditions apply |
| `no-cert-bound` | HTTPS listening is on but no certificate is bound | Bind a CA-issued certificate covering the domain (wildcard/SAN must match): WAF `接入管理` → `CNAME 接入` → `编辑` → `更新证书` |
| `https-not-enabled` | HTTP-only listener; nothing to expire | Informational only. If HTTPS is intended, enable it and bind a certificate; otherwise no action |
| `expiry-not-retrieved` (CertId not in CAS) | WAF references a certificate CAS cannot resolve | Check the certificate source: if deleted from CAS, re-upload; if cross-account, share it into this account or re-upload; then re-run the check |
| `expiry-not-retrieved` (cross-account / region mismatch) | The certificate lives in another account or the wrong CAS region | Re-upload or share the certificate into this account, in the CAS region matching the WAF region (cn-hangzhou / ap-southeast-1); then re-run |
| Symptom is a trust / handshake / chain error, not a date | Likely an incomplete certificate chain rather than expiry | Out of this skill's scope: re-deploy the certificate **with the full chain** (root + intermediate + domain cert); route to a certificate-chain / TLS troubleshooting flow |
| Customer wants a self-signed certificate on WAF | WAF requires a CA-issued certificate | Self-signed is **not** supported for WAF onboarding; obtain a CA certificate (a free Let's Encrypt certificate works), or terminate TLS elsewhere (e.g. an API gateway). Never promise a self-signed cert can be bound |
| Frequent manual renewals across many domains | Renewal is easy to miss | Suggest CAS `证书托管` (hosting / auto-renewal) and `云产品部署` for automatic redeploy to WAF — state the preconditions, do not assert it is already active |
| Customer asks this skill to renew / replace / deploy | Write action | Decline the write; hand over the console path above and offer to re-run the read-only check afterwards to verify |

Console navigation paths (original Chinese wording):

```
C-1 数字证书管理服务控制台 → 证书管理 → SSL 证书管理 → 续费 / 上传证书
C-2 数字证书管理服务控制台 → 证书管理 → SSL 证书管理 → 云产品部署 → 选择 WAF
C-3 WAF 控制台 → 接入管理 → CNAME 接入 → 目标域名 → 编辑 → 更新证书
C-4 数字证书管理服务控制台 → 证书管理 → 开启证书托管（自动续费）
```

## Escalation criteria

- A CertId that resolves in neither CAS nor the customer's records, and the source cannot be identified →
  advise opening a ticket with the raw CertId and domain attached.
- The customer reports HTTPS trust errors while every certificate shows `healthy` with a valid chain →
  the symptom is not an expiry problem; escalate to a certificate-chain / TLS troubleshooting flow rather
  than forcing an expiry verdict.

## Official documentation

| Topic | Link |
|-------|------|
| SSL certificate renewal | https://help.aliyun.com/zh/ssl-certificate/ssl-official-certificate-renewal |
| Upload / sync / share SSL certificate | https://help.aliyun.com/zh/ssl-certificate/upload-an-ssl-certificate |
| Deploy SSL certificate to cloud products (incl. WAF) | https://help.aliyun.com/zh/ssl-certificate/deploy-ssl-certificates-to-alibaba-cloud-services |
| Certificate hosting (auto-renewal) | https://help.aliyun.com/zh/ssl-certificate/enable-certificate-hosting |
| WAF 3.0 CNAME onboarding & HTTPS certificate | https://help.aliyun.com/zh/waf/web-application-firewall-3-0/add-a-domain-name-to-waf-in-cname-record-mode |
| WAF 2.0 add a domain | https://help.aliyun.com/zh/waf/web-application-firewall-2-0/user-guide/add-a-domain-name-to-waf |
