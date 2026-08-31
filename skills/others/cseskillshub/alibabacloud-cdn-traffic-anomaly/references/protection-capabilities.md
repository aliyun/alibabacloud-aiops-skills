# CDN Protection Capabilities (what really exists)

Only recommend capabilities listed here. Recommending a non-existent CDN feature is a hard error. This skill is read-only: every item below is **manual guidance for the user**, never executed by the skill.

## Capabilities CDN actually has

### 1. Referer hotlink protection
- Black/whitelist on the HTTP Referer header; optional "allow empty Referer".
- Fits: embedded web resources (images/CSS/JS), downloads reached from your own pages.
- Does NOT fit: APP/client downloads, APK distribution, mini-programs, API calls — these clients send no Referer.
- Limit: Referer is client-forgeable; this is a basic defense only. For download-type URLs (.apk/.exe/.zip/.mp4) do NOT lead with Referer protection — prefer URL authentication.

### 2. URL authentication (signed URLs)
- Time-limited signed URL parameters; signatures expire automatically. Types A/B/C differ in signature format (path + timestamp + secret).
- Fits: high-value resources (video, installers, paid content), time-limited download links.
- Does NOT fit: permanently public resources; clients that cannot generate signed URLs with backend support.
- Limit: requires customer backend/APP integration (development cost).

### 3. IP blacklist/whitelist
- Block/allow by IP or IP range.
- Fits: attack sources concentrated on a few IPs/subnets.
- Does NOT fit: distributed attacks (2000+ IPs, low per-IP volume), proxy pools/botnets rotating IPs, attackers sharing NAT/enterprise egress with legitimate users.
- Limit: blacklist entry quota; manual upkeep cost.

### 4. UA blacklist/whitelist
- Block/allow by User-Agent string.
- Fits: attackers using obvious non-browser UAs (`python-requests`, `Go-http-client`, `curl`, `wget`).
- Does NOT fit: attackers spoofing mainstream browser UAs (indistinguishable from real users); legitimate custom-UA apps of your own.
- Limit: UA is freely forgeable. Always confirm the target UA is not legitimate business traffic before blacklisting.

### 5. Bandwidth cap
- Set a bandwidth ceiling; the domain goes offline (or falls back to origin) when exceeded.
- Fits: safety net against bill blow-up during theft/attack. Post-facto loss control; it does not stop the attack itself.
- **Every CDN domain should have a bandwidth cap configured** — this is the most basic cost safety net.

### 6. Remote authentication
- CDN forwards each request to the customer's auth server for allow/deny decisions.
- Fits: access control needing complex business logic (login state, entitlement checks).
- Limit: adds origin latency; depends on the availability of the customer's auth service.

### 7. Precise access control (URL-path level)
- URL-path-level rules for targeted restriction when a specific path is abused.

## Capabilities CDN does NOT have (never recommend as CDN features)

| Missing capability | Upgrade path |
|--------------------|--------------|
| Rate limiting / frequency control | Migrate to ESA (WAF frequency control) or use DDoS-pro |
| WAF rule engine | ESA or a dedicated WAF product |
| JS challenge / human verification | ESA WAF challenge actions |
| Bot management | ESA Bot management |
| Intelligent/intelligence-based anti-abuse | ESA one-click anti-abuse |
| Strong DDoS defense | DDoS-pro / SCDN-class products |
| Multi-condition custom rule engine | ESA WAF custom rules |

## Business-scenario decision matrix

| Business scenario | Referer protection | URL authentication | IP blacklist | UA blacklist |
|-------------------|--------------------|--------------------|--------------|--------------|
| Embedded web resources | Effective | Usable | Limited | Limited |
| Web page access | Effective | Hurts UX | Limited | Limited |
| APP downloads (.apk/.ipa/.exe) | NOT applicable | **Recommended** | Limited | Usually ineffective |
| Video / streaming | Partial | **Recommended** | Limited | Usually ineffective |
| API backends | NOT applicable | Usable | Limited | Limited |
| Large-file download sites | NOT applicable | **Recommended** | Limited | Usually ineffective |

## Recommendation decision rules

1. Determine the business scenario of the attacked URL first.
2. Exclude inapplicable measures per the matrix above.
3. Match the attack signature: IP concentrated → IP blacklist; distinguishable non-browser UA → UA blacklist; high-value large files → URL authentication.
4. When CDN capabilities are insufficient, say so honestly and point to ESA/DDoS-pro as the upgrade path.
5. Always add the safety net: bandwidth cap + billing alerts.
