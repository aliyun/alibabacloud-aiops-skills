# Attack Level x Protection Strategy Matching Matrix

## Five-Level Attacker Classification

### Level 1: Script Kiddies

Characteristics: Use off-the-shelf tools (curl/wget/requests) or simple scripts with no evasion capabilities.

Identification methods:
- User-Agent exposes the tool name
- No browser environment; JS challenge fails immediately
- Fixed and high-frequency request patterns

Protection strategy: JS challenge alone is sufficient to block. Configure JS challenge for root paths via WAF core protection - custom rules; no Bot module required.

### Level 2: Tool Developers

Characteristics: Write their own Python/Go/NodeJS scripts, can forge basic UA, but have no browser environment.

Identification methods:
- Script client detection (malicious_crawler_* labels)
- TLS fingerprint anomalies (JA3/JA4 fingerprints can identify non-browser clients)
- Fixed request patterns

Protection strategy: Bot management module's script client detection + crawler client detection, with action set to block. Combine with advanced custom rules for JA3/JA4 fingerprint blocking.

### Level 3: Browser Automation

Characteristics: Use browser automation tools such as Selenium/Puppeteer/Playwright; can execute JS.

Identification methods:
- Webdriver detection (web_webdriver label)
- Browser probe (web_browser_probe label)
- Device spoofing detection
- No interaction traces / trace replay
- JS challenge can execute but token challenge may fail

Protection strategy: Bot management module's device behavior detection rules (browser probe + device spoofing + Webdriver + no interaction traces), with action set to captcha. Dynamic token challenge (token challenge) is more effective than JS challenge. Web SDK integration is required.

### Level 4: Professional Crawling Teams

Characteristics: Build their own crawling platforms, use proxy IP pools, device fingerprint spoofing, and CAPTCHA solving services.

Identification methods:
- IDC intelligence library (proxy IPs are mostly data center IPs)
- AI intelligent protection engine (behavioral pattern recognition)
- Rate control (even if individual rules are bypassed, overall behavior remains anomalous)
- Device spoofing detection (advanced spoofing still leaves traces)

Protection strategy: Multi-layer rule combination + rate control. IDC intelligence library (captcha) + AI intelligent protection (block) + multi-device/multi-account switching detection (block). Use origin-pass markers to coordinate with business risk control. Continuous adversarial engagement; rules need periodic adjustment based on new attack patterns.

### Level 5: Scalpers / Business Fraud

Characteristics: Clear objectives (flash sale sniping / bonus abuse), use customized tools, with manual assistance to bypass CAPTCHAs.

Identification methods:
- Behavioral analysis (single device with multiple accounts, single account with multiple devices/IPs, persistent login)
- Phone number reputation library (scalper accounts, spam registrations)
- Rate anomalies (traffic spikes at the moment of sale)
- Abnormal request sequences (only target API endpoints, no browsing behavior)

Protection strategy: Advanced custom rules for behavioral analysis + risk identification (phone number reputation library) + strict slider on critical endpoints (captcha_strict). Enable token challenge before major promotions. Use region blocking and scheduled tasks for timed activation/deactivation. Integrate with business risk control systems.

---

## Attack Level x Protection Method Quick Reference Matrix

| Protection Method | Level 1 | Level 2 | Level 3 | Level 4 | Level 5 |
|---------|:------:|:------:|:------:|:------:|:------:|
| JS Challenge (zero cost) | Effective | Effective | Ineffective | Ineffective | Ineffective |
| Script/Crawler Client Detection | - | Effective | - | - | - |
| Browser Probe + Device Spoofing | - | - | Effective | Partial | - |
| Webdriver Detection | - | - | Effective | Partial | - |
| Dynamic Token Challenge | - | Effective | Effective | Partial | Partial |
| IDC Intelligence Library | - | - | - | Effective | Partial |
| AI Intelligent Protection Engine | Effective | Effective | Effective | Effective | Partial |
| Rate Control/Throttling | Partial | Partial | Partial | Effective | Effective |
| Behavioral Analysis (multi-account/device/IP switching) | - | - | - | Partial | Effective |
| Phone Number Reputation Library | - | - | - | - | Effective |
| Strict Slider (captcha_strict) | - | - | - | Partial | Effective |
| Region Blocking | - | - | - | Partial | Partial |
| Origin-Pass Markers + Business Risk Control | - | - | - | Effective | Effective |

"Effective" indicates that the method provides good blocking performance against attackers at that level. "Partial" indicates it may be effective but requires combination with other methods. "-" indicates the method is not a primary protection approach for this level.

---

## Progressive Protection Escalation Recommendations

Gradually escalate protection intensity based on actual attack conditions:

1. **Daily Baseline Protection**: JS Challenge (zero cost) + Script/Crawler Client Detection (block) + AI Intelligent Protection Engine (block)
2. **Browser Automation Attacks Detected**: Add Browser Probe + Device Spoofing Detection (captcha) + Integrate Web SDK + Upgrade to Token Challenge
3. **Proxy IP Pool Attacks Detected**: Add IDC Intelligence Library (captcha) + Rate Control
4. **Professional Crawlers/Scalpers Detected**: Fully enable all Bot rules + Behavioral Analysis + Phone Number Reputation Library + Strict Slider + Origin-Pass Markers + Business Risk Control integration
5. **High-Risk Periods (Major Promotions/Events)**: In addition to the above, enable scheduled tasks for timed enforcement + Region Blocking + Real-time SLS alert monitoring
