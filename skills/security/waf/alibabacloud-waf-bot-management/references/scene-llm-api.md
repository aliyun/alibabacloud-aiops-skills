# LLM API Scene Configuration Manual

## Scene Characteristics

Core bot risks faced by LLM API services:
- API abuse: Attackers use scripts to make massive LLM API calls, consuming compute resources
- Model output scraping: Crawlers scrape model-generated content to train competing models
- Unauthorized access: Exploiting leaked AK/SK or weak credentials to call APIs
- Resource exhaustion attacks: High-frequency calls cause legitimate user API requests to be rate-limited

API traffic now accounts for nearly 90% of WAF traffic. The integration of API security and bot management is key for LLM scenarios.

## Protection Chain

```
API Security Module (asset discovery + risk identification) → Bot Management (abnormal call detection) → CC Protection (rate limiting as last resort)
```

## Protection Scene Definition

When creating a Bot-Web protection template, set the protection target to "Custom Match Conditions" and specify the API path prefix (e.g., `/api/v1/`). If both web pages and API endpoints exist, it is recommended to configure separate protection policies for API and web. You may check "Exclude Static Files".

## Recommended Configuration

### Bot Management - Basic Rules

| Rule | Action | False Positive Risk | Description |
|------|--------|---------------------|-------------|
| Script client detection (Python/Java/Go/NodeJS/C#/Okhttp/CLI) | block | Low | Script tools in LLM API scenarios are most likely malicious calls |
| Crawler client detection (chatgpt/perplexity/Meta, etc.) | block | Low | Known LLM crawlers |
| AI-powered protection engine | block | Medium | Automatically learns abnormal features and generates rules |
| IDC intelligence database | captcha | Medium | Enable but exclude the customer's own cloud resource IP ranges |

### Bot Management - Advanced Custom Rules

| Rule | Condition | Action | Description |
|------|-----------|--------|-------------|
| API endpoint IP rate limiting | Single IP requests > N times in 60 seconds | js (JS verification) | Set threshold based on normal business baseline |
| Unauthenticated high-frequency access | No Authorization/Bearer Token and > 10 times in 60 seconds | captcha | |
| Abnormal UA blocking | UA is empty or contains curl/wget/requests, etc. | block | Use User-Agent match field |
| Single device high-frequency calls | Single UMID requests > 50 times in 60 seconds | captcha | Requires Web SDK integration |
| JA3/JA4 fingerprint blocking | Matches known malicious TLS fingerprint | block | Use JA3/JA4 Fingerprint match field |

Rate control rule notes: CC-type rules trigger immediately when the threshold is reached within the statistical period, without waiting for the period to end. After a statistical subject enters the blacklist, continued triggering of the rule will refresh the blacklist timeout.

### Rules Not Recommended for Enablement

| Rule | Reason |
|------|--------|
| suspicious_idc_aws / suspicious_idc_gcp | Academic/enterprise users may legitimately call APIs from AWS/GCP VMs |
| suspicious_threat_intelligence_db | ISP IP pool contamination causes false blocks |
| suspicious_development_tool_* | Legitimate developers use tools like Postman to debug APIs |
| web_suspicious_request_sequence_ip_path_excessive | Normal API calls may also access multiple paths |

For the detailed not-recommended list, refer to `rules-blacklist.md`

### API Security Integration

1. Enable the API Security module → Automatic API asset discovery
2. Configure API security effective objects (enable in Policy Configuration - Effective Objects)
3. Monitor API security risk alerts: unauthorized access, AK/SK leaks, weak credentials
4. Monitor API security event alerts: abnormally high-frequency access, traversal scraping, malicious consumption
5. Upon discovering attack events, coordinate with Bot Management or CC Protection to configure blocking rules

API security event handling recommendations:
- Account brute force/credential stuffing → Add CC protection or enable Bot Management
- Malicious SMS consumption → Add CC protection or enable Bot Management
- Traversal data scraping → WAF blacklist + custom rules + Bot Management

## Canary Verification

1. Set all actions to `monitor` (observation only)
2. Run for 24-48 hours
3. Review API call logs to confirm that flagged requests are indeed malicious
4. Check whether legitimate developers/partners have been falsely flagged
5. After confirming no false positives, gradually switch to formal actions (monitor → captcha → block) following the canary switch SOP in SKILL.md
6. Use the traffic analysis page to view top rule-hit IPs, client type top statistics, and JA3/JA4 fingerprint top statistics

## Best Practices

1. **Configure whitelists**: Add trusted IPs (internal monitoring, CI/CD, partner fixed IPs) to the whitelist
2. **Canary testing**: First apply to non-production environments, or set observation mode, or enable rule canary to gradually increase traffic by IP dimension
3. **Analyze test results**: Review security reports and logs, pay attention to JA3/JA4 fingerprint top statistics in traffic analysis
4. **Apply to production**: Adjust to target actions after confirming the false positive rate is acceptable
5. **Continuous monitoring and optimization**: Regularly review traffic analysis and adjust policies based on attack changes
