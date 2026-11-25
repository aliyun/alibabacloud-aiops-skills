#!/usr/bin/env python3
"""Help-centre products, semantic aliases, parent/child search IDs and document trees."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse

from help_const import (
    MAIN_MENU_API,
    MENU_CACHE_DIR,
    MENU_CACHE_TTL_SECONDS,
    MENU_MAX_BYTES,
    MENU_PATH_API,
    MENU_PRODUCT_NODE_TYPE,
    MENU_SUBPRODUCT_NODE_TYPE,
    SITES,
)
from help_http import _is_err, _looks_like_html, fetch, fetch_response
from help_scope import (
    _path_prefix, _resolve_site_lang, _semantic_alias, _url_host, _url_in_product, _url_lang_segment,
)


def _menu_url(site: str, lang: str) -> str:
    return MAIN_MENU_API[site].format(lang=lang)


def _url_code(url: str, site: str, lang: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return ""
    if parsed.netloc and parsed.hostname != SITES[site]["result_host"]:
        return ""
    prefix = _path_prefix(site, lang)
    return parsed.path[len(prefix):].strip("/") if parsed.path.startswith(prefix) else ""


def _node_code(node: dict, site: str, lang: str) -> str:
    alias = _semantic_alias(node.get("alias"))
    return alias.strip("/") or _url_code(node.get("url") or "", site, lang)


def parse_menu(data, site: str, lang: str) -> list:
    if (not isinstance(data, dict) or not isinstance(data.get("data"), dict)
            or data.get("success") is False):
        return []
    host = "https://" + SITES[site]["result_host"]
    products, seen = [], set()

    def walk(node: dict, top: str, parent=None) -> None:
        node_type = node.get("nodeType")
        is_main = node_type == MENU_PRODUCT_NODE_TYPE
        is_child = (node_type == MENU_SUBPRODUCT_NODE_TYPE and node.get("level") == 4
                    and parent is not None)
        if (is_main or is_child) and type(node.get("id")) is int and node["id"] > 0:
            code = _node_code(node, site, lang)
            if code:
                url = node.get("url") or ""
                alias = _semantic_alias(node.get("alias")) or _semantic_alias("/" + code)
                record = {
                    "code": code,
                    "alias": alias,
                    "node_id": node["id"],
                    "node_type": node_type,
                    "category_id": parent["category_id"] if is_child else node["id"],
                    "category4_id": node["id"] if is_child else None,
                    "parent_code": parent["code"] if is_child else "",
                    "name": (node.get("title") or "").replace("\xa0", " ").strip(),
                    "short_name": node.get("shortName") or "",
                    "category": top,
                    "url": host + url if url.startswith("/") else url,
                    "desc": node.get("desc") or "",
                }
                if node["id"] not in seen:
                    seen.add(node["id"])
                    products.append(record)
                if is_main:
                    parent = record
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child, (child.get("title") or "") if node.get("level") == 1 else top, parent)

    walk(data["data"], "")
    return products


def _cache_path(site: str, lang: str) -> str:
    return os.path.join(MENU_CACHE_DIR, site, f"{lang}.json")


def _read_cache(site: str, lang: str):
    """(written_at, products) from the local cache, or (0, None) when absent or unreadable."""
    try:
        with open(_cache_path(site, lang), encoding="utf-8") as f:
            blob = json.load(f)
        products = blob.get("products")
        # Older snapshots omitted subproducts and their parent IDs.
        if blob.get("schema") == 2 and isinstance(products, list) and products:
            return blob.get("written_at", 0), products
    except (OSError, ValueError, AttributeError):
        pass
    return 0, None


def _write_cache(site: str, lang: str, products: list) -> None:
    path = _cache_path(site, lang)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"schema": 2, "written_at": int(time.time()), "products": products},
                      f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError as e:
        print(f"WARN[cache-write]: failed to write the product menu cache ({e}); skipping cache this time",
              file=sys.stderr)


def load_menu(site: str, lang: str):
    """Products of one (site, language) menu, cache-first; None when the menu is unavailable.

    A fresh cache (under one day) is used as is. Otherwise the menu is fetched; when that fails a
    stale cache is still served with a WARN, because the product set changes slowly.
    """
    written_at, cached = _read_cache(site, lang)
    if cached is not None and time.time() - written_at <= MENU_CACHE_TTL_SECONDS:
        return cached
    url = _menu_url(site, lang)
    text = fetch(url, max_bytes=MENU_MAX_BYTES, timeout=SITES[site]["index_timeout"])
    reason = ""
    products = []
    if _is_err(text):
        reason = text
    elif _looks_like_html(text):
        reason = "HTTP 200 with an HTML page instead of JSON"
    else:
        try:
            products = parse_menu(json.loads(text), site, lang)
        except ValueError:
            reason = "unparsable JSON"
        if not products and not reason:
            reason = "no product node in the menu"
    if products:
        _write_cache(site, lang, products)
        return products
    if cached is not None:
        print(f"WARN[menu-stale]: the product menu of the {SITES[site]['label']} ({lang}) is unavailable "
              f"({reason}); using the cached copy from {time.strftime('%Y-%m-%d', time.localtime(written_at))}",
              file=sys.stderr)
        return cached
    print(f"WARN[menu-unavailable]: the product menu of the {SITES[site]['label']} ({lang}) is "
          f"unavailable ({reason}); URL: {url}", file=sys.stderr)
    return None


def find_product(products, product: str):
    """Menu record whose code equals the product code (case-insensitive), or None."""
    want = (product or "").strip("/").lower()
    for record in products or []:
        if record["code"].lower() == want or record["alias"].strip("/").lower() == want:
            return record
        url = urllib.parse.urlsplit(record["url"])
        if (want.startswith(("document_detail/", "product/"))
                and url.path.rstrip("/").lower().endswith("/" + want)):
            return record
    return None


def menu_product_codes(site: str, lang: str):
    """Doc product codes of one (site, language) menu in menu order, or None when unavailable."""
    products = load_menu(site, lang)
    return None if products is None else [p["code"] for p in products]


def load_product_tree(record: dict, site: str, lang: str, alias: str = ""):
    requested = _semantic_alias(alias or record["alias"])
    if not requested:
        return None
    params = {"alias": requested, "website": site, "language": lang, "channel": ""}
    url = MENU_PATH_API[site] + "?" + urllib.parse.urlencode(params)
    text, meta = fetch_response(url, max_bytes=MENU_MAX_BYTES, allow_redirects=False,
                                timeout=SITES[site]["index_timeout"])
    root = None
    if not meta["truncated"] and not _is_err(text) and not _looks_like_html(text):
        try:
            data = json.loads(text)
            if (isinstance(data, dict) and data.get("success") is True
                    and data.get("code", 200) in (200, "200")):
                root = data.get("data")
        except ValueError:
            pass
    if isinstance(root, dict):
        root_alias = _semantic_alias(root.get("alias"))
        expected = record["alias"]
        parent = record["parent_code"]
        if (root.get("id") == record["node_id"]
                and root.get("nodeType") == record["node_type"]
                and root.get("website", site) == site and root.get("language", lang) == lang
                and root_alias and (not expected or root_alias == expected)
                and (requested == root_alias or requested.startswith(root_alias + "/"))
                and (expected or not parent or root_alias.startswith("/" + parent + "/"))
                and isinstance(root.get("children"), list)):
            return root
    print(f"WARN[menu-path-unavailable]: menupath returned an incomplete or identity-mismatched "
          f"document tree for '{record['code']}' ({site}/{lang}); degrading to llms.txt",
          file=sys.stderr)
    return None


def product_tree_docs(root: dict, product: str, site: str, lang: str) -> list | None:
    docs, seen = [], set()
    pending = [root]
    dropped = 0
    while pending:
        node = pending.pop()
        if not isinstance(node, dict):
            dropped += 1
            continue
        children = node.get("children") or []
        if not isinstance(children, list):
            dropped += 1
            continue
        pending.extend(reversed(children))
        if node.get("nodeType") != 1:
            continue
        url = node.get("url") or ""
        if url.startswith("/"):
            url = "https://" + SITES[site]["result_host"] + url
        if url and (_url_host(url) != SITES[site]["result_host"]
                    or _url_lang_segment(url, site) not in ("", lang)):
            dropped += 1
            continue
        if not _url_in_product(url, product, site, lang):
            alias = _semantic_alias(node.get("alias"))
            url = ("https://" + SITES[site]["result_host"] + _path_prefix(site, lang)
                   + alias.lstrip("/")) if alias else ""
        if (node.get("website", site) != site or node.get("language", lang) != lang
                or not _url_in_product(url, product, site, lang)):
            dropped += 1
            continue
        if url not in seen:
            seen.add(url)
            docs.append({"title": (node.get("title") or "").strip(), "url": url,
                         "desc": str(node.get("desc") or "")[:100]})
    if dropped:
        print(f"WARN[menu-path-partial]: dropped {dropped} invalid or out-of-scope tree node(s); "
              "this directory listing is not exhaustive", file=sys.stderr)
    return docs if docs or not dropped else None


_KEYWORD_FIELDS = ("code", "name", "short_name", "category")
_SEARCH_FALLBACK_HITS = 10


def _products_from_search(keyword: str, menu: list, site: str, lang: str) -> list:
    """Menu products named by the URLs of the top full-text hits, in hit order."""
    from help_search import search_api  # deferred: help_search imports this module

    hits = search_api(keyword, limit=_SEARCH_FALLBACK_HITS, site=site, lang=lang) or []
    found, seen = [], set()
    for hit in hits:
        code = (hit.get("product") or "").strip("/")
        url_code = _url_code(hit.get("url") or "", site, lang).split("/", 1)[0]
        record = next((find_product(menu, c) for c in (url_code, code) if c and find_product(menu, c)), None)
        if record and record["node_id"] not in seen:
            seen.add(record["node_id"])
            found.append({**record, "matched_by": "search", "hit_title": hit.get("title") or ""})
    return found


def list_products(args) -> int:
    """List every product of one (site, language) menu, optionally filtered by a keyword."""
    site, lang = _resolve_site_lang(args)
    products = load_menu(site, lang)
    if products is None:
        return 2
    keyword = (getattr(args, "keyword", None) or "").strip().lower()
    if keyword:
        menu = products
        products = [p for p in menu
                    if any(keyword in str(p.get(k, "")).lower() for k in _KEYWORD_FIELDS)]
        if not products:
            products = _products_from_search(keyword, menu, site, lang)
            if not products:
                print(f"No product of the {SITES[site]['label']} ({lang}) matches '{keyword}', and "
                      f"the full-text search hits name no menu product. Use a product name, or run "
                      f"search without -p and read the hit bodies.", file=sys.stderr)
                if args.json:
                    print("[]")
                return 1
            print(f"WARN[product-from-search]: no product name matches '{keyword}'; the products below "
                  f"come from the top full-text search hits and are candidates only: read a hit body "
                  f"to confirm which product the question belongs to.", file=sys.stderr)
    limit = getattr(args, "max_results", 0) or 0
    if limit > 0:
        products = products[:limit]
    if args.json:
        print(json.dumps(products, ensure_ascii=False, indent=2))
        return 0
    print(f"{len(products)} products on the {SITES[site]['label']} ({lang}); "
          f"columns: code  categoryId  category4Id  name")
    for p in products:
        label = p["name"]
        if p["short_name"] and p["short_name"].lower() not in label.lower():
            label += f" ({p['short_name']})"
        child_id = str(p["category4_id"]) if p["category4_id"] is not None else "-"
        print(f"  {p['code']:<40s} {p['category_id']:<9d} {child_id:<11s} {label}")
        if p.get("hit_title"):
            print(f"    search hit: {p['hit_title']}")
        if args.verbose:
            detail = " | ".join(x for x in (p["category"], p["desc"][:60]) if x)
            if detail:
                print(f"    {detail}")
    return 0

