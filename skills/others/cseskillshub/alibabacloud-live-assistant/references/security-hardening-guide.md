# Security Hardening Guide (Customer-Facing)

Hardening guidance to hand to the user after `scripts/live_theft_handler.py`
locates traffic abuse or an unprotected live domain. This skill is read-only:
every action below must be performed by the user in the ApsaraVideo Live
console or via their own tooling — never executed by this skill.

Security overview (official documentation):
https://help.aliyun.com/zh/live/user-guide/security-overview/

## Priority order

| Priority | Measure | Effect |
|----------|---------|--------|
| P0 | Enable URL authentication (Type A recommended) | Root fix: unsigned ingest/playback URLs are rejected |
| P1 | Configure an IP blacklist | Block known abusive source IPs |
| P2 | Configure Referer-based hotlink protection | Restrict playback request origins |
| P2 | Enable ingest callbacks | Detect abnormal pushes in real time |
| P3 | Configure bandwidth/traffic caps and billing alerts | Prevent a future anomaly from silently inflating the bill |

## 1. URL authentication (Type A `auth_key`)

- Root cause of most live traffic theft: with URL authentication disabled,
  anyone can use the ingest/playback domains and the owner pays the traffic.
- Recommend enabling **Type A** authentication on both the ingest and the
  playback domains. Type A appends `?auth_key={timestamp}-{rand}-{uid}-{md5hash}`
  to the URL; expired or forged URLs are rejected at the edge.
- Choose a sensible validity window; the URL generator in this skill adds the
  configured `ali_auth_delta` clock-skew tolerance automatically.
- If abuse continues although authentication is enabled, treat it as a key
  leak or URL redistribution: rotate the key immediately and investigate the
  sources (the theft report's Top URL/Referer data helps here).
- Documentation: see the URL authentication section of the security overview
  page linked above.

## 2. Referer-based hotlink protection

- Restrict playback requests to expected Referer values (whitelist) and/or
  block empty Referers if the business allows it.
- **Cross-check the business scenario first**: download-style players, some
  SDKs, and direct API clients legitimately send an empty Referer — a blind
  empty-Referer block can break real viewers. Only recommend it when the
  playback is browser-embedded.
- Documentation: see the Referer blacklist/whitelist section of the security
  overview page linked above.

## 3. IP blacklist

- Add the abusive IPs collected in the theft report (`top_ips` of the
  `live_theft_handler.py analyze` output) to the domain IP blacklist.
- Prefer blocking confirmed high-frequency abusers; avoid broad /8-style
  blocks that may hit real viewers.
- Documentation: see the IP blacklist section of the security overview page
  linked above.

## 4. Rate / bandwidth limiting and alerts

- Configure bandwidth or traffic limits on the live domain so a sudden abuse
  spike is capped instead of billed.
- Enable billing alerts so anomalous traffic is noticed within hours, not at
  invoice time.
- Documentation: see the bandwidth-cap and usage-alert sections of the
  security overview page linked above.

## 5. Communication template

When notifying the user, keep this structure (mirrors the SOP output of
`live_theft_handler.py guide`):

1. Problem summary — domain, analysis window, log volume analyzed.
2. Billing impact — abnormal period and the root cause (authentication
   disabled or key leaked).
3. Authentication status — current `auth_type` and the risk-window caveat
   (the query reflects the status now, not necessarily during the abuse).
4. Abuse evidence — Top IPs, Top URLs, anomaly features (single-IP
   dominance, empty-referer ratio, non-2xx ratio).
5. Recommendations — the P0~P3 list above, with the documentation link.

Never promise refunds or compensation from this skill; billing disputes are
handled through the user's official support channels.
