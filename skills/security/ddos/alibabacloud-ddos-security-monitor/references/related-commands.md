# CLI Command Table

## DDoS Basic Protection (antiddos-public)

| CLI Command | Description | Required Parameters |
|-------------|-------------|-------------------|
| `aliyun antiddos-public describe-instance-ip-address` | Query Basic Protection assets | `--ddos-region-id`, `--instance-type` |
| `aliyun antiddos-public describe-ddos-event-list` | Query Basic Protection events | `--ddos-region-id`, `--instance-type`, `--instance-id` |

## DDoS Native Protection (ddosbgp)

| CLI Command | Description | Required Parameters |
|-------------|-------------|-------------------|
| `aliyun ddosbgp describe-instance-list` | Query Native Protection instances | `--page-no`, `--page-size`, `--region` |
| `aliyun ddosbgp describe-pack-ip-list` | Query Native Protection associated IPs | `--instance-id`, `--page-no`, `--page-size`, `--biz-region-id` |
| `aliyun ddosbgp describe-ddos-event` | Query Native Protection attack events | `--end-time`, `--instance-id`, `--page-no`, `--page-size`, `--start-time` (`--biz-region-id` optional) |
| `aliyun ddosbgp describe-traffic` | Query Native Protection L4 traffic | `--start-time`, `--region` |

## DDoS Anti-DDoS Pro/Premium (ddoscoo)

| CLI Command | Description | Required Parameters |
|-------------|-------------|-------------------|
| `aliyun ddoscoo describe-instances` | Query Anti-DDoS Pro instances | `--page-number`, `--page-size`, `--region` |
| `aliyun ddoscoo describe-domains` | Query Anti-DDoS Pro domains | `--region` (`--instance-ids` optional) |
| `aliyun ddoscoo describe-ddos-events` | Query Anti-DDoS Pro attack events | `--instance-ids`, `--start-time`, `--end-time`, `--page-number`, `--page-size`, `--region` |
| `aliyun ddoscoo describe-ddos-all-event-list` | Query Anti-DDoS Pro all events | `--start-time`, `--end-time`, `--page-number`, `--page-size`, `--region` |
| `aliyun ddoscoo describe-domain-qps-list` | Query Anti-DDoS Pro QPS | `--start-time`, `--end-time`, `--interval`, `--region` |
| `aliyun ddoscoo describe-port-flow-list` | Query Anti-DDoS Pro port traffic | `--instance-ids`, `--start-time`, `--end-time`, `--interval`, `--region` |
| `aliyun ddoscoo describe-domain-status-code-list` | Query Anti-DDoS Pro HTTP status codes | `--interval`, `--query-type`, `--start-time`, `--region` |

## Parameter Format Notes

- **Time parameters**: All time parameters use **second-precision Unix timestamps**
- **Region parameters**: Some ddosbgp commands use `--biz-region-id`, others use the global `--region` parameter
- **Instance list**: ddoscoo's `--instance-ids` uses space-separated values, format: `--instance-ids id1 id2 id3`
- **query-type values**: `gf` (Anti-DDoS Pro frontend) or `upstrem` (origin; note: official API spelling is `upstrem`)
