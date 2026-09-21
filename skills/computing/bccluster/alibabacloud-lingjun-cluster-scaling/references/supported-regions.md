# Supported Regions for Lingjun Clusters

This document lists the Alibaba Cloud regions where Lingjun intelligent computing clusters are available.

> **Important**: This document is a static fallback reference (last updated: 2026-05). At runtime the SKILL should **prefer calling the `describe-regions` API for the real-time region list**, and fall back to this document only when the API is unavailable.

> **⚠️ Region Required (MANDATORY)** ｜ Every `aliyun eflo-controller` command example in this file **must** explicitly carry `--region <region>` (`<region>` given explicitly by the user via HITL; defaulting / reusing / persisting via environment variable is **strictly forbidden**). The endpoint is auto-derived by the aliyun CLI from `--region`; an explicit `--endpoint` is **neither needed nor desired** (see [SKILL.md §B-6 Region Required](../SKILL.md)). This rule does **not** apply to `aliyun bssopenapi` and `aliyun ecs` commands.

> **⚠️ Transient Failure Retry (MANDATORY)** ｜ All `aliyun ...` in this file's bash blocks are uniformly wrapped as `safe_aliyun aliyun ...`, matching the [SKILL.md → Transient Failure Retry (MANDATORY)](../SKILL.md) hard rule. Before running scripts you **must** first `source` the definition of `safe_aliyun` (implementation skeleton in [edge-cases.md → Appendix B.4](./edge-cases.md): `retry_with_jitter` + `retry_on_throttle` + retry blacklist). A bare `aliyun ...` call is treated as a hard-rule violation.

## How to Query Supported Regions

Always use the latest region information by querying the API:

```bash
safe_aliyun aliyun eflo-controller describe-regions
```

**Actual response example** (queried 2026-05; `LocalName` values translated to English for this document):
```json
{
  "RequestId": "C7B36613-F9DB-55AD-8E40-6B9565C78F80",
  "Regions": [
    { "RegionId": "cn-hangzhou", "LocalName": "China East 1 (Hangzhou)" },
    { "RegionId": "cn-shanghai", "LocalName": "China East 2 (Shanghai)" },
    { "RegionId": "cn-beijing", "LocalName": "China North 2 (Beijing)" },
    { "RegionId": "cn-zhangjiakou", "LocalName": "China North 3 (Zhangjiakou)" },
    { "RegionId": "cn-huhehaote", "LocalName": "China North 5 (Hohhot)" },
    { "RegionId": "cn-wulanchabu", "LocalName": "China North 6 (Ulanqab)" },
    { "RegionId": "cn-shenzhen", "LocalName": "China South 1 (Shenzhen)" },
    { "RegionId": "cn-heyuan", "LocalName": "China South 2 (Heyuan)" },
    { "RegionId": "cn-guangzhou", "LocalName": "China South 3 (Guangzhou)" },
    { "RegionId": "cn-zhongwei", "LocalName": "China Northwest 2 (Zhongwei)" },
    { "RegionId": "cn-hongkong", "LocalName": "China (Hong Kong)" },
    { "RegionId": "ap-southeast-1", "LocalName": "Singapore" },
    { "RegionId": "ap-southeast-3", "LocalName": "Malaysia (Kuala Lumpur)" },
    { "RegionId": "ap-southeast-7", "LocalName": "Thailand (Bangkok)" },
    { "RegionId": "ap-southeast-8", "LocalName": "Malaysia (Johor)" },
    { "RegionId": "ap-northeast-1", "LocalName": "Japan (Tokyo)" },
    { "RegionId": "eu-central-1", "LocalName": "Germany (Frankfurt)" },
    { "RegionId": "us-southeast-1", "LocalName": "US (Atlanta)" },
    { "RegionId": "me-east-1", "LocalName": "UAE (Dubai)" },
    { "RegionId": "cn-shanghai-finance-1", "LocalName": "China East 2 Finance" },
    { "RegionId": "cn-north-2-gov-1", "LocalName": "China North 2 Gov 1" },
    { "RegionId": "cn-chengdu-ant", "LocalName": "China Southwest 1 Ant Cloud" },
    { "RegionId": "cn-wulanchabu-acdr-1", "LocalName": "Ulanqab Dedicated Cloud HDG" },
    { "RegionId": "cn-wulanchabu-acdr-ut-1", "LocalName": "Ulanqab Dedicated Cloud POC" },
    { "RegionId": "cn-hangzhou-acdr-ut-3", "LocalName": "Hangzhou Dedicated Cloud BJZS" },
    { "RegionId": "cn-hangzhou-acdr-ut-1", "LocalName": "Hangzhou Dedicated Cloud KS01" }
  ]
}
```

> **Note**: `describe-regions` returns **all** regions registered for the eflo-controller product, including dedicated cloud, finance cloud, gov cloud and test environments. Public-cloud users normally only need the regions listed in the "Public Cloud Regions" sections below.

---

## Public Cloud Regions (Mainland China)

| RegionId | Name | Recommended scenarios |
|----------|------|----------|
| `cn-hangzhou` | China East 1 (Hangzhou) | Production, low latency |
| `cn-shanghai` | China East 2 (Shanghai) | Low latency, financial services |
| `cn-beijing` | China North 2 (Beijing) | Government / enterprise apps |
| `cn-zhangjiakou` | China North 3 (Zhangjiakou) | Big data, training jobs |
| `cn-huhehaote` | China North 5 (Hohhot) | Training jobs |
| `cn-wulanchabu` | China North 6 (Ulanqab) | Cost-first, large-scale training |
| `cn-shenzhen` | China South 1 (Shenzhen) | South China production |
| `cn-heyuan` | China South 2 (Heyuan) | South China training |
| `cn-guangzhou` | China South 3 (Guangzhou) | South China production |
| `cn-zhongwei` | China Northwest 2 (Zhongwei) | Cost-first |

---

## Public Cloud Regions (International)

| RegionId | Name | Recommended scenarios |
|----------|------|----------|
| `cn-hongkong` | China (Hong Kong) | Nearest access for overseas users |
| `ap-southeast-1` | Singapore | Southeast Asia |
| `ap-southeast-3` | Malaysia (Kuala Lumpur) | Southeast Asia |
| `ap-southeast-7` | Thailand (Bangkok) | Southeast Asia |
| `ap-southeast-8` | Malaysia (Johor) | Southeast Asia |
| `ap-northeast-1` | Japan (Tokyo) | East Asia |
| `eu-central-1` | Germany (Frankfurt) | Europe |
| `us-southeast-1` | US (Atlanta) | North America |
| `me-east-1` | UAE (Dubai) | Middle East |

---

## Special Regions (Finance / Gov / Dedicated Cloud)

> The following regions are open only to specific customers and are not available to public-cloud users.

| RegionId | Name | Type |
|----------|------|------|
| `cn-shanghai-finance-1` | China East 2 Finance | Finance cloud |
| `cn-north-2-gov-1` | China North 2 Gov 1 | Gov cloud |
| `cn-chengdu-ant` | China Southwest 1 Ant Cloud | Dedicated cloud |
| `cn-wulanchabu-acdr-1` | Ulanqab Dedicated Cloud HDG | Dedicated cloud |
| `cn-wulanchabu-acdr-ut-1` | Ulanqab Dedicated Cloud POC | Dedicated cloud |
| `cn-hangzhou-acdr-ut-3` | Hangzhou Dedicated Cloud BJZS | Dedicated cloud |
| `cn-hangzhou-acdr-ut-1` | Hangzhou Dedicated Cloud KS01 | Dedicated cloud |

---

## Region Selection Guidelines

### 1. Cost Optimization

- **Best Choice**: `cn-wulanchabu` (Ulanqab) / `cn-zhongwei` (Zhongwei)
- **Reason**: Typically offers the most competitive pricing for compute resources
- **Use Case**: Training jobs, batch processing, development/test environments

### 2. Low Latency

- **Best Choices**: Regions close to your users or data sources
- **East China**: `cn-hangzhou`, `cn-shanghai`
- **North China**: `cn-beijing`
- **South China**: `cn-shenzhen`, `cn-guangzhou`
- **Use Case**: Real-time inference, interactive applications

### 3. Data Residency

- **Consideration**: Keep data and compute in the same region to comply with data residency requirements
- **Use Case**: Financial services, healthcare, government

### 4. High Availability

- **Best Practice**: Deploy across multiple availability zones within the same region
- **Use Case**: Production workloads requiring 99.99% uptime

---

## Querying Zones in a Region

To get availability zones for a specific region:

```bash
safe_aliyun aliyun eflo-controller describe-zones \
  --region cn-wulanchabu
```

**Example Output** (`LocalName` values translated to English):
```json
{
  "RequestId": "12345678-ABCD-EF12-3456-7890ABCDEF12",
  "Zones": [
    {
      "ZoneId": "cn-wulanchabu-a",
      "LocalName": "Ulanqab Zone A"
    },
    {
      "ZoneId": "cn-wulanchabu-b",
      "LocalName": "Ulanqab Zone B"
    },
    {
      "ZoneId": "cn-wulanchabu-c",
      "LocalName": "Ulanqab Zone C"
    }
  ]
}
```

---

## Region-Specific Considerations

### Network Connectivity

**Within Region**:
- Free network transfer between zones
- Low latency (< 2ms)
- High bandwidth

**Cross-Region**:
- Requires CEN (Cloud Enterprise Network) for private connectivity
- Network transfer charges apply
- Higher latency (varies by distance)

### Resource Availability

**Note**: Not all machine types are available in all regions. Check availability:

```bash
safe_aliyun aliyun eflo-controller list-machine-types \
  --region cn-wulanchabu
```

### Service Endpoints

Each region has its own API endpoint, in the format `eflo-controller.{RegionId}.aliyuncs.com`:

| Region | Endpoint |
|--------|----------|
| cn-wulanchabu | `eflo-controller.cn-wulanchabu.aliyuncs.com` |
| cn-hangzhou | `eflo-controller.cn-hangzhou.aliyuncs.com` |
| cn-shanghai | `eflo-controller.cn-shanghai.aliyuncs.com` |
| cn-beijing | `eflo-controller.cn-beijing.aliyuncs.com` |
| cn-shenzhen | `eflo-controller.cn-shenzhen.aliyuncs.com` |
| cn-guangzhou | `eflo-controller.cn-guangzhou.aliyuncs.com` |
| ap-southeast-1 | `eflo-controller.ap-southeast-1.aliyuncs.com` |

**Note**: You don't need to specify endpoints manually when using Aliyun CLI; the `--region` flag automatically routes to the correct endpoint.

---

## Multi-Region Deployment

### Cross-Region Cluster Management

To manage clusters across multiple regions:

```bash
# List clusters in all public cloud regions
for REGION in cn-hangzhou cn-shanghai cn-beijing cn-zhangjiakou cn-huhehaote cn-wulanchabu cn-shenzhen cn-heyuan cn-guangzhou cn-zhongwei cn-hongkong; do
  echo "=== Clusters in $REGION ==="
  aliyun eflo-controller list-clusters --region "$REGION"
  echo ""
done
```

### Cross-Region Networking

To connect clusters across regions, use CEN:

1. Create CEN instance
2. Attach VPCs from each region
3. Configure routing

**Note**: Cross-region cluster management requires proper CEN configuration. See Alibaba Cloud CEN documentation for details.

---

## Region Limitations

### Current Limitations (as of 2024)

1. **Cannot move clusters between regions** - Clusters are region-locked after creation
2. **Node types vary by region** - Not all machine types available in all regions
3. **Quota limits are region-specific** - Each region has independent quotas
4. **Network isolation** - Clusters in different regions require CEN for connectivity

---

## Checking Your Region Quota

To check how many clusters you can create in a region:

```bash
# List current clusters
safe_aliyun aliyun eflo-controller list-clusters \
  --region cn-wulanchabu \
  --cli-query "TotalCount"

# Compare with your quota (contact support if needed)
```

To request quota increase:
1. Visit [Quota Center](https://quotas.console.aliyun.com/)
2. Search for "Lingjun" or "eflo-controller"
3. Request increase for specific region

---

## Best Practices

1. **Query regions dynamically** - Always use `describe-regions` to get latest supported regions
2. **Use nearest region** - Choose region closest to users for best performance
3. **Check machine availability** - Verify desired machine types are available in target region
4. **Plan for growth** - Ensure region has capacity for future expansion
5. **Consider compliance** - Some industries require data to stay in specific regions
6. **Test in dev region** - Use cost-effective region (e.g., Ulanqab) for testing
7. **Deploy production strategically** - Choose region based on latency and compliance needs

---

## Example: Region Selection Script

```bash
#!/bin/bash

echo "Available Lingjun Regions:"
echo ""

# Query supported regions dynamically
REGIONS=$(safe_aliyun aliyun eflo-controller describe-regions 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$REGIONS" ]; then
  echo "[WARN] describe-regions API unavailable, falling back to static region list"
  echo "1) cn-wulanchabu - China North 6 (Ulanqab)"
  echo "2) cn-hangzhou - China East 1 (Hangzhou)"
  echo "3) cn-shanghai - China East 2 (Shanghai)"
  echo "4) cn-beijing - China North 2 (Beijing)"
  echo "5) cn-shenzhen - China South 1 (Shenzhen)"
  echo "6) cn-guangzhou - China South 3 (Guangzhou)"
else
  # Filter out dedicated/test/finance/gov regions for public cloud users
  echo "$REGIONS" | jq -r '.Regions[] | select(.RegionId | test("acdr|test|finance|gov|ant") | not) | "\(.RegionId) - \(.LocalName)"'
fi

echo ""
read -p "Enter RegionId: " REGION

if [ -z "$REGION" ]; then
  echo "No region selected, exiting."
  exit 1
fi

echo "Selected region: $REGION"

# Query zones in selected region
echo ""
echo "Available zones in $REGION:"
safe_aliyun aliyun eflo-controller describe-zones --region "$REGION" \
  | jq -r '.Zones[] | .ZoneId'
```

---

## Updates

**Note**: This document reflects Lingjun region availability as of **May 2026** (verified via an actual `aliyun eflo-controller describe-regions` query). Always verify current availability using the `describe-regions` command as new regions may be added.

For the latest official information, visit:
- [Alibaba Cloud Regions and Zones](https://www.alibabacloud.com/help/doc-detail/123712.htm)
- [Lingjun Product Page](https://www.alibabacloud.com/product/lingjun)
