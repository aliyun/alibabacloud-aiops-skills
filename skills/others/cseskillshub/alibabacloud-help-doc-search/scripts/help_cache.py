#!/usr/bin/env python3
"""User-directory caches for product llms.txt bodies and the categoryId mapping.

Files live under ~/.cache/aliyun-help-search and are written atomically (tmp +
os.replace); nothing is ever written inside the skill directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time

from help_core import (
    CATEGORY_CACHE_PATH,
    CATEGORY_CACHE_TTL_DAYS,
    CATEGORY_SEED,
    DEFAULT_SITE,
    LLMS_CACHE_DIR,
    LLMS_CACHE_MAX_BYTES,
    LLMS_CACHE_TRIM_TO,
    LLMS_CACHE_TTL_DAYS,
    SITES,
    _product_llms_url,
)
from help_http import (
    _fetch_index,
    _is_index_corpus,
    _non_corpus_reason,
)


def _category_cache_key(site: str, lang: str, product: str) -> str:
    """categoryId cache key of a (site, lang, product) triple.

    cn+zh keeps the historical bare-product key so that the built-in CATEGORY_SEED entries
    and the cache files written before the scoping stay valid, and a default invocation stays
    byte-for-byte identical. Every other pair gets a scoped key: the categoryId namespace has
    the same values on both sites, but the corpus behind one id differs per site and per
    language (id 31815 measured total 100 / 130 / 99 / 132 for cn-zh / cn-en / intl-zh /
    intl-en), so entries must never be shared across them.
    """
    if site == "cn" and lang == "zh":
        return product
    return f"{site}:{lang}:{product}"


def _load_category_cache() -> dict:
    """Load the product_code -> categoryId cache.

    When the file is missing, JSON parsing fails, or the top level is not an object (e.g. `[1,2,3]`, `"abc"`),
    fall back to the built-in seeds (seeds are bare ints; the reader is compatible with them and they are TTL-exempt).
    Valid file entries only accept the {"category_id": int, "written_at": number} shape;
    bare-int entries come only from the built-in seeds and are never written to the file by _save_category_cache.
    """
    cache = {"expires_days": CATEGORY_CACHE_TTL_DAYS, "entries": dict(CATEGORY_SEED)}
    try:
        with open(CATEGORY_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return cache
        entries = data.get("entries")
        if isinstance(entries, dict):
            cache["entries"].update(
                {k: v for k, v in entries.items()
                 if isinstance(v, dict) and isinstance(v.get("category_id"), int)})
    except (OSError, ValueError):
        pass
    return cache


def _get_cached_category_id(cache: dict, product: str):
    """Return a non-expired cached categoryId; return None when there is no entry or the TTL has passed.

    Bare-int entries (the built-in seed shape, e.g. {"oss": 31815}) are compatible: return them directly;
    seeds are TTL-exempt (no written_at, valid forever).
    """
    entry = cache.get("entries", {}).get(product)
    if isinstance(entry, bool):
        return None
    if isinstance(entry, int):
        return entry if entry > 0 else None
    if not isinstance(entry, dict):
        return None
    written = entry.get("written_at")
    if not isinstance(written, (int, float)):
        return None
    ttl = cache.get("expires_days", CATEGORY_CACHE_TTL_DAYS) * 86400
    if time.time() - written > ttl:
        return None
    cid = entry.get("category_id")
    return cid if isinstance(cid, int) else None


def _save_category_cache(cache: dict) -> None:
    """Write the cache file back (create the directory if missing).

    Bare-int seed entries are not written to the file (avoid cache-file shape drift; seeds only take effect in memory).
    Write to a temp file (same directory, pid suffix) then os.replace atomically; on write failure only WARN,
    without affecting the main flow.
    """
    entries = {k: v for k, v in cache.get("entries", {}).items()
               if not isinstance(v, int)}
    payload = {"expires_days": cache.get("expires_days", CATEGORY_CACHE_TTL_DAYS),
               "entries": entries}
    try:
        os.makedirs(os.path.dirname(CATEGORY_CACHE_PATH), exist_ok=True)
        tmp_path = f"{CATEGORY_CACHE_PATH}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, CATEGORY_CACHE_PATH)
    except OSError as e:
        print(f"WARN[cache-write]: failed to write the categoryId cache ({e}); skipping cache this time", file=sys.stderr)


def _llms_cache_path(product: str, site: str = DEFAULT_SITE, lang: str = "") -> str:
    """Cache file path of a product llms.txt, scoped by (site, lang).

    Layout: ~/.cache/aliyun-help-search/llms/{site}/{lang}/{product}.txt. Site and language
    are directories on purpose: the same slug on the two sites (or in two languages) is a
    different corpus, and a flat key would silently serve one site's ~1 MB index for the other
    for the whole 3-day TTL. Files written before the scoping live one level up, are never read
    again and are left to expire naturally (no migration, no cleanup). Path separators inside
    the product code are escaped to underscores.
    """
    safe = product.replace("/", "_")
    lang = lang or SITES[site]["default_lang"]
    return os.path.join(LLMS_CACHE_DIR, site, lang, f"{safe}.txt")


def _trim_llms_cache() -> int:
    """Keep the llms.txt cache inside LLMS_CACHE_MAX_BYTES by dropping the oldest entries (N1).

    Only regular '*.txt' files directly under the cache tree are candidates; the file being
    written and any in-flight 'tmp' sibling are never touched, and nothing outside
    LLMS_CACHE_DIR is ever removed. Deletion is safe by construction: every entry is a
    regenerable mirror of a public index with a 3-day TTL.
    """
    entries = []
    total = 0
    for root, _dirs, files in os.walk(LLMS_CACHE_DIR):
        for name in files:
            if not name.endswith(".txt"):
                continue
            path = os.path.join(root, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            entries.append((st.st_mtime, st.st_size, path))
            total += st.st_size
    if total <= LLMS_CACHE_MAX_BYTES:
        return 0
    target = int(LLMS_CACHE_MAX_BYTES * LLMS_CACHE_TRIM_TO)
    dropped = 0
    for _mtime, size, path in sorted(entries):
        if total <= target:
            break
        try:
            os.remove(path)
        except OSError:
            continue
        total -= size
        dropped += 1
    if dropped:
        print(f"INFO: llms.txt cache exceeded {LLMS_CACHE_MAX_BYTES // (1024 * 1024)} MB; "
              f"dropped {dropped} oldest entr(y/ies) to stay within budget", file=sys.stderr)
    return dropped


def _get_llms_text(product: str, site: str = DEFAULT_SITE, lang: str = "") -> tuple:
    """Get the product llms.txt content of one (site, lang) pair, preferring a non-expired local cache.

    Returns (text, from_cache). On cache miss/expiry/read failure, silently refetch from origin and atomically
    refresh the cache; a body that is not a real index - an error marker ([HTTP ...]/[Error]...), an empty body,
    the international 'no LLMS content yet' placeholder, or a WAF interstitial HTML page - is never cached, so a
    dead slug is not pinned as dead for the whole TTL and a transient WAF answer is not served from cache later.
    Rate-limit/outage local degradation: when the origin fetch fails but an expired local cache exists,
    degrade to the stale cache (non-empty content only) with a WARN, instead of surfacing nothing.
    """
    lang = lang or SITES[site]["default_lang"]
    path = _llms_cache_path(product, site, lang)
    try:
        st = os.stat(path)
        if time.time() - st.st_mtime <= LLMS_CACHE_TTL_DAYS * 86400:
            with open(path, encoding="utf-8") as f:
                return f.read(), True
    except OSError:
        pass
    text = _fetch_index(_product_llms_url(site, lang, product), site, lang)
    if _is_index_corpus(text):
        try:
            _trim_llms_cache()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = f"{path}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp_path, path)
        except OSError as e:
            print(f"WARN[cache-write]: failed to write the llms.txt cache ({e}); skipping cache this time", file=sys.stderr)
    else:
        # Local degradation on rate limit / outage: serve the expired cache if present
        try:
            with open(path, encoding="utf-8") as f:
                stale = f.read()
            if stale.strip():
                print(f"WARN[no-corpus]: llms.txt fetch returned no usable index ({_non_corpus_reason(text)}); "
                      f"degrading to the expired local cache for '{product}' "
                      f"(results may lag the live docs)", file=sys.stderr)
                return stale, True
        except OSError:
            pass
    return text, False


# ---------------------------------------------------------------------------
# N8: short-TTL cache of full-text search results
# ---------------------------------------------------------------------------

# The endpoints have no SLA and their ranking jitters minute to minute, so a search result is
# reused only for a few minutes: enough to absorb the repeated queries an Agent makes while it
# reads and re-reads a document list, short enough that a ranking change is visible quickly.
SEARCH_CACHE_DIR = os.path.join(LLMS_CACHE_DIR.replace("/llms", ""), "search")
SEARCH_CACHE_TTL_SECONDS = 600


def search_cache_key(site: str, lang: str, backend: str, params: dict) -> str:
    """Key of one full-text request: the site, the language, the backend and every parameter sent.

    The key is a hash of the *request*, never of the response body, so the jittering fields of a
    search.json payload (keywords.now and the scm trace block) cannot split the cache. Parameters
    are sorted so a re-ordered dict reuses the same entry.
    """
    parts = [site, lang, backend]
    parts.extend(f"{k}={params[k]}" for k in sorted(params))
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:20]


def read_search_cache(key: str):
    """Cached records of a request, or None when absent, unreadable or older than the TTL."""
    path = os.path.join(SEARCH_CACHE_DIR, f"{key}.json")
    try:
        with open(path, encoding="utf-8") as f:
            blob = json.load(f)
        if time.time() - blob.get("written_at", 0) > SEARCH_CACHE_TTL_SECONDS:
            return None
        records = blob.get("records")
        return records if isinstance(records, list) else None
    except (OSError, ValueError):
        return None


def write_search_cache(key: str, records: list) -> None:
    """Store one trustworthy result set (an empty list is a trustworthy "no matches" answer).

    Only the caller that has already passed every legality guard reaches this point, so a
    degradation envelope is never cached; writes are atomic and failures are silent by design -
    a cache that cannot be written must not break a search.
    """
    try:
        os.makedirs(SEARCH_CACHE_DIR, exist_ok=True)
        tmp_path = os.path.join(SEARCH_CACHE_DIR, f"{key}.json.tmp.{os.getpid()}")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"written_at": int(time.time()), "records": records}, f, ensure_ascii=False)
        os.replace(tmp_path, os.path.join(SEARCH_CACHE_DIR, f"{key}.json"))
    except OSError as e:
        print(f"WARN[cache-write]: could not write the search-result cache ({e}); "
              f"this run simply re-queries", file=sys.stderr)


def clear_expired_search_cache() -> int:
    """Drop search-cache entries past their TTL; returns how many were removed."""
    removed = 0
    try:
        names = os.listdir(SEARCH_CACHE_DIR)
    except OSError:
        return 0
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(SEARCH_CACHE_DIR, name)
        try:
            if time.time() - os.path.getmtime(path) > SEARCH_CACHE_TTL_SECONDS * 4:
                os.remove(path)
                removed += 1
        except OSError:
            continue
    return removed
