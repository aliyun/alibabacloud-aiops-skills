# API Parameter Reference

## Time Parameter Specification

- All time parameters use **second-precision Unix timestamps**
- Anti-DDoS Pro related API timestamps must be **precise to the minute**

## Required Parameters Summary

| API Command | Required Parameters | Description |
|-------------|-------------------|-------------|
| `antiddos-public describe-instance-ip-address` | `--ddos-region-id`, `--instance-type` | Query Basic Protection assets |
| `antiddos-public describe-ddos-event-list` | `--ddos-region-id`, `--instance-type`, `--instance-id` | Query Basic Protection events |
| `ddosbgp describe-ddos-event` | `--end-time`, `--instance-id`, `--page-no`, `--page-size`, `--start-time` | Query Native Protection events |
| `ddosbgp describe-traffic` | `--start-time` | Query Native Protection traffic |
| `ddosbgp describe-instance-list` | `--page-no`, `--page-size` | Query Native Protection instances |
| `ddosbgp describe-pack-ip-list` | `--instance-id`, `--page-no`, `--page-size` | Query Native Protection associated IPs |
| `ddoscoo describe-ddos-events` | `--instance-ids`, `--start-time`, `--page-number`, `--page-size` | Query Anti-DDoS Pro events |
| `ddoscoo describe-domain-qps-list` | `--end-time`, `--interval`, `--start-time` | Query Anti-DDoS Pro QPS |
| `ddoscoo describe-port-flow-list` | `--end-time`, `--instance-ids`, `--interval`, `--start-time` | Query Anti-DDoS Pro port traffic |
| `ddoscoo describe-domain-status-code-list` | `--interval`, `--query-type`, `--start-time` | Query Anti-DDoS Pro status codes |

## Region Parameter Reference

- `antiddos-public`: Uses `--ddos-region-id` parameter
- `ddosbgp describe-ddos-event` / `describe-pack-ip-list`: Uses `--biz-region-id` parameter
- `ddosbgp` other commands and all `ddoscoo` commands: Uses `--region` global parameter

## ddosbgp Endpoint Routing (Critical)

The CLI default endpoint `ddosbgp.aliyuncs.com` for `ddosbgp describe-instance-list` does NOT support mainland China Regions (cn-hangzhou/cn-beijing etc. return `DDosBgp.CheckError.InvalidRegion`). You MUST explicitly specify the endpoint:

```bash
# Must add --endpoint parameter, this endpoint covers both mainland and overseas Regions
aliyun ddosbgp describe-instance-list --page-no 1 --page-size 50 --region <region> --endpoint ddosbgp.cn-hangzhou.aliyuncs.com
```

Note: `describe-ddos-event`, `describe-pack-ip-list`, `describe-traffic` are NOT affected by this issue and do not need an explicit endpoint.

Global instances (CoverageType=4, shown as "Global" in console) will appear in every Region query and must be deduplicated by InstanceId.

To get the full list of Regions supported by ddosbgp: `aliyun ddosbgp describe-regions` (approximately 26 Regions, more accurate than the ECS Region list).

## query-type Values (Anti-DDoS Pro Status Codes)

| Value | Description |
|-------|-------------|
| `gf` | Anti-DDoS Pro frontend (WAF response to client) |
| `upstrem` | Origin (origin server response to WAF; note: official API spelling is `upstrem`) |

## instance-ids Format (ddoscoo)

The `--instance-ids` parameter for ddoscoo uses space-separated values:

```bash
aliyun ddoscoo describe-ddos-events --instance-ids id1 id2 id3 ...
```

## Common Region Codes

| Region | Code |
|--------|------|
| China East 1 (Hangzhou) | `cn-hangzhou` |
| China East 2 (Shanghai) | `cn-shanghai` |
| China North 2 (Beijing) | `cn-beijing` |
| China South 1 (Shenzhen) | `cn-shenzhen` |
| China (Hong Kong) | `cn-hongkong` |
| Singapore | `ap-southeast-1` |

## Instance Type Values (Basic Protection)

| Type | Value |
|------|-------|
| ECS | `ecs` |
| SLB | `slb` |
| EIP | `eip` |
| IPv6 | `ipv6` |
| Simple Application Server | `swas` |
| WAF | `waf` |
| GA Basic | `ga_basic` |
