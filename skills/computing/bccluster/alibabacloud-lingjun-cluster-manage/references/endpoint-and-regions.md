# Endpoint Routing & Region List

For every Lingjun `aliyun eflo-controller` CLI command, the **endpoint and region must be strictly identical values**, otherwise the request is routed to the wrong gateway.

> **The region tables below are a lookup aid, NOT an allow-list.** The skill applies no client-side
> region filtering or locking: whatever region id the user names is passed straight to the API, and
> switching region within one conversation is always allowed. If a region is genuinely unavailable
> the gateway says so (`InvalidRegionId`) — that is the authoritative answer, not this document.
> Region coverage changes over time; prefer `describe-regions` (see below) over these tables.

## 🔑 Core Rule: endpoint = region

```bash
# ✅ Correct: endpoint and region share the same value
aliyun eflo-controller list-clusters \
  --endpoint eflo-controller.cn-wulanchabu.aliyuncs.com \
  --region cn-wulanchabu
```

| Counter-example | Failure reason |
|---|---|
| Only `--region` passed, no `--endpoint` | The CLI does not auto-route; it falls back to the default central endpoint, causing cross-region errors |
| `--endpoint eflo-controller.cn-hangzhou` + `--region cn-wulanchabu` | Gateway returns `InvalidRegionId` |
| `--endpoint eflo-controller.<region>.aliyuncs.com` placeholder not substituted | DNS resolution failure |

**This rule applies only to `aliyun eflo-controller`**: `aliyun bssopenapi` uses the central endpoint `business.aliyuncs.com`; `aliyun ecs` has its own endpoint rules.

## ⚠️ Test Region `cn-wulanchabu-test-6` Requires `--insecure`

This region is an internal test gateway with a self-signed TLS certificate. Once a session uses this region, **all** `aliyun ...` commands (including eflo-controller / bssopenapi / ecs / vpc) must append `--insecure`.

```bash
# ✅ Correct
aliyun eflo-controller list-clusters \
  --endpoint eflo-controller.cn-wulanchabu-test-6.aliyuncs.com \
  --region cn-wulanchabu-test-6 \
  --insecure
```

⚠️ **Never add `--insecure` in production commercial regions** (it bypasses TLS verification — a security risk).

⚠️ Put `--insecure` in the parameter area; do **not** stuff it into the `--endpoint` string.

## Region Discovery (runtime first)

Prefer the API for the live list; this document is only a static fallback as of 2026-05:

```bash
# describe-regions is a discovery API; cn-hangzhou works as the seed call
aliyun eflo-controller describe-regions \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
  --region cn-hangzhou
```

```bash
# List zones of a region
aliyun eflo-controller describe-zones \
  --endpoint eflo-controller.<region>.aliyuncs.com \
  --region <region>
```

## Public Cloud Regions (Mainland China)

| RegionId | Name | Typical scenario |
|---|---|---|
| `cn-hangzhou` | China East 1 (Hangzhou) | Production, low latency |
| `cn-shanghai` | China East 2 (Shanghai) | Low latency, finance |
| `cn-beijing` | China North 2 (Beijing) | Government / enterprise |
| `cn-zhangjiakou` | China North 3 (Zhangjiakou) | Big data, training |
| `cn-huhehaote` | China North 5 (Hohhot) | Training |
| `cn-wulanchabu` | China North 6 (Ulanqab) | **Cost-first**, large-scale training |
| `cn-shenzhen` | China South 1 (Shenzhen) | South-China production |
| `cn-heyuan` | China South 2 (Heyuan) | South-China training |
| `cn-guangzhou` | China South 3 (Guangzhou) | South-China production |
| `cn-zhongwei` | China Northwest 2 (Zhongwei) | **Cost-first** |

## Public Cloud Regions (Overseas & Hong Kong/Macao/Taiwan)

| RegionId | Name |
|---|---|
| `cn-hongkong` | China (Hong Kong) |
| `ap-southeast-1` | Singapore |
| `ap-southeast-3` | Malaysia (Kuala Lumpur) |
| `ap-southeast-7` | Thailand (Bangkok) |
| `ap-southeast-8` | Malaysia (Johor) |
| `ap-northeast-1` | Japan (Tokyo) |
| `eu-central-1` | Germany (Frankfurt) |
| `us-southeast-1` | US (Atlanta) |
| `me-east-1` | UAE (Dubai) |

## Special Regions (finance / government / dedicated cloud / test)

> Open only to specific customers; unavailable to public cloud users.

| RegionId | Type |
|---|---|
| `cn-shanghai-finance-1` | Finance cloud |
| `cn-north-2-gov-1` | Government cloud |
| `cn-chengdu-ant` | Ant dedicated cloud |
| `cn-wulanchabu-acdr-1` | Ulanqab dedicated cloud HDG |
| `cn-wulanchabu-acdr-ut-1` | Ulanqab dedicated cloud POC |
| `cn-hangzhou-acdr-ut-3` | Hangzhou dedicated cloud BJZS |
| `cn-hangzhou-acdr-ut-1` | Hangzhou dedicated cloud KS01 |
| `cn-wulanchabu-test-6` | **Internal test gateway** (requires `--insecure`) |

## Region Selection Advice

| Optimization goal | Recommendation |
|---|---|
| Lowest cost | `cn-wulanchabu` / `cn-zhongwei` |
| Low latency (east) | `cn-hangzhou` / `cn-shanghai` |
| Low latency (north) | `cn-beijing` |
| Low latency (south) | `cn-shenzhen` / `cn-guangzhou` |
| Data compliance (finance / government) | `cn-shanghai-finance-1` / `cn-north-2-gov-1` |
| Overseas low latency | Pick the geographically nearest region |

## Region-Level Hard Limits

| Limit | Explanation |
|---|---|
| Clusters **cannot migrate across regions** after creation | Region is an intrinsic property of a cluster |
| Machine types are not available in every region | Verify with `list-machine-types --region <r>` before deployment |
| Quotas are independent per region | Each region has its own quota; apply separately |
| Cross-region communication requires CEN | VPCs in different regions are isolated by default |

## Multi-Region Inventory ("what clusters do I have" style queries)

The Lingjun inventory APIs (`list-clusters` / `list-cluster-nodes` / `list-node-groups` / `list-machine-types` / `list-images`) are all **region-level**; there is no cross-region aggregation endpoint.

To list clusters account-wide, call each region and merge:

```bash
for REGION in cn-hangzhou cn-shanghai cn-beijing cn-wulanchabu cn-shenzhen cn-guangzhou; do
  echo "=== $REGION ==="
  aliyun eflo-controller list-clusters \
    --endpoint eflo-controller.$REGION.aliyuncs.com \
    --region $REGION
done
```

A single-region failure (no permission / throttled) must not abort the whole traversal; log the failure reason and continue.

## 📖 References

- [Lingjun product page](https://www.alibabacloud.com/product/lingjun)
- [Alibaba Cloud Regions and Zones](https://www.alibabacloud.com/help/doc-detail/123712.htm)
- [Quota center](https://quotas.console.aliyun.com/)
