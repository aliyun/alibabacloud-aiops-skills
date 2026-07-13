# UGC Application Hardening — Public UGC Site Security Checklist

> When `sku-sizing-questionnaire.md` Q-userdata=Yes (Q2a registration/payment OR Q2b upload, inferred from the description) or §4 Q7–Q10 any is "Yes" → advisor **must** output this checklist link + include "pre-launch mandatory items" in the prescription. The full checklist is **38 items across §1–§6** (§7 is the deploy-side landing subset, not separate items); cite the count as 38, not 24.

## 1. Identity & Authentication (derived from iron-rules #29)

| Item | Requirement | Failure Consequence |
|------|-------------|---------------------|
| Password hashing | argon2id (recommended) / bcrypt cost≥12 / scrypt N≥2^15. **Forbidden:** MD5/SHA1/SHA256 bare | DB leak → passwords instantly reversible |
| Registration CAPTCHA | Third-party (e.g., Alibaba Cloud CAPTCHA 2.0) or self-implemented slider; plain-text captcha **forbidden** | Bot mass-registration → credential-stuffing source |
| Email verification | Post-registration must click link before uploading; link expires in 24h | Fake accounts + spam content |
| Password reset | One-time token + 30-min expiry + same-IP rate limit | Brute-force reset via security questions |
| Session/Cookie | `Secure` + `HttpOnly` + `SameSite=Lax` (admin area uses `Strict`) | XSS session theft / CSRF |
| Multi-device login | At minimum record device list + email alert on login from new location | Account compromise undetected |
| Real-name verification (optional) | OPC context: if money/in-person meetings involved, strongly recommend Alibaba Cloud real-name OpenAPI | Black/gray market abuse |

## 2. Upload Content Safety

| Item | Requirement |
|------|-------------|
| File-type whitelist | `Content-Type` + file-header magic-bytes dual verification; **forbidden** to rely on extension alone |
| File size limit | Single file ≤ 10 MB (images) / 100 MB (video); total quota ≤ 1 GB/user |
| Content moderation | Integrate Alibaba Cloud Content Safety — image/video moderation (Green Net); hit porn/terrorism/prohibited → reject + flag user |
| EXIF stripping | Post-upload **must** remove GPS/camera serial/photographer; retain capture time (business need) |
| Thumbnail isolation | Full image: private ACL + thumbnail: public ACL; previews use thumbnail |
| Hotlink protection | OSS Referer whitelist + temporary signed URL (5-min validity) |
| DMCA process | Site must publish takedown contact email; respond to complaints within 48h |

## 3. Database & Query Security

| Item | Requirement |
|------|-------------|
| SQL injection | All parameterized queries; ORM preferred; **forbidden:** string concatenation |
| Sensitive field encryption | PII (email/phone/name/location) at-rest encryption (KMS or field-level AES) |
| Soft delete | 30-day recoverable retention after account deletion + audit log; after expiry **hard delete** (including OSS objects + cache) |
| Account-deletion cascade | Deleting user must cascade: photos, thumbnails, comments, likes, follow relationships, sessions, cookies |
| Backup encryption | RDS backups + OSS cross-region replication both encrypted |

## 4. Network & Transport

| Item | Requirement |
|------|-------------|
| HTTPS only | 80 → 301 → 443; HSTS 1 year + preload |
| Certificate | ESA free certificate or ACM; auto-renewal |
| CSP | At minimum `default-src 'self'` + business whitelist |
| CORS | Strict origin whitelist; **forbidden:** `Access-Control-Allow-Origin: *` |
| Rate limit | Registration 5/min/IP; upload 10/min/user; login 3/min/IP (failure counting) |
| Anti-bot | UA blacklist + behavioral analysis; malicious IP blocked 24h |
| EIP inbound | 80/443 from 0.0.0.0/0; SSH only MY_IP/32; management ports (22/3389) must whitelist IP |

## 5. Legal & Compliance

| Item | Requirement |
|------|-------------|
| Privacy policy page | Must have `/privacy`; list collected fields/purposes/retention/third-party sharing/deletion process |
| Terms of service | Must have `/terms`; user conduct rules + violation handling + liability disclaimer |
| Cookie consent | Entry banner; "necessary only" / "all" two-tier choice |
| ICP filing | Mainland China server + mainland access requires ICP filing; filing number displayed in footer |
| Public security filing | Some provinces require PSB filing within 30 days |
| Minor protection | Registration collects DOB; <18 triggers parental consent / content classification |
| Cross-border data | Involves overseas users/data leaving mainland → triggers PIPL cross-border assessment |

## 6. Monitoring & Incident Response

| Item | Requirement |
|------|-------------|
| Log retention | Application logs 30 days / security logs 6 months / audit logs 1 year |
| Anomaly alerting | Login failures > threshold / upload volume anomaly / OSS traffic spike / CPU anomaly |
| Backup testing | Monthly recovery drill |
| Incident response | Public security contact email + 24h response |
| User notification | Data breach → notify users + regulator within 72h |

## 7. OPC Deploy-Side Landing Checklist (deploy interlocks with advisor)

When advisor recommends a UGC SKU, the prescription template section must include:

```text
【上线前必做（UGC 公开站加固）】

- [ ] 部署完成后第一件事：把所有 admin 路由加白到 MY_IP/32
- [ ] OSS bucket ACL = private；缩略图独立 bucket public-read
- [ ] 接入阿里云内容安全（图片审核），费率 ${rate}
- [ ] 设置 EIP 入站 80/443，禁开 22/3389 给公网
- [ ] RDS 内网访问，禁公网；密码 16 位以上随机
- [ ] 部署 https + HSTS；ESA/Certbot 二选一
- [ ] 隐私政策页 /privacy + 服务条款 /terms 必备
- [ ] ICP 备案：${domain} → https://beian.aliyun.com
- [ ] 完整加固清单见 ugc-application-hardening.md
```
