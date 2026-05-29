# General Anti-Crawl Scene Configuration Manual

## Scene Characteristics

The general anti-crawl scene applies to websites without a specific industry attribute. The main bot risks include:
- Content/data scraping (prices, articles, images, etc.)
- Server bandwidth saturation
- Credential stuffing/brute force on login pages
- SMS/email interface abuse

## Tiered Configuration Path

### Tier 1: Zero Cost (No Bot Module Required, Enterprise WAF Sufficient)

**Web Core Protection - Custom Rules**

Configure JS verification for the root path `/`. The HTML file returned by the root path has the most associated resources and is a primary target for crawlers.

JS verification is based on the POW (Proof of Work) mechanism: WAF returns an HTML page containing a JS challenge generation algorithm, the browser loads the JS challenge page, generates encrypted parameters, adds them to the Cookie, and resends the request. WAF verifies the parameters are correct and forwards to the origin server. The default WAF rule sets the string validity period to 30 minutes per IP. Upon passing verification, WAF sets `acw_sc__v2` in the response header Set-Cookie.

This configuration is supported with a WAF Enterprise edition purchase; no additional Bot protection add-on module is required.

### Tier 2: Bot Module - Web (Requires Bot Management Add-on Module)

Prerequisite: Web SDK must be integrated first. Automatic integration is one-click enablement (ALB/MSE/APIG/FC/SAE do not support automatic integration and require manual integration). Manual integration requires obtaining the SDK code and placing it before all `<script>` nodes on the page.

#### Recommended Rules to Enable

| Rule | Action | False Positive Risk | Description |
|------|--------|---------------------|-------------|
| Browser probe | captcha | Low | Detect developer tools/simulators/environment anomalies |
| Device spoofing - hardware info | captcha | Low | |
| Device spoofing - network & geolocation | captcha | Low | |
| Device spoofing - browser properties | captcha | Low | |
| Device spoofing - OS & environment | captcha | Low | |
| Crawler client detection | block or captcha | Low | Choose based on attack intensity |
| Script client detection | block or captcha | Low | |
| IDC data center policy | captcha | Medium | Slider for all except Alibaba IDC |
| AI-powered protection engine | block | Medium | Automatically learns abnormal features |

#### Action Selection Recommendations

- Other pages (JS can be injected): Configure JS verification first, upgrade to slider if bypassed
- Static file pages: Bot rules + slider (SDK cannot be injected). Check "Exclude Static Files" when creating the template
- Login pages: JS verification + slider

#### Not Recommended for Enablement

| Rule | Reason | Recommendation |
|------|--------|----------------|
| Crawler threat intelligence IP database | ISPs package IPs into pools that get rented by hackers; hackers contaminate IPs causing them to be flagged; when IPs are reassigned to normal users, WAF will falsely block them | Enable observation (monitor) during normal periods, switch to captcha during promotions |
| Crawler whitelist (friendly_crawler_*) | Official crawlers (e.g., Sogou) can generate millions of requests in one morning | Customers should customize whitelist with specific crawler IP lists as needed |
| Session anomaly (web_session_anomaly) | High false positive risk, public egress networks may trigger false blocks | Disabled by default |

### Tier 3: Bot Module - App (If App Exists)

App protection targets natively developed iOS or Android apps (excluding H5 pages within apps).

| Rule | Action | Description |
|------|--------|-------------|
| Signature anomaly detection | block | Enabled by default |
| Repackaging detection | block | |
| Device environment detection (root/simulator/multi-instance, etc.) | captcha | |

The app side does not support JS verification (no browser JS environment). Available actions include block, monitor, slider, strict slider, and origin tagging.

### Tier 4: Static File Specific

Static files cannot have Web SDK injected (resource loading and SDK insertion run in parallel in the browser). Only built-in Bot detection rules + slider can be used.

Recommended configuration:
1. Browser probe → captcha
2. Device spoofing detection (4 items) → captcha
3. Crawler client detection → block or captcha
4. Script client detection → block or captcha
5. IDC data center policy → captcha (exclude Alibaba IDC)

---

## Dynamic Token (Advanced)

When JS verification is bypassed, upgrade to dynamic token (token challenge).

Token challenge capabilities stronger than JS verification:
1. Collects client environment information; when anomalies such as WebDriver are detected, requires re-verification
2. Signature algorithms support rotation; when one algorithm is compromised, switch to a new one immediately

Verification logic: When a client request matches a rule, WAF returns an HTML page with a dynamic token. The browser generates encrypted parameters, adds them to the request URL parameters, and resends the request. WAF verifies the parameters are correct and forwards to the origin server. It is recommended to enable during critical protection periods (e.g., minutes before an event starts).

---

## Protection Effectiveness Reference

After configuring rules across 3 directions (login page slider, static files Bot rules + slider, other pages Bot rules + JS protection), the blocking ratio is between 85% and 95%.

## Canary Verification

1. Set all actions to `monitor` (observation only), run for 24-48 hours
2. Use the rule canary feature to apply rules in a small scope by IP or custom Header dimension
3. Use traffic analysis to view malicious bot/suspected bot/friendly bot trends and top rule-hit IPs
4. Check whether any flagged top IPs/UAs are legitimate users
5. After confirming no false positives, gradually switch to formal actions following the canary switch SOP in SKILL.md

## Best Practices

1. **Configure whitelists**: Add trusted IPs to the whitelist
2. **Canary testing**: Use the rule canary feature to apply rules in a small scope by IP or custom Header dimension
3. **Analyze test results**: Review security reports and logs, use traffic analysis to view malicious bot/suspected bot/friendly bot trends
4. **Apply to production**: Adjust to target actions after confirming the false positive rate is acceptable
5. **Continuous monitoring and optimization**: Regularly review traffic analysis TOP data, add targeted policies based on newly discovered attack patterns
