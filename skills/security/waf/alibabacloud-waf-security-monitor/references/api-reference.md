# API Parameter Reference

## Region Parameter

WAF 3.0 uses `--region` (CLI global flag) for region routing. Only 2 business regions are supported:
- `cn-hangzhou` -- Mainland China
- `ap-southeast-1` -- International

**[FORBIDDEN]** NEVER use `--region-id` (CLI returns "unknown flag"). NEVER use `--biz-region-id` (doesn't correctly route to ap-southeast-1 endpoint). The ONLY correct flag is `--region`.

The API documentation parameter `RegionId` is automatically handled by the CLI's `--region` flag -- no separate business parameter needed.

Pattern:
- cn-hangzhou: `aliyun waf-openapi <cmd> --region cn-hangzhou --user-agent "$ALIBABA_CLOUD_USER_AGENT" ...`
- ap-southeast-1: `aliyun waf-openapi <cmd> --region ap-southeast-1 --user-agent "$ALIBABA_CLOUD_USER_AGENT" ...`

**[CRITICAL] Per-Region Independence**: Failure querying cn-hangzhou does NOT exempt ap-southeast-1. Both regions MUST always be queried independently.

## Time Parameter Specification

- All time parameters use **second-precision Unix timestamps**
- `--interval` must be a multiple of 60 (recommended: 300)

## Required Parameters Summary

| API | Required Parameters | Description |
|-----|---------------------|-------------|
| `describe-instance` | --region | Query WAF instance details |
| `describe-domains` | --instance-id, --region | Query CNAME-connected domains |
| `describe-cloud-resource-list` | --instance-id, --region | Query cloud product access |
| `describe-certs` | --instance-id, --region | Query SSL certificates |
| `describe-flow-chart` | --instance-id, --start-timestamp, --end-timestamp, --interval, --region | Traffic time-series |
| `describe-peak-trend` | --instance-id, --start-timestamp, --end-timestamp, --interval, --region | QPS trend |
| `describe-flow-top-resource` | --instance-id, --start-timestamp, --end-timestamp, --region | Top protected objects |
| `describe-flow-top-url` | --instance-id, --start-timestamp, --end-timestamp, --region | Top URLs |
| `describe-response-code-trend-graph` | --instance-id, --start-timestamp, --end-timestamp, --interval, --type, --region | Status code trends |
| `describe-defense-rule-statistics` | --instance-id, --primary-key, --template-id, --region | Defense rule statistics. **template-id MUST be obtained from describe-defense-templates** |
| `describe-defense-templates` | --instance-id, --region | Query defense templates (prerequisite for rule statistics) |
| `describe-apisec-events` | --instance-id, --region | API security events |
| `describe-pause-protection-status` | --instance-id, --region | Protection switch status |
| `describe-alarm-list` | --instance-id, --region | Alarm list |
| `describe-ddos-status` | --instance-id, --region | DDoS attack status |
| `describe-major-protection-black-ips` | --instance-id, --region | Major protection black IPs |

## --type Values (describe-response-code-trend-graph)

| Value | Description |
|-------|-------------|
| `waf` | Response codes from WAF to client (frontend status codes) |
| `upstream` | Response codes from origin to WAF (upstream status codes) |

## --primary-key Values (describe-defense-rule-statistics)

| Value | Description |
|-------|-------------|
| `riskLevel` | Risk level |
| `detectType` | Detection type |
| `action` | Rule action (block/monitor/captcha, etc.) |
| `scene` | Protection scenario |
| `status` | Rule status |

## Supported Protection Scenarios (for --template-id lookup)

| Scenario | Description |
|----------|-------------|
| `bot_manager` | BOT management -- the ONLY scene supported by describe-defense-rule-statistics |

> **IMPORTANT**: `waf_group` (Web Core Protection in console) is NOT supported by this API. `waf_base` does not exist in current WAF 3.0 accounts. Only `bot_manager` works.

## template-id Handling

**CRITICAL**: `--template-id` MUST be extracted from a template with `DefenseScene=bot_manager` ONLY.

**Templates from ALL other DefenseScene values (waf_group, cc, custom_acl, ip_blacklist, region_block, whitelist, bot) return `DefenseSceneNotSupported` error.** Do NOT use them.

If describe-defense-templates returns no bot_manager template:
- Use `${BOT_TEMPLATE_ID:-0}` as fallback value (ensures CLI call reaches server)
- The API will return "template not found" error -- log it and report to user
- **FORBIDDEN**: Using template-ids from waf_group/cc/custom_acl/ip_blacklist as substitutes
