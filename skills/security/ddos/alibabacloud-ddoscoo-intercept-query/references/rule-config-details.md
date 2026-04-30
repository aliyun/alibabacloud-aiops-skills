# DDoS Pro Rule Configuration Details

## Rule Types Overview

| Rule Type | CLI Query Command | Description |
|-----------|-------------------|-------------|
| CC Protection Rules | `describe-web-cc-rules-v2` | Custom frequency control (rate limiting) rules |
| Precise Access Control | `describe-web-precise-access-rule` | Custom ACL rules with condition matching |
| Region Blocking | `describe-web-area-block-configs` | Geographic region blocking |
| IP Blacklist | `describe-auto-cc-blacklist` | Auto CC blacklist IPs |
| IP Whitelist | `describe-auto-cc-whitelist` | Auto CC whitelist IPs |
| Global Defense Policy | `describe-l7-global-rule` | Global L7 defense rules |
| AI Smart Protection | `modify-web-ai-protect-mode` | AI-based protection mode |

## CC Protection Rule Fields

| Parameter | Type | Description |
|-----------|------|-------------|
| `Name` | string | Rule name |
| `Domain` | string | Associated domain |
| `Act` | string | Action: block, captcha, close (observation) |
| `Count` | int | Request count threshold |
| `Interval` | int | Time window (seconds) |
| `Mode` | string | Matching mode |
| `Ttl` | int | Blacklist duration (seconds) |
| `Uri` | string | URI pattern to match |

## Precise Access Control Rule Fields

| Parameter | Type | Description |
|-----------|------|-------------|
| `Name` | string | Rule name |
| `Domain` | string | Associated domain |
| `Action` | string | Action: block, captcha, allow |
| `Conditions` | array | List of matching conditions |
| `Expires` | int | Rule expiration time (0 = permanent) |

### Condition Structure

| Field | Description |
|-------|-------------|
| `Field` | Match field (e.g., URI, IP, Referer, User-Agent, Header, Cookie, etc.) |
| `MatchMethod` | Match method (e.g., contain, not-contain, prefix, regex, etc.) |
| `Content` | Match content/value |

## Region Blocking Config Fields

| Parameter | Type | Description |
|-----------|------|-------------|
| `Domain` | string | Associated domain |
| `RegionList` | array | List of blocked regions |

## SLS Log Field Mapping to Rule Type

| Log Field Pattern | Likely Rule Type |
|-------------------|-----------------|
| `cc_action` = block/captcha, `cc_rule_id` present | CC Protection Rule |
| `final_plugin` contains "precise" or "acl" | Precise Access Control |
| `final_plugin` contains "region" or "geo" | Region Blocking |
| `final_plugin` contains "blacklist" or "ip" | IP Blacklist |
| `final_plugin` contains "ai" | AI Smart Protection |
