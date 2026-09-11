# Search Backend Architecture

The `search` subcommand of `scripts/aliyun_help.py` uses a dual-leg design: a
relevance-ranked full-text leg as the primary path, and a deterministic llms.txt
index leg that guarantees degraded-but-functional search when the primary is
unavailable. When a product filter (`-p`) is given and the escape switch is not set,
the two legs run together and their results are fused (see "Multi-leg fusion" below).

Every request is scoped to exactly one (site, language) pair and the two portals are
never mixed inside one query. Which full-text backend serves which pair:

| site | lang | full-text leg | index leg |
|---|---|---|---|
| `cn` | `zh` (default) | doSearch — the unchanged legacy path | yes |
| `cn` | `en` | search.json (`website=cn&language=en`) | yes |
| `intl` | `en` (default), `zh` | search.json (`website=intl&language={en,zh}`) | yes |
| `intl` | `tc`, `ja`, `id`, `pt-br`, `fr` | skipped on purpose (guard S3) | yes, and it is the primary path |
| `cn` | `tc`, `ja`, `id`, `pt-br`, `fr` | invalid combination: exit `2`, no request issued | — |
| any | `ko`, `de`, `es`, `th`, `vi`, `tr`, `ru`, `it` | WARN, then the site default language is used | same |

All endpoint contracts, response envelopes and latency figures in this file were
re-measured against the live portals on 2026-09-08.

## Full-text backend 1: doSearch (`cn` + `zh` only)

- Endpoint: `GET https://t.aliyun.com/abs/search/doSearch`
- Query parameters: `queryWord` (URL-encoded keyword), `limit` (the requested page size,
  clamped to 2..200; an unscoped query asks for at most 20 so it still gets one top-ranked
  page), `bizType=help`, and optionally `categoryId` (numeric, server-side category filter;
  see below). `limit` is the **only** page-size parameter this endpoint honours: `pageSize`
  and `pageNo` are accepted and silently ignored (measured: `limit=50` answers 49 items,
  `limit=200` answers 198, `pageSize=50` answers 10), so one request fetches the whole page
  and no accumulation loop runs (F1, 2026-09-09).
- Response is JSON. Relevant fields:
  - `data.info[]`: result items, each containing `title`, `url`, `content`
    (HTML snippet), `productName`, `categoryName`, `gmtModifiedOrigin`, and
    `categoryId` (a prefixed string such as `help@@31815`; the numeric part is the
    value accepted by the `categoryId` request parameter)
  - `data.totalCount`: total match count
- **`pageSize` is ignored by this endpoint.** Its real page-size parameter is `limit`
  (measured 2026-09-08: `limit=50` returns 49 items, `limit=200` returns 198, while
  `totalCount` stays 427). Because this client sends `pageSize`, the server answers
  with its own default page of 10 items — that, and not a server-side cap on
  `data.info`, is why an unscoped query yields at most 10 results. `limit` is
  deliberately not adopted: switching to it would change the `cn` + `zh` result set,
  which must stay byte-for-byte identical to the pre-i18n behaviour.
- doSearch has **no language dimension at all**. An English query against the `cn`
  corpus recalls an order of magnitude less than the same query on the English corpus
  (13 vs 301, 5 vs 59, 25 vs 132 on three measured queries), which is exactly why
  `cn` + `en` is routed to search.json instead of doSearch.
- This is the same backend that powers the public help-center search box. It is an
  undocumented internal endpoint with **no SLA**: the response schema, rate limits,
  and even availability may change without notice. The index leg exists precisely for
  this reason.

### Field mapping

| Output field | Source |
|---|---|
| `title` | `title`, truncated at the first `" \| "` separator (drops the trailing product-name suffix); pure numeric titles (`^\d{4}-\d{8}$`, typically announcement-style documents) fall back to the first non-empty, non-numeric value among `seoTitle` / `originTitle` / `categoryName`, keeping the original title when no fallback exists. Every fallback value carries a `help@@` prefix on both portals (`help@@31815`, `help@@Object Storage Service`), so `_readable_title` strips it before returning; without that stripping the rendered line would show the raw prefix to the user. On current data `seoTitle` is always `None` on doSearch and absent on search.json, so the fallback chain effectively resolves to `categoryName`. |
| `url` | `url`, passed through unchanged |
| `desc` | `content` after HTML cleaning, truncated to 120 characters |
| `product` | `productName` on doSearch. search.json has no such field, so the product name is taken from `categoryName` with the `help@@` prefix stripped; when that is empty too, it is extracted from the URL with the site-scoped regex — `/{lang}/([^/]+)/` on `cn`, `/help/{lang}/([^/]+)/` on `intl`. `productName` is empty on about 2% of doSearch items, so the URL fallback stays necessary there as well. |
| `updated` | `gmtModifiedOrigin` (millisecond timestamp) converted to `YYYY-MM-DD` (UTC); omitted entirely when the value is missing or invalid. Only doSearch returns it. |

The `updated` freshness field exists **only** on doSearch full-text items: search.json
has no modification-timestamp field at all, and index-leg (llms.txt) entries never
carry one, so fused results may mix items with and without the field. That is normal —
the absence of `updated` means the entry came from a backend that does not report
timestamps, not that the document is stale. `updated` is display-only: it takes no
part in fusion scoring, so ranking is unaffected. When an explicitly scoped query
returns nothing but items with no date, the script says so on stderr.

### HTML cleaning rules for `content`

Search snippets arrive with inline HTML markup. Cleaning is done by `_strip_html()`:

1. Strip all tags with `re.sub(r"<[^>]+>", "", text)`
2. Unescape HTML entities (`html.unescape`)
3. Collapse consecutive whitespace into single spaces and trim

## Full-text backend 2: search.json (`intl`, and `cn` + `en`)

- Endpoint constant: `https://www.alibabacloud.com/help/json/search.json`
- The whole URL is a single hard-coded constant on purpose. The site is selected by
  the explicit `website` query parameter, **not** by the host: both
  `www.alibabacloud.com/help/json/search.json` and
  `help.aliyun.com/help/json/search.json` are field-equivalent entry points, and the
  `/help` path prefix is mandatory on both (`https://help.aliyun.com/json/search.json`
  returns 404). Dropping `/help` from the international URL returns **HTTP 200 with a
  ~92 KB WAF interstitial HTML page** instead of JSON, which would silently poison the
  result set — guard S4 catches it, but the constant must never be assembled from a
  host plus a relative path.
- Query parameters: `keywords`, `pageNum` (1-based), `pageSize`, `website`
  (`cn` or `intl`, **case-sensitive**), `language`. `topics` and `category4Id` are
  accepted by the endpoint but have no measurable effect, so they are not sent.
  `bizType` is doSearch-only and is dropped.
- **Zero header dependency.** 24/24 header permutations (bare, browser UA, empty UA,
  with Referer, with the WAF cookie, with Accept, all combined) returned 200 with an
  identical `totalCount`; the response has full CORS headers and no `set-cookie`, no
  `cache-control`, no `etag` and no `last-modified`, so conditional requests are
  impossible and the local TTL cache is the right design. The skill's own User-Agent
  (see the Observability section of `../SKILL.md`) was verified on 2026-09-08 to
  return 200 on all six paths it uses: doSearch, search.json, both master llms.txt
  indexes and both `.md` document bodies.
- Response is JSON. Relevant fields:
  - `data.documents.data[]`: result items
  - `data.documents.totalCount`: total match count
  - `data.documents.pageNum` / `data.documents.pageSize`: the values the server
    actually used (compared against the request — see envelope C)
  - `data.categoryMap.category_id`: a ranked facet list of `{id, name}` objects whose
    length varies with the query (measured 9 entries for `CORS`, 1 for `oss`); used by
    the categoryId discovery mechanism
- Schema difference versus doSearch: doSearch items carry 27 fields, search.json items
  10, and the intersection is only 6 (`categoryId`, `categoryName`, `content`, `scm`,
  `title`, `url`). search.json has **no** `productName`, `seoTitle`, `originTitle`,
  `productCode` or `gmtModifiedOrigin` (hence no `updated`). Its `categoryId` is a
  JSON number (`31815`) where doSearch returns a prefixed string (`"help@@31815"`);
  `_parse_category_id` accepts both. Its `scm` values are identical to doSearch's for
  the same query, and the `totalCount` and URL sets of six measured query pairs were
  identical (Jaccard 1.000, same top hit) — the two endpoints are two gateways in
  front of the same search backend.

### The four HTTP 200 envelopes

search.json answers several malformed requests with HTTP 200 and `success: true`, so
the status code alone proves nothing:

| envelope | shape | triggered by | handling |
|---|---|---|---|
| A — invalid parameter | `success: false`, `code` such as `400`, and a `msg` that can contain a server-side Java stack trace | a non-numeric `categoryId`, an empty `language` | S5: return `None` and degrade. Only the numeric code is logged; the `msg` text is never surfaced to the user. |
| B — normal | `data.documents.data[]` plus `totalCount`, `pageNum`, `pageSize`, and a populated `data.categoryMap` | a valid request | parsed normally |
| C — silent degradation | `data.categoryMap` is `{}`, `data.documents` keeps `pageNum`/`pageSize`/`totalCount: 0` but the **`data` key is missing** | `pageSize > 200`, an over-long `keywords`, `pageNum` of `-1` or `999` | S9: WARN and degrade to the index leg |
| D — wrong-case `website` | an extra top-level `code: 200`, an extra `products` key, no `categoryMap` | `website=INTL` | S9: WARN and degrade to the index leg |

Envelope C is field-identical to a genuine empty result, so it is distinguished by
comparing the echoed `pageSize`/`pageNum` against the values that were requested
(`_detect_degraded_envelope`). A real zero-result answer echoes them unchanged and is
returned as a trustworthy `[]`.

### Request guards on this backend

- **`pageSize` clamped to 2..200 (S7).** `pageSize > 200` degrades silently to
  `totalCount = 0`; `pageSize == 1` makes `totalCount` collapse to 0 whenever the
  query hits a product name (reproduced on `intl`/`en`, `intl`/`zh` and `cn`/`zh`).
  `pageSize = 200` costs 2.5-3.1 s, so the client asks for at most 50 items per page
  (`INTL_SEARCH_PAGESIZE_DEFAULT`) and 200 only for an unlimited `-n 0`.
- **Query length clamped to 60 characters.** An over-long `keywords` returns
  `totalCount = 0` with no error; the truncation leaves a WARN.
- **Empty query rejected without a request.** An empty `keywords` returns the
  whole-corpus hot list (93046 items), which is not a search result.
- **Paging termination must use `totalCount` (S8).** An out-of-range `pageNum` is not
  an error here: `pageNum = 50` answers HTTP 200 with a full page of 10 items that lost
  `categoryId`, `categoryName` and `content`. `len(items) < pageSize` therefore never
  becomes true and would loop forever. The loop condition is
  `pageNum * pageSize >= totalCount`, and shell items missing `url` (or `content`, on
  this backend) are dropped by `_drop_shell_items`. A single page is requested in
  practice: no pagination loop is needed because `pageSize` is honoured.

## Language whitelist and the silent-fallback trap

The `language` parameter of search.json only serves a real corpus for `en` and `zh`
(`SEARCH_LANG_WHITELIST`). Every other value silently falls back to English: 4 queries
x 7 languages = 28 combinations all returned the English `totalCount` and English URL
language segments, and invalid values (`EN`, `xx`, `zh-CN`, `ja-JP`, `tr`) behave the
same way. Only an empty or missing `language` produces `success: false`.

Two guards make that visible instead of silent:

- **S3 (pre-emptive).** For a language outside the whitelist the full-text leg is not
  requested at all; the script goes straight to the index leg and prints an INFO line
  saying why. This is the normal path for `tc`/`ja`/`id`/`pt-br`/`fr`, not a failure.
- **S2 (post-hoc).** Every result URL's language path segment is compared with the
  requested language; a mismatch means the server fell back, and the item is dropped
  with a WARN. A URL with no recognizable language segment is left alone: doSearch
  legitimately returns a small share of `document_detail/{id}.html` URLs that have none
  (2 of 119 measured), and only segments that are known language codes are judged.
- **S1 (post-hoc).** Every result URL's host is compared with the requested site's
  `result_host`; a cross-portal item is dropped with a WARN. Both master indexes
  contain a handful of links to the other portal (2 on `intl`, 6 on `cn`), which would
  otherwise pull the other site's products into the concurrent index scan.

**S13 — the index leg never follows redirects.** llms.txt has its own fallback trap,
and it is worse because it produces no HTTP signal at all: `ko`/`de`/`es`/`th`/`vi`/`tr`
answer `302` to `/help/en/llms.txt` (200 plus a full English index), and
`pt`/`ru`/`it` answer `302` to a target that returns 200 with **zero bytes**.
`urllib.request.urlopen` follows redirects by default, so the English corpus would be
served as if it were the requested language. `_NoRedirectHandler` makes any 3xx surface
as an error marker instead, and `_fetch_index` reports it with a WARN. Redirects are
still followed on `cn`, whose slug space contains legitimate 301s to a canonical slug
and which hosts no language that silently falls back to another one.

`ko` and `de` are **not supported at all**: their master llms.txt is byte-identical to
the English one (same sha256), so there is no corpus to serve. `pt` is not a valid code
either, but it is a very common mistake for `pt-br`, so it is normalized with an INFO
line rather than rejected.

**S12 — query/corpus language consistency.** A CJK query against an `en` corpus is not
an error server-side and produces garbage: one measured Chinese query returned a single
irrelevant hit, another returned a fake whole-corpus match with `totalCount = 13618`.
S2 cannot catch this (the URL language segment is correct), so `search_docs` detects CJK
in the query with a standard-library regex and WARNs that the results will be poor.

## Guard summary

| # | guard | protects against |
|---|---|---|
| S1 | result host must equal the requested site's host | cross-portal contamination |
| S2 | result URL language segment must equal the requested language | silent `language` fallback to English |
| S3 | full-text leg only for `en`/`zh` | same, pre-empted before any request |
| S4 | a non-JSON / HTML body degrades | the WAF interstitial served with HTTP 200 |
| S5 | `success is false` or `code != "200"` degrades | envelope A |
| S7 | `pageSize` clamped to 2..200 | envelopes C and the fake `totalCount = 0` |
| S8 | paging terminates on `totalCount`; shell items dropped | the endless-page trap of an out-of-range `pageNum` |
| S9 | degraded-envelope detection (`data` key missing, empty `categoryMap`, unexpected `products` key) | envelopes C and D |
| S10 | `ALIYUN_HELP_NO_SEARCH_API=1` escape switch kept | drift of an endpoint with no SLA |
| S12 | CJK query against a non-`zh` corpus WARNs | plausible-looking but meaningless results |
| S13 | the index leg never follows redirects | the 302 language fallback with no HTTP signal |

S6 (a mandatory `Referer` assertion) was removed: the new endpoint has no header
dependency, and the site is chosen by the `website` parameter. S11 (hashing a search
response for integrity) is not enabled; if it ever is, `keywords` and `scm` must be
removed from the payload first, since they are the only two fields that jitter.

Two index-leg checks sit outside the S1-S13 numbering because they guard the llms.txt
backend rather than a search response: `_is_index_corpus` rejects a body that is an error
marker, empty, an HTML interstitial, or the international `Sorry, this product does not
have LLMS content yet.` placeholder, so such a body is never cached and never rendered as
an index; and a master index that yields no parsable product entry WARNs instead of
producing a silent empty product list or an empty concurrent scan.

## Product filtering: categoryId server-side filter with local cache

Product-scoped searches (`-p/--product`) prefer **server-side filtering** via the
`categoryId` parameter, which removes the client-side post-filter false negatives
(e.g. legacy `document_detail` URLs that lack a `/{lang}/{product}/` path segment).

### Mapping cache

- Location: `~/.cache/aliyun-help-search/category_map.json` (user home cache only —
  the script never writes files inside the skill directory). The directory is created
  on first write.
- Shape: `{"expires_days": 30, "entries": {"<key>": {"category_id": <int>,
  "written_at": <unix_ts>}}}`
- Key (`_category_cache_key`): the bare product code for `cn` + `zh`, so the built-in
  seed and every cache file written before the scoping stay valid and a default
  invocation is unchanged; `"{site}:{lang}:{product}"` for every other pair. The
  categoryId namespace has the same values on both portals, but the corpus behind one
  id differs per site and per language (id 31815 measured `totalCount` 100 / 130 / 99 /
  132 for cn-zh / cn-en / intl-zh / intl-en), so entries must never be shared.
- Built-in seed: `{"oss": 31815, "functioncompute": 2508973, "ecs": 25365, "rds": 26090,
  "slb": 27537, "vpc": 27706, "cdn": 27099, "ack": 85222, "ram": 28625, "sls": 28958,
  "kms": 28933, "waf": 28515, "polardb": 2249963, "maxcompute": 27797}` (oss verified:
  with the CORS keyword, total drops from 978 to 131 and every result is an OSS
  document; functioncompute verified: wide searches with cold-start and
  function-compute related keywords yielded 8 votes for 2508973 among
  `/zh/functioncompute/` items, and a precise query with that id returned only Function
  Compute documents). The twelve additional entries were verified on 2026-08-28: wide
  queries collected >=7 product-needle votes per id, and precise queries with each id
  returned 10/10 pure product documents. The same ids were re-verified on the
  international portal on 2026-09-08 (oss 31815, ecs 25365, cdn 27099,
  functioncompute 2508973, slb 27537, ack 85222, security-center 28498). Seed entries
  are bare integers; the read path accepts them directly and exempts them from the TTL
  (no `written_at`, permanently valid). Bare-integer entries are never written to the
  cache file — `_save_category_cache` filters them out so the on-disk shape stays
  `{"category_id": int, "written_at": ts}`.
- TTL: 30 days per entry; expired entries are rediscovered on next use. Cache read
  failures silently fall back to the seed.

### Discovery mechanism

When a product-scoped query has no valid cached categoryId:

1. On the search.json backend only, one **categoryMap facet probe** is issued first
   (`keywords={product}`, `pageSize=2`, the smallest legal page). The top facet entry
   `data.categoryMap.category_id[0]` gives an `{id, name}` pair, and the id is accepted
   only after a product-name gate confirms it (`_catmap_name_matches`: slug equality,
   token overlap, or the initials of the facet name — which is what makes `alb` match
   `Server Load Balancer` and `sas` match `Security Center`). A rejected or missing
   facet falls through to step 2 without a WARN, since step 2 is the historical path.
2. One wide query is issued (no `categoryId`, `pageSize=50`), keeping the raw result
   items including their `categoryId` field.
3. Items whose URL contains the site-scoped product needle (`/{lang}/{product}/` on
   `cn`, `/help/{lang}/{product}/` on `intl`) are collected, their categoryId values
   normalized (the `help@@` prefix is stripped), and the mode is taken.
4. If the mode has **at least 2 votes**, a precise query is re-issued with the
   discovered `categoryId`; only when that precise query succeeds is the id written to
   the cache (a failing precise query is never cached), and it is the full-text leg
   result for this invocation.
5. If the categoryId cannot be discovered (not enough votes, or the wide query failed),
   this invocation falls back to client-side URL post-filtering on the wide results
   (`pageSize=50`, raised from the old 20 to reduce false negatives), and a WARN line
   is logged.

When a valid cached categoryId exists, the backend is called with `categoryId` and
`pageSize=50`, and its results are **trusted as-is** (no URL post-filter). If the
precise query fails, the flow degrades to the wide query + post-filter path described
above; all transitions are logged as INFO/WARN on stderr (cache hit / facet discovery /
mode-vote discovery / fallback are all traceable).

Note: the separate `doSearchHelpDocFilters` endpoint cannot be used to bulk-fetch the
product_code to categoryId mapping (it currently returns `success:false` / `code:001`),
hence the discovery-from-results approach.

### Pagination on the precise (categoryId) path

There is no client-side pagination any more. The endpoint's own `pageSize`/`pageNo`
pairing was never honoured, so asking for a bigger page with a bigger `limit` replaced it:
the request is a single call sized 2..200, and the historical loop with its
`SEARCH_PAGE_CAP = 10` / `SEARCH_MAX_PAGES = 3` caps (which made 30 items the hard ceiling
on the precise path) was deleted along with the constants (F1, 2026-09-09).

The wide-query path (no `categoryId`) and unscoped searches (no `-p`) always issue a
single doSearch request, so without `-p` a limit of 20 yields at most 10 results in
practice. The search.json backend honours `pageSize` and needs no loop: one request
returns the requested page, and an INFO line reports how many documents matched in total
when the returned page is shorter than that.

### Empty-result semantics with -p

With `-p`, an empty full-text leg is **no longer final**: the index leg still runs and
its hits are surfaced (this is exactly the false-negative case fusion is meant to fix).
"Not found" plus the WebSearch suggestion is printed only when **both** legs return
nothing, and the message names the portal and language that were searched. As an
operational rule, empty results with `-p` should also be rechecked via `list-products`
run with the same `--site`/`--lang` (the product code may be wrong, or the product may
not exist on that portal) and with a retry without the product filter. There is **no
cross-site fallback**: an empty `intl` result stays empty and exits `1`.

## Multi-leg fusion (product-scoped search)

With `-p` and the escape switch unset, both legs always run and are fused:

- **Full-text leg**: doSearch or search.json with categoryId server-side filtering (see
  above), or nothing at all when the language is outside the whitelist.
- **Index leg**: substring scan of the product's `llms.txt` index (title + summary), the
  same logic used by the degraded path.

Fusion rules (deterministic, no randomness):

1. URL normalization: drop the query/fragment part and the `.md` suffix, then
   deduplicate across legs.
2. Scoring: each full-text hit earns a rank-based base score (`N - rank`, decreasing
   with rank); each index hit earns a share of a bonus equal to the full-text hit count,
   weighted by its own index score: `bonus x (0.5 + 0.5 x min(1, score / 8.0))` where `8.0`
   is `_INDEX_FUSION_FULL_SCORE`. Entries hit by **both** legs therefore score highest and are
   tagged `source=both`.
3. Ordering: score descending; ties keep the full-text leg's original order, and
   index-only entries sort after all full-text entries in index order.

The weighting is why an unscoped weak index match no longer dominates the visible window, and
the `0.5` floor is why a real index hit can never be buried by it: the index leg compares title
and summary lexically and cannot see that "rule count" and "limits and quotas" ask the same
thing. Measured 2026-09-09 over eight product-scoped queries against the previous implementation:
the returned set is unchanged for five of them, and across all twenty-five swapped entries every
dropped one came from the index leg while every added one came from the full-text leg - the fusion
never evicts a document the search backend itself ranked (mean set churn 2.2 of 20 entries).

A one-line statistic is logged to stderr whenever fusion is performed, e.g.
`INFO: fused: 10 fulltext + 36 index -> 36 unique`. (When the index leg faults while the
full-text leg succeeded, the full-text results are still surfaced with a WARN instead,
and no fusion statistic line is emitted.)

Path matrix for `search`:

| Mode | Full-text leg | Index leg | Output |
|---|---|---|---|
| No `-p` | Yes (one global query) | Only if the full-text leg returns `None` | Full-text results as-is |
| `-p` (normal) | Yes (categoryId or post-filter fallback) | Always (on leg fault, output degrades to full-text only with a WARN) | Fused |
| `-p`, full-text leg faulted (`None`) | — | Yes | Index results only |
| Language outside the whitelist (`tc`/`ja`/`id`/`pt-br`/`fr`) | Skipped with an INFO line | Yes, primary path | Index results only |
| Escape switch set | Skipped | Yes | Index results only |

The index leg scores title and summary instead of returning catalogue order: CJK queries are
matched on overlapping character bigrams, Latin queries on words, with a coverage floor (see
"Index-leg ranking (F3)"). It carries no synonym table and no semantic model, so it still recalls
nothing for error codes, parameter names or quota numbers that never appear in a heading - 4 of 8
measured query classes returned zero hits before scoring was added and those classes stay outside
its reach. For the languages that have no full-text leg this is the normal capability boundary
rather than a degradation, and the answer should say so.

The summaries the index leg matches on are also less reliable on the international
portal: comparing each entry's summary with the body of the document it links (token
overlap, 14 sampled `intl`/`en` SLB entries versus the same 14 lines of the `cn`/`zh`
index, measured 2026-09-08) averages **0.64** on `intl` against **0.96** on `cn`, and two
international lines carry a summary copied from an unrelated document (the "Product
Overview" line describes Grafana data sources, "Announcements and Updates" describes an
iSCSI gateway). Summary-based recall is therefore weaker for international queries than
the title alone would suggest; when an `intl` query returns nothing, rephrase on the
title terms rather than assuming the summary vocabulary is accurate.

## Fallback backend: llms.txt index

When the full-text leg returns `None` (or is skipped), the command scans the `llms.txt`
indexes published per site and language:

| | master index | product index |
|---|---|---|
| `cn` | `https://help.aliyun.com/{lang}/llms.txt` | `https://help.aliyun.com/{lang}/{product}/llms.txt` |
| `intl` | `https://www.alibabacloud.com/help/{lang}/llms.txt` | `https://www.alibabacloud.com/help/{lang}/{product}/llms.txt` |

The master index lists every product with its own index; the concurrent unscoped scan
walks that list with 8 workers and reports progress every 100 indexes (N2/N7). Measured 2026-09-08, products are listed under three
path shapes and all three resolve to a scannable product code:

| shape | example | `cn`/`zh` count | `intl`/`en` count |
|---|---|---|---|
| `/{lang}/{slug}/llms.txt` | `/zh/oss/llms.txt` | 218 | 226 |
| `/{lang}/product/{id}.html/llms.txt` | `/zh/product/435019.html/llms.txt` | 64 | 2 |
| `/{lang}/document_detail/{id}.html/llms.txt` | `/zh/document_detail/2391397.html/llms.txt` | 178 | 0 |

That is 460 product URLs on `cn`/`zh` resolving to **412 distinct** products (the master
repeats a product across sections; the scan de-duplicates, otherwise 48 indexes would be
fetched twice per run), and 228 URLs / **215 distinct** products on `intl`/`en`. Before
the third shape was handled, 178 of 460 `cn`/`zh` products — 38.7% of the catalog, many of
them substantial (that OpenSearch index alone carries 377 documents) — were silently absent
from every unscoped scan. Their extracted code (`document_detail/{id}.html`) round-trips
back into the same URL, and `_llms_cache_path()` escapes the `/` so the cache file stays a
single flat name.

The only master entry with no resolvable code is the `cn`/`zh` Apsara Stack entry (its
master-index title is the Chinese product name), whose link is
`https://help.aliyun.com/apsara/enterprise.html/llms.txt` — outside the `/{lang}/` tree and
answering HTTP 302 (verified 2026-09-08), so it is not addressable by a `(site, language)`
scope and is reported as `(unknown)` instead of being scanned. Cross-portal links inside a
master index are filtered out (guard S1: the `intl`/`en` master carries 7 of them, all
language/portal navigation lines), and the "available sites and languages" preamble block of
each master index is not a product entry and is skipped.

Entry shape: `- [title](url)[ optional ": summary"]`. The summary part is **optional** and
the parsers must not require it: on `cn`/`zh` 6 of 461 master lines and 492 of 4359 OSS
product lines (11.3%) and 198 of 1568 ECS lines (12.6%) carry none, and a required summary
group made every one of them invisible to `list-docs` and to both index-leg scanners. Most
summary-less lines are navigation nodes rather than leaf documents, but they are real
catalog entries and some of them are the only path to a topic. `re.findall()` yields `''`
for the absent group while `re.match()` yields `None`, so a caller that reads group 3 from
`match()` must coerce it.

`list-products` and the unscoped scan now agree by construction (both parse the same
optional-summary entry shape and resolve codes through one helper); on 2026-09-08 they
report 461 vs 460 entries on `cn`/`zh` and 228 vs 228 on `intl`/`en`, the single missing
line being the `apsara` shape described above.

A master index that yields **no** parsable product entry is never treated as a real "this
portal lists no product" answer — both portals list 200+ of them. `list-products` WARNs and
exits `1`; the index leg WARNs that the scan has nothing to walk, so a degraded empty result
is never reported as if it were a trustworthy no-match.

Each supported language has a real, distinct corpus, verified by its localized first-line
title: the `en` master opens with the English product-suite heading, while `zh`, `tc`,
`ja`, `id` and `pt-br` each open with the same heading translated into that language
(simplified Chinese, traditional Chinese, Japanese, Indonesian and Brazilian Portuguese
respectively). `fr` is a **grey release**: its master index is far smaller than the
others, its first line is still the English heading and its entry descriptions are empty,
even though its per-product indexes look complete. Treat `fr` as experimental.

### Local llms.txt cache

A product's llms.txt is about 1 MB and is fetched on every product-scoped search,
`list-docs`, and `read-product` invocation, so it is cached locally:

- Location: `~/.cache/aliyun-help-search/llms/{site}/{lang}/{product}.txt` (user home
  cache only, never inside the skill directory). Written atomically via a temp file plus
  `os.replace`. Site and language are directories on purpose: the same slug on the two
  portals, or in two languages, is a different corpus, and a flat key would silently
  serve one portal's index for the other for the whole 3-day TTL.
- Files written before the scoping live one level up, are never read again, and are left
  to expire naturally — no migration and no cleanup, by design.
- TTL: 3 days (based on file mtime). Expired entries, missing files, and read failures
  silently fall back to the network and refresh the cache.
- **A body that is not a real index is never cached** (`_is_index_corpus`). A dead product
  slug answers **HTTP 200** in three different shapes, none of which is a corpus:

  | portal | body for a dead slug | size |
  |---|---|---|
  | `cn` | empty | 0 B |
  | `intl` | `Sorry, this product does not have LLMS content yet.` | 51 B |
  | `intl` (intermittent, under rate limiting) | the `bxpunish` WAF interstitial HTML page | ~92 KB |

  The last row corrects an earlier assumption that the WAF page only appears on `www`
  root paths: `https://www.alibabacloud.com/help/en/ahas/llms.txt` was measured serving it
  with HTTP 200 and `content-sn: 2` during a rate-limited window, then serving the 51-byte
  placeholder for the same URL minutes later. Caching any of the three would pin a slug as
  dead for the whole TTL, and caching the WAF page would later serve an interstitial as if
  it were an index. All three are recognised and reported as "this product has no
  documentation on that site", with exit `1`.
- Shared by `_scan_product_index`, `list_docs`, and `read-product` through a single read
  layer (`_get_llms_text`). Cache hits leave an INFO line on stderr in `list-docs` /
  `read-product`; the index leg stays silent. A missing or empty index reports "index
  does not exist" plus a WARN naming the portal and language.

Known limitations of the index leg (printed to stderr when it is used):

- Substring match on title + summary only — no tokenization, no synonyms, no ranking
- A single-product query fetches one index (fast); an unscoped query scans every product
  index concurrently (10-20 seconds) and bypasses the cache, re-downloading roughly
  15-25 MB per run, so repeating it does not get faster
- The master index only exposes products whose URL carries a product slug; the
  `document_detail/{id}.html` form (about 37% of the entries on `cn`/`zh`) is skipped by
  the scan, while the full-text leg is not limited by URL shape

## Local degradation on rate limit / outage (stale cache fallback)

The llms.txt read layer (`_get_llms_text`) has a third tier beyond "fresh cache / network":

1. Fresh cache (within the 3-day TTL) — returned immediately.
2. Network fetch — on success the cache is atomically refreshed.
3. **Stale cache fallback**: when the network fetch fails (rate limit, outage, any
   `[HTTP ...]`/`[Error]` marker) but an expired local cache exists for that
   (site, lang, product) triple, the expired content is served instead of nothing, with
   a WARN noting the results may lag the live docs. Empty stale files are never served.

This keeps product-scoped search, `list-docs`, and `read-product` functional during
backend saturation as long as that exact scope was queried at least once within recent
history. The full-text leg's own degradation (to the index leg) then combines with this
layer: under a full rate-limit event, search degrades to "index leg over stale local
cache".

## Degradation hints on api-* failure exits

The `api-products` / `api-list` / `api-info` commands depend on the single
`api.aliyun.com` metadata endpoint (no backup backend), which is site-independent — that
is why they take no `--site`/`--lang`. Every failure exit (product not resolved, catalog
fetch failed, single-API metadata invalid) prints a fallback hint on stderr: verify codes
with `api-products`, or fall back to help-doc search
(`search "<error-code-or-keyword>" -p <product>`). Hint only; the commands' behavior is
unchanged. The international portal's error-code corpus is markedly thinner than the
`cn` one (2 hits for a measured code with a categoryId filter), so for exhaustive
error-code contracts `api-info <product> <ApiName>` remains the authoritative source.

## Degradation trigger matrix

`search_api()` returns `None` (triggering degradation) on the conditions below. Every
degradation is logged as a `WARN` line on stderr so the downgrade always leaves a trace.
An empty result list (`totalCount=0` / empty items) is a **trustworthy "no results"**
conclusion and is returned as `[]`, never degraded. Note that with `-p` the fused
pipeline still runs the index leg on an empty full-text list (see above), while an
unscoped search keeps the classic "empty list -> not found" behavior.

| Condition | Backend | Retry? | Action |
|---|---|---|---|
| Network exception / timeout | both | Yes, 1 retry with the same timeout | Return `None` if the retry also fails |
| HTTP 4xx / 5xx | both | No | Return `None` immediately |
| HTTP 200 but the response is HTML | both | No | Return `None` (S4; WARN notes "suspected rate-limit or redesign") |
| HTTP 200 but non-JSON / parse failure | both | No | Return `None` (same WARN note) |
| JSON `success` == false | both | No | Return `None` (S5, envelope A; only the numeric code is logged) |
| JSON `code` != "200" | both | No | Return `None` |
| `documents` without a `data` key, empty `categoryMap`, or an unexpected `products` key | search.json | No | Return `None` (S9, envelopes C and D) |
| The echoed `pageSize`/`pageNum` differs from the request | search.json | No | Return `None` (S9) |
| Items whose host or language segment does not match the requested scope | both | — | Dropped individually with a WARN (S1/S2); the rest is kept |
| Items missing `url` (or `content` on search.json) | both | — | Dropped silently as shells (S8) |
| Items empty / `totalCount` == 0 | both | — | Return `[]` (no degradation) |

## Timeout and retry parameters

| Parameter | Value | Applies to |
|---|---|---|
| `SEARCH_TIMEOUT` | 8 seconds | doSearch and search.json requests (both attempts) |
| `TIMEOUT` | 15 seconds | `cn` llms.txt / `.md` / metadata endpoints |
| `SITES["intl"]["index_timeout"]` | 20 seconds | `intl` llms.txt and `.md` (its indexes are 4-6 times slower to serve: ja/oss measured avg 5.18 s, max 5.53 s) |
| Network-error retries | 1 | full-text leg; the `intl` index leg also retries once after 0.5 s. HTTP errors are never retried. |

The ~47 s / ~31 s figures quoted for a `-p` search are a **worst-case timeout
accumulation upper bound**, not a measured scan duration: with a cache miss up to three
sequential network requests can each hit their timeout — wide query (2x8 s) then precise
query (2x8 s) then index leg (15 s) — which adds up to about 47 seconds; with a cache hit
the wide query is skipped, leaving about 31 seconds. Real-world latency is far lower:
the measured median for a `-p` search is about 1.1 s, a single global query without `-p`
about 1.1 s, and the concurrent all-product index scan 7-9 s (about 15-25 MB re-downloaded
per run because that path bypasses the cache). With `-p` and a hot cache, the index leg
alone is about 0.20 s versus about 1.12 s for the default dual-leg run.

## Exit codes

| code | meaning |
|---|---|
| `0` | success, including a degraded leg that still produced results |
| `1` | degraded and zero results, or the requested product has no documentation on that site, or a document body could not be read |
| `2` | unusable: an invalid site/language combination (no request issued), or every backend failed |

The entry point is `sys.exit(main())`; before the i18n work the script had no exit-code
mechanism at all and always exited `0`. The success path still returns `0`, so existing
automated checks are unaffected.

## Escape switch

Set `ALIYUN_HELP_NO_SEARCH_API=1` to skip the full-text backend entirely and go straight
to the llms.txt index leg (no fusion, no categoryId cache access):

```bash
ALIYUN_HELP_NO_SEARCH_API=1 python3 scripts/aliyun_help.py search "snapshot" -p ecs
```

Use this when the primary backend is misbehaving (rate limiting, schema changes) and you
need deterministic, if lower-quality, results.

## Result source tagging

With `--json`, every result carries a `source` field: `fulltext` for full-text-leg-only
hits, `index` for llms.txt-only hits, and `both` for entries found by both legs in a
fused product-scoped search. This makes it explicit which backend produced each hit.
When the scope was requested explicitly, each record is additionally annotated with the
`site` and `lang` it came from, and the same is stated on stderr; a default
(`cn` + `zh`) invocation prints no such annotation, so its output is unchanged.

## Built-in self-test

`ALIYUN_HELP_SELFTEST=1` runs a private `_selftest()` inside the script — no extra
subcommand, no extra file, and no network access:

```bash
ALIYUN_HELP_SELFTEST=1 python3 scripts/aliyun_help.py
```

It exercises every scope-related pure helper with normal, boundary and invalid inputs:
site dictionary lookup and URL construction, needle construction, cache path and
categoryId cache key construction, `pageSize` and query clamping, backend routing and the
language whitelist, language normalization and site inference, host and language-segment
extraction, site-purity validation, shell-item dropping, degraded-envelope detection (all
four envelopes plus a genuine empty result), item and total extraction, `help@@` prefix
stripping, CJK detection, scope annotation, the site-scoped document and product-code
regexes (compared literally against the pre-i18n patterns so the `cn` + `zh` path cannot
drift), the categoryMap name gate, categoryId parsing and discovery, URL post-filtering,
the no-redirect handler, `_readable_title` and both backends' item parsers. Guard traces
that the assertions expect to see are captured from stderr and echoed back with a
`trace|` prefix. Output is one summary line, the traces, any `FAIL:` detail, then
`SELFTEST RESULT: PASS` or `FAIL`; the exit code is `0` on success and `1` on failure.

## Result caching, budgets, ranking and trace markers (measured 2026-09-09)

### Full-text result cache (N8)

An identical full-text request is reused for `SEARCH_CACHE_TTL_SECONDS = 600` from
`~/.cache/aliyun-help-search/search/`. The key is a SHA-256 over the *request*
(`site|lang|backend|every parameter in sorted order`), never over the response: across six
identical search.json requests only 6 of 149 leaf fields varied, all inside `keywords.now`
and the `scm` trace block, so a response-based key would never hit. Only a result set that
passed every legality guard is stored, an empty list is a valid stored value, and a hit is
always traced with `INFO[result-cache]`. `--no-result-cache` bypasses the cache.

### Transport budgets (N2, N4)

`fetch_response()` is the shared request primitive: it returns the body plus
`{status, retry_after, truncated}`, retries a network failure, a 429 or a 5xx once with
exponential backoff and jitter (honouring `Retry-After`), treats every other 4xx as final,
and caps the body. Caps leave at least double headroom over the largest legitimate payload:
index 8 MB (largest measured 1.49 MB), search response 2 MB (419 KB), document body 4 MB
(119 KB); the llms.txt cache has a 300 MB budget with mtime-based eviction.

### Index-leg ranking (F3)

The index leg scores entries instead of returning catalogue order: an exact full-query title
hit (`4.0`) beats title bigram coverage (`3.0 x ratio`), which beats summary coverage
(`1.5 x ratio`), plus `0.5` for carrying a summary. A partial match must cover at least
`_INDEX_MIN_COVERAGE = 0.34` of the query tokens: without that floor one common bigram
matched 3881 of the 4359 OSS entries. CJK queries are matched on overlapping character
bigrams, because the previous whole-string test recalled nothing for a Chinese query that is
phrased differently from the titles (two four-to-seven-character Chinese queries that scored
zero before now score 62 and 2 entries on the OSS index, with a relevant first hit). Record
shape is unchanged; only the order is.

**Cross-product ordering (2026-09-09 increment).** The scores used to be dropped at the product
boundary, so an unscoped scan (`search` without `-p`) concatenated per-product hits in
master-index order and the caller truncated that list. A weak bigram match inside a product
listed early therefore outranked an exact title hit inside a product listed late. `_merge_scored_scans`
now pools the scored hits of all scanned products and sorts them once, stably, so equal scores
still keep catalogue order. Before and after, for the same Chinese query meaning "server side
encryption": the old head of the list was `pai` and `model-studio` pages that merely contain the
substring for "server-side" (one of them an endpoint-list API page), the new head is the
object-storage encryption document family; all twenty visible entries changed and every one of them
is on topic. For `how is cross-origin access configured` three noise entries (a certificate page,
an Elasticsearch parameter page, a compute-settings page) left the top ten.

The same scores now also feed the fusion weight described in "Multi-leg fusion", so an index hit is
no longer treated as equally strong whatever it matched on.

### categoryId discovery chain (F4)

`categoryMap` facet with the name gate, then the wide-search mode vote (>= 2 votes), then the
product landing page `nodeId`, then the client-side URL post-filter. The landing value is only
a candidate: measured over the 14 seeded China-site products, `nodeId` equals the endpoint
`categoryId` for 9 and differs for 5 (`ack` 126295 vs 85222, `polardb` 58609 vs 2249963,
`rds` 95798 vs 26090, `slb` 196881 vs 27537, `waf` 2402328 vs 28515), so the assumption that
`nodeId` is universally the same value is only partly true; it is never cached before a
categoryId-filtered query has returned results.

### Trace markers (N10)

Degradations print `WARN[kind]: ...` from the set `rate-limit`, `waf-block`, `schema-drift`,
`site-cross`, `lang-fallback`, `query-clamp`, `query-lang`, `oversize`,
`cache-write`, `no-corpus`, `unreachable`, `leg-fallback` (12 kinds) - 48 tagged traces across the
modules on 2026-09-09 (schema-drift 10, leg-fallback 7, no-corpus 6, site-cross 5, then
rate-limit / oversize / lang-fallback / cache-write at 3 each, unreachable and query-clamp
at 2, waf-block and query-lang at 1) - plus the information lines `INFO[result-cache]`
and `INFO[query-translate]`. Reusing an expired local index because the live index returned no
usable corpus is one of the `no-corpus` traces, not a separate kind; its message names the stale
cache being reused, so the attribution is still unambiguous. Marking is attribution only - no
marker changes an outcome, and each one still degrades rather than fails.

### Ranking jitter (N9)

Tied scores are broken by catalogue position, and the endpoints' own ranking is not stable to
the second: two identical requests about ten minutes apart were observed swapping the top two
items once while the top-10 set itself stayed identical (Jaccard 1.000 on both portals). The
short-TTL result cache (N8) reduces how often a repeated question can land in a different
ordering window. Do not describe an item as "the most relevant document"; describe it as a top
match of this run, and re-query with `--no-result-cache` when the ordering itself matters.

### Contract probe (N14)

`ALIYUN_HELP_PROBE=1 python3 scripts/aliyun_help.py` re-checks the undocumented contracts (the
out-of-range `pageSize` envelope, both master indexes, the `help-portal-fe` bundle version, the
metadata leg) and exits non-zero on drift; measured 2026-09-09 all five checks pass with
bundle `0.12.63`. It never runs on a normal invocation and must not be asserted on in
evaluation cases.

### Query vocabulary gate (F6)

A Chinese query aimed at a non-Chinese corpus is first mapped through a built-in table of
high-confidence documentation terms (`INFO[query-translate]`). When nothing maps, the full-text
leg is dropped rather than sent, because the endpoint accepts the mismatch without an error and
answers with unrelated hits or a fake whole-corpus match.
