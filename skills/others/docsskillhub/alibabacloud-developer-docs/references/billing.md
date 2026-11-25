# Billing, renewal, cancellation, and bill usage guide

For questions about billing rules, detailed prices, cost estimation, renewal, cancellation & refund, or bills, combine product billing bodies, official website prices, and the corresponding site's Billing Management bodies per this guide. Generic search/read, unavailable-evidence and conflict handling follow Doc retrieval rules; product identification follows the Product code table.

## 1. Distinguish the request and its evidence sources

| What the user asks | Where to look first | What to verify |
| --- | --- | --- |
| how it charges, which billable items exist, pay-as-you-go vs. subscription, how resource packages deduct | the target product's billing catalog and bodies | billed object, metering rules, billing method, cycle, free quota and deduction conditions |
| how much a billable item costs, budget estimation, cost comparison of options | product billing rules + the confirmed site's official product price page | exact billable item, region/spec/tier, price unit, currency, applicability conditions |
| cancellation, refund, renewal, auto-renewal, expiry and overdue | product bodies + the site's Billing Management bodies | product-specific conditions, generic operations, timing, amount rules, resource impact |
| how to read bills, why a charge occurred, fees not matching usage | product billing rules + the site's bill explanations + user-provided redacted details | billing period, billable items, usage, unit price, deductions, payable/paid and adjustments |

Determine site and product per `SKILL.md`; for purely generic bill or renewal-operation questions, do not force a cloud product choice first — query that site's Billing Management docs directly. Verify multi-product fee questions product by product; never explain all fees with one product's doc.

## 2. Look up the product's full billing rules

Browse the billing catalog with `list-docs` first, then search official wording per the request and `read` the needed bodies; never rely on fixed titles or guessed page paths:

    python3 scripts/aliyun_help.py list-docs <doc-product-code> -n 0 --site cn -L zh
    python3 scripts/aliyun_help.py search "计费概述" -p <doc-product-code> -n 5 --site cn -L zh
    python3 scripts/aliyun_help.py search "计费项" -p <doc-product-code> -n 5 --site cn -L zh
    python3 scripts/aliyun_help.py search "计费方式" -p <doc-product-code> -n 5 --site cn -L zh
    python3 scripts/aliyun_help.py read <hit billing doc URL>

(The Chinese keywords above mean "billing overview", "billable items", "billing methods" — China-site corpus examples.) On the International site add `--site intl -L <language>` with keywords matching the corpus language, e.g., `billing overview`, `billable items`, `billing methods`; `read` takes no `-L`. When titles miss, switch to wording used in bodies, e.g., the Chinese terms `收费项` / `按量付费` / `资源包` (chargeable items / pay-as-you-go / resource packages).

Extract the fields below per the question; treat only what bodies explicitly state as facts, and label missing items not yet verified:

- **Billable items and metering**: billed object, trigger conditions, counting basis, unit, metering granularity, tiered or segmented rules, formulas.
- **Billing method and cycle**: prepaid/postpaid, pay-as-you-go/subscription, settlement or billing cycle, billing start/stop points; never confuse the metering unit with the billing cycle.
- **Quotas and deductions**: free quota, resource-package/plan applicable regions and billable items, deduction order, validity, overage fees.
- **Related fees and limits**: other chargeable items, cross-region/public-network applicability, expiry and overdue handling; never turn "one item is free" into "the whole product is free".

Billing docs verify rules; price pages verify concrete prices. Some docs also contain unit prices — never claim all docs lack prices. Not finding docs does not mean the product is free of charge; not finding a unit price does not mean it is free.

## 3. Look up detailed prices and state conditions

**Fixed order for detailed prices: official website first, then doc examples — never the reverse.**

1. First locate the official price entry for the confirmed site and product. China-site example: the user-provided `https://www.aliyun.com/price/product#/nas/detail/nas`; confirm the real detail page/iframe from the entry, then read raw price data as below. That NAS address is an entry example only — its prices and data structure are not thereby verified.
2. When an official price matching the user's region, spec, billable item, billing method, and tier is obtained, prefer it for quoting or estimation; product docs verify billing formulas, quotas, and deduction rules — never replace an obtained official price with a doc's example unit price.
3. When the website offers no matching price or cannot be read this time, state whether it is "no applicable price found" or "official price currently unverifiable", then `search` → `read` the corresponding site's docs; only with an applicable unit price and formula make an example estimation, noting source, conditions, and assumptions. With no usable doc unit price either, compute no amount — list the missing price conditions and give the official entry.
4. **Every detailed-price/cost-estimation reply must state: `价格以官网为准，文档价格仅为示例。`** When using doc prices, additionally mark "the following uses doc example prices, not live official quotes"; never present fallback results as current sale prices or actual bill amounts. Express the notice equivalently in the answer language, e.g., "Prices on the official website prevail; document prices are examples only."

First distinguish the price-calculator shell from the actual detail document. The verified raw price data page for OSS on the China site is `https://www.aliyun.com/price/detail/oss`: an anonymous GET's HTML contains hidden `textarea` JSON, readable without executing frontend components. `https://www.aliyun.com/price/product#/oss/detail/oss` is the calculator shell; `https://www.aliyun.com/price/detail?saleProductCode=oss` is also an entry — never conclude dynamic quoting is required just because the entry body shows no unit price. Confirm `saleProductCode` values and the sales-product identifier in detail paths from the product's official billing body/price entry; they belong to a different identifier system than doc codes and OpenAPI codes and are not interchangeable. Other products' `/price/detail/<sales-product-id>` paths are candidates only — confirm the product and actual price data after an anonymous GET; never assume OSS's structure. Navigation tracking parameters need not be kept.

**Raw HTML → hidden JSON → price tables with context**:

1. Fetch the actual detail page's raw HTML with an anonymous GET, not only a page-to-text tool; text tools may ignore hidden elements. If the page is a shell, check official detail links/iframe addresses; never load tracking, login-state queries, or unverified internal quoting APIs.
2. Extract each `textarea`'s text with an HTML parser, decode HTML entities, then parse with `json.loads`; keep the owning module identifier. Parse data only — no `eval`, no executing embedded JavaScript, no dumping whole-page HTML or the full price matrix.
3. OSS's data object contains `moduleinfo`, `priceArray`, etc.; price tables live mainly in `priceArray[*].firstTableWrap`, not only under `moduleinfo`; the same group may also have `secondTableWrap`, `thirdTableWrap`, `fourthTableWrap`. `$context` holds duplicate copies — dedupe by owning module and identical data; never treat repeated occurrences of one matrix as multiple independent quotes.
4. Keep `moduleinfo.title/text`, the group's `regions/databases`, each table's title/description and header row, then select tables by the user's region, billable item, and billing method. Numeric keys `"1"`, `"2"`, `"3"`, etc. are column identifiers, not fixed parameter semantics; interpret them with that table's headers — never force the same column names onto all tables. Catalog prices, website discount prices, public cloud and finance cloud must not be mixed.
5. Cells may contain free quotas, tiers, time windows, minimum metering/storage durations, and notes — never extract just one amount; `/`, blanks, or values like `不涉及` ("not applicable") must not be converted to zero or used to guess support. Output only matching tables and conditions, preserving raw values and notes.

- **China site**: prefer the embedded price data in the official detail HTML, verified against the product's billing body. OSS's `oss-domestic-tables` / `oss-abroad-tables` separate region tables; RMB prices for overseas regions on the China site are not International-site quotes.
- **International site**: locate its official price entry from the International site's product billing body; never re-domain a China-site price page into an International quote, and never convert RMB prices by exchange rate to pose as International prices. When it cannot be located, state plainly that International prices are not yet verified.
- **Page-reading boundaries**: price pages are not Help Center bodies — never hand them to `aliyun_help.py read` as documents. Check the raw HTML's embedded data and detail links first; only when no usable data exists and interaction/login is required, state the limitation and ask the user to view it themselves and paste back relevant quote conditions and unit prices. Form configuration, product catalogs, and navigation/marketing content are not price evidence — never accepted just because product/billable-item names appear; no calling unverified internal quoting APIs, no cookies/tokens, no logging in on the user's behalf.
- **Quoting unit prices**: record query date, site, billable item, region/spec, billing method, tier, value, currency, unit, tax basis, and discount applicability. Fields the page does not state stay unknown — never copy just a number; public prices are not the user's contract price or final charge.
- **Cost estimation**: compute only from verified billing formulas, prices for the matching conditions, and user-confirmed usage; preserve dimensions, tiers, and deduction conditions, and mark assumptions and excluded fees. With insufficient information, first ask about conditions that affect the calculation — never guess monthly usage, default regions, or a uniform unit price.
- **Historical fees**: current prices do not prove historical periods' unit prices; check the prices/billing-change announcements effective then plus the user's details, fetching announcement full text per Announcement search rules. When price pages and docs conflict, list dates, conditions, and sources; before the conflict is explained, never pick one amount as final.

## 4. Cancellation, renewal, and bills: query product docs and Billing Management together

The doc entries below are verified via `list-products` on both sites; they are doc catalogs, not the user's bill console:

| Site | Catalog name / doc product code | Entry |
| --- | --- | --- |
| China site | `费用与成本` (Expenses and Costs) / `user-center` | `https://help.aliyun.com/zh/user-center/` |
| International site | Expenses and Costs / `user-center` | `https://www.alibabacloud.com/help/en/user-center/` |

The same doc code on both sites today does not mean identical cancellation, refund, renewal, or bill rules; still verify against the current site's catalog and bodies before use. The International site's Account Center uses doc code `account` — never treat Account Center as the Expenses and Costs catalog. Locate and verify other-language International entries per site rules; never quote them by simply swapping the language segment.

    python3 scripts/aliyun_help.py list-products user --site cn -L zh
    python3 scripts/aliyun_help.py list-products Costs --site intl -L en
    python3 scripts/aliyun_help.py list-docs user-center -n 0 --site <site> -L <language>
    python3 scripts/aliyun_help.py search "<single keyword for cancellation/renewal/bills>" -p <doc-product-code> --site <site> -L <language>
    python3 scripts/aliyun_help.py search "<same keyword>" -p user-center --site <site> -L <language>
    python3 scripts/aliyun_help.py read <relevant body URL>

When the Billing Management name misses, switch to that site's official wording; never accept irrelevant fuzzy hits. Search product bodies and Billing Management bodies in parallel as needed; never claim a generic operation is undocumented after checking only product docs. Skip product retrieval for purely generic requests. Example cancellation bodies (each read and verified; still check applicability for the user's scenario — never use them as the basis for renewal or all bill questions):

- China site `发起退订` (Initiate unsubscription): `https://help.aliyun.com/zh/user-center/initiate-unsubscribe`
- International site "Initiate unsubscription": `https://www.alibabacloud.com/help/en/user-center/initiate-unsubscribe`

| Topic | Verify jointly on the product side and Billing Management side |
| --- | --- |
| Cancellation and refund | cancellable resource/order types, limits and deadlines, refund calculation, offer/deduction handling, payout method and cycle, post-cancellation resource and data impact |
| Renewal and expiry | which resources are renewable, manual/auto renewal, timing, renewal price/offer conditions, failure and post-expiry impact |
| Bills and charges | billing period/statement time, meaning of summaries and details, billable items and usage, unit prices and deductions, payable/paid, refund or adjustment records, download and reconciliation steps |

Billing Management's generic rules cannot cover every product's exceptions; check bodies' applicability, explain conflicts, and never promise from a generic page that a resource is definitely cancellable, renewable, or fully refundable. Distinguish cancellation refunds from account-balance withdrawal — similar names do not mean identical operations or amount rules.

## 5. Combined answer and operation boundaries

Per `SKILL.md` output constraints: conclusion first, then the rules, price conditions, handling/verification steps, and unverified items the question needs — no mechanical display of all sections, no catalog dumps or unrelated billable items. End with deduplicated titled doc links supporting the conclusions, stripping trailing `.md`: rules → product bodies, official unit prices → price pages, fallback example prices → docs marked as non-live quotes, cancellation/renewal/bill steps → same-site product and Billing Management bodies; never attach bill/order APIs. Whenever detailed prices or cost estimation are involved, state `价格以官网为准，文档价格仅为示例。` (equivalently in the answer language). Entry links are neither read quotes nor verified operation steps; give concrete conclusions only after reading the content.

- **Abnormal bills**: ask the user for the necessary redacted billing period, product, region, billable item, usage, unit price, deductions, and amounts, and compare item by item against the rules; never declare "double charging" or a root cause from public prices alone. Separate confirmed from pending items; with insufficient evidence, list the fields to check.
- **No account access**: never read local bill/account files, log in to Billing Management, or call bill/order APIs; the user obtains and provides account details themselves — remind them to mask account IDs, order/resource identifiers, and other sensitive content, and never send complete bills to anonymous retrieval tools.
- **No transactions on the user's behalf**: no purchasing, cancelling, refund requests, renewing, switching billing methods, or changing auto-renewal/payment settings. Explain only verified steps, prerequisites, amounts, and resource impact; the user executes and then reads back order/bill/resource state themselves.