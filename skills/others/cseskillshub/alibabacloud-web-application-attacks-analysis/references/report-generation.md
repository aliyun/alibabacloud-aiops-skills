# Report Generation Module

## Output Structure

The report serves **two audiences**:

1. **Non-technical users** - the report opens with an **Executive Summary** (section 0): a one-line conclusion with an overall risk level, a plain-language explanation, and prioritized actions.
2. **Technical staff / downstream agents** - the 11 detail sections follow (deep-dive evidence), and the report closes with **Structured Findings** (section 12): a machine-readable JSON block that can be consumed as the next agent stage's input.

The report MUST contain the following sections in order. All sections are rendered with pure ASCII visual separators (`=` for the report title and section top borders, `-` for section underlines and table separators, `#` for ratio bars) and thousands separators for numeric values.

**Important**: Reports MUST NOT contain any emoji characters. All markers and symbols use pure ASCII characters only.

### 0. Executive Summary (dual-audience front section)

Rendered first, before all detail sections. Contains three parts:

- **Conclusion** - one sentence stating whether an attack was detected and the overall risk level (`NONE / LOW / MEDIUM / HIGH / CRITICAL`). The overall risk is the highest severity across all detected attacks; severity is derived from attack type + confidence (e.g. High-confidence Single-IP CC or login brute force => critical).
- **Plain language explanation** - 2-4+ non-technical sentences describing what happened and what it means for the website, using restrained everyday analogies (e.g. "like someone ringing your doorbell thousands of times non-stop") and concrete numbers from the evidence (top attacker IP, request counts, most targeted page, time window).
- **What you should do** - 3-5 prioritized, one-sentence actions (block attacker IPs/CIDRs, rate limiting, bot/human verification, account lockout/CAPTCHA for brute force, CDN/DCDN protection, continued monitoring). Jargon is always followed by a short parenthetical explanation.

The same content is rendered in both text and Markdown formats (Markdown uses `## 0. Executive Summary` with paragraphs and a numbered list).

### 1. Attack Conclusion

- **Attack type(s)** detected with confidence level (High / Medium / Low) prefixed by `[HIGH] / [MED] / [LOW]` tags
- **Attack time window** (start timestamp -> end timestamp)
- **Peak QPS** value
- **Primary target(s)** (Top URLs under attack)
- **Origin impact assessment** - 200 ratio, 5xx errors, request_time P95 change

### 2. Core Evidence

Bullet-pointed quantitative evidence using `-` markers:
- Request volume surge after time X, peak QPS value
- Unique client_ip count vs. baseline
- URL concentration ratio
- Average requests per IP
- Empty Referer ratio
- Same UA reused across N IPs (UA displayed **in full**, never truncated)
- Status code 200 ratio for dynamic endpoints
- request_time / upstream_time P95 range

### 3. Top client_ip Table

| Column | Description |
|--------|-------------|
| client_ip | Attacker IP (derived real client IP) |
| request_count | Total requests (with `,` thousands separator) |
| ratio | Percentage of total requests |
| peak_qps | Highest QPS in any 1-minute bucket |
| url_count | Number of unique URLs accessed |
| ua_count | Number of unique UAs |
| bytes | Total bytes (auto-converted to B / KB / MB / GB / TB) |
| risk | critical / high / medium |

Table header is underlined with a `-` separator line; numeric columns are right-aligned.

Note: peakQPS values are per-minute request counts by design (inherited from the upstream detection semantics); detection thresholds are calibrated against this unit and must not be reinterpreted as per-second rates.

### 3b. Attacker IP CIDR Aggregation

After the Top client_ip table, if **two or more high-risk IPs** (risk critical / high) are present, the report automatically aggregates them into precise IPv4 CIDR blocks (grouped by /24 subnet, each CIDR guaranteed to be /24 or tighter; single IPs appear as /32 only when high-risk):

- Algorithm: group high-risk IPs by /24 subnet, then compute the tightest containing CIDR per group (XOR min/max to derive prefix length, then mask the network address).
- When a non-/32 aggregation exists, the report displays:
  ```
  [Attacker IP subnet aggregation]
    -x.x.x.x/y            contains N attack IPs: ip1, ip2, ...
  ```
- The aggregated CIDRs feed the deny list reused in the mitigation recommendations section.

### 4. Top URL Table

| Column | Description |
|--------|-------------|
| url | Request path (truncated to 34 chars with `..` if longer) |
| request_count | Total requests (with `,` thousands separator) |
| unique_ip | Distinct client_ip count |
| avg_req_per_ip | request_count / unique_ip |
| p95_request_time | P95 request_time |
| empty_referer_ratio | Percentage of empty Referer |
| risk | critical / high / medium |

### 5. IP x URL Cross Analysis

All four cross-analysis categories MUST be printed when data exists:

- **[Single-IP High-Frequency CC]** - One IP -> one URL, high frequency (`unique_urls == 1` and `count > 100`)
- **[Scanning / Probing]** - One IP -> many unique paths (`unique_urls > 50`)
- **[Abnormal Crawler]** - One IP -> many detail pages (`unique_urls > 10` and `total > 50`)
- **[Proxy-Pool Characteristics]** - Many IPs -> same URL (`proxy_pool[url] > 100`)

### 6. UA Analysis

| Column | Description |
|--------|-------------|
| ua | User-Agent string (**displayed in full**, column width dynamically adjusted to longest UA) |
| request_count | Total requests (with `,` thousands separator) |
| ip_count | Distinct client_ip count |
| url_count | Number of unique URLs |
| risk | high / medium |

High-risk UA indicators: empty UA, curl, wget, python-requests, go-http-client, java, apache-httpclient, okhttp, sqlmap, masscan.

Fake browser detection: same Chrome/Safari UA reused across > 100 IPs, only accessing APIs, empty Referer, consistent request rhythm.

### 7. Referer Analysis

| Column | Description |
|--------|-------------|
| referer | Referer value (truncated to 44 chars with `..` if longer) |
| request_count | Total requests (with `,` thousands separator) |
| ip_count | Distinct client_ip count |
| risk | high / low |

Anomalies: high empty Referer ratio, Referer mismatch with path, external abnormal Referer concentration, direct API access without page navigation.

### 8. Status Code Analysis

| Status | High Volume Interpretation |
|--------|---------------------------|
| 200 | Successfully hit business; high resource consumption risk |
| 301/302 | Possible redirect abuse or login loops |
| 401 | Authentication failure; suspected brute-force |
| 403 | Existing blocking or permission restriction |
| 404 | Scanning / probing |
| 408/499 | Client timeout/disconnect; abnormal scripts or slow attacks |
| 500/502/503/504 | Origin already affected |

Rendering: each status line includes a proportional `#` bar (one block per ~2% of total traffic) for visual ratio indication.

### 9. Traffic Analysis

- **Average response size** - auto-converted to human-readable units (B / KB / MB / GB / TB)
- **Top traffic IP** - IP + human-readable byte value
- **Top traffic URL** - URL + human-readable byte value

Interpretation:
- Small request + high frequency + dynamic interface = CPU / DB consumption CC
- Large response + high frequency = Bandwidth consumption attack
- POST large payload = Upload / form resource consumption
- High request_time + small response = Backend slow processing

### 10. Request Latency Analysis

If request_time / time-taken available:
- Average request_time
- P95 request_time
- P99 request_time
- Slow request URLs
- Slow request IPs
- Slow request status codes

Interpretation:
- High request volume + rising P95 = Dynamic interface under pressure
- 5xx surge + rising request_time = Origin under stress
- 499/408 surge = Attacker or client mass timeout/disconnect

### 11. Mitigation Recommendations

A flat numbered list of 4 actionable items:

1. **IP / CIDR Blacklist** - Set `deny` for the aggregated attacker CIDRs (computed via /24-grouped precise CIDR aggregation when multiple high-risk IPs share a segment); falls back to single-IP `deny` when no aggregation is possible.
2. **WAF Bot/Human Verification (paid)** - Trigger JavaScript challenges, sliders, or other CAPTCHA-like mechanisms for suspicious IPs to distinguish real users from automated scripts.
3. **WAF Custom Rate-Limit Rules (paid)** - Apply rate-limiting custom rules on critical endpoints (e.g., login, payment): count window 10s, threshold 5 requests, block duration 1800s, to prevent interface overload.
4. **CDN / DCDN Caching** - Cache static content at the edge to reduce origin bandwidth pressure and improve resilience against high-volume attacks.

### 12. Structured Findings (dual-audience back section)

Rendered last, after all detail sections. A single machine-readable JSON block intended as the **next agent stage's input**. The JSON MUST be parseable by `json.loads`.

| Field | Description |
|-------|-------------|
| `overall_risk` | none / low / medium / high / critical (highest severity across detected attacks) |
| `attack_types` | Array of `{type, severity, evidence_count}` for each detected attack |
| `top_attack_sources` | Array of `{ip, request_count}` for the top 5 client_ip entries |
| `time_window` | `{start, end}` minute-level timestamps of the analyzed data (null when empty) |
| `total_requests` | Number of analyzed records |
| `format` | Detected/forced log format (nginx / apache / iis) |
| `data_quality_notes` | Missing fields (xff / ua / referer / request_time) and their impact |

Rendering: in the text report the JSON is printed indented inside the section; in the Markdown report it is wrapped in a ```` ```json ```` fenced code block. Rendering layer only - this section never changes detection results.

## Confidence Levels

| Level | Criteria |
|-------|----------|
| **High** | >= 3 primary behavioral signatures matched + origin impact confirmed |
| **Medium** | 2 primary signatures matched OR origin impact partially confirmed |
| **Low** | 1 primary signature matched, no confirmed origin impact |

## Missing Field Impact

For any missing standardized field, the report MUST include:

| Missing Field | Impact on Analysis |
|---------------|-------------------|
| xff | Cannot accurately identify real client IP; may only see CDN/WAF/CLB back-source IP |
| ua | Cannot detect tool UA, fake browsers, or same-UA-multi-IP bot patterns |
| referer | Cannot detect direct API access bypassing page navigation |
| request_time / upstream_time | Cannot detect slow resource consumption or origin pressure |

## Human-Readable Size Conversion

All byte values in the report MUST be auto-converted using the following thresholds:

| Range | Display Format |
|-------|----------------|
| < 1,024 B | `X B` |
| < 1,024 KB | `X.XX KB` |
| < 1,024 MB | `X.XX MB` |
| < 1,024 GB | `X.XX GB` |
| >= 1,024 GB | `X.XX TB` |

## Report Language

The report is always generated in English (pure ASCII). If the user communicates in another language, summarize or translate the key findings in the reply, but keep the report file itself in English.

## Input Robustness (real-world log handling)

The analyzer is designed to survive messy real-world access logs:

- Encoding: files are read as UTF-8 with invalid bytes ignored (tolerates latin-1/GBK fragments in URLs and user agents).
- Malformed lines are skipped and counted (`Skipped N unparseable lines`); they never abort the analysis.
- Tolerant fallback parsing handles common variants without changing detection semantics:
  - nginx lines with a leading X-Forwarded-For field (quoted or comma-separated IP list) before remote_addr, and empty request lines (`"" 400`).
  - Apache common-format lines that omit the referer/user-agent fields.
  - IIS W3C logs concatenated from multiple days/servers with different `#Fields:` layouts: each data line is matched against every schema seen so far.
- Corrupt or truncated gzip input, unreadable files, and directories produce a clean `Error:` message with exit code 1 (never a raw traceback).
- Mixed timestamp types disable the `--time-window` filter with a warning instead of crashing.
