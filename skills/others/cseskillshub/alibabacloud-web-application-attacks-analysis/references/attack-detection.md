# Attack Detection Module

## Detection Thresholds

| Attack Type | Trigger Condition | Confidence |
|-------------|-------------------|------------|
| Single-IP High-Frequency CC | Single client_ip peak QPS >= 100 OR total requests > 1000 | High |
| Proxy-Pool Distributed CC | > 500 unique client_ip, avg req/IP < 50, URL concentration > 60%, empty Referer > 80% | High |
| API Abuse | API requests > 200 and > 30% of total, 200 ratio > 80% | Medium |
| Scanning / Probing | > 50 probe requests to sensitive paths with 404 ratio > 40%, or overall 404 ratio > 10% | Medium |
| Login Brute-Force / Credential Stuffing | > 20 POST to login endpoints with 401/403/302 ratio > 50% | Medium |
| Abnormal Crawler | Tool UA requests > 100, or fake browser UA reused across > 100 IPs | Low-Medium |
| QPS Surge / Drop | Adjacent minute QPS change >= +100% and >= +500 absolute, or <= -70% | High (surge) / Medium (drop) |
| Slow Resource Consumption | P95 request_time > 5s or upstream_time > 3s for > 3 minutes | Medium |
| Origin Direct-Connect Risk | remote_ip == client_ip for > 30% of traffic | Low |
| Bandwidth Surge / Drop | Adjacent minute total_bytes change >= +100% and >= +100 MB absolute, or <= -70% | High (surge) / Medium (drop) |
| Status Code Surge (4xx/5xx) | Adjacent minute 4xx or 5xx count change >= +100% and >= +50 absolute | High (5xx) / Medium (4xx) |

## Attack Time Line Judgment

| Pattern | Interpretation |
|---------|----------------|
| Request surge + few unique IPs | Single-IP / small-group high-frequency CC |
| Request surge + IP count surge | Proxy-pool / distributed bot |
| Request volume normal + request_time rises | Slow resource consumption or performance bottleneck |
| 5xx surge | Origin already affected |

## Behavioral Signatures

### Proxy-Pool / Distributed Bot Evidence

1. **IP Count Surge**: Unique client_ip count exceeds baseline by > 5x.
2. **Low Frequency per IP**: Average requests per IP < 50 in attack window.
3. **URL Concentration**: Top 3 URLs account for > 60% of total requests.
4. **UA Homogeneity**: Same UA string used by > 100 distinct IPs.
5. **Empty Referer**: > 80% requests lack Referer header.
6. **No Session Signals**: Absence of cookies, session tokens, or progressive page navigation.
7. **Success Rate Anomaly**: 200 status ratio > 80% for dynamic endpoints (indicates valid attack).

### Scanning / Probing Signatures

- **Sensitive paths**: `/.env`, `/.git/config`, `/phpmyadmin`, `/wp-admin`, `/admin`, `/server-status`, `/actuator`, `/manager/html`, `/config`, `/backup`
- High 404 ratio (> 40%) from single IP.
- HEAD/OPTIONS method overuse.
- Sequential path patterns (e.g., `/id/1`, `/id/2`, `/id/3`).

### Login Brute-Force Signatures

- **Target endpoints**: `/login`, `/api/login`, `/auth`, `/signin`, `/api/v1/auth`, `/oauth/token`, `/admin/login`.
- Method: POST.
- Status code: 401, 403, 302 (redirect after failed login).
- Request body size consistency (same payload length suggests automated tool).
- No Referer or valid session cookie.

### Abnormal Crawler Signatures

- **Suspicious UA keywords**: `curl`, `wget`, `python-requests`, `go-http-client`, `java`, `apache-httpclient`, `okhttp`, `sqlmap`, `masscan`.
- **Fake browser detection**: Same Chrome/Safari UA reused across > 100 IPs, only accessing APIs, empty Referer, consistent request rhythm.
- Request rate > 10 req/sec sustained.
- Depth-first path traversal without human-like delays.

### Status Code Analysis

| Status | High Volume Interpretation |
|--------|---------------------------|
| 200 | Requests successfully hit business logic; high resource consumption risk |
| 301/302 | Possible redirect abuse or login redirect loops |
| 401 | Authentication failure; suspected brute-force or credential stuffing |
| 403 | Existing blocking or permission restriction |
| 404 | Scanning / probing |
| 408/499 | Client timeout or disconnect; possible abnormal scripts or slow attacks |
| 500/502/503/504 | Origin already affected |

### Traffic Analysis

| Pattern | Interpretation |
|---------|----------------|
| Small request + high frequency + dynamic interface | CPU / DB consumption CC |
| Large response + high frequency | Bandwidth consumption application-layer attack |
| POST large payload | Upload / form resource consumption |
| High request_time + small response | Backend slow processing; possibly hitting complex query endpoints |

## IP x URL Cross Analysis

| Pattern | Attack Type |
|---------|-------------|
| One IP -> one URL, high frequency | Single-IP CC |
| Many IPs -> same URL, low frequency per IP | Proxy-pool CC |
| Many IPs or few IPs -> many detail pages | Crawler |
| One IP or many IPs -> many non-existent paths | Scanning / probing |

## Aggregate Functions

### aggregate_timeline()

Group records by minute buckets. For each bucket compute:
- `request_count`: Total requests
- `unique_ip`: Distinct client_ip count
- `qps`: request_count / 60
- `status_codes`: Distribution of status codes
- `count_4xx`: Count of 4xx status codes
- `count_5xx`: Count of 5xx status codes
- `avg_request_time`: Average request_time
- `p95_request_time`: 95th percentile of request_time
- `p95_upstream_time`: 95th percentile of upstream_time
- `total_bytes`: Total bytes sent

### aggregate_dimensions()

Compute Top-N tables:
- **Top client_ip**: request count, ratio, peak QPS, URL count, top URL, status distribution, UA count, Referer count, bytes, risk level
- **Top URL**: request count, unique IP, avg req/IP, status distribution, bytes, avg request_time, P95 request_time, P95 upstream_time, empty Referer ratio, UA concentration, risk level
- **UA analysis**: request count, IP count, URL count, status distribution, risk judgment
- **Referer analysis**: request count, IP count, top URL, risk judgment
- **Status code distribution**: all observed status codes
- **Traffic analysis**: top traffic IPs, top traffic URLs, average response size
- **Latency analysis**: avg request_time, P95, P99, slow request count, slow top URLs, slow top IPs

### ip_url_cross_analysis()

Cross-tabulation of IP and URL:
- `single_ip_cc`: IPs with high frequency to a single URL
- `scan_ips`: IPs visiting many unique URLs (> 50)
- `crawler_ips`: IPs visiting many detail pages (> 10 URLs, > 50 requests)
- `proxy_pool_targets`: URLs visited by many distinct IPs

### detect_qps_surge()

Analyze minute-level QPS timeline to detect sudden traffic mutations between adjacent windows.

**Parameters:**
- `timeline`: List of dicts from `aggregate_timeline()`, each containing `minute` and `qps`
- `surge_threshold_pct`: Percentage increase threshold (default 300.0)
- `surge_threshold_abs`: Absolute QPS increase threshold (default 500.0)
- `drop_threshold_pct`: Percentage decrease threshold (default -70.0)

**Returns:** List of event dicts:
- `minute`: Timestamp of the affected window
- `type`: `'surge'` or `'drop'`
- `from_qps`: QPS in the previous minute
- `to_qps`: QPS in the current minute
- `delta_pct`: Percentage change
- `delta_abs`: Absolute QPS change

**Detection logic:**
1. Iterate adjacent minute pairs in the timeline.
2. Skip pairs where previous QPS is 0; treat any positive current QPS as infinite surge.
3. Flag **surge** when `delta_pct >= surge_threshold_pct` AND `delta_abs >= surge_threshold_abs`.
4. Flag **drop** when `delta_pct <= drop_threshold_pct`.
5. Return all matched events sorted by timeline order.

### detect_bandwidth_surge()

Analyze minute-level `total_bytes` timeline to detect sudden bandwidth surges or drops.

**Parameters:**
- `timeline`: List of dicts from `aggregate_timeline()`, each containing `minute` and `total_bytes`
- `surge_threshold_pct`: Percentage increase threshold (default 300.0)
- `surge_threshold_abs_mb`: Absolute increase threshold in MB (default 100.0)
- `drop_threshold_pct`: Percentage decrease threshold (default -70.0)

**Returns:** List of event dicts:
- `minute`: Timestamp of the affected window
- `type`: `'surge'` or `'drop'`
- `from_bytes`: Total bytes in the previous minute
- `to_bytes`: Total bytes in the current minute
- `delta_pct`: Percentage change
- `delta_abs`: Absolute byte change
- `delta_abs_mb`: Absolute change in MB

### detect_status_surge()

Analyze minute-level status code counts to detect sudden 4xx or 5xx surges.

**Parameters:**
- `timeline`: List of dicts from `aggregate_timeline()`, each containing `minute` and `status_codes`
- `status_filter`: `'4xx'`, `'5xx'`, or a list of specific status codes (default `'5xx'`)
- `surge_threshold_pct`: Percentage increase threshold (default 300.0)
- `surge_threshold_abs`: Absolute count increase threshold (default 50.0)
- `drop_threshold_pct`: Percentage decrease threshold (default -70.0)

**Returns:** List of event dicts:
- `minute`: Timestamp of the affected window
- `type`: `'surge'` or `'drop'`
- `status_filter`: Monitored status code filter
- `from_count`: Status count in the previous minute
- `to_count`: Status count in the current minute
- `delta_pct`: Percentage change
- `delta_abs`: Absolute count change

### detect_attack_type()

Iterate through all attack signatures. For each signature:
1. Evaluate primary conditions against aggregated data and cross-analysis.
2. If primary conditions met, evaluate secondary conditions.
3. Assign confidence (High / Medium / Low).
4. Classify as detected if sufficient evidence.
5. Rank detected attacks by confidence.
