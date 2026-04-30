# Common DDoS Pro Block Reasons and Recommendations

## Block Reason Reference Table

| Rule Type | Common Causes | Recommendations |
|-----------|---------------|-----------------|
| CC Protection (频率控制) | Request frequency exceeded CC threshold | Check if request pattern is normal; adjust CC rule threshold or switch to observation mode |
| Precise Access Control (精确访问控制) | URL/headers/parameters matched ACL rules | Verify if the request matches business expectations; check rule matching conditions |
| Region Blocking (区域封禁) | Source region/country is restricted | Verify if the access region should be allowed; adjust region blocking config |
| IP Blacklist (IP黑名单) | Client IP is on the auto CC blacklist | Check if IP was blocked by mistake; remove from blacklist if legitimate |
| AI Smart Protection (AI智能防护) | AI model identified request as malicious | Verify if request behavior is normal; adjust AI protection mode |
| Global Defense Policy (全局防护策略) | Triggered global L7 defense rules | Check global rule configuration; adjust if causing false positives |

## DDoS Pro SLS Full Log Key Fields

| Field | Description |
|-------|-------------|
| `request_traceid` | Request trace ID (used for intercept query) |
| `cc_action` | CC protection action: close (pass), captcha (challenge), block (deny) |
| `cc_rule_id` | CC rule ID that triggered the action |
| `cc_phase` | CC protection phase |
| `final_action` | Final action taken on the request |
| `final_plugin` | Plugin/module that triggered the block |
| `final_rule_id` | Rule ID that caused the final action |
| `matched_host` | Matched domain name |
| `real_client_ip` | Real client IP address |
| `host` | Request Host header |
| `request_uri` | Request URI path |
| `request_method` | HTTP method (GET, POST, etc.) |
| `status` | HTTP response status code |
| `upstream_status` | Origin server response status code |
| `http_user_agent` | Client User-Agent header |
| `time` | Log timestamp |

## Domain Naming in DDoS Pro

DDoS Pro website forwarding rules are domain-based. The domain configured in DDoS Pro forwarding rules is directly used as the identifier (e.g., `www.example.com`).
