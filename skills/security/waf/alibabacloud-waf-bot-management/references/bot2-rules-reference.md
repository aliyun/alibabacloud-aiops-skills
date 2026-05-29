# BOT 2.0 Rule Labels Quick Reference

## Web Protection Labels

Web protection templates contain three categories of rules: Malicious BOT, Suspected BOT, and Friendly BOT. Each rule can be independently toggled on/off and assigned an action.

### Malicious BOT Rules

| Label Name | Description | False Positive Risk | Notes |
|------------|-------------|---------------------|-------|
| web_browser_probe | Browser probe (dev tools/emulator/abnormal environment) | Low | Requires Web SDK |
| web_device_spoofing_os | OS and environment spoofing | Low | Requires Web SDK |
| web_device_spoofing_hardware | Device hardware info spoofing | Low | Requires Web SDK |
| web_device_spoofing_browser | Browser attribute spoofing | Low | Requires Web SDK |
| web_device_spoofing_network | Network and geolocation spoofing | Low | Not recommended when hit rate is very low; requires Web SDK |
| web_no_operation_trace | No operation trace detection | Low | Requires Web SDK |
| web_trace_replay | Trace replay detection | Low | Requires Web SDK |
| web_webdriver | WebDriver traffic detection | Low | Requires Web SDK |
| web_time_stamp_anomaly | Timestamp anomaly | Medium | Web pages open for over 2 hours without refresh may trigger false positives |
| web_sdk_version_anomaly | WebSDK version anomaly | Low | Users with manually integrated older versions may be at risk |
| malicious_crawler_meta | Meta-ExternalAgent crawler | Low | |
| malicious_crawler_perplexity | PerplexityBot crawler | Low | |
| malicious_crawler_chatgpt | ChatGPT LLM crawler | Low | |
| malicious_crawler_duckduck | DuckDuckBot crawler | Low | |
| malicious_crawler_apple | Applebot crawler | Low | |
| malicious_crawler_amazon | Amazonbot crawler | Low | |
| malicious_crawler_petal | PetalBot crawler | Low | |
| malicious_crawler_icc | ICC-crawler | Low | |
| malicious_crawler_python | Python tool traffic | Low | Academic platforms may have legitimate Python API calls |
| malicious_crawler_java | Java tool traffic | Low | |
| malicious_crawler_go | Go tool traffic | Low | |
| malicious_crawler_php | PHP tool traffic | Low | |
| malicious_crawler_nodejs | NodeJS tool traffic | Low | |
| malicious_crawler_csharp | C# tool traffic | Low | |
| malicious_crawler_okhttp | OkHttp tool traffic | Low | Native apps cannot enable OkHttp |
| malicious_crawler_cli | Command-line tool traffic | Low | |
| malicious_crawler_apitest | API testing tool traffic | Low | |

### Suspected BOT Rules

| Label Name | Description | False Positive Risk | Notes |
|------------|-------------|---------------------|-------|
| ai_intelligent_protection | AI intelligent protection engine | Medium | Abnormal path sequences, device anomalies, malicious groups, etc.; recommended to enable |
| spider_crawler_bot | Spider/crawler detection | Medium | |
| suspicious_threat_intelligence_db | Crawler threat intelligence IP database | Medium | ISP IP pool contamination may cause false blocks |
| web_operation_analysis | Operation behavior analysis | Medium | May cause false positives for users with low mouse sensitivity |
| web_access_analysis | Access behavior analysis | Low-Medium | Persistent non-collecting access, batch replay, etc. |
| web_session_anomaly | Session anomaly | High | Public egress networks may cause false positives |
| script_client | Script client | Low | Depends on business context |

### IDC Intelligence Database

| Label Name | Description | Default Status | Notes |
|------------|-------------|----------------|-------|
| suspicious_idc_aliyun | Alibaba Cloud data center | Enabled | Legitimate users may access from Alibaba Cloud VMs |
| suspicious_idc_tencent | Tencent Cloud data center | Enabled | Legitimate users may access from Tencent Cloud VMs |
| suspicious_idc_huawei | Huawei Cloud data center | Enabled | |
| suspicious_idc_azure | Microsoft Azure data center | Enabled | |
| suspicious_idc_aws | Amazon AWS data center | Enabled | Academic platform users may access from AWS VMs |
| suspicious_idc_gcp | Google GCP data center | Enabled | Academic platform users may access from GCP VMs |
| suspicious_idc_kingsoft | Kingsoft Cloud data center | Disabled | Hit rate is typically very low |

### Development Tools (10 rules, disabled by default)

Label names are prefixed with `suspicious_development_tool_*`, used for development tool detection. Academic/enterprise users may have legitimate API call scenarios; enabling these may disrupt normal integrations.

### Friendly Crawlers (allowed by default)

Label names are prefixed with `friendly_crawler_*`, including search engine spiders such as Google/Bing/Baidu. It is recommended to keep the default allow configuration.

---

## Bot Verification Rules

Web protection supports two bot verification modes:

**JavaScript Verification**: Suitable for low-intensity daily protection. Authenticated clients have all requests allowed through for 30 minutes (cookie-based mechanism). WAF returns an HTML page containing a JS challenge generation algorithm; the browser executes the JS to generate encrypted parameters and adds them to a cookie before resending the request.

**Token Challenge**: Suitable for high-intensity confrontation scenarios. Recommended to enable during critical protection periods (e.g., a few minutes before major promotional events). Options include signature timestamp anomaly and WebDriver attack. WAF returns an HTML page with a dynamic token; the browser generates encrypted parameters and adds them to the request URL parameters before resending the request.

---

## Action Types

| Action | Code | Description |
|--------|------|-------------|
| JS Verification | js | Returns JS code; after browser execution, traffic is allowed for 30 minutes |
| Block | block | Blocks the request directly and returns a block page |
| Monitor | monitor | Does not block; only logs |
| CAPTCHA | captcha | Returns a slider verification page; after passing, traffic is allowed for 30 minutes |
| Strict CAPTCHA | captcha_strict | Every request requires slider verification |
| Origin Tag | bypass | Passes hit information to the origin server via headers for business-side handling |

Notes:
- JS verification or slider verification only applies to synchronous requests; asynchronous requests (XMLHttpRequest/Fetch) require Web SDK injection
- When JS verification is enabled, WAF sets `acw_sc__v2` in the response Set-Cookie header upon successful verification
- When slider verification is enabled, WAF sets `acw_sc__v3` upon successful verification
- Crawler client, script client, AI intelligent protection, and similar rules do not support ALB/MSE/APIG/FC/SAE integration

---

## App Protection Labels

### Signature and Packaging Detection

| Label Name | Description | Default Status | Notes |
|------------|-------------|----------------|-------|
| app_signature_anomaly | Signature anomaly detection | Enabled | Cannot be disabled in 1.0; can be disabled in 2.0 |
| app_signature_expired | Signature expiration detection | Disabled | Configured within the signature anomaly detection label |
| app_custom_signature | Custom signing | Disabled | Configured within the signature anomaly detection label |
| app_repackaging | Repackaging detection | Enabled | |

### Device Environment Detection

| Label Name | Description | Default Status |
|------------|-------------|----------------|
| app_root | Rooted device detection | Enabled |
| app_emulator | Emulator detection | Enabled |
| app_multi_instance | Multi-instance detection | Enabled |
| app_cloud_phone | Cloud phone detection | Enabled |
| app_group_control | Group control detection | Enabled |
| app_abnormal_rom | Abnormal ROM detection | Enabled |
| app_hook | Hook framework detection | Enabled |

App-side actions are similar to Web-side actions, but JS verification is not supported (no browser JS environment on apps). Once app-side risk detection is enabled, JS verification cannot be selected as an action.

---

## Rule Canary Deployment

Protection templates support canary (gradual) rollout of rules by dimension. Canary takes effect by dimension, not by random percentage. Supported canary dimensions:

- IP
- Custom Header
- Custom Parameter
- Custom Cookie
- Session
- Web UMID / App UMID

---

## Effective Modes

- Permanent (default)
- By time period
- By cycle

---

## Advanced Custom Rules

BOT 2.0 extracts rate limiting logic from App/Web templates and consolidates it into the advanced custom rules module. Two types of rules are supported:

**Access Control Rules**: Define match conditions based on client IP, request URL, and request header fields.

**Rate Limiting Rules**: Define access frequency detection conditions on top of access control, including statistical object (IP/Header/Parameter/Cookie/Session/Body Parameter/UMID/Account/Device ID), statistical duration, and threshold. Supports response code detection conditions and deduplication statistics (up to 5 conditions).

### Full Match Field List

| Match Field | Description |
|-------------|-------------|
| URI | Request URI (path + query string) |
| IP | Source IP (supports IPv4/IPv6/CIDR, up to 100 entries) |
| Referer | Referrer URL |
| User-Agent | Client browser identifier |
| Query String | Part of URL after the question mark |
| Cookie | Cookie information |
| Content-Type | MIME type |
| Content-Length | Byte count (0~2147483648) |
| X-Forwarded-For | Client real IP |
| Body | Request content |
| Http-Method | GET/POST/DELETE, etc. |
| Header | Custom header field |
| URI Path | URI path portion |
| Query String Parameter | Request parameter name (case-sensitive) |
| Client-ID | Client identifier (based on UA and traffic fingerprint) |
| Server-Port | Server port |
| File Extension | File extension |
| Filename | File name |
| Host | Domain name |
| Cookie Name | Cookie key name (case-sensitive) |
| Body Parameter | Body parameter name |
| JA3 Fingerprint | TLS handshake MD5 fingerprint |
| JA4 Fingerprint | Enhanced TLS fingerprint |
| HTTP/2 Fingerprint | HTTP/2 fingerprint |
| IDC | Source IP data center attribution |
| Web SDK | Probe information collected by WebSDK |
| App SDK | Probe information collected by AppSDK |

Rate limiting blacklist handling: After a statistical object enters the blacklist, continued triggering of the rule will refresh the blacklist timeout. CC-type rules trigger immediately when the threshold is reached within the statistical duration, without waiting for the duration to end. Blacklist timeout range: 60~86400 seconds.

### Rate Limiting Configuration Examples

- Single account switches IPs more than 5 times in 60 seconds -> Block
- Single IP makes >30 requests in 60 seconds -> JS verification
- Single UMID makes >50 requests in 60 seconds -> CAPTCHA

---

## Traffic Analysis

The traffic analysis feature provides basic risk interface data without needing to enable Bot management. After enabling the full version, more detailed information can be viewed.

### Basic Concepts

| Concept | Description |
|---------|-------------|
| Malicious BOT | Automated attack programs driven by illegitimate purposes |
| Suspected BOT | Exhibits crawler characteristics but lacks direct evidence |
| Friendly BOT | Bots with beneficial purposes such as search engine indexing |
| Top 20 Clients | Client identifiers identified via UA and traffic fingerprint |
| Web UMID | Unique device identifier for web clients |
| App UMID | Unique device identifier for app clients |
| JA3 Fingerprint | MD5 hash of key TLS handshake parameters |
| JA4 Fingerprint | Enhanced TLS fingerprint |
| HTTP/2 Fingerprint | MD5 of HTTP/2 client raw fingerprint |

### Analysis Dimensions

- Traffic classification TOP IPs: Top 10 IPs hitting Malicious BOT/Suspected BOT/Friendly BOT
- Rule hit TOP IPs: Top 10 IPs hitting different labels
- Client type TOP statistics: Top 20 clients/Web UMID/App UMID
- Traffic fingerprint TOP statistics: JA3/JA4/HTTP2 fingerprints
- Request header TOP statistics: Top 10 Host/Path/Query Parameter/Referer
- Protection object TOP statistics: Top 10 protection objects by request count

If abnormal access volumes are detected for specific Client IDs, UMIDs, JA3/JA4 fingerprints, or HTTP/2 fingerprints, blocking can be configured via Bot advanced custom rules.

---

## Risk Identification (Phone Number Reputation Database)

WAF includes a built-in phone number reputation database that can detect phone numbers or their MD5-encrypted values in HTTP requests and compare them against the reputation database.

Risk labels: Suspected secondary number, fraud risk, spam registration, marketing fraud, scalper account (all high risk).

Risk levels: High risk / Medium-high risk / Medium risk.

Billing: 0.05 CNY/request (only billed when traffic hits rules); no charge if no rules are configured or no traffic hits any rules.
