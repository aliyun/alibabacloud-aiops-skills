# Academic Research Scene Configuration Manual

## Scene Characteristics

Academic/research platforms face unique bot management challenges:

**Legitimate user behavior heavily overlaps with bots**:
- Researchers access APIs from cloud vendor VMs (AWS/GCP/Azure/Alibaba Cloud, etc.)
- Use Python scripts to make batch API calls for data analysis
- Use development tools (Postman, curl, etc.) to debug endpoints
- Access from around the world with widely distributed IPs

**Traditional bot rules cause significant false positives**:
- IDC intelligence database blocks legitimate researchers accessing from cloud VMs
- Script client detection blocks legitimate Python/CLI calls
- Development tool rules block debugging tools like Postman
- Geolocation spoofing detection blocks overseas users using VPNs

## Core Principle

The bot management principle for academic scenarios is fundamentally different from other scenarios: **rather let some through than falsely block any**.

Reason: Academic platform user bases are small but high-value; a single false positive could interrupt important research.

## Recommended Configuration

### Protection Scene Definition

When creating a Bot-Web protection template, set the protection target to "Custom Match Conditions" and specify the API paths and web page paths that need protection. It is recommended to configure separate protection policies for pure API endpoints and web pages.

### Action Selection Principles

| Rule Type | Recommended Action | Reason |
|-----------|-------------------|--------|
| IDC / request sequence / threat intelligence | captcha (slider) | Normal users can pass verification |
| AI crawlers / spoofed spiders / known malicious tools | block (block) | Clearly malicious, no verification opportunity given |

### Recommended Rules to Enable

| Rule | Action | False Positive Risk | Description |
|------|--------|---------------------|-------------|
| AI-powered protection engine | block | Medium | Self-learning abnormal features, low false positive rate |
| Browser probe | captcha | Low | Detect non-browser environments |
| Device spoofing detection | captcha | Low | Hardware/browser/OS spoofing |
| Known malicious crawlers (chatgpt/perplexity/Meta, etc.) | block | Low | Known LLM crawlers |
| Spoofed spider detection | block | Low | Crawlers disguised as search engine spiders |

### Rules Not Recommended for Enablement

| Rule | Reason |
|------|--------|
| suspicious_idc_azure | Microsoft data centers have normal user traffic |
| suspicious_idc_tencent | Tencent data centers have normal user traffic |
| suspicious_idc_huawei | Huawei data centers have normal user traffic |
| suspicious_idc_aliyun | Alibaba Cloud data centers have large volumes of normal user traffic |
| suspicious_idc_aws | No baseline data, cannot rule out academic platform cloud VM access risk |
| suspicious_idc_gcp | No baseline data, cannot rule out academic platform cloud VM access risk |
| suspicious_idc_kingsoft | Very low hit rate (2 times/2h), cannot rule out normal users |
| web_suspicious_request_sequence_ip_path_excessive | Normal users browsing multiple pages will also trigger, high false positive risk |
| suspicious_threat_intelligence_db | Very low hit rate (4 times/2h), cannot rule out false positives |
| malicious_crawler_python | Academic platforms have legitimate Python API calls |
| web_device_spoofing_network | Geolocation spoofing hits are very low (3-59 times/2h), cannot rule out normal users |
| suspicious_development_tool_* (10 rules) | Academic sites have legitimate API call scenarios; enabling will affect normal integrations |

### Rate Limiting Policy

| Rule | Condition | Action | Description |
|------|-----------|--------|-------------|
| API endpoint IP rate limiting | Single IP > 100 times in 60 seconds | captcha | Threshold higher than other scenarios to avoid blocking batch computation tasks |
| Unauthenticated high-frequency access | No Authorization and > 30 times in 60 seconds | captcha | |
| Abnormal UA | UA is empty or exactly matches known bots | block | Use User-Agent match field |

Rate control notes: CC-type rules trigger immediately when the threshold is reached within the statistical period, without waiting for the period to end. After a statistical subject enters the blacklist, continued triggering of the rule will refresh the blacklist timeout.

### Canary Recommendations

The canary period for academic scenarios is recommended to be longer (7-14 days), for the following reasons:
1. Academic users have diverse usage patterns, requiring longer observation periods
2. Different research groups may have different API call patterns
3. Overseas users have different access time distributions compared to domestic users

Canary dimensions support IP, custom Header, custom parameters, custom Cookie, Session, and web UMID. Canary takes effect by dimension rather than by random percentage, making it suitable for rolling out by research group or department.

---

## SDK Integration Notes

If the academic platform is primarily an API service (not web pages), Web SDK integration may not be applicable. In this case:
1. Rely on built-in Bot detection rules (rules that do not depend on SDK), such as IDC intelligence, crawler client detection, etc.
2. Configure request feature-based rate limiting through advanced custom rules (JA3/JA4 fingerprints, Client-ID, and other match fields do not depend on SDK)
3. Integrate with the API Security module for unauthorized access detection

If the academic platform also has web management pages, those pages should integrate the Web SDK (automatic or manual integration) to support JS verification and slider verification. After SDK integration, `ssxmod_itna` / `ssxmod_itna2` / `ssxmod_itna3` Cookies will be implanted in the Header.

---

## Traffic Analysis

Use the traffic analysis feature (basic data viewable without enabling Bot Management) to observe the following dimensions:
- Malicious bot/suspected bot/friendly bot trends
- Traffic classification TOP IPs and rule-hit TOP IPs
- JA3/JA4/HTTP2 fingerprint top statistics
- Top 20 client identifiers

If access volumes for specific Client IDs or JA3/JA4 fingerprints are abnormally high, targeted blocking can be configured through advanced custom rules.
