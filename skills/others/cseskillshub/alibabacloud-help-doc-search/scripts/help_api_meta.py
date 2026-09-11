#!/usr/bin/env python3
"""OpenAPI metadata leg (api.aliyun.com/meta/v1).

Site-independent by design: the metadata contract is the same for both portals, so the
api-* subcommands take no --site/--lang.
"""

from __future__ import annotations

import json
import os
import sys

from help_core import (
    META_BASE,
)
from help_http import (
    fetch_json,
)


def _load_meta_products() -> list:
    data = fetch_json(f"{META_BASE}/products.json")
    return data if isinstance(data, list) else []


def _resolve_meta_product(code: str) -> dict:
    """Match an OpenAPI product code case-insensitively (meta paths require exact casing, e.g. Actiontrail/Ecs)."""
    products = _load_meta_products()
    low = code.lower()
    for p in products:
        if (p.get("code") or "").lower() == low or (p.get("shortName") or "").lower() == low:
            return p
    # Fallback: substring match on name
    hits = [p for p in products if low in (p.get("name") or "").lower()]
    if len(hits) == 1:
        return hits[0]
    if hits:
        print(f"[hint] '{code}' matches multiple products; please use an exact code:", file=sys.stderr)
        for p in hits[:10]:
            print(f"  {p['code']:<24s} {p['name']}", file=sys.stderr)
    return {}


def api_products(args) -> int:
    """List OpenAPI metadata products (code/name/version), with optional keyword filtering.

    The metadata endpoint is site-independent (one global product registry), so this command
    takes no --site/--lang. Returns 0 when a list was rendered, 2 when the endpoint is unusable.
    """
    products = _load_meta_products()
    if not products:
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return 2
    kw = (args.keyword or "").lower()
    if kw:
        products = [p for p in products
                    if kw in (p.get("code") or "").lower() or kw in (p.get("name") or "").lower()
                    or kw in (p.get("group") or "").lower()]
    if args.json:
        print(json.dumps(products, ensure_ascii=False, indent=2))
        return 0
    print(f"{len(products)} products in total:")
    for p in products[:args.max_results]:
        versions = ",".join(p.get("versions") or [])
        print(f"  {p.get('code') or '':<24s} {p.get('name') or '':<20s} default version {p.get('defaultVersion') or '-'}"
              f"  (all: {versions})")
    if len(products) > args.max_results:
        print(f"... ({len(products)} entries in total, first {args.max_results} shown; add a keyword to filter)")
    return 0


def api_list(args) -> int:
    """List all APIs (name/title/read-write type) of a given product version, with optional keyword filtering.

    Returns 0 when a list was rendered, 1 when the product code is unknown, 2 when the endpoint
    call failed.
    """
    prod = _resolve_meta_product(args.product)
    if not prod:
        print(f"Product '{args.product}' not found in the OpenAPI metadata; use api-products to see product codes.")
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return 1
    version = args.api_version or prod.get("defaultVersion")
    data = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/api-docs.json")
    if not data:
        print(f"Failed to fetch the API list of {prod['code']}/{version}; available versions: {prod.get('versions')}")
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return 2
    apis = data.get("apis") or {}
    kw = (args.keyword or "").lower()
    rows = []
    for name, info in apis.items():
        title = info.get("title") or ""
        summary = (info.get("summary") or "").split("\n")[0]
        if kw and kw not in name.lower() and kw not in title.lower() and kw not in summary.lower():
            continue
        rows.append((name, title, info.get("operationType", "-"), bool(info.get("deprecated")), summary))
    rows.sort()

    if args.json:
        print(json.dumps([{"api": n, "title": t, "operationType": o, "deprecated": dep, "summary": s}
                          for n, t, o, dep, s in rows], ensure_ascii=False, indent=2))
        return 0
    print(f"{prod['code']} / {version}: {len(rows)} matching APIs in total:\n")
    for name, title, op, deprecated, summary in rows[:args.max_results]:
        flag = " (deprecated)" if deprecated else ""
        print(f"  {name:<44s} {title}{flag} [{op}]")
    if len(rows) > args.max_results:
        print(f"\n... ({len(rows)} entries in total, first {args.max_results} shown; add a keyword to filter)")
    return 0


def _render_schema_type(schema: dict) -> str:
    t = schema.get("type", "-")
    if t == "array":
        item_t = (schema.get("items") or {}).get("type", "?")
        return f"array<{item_t}>"
    return t


def _is_valid_api_meta(data) -> bool:
    """Determine whether single-API metadata is valid (a nonexistent API endpoint returns empty/insubstantial JSON instead of an error)."""
    return isinstance(data, dict) and bool(
        data.get("title") or data.get("methods") or data.get("parameters") or data.get("summary")
    )


# Degradation hint for the api-* failure exits: the meta endpoint is a single dependency (no backup
# backend), so every failure exit points the caller at the narrative fallback path.
_META_FALLBACK_HINT = ("Hint: the OpenAPI metadata endpoint (api.aliyun.com) may be unavailable or rate-limited, "
                       "or the product/API name may be wrong; verify codes with api-products, "
                       "or fall back to help-doc search, e.g. search \"<error-code-or-keyword>\" -p <product>")


# Arguments of the running command, recorded by api_info so the optional documentation lookup
# (F8) can honour --json without threading the parser object through the render helpers.
_CURRENT_ARGS = {}


def api_info(args) -> int:
    """Output the structured contract of a single API: parameters / error codes / RAM permission points / debug link.

    Returns 0 when the contract was rendered, 1 when the product or API name is unknown.
    """
    _CURRENT_ARGS["args"] = args
    prod = _resolve_meta_product(args.product)
    if not prod:
        print(f"Product '{args.product}' not found in the OpenAPI metadata; use api-products to see product codes.")
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return 1
    version = args.api_version or prod.get("defaultVersion")
    api_name = args.api

    data = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/apis/{api_name}/api.json")
    if not _is_valid_api_meta(data):
        # API-name casing fallback: find the exact name from api-docs.json and retry
        docs = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/api-docs.json")
        apis = (docs or {}).get("apis") or {}
        match = next((n for n in apis if n.lower() == api_name.lower()), None)
        if match and match != api_name:
            api_name = match
            data = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/apis/{api_name}/api.json")
        if not _is_valid_api_meta(data):
            print(f"API '{args.api}' not found ({prod['code']}/{version}). "
                  f"Use api-list {prod['code']} to see the API catalog.")
            print(_META_FALLBACK_HINT, file=sys.stderr)
            return 1

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"# {api_name} ({prod['code']} / {version})")
    if data.get("title"):
        print(f"Title: {data['title']}")
    summary = (data.get("summary") or "").strip()
    if summary:
        print(f"Summary: {summary.splitlines()[0]}")
    print(f"Methods: {','.join(data.get('methods', []))}  |  Read/Write: {data.get('operationType', '-')}"
          f"  |  Deprecated: {'yes' if data.get('deprecated') else 'no'}")

    ram = data.get("ramActions") or []
    acts = []
    for a in ram:
        if not isinstance(a, dict):
            continue
        # Two historical shapes: nested {ramAction:{action}} or flat {action}
        act = ((a.get("ramAction") or {}).get("action")) or a.get("action")
        if act:
            acts.append(act)
    if acts:
        print(f"RAM permission points: {', '.join(acts)}")

    params = data.get("parameters") or []
    if params:
        print(f"\n## Request parameters ({len(params)})\n")
        print("| Parameter | In | Type | Required | Description |")
        print("|---|---|---|---|---|")
        for p in params:
            schema = p.get("schema") or {}
            desc = (schema.get("description") or "").split("\n")[0].strip()
            if len(desc) > 80:
                desc = desc[:80] + "..."
            desc = desc.replace("|", "\\|")
            required = "✅" if schema.get("required") else ""
            print(f"| {p.get('name', '-')} | {p.get('in', '-')} | {_render_schema_type(schema)}"
                  f" | {required} | {desc} |")

    err = data.get("errorCodes") or {}
    entries = []
    if isinstance(err, dict):
        for status, items in err.items():
            for it in items if isinstance(items, list) else []:
                entries.append((status, it.get("errorCode", "-"), (it.get("errorMessage") or "")[:80]))
    if entries:
        print(f"\n## Error codes ({len(entries)})\n")
        print("| HTTP | Error code | Message |")
        print("|---|---|---|")
        for status, code, msg in entries:
            print(f"| {status} | {code} | {msg.replace('|', '·')} |")

    print(f"\nDebug / full schema: https://api.aliyun.com/api/{prod['code']}/{version}/{api_name}"
          f" (append --json to this command to dump the full raw metadata, including response structures and examples)")
    _print_related_docs(prod, api_name)
    return 0


def _print_related_docs(prod: dict, api_name: str) -> None:
    """Attach the narrative documentation of this API operation (F8), or say nothing.

    The metadata leg and the documentation leg used to be separate entry points, so a caller
    holding an API name had to guess which words the docs use. The OpenAPI code is lowercased
    into a help-center slug (Oss -> oss, Actiontrail -> actiontrail), which is the documented
    convention rather than a lookup table.

    Strictly additive: it is skipped for --json (the payload must stay parseable), skipped with
    the full-text escape switch, and any failure at all - import, network, or an empty answer -
    is reported on stderr and changes nothing else.
    """
    args = _CURRENT_ARGS.get("args")
    if args is None:
        return
    _CURRENT_ARGS.pop("args", None)
    if getattr(args, "json", False):
        return
    if os.environ.get("ALIYUN_HELP_NO_SEARCH_API") == "1":
        return
    slug = str(prod.get("code", "")).lower()
    if not slug or not api_name:
        return
    try:
        # Imported lazily: the search flow depends on this package's other modules, and the
        # metadata leg must stay loadable without it.
        import help_search
        hits = help_search.search_api(api_name, product=slug, limit=3,
                                     site="cn", lang="zh") or []
    except Exception as e:  # a broken optional leg must never break the contract output
        print(f"WARN[leg-fallback]: the related-documentation lookup failed ({e}); the "
              f"metadata contract above is complete on its own", file=sys.stderr)
        return
    if not hits:
        print(f"INFO: no help-center document was found for '{api_name}' under product '{slug}'; "
              f"the metadata contract above is unaffected", file=sys.stderr)
        return
    print("\n## Related documentation (China site, zh)\n")
    for hit in hits[:3]:
        print(f"- {hit.get('title', '-')} - {hit.get('url', '-')}")
    print("\n(Documentation is narrative and can lag the live contract; where the two disagree, "
          "the metadata above is authoritative.)")
