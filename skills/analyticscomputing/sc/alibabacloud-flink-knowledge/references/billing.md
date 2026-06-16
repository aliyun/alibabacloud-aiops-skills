# Alibaba Cloud Realtime Compute for Apache Flink — Billing & Engine Versions

## Product Billing

### Billing Items

Realtime Compute for Apache Flink billing items include:
- **Management Resources**: Fees for managing workspaces
- **Compute Resources**: CU (Compute Unit) fees for executing job computation tasks

### Billing Mode Comparison

| Billing Mode | Description | Use Case |
|---|---|---|
| **Subscription** | Purchase resources for a fixed duration; pay before use | Long-term stable production jobs; most cost-effective |
| **Pay-as-you-go** | Provision and release resources on demand; pay after use | Temporary/test jobs, burst compute demands |
| **Hybrid Billing** | Subscription + elastic compute (pay-as-you-go) | Base load on subscription + peak elastic scaling |

### Other Billing Methods

- **Resource Deduction Plans**: Pre-purchased resource packages that offset pay-as-you-go CU consumption at discounted rates
- **CU-Level Billing**: Fine-grained metering down to individual CU units

### Cost Control Recommendations

1. Choose **subscription** for long-term stable jobs — best value
2. Choose **pay-as-you-go** for test/dev jobs — release when done
3. Purchase **resource deduction plans** to further reduce elastic costs
4. Leverage **smart tuning** to reduce resource waste

## Engine Versions

### Version Label Meanings

| Label | Meaning | Recommendation |
|---|---|---|
| **Recommend** | Latest minor version under the current major version | Preferred for new jobs |
| **Stable** | Latest minor version under the previous major version still in service; historical defects fixed | For production jobs with high stability requirements |
| **Normal** | Other minor versions still in service | Use when compatibility is required |
| **EOS (Deprecated)** | Versions past their end-of-service date | Not recommended |

> It is recommended to use versions labeled `Recommend` or `Stable`, which offer higher reliability and performance.

## Regions and Availability Zones

- Multiple **regions** available
- **Same-city high availability** architecture with multi-AZ disaster recovery
- Choose the region closest to your data source to minimize network latency

## Official Documentation Links

- [Product Billing](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/billing/)
- [Subscription](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/subscription)
- [Pay-as-you-go](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/pay-as-you-go)
- [Hybrid Billing](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/hybrid-pricing)
- [Engine Version Overview](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/engine-version)
- [Regions and Availability Zones](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/regions-and-zones)
- [Lifecycle Policies](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/lifecycle-policies)
- [Feature Release Notes](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/release-notes/)
