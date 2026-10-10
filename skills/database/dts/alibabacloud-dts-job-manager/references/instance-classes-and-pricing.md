# DTS Instance Classes and Pricing

> Official sources:
> - [Data synchronization channel specifications](https://help.aliyun.com/en/dts/product-overview/specifications-of-data-synchronization-channels).
> - [DTS billable items](https://help.aliyun.com/en/dts/product-overview/billable-items).
>
> Specifications may change. Before purchase, require a validated current quotation for the selected class.

## Class selection

Retain a supplied class when it remains supported and has a valid quotation; query only that class and do not ask the user to select it again. When no valid selection exists, obtain quotations for all reviewed classes, display only supported classes with complete quotations, RPS references, prices, and applicable warnings, and require the user to select one. Do not preselect or recommend a class from RPS or price alone.

When `instance_class` is omitted, the CLI compiles `small`. That is only a field default, not the user's choice: when the user has not selected a class, still display the quotations and require a selection under this section, then write the result into the public input.

Recommend a class only when an applicable formal sizing source has been verified and every database load input required by that source has been obtained. Do not infer a class from the RPS or price table alone.

| Selectable CLI class | Incremental performance upper-limit reference (RPS) |
| --- | ---: |
| `micro` | 200 |
| `small` | 2,000 |
| `medium` | 5,000 |
| `large` | 11,000 |

> **Full official specification list:** Alibaba Cloud's official documentation also defines higher instance classes: `xlarge` (17,000), `2xlarge` (34,000), `4xlarge` (68,000), `6xlarge` (102,000), and `8xlarge` (136,000). See [Data synchronization channel specifications](https://help.aliyun.com/en/dts/product-overview/specifications-of-data-synchronization-channels). However, this CLI currently supports only the four lowercase classes in the table above. The Planner, compiled-plan validator, and price query must use this same exact list. Reject every other spelling, even when syntactically valid, before any price or cloud call; never delegate validation of an unknown value to the service.
>
> Data sourced via Firecrawl scrape (2026-08-11). Specifications may change; always confirm against the official documentation and purchase page before buying.

### Production warning for `micro`

Official documentation does not recommend `micro` for production environments. Include this warning whenever that class is offered or selected, including the pre-purchase review.

RPS means rows incrementally synchronized to the destination per second. It is a reference upper limit, not an SLA, byte-throughput guarantee, full-load speed, or latency promise. Actual performance depends on source load, transmission bandwidth, network latency, and destination write capacity; reaching the reference requires no destination bottleneck and no more than 2 ms network latency among source, destination, and DTS.

<a id="billing-and-quote-requirements"></a>
## Billing and quotation requirements

Creation uses `JobType=SYNC`, `PayType=PostPaid`, `SyncArchitecture=oneway`, and `IncreDataValidate=false`. Billing begins when incremental data collection starts and continues while the job is suspended.

Accept only a complete quote with `Currency=CNY`, `BillingQuantity=1`, and `BillingUnit=Hour`. Do not convert, infer, or estimate a price. `CURRENCY_UNSUPPORTED`, `CURRENCY_UNCONFIRMED`, `BILLING_DURATION_UNCONFIRMED`, or `BILLING_DURATION_MISMATCH` stops class presentation, confirmation, and purchase. The purchase page and final order remain official for the charged amount.

The review before purchase includes the selected class, RPS reference, DTS region, current quotation with currency and duration, billing start condition, and any warning required above. Use the selected class's `prices[].source` to explain its quotation: `cache` means a local quote valid for 24 hours; only `live` may be described as verified this run. Regardless of quote source, the purchase page and final order remain official for the charged amount.

<a id="service-access-evidence"></a>
## Query current prices

Run after validating the current CLI profile. Use the applicable path below; do not run an additional `--help` command to discover these documented arguments.

A request that only asks for a price is a read-only query: run `dtscli job price` and report the unit price, the currency, the billing unit, and where the quote came from, and do nothing else. Do not compile a plan, collect credentials, test connectivity, or run `create`, `start`, `pause`, or `rename`. Do not pick a class the user did not choose, do not recommend other classes, and do not re-query or repeat `--refresh-cache` for a fresher price.

Normal creation accepts a valid cached quote that is less than 24 hours old. Run `dtscli job price --refresh-cache` only when the user explicitly requires live verification in this run or a valid cached quote cannot satisfy the current review. This option only bypasses the price cache and queries the selected class live; it does not expand class or API scope and does not replace the database connection tests in `job create test`.

Instance price depends only on class. This Skill quotes one-way synchronization only. Do not pass region, engine, or architecture flags to `dtscli job price`.

```bash
# User supplied a class: query only the supplied class.
dtscli job price --instance-class <selected-class>

# Class unresolved: query all reviewed classes for user selection.
dtscli job price
```

`--instance-class` may be repeated to query multiple classes. Omit `--instance-class` only when no class has been selected.

Live quotation requests have no `--timeout` flag; each OpenAPI call times out after 10 seconds.

This command does not accept `--region`. The destination region is still required later for purchase and configuration.

Continue only when the exit code is zero and `prices` contains every class that will be displayed. There is no `status` field: success is the exit code, and failure carries `error_class`.

Field names are lowercase with underscores, and source values are lowercase:

| Field | Required interpretation |
| --- | --- |
| `currency` | Always `CNY`; never show an amount without it. Every price is the hourly rate of one postpaid one-way `SYNC` instance |
| `prices[].instance_class` | The quoted instance class |
| `prices[].trade_amount` | The decimal amount as a string; do not convert it through floating-point arithmetic |
| `prices[].source` | `live` means queried this run; `cache` means a valid local quotation less than 24 hours old |

The cache is keyed by instance class only. A quote for one class is never served for another.

At least one `live` item proves DTS service access for the current profile in this run; an entirely cached result does not. Continue with the next business command, or use `--refresh-cache` when live verification is required. Do not run a separate probe. A live quote for one class does not make cached quotes for other classes live.

Cache read or write diagnostics go to stderr. They do not invalidate a complete, validated quotation or require `--refresh-cache`; each item's `source` still identifies where its price came from.

On failure, follow `error_class` and stop before presenting classes or purchasing. If any requested class cannot be quoted, the entire query fails; it never returns an incomplete price set.
