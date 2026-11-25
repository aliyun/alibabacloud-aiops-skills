#!/usr/bin/env python3
"""OpenAPI metadata and SDK documentation, selected by --site cn|intl."""

from __future__ import annotations

import difflib
import json
import os
import re
import sys
from urllib.parse import urlencode

from help_const import (
    DEFAULT_SITE,
    DOC_MAX_BYTES,
    META_BASE,
    META_LANGS,
    SDK_DOC_API,
    SDK_DOC_LANGS,
    SDK_HIDDEN_KEYS,
    SDK_INFO_API,
    SITES,
    _UsageError,
)
from help_http import (
    _is_err,
    _looks_like_html,
    fetch_json,
    fetch_response,
)
from help_scope import (
    _infer_site,
    _normalize_lang,
)


def _meta_scope(args) -> tuple:
    """Resolve (site, lang) for the metadata commands; lang picks the ?language= variant."""
    lang = _normalize_lang(getattr(args, "lang", None))
    if lang and lang not in META_LANGS:
        raise _UsageError(f"ERROR: OpenAPI metadata --lang supports {'/'.join(META_LANGS)}.")
    site = args.site or (_infer_site(lang) if lang else DEFAULT_SITE)
    return site, lang or SITES[site]["default_lang"]


def _meta_url(site: str, lang: str, path: str) -> str:
    return f"{META_BASE[site]}/{path}?{urlencode({'language': META_LANGS[lang]})}"


def _load_meta_products(site: str = DEFAULT_SITE, lang: str = "") -> list:
    data = fetch_json(_meta_url(site, lang or SITES[site]["default_lang"], "products.json"))
    return data if isinstance(data, list) else []


def _squash(text) -> str:
    """Lowercase a code or name and drop separators and punctuation, so 'FC-Open' == 'fcopen'.

    Only separators go: CJK is kept, otherwise every Chinese product name would collapse to its
    latin fragment and 'VPC对等连接' would compare equal to 'vpc'.
    """
    return re.sub(r"[^\w]+", "", (text or "").lower(), flags=re.UNICODE)


def _is_acronym_of(code: str, slug: str) -> bool:
    """True when a short product code is the initialism of a longer slug.

    The doc portal and the OpenAPI metadata name the same product differently
    ('functioncompute' vs 'FC'), and the metadata carries no English name to match against, so
    the code's letters are matched as an in-order subsequence of the slug anchored on its first
    letter. Only short codes qualify, and a hit is still only a candidate: an ambiguous match
    falls through to the "use an exact code" hint rather than picking one.
    """
    if not (2 <= len(code) <= 4) or not slug.startswith(code[0]):
        return False
    i = 0
    for ch in slug:
        if i < len(code) and ch == code[i]:
            i += 1
    return i == len(code)


def _resolve_meta_product(code: str, site: str = DEFAULT_SITE, *, products=None, lang: str = "") -> dict:
    """Resolve an OpenAPI product from a code, short name, product name or doc slug.

    Matching is deliberately generic rather than a maintained alias table: exact code/shortName
    first (ignoring case and separators, since meta paths need exact casing, e.g. Actiontrail/Ecs),
    then a name substring, then the initialism rule above. A unique candidate wins; several
    candidates are listed as a hint so the caller can pass an exact code.
    """
    products = _load_meta_products(site, lang) if products is None else products
    want = (code or "").strip().lower()
    squashed = _squash(want)
    if not squashed:
        return {}
    for p in products:
        for field in ("code", "shortName", "name"):
            if _squash(p.get(field)) == squashed:
                return p
    hit_tiers = (
        [p for p in products if want in (p.get("name") or "").lower()],
        [p for p in products if _is_acronym_of(_squash(p.get("code")), squashed)],
    )
    for hits in hit_tiers:
        if len(hits) == 1:
            return hits[0]
        if hits:
            print(f"[hint] '{code}' matches multiple products; please use an exact code:",
                  file=sys.stderr)
            for p in hits[:10]:
                print(f"  {p['code']:<24s} {p['name']}", file=sys.stderr)
            return {}
    near = difflib.get_close_matches(squashed, [_squash(p.get("code")) for p in products],
                                     n=5, cutoff=0.6)
    if near:
        print(f"[hint] '{code}' matches no product; did you mean: "
              f"{', '.join(p['code'] for p in products if _squash(p.get('code')) in near)}?",
              file=sys.stderr)
    return {}


def api_products(args) -> int:
    """List OpenAPI metadata products on the selected site, with optional keyword filtering."""
    site, lang = _meta_scope(args)
    products = _load_meta_products(site, lang)
    if not products:
        print(_META_FALLBACK_HINT.format(base=META_BASE[site], site=site), file=sys.stderr)
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
    limit = args.max_results if args.max_results > 0 else len(products)
    for p in products[:limit]:
        recommended = p.get("recommendVersions")
        recommendation_known = (isinstance(recommended, list)
                                and all(isinstance(v, str) and v for v in recommended))
        versions = []
        for version in p.get("versions") or []:
            status = "recommendation unknown"
            if recommendation_known:
                status = "recommended" if version in recommended else "not recommended"
            versions.append(f"{version} [{status}]")
        print(f"  {p.get('code') or '':<24s} {p.get('name') or '':<20s} default version {p.get('defaultVersion') or '-'}"
              f"  (all: {', '.join(versions) or '-'})")
    if len(products) > limit:
        print(f"... ({len(products)} entries in total, first {limit} shown; add a keyword to filter or pass -n 0 for all)")
    return 0


def api_list(args) -> int:
    """List all APIs (name/title/read-write type) of a given product version, with optional keyword filtering.

    Returns 0 when a list was rendered, 1 when the product code is unknown, 2 when the endpoint
    call failed.
    """
    site, lang = _meta_scope(args)
    prod = _resolve_meta_product(args.product, site, lang=lang)
    if not prod:
        print(f"Product '{args.product}' not found in the OpenAPI metadata; use api-products to see product codes.")
        print(_META_FALLBACK_HINT.format(base=META_BASE[site], site=site), file=sys.stderr)
        return 1
    version = args.api_version or prod.get("defaultVersion")
    data = fetch_json(_meta_url(site, lang, f"products/{prod['code']}/versions/{version}/api-docs.json"))
    if not data:
        print(f"Failed to fetch the API list of {prod['code']}/{version}; available versions: {prod.get('versions')}")
        print(_META_FALLBACK_HINT.format(base=META_BASE[site], site=site), file=sys.stderr)
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
    limit = args.max_results if args.max_results > 0 else len(rows)
    for name, title, op, deprecated, summary in rows[:limit]:
        flag = " (deprecated)" if deprecated else ""
        print(f"  {name:<44s} {title}{flag} [{op}]")
    if len(rows) > limit:
        print(f"\n... ({len(rows)} entries in total, first {limit} shown; add a keyword to filter or pass -n 0 for all)")
    return 0


_SDK_KEY_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")


def _fetch_sdk_languages(site: str, product: str, version: str) -> tuple:
    """Return (url, entries) of the portal's SDK language keys; entries is None when unusable.

    Applies the portal's own rules: SDK_HIDDEN_KEYS are dropped, a '-tea' key is SDK V2.0
    (recommended) and any other key is V1.0. Recommended keys sort first.
    """
    url = f"{SDK_INFO_API[site]}?{urlencode({'product': product, 'version': version})}"
    text, meta = fetch_response(url, allow_redirects=False, max_bytes=DOC_MAX_BYTES)
    if _is_err(text) or _looks_like_html(text) or meta.get("truncated"):
        return url, None
    try:
        envelope = json.loads(text)
    except (ValueError, RecursionError):
        return url, None
    if not isinstance(envelope, dict) or type(envelope.get("code")) is not int or envelope["code"] != 0:
        return url, None
    data = envelope.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("lastSdkInfo"), dict):
        return url, None
    entries = []
    for key, value in data["lastSdkInfo"].items():
        if key in SDK_HIDDEN_KEYS:
            continue
        if not (_SDK_KEY_RE.fullmatch(key) and isinstance(value, dict)
                and isinstance(value.get("language"), str)
                and isinstance(value.get("package_name"), str)):
            return url, None
        v2 = key.endswith("-tea")
        entries.append({"key": key, "generation": "V2.0" if v2 else "V1.0", "recommended": v2,
                        "language": value["language"], "packageName": value["package_name"]})
    entries.sort(key=lambda e: (not e["recommended"], e["key"]))
    return url, entries


def _print_sdk_languages(args, site: str, code: str, version: str, url: str, entries: list) -> int:
    if args.json:
        print(json.dumps({"site": site, "product": code, "apiVersion": version, "url": url,
                          "languages": entries}, ensure_ascii=False, indent=2))
        return 0
    print(f"# OpenAPI SDK languages: {code} / {version} ({site})\n\nSource: {url}")
    print("\nNOTE: '-tea' keys are SDK V2.0, the generation the portal recommends; other keys are the "
          "legacy V1.0 SDK. Pass one key to --language to read its complete guide. The SDK generation "
          "is neither the API version nor the SDK package version.")
    for recommended, title in ((True, "V2.0 (recommended)"), (False, "V1.0 (not recommended)")):
        group = [e for e in entries if e["recommended"] is recommended]
        if group:
            print(f"\n## {title}\n")
            for e in group:
                print(f"- {e['key']}: {e['language']}, package {e['packageName']}")
    return 0


def sdk_doc(args) -> int:
    lang = _normalize_lang(args.lang)
    if lang and lang not in SDK_DOC_LANGS:
        raise _UsageError("ERROR: sdk-doc --lang supports zh/en only; --language selects the SDK language key.")
    site = args.site or (_infer_site(lang) if lang else DEFAULT_SITE)
    lang = lang or SITES[site]["default_lang"]
    language = (args.language or "").strip().lower()
    if args.language is not None and not _SDK_KEY_RE.fullmatch(language):
        raise _UsageError("ERROR: sdk-doc --language requires an SDK language key, e.g. python-tea; "
                          "omit it to list the available keys.")
    products = _load_meta_products(site, lang)
    if not products:
        print("Failed to fetch OpenAPI products; the SDK documentation cannot be verified.", file=sys.stderr)
        return 2
    prod = _resolve_meta_product(args.product, site, products=products)
    if not prod:
        print(f"Product '{args.product}' not found; use api-products --site {site} to confirm the OpenAPI code.")
        return 1
    version = args.api_version or prod.get("defaultVersion")
    if not version or version not in (prod.get("versions") or []):
        raise _UsageError(f"ERROR: unknown API version '{version}' for {prod['code']}; available: {prod.get('versions')}.")
    info_url, entries = _fetch_sdk_languages(site, prod["code"], version)
    if entries is None:
        print(f"Failed to fetch a usable SDK language list: {info_url}", file=sys.stderr)
        return 2
    if not entries:
        print(f"No OpenAPI SDK language is published for {prod['code']}/{version} ({site}).")
        return 1
    if not language:
        return _print_sdk_languages(args, site, prod["code"], version, info_url, entries)
    sdk = next((e for e in entries if e["key"] == language), None)
    if sdk is None:
        base = language.split("-")[0]
        near = [e["key"] for e in entries if e["key"].split("-")[0] == base or e["language"] == base]
        print(f"SDK language key '{language}' is not offered for {prod['code']}/{version} ({site}).")
        if near:
            print(f"Matching keys: {', '.join(near)} (prefer a V2.0 '-tea' key).")
        print(f"List every key with: sdk-doc {prod['code']} -V {version} --site {site}")
        return 1
    alternative = None if sdk["recommended"] else next(
        (e["key"] for e in entries if e["recommended"] and e["language"] == sdk["language"]), None)
    params = {"product": prod["code"], "version": version,
              "language": language, "lang": SDK_DOC_LANGS[lang]}
    url = f"{SDK_DOC_API[site]}?{urlencode(params)}"
    text, meta = fetch_response(url, allow_redirects=False, max_bytes=DOC_MAX_BYTES)
    if _is_err(text) or _looks_like_html(text) or meta.get("truncated"):
        print(f"Failed to fetch complete SDK documentation: {url}", file=sys.stderr)
        return 2
    try:
        envelope = json.loads(text)
    except (ValueError, RecursionError):
        print(f"Invalid SDK documentation JSON: {url}", file=sys.stderr)
        return 2
    if not isinstance(envelope, dict) or type(envelope.get("code")) is not int:
        print(f"Invalid SDK documentation envelope: {url}", file=sys.stderr)
        return 2
    data = envelope.get("data")
    if envelope["code"] == 1 and data == params:
        print(f"No SDK documentation for {prod['code']}/{version}/{language} ({lang}, {site}).")
        return 1
    docs = data.get("documentation") if isinstance(data, dict) else None
    valid = (envelope["code"] == 0 and isinstance(data, dict)
             and isinstance(data.get("status"), str)
             and isinstance(data.get("codeSample"), str) and bool(data["codeSample"].strip())
             and isinstance(data.get("install"), list)
             and all(isinstance(entry, dict) and isinstance(entry.get("method"), str)
                     and isinstance(entry.get("command"), str) for entry in data["install"])
             and isinstance(data.get("info"), dict)
             and (docs is None or (isinstance(docs, dict)
                                   and isinstance(docs.get("intro"), str)
                                   and isinstance(docs.get("urls"), list)
                                   and all(isinstance(entry, dict) and isinstance(entry.get("name"), str)
                                           and isinstance(entry.get("value"), str)
                                           for entry in docs["urls"]))))
    if not valid:
        print(f"Unusable SDK documentation response: {url}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"site": site, "lang": lang, "product": prod["code"],
                          "apiVersion": version, "language": language, "url": url,
                          "sdk": sdk, "recommendedAlternative": alternative,
                          "languagesUrl": info_url, "data": data}, ensure_ascii=False, indent=2))
        return 0
    label = "recommended" if sdk["recommended"] else "not recommended"
    print(f"# OpenAPI SDK: {prod['code']} / {version} / {language} ({lang})\n\nSource: {url}")
    print(f"SDK generation: {sdk['generation']} ({label}); package: {sdk['packageName']}")
    if not sdk["recommended"]:
        hint = f"; the portal recommends the V2.0 key '{alternative}'" if alternative else ""
        print(f"\nNOTE: This is the legacy V1.0 SDK{hint}. Do not mix V1.0 and V2.0 classes in one project.")
    print("\nNOTE: The official example illustrates SDK usage and may call a write API. "
          "Verify the requested API with api-info; installation and execution are left to the user.")
    print(f"\n## Environment and dependencies\n\n{data['status']}")
    print("\n## SDK installation")
    for entry in data["install"]:
        print(f"\n### {entry['method']}\n\n{entry['command']}")
    print(f"\n## Complete example and usage steps\n\n{data['codeSample']}")
    print("\n## SDK information\n\n```json\n"
          + json.dumps(data["info"], ensure_ascii=False, indent=2) + "\n```")
    if docs is None:
        return 0
    print(f"\n## Usage documentation\n\n{docs['intro']}")
    for entry in docs["urls"]:
        print(f"- {entry['name']}: {entry['value']}")
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
_META_FALLBACK_HINT = ("Hint: the OpenAPI metadata endpoint ({base}) may be unavailable or rate-limited, "
                       "or the product/API name may be wrong; verify codes with api-products --site {site}, "
                       "or fall back to help-doc search, e.g. search \"<error-code-or-keyword>\" "
                       "-p <product> --site {site}")


# Arguments of the running command, recorded by api_info so the optional documentation lookup
# (F8) can honour --json without threading the parser object through the render helpers.
_CURRENT_ARGS = {}


def api_info(args) -> int:
    """Output the structured contract of a single API: parameters / error codes / RAM permission points / debug link.

    Returns 0 when the contract was rendered, 1 when the product or API name is unknown.
    """
    _CURRENT_ARGS["args"] = args
    site, lang = _meta_scope(args)
    prod = _resolve_meta_product(args.product, site, lang=lang)
    if not prod:
        print(f"Product '{args.product}' not found in the OpenAPI metadata; use api-products to see product codes.")
        print(_META_FALLBACK_HINT.format(base=META_BASE[site], site=site), file=sys.stderr)
        return 1
    version = args.api_version or prod.get("defaultVersion")
    api_name = args.api
    api_path = f"products/{prod['code']}/versions/{version}"

    data = fetch_json(_meta_url(site, lang, f"{api_path}/apis/{api_name}/api.json"))
    if not _is_valid_api_meta(data):
        # API-name casing fallback: find the exact name from api-docs.json and retry
        docs = fetch_json(_meta_url(site, lang, f"{api_path}/api-docs.json"))
        apis = (docs or {}).get("apis") or {}
        match = next((n for n in apis if n.lower() == api_name.lower()), None)
        if match and match != api_name:
            api_name = match
            data = fetch_json(_meta_url(site, lang, f"{api_path}/apis/{api_name}/api.json"))
        if not _is_valid_api_meta(data):
            print(f"API '{args.api}' not found ({prod['code']}/{version}). "
                  f"Use api-list {prod['code']} to see the API catalog.")
            print(_META_FALLBACK_HINT.format(base=META_BASE[site], site=site), file=sys.stderr)
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

    explorer_base = META_BASE[site].removesuffix("/meta/v1")
    print(f"\nDebug / full schema: {explorer_base}/api/{prod['code']}/{version}/{api_name}"
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
    site, lang = _meta_scope(args)
    if lang not in SITES[site]["langs"]:
        lang = SITES[site]["default_lang"]
    try:
        # Imported lazily: the search flow depends on this package's other modules, and the
        # metadata leg must stay loadable without it.
        import help_search
        hits = help_search.search_api(api_name, product=slug, limit=3,
                                     site=site, lang=lang) or []
    except Exception as e:  # a broken optional leg must never break the contract output
        print(f"WARN[leg-fallback]: the related-documentation lookup failed ({e}); the "
              f"metadata contract above is complete on its own", file=sys.stderr)
        return
    if not hits:
        print(f"INFO: no help-center document was found for '{api_name}' under product '{slug}'; "
              f"the metadata contract above is unaffected", file=sys.stderr)
        return
    print(f"\n## Related documentation ({SITES[site]['label']}, {lang})\n")
    for hit in hits[:3]:
        print(f"- {hit.get('title', '-')} - {hit.get('url', '-')}")
    print("\n(Documentation is narrative and can lag the live contract; where the two disagree, "
          "the metadata above is authoritative.)")
