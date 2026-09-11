# Help Center Product Codes

Product codes (slugs) used in help-center URLs and in the `-p/--product` option of
`scripts/aliyun_help.py`. Codes are lowercase, and **the same slug space serves both
portals**:

| portal | document URL shape | product llms.txt shape |
|---|---|---|
| `cn` (help.aliyun.com) | `https://help.aliyun.com/{lang}/{product_code}/...` | `https://help.aliyun.com/{lang}/{product_code}/llms.txt` |
| `intl` (www.alibabacloud.com) | `https://www.alibabacloud.com/help/{lang}/{product_code}/...` | `https://www.alibabacloud.com/help/{lang}/{product_code}/llms.txt` |

`{lang}` is `zh` or `en` on `cn`, and `en`, `zh`, `tc`, `ja`, `id`, `pt-br` or `fr` on
`intl`. The slug of a given product is the same on both portals and in every language;
what differs is the corpus behind it, so the local cache is keyed by
(site, lang, product) and the two portals are never mixed in one query.

## Quick reference

| Code | Product |
|---|---|
| `ecs` | Elastic Compute Service |
| `oss` | Object Storage Service |
| `rds` | ApsaraDB RDS |
| `slb` | Server Load Balancer |
| `vpc` | Virtual Private Cloud |
| `eip` | Elastic IP Address (a separate product from VPC; see aliases below) |
| `cdn` | Content Delivery Network |
| `ack` | Container Service for Kubernetes |
| `functioncompute` | Function Compute (**not** `fc`; `fc` only 301-redirects) |
| `nas` | File Storage NAS |
| `dns` | Alibaba Cloud DNS |
| `ram` | Resource Access Management |
| `sts` | Security Token Service |
| `kms` | Key Management Service |
| `waf` | Web Application Firewall |
| `ddos` | Anti-DDoS |
| `cms` | CloudMonitor |
| `sls` | Simple Log Service |
| `api-gateway` | API Gateway |
| `mns` | Message Service |
| `rocketmq` | Message Queue for RocketMQ |
| `kafka` | Message Queue for Apache Kafka |
| `elasticsearch` | Elasticsearch |
| `dataworks` | DataWorks |
| `maxcompute` | MaxCompute |
| `pai` | Platform for AI |
| `model-studio` | Model Studio |
| `actiontrail` | ActionTrail |

## Aliases and non-obvious codes

Common aliases and product relationships that frequently cause empty results:

| What you might type | Correct code | Note |
|---|---|---|
| `fc` | `functioncompute` | Function Compute's canonical code is `functioncompute`; `fc` only 301-redirects (on both portals) and breaks llms.txt fetches |
| `sas` | `security-center` | Security Center's canonical slug is `security-center`; `sas` answers HTTP 200 with a **zero-byte body** on both portals, i.e. the slug does not exist |
| `alb`, `nlb`, `clb` | `slb` | Application Load Balancer, Network Load Balancer and Classic Load Balancer are documented under the Server Load Balancer slug `slb`; all three own slugs answer HTTP 200 with a zero-byte body on both portals |
| `cs` | `cs` **or** `ack` — not aliased | Container Service (`cs`) and Container Service for Kubernetes (`ack`) are two distinct live indexes (measured 144461 B vs 90559 B on `cn`/`zh`), so the script deliberately does not collapse them; pick the one you mean |
| EIP / Elastic IP (under `vpc`?) | `eip` | Elastic IP Address is an independent product with its own code `eip`, **not** part of `vpc` |

The first four rows are normalized automatically by `_normalize_product_code`, which
leaves an `INFO:` line on stderr. The alias table is embedded in the script as a constant
and is not split per portal: both portals were verified to use the same slug for every
entry (2026-09-08).

Rules of thumb:

- When a product-scoped search returns nothing, suspect the code first: verify it
  with `list-products` **run with the same `--site`/`--lang`**, then retry with the
  canonical code (or without `-p`). The two portals do not carry the same product
  portfolio, so a slug that exists on one may be absent from the other, and there is no
  cross-site fallback.
- Codes can be verified against the help-center catalog at any time:
  `python3 scripts/aliyun_help.py list-products` prints the default scope and
  `list-products --site intl --lang en` the international one. Measured 2026-09-08, every
  product line of both masters resolves to a usable code: 461 entries on `cn`/`zh` (218
  plain slugs, 64 `product/{id}.html`, 178 `document_detail/{id}.html`) and 228 on
  `intl`/`en`. A `document_detail/{id}.html` code is passed to `-p` verbatim, including the
  slash. One `cn`/`zh` line has no code — the Apsara Stack entry, whose index URL sits
  outside the language tree and answers HTTP 302; it shows as `(unknown)` and cannot be
  scanned. The unscoped index scan walks the de-duplicated set behind these numbers (412
  distinct products on `cn`/`zh`, 215 on `intl`/`en`): the master repeats a product across
  sections, so raw entry counts are larger than the number of indexes fetched.
  See `search-backend.md` for the shapes and the scan itself.

## Caveats

- Most codes match the product's English name, but there are exceptions (Function
  Compute is `functioncompute`, not `fc`).
- Some products use numeric IDs as codes (for example, vector search uses `2510217`).
  Use `list-products` to discover them.
- Help-center codes (lowercase, e.g. `actiontrail`) belong to a different system than
  OpenAPI metadata codes (PascalCase, e.g. `Actiontrail`). The script's `api-*`
  subcommands normalize case automatically; raw `curl` calls against the meta endpoints
  require exact casing (the `api-products` output shows the exact casing for every
  product). The metadata endpoints are site-independent, which is why `api-*` takes no
  `--site`/`--lang`.
- The international portal is a **fully supported retrieval path**, not a footnote: it
  has its own master and per-product llms.txt indexes in seven languages, its own
  full-text endpoint (see `search-backend.md`), and the same `.md` document-body
  convention (`https://www.alibabacloud.com/help/en/oss/user-guide/what-is-oss.md`
  returns `200` with `content-type: text/markdown;charset=UTF-8`, byte-identical with and
  without a User-Agent header). Its portfolio is narrower than the `cn` one and its
  error-code corpus is markedly thinner, so a query that succeeds on `cn` may legitimately
  return nothing there.
- **A dead slug answers `200`, never an error status.** This is the single most misleading
  behaviour of the whole surface, and it comes in three shapes (all measured 2026-09-08):

  | body | meaning | examples |
  |---|---|---|
  | `200` + 0 bytes | the slug does not exist on that portal at all | `sas`, `alb`, `nlb`, `clb` on both portals |
  | `200` + `Sorry, this product does not have LLMS content yet.` (51 B) | the product is in the catalog but has no llms.txt corpus on that portal | `ahas`, `dbfs` on `intl` (both have a full corpus on `cn`) |
  | `200` + ~92 KB `bxpunish` WAF interstitial HTML | intermittent rate limiting, not a statement about the slug | observed on `intl` for both a product index and the master index |

  An unsupported language is different again: it answers `302` to the English index.
  The script recognises all four cases, never caches a body that is not a real index,
  reports "no documentation on this site" with a WARN naming the portal and language, and
  exits `1` rather than serving an empty index as a result.

## How a product code is resolved at run time

`list-products` enumerates the llms.txt catalogue only; it never consults a search facet, and
the codes it prints are exactly the three shapes the master uses (plain slug,
`product/{id}.html`, `document_detail/{id}.html`). Pass a `document_detail/...` code to `-p`
verbatim.

When a product-scoped search needs a `categoryId`, the script tries the search facet first,
then the wide-result mode vote, then the product landing page `nodeId`. The landing value is
only a candidate: measured over the 14 built-in seed entries, `nodeId` matched the endpoint
`categoryId` for 9 and differed for 5 (including `slb`, `rds`, `ack`, `polardb` and `waf`), so
a landing-derived id is cached only after a filtered query has returned results. If the seed
table is wrong for a product, correct it here rather than relying on the fallback.

`list-products --show-sites` additionally prints the site x language block the master index
publishes. It is display only: the queryable scope stays `cn` (zh, en) and `intl`
(en, zh, tc, ja, id, pt-br, fr), and a missing or reshaped block is reported and skipped.
