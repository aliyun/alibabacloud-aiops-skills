# Retail Promotion Scene Configuration Manual

## Scene Characteristics

Core bot risks faced by retail e-commerce during promotions:
- Scalper hoarding: Automated tools place bulk orders at the moment of sale, preventing normal users from purchasing
- Price scraping: Competitors scrape product prices for dynamic pricing
- Coupon abuse: Bulk registration/coupon claiming, reducing benefits for real users
- SMS verification code abuse: Spamming SMS interfaces to consume communication resources
- Promotion traffic surge: Bot + real traffic combined causes origin server crashes

## Protection Chain (Three Phases)

```
DDoS layer peak absorption → WAF Bot identification → Business risk control integration → Origin server protection
```

## Phase 1: 2 Weeks Before Promotion - Basic Protection

### Preparation

1. Confirm Bot Management module is activated (Advanced/Enterprise/Ultimate editions support a 7-day free trial, once per account)
2. Deploy Web SDK (web) + App SDK (app)
3. Enable WAF log service, add bot collection fields, and enable indexing
4. Confirm WAF QPS specifications meet promotion business needs (including bot traffic)
5. Confirm web services are onboarded on the Access Management page

### Protection Scene Definition

Create a Bot-Web protection template and select the protection target based on your business:
- **Global effect**: Suitable for scenarios with only web/H5 environments
- **Custom match conditions**: Suitable for scenarios with both app/mini-programs, or for protecting specific business endpoints (login, flash sales)

Match conditions consist of match fields + logical operators + match content. Multiple conditions are combined with logical AND. It is recommended to create separate templates with stronger policies for key pages such as login, order placement, and shopping cart.

### Basic Rule Configuration

| Rule | Action | False Positive Risk | Description |
|------|--------|---------------------|-------------|
| AI-powered protection engine | block | Medium | Self-learning based on historical traffic |
| Crawler threat intelligence database | monitor (observation) | Medium | Observe for 2 weeks before promotion, switch to captcha 1 week before, keep captcha during promotion (do not block, ISP IP pool contamination may cause false blocks) |
| IDC intelligence database | captcha | Medium | Exclude Alibaba IDC (customers may have cloud business calls) |
| Browser probe | captcha | Low | Detect developer tools/simulators |
| Device spoofing detection (4 items) | captcha | Low | Hardware/network/browser/OS spoofing |
| Script client detection | block | Low | Python/Java/Go, etc. |
| Crawler client detection | block | Low | Various known crawlers |

### CAPTCHA Mode Selection

- **Daily protection**: Use JS verification, 30-minute exemption after passing verification, better user experience
- **Critical periods** (e.g., minutes before promotion starts): Switch to token challenge, signature algorithms support rotation, can be switched immediately if compromised. Options include signature timestamp anomaly and WebDriver attack

### Risk Identification (Phone Number Reputation Database)

For retail scenarios, it is recommended to enable the risk identification feature, which blocks scalper accounts based on WAF's built-in phone number reputation database. Risk labels include: suspected secondary account, fraud risk, spam registration, marketing fraud, scalper account. Cost: 0.05 CNY per query.

### Peak Rate Limiting

Configure rate limiting thresholds based on origin server performance to ensure business stability. Requests exceeding the limit enter a waiting queue or are directly rejected.

### Key Endpoint Rate Limiting

Configure IP/device-level rate limiting for key endpoints such as login, order placement, and shopping cart pages. Use frequency control rules; statistical subjects support IP, custom Header, custom parameters, Cookie, Session, Body parameters, UMID, and account.

---

## Phase 2: 1 Week Before Promotion - Fine-tuning

### Behavioral Analysis Rules

| Rule | Condition | Action |
|------|-----------|--------|
| Single device multi-account switching | > 5 account switches in 60 seconds | block |
| Single account multi-device switching | > 5 device switches in 60 seconds | block |
| Single account multi-IP switching | > 5 IP switches in 60 seconds | block |
| Early morning peak persistent login | Login during early peak for N consecutive days | monitor |

The above rules are implemented through advanced custom rules, using the deduplication statistics capability of frequency control.

### Region Blocking

If the business serves only domestic users, overseas region blocking can be scheduled during early morning peak hours (e.g., 6:45-7:30). Use the "effective by time period" or "effective by cycle" feature in the effective mode. Some customers cannot enable region blocking long-term due to compliance requirements; scheduled tasks can be used for timed enable/disable.

---

## Canary Verification

Canary verification for retail promotion scenarios is carried out in phases, aligned with the promotion timeline:

1. **Phase 1 canary** (2 weeks before promotion): Set all basic rule actions to `monitor` (observation only), run for 24-48 hours and review hit data
2. **Canary dimension verification**: Use the rule canary feature to apply rules in a small scope by IP or custom Header dimension. Canary dimensions support IP, custom Header, custom parameters, custom Cookie, Session, web UMID, and app UMID
3. **Simulated attack testing**: Use your own test IP to simulate attacks, verify that rules trigger correctly, and confirm that normal users are not affected
4. **Switch to formal actions after confirming no false positives**: Gradually switch from monitor to captcha or block following the canary switch SOP in SKILL.md. If the target action is block, it is recommended to first switch to captcha, observe for 4 hours, then upgrade to block
5. **Phase 2 canary** (1 week before promotion): Set behavioral analysis rules and region blocking to monitor first, run for 24 hours, then switch

---

## Phase 3: During Promotion - Continuous Confrontation

### SLS Log Analysis

Monitor the following metrics in real-time (see `sls-query-templates.md` for details):
- Abnormal device/IP/account count trends
- Policy hit rate (which rules are taking effect)
- Access/blocked traffic trends
- Abnormal calls to quick-booking APIs

### Origin Tagging Strategy

For requests that hit suspicious indicators but are uncertain, instead of blocking directly, use origin tagging (bypass action, adding a special tag in the request header) so the business side can identify them and place them in a low-priority waiting queue. Benefits:
- Does not expose protection policies (attackers don't know they've been identified)
- No false positives on normal users
- Consumes attacker resources without yielding valid results

### Confrontation Effectiveness Metrics

1. **Business-integrated bot metrics**: Abnormal devices/IPs/accounts, abnormal rates
2. **Data analysis-based bot feature metrics**: IPs/accounts that only access specific endpoints
3. **Behavior-based anomaly metrics**: Persistent login, multi-account switching, multi-device switching
4. **Policy protection trend metrics**: Hit volume trends, false positive rate, coverage rate

### Standardized Deliverables

| Deliverable | Frequency | Description |
|-------------|-----------|-------------|
| AntiBot Daily Report | Daily | Access/protection data analysis across dimensions |
| Bot Monitoring Alerts | Real-time | Anomaly metric alerts based on SLS |
| Security Policy Tracking Sheet | Ongoing | Track new policy effectiveness, dynamic adjustments |
| Bot Governance Metrics | Weekly | Dashboard tracking |
| Monthly Report | Monthly | Phased governance summary and trend forecast |

---

## Slider Policy Selection

| Page Type | Recommended Slider Type | Reason |
|-----------|------------------------|--------|
| Login page | Standard slider (captcha) | 30-minute exemption after verification, better user experience |
| Order/payment page | Strict slider (captcha_strict) | Verification every time, strongest security |
| Product detail page | JS verification (js) | Minimal impact on user experience |
| Homepage/static page | Bot rules + slider | Static files cannot have SDK injected |

After enabling JS verification, WAF sets the `acw_sc__v2` Cookie upon passing verification; after enabling the slider, it sets `acw_sc__v3`.

## Rules Not Recommended for Enablement

| Rule | Reason | Recommendation |
|------|--------|----------------|
| Crawler whitelist (friendly_crawler_*) | Official crawlers (e.g., Sogou) can generate millions of requests in one morning | Do not enable all; customers should customize whitelist with specific crawler IP lists as needed |
| Crawler threat intelligence IP database (threat_intelligence_db) | ISP IP pool contamination causes false blocks | Phased approach: monitor for 2 weeks → captcha 1 week before → captcha during promotion, do not block |
| Session anomaly (web_session_anomaly) | High false positive risk, public egress networks may trigger false blocks | Disabled by default |
