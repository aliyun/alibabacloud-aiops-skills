# Cost Estimation Reference

This document describes how to estimate GA deployment costs, including bandwidth package fees, specification fees, and pay-as-you-go estimates.

> **Important**: Estimates are for reference only. Actual charges are based on your bill. Prices may change due to promotions.

---

## 1. GA Billable Items

| Item | Billing Mode | Description |
|---|---|---|
| Specification fee | PREPAY / POSTPAY | Charged by spec for Standard accelerators; Basic accelerators are usually free |
| Bandwidth package fee | PREPAY / POSTPAY | PREPAY requires a bandwidth package; POSTPAY uses CDT |
| Traffic fee | POSTPAY (CDT) | Charged by outbound traffic |
| Cross-region fee | POSTPAY | Extra fee may apply for cross-border scenarios |
| Anycast EIP fee | POSTPAY | Applies when Anycast EIP is used as the accelerate IP |

---

## 2. Query GA Product Prices

### Method 1: BssOpenApi

```bash
aliyun bssopenapi query-product-list \
  --product-code ga \
  --page-size 50 | jq '.Data.ProductList[] | {ProductCode, ProductName, ProductType}'
```

### Method 2: DescribePricing for PREPAY

> Parameters below are examples; verify in OpenAPI Explorer.

```bash
aliyun ga describe-pricing \
  --biz-region-id cn-hangzhou \
  --commodity-code "ga" \
  --order-type "BUY" \
  --charge-type "PrePaid" \
  --pricing-cycle "Month" \
  --duration 1 \
  --bandwidth-package-id "cbwp-bp1xxxx" \
  --user-agent "$GA_USER_AGENT" | jq '.PriceInfo'
```

---

## 3. POSTPAY Hourly Cost Estimate Script

```bash
#!/bin/bash
BANDWIDTH_MBPS="${1:?Please provide bandwidth in Mbps}"
TRAFFIC_GB_PER_MONTH="${2:?Please provide estimated monthly traffic in GB}"

# Example unit prices; query current prices for accurate results.
INSTANCE_HOURLY=0.5            # instance spec hourly price (CNY/hour)
TRAFFIC_PER_GB=0.8             # traffic price (CNY/GB)
HOURS_PER_MONTH=730

INSTANCE_MONTHLY=$(echo "$INSTANCE_HOURLY * $HOURS_PER_MONTH" | bc)
TRAFFIC_MONTHLY=$(echo "$TRAFFIC_PER_GB * $TRAFFIC_GB_PER_MONTH" | bc)
TOTAL=$(echo "$INSTANCE_MONTHLY + $TRAFFIC_MONTHLY" | bc)

echo "=== GA POSTPAY Estimate ==="
echo "Instance spec fee: CNY $INSTANCE_MONTHLY/month"
echo "Traffic fee: CNY $TRAFFIC_MONTHLY/month"
echo "Estimated total: CNY $TOTAL/month"
```

---

## 4. PREPAY Bandwidth Package Estimate

```bash
#!/bin/bash
BANDWIDTH_MBPS="${1:?Please provide bandwidth in Mbps}"
MONTHS="${2:-1}"

# Example unit price: 100 CNY/Mbps/month; query current prices for accurate results.
PRICE_PER_MBPS_MONTH=100

TOTAL=$(echo "$BANDWIDTH_MBPS * $PRICE_PER_MBPS_MONTH * $MONTHS" | bc)

echo "=== Bandwidth Package Estimate ==="
echo "Bandwidth: ${BANDWIDTH_MBPS} Mbps"
echo "Duration: ${MONTHS} month(s)"
echo "Estimated cost: CNY $TOTAL"
```

---

## 5. Query Existing Resource Bills

### GA spending in the last 7 days

```bash
START_TIME=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

aliyun bssopenapi query-bill-overview \
  --billing-cycle $(date +%Y-%m) \
  --product-code ga | jq '.Items.Item[] | {ProductName, PretaxAmount, Usage}'
```

### Bill details by instance ID

```bash
GA_ID="ga-bp1xxxx"

aliyun bssopenapi query-instance-bill \
  --billing-cycle $(date +%Y-%m) \
  --product-code ga \
  --instance-id "$GA_ID" | jq '.Items.Item[] | {PretaxAmount, Usage, UsageUnit}'
```

---

## 6. Skill Integration Notes

After Step 1 (select billing mode), optionally ask:

```
Question: Do you want to estimate the cost of this deployment?
- Option 1: No (default)
- Option 2: Yes

If yes:
1. Ask for instance type, billing mode, bandwidth, and estimated traffic.
2. Call bssopenapi QueryProductList or DescribePricing to query current prices.
3. Output the estimate and ask the user to confirm before continuing.
```

---

## 7. Notes

1. Prices vary by region, ISP, and promotions; the unit prices in scripts are examples only.
2. POSTPAY cost = specification fee + traffic fee (CDT).
3. PREPAY cost = specification fee + bandwidth package fee.
4. Cross-border scenarios may incur extra cross-region bandwidth fees.
5. New users may have free credits or trial offers, so actual costs may be lower than estimates.
