# M2 — Console Entries and Filter Parameters ("where do I actually look")

Half of the "the bill is wrong" tickets are "the bill is on another page".
Point the customer at the exact entry with the exact filters, then ground
the discussion in the same numbers the script printed.

## Bill / expense entries

| Entry | URL | Filters / parameters | Use it for |
|---|---|---|---|
| Bill detail (per instance) | https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance | `BillingCycle=YYYY-MM`, `StatisticItem=DEFAULT_CHARGE_ITEM` (per billing item) or `RESOURCE` (per resource), `StatisticCycle=MONTHLY`; switch time granularity to DAY for a daily traffic series; CSV export here | The authoritative per-item breakdown; answering "show me the detail" |
| Month bill overview | https://billing-cost.console.aliyun.com/finance/month-bill/account | month picker | Per-product summary: payable / paid / due columns |
| Expense report | https://billing-cost.console.aliyun.com/finance/expense-report | — | Report entry after CDT upgrade: filter product = Cloud Data Transfer, commodity = CDT-internet, "combined payable amount = 0" to see fully covered usage |
| My orders | https://billing-cost.console.aliyun.com/order/list | `pageIndex`, `pageSize`, `timeRange` | Auto-renewal payments live HERE, not in the bill detail: separates "156.4 yuan renewal order" from "post-paid settlement" |
| Billing center top-up | https://usercenter2.aliyun.com/home | — | Settling arrears (manual customer action) |
| Resource packages / coupons inventory | billing console resource-package / coupon pages | — | Package remaining quota / validity and coupon applicability (no read-only inventory API is whitelisted in this skill; guide the customer to the page) |

## Related product entries

| Entry | URL | Notes |
|---|---|---|
| CDT overview | https://cdt.console.aliyun.com/overview | Traffic usage, updated hourly, NOT real time |
| CloudMonitor host monitor | https://cloudmonitornext.console.aliyun.com/hostMonitor/ | Bandwidth curves around a suspected saturation window |
| ECS console instances | https://ecs.console.aliyun.com/server/region/cn-hangzhou | Region-scoped instance list; check charge type / bandwidth mode |
| ECS console snapshots | https://ecs.console.aliyun.com/snapshot/region/cn-hangzhou | Snapshot inventory per region (operations belong to the snapshot skill) |
| ActionTrail events | https://actiontrail.console.aliyun.com/cn-beijing/events | "Who performed the operation" — handoff aid, out of this skill's scope |
| RAM overview | https://ram.console.aliyun.com/overview?activeTab=overview | Sub-account existence checks |

## Known page traps

- "The expense-overview landing pages do NOT show daily traffic
  consumption": use Bill detail with product = ECS, billing item = public
  traffic, granularity = DAY (ticket-verified correction).
- "I clicked Details on the deduction and the page is empty": almost always
  the wrong bill month (a deduction at the start of month N belongs to
  cycle N-1) or the wrong statistic dimension — switch the month and set
  `StatisticItem=DEFAULT_CHARGE_ITEM` / `RESOURCE`.
- Resource-package remaining-quota views live on the package pages, not on
  the bill detail.
- Console entry names change; when a path is not found, search the billing
  console for "bill detail" rather than guessing deeper URLs.
