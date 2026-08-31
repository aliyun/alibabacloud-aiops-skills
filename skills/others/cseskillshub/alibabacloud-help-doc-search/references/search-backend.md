# Search Backend Architecture

The `search` subcommand of `scripts/aliyun_help.py` uses a dual-backend design: a
relevance-ranked full-text backend as the primary path, and a deterministic local-index
leg that guarantees degraded-but-functional search when the primary is unavailable.
When a product filter (`-p`) is given and the escape switch is not set, the two legs
run together and their results are fused (see "Multi-leg fusion" below).

## Primary backend: doSearch full-text search

- Endpoint: `GET https://t.aliyun.com/abs/search/doSearch`
- Query parameters: `queryWord` (URL-encoded keyword), `pageSize` (20 for unscoped
  queries, 50 for product-scoped and categoryId queries; the server effectively caps
  `data.info` at 10 items per page), `pageNo=1`, `bizType=help`, and optionally
  `categoryId` (numeric, server-side category filter; see below)
- Response is JSON. Relevant fields:
  - `data.info[]`: result items, each containing `title`, `url`, `content`
    (HTML snippet), `productName`, `categoryName`, `gmtModifiedOrigin`, and
    `categoryId` (a prefixed string such as `help@@31815`; the numeric part is the
    value accepted by the `categoryId` request parameter)
  - `data.totalCount`: total match count
- This is the same backend that powers the public help-center search box. It is an
  undocumented internal endpoint with **no SLA**: the response schema, rate limits, and
  even availability may change without notice. The fallback backend exists precisely
  for this reason.

### Field mapping

| Output field | Source |
|---|---|
| `title` | `title`, truncated at the first `" \| "` separator (drops the trailing product-name suffix); pure numeric titles (`^\d{4}-\d{8}$`, typically announcement-style documents) fall back to the first non-empty, non-numeric value among `seoTitle` / `originTitle` / `categoryName`, keeping the original title when no fallback exists |
| `url` | `url`, passed through unchanged |
| `desc` | `content` after HTML cleaning, truncated to 120 characters |
| `product` | `productName`; if empty, extracted from the URL via regex `/zh/([^/]+)/` |
| `updated` | `gmtModifiedOrigin` (millisecond timestamp) converted to `YYYY-MM-DD` (UTC); omitted entirely when the value is missing or invalid |

The `updated` freshness field only exists on full-text leg items: index-leg
(llms.txt) entries carry no update timestamp, so fused results may mix items with
and without the field. That is normal — the absence of `updated` simply means the
entry was surfaced by the index leg (or the backend did not report a timestamp),
not that the document is stale.

### HTML cleaning rules for `content`

Search snippets arrive with inline HTML markup. Cleaning is done by `_strip_html()`:

1. Strip all tags with `re.sub(r"<[^>]+>", "", text)`
2. Unescape HTML entities (`html.unescape`)
3. Collapse consecutive whitespace into single spaces and trim

## Product filtering: categoryId server-side filter with local cache

Product-scoped searches (`-p/--product`) prefer **server-side filtering** via the
`categoryId` parameter, which removes the client-side post-filter false negatives
(e.g. legacy `document_detail` URLs that lack the `/zh/{product}/` path segment).

### Mapping cache

- Location: `~/.cache/aliyun-help-search/category_map.json` (user home cache only —
  the script never writes files inside the skill directory). The directory is created
  on first write.
- Shape: `{"expires_days": 30, "entries": {"<product_code>": {"category_id": <int>,
  "written_at": <unix_ts>}}}`
- Built-in seed: `{"oss": 31815, "functioncompute": 2508973, "ecs": 25365, "rds": 26090,
  "slb": 27537, "vpc": 27706, "cdn": 27099, "ack": 85222, "ram": 28625, "sls": 28958,
  "kms": 28933, "waf": 28515, "polardb": 2249963, "maxcompute": 27797}` (oss verified:
  with the CORS keyword, total drops from 978 to 131 and every result is an OSS
  document; functioncompute verified: wide searches with cold-start and
  function-compute related Chinese keywords yielded 8 votes for 2508973 among
  `/zh/functioncompute/` items, and a
  precise query with that id returned only Function Compute documents). The twelve
  additional entries were verified on 2026-08-28: wide queries collected >=7
  `/zh/{product}/` votes per id, and precise queries with each id returned 10/10 pure
  product documents. Seed
  entries are bare integers; the read path accepts them directly and exempts
  them from the TTL
  (no `written_at`, permanently valid). Bare-integer entries are never written to
  the cache file — `_save_category_cache` filters them out so the on-disk shape
  stays `{"category_id": int, "written_at": ts}`.
- TTL: 30 days per entry; expired entries are rediscovered on next use. Cache read
  failures silently fall back to the seed.

### Discovery mechanism

When a product-scoped query has no valid cached categoryId:

1. One wide query is issued (no `categoryId`, `pageSize=50`), keeping the raw result
   items including their `categoryId` field.
2. Items whose URL contains `/zh/{product}/` are collected, their categoryId values
   normalized (the `help@@` prefix is stripped), and the mode is taken.
3. If the mode has **at least 2 votes**, a precise query is re-issued with the
   discovered `categoryId`; only when that precise query succeeds is the id
   written to the cache (a failing precise query is never cached), and it is
   the full-text leg result for this invocation.
4. If the categoryId cannot be discovered (not enough votes, or the wide query
   failed), this invocation falls back to client-side URL post-filtering on the wide
   results (`pageSize=50`, raised from the old 20 to reduce false negatives), and a
   WARN line is logged.

When a valid cached categoryId exists, doSearch is called with `categoryId` and
`pageSize=50`, and its results are **trusted as-is** (no URL post-filter). If the
precise query fails, the flow degrades to the wide query + post-filter path described
above; all transitions are logged as INFO/WARN on stderr (cache hit / discovery /
fallback are all traceable).

### Pagination on the precise (categoryId) path

The server effectively returns at most 10 items per page regardless of `pageSize`,
but `pageNo` paging works. Pagination is therefore enabled **only** on the precise
query path (a `categoryId` is present) and only when the requested limit exceeds
10 (or is unlimited): pages are fetched sequentially up to `ceil(limit/10)`,
capped at 3 pages (i.e. at most 30 items), each request reusing `SEARCH_TIMEOUT`
and its single network retry. A failed page fetch keeps the pages already fetched
(WARN logged). Pagination is traceable: an INFO line on stderr records the number
of page requests issued and the cumulative item count whenever more than one page
is fetched.

The wide-query path (no `categoryId`) and unscoped searches (no `-p`) always issue
a single request, so without `-p` a limit of 20 yields at most 10 results in
practice.

Note: the separate `doSearchHelpDocFilters` endpoint cannot be used to bulk-fetch the
product_code to categoryId mapping (it currently returns `success:false` / `code:001`),
hence the discovery-from-results approach.

### Empty-result semantics with -p

With `-p`, an empty full-text leg is **no longer final**: the index leg still runs and
its hits are surfaced (this is exactly the false-negative case fusion is meant to
fix). "Not found" + WebSearch suggestion is printed only when **both** legs return
nothing. As an operational rule, empty results with `-p` should also be rechecked via
`list-products` (the product code may be wrong) and with a retry without the product
filter.

## Multi-leg fusion (product-scoped search)

With `-p` and the escape switch unset, both legs always run and are fused:

- **Full-text leg**: doSearch with categoryId server-side filtering (see above).
- **Index leg**: substring scan of the product's `llms.txt` index (title + summary),
  the same logic used by the degraded path.

Fusion rules (deterministic, no randomness):

1. URL normalization: drop the query/fragment part and the `.md` suffix, then
   deduplicate across legs.
2. Scoring: each full-text hit earns a rank-based base score (`N - rank`, decreasing
   with rank); each index hit earns a fixed bonus equal to the full-text hit count.
   Entries hit by **both** legs therefore score highest and are tagged `source=both`.
3. Ordering: score descending; ties keep the full-text leg's original order, and
   index-only entries sort after all full-text entries in index order.

A one-line statistic is logged to stderr whenever fusion is performed, e.g.
`INFO: fused: 10 fulltext + 36 index -> 36 unique`. (When the index leg faults
while the full-text leg succeeded, the full-text results are still surfaced with
a WARN instead, and no fusion statistic line is emitted.)

Path matrix for `search`:

| Mode | Full-text leg | Index leg | Output |
|---|---|---|---|
| No `-p` | Yes | Only if full-text leg returns `None` | Full-text results as-is |
| `-p` (normal) | Yes (categoryId or post-filter fallback) | Always (on leg fault, output degrades to full-text only with a WARN) | Fused |
| `-p`, full-text leg faulted (`None`) | — | Yes | Index results only |
| Escape switch set | Skipped | Yes | Index results only |

## Fallback backend: llms.txt index

When the primary backend returns `None`, the command falls back to scanning the
`llms.txt` indexes published at `https://help.aliyun.com/zh/{product}/llms.txt`.

### Local llms.txt cache

A product's llms.txt is about 1MB and is fetched on every product-scoped search,
`list-docs`, and `read-product` invocation, so it is cached locally:

- Location: `~/.cache/aliyun-help-search/llms/{product}.txt` (user home cache only,
  never inside the skill directory). Written atomically via a temp file plus
  `os.replace`.
- TTL: 3 days (based on file mtime). Expired entries, missing files, and read
  failures silently fall back to the network and refresh the cache; fetch errors
  (`[HTTP ...]` / `[Error] ...` markers) are never cached.
- Shared by `_scan_product_index`, `list_docs`, and `read-product` through a single
  read layer (`_get_llms_text`). Cache hits leave an INFO line on stderr in
  `list-docs` / `read-product`; the index leg stays silent. Existing fault/empty
  semantics are unchanged: a missing or empty index still reports "index does not
  exist" exactly as before.

Known limitations of the fallback leg (printed to stderr when it is used):

- Substring match on title + summary only — no tokenization, no synonyms, no ranking
- A single-product query fetches one index (fast); an unscoped query scans 270+ product
  indexes concurrently (10–20 seconds)

## Local degradation on rate limit / outage (stale cache fallback)

The llms.txt read layer (`_get_llms_text`) has a third tier beyond "fresh cache / network":

1. Fresh cache (within the 3-day TTL) — returned immediately.
2. Network fetch — on success the cache is atomically refreshed.
3. **Stale cache fallback**: when the network fetch fails (rate limit, outage, any
   `[HTTP ...]`/`[Error]` marker) but an expired local cache exists for that product,
   the expired content is served instead of nothing, with a WARN noting the results
   may lag the live docs. Empty stale files are never served.

This keeps product-scoped search, `list-docs`, and `read-product` functional during
backend saturation as long as the product was queried at least once within recent
history. The doSearch leg's own degradation (to the index leg) then combines with
this layer: under a full rate-limit event, search degrades to
"index leg over stale local cache".

## Degradation hints on api-* failure exits

The `api-products` / `api-list` / `api-info` commands depend on the single
`api.aliyun.com` metadata endpoint (no backup backend). Every failure exit
(product not resolved, catalog fetch failed, single-API metadata invalid) prints a
fallback hint on stderr: verify codes with `api-products`, or fall back to
help-doc search (`search "<error-code-or-keyword>" -p <product>`). Hint only; the
commands' behavior is unchanged.

## Degradation trigger matrix

`search_api()` returns `None` (triggering degradation) on the conditions below. Every
degradation is logged as a `WARN` line on stderr so the downgrade always leaves a trace.
An empty result list (`totalCount=0` / empty `info`) is a **trustworthy "no results"**
conclusion and is returned as `[]`, never degraded. Note that with `-p` the fused
pipeline still runs the index leg on an empty full-text list (see above), while an
unscoped search keeps the classic "empty list → not found" behavior.

| Condition | Retry? | Action |
|---|---|---|
| Network exception / timeout | Yes, 1 retry with same timeout | Return `None` if retry also fails |
| HTTP 4xx / 5xx | No | Return `None` immediately |
| HTTP 200 but response is HTML | No | Return `None` (channel change / rate-limit signal; WARN notes "suspected rate-limit or redesign") |
| HTTP 200 but non-JSON / parse failure | No | Return `None` (same WARN note) |
| JSON `success` == false | No | Return `None` |
| JSON `code` != "200" | No | Return `None` |
| `data.info` empty / `totalCount` == 0 | — | Return `[]` (no degradation) |

## Timeout and retry parameters

| Parameter | Value | Applies to |
|---|---|---|
| `SEARCH_TIMEOUT` | 8 seconds | doSearch requests (both attempts) |
| `TIMEOUT` | 15 seconds | llms.txt / .md / meta endpoints |
| Network-error retries | 1 | doSearch only; HTTP errors are never retried |

Worst-case latency with `-p` (all network calls hitting their timeouts, with the
one doSearch retry): a cache miss can cost up to 3 sequential network requests —
wide query (2×8s) → precise query (2×8s) → index leg (15s) — i.e. about 47 seconds
in the worst case; with a cache hit the wide query is skipped, so the worst case
is precise query (2×8s) + index leg (15s), about 31 seconds. Real-world latency
is typically far lower since requests normally return in well under a second.

## Escape switch

Set `ALIYUN_HELP_NO_SEARCH_API=1` to skip the doSearch backend entirely and go straight
to the llms.txt index leg (no fusion, no categoryId cache access):

```bash
ALIYUN_HELP_NO_SEARCH_API=1 python3 scripts/aliyun_help.py search "snapshot" -p ecs
```

Use this when the primary backend is misbehaving (rate limiting, schema changes) and you
need deterministic, if lower-quality, results.

## Result source tagging

With `--json`, every result carries a `source` field: `fulltext` for doSearch-only
hits, `index` for llms.txt-only hits, and `both` for entries found by both legs in a
fused product-scoped search. This makes it explicit which backend produced each hit.
