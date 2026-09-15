# M3: Transfer Acceleration Fee Fact Sheet

Fee-semantics answers for "why am I billed for acceleration traffic"
and "is acceleration charged on top of normal traffic". All figures and
rules below come from the official documentation (help.aliyun.com
transfer-acceleration-fees, verified 2026-08) unless noted.

## Core fee rules

1. **Enabling is free.** Switching transfer acceleration on or off in
   the console costs nothing; only acceleration traffic is billed.
2. **Acceleration traffic is billed separately from, and in addition
   to, regular traffic fees.** When data travels through the accelerate
   domain, the customer pays BOTH the applicable public internet /
   downstream traffic fee AND the acceleration traffic fee. Using plain
   endpoints never incurs acceleration fees.
3. **Direction matters.** Fees are grouped by the origin/destination
   pair of the transfer; cross-border directions are priced higher than
   mainland-to-mainland.
4. **Disabling stops future acceleration fees** (after the ~30-minute
   propagation window) because traffic leaves the acceleration path -
   but clients must switch back to plain endpoints, or their requests
   to the accelerate domain will fail.
5. Unit prices vary by direction and change with official pricing; the
   skill explains the structure, never quotes an unverified price.
   Typical ticket-reported reference points (customer bills, not an
   official quote): mainland cross-region acceleration around
   0.50 CNY/GB and cross-border around 1.25 CNY/GB - always refer the
   user to the official pricing page for the authoritative number.

## Per-direction billing item codes

Acceleration traffic appears in bills/metering under four direction
families (in/out measured at the OSS side):

| Code family | Direction | Meaning |
|---|---|---|
| `AccM2MIn` / `AccM2MOut` | mainland <-> mainland | Cross-region acceleration inside mainland China (cheapest direction) |
| `AccM2OIn` / `AccM2OOut` | mainland <-> overseas | Cross-border transfer between mainland China and outside |
| `AccO2MIn` / `AccO2MOut` | overseas <-> mainland | Cross-border transfer from outside into mainland China |
| `AccO2OIn` / `AccO2OOut` | overseas <-> overseas | Transfer between two non-mainland locations (matches `oss-accelerate-overseas.aliyuncs.com`) |

## Acceleration-fee attribution field (access-log semantics)

In OSS access logs, whether a request generated acceleration fees and
which direction it belongs to is carried by the `acc_linetype` field
(four-value table, format `<direction>#<link>#<charged>`):

| acc_linetype value | Billing type |
|---|---|
| `1#1#1` | mainland -> overseas, dedicated backbone link, charged |
| `2#4#1` | mainland -> overseas, public network, charged |
| `3#4#1` | overseas -> mainland, public network, charged |
| `4#4#1` | overseas -> overseas, public network, charged |

Metering records expose the same four directions as `acc_m2m_in/out`,
`acc_m2o_in/out`, `acc_o2m_in/out`, `acc_o2o_in/out` traffic fields.

Use this table only to EXPLAIN which line on a customer's evidence
corresponds to acceleration billing. Itemizing a concrete bill (amounts,
resource-plan deductions, region aggregation) belongs to
alibabacloud-oss-billing-diagnosis; this skill stops at semantics.

**Portability boundary (TAC-2)**: `acc_linetype` and the `acc_*`
metering fields are access-log / metering semantics only - they record
which direction a PAST request was billed as. They are NOT an
API-queryable configuration state and cannot be ported to answer "is
transfer acceleration enabled" (that is GetBucketTransferAcceleration,
queried by the entry script) or "is the Data Accelerator configured"
(no public API path within this skill's surface - see the Data
Accelerator status-query API boundary in
[accelerator-vs-transfer-acceleration.md](accelerator-vs-transfer-acceleration.md)).

## Script-facing summary (`billing_notes`)

The entry script's `billing_notes` field emits exactly these rules:
free enablement, independent-and-stacked charging, direction-based
item codes, and the boundary that detailed bill attribution is deferred
to the billing skill. Fee questions answered outside the script must
relay the same facts and never invent unit prices.
