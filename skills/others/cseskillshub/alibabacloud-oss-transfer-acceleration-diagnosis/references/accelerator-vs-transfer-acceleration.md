# M2: OSS Data Accelerator vs Transfer Acceleration - Selection Matrix

Two different products are routinely confused in tickets: the **OSS
Data Accelerator** and **Transfer Acceleration**. They solve different
problems and are not substitutes.

## Product facts

| Dimension | Data Accelerator | Transfer Acceleration |
|---|---|---|
| What it is | A dedicated cache layer for **hot data reads** (large-file / high-QPS read caching) | A **network-path optimization** for uploads and downloads over long-distance links |
| Where it helps | **Same-region** repeated reads of hot objects (cache-hit acceleration) | **Cross-border / cross-region** access where latency or loss on the public path is the bottleneck |
| Access path | Same-region VPC access through a dedicated accelerator endpoint (feature-specific configuration) | Replace the client Endpoint with the accelerate domain `oss-accelerate.aliyuncs.com` (or `oss-accelerate-overseas.aliyuncs.com`) |
| Does not help | Cross-border latency - it caches within one region and never shortens an international link | Same-region cold reads - if client and bucket are in the same network/region, plain endpoints already give the best path |
| Billing posture | Capacity-based accelerator resources (see official pricing page) | Enabling is free; per-direction acceleration traffic fees stack on top of regular traffic fees (see [fee-facts.md](fee-facts.md)) |

## Selection logic (mirrors the script's `selection_advice`)

| Access pattern | Workload | Advice |
|---|---|---|
| cross-border | any | **Transfer Acceleration** - the Data Accelerator cannot shorten an international link |
| cross-region (mainland <-> mainland) | upload-download | **Transfer Acceleration** |
| same-region | hot-cache-read (repeated reads of the same hot objects, read-heavy) | **Data Accelerator** candidate; otherwise plain endpoints |
| same-region | upload-download | **Neither** - plain endpoints are correct; acceleration adds cost without benefit |
| unknown pattern | unknown | **Needs clarification** - ask where the clients run and what the bottleneck symptom is before recommending |

## The ticket-proven confusion pattern

Real tickets show the recurring mistake: a customer with **cross-border
slow access** configures the **Data Accelerator** (or an on-premises
cache-style product), sees no improvement, and opens a ticket asking why
"the accelerator" does not work. The diagnosis is:

1. The symptom (cross-border latency) is a **link** problem, so the
   matching product is **Transfer Acceleration**.
2. The Data Accelerator only caches hot reads **within one region**; it
   physically cannot improve an overseas client's round trip to a
   mainland bucket.
3. Corrective guidance: evaluate Transfer Acceleration for the affected
   bucket, enable it in the OSS console (manual action), and replace
   client endpoints with the accelerate domain - see
   [adoption-decision-tree.md](adoption-decision-tree.md).

The reverse mistake also happens: enabling Transfer Acceleration for a
same-region read-heavy workload and paying acceleration traffic fees
for no measurable gain - the answer there is to switch the workload to
plain endpoints (or evaluate the Data Accelerator if reads are hot and
repeated).

## Official acceleration portfolio (context for selection)

The official performance-acceleration overview lists FIVE acceleration
options; this skill owns only the two above, the rest are named so the
Agent can defer instead of guessing:

| Official option | One-liner | Deferral target |
|---|---|---|
| CDN acceleration | Edge caching of static content (CNAME to CDN) | CDN product docs / CDN skill |
| Transfer Acceleration | Backbone-network path optimization (this skill) | - |
| Global Accelerator (GA) | Dedicated GA instance for cross-country access with listener + endpoint configuration | GA product docs |
| EFC distributed cache | P2P read-only cache for mounted file systems (AI training) | EFC product docs |
| OSS Data Accelerator | Same-region NVMe cache for hot reads (this skill's M2 comparison) | - |

Same-family context: single-link speed limiting and resource-pool QoS are
the official bandwidth-MANAGEMENT tools (not acceleration) - billing or
throttling questions about them belong to the billing skill.

Also note: buckets WITHOUT a region attribute do not support transfer
acceleration (official region-attribute doc) - a "cannot enable" finding
worth checking before deeper diagnosis.

## Data Accelerator status query - API boundary (TAC-2)

This skill deliberately does **NOT** call `GetBucketDataAccelerator`
to read the Data Accelerator's state. API integration was evaluated
and ruled out by first-hand read-only probes (2026-09, STS role
skillsclienttest, bucket test-agentceping, oss2 2.19.1 issuing a
V4-signed raw `GET /?dataAccelerator=` sub-resource request):

| Probe path | Endpoint | Result |
|---|---|---|
| Public region endpoint | `https://oss-cn-hangzhou.aliyuncs.com` | **403 AccessDenied, `EC 0024-00000008`** "Configuration is disabled for the current user" (RequestId `6A981BB5B636B739365322C1`; a verbose-parameter retry returned the same: RequestId `6A981BB55F75A93532097BFA`) |
| Dedicated accelerator domain | `https://cn-hangzhou-j-internal.oss-data-acc.aliyuncs.com` | ConnectTimeout from the public internet - the `oss-data-acc` domain serves intranet accelerator access only |
| SDK surface | oss2 2.19.1 | No `get_bucket_data_accelerator` method exists |

Interpretation - **function gating, not a RAM permission gap**: the probe
role held ReadOnlyAccess (its `oss:Get*` wildcard already covers
`oss:GetBucketDataAccelerator`), yet the service answered 403 with
`EC 0024-00000008` "Configuration is disabled for the current user".
That error code marks a feature-availability boundary for the
account/user; do NOT chase it with RAM policy changes.

> Catalog status of `EC 0024-00000008` - **first-hand measured, officially
> uncatalogued**: this code is a first-hand measured behavior and is NOT
> present in the official 0024 EC family (the official family lists 37 codes,
> 0024-00000001~004 / 101~108 / 201~202 / 301~307 / 401~407 / 501~508 / 801;
> `search "0024-00000008"` returns no doc). Never present it as an officially
> catalogued error code - cite the RequestId-level probe evidence above
> (`6A981BB5B636B739365322C1` / `6A981BB55F75A93532097BFA`) as its source. The
> sibling skill alibabacloud-oss-transfer-error-code-diagnosis only routes this
> code onward (referral-only) and likewise does not claim it as official.

Feasible ways to determine the acceleration states:

- **Transfer Acceleration (this skill's own evidence)**:
  `GetBucketTransferAcceleration` via the entry script is the reliable
  API path (404 `NoSuchTransferAccelerationConfiguration` = feature
  never enabled). Console path (same page that carries the on/off
  switch, per [adoption-decision-tree.md](adoption-decision-tree.md)):
  OSS console -> target bucket -> Bucket Configuration -> Transfer
  Acceleration.
- **Data Accelerator**: no reachable public API path from this skill's
  SDK surface (see the probe table above). SDK requirement note:
  reading the `dataAccelerator` sub-resource requires a client that
  implements the raw sub-resource call AND an account for which the
  feature is enabled - oss2 2.19.1 has neither. Use the console
  accelerator management pages instead (official docs: OSS Accelerator
  overview / create-accelerator / accelerator-preheating, listed
  below), or ask the user for a console screenshot of the Data
  Accelerator page and state the evidence source explicitly.

`related_apis.yaml` therefore declares no `GetBucketDataAccelerator`
entry: the API is never called, so it must not be declared (no-fabrication
rule, SKILL.md Absolute Rule 4).

## Boundaries

- This module only advises on product selection. It never enables,
  configures, or purchases anything.
- The Data Accelerator's live state is not queryable within this skill's
  API surface (see the TAC-2 boundary above); selection advice here is
  pattern-based, never state-fabricated.
- Detailed bill attribution for either product belongs to
  alibabacloud-oss-billing-diagnosis; plain internal/public endpoint
  and region choice belongs to
  alibabacloud-oss-endpoint-internal-diagnosis.

## Official documentation sources

- Transfer Acceleration user guide:
  <https://help.aliyun.com/zh/oss/user-guide/transfer-acceleration>
- Transfer Acceleration fees (value-added billing item):
  <https://help.aliyun.com/zh/oss/value-added-billing-item/>
- GetBucketTransferAcceleration API reference:
  <https://help.aliyun.com/zh/oss/developer-reference/getbuckettransferacceleration>
- OSS Accelerator overview:
  <https://help.aliyun.com/zh/oss/user-guide/overview-77/>
- Create / modify / delete an OSS accelerator:
  <https://help.aliyun.com/zh/oss/user-guide/create-accelerator>
- OSS Accelerator preheating:
  <https://help.aliyun.com/zh/oss/user-guide/accelerator-preheating>
