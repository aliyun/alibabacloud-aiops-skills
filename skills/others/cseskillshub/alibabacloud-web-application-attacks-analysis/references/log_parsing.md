# Log Parsing Module

## Auto-Detection Logic

The `detect_log_type()` function identifies the log format by sampling the first 10 non-empty lines and applying regex pattern matching.

| Detected Result | Condition |
|-----------------|-----------|
| `iis` | Sample contains `#Software:` or `#Fields:` directives |
| `nginx` | All matching lines conform to Nginx combined pattern |
| `apache` | All matching lines conform to Apache combined pattern |
| `mixed` | Sample contains both Nginx and Apache matching lines |
| `unknown` | No line matches any known pattern |

When `mixed` or `unknown` is detected, the parser falls back to trying **all** known format parsers (Nginx -> Apache) on each line, using the first successful match. The final report labels the source type as `MIXED` or `UNKNOWN` accordingly.

### Nginx Patterns

**Standard combined:**
```
$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
```

**Enhanced (recommended):**
```
$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" $request_time $upstream_response_time
```

### Apache Patterns

**Standard combined:**
```
%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i"
```

**Enhanced (recommended):**
```
%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i" "%{X-Forwarded-For}i" %D
```

### IIS W3C Pattern

IIS W3C logs have a header section defining fields. The parser reads the `#Fields:` directive to build a dynamic CSV parser.

**Recommended IIS fields:**
```
#Fields: date time c-ip cs-method cs-uri-stem cs-uri-query sc-status sc-bytes cs(User-Agent) cs(Referer) cs(X-Forwarded-For) time-taken
```

## Real IP Extraction

### Algorithm: extract_client_ip()

```
Input: remote_ip, xff_header
Output: client_ip

1. If xff_header exists and is not empty or "-":
   a. Split xff_header by comma
   b. For each IP in left-to-right order:
      - Trim whitespace
      - Skip private/reserved IPs (10.x, 172.16-31.x, 192.168.x, 127.x, fc00::, etc.)
      - Skip empty/invalid values
      - First valid public IP becomes client_ip
2. If xff_header absent, empty, "-", or invalid:
   client_ip = remote_ip
3. remote_ip is always preserved and never overwritten
4. Return client_ip
```

### Private IP Ranges

| Range | CIDR |
|-------|------|
| Loopback | 127.0.0.0/8 |
| Private A | 10.0.0.0/8 |
| Private B | 172.16.0.0/12 |
| Private C | 192.168.0.0/16 |
| Link-local | 169.254.0.0/16 |
| Unique Local (IPv6) | fc00::/7 |

### Example

```json
{
  "remote_ip": "100.64.1.10",
  "xff": "8.8.8.8, 47.96.1.1, 10.0.0.12",
  "client_ip": "8.8.8.8"
}
```

## Standardized Fields

| Priority | Field | Description |
|----------|-------|-------------|
| Required | timestamp | Request timestamp |
| Required | source_type | Log format: nginx / apache / iis / mixed / unknown |
| Required | remote_ip | IP seen by the web server (never overwritten) |
| Required | method | HTTP method |
| Required | url | Full request URL |
| Required | path | URL path component |
| Required | status | HTTP response status code |
| Strongly recommended | xff | X-Forwarded-For header value |
| Strongly recommended | ua | User-Agent header |
| Strongly recommended | referer | Referer header |
| Strongly recommended | bytes | Response body bytes sent |
| Enhancement | client_ip | Derived real client IP for attack analysis |
| Enhancement | request_time | Total request processing time (seconds) |
| Enhancement | upstream_time | Upstream/backend response time (seconds) |
| Enhancement | query | URL query string |

## Missing Field Impact

| Missing Field | Impact on Analysis |
|---------------|-------------------|
| xff | Cannot accurately identify real client IP; may only see CDN/WAF/CLB back-source IP |
| ua | Cannot detect tool UA, fake browsers, or same-UA-multi-IP bot patterns |
| referer | Cannot detect direct API access bypassing page navigation |
| request_time / upstream_time | Cannot detect slow resource consumption or origin pressure |

## URL Decomposition

```python
from urllib.parse import urlparse

parsed = urlparse(url)
path = parsed.path
query = parsed.query
```

## Timestamp Normalization

All timestamps are converted to timezone-aware datetime. Nginx/Apache use `strptime` with format `%d/%b/%Y:%H:%M:%S %z`. IIS uses the combined `date time` fields.

## Error Handling

| Scenario | Action |
|----------|--------|
| Unrecognized format | Detect as `unknown`; try all parsers per line; label source_type as UNKNOWN in report |
| Malformed line | Log warning; skip line; count skipped lines in report |
| Invalid IP in xff | Skip to next IP in chain |
| Missing mandatory field (timestamp, status, remote_ip) | Skip line; increment error counter |
| Empty log file | Return error with clear message |
