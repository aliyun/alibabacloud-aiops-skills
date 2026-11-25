#!/usr/bin/env python3
# SECURITY: announcement text is remote content. It is rendered as reference DATA only; nothing
# in it is executed or followed. The raw item also carries an internal "ExtInfo" blob (an
# approval-process URL on an internal host), so only the whitelisted fields of _parse_item are
# ever printed, in text mode and in --json alike.
"""Announcement leg: official Alibaba Cloud notices, selected by --site cn|intl and --lang.

Docs describe how a product behaves; announcements say what is about to change - instance
types going offline, billing starting, domains retired, maintenance windows, vulnerability
alerts. This leg queries the public notice list of one site (www.aliyun.com/notice or
www.alibabacloud.com/notice) by keyword, product and type, newest first, and never mixes sites.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

from help_const import (
    DEFAULT_SITE,
    MAX_QUERY_LEN,
    _ALL_LANGS,
    _UsageError,
    UNSUPPORTED_LANGS,
    NOTICE_API,
    NOTICE_LANGS,
    NOTICE_MAX_BYTES,
    NOTICE_PAGE,
    NOTICE_PAGESIZE_MAX,
    SEARCH_LANG_WHITELIST,
    SITES,
)
from help_http import _is_err, _looks_like_html, fetch_response
from help_scope import _infer_site, _normalize_lang

# PublishTime is epoch milliseconds; the notices themselves state times in Asia/Shanghai.
_UTC8 = timezone(timedelta(hours=8))


def _notice_scope(args) -> tuple[str, str]:
    site = args.site or DEFAULT_SITE
    if site not in SITES:
        raise _UsageError(f"ERROR: invalid --site '{site}'. Supported: {', '.join(SITES)}.")
    lang = _normalize_lang(args.lang)
    if lang and lang not in set(_ALL_LANGS) | UNSUPPORTED_LANGS:
        raise _UsageError(f"ERROR: unsupported --lang '{lang}'. Supported: {', '.join(_ALL_LANGS)}.")
    if lang and not args.site:
        site = _infer_site(lang)
    return site, lang or SITES[site]["default_lang"]


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _build_params(site: str, lang: str, keyword: str, product: str, kind: str,
                  page: int, page_size: int) -> dict:
    params = {"PageNo": max(page, 1), "PageSize": min(max(page_size, 1), NOTICE_PAGESIZE_MAX),
              "Website": site, "Language": lang}
    if keyword:
        params["QueryFuzzy"] = keyword[:MAX_QUERY_LEN]
    if product:
        params["ProductCode"] = product
    if kind:
        params["BulletinType"] = kind
    return params


def _query(site: str, params: dict) -> tuple[list, int, int]:
    """One page of notices as (items, total, rc): rc 0 = answered, 2 = unusable."""
    url = NOTICE_API[site]
    body = urlencode({"product": "bulletin", "action": "Query", "sec_token": "",
                      "params": json.dumps(params, ensure_ascii=False, separators=(",", ":"))})
    text, _ = fetch_response(url, data=body.encode(), max_bytes=NOTICE_MAX_BYTES, attempts=2,
                             allow_redirects=False,
                             headers={"Content-Type": "application/x-www-form-urlencoded",
                                      "Referer": NOTICE_PAGE[site]})
    if _is_err(text):
        print(f"[request failed] {url} -> {text}", file=sys.stderr)
        return [], 0, 2
    if _looks_like_html(text):
        print(f"[request failed] {url} returned an HTML page instead of JSON", file=sys.stderr)
        return [], 0, 2
    try:
        blob = json.loads(text)
    except (ValueError, RecursionError):
        print(f"[JSON parse failed] {url}", file=sys.stderr)
        return [], 0, 2
    if not isinstance(blob, dict):
        print(f"[unexpected payload] {url} did not return a JSON object", file=sys.stderr)
        return [], 0, 2
    raw_code = blob.get("code")
    code = str(raw_code) if isinstance(raw_code, (str, int)) else ""
    if code != "200":
        print(f"[endpoint error] {url} answered code {code if code.isdecimal() else 'unknown'}",
              file=sys.stderr)
        return [], 0, 2
    data = (blob.get("data") or {}).get("Data") if isinstance(blob.get("data"), dict) else None
    if not isinstance(data, dict):
        print(f"[unexpected payload] {url} carried no data.Data object", file=sys.stderr)
        return [], 0, 2
    info = data.get("Info")
    try:
        total = int(data.get("TotalCount") or 0)
    except (TypeError, ValueError, OverflowError):
        print(f"[unexpected payload] {url} carried an invalid TotalCount", file=sys.stderr)
        return [], 0, 2
    if total < 0 or not isinstance(info, list):
        print(f"[unexpected payload] {url} carried an invalid announcement list", file=sys.stderr)
        return [], 0, 2
    return info, total, 0


def _json_field(raw, default):
    """Several fields are JSON documents serialized into a string."""
    if not isinstance(raw, str) or not raw.strip():
        return default
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError):
        return default
    return value if isinstance(value, type(default)) else default


def _format_ms(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, _UTC8).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def _impact(raw) -> list:
    """Impact windows as 'start ~ end zone (remark)' strings."""
    out = []
    for w in _json_field(raw, []):
        if not isinstance(w, dict):
            continue
        start, end = _text(w.get("startTime")).strip(), _text(w.get("endTime")).strip()
        if not start and not end:
            continue
        span = f"{start} ~ {end}" if start and end else (start or f"~ {end}")
        zone = _text(w.get("timeZone")).strip()
        remark = " ".join(_text(w.get("timeRemark")).split())
        out.append(span + (f" {zone}" if zone else "") + (f" ({remark})" if remark else ""))
    return out


def _parse_item(item: dict, lang: str) -> dict:
    """Whitelisted, normalized view of one notice; anything not listed here is never output."""
    products = []
    for p in _json_field(item.get("ProductInfo"), []):
        if not isinstance(p, dict) or not _text(p.get("productCode")):
            continue
        name = p.get("productName") if lang == "zh" else p.get("productNameEn")
        products.append({"code": p["productCode"],
                         "name": _text(name) or _text(p.get("productName")) or _text(p.get("productNameEn"))})
    if not products:
        products = [{"code": c, "name": ""} for c in _json_field(item.get("ProductCode"), [])
                    if isinstance(c, str)]
    ident = item.get("BulletinId")
    return {
        "id": ident if type(ident) is int or isinstance(ident, str) and ident.isdecimal() else None,
        "title": " ".join((_text(item.get("Title")) or _text(item.get("TitleFill"))).split()),
        "url": _text(item.get("Url")),
        "published": _format_ms(item.get("PublishTime")),
        "lang": _text(item.get("Language")),
        "type": [t for t in (item.get("BulletinType"), item.get("BulletinType2"),
                             item.get("BulletinType3")) if isinstance(t, str) and t],
        "products": products,
        "impact": _impact(item.get("ImpactTime")),
        "content": " ".join(_text(item.get("Content")).split()),
    }


# ---------------------------------------------------------------------------
# Redundant document-side query: the same fact (a limit, a change, a retired feature)
# may live in the docs instead of an announcement, so an empty (or unreachable)
# announcement list is never the end of the search.
# ---------------------------------------------------------------------------

def _docs_query(keyword: str, product: str, kind: str) -> str:
    """The doc-side query: keyword first; -p / -t are announcement dimensions and are not reused."""
    parts = [keyword]
    if not keyword:
        parts = [product]
        if kind:
            parts.append({"loss": "下线", "security": "安全", "other": "变更"}.get(kind, kind))
    query = " ".join(part for part in parts if part)
    return query[:MAX_QUERY_LEN]


def _docs_category(site: str, lang: str, product: str):
    """(categoryId, confirmed) of the doc product code read from the site menu; (None, False) without -p.

    A record outside the menu (category4Id-only or no alias) is not verified enough to filter on:
    only the categoryId itself is reused, and the hits are then filtered by the product URL path.
    """
    if not product:
        return None, False
    # The doc search only serves en/zh (other languages silently answer in English), so a
    # menu lookup in, say, 'ja' would scope a corpus the leg cannot read.
    if lang not in SEARCH_LANG_WHITELIST:
        return None, False
    from help_menu import find_product, load_menu
    record = find_product(load_menu(site, lang), product)
    if record is None:
        return None, False
    confirmed = record["category4_id"] is None and bool(record["alias"])
    return record["category_id"], confirmed


def _notice_fallback(args, site: str, lang: str, keyword: str, product: str, kind: str):
    """Document-side results carrying the same query, or None when the doc leg is unavailable."""
    if getattr(args, "no_docs", False):
        return None
    query = _docs_query(keyword, product, kind)
    if not query:
        return None
    from help_search import search_api
    category_id, confirmed = _docs_category(site, lang, product)
    hits = search_api(query, limit=args.max_results, category_id=category_id, site=site, lang=lang)
    if hits is None:
        print(f"WARN[docs-redundant-unavailable]: the document full-text search could not be "
              f"verified either, so whether '{query}' is documented remains unknown", file=sys.stderr)
        return None
    if category_id is not None and not confirmed:
        from help_scope import _url_in_product
        hits = [h for h in hits if _url_in_product(h["url"], product, site, lang)]
    return hits


def _render_docs_fallback(args, site: str, lang: str, reason: str, docs: list) -> None:
    """Print (or, with --json, emit as the sole payload) the document-side results."""
    if args.json:
        print(json.dumps({"docs": docs, "redundantQuery": True}, ensure_ascii=False, indent=2))
        return
    print(f"Redundant document-side query ({SITES[site]['label']}, {lang}): "
          f"announcements and documents are separate sources and neither replaces the other.")
    if not docs:
        print(f"No document matched either ({reason}); that does not prove the information does "
              f"not exist. Broaden the keyword or browse the product directory (list-docs).")
        return
    print(f"Document matches (announcements: {reason}):")
    print()
    print(f"Found {len(docs)} matching docs:\n")
    for i, doc in enumerate(docs, 1):
        print(f"{i}. [{doc.get('product') or '-'}] {doc['title']}")
        print(f"   {doc['url']}")
        if doc.get("desc"):
            print(f"   {doc['desc']}")
        print()


def notice_search(args) -> int:
    """List official announcements matching a keyword / product / type, newest first.

    Returns 0 when at least one notice (or, without one, at least one document from the redundant
    document-side query) was rendered, 1 when neither source matched (a normal answer), 2 when the
    announcement list could not be reached (document matches are still printed alongside).
    """
    site, lang = _notice_scope(args)
    keyword = (args.keyword or "").strip()
    product = (args.product or "").strip().lower()
    kind = (args.type or "").strip().lower()
    no_docs = getattr(args, "no_docs", False)

    def doc_leg():
        # --no-docs is a plain absence of results, never an unavailable document leg.
        return None if no_docs else _notice_fallback(args, site, lang, keyword, product, kind)

    if getattr(args, "docs_only", False):
        if not (keyword or product):
            raise _UsageError("--docs-only needs a keyword or -p product for the document search.")
        results = doc_leg()
        if results is None:
            print(f"ERROR: no document-side query could be issued, so nothing was searched.")
            return 2
        _render_docs_fallback(args, site, lang, "docs-only", results)
        return 0 if results else 1
    params = _build_params(site, lang, keyword, product, kind, args.page, args.max_results)
    raw, total, rc = _query(site, params)
    label = SITES[site]["label"]
    if rc != 0:
        docs = doc_leg()
        print(f"Failed to query the {label} announcement list, so it is unknown whether a "
              f"matching announcement exists.")
        print(f"Endpoint: {NOTICE_API[site]}")
        print(f"Suggestion: retry, or ask the user to open {NOTICE_PAGE[site]} and search there.")
        if docs is not None:
            _render_docs_fallback(args, site, lang, "announcement list unreachable", docs)
        elif args.json:
            print(json.dumps({"docs": None, "redundantQuery": False}, ensure_ascii=False, indent=2))
        return 2

    items = []
    host = urlsplit(NOTICE_PAGE[site]).hostname
    for item in raw:
        if not isinstance(item, dict) or item.get("Website") != site:
            continue
        actual_lang = item.get("Language")
        if actual_lang != lang and not (site == "intl" and lang == "ja" and actual_lang == "en"):
            continue
        try:
            url = urlsplit(_text(item.get("Url")))
        except ValueError:
            continue
        if url.scheme != "https" or url.hostname != host or url.username or url.password:
            continue
        parsed = _parse_item(item, lang)
        if parsed["id"] is None or not parsed["title"]:
            continue
        items.append(parsed)
    if len(items) < len(raw):
        print(f"WARN[notice-scope]: dropped invalid or out-of-scope announcements from the {label}",
              file=sys.stderr)
    if raw and not items:
        print(f"No usable announcement was returned by the {label}; the response could not be verified.")
        return 2

    if not items:
        docs = doc_leg()
        what = ", ".join(f"{k} '{v}'" for k, v in (("keyword", keyword), ("product", product),
                                                    ("type", kind)) if v) or "any filter"
        answer = f"The {label} has no announcement in '{lang}' matching {what} (page {params['PageNo']})."
        if args.json:
            payload = {"site": site, "lang": lang, "keyword": keyword, "product": product,
                       "type": kind, "page": params["PageNo"], "total": 0, "list": []}
            if docs is not None:
                payload.update(docs=docs, redundantQuery=True)
                print(f"INFO[no-announcement]: no announcement matched on the {label} ({lang}); "
                      f"the payload lists document-side matches instead", file=sys.stderr)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(answer)
            if lang not in NOTICE_LANGS[site]:
                print(f"Note: the {label} publishes announcements in {', '.join(NOTICE_LANGS[site])}; "
                      f"retry with -L {NOTICE_LANGS[site][0]}.")
            if product:
                print("Note: -p matches the announcement system's own product code, which can differ "
                      "from the doc product code; retry without -p and use the product name as keyword.")
            other = "intl" if site == "cn" else "cn"
            print(f"Note: the two sites publish different announcements; use '--site {other}' only if "
                  f"the user is on that site. No automatic site fallback is performed.")
            if docs is not None:
                _render_docs_fallback(args, site, lang, "no announcement matched", docs)
        return 0 if docs else 1


    if args.json:
        print(json.dumps({"site": site, "lang": lang, "keyword": keyword, "product": product,
                          "type": kind, "page": params["PageNo"], "total": total, "list": items},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"{label} announcements ({lang}): {total} matching, {len(items)} shown on page "
          f"{params['PageNo']}, newest first\n")
    for n in items:
        marker = f" [{n['lang']}]" if n["lang"] and n["lang"] != lang else ""
        print(f"- [{n['id']}] {n['title']}{marker}")
        prods = ", ".join(f"{p['code']} ({p['name']})" if p["name"] else p["code"]
                          for p in n["products"]) or "-"
        print(f"  published {n['published'] or '-'} (UTC+8)  |  type {' / '.join(n['type']) or '-'}"
              f"  |  products {prods}")
        for window in n["impact"]:
            print(f"  impact {window}")
        if n["url"]:
            print(f"  {n['url']}")
        body = n["content"]
        if body:
            print(f"  {body}" if args.full or len(body) <= 200 else f"  {body[:200]}...")
    shown_to = (params["PageNo"] - 1) * params["PageSize"] + len(items)
    if total > shown_to:
        print(f"\n... ({total} in total; pass --page {params['PageNo'] + 1} for the next page, or "
              f"narrow with a keyword, -p or -t)")
    if not args.full:
        print("\nPass --full to print every announcement body in full.")
    return 0
