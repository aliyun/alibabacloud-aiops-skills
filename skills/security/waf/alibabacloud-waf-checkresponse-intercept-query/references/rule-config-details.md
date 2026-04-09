# WAF Rule Configuration Details

## Config Field Description

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string | Action to execute (block - block request, monitor - observe only) |
| `ccStatus` | int | **CC rule indicator**: 1 - custom rate limiting rule, 0 - custom access control rule |
| `effect` | string | **Only valid when ccStatus=1**, scope of effect after blacklisting |
| `conditions` | array | List of matching conditions |

## Important Notes - `ccStatus` and `effect`

### `ccStatus` Parameter

- `1` - The rule is a **custom rate limiting rule (CC rule)**
- `0` - The rule is a **custom access control rule (ACL rule)**

### `effect` Parameter (only valid when `ccStatus=1`)

- `service` - After blacklisting, takes effect on the **entire protection object** (i.e., `matched_host` in SLS logs)
- `rule` - After blacklisting, takes effect only within the **scope of this rule** (must satisfy rule matching conditions)

**Note**: When `ccStatus=0`, the `effect` parameter is meaningless and can be ignored.

## Example Configuration Interpretation

```json
{
  "action": "block",
  "ccStatus": 0,          // ACL rule, not a CC rule
  "effect": "service",    // Meaningless because ccStatus=0
  "conditions": [{"key": "URL", "opValue": "contain", "values": "/test"}]
}
```

## Common Rule ID Prefixes

| Prefix | Rule Type |
|--------|-----------|
| 101xxx | Custom Access Control (ACL) |
| 102xxx | CC Protection Rules |
| 103xxx | IP Blacklist/Whitelist |
| 104xxx | Region Blocking |
| 105xxx | Bot Management |
| 106xxx | Data Risk Control |

## SLS Log Key Fields

| Field | Description |
|-------|-------------|
| `request_traceid` | Request ID |
| `final_rule_id` | Block rule ID |
| `final_plugin` | Block plugin type (e.g., acl, cc, etc.) |
| `final_action` | Action executed (block - blocked, monitor - observed) |
| `status` | HTTP response status code |
| `real_client_ip` | Real client IP |
| `host` | Request domain |
| `request_uri` | Request URI |
