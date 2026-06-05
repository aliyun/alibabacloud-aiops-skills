# CLI Command Table

## WAF 3.0 (waf-openapi) Full Command List

| Function | CLI Command | Required Parameters | Description |
|----------|-------------|---------------------|-------------|
| WAF instance query | `describe-instance` | **--region** | Query instance details. WAF 3.0 supports cn-hangzhou and ap-southeast-1 only |
| Domain query | `describe-domains` | --instance-id, **--region** | Query CNAME-connected domains |
| Cloud product access | `describe-cloud-resource-list` | --instance-id, **--region** | Query ECS/CLB/ALB connected resources |
| Certificate query | `describe-certs` | --instance-id, **--region** | Query SSL certificate list |
| Defense rule stats | `describe-defense-rule-statistics` | --instance-id, --primary-key, --template-id, **--region** | Statistics by scene/action/status. MUST have valid template-id from describe-defense-templates |
| API security events | `describe-apisec-events` | --instance-id, **--region** | Query API security event list |
| Flow chart | `describe-flow-chart` | --instance-id, --start-timestamp, --end-timestamp, --interval, **--region** | Traffic time-series analysis |
| QPS trend | `describe-peak-trend` | --instance-id, --start-timestamp, --end-timestamp, --interval, **--region** | QPS peak trend |
| Top resources | `describe-flow-top-resource` | --instance-id, --start-timestamp, --end-timestamp, **--region** | Top protected objects |
| Top URLs | `describe-flow-top-url` | --instance-id, --start-timestamp, --end-timestamp, **--region** | Top URL analysis |
| HTTP status codes | `describe-response-code-trend-graph` | --instance-id, --start-timestamp, --end-timestamp, --interval, --type, **--region** | Frontend/upstream status code trends |
| Protection switch | `describe-pause-protection-status` | --instance-id, **--region** | Query protection pause status |
| Defense templates | `describe-defense-templates` | --instance-id, **--region** | Query defense template list (MUST execute before describe-defense-rule-statistics) |
| Alarm list | `describe-alarm-list` | --instance-id, **--region** | Query current alarms |
| DDoS status | `describe-ddos-status` | --instance-id, **--region** | Query if WAF is under DDoS attack |
| Major protection IPs | `describe-major-protection-black-ips` | --instance-id, **--region** | Query major protection blacklisted IPs |

## Region Parameter

WAF 3.0 CLI uses `--region` as the ONLY region parameter. FORBIDDEN: `--region-id` (unknown flag) and `--biz-region-id` (doesn't route correctly for ap-southeast-1).

For ap-southeast-1 calls, `--region ap-southeast-1` ensures the request reaches the international endpoint.

## Business Regions

WAF 3.0 supports only 2 business regions:
- `cn-hangzhou` -- Mainland China
- `ap-southeast-1` -- International

## Common Query Scenarios

| Scenario | Recommended Command Sequence |
|----------|------------------------------|
| Asset inventory | describe-instance --> describe-domains --> describe-cloud-resource-list --> describe-certs |
| Attack analysis | describe-defense-templates --> (extract template-id) --> describe-defense-rule-statistics --> describe-apisec-events |
| Traffic monitoring | describe-flow-chart + describe-peak-trend + describe-flow-top-resource + describe-flow-top-url |
| Status code analysis | describe-response-code-trend-graph (--type waf) + describe-response-code-trend-graph (--type upstream) |
| Protection status | describe-pause-protection-status + describe-alarm-list + describe-ddos-status |

## Notes

- All commands use plugin mode kebab-case format (e.g., `describe-instance`, NOT `DescribeInstance`)
- Region parameter: ALWAYS `--region` (e.g., `--region cn-hangzhou` or `--region ap-southeast-1`).
- Time parameters use second-precision Unix timestamps
- `--interval` must be a multiple of 60 (recommended: 300)
- `describe-response-code-trend-graph` `--type` values: `waf` (frontend) or `upstream` (origin)
- `describe-defense-rule-statistics` REQUIRES --template-id from describe-defense-templates (bot_manager scene only). If no bot_manager template exists, use `${BOT_TEMPLATE_ID:-0}` as fallback to ensure the call reaches the server; server returns "template not found" error which is logged and reported
