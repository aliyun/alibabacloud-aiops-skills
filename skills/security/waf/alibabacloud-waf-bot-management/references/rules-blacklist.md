# Rules Not Recommended for Enablement

## Overview

The following rules are prone to false positives in specific scenarios and are not recommended for default enablement. Before enabling, evaluate based on the scenario and closely monitor hit patterns during the gray-release period.

---

## IDC Intelligence Library Rules

### suspicious_idc_aliyun (Alibaba Cloud Data Center)

Not recommended scenarios: Customers have Alibaba Cloud ECS/Function Compute or similar resources; internal services or employees may access from Alibaba Cloud IDCs.
Recommendation: First review hit IPs via SLS, exclude known self-owned cloud resource IP ranges before enabling.

### suspicious_idc_aws / suspicious_idc_gcp (AWS/GCP Data Centers)

Not recommended scenarios: Academic research platforms, enterprise-grade API services. Researchers and enterprise users may legitimately invoke APIs from AWS/GCP VMs.
Recommendation: Not recommended for academic and LLM API scenarios. Retail and general anti-crawling scenarios can enable based on actual conditions.

### suspicious_idc_azure (Microsoft Data Center)

Not recommended scenarios: Enterprise users using Azure services or SaaS products such as Microsoft 365.
Recommendation: First observe hit data to confirm whether legitimate enterprise traffic exists.

### suspicious_idc_tencent / suspicious_idc_huawei (Tencent/Huawei Data Centers)

Not recommended scenarios: Customers with multi-cloud architecture where some services are deployed on Tencent Cloud or Huawei Cloud.
Recommendation: Same as Alibaba Cloud IDC — first exclude known IP ranges.

### suspicious_idc_kingsoft (Kingsoft Cloud Data Center)

Not recommended scenarios: Nearly all scenarios. Hit volume is typically very low (2 hits/2h), resulting in low benefit but non-zero false positive risk.
Recommendation: Do not enable by default.

---

## Threat Intelligence Rules

### suspicious_threat_intelligence_db (Crawler Threat Intelligence IP Database)

Not recommended scenarios: High-frequency adversarial engagement phases (e.g., late stages of major promotions). ISPs package IPs into pools that get rented by attackers; after attackers pollute these IPs and they get flagged, the IPs are reassigned to normal users, causing WAF to incorrectly block them.
Recommendation: Enable in monitor mode during normal operations. During major promotions, switch to captcha instead of block, and continuously monitor for false positives.

---

## Request Sequence Rules

### web_suspicious_request_sequence_ip_path_excessive (IP Accesses Too Many Paths)

Not recommended scenarios: Nearly all scenarios. Normal users browsing multiple pages will also trigger this. In API scenarios, normal API calls may also access multiple paths.
Recommendation: Do not enable by default. If it must be enabled, set the threshold relatively high and validate closely during the gray-release period.

---

## Script/Development Tool Rules

### malicious_crawler_python (Python Tool Traffic)

Not recommended scenarios: Academic research platforms. Researchers widely use Python to call APIs for data analysis and experiments.
Recommendation: Do not enable for academic scenarios. For LLM API scenarios, decide based on whether the customer has legitimate Python invocation requirements. Retail and general anti-crawling scenarios can enable.

### suspicious_development_tool_* (Development Tools, 10 rules total)

Not recommended scenarios: Academic platforms, LLM API services. Legitimate developers use tools like Postman and Insomnia to debug APIs.
Recommendation:
- Academic scenarios: Do not enable any
- LLM API scenarios: Do not enable (or enable in monitor mode only)
- Retail/General anti-crawling scenarios: Can enable

### malicious_crawler_okhttp (Okhttp Tool Traffic)

Not recommended scenarios: Android apps commonly use Okhttp as the HTTP client. If the app and web share the same domain, enabling this rule will block normal app traffic.
Recommendation: Only enable when it is confirmed that no legitimate app traffic passes through WAF.

---

## Device Spoofing Rules

### web_device_spoofing_network (Network and Geolocation Spoofing)

Not recommended scenarios: Academic platforms, platforms with many overseas users. When hit volume is very low (3-59 hits/2h), the benefit of enabling is low, and overseas users using VPNs may be incorrectly flagged.
Recommendation: First observe hit data; if hit volume is very low, do not enable.

---

## Session Rules

### web_session_anomaly (Session Anomaly)

Not recommended scenarios: Nearly all scenarios. High false positive risk; public egress networks (e.g., corporate NAT, campus networks) may trigger false positives.
Recommendation: Do not enable by default. If needed, first set the action to monitor for observation.

---

## Crawler Whitelist Rules

### friendly_crawler_* (Friendly/Legitimate Crawlers)

Not recommended scenarios: Full allowlisting is not recommended for any scenario. Official crawlers (e.g., Sogou) may generate millions of requests in a single morning; although classified as "friendly," they still impose load on the business.
Recommendation: Do not enable all friendly crawler whitelist entries. Customers should define custom whitelists for specific crawler IP lists they need, and keep the rest at default or disabled.

---

## Okhttp Rules

### malicious_crawler_okhttp (Okhttp Tool Traffic)

Not recommended scenarios: Android apps commonly use Okhttp as the HTTP client. If the app and web share the same domain, enabling this rule will block normal app traffic.
Recommendation: Only enable when it is confirmed that no legitimate app traffic passes through WAF. In app+web shared domain scenarios, traffic must be separated using custom match conditions to distinguish app and web traffic.

---

## AI Intelligent Protection

### ai_intelligent_protection (AI Intelligent Protection Engine)

Note: This rule is overall recommended for enablement (officially disabled by default but recommended to enable), though it carries a moderate false positive risk. The AI engine performs automatic learning across dimensions such as path sequence anomalies, device anomalies, and malicious group behavior. It performs well in scenarios with stable traffic patterns but may produce false positives when new services are launched or traffic patterns change abruptly.
Recommendation: After enabling, observe for 24-48 hours in gray-release mode. Confirm there are no false positives before putting into full effect.

---

## Scenario Quick Reference Table

| Rule | LLM API | Retail Promotion | General Anti-Crawl | Academic Research |
|------|:---------:|:-------:|:-------:|:-------:|
| IDC-aliyun | Enable after observation | Enable | Enable | Do not enable |
| IDC-aws/gcp | Do not enable | Case by case | Case by case | Do not enable |
| IDC-azure/tencent/huawei | Enable after observation | Case by case | Case by case | Do not enable |
| IDC-kingsoft | Do not enable | Do not enable | Do not enable | Do not enable |
| threat_intelligence_db | Monitor | Phased captcha | Enable | Do not enable |
| request_sequence | Do not enable | Do not enable | Do not enable | Do not enable |
| python | Case by case | Enable | Enable | Do not enable |
| development_tool_* | Do not enable | Enable | Enable | Do not enable |
| malicious_crawler_okhttp | Case by case | Case by case | Case by case | Do not enable |
| spoofing_network | Case by case | Enable | Enable | Do not enable |
| session_anomaly | Do not enable | Do not enable | Do not enable | Do not enable |
| friendly_crawler_* | Custom whitelist | Custom whitelist | Custom whitelist | Default allow |
