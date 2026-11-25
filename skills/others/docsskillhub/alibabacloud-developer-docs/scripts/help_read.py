#!/usr/bin/env python3
"""Document reading: China-site Markdown, international-site HTML converted to Markdown."""

from __future__ import annotations

import json
import sys
from urllib.parse import quote, unquote, urlencode, urljoin, urlsplit, urlunsplit

from help_cache import (
    _llms_cache_path,
)
from help_const import (
    DOC_DETAIL_API,
    DOC_MAX_BYTES,
    SITES,
    _UsageError,
)
from help_llms_index import (
    _get_llms_text,
)
from help_scope import (
    _remember_scope,
    _resolve_site_lang,
    _url_host,
    _url_scope,
)
from help_http import (
    _is_err,
    _index_failure_code,
    _is_index_corpus,
    _looks_like_html,
    _non_corpus_reason,
    fetch,
)
from help_render import (
    _convert_html_tables,
    _fold_code_escape_marker,
    _html_to_markdown,
)


def _intl_doc_scope(url: str) -> tuple[str, str, str]:
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname != SITES["intl"]["result_host"]
                or parsed.port not in (None, 443) or parsed.username is not None
                or parsed.password is not None):
            raise ValueError
        parts = parsed.path.split("/", 3)
        if len(parts) != 4 or parts[1] != "help" or parts[2] not in SITES["intl"]["langs"]:
            raise ValueError
        lang = parts[2]
        alias = "/" + unquote(parts[3]).rstrip("/").removesuffix(".md")
        if (alias == "/" or any(p in ("", ".", "..") for p in alias[1:].split("/"))
                or any(ord(c) < 32 or c == "\\" for c in alias)):
            raise ValueError
    except ValueError:
        raise _UsageError("ERROR: an international document URL must use HTTPS and "
                          "www.alibabacloud.com/help/{lang}/{document}, with a supported language.") from None
    path = quote(f"/help/{lang}{alias}", safe="/-._~")
    canonical = urlunsplit(("https", SITES["intl"]["result_host"], path, "", ""))
    return lang, alias, canonical


def _fetch_intl_doc(lang: str, alias: str) -> tuple[str, int]:
    params = {"alias": alias, "website": "intl", "language": lang}
    text = fetch(DOC_DETAIL_API["intl"] + "?" + urlencode(params),
                 max_bytes=DOC_MAX_BYTES, allow_redirects=False)
    if _is_err(text):
        if text.startswith("[HTTP 3") or text.startswith("[HTTP 404]"):
            print("WARN[doc-moved]: the international document moved or does not exist; "
                  "use search/list-docs on the same site to find its current URL", file=sys.stderr)
            return "", 1
        print("ERROR: the international document-detail request failed", file=sys.stderr)
        return "", 2
    if len(text.encode("utf-8", errors="replace")) >= DOC_MAX_BYTES:
        print("WARN[oversize]: the international document-detail response exceeded the size limit", file=sys.stderr)
        return "", 2
    try:
        response = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        print("WARN[schema-drift]: the international document-detail endpoint returned non-JSON content", file=sys.stderr)
        return "", 2
    if not isinstance(response, dict):
        print("WARN[schema-drift]: the international document-detail response is not an object", file=sys.stderr)
        return "", 2
    code = str(response.get("code"))
    if code in ("302", "404"):
        print("WARN[doc-moved]: the international document moved or does not exist; "
              "use search/list-docs on the same site to find its current URL", file=sys.stderr)
        return "", 1
    data = response.get("data")
    if response.get("success") is not True or code != "200" or not isinstance(data, dict):
        print("WARN[schema-drift]: the international document-detail request was not successful", file=sys.stderr)
        return "", 2
    if data.get("website") != "intl" or data.get("language") != lang:
        print("WARN[scope-mismatch]: the international document-detail response has the wrong site or language", file=sys.stderr)
        return "", 2
    returned_url = data.get("url")
    try:
        if not isinstance(returned_url, str) or not returned_url:
            raise ValueError
        returned_lang, returned_alias, _ = _intl_doc_scope(urljoin(DOC_DETAIL_API["intl"], returned_url))
        if returned_lang != lang or returned_alias != alias:
            raise ValueError
    except (ValueError, _UsageError):
        print("WARN[scope-mismatch]: the international document-detail response names a different document", file=sys.stderr)
        return "", 2
    content = data.get("content")
    if not isinstance(content, str):
        print("WARN[schema-drift]: the international document-detail response has no HTML body", file=sys.stderr)
        return "", 2
    if not content.strip():
        print("WARN[empty-doc]: the international document has an empty body", file=sys.stderr)
        return "", 1
    if _looks_like_html(content):
        print("WARN[schema-drift]: the international document-detail body is a full HTML page, not a document fragment", file=sys.stderr)
        return "", 2
    return content, 0


def _fetch_cn_doc(alias: str, lang: str) -> tuple[str, int]:
    """Fetch a China-site document via the document_detail.json API; returns (html_content, rc)."""
    params = {"alias": alias, "website": "cn", "language": lang}
    text = fetch(DOC_DETAIL_API["cn"] + "?" + urlencode(params),
                 max_bytes=DOC_MAX_BYTES, allow_redirects=False)
    if _is_err(text):
        if text.startswith("[HTTP 3") or text.startswith("[HTTP 404]"):
            print("WARN[doc-moved]: the China-site document moved or does not exist; "
                  "use search/list-docs on the same site to find its current URL", file=sys.stderr)
            return "", 1
        print("ERROR: the China-site document-detail request failed", file=sys.stderr)
        return "", 2
    try:
        response = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        print("WARN[schema-drift]: the China-site document-detail endpoint returned non-JSON content", file=sys.stderr)
        return "", 2
    if not isinstance(response, dict):
        print("WARN[schema-drift]: the China-site document-detail response is not an object", file=sys.stderr)
        return "", 2
    code = str(response.get("code"))
    if code in ("302", "404"):
        print("WARN[doc-moved]: the China-site document moved or does not exist; "
              "use search/list-docs on the same site to find its current URL", file=sys.stderr)
        return "", 1
    data = response.get("data")
    if response.get("success") is not True or code != "200" or not isinstance(data, dict):
        print("WARN[schema-drift]: the China-site document-detail request was not successful", file=sys.stderr)
        return "", 2
    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        print("WARN[empty-doc]: the China-site document has an empty body", file=sys.stderr)
        return "", 1
    return content, 0


def _emit_doc(text: str, max_lines: int) -> int:
    """Print a document body, honouring the shared --max-lines cap."""
    if max_lines > 0:
        lines = text.split("\n")
        if len(lines) > max_lines:
            text = "\n".join(lines[:max_lines])
            text += f"\n\n... ({len(lines)} lines in total, first {max_lines} shown)"
            print(f"WARN[line-clipping]: document output clipped to {max_lines} of {len(lines)} lines; "
                  "the remaining lines are not shown", file=sys.stderr)
    print(text)
    return 0


def _html_page_hint(parsed, host: str) -> str:
    """Targeted next step for URLs that are known never to serve a Markdown body."""
    if host == SITES["cn"]["result_host"] and "/document_detail/" in parsed.path:
        return ("this is a legacy document_detail link that cannot be read directly; search the "
                "document title (or the question keywords) on the same site and read the current URL.")
    if host and host != SITES["cn"]["result_host"]:
        if "/notice/" in parsed.path:
            return "this is an announcement page; use notice-search with its keywords and --full instead."
        return ("this is not a Help Center document (marketing, activity or console page); use "
                "trial-search for trial offers, the billing rules for price pages, or search for the "
                "related Help Center document.")
    return ""


# read fetches only first-party China-site doc hosts; www.aliyun.com is accepted solely to
# give the targeted non-document hint and is never fetched.
_CN_READ_HOSTS = frozenset({SITES["cn"]["result_host"], "www.aliyun.com"})


def _cn_doc_scope(url: str):
    """Bound the China-site read path: HTTPS on a first-party host, no user info, sane path."""
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in _CN_READ_HOSTS
                or parsed.port not in (None, 443) or parsed.username is not None
                or parsed.password is not None):
            raise ValueError
        path = parsed.path
        if (not path.startswith("/") or "\\" in path
                or any(ord(c) < 32 for c in path)
                or any(p in (".", "..") for p in path.split("/"))):
            raise ValueError
    except ValueError:
        raise _UsageError("ERROR: read only accepts document URLs on help.aliyun.com or "
                          "www.aliyun.com over HTTPS, without user info or a non-standard port; "
                          "other hosts and local file URLs are never fetched. Use search/list-docs "
                          "to find the official document URL.") from None
    return parsed


def read_doc(args) -> int:
    """Read a document body, routing by the host in the URL.

    help.aliyun.com serves raw Markdown at '<url>.md'; www.alibabacloud.com no longer does and
    its body is fetched from the document-detail endpoint as HTML, then converted to Markdown.

    Returns the process exit code: 0 = body rendered, 1 = the document is dead, moved or empty,
    2 = the request itself failed or the response did not match the requested document.
    """
    url = args.url
    host = _url_host(url)
    if getattr(args, "lang", None):
        print(f"WARN[lang-ignored]: read takes the language from the URL; -L {args.lang} is ignored",
              file=sys.stderr)

    site = (getattr(args, "site", None) or "").strip().lower()
    if site in SITES and host and host != SITES[site]["result_host"]:
        print(f"WARN[site-cross]: --site {site} points at {SITES[site]['result_host']} but the given URL is "
              f"on '{host}'; the URL is read as-is and no cross-site rewriting is performed",
              file=sys.stderr)
    else:
        # The body is read in the URL's site and language whatever -L said, so a later unscoped
        # run that follows this read stays on the corpus the answer came from.
        url_site, url_lang = _url_scope(url)
        if url_site:
            _remember_scope(url_site, url_lang or SITES[url_site]["default_lang"])

    if host == SITES["intl"]["result_host"]:
        lang, alias, canonical = _intl_doc_scope(url)

        # Prefer the .md endpoint (already Markdown, no conversion needed); fall back to the
        # document-detail API when the .md file is unavailable.
        md_url = canonical + ".md" if not canonical.endswith(".md") else canonical
        md_text = fetch(md_url, max_bytes=DOC_MAX_BYTES, allow_redirects=False)
        if not _is_err(md_text) and md_text.strip() and not _looks_like_html(md_text):
            if args.raw:
                return _emit_doc(md_text, args.max_lines)
            text = _convert_html_tables(md_text)
            text = _fold_code_escape_marker(text)
            return _emit_doc(text, args.max_lines)

        content, rc = _fetch_intl_doc(lang, alias)
        if rc != 0:
            print(f"[warning] the international document body could not be read.")
            print(f"URL: {canonical}")
            print("Suggestion: use search/list-docs --site intl to find the current URL of this doc.")
            return rc
        if args.raw:
            return _emit_doc(content, args.max_lines)
        body = _html_to_markdown(content, canonical)
        if not body.strip():
            print(f"[warning] the international document body held no readable content after conversion.")
            print(f"URL: {canonical}")
            print("Suggestion: append --raw to inspect the original HTML fragment.")
            return 1
        return _emit_doc(body, args.max_lines)

    # China site: bound the URL before any fetch, then prefer the .md endpoint; fall back to
    # document_detail.json API + HTML conversion.
    parsed = _cn_doc_scope(url)
    hint = _html_page_hint(parsed, host)
    if hint:
        print("[warning] this URL cannot be read as a Help Center document body.")
        print(f"URL: {url}")
        print(f"Next step: {hint}")
        return 1
    path = parsed.path
    if not path.endswith(".md"):
        md_path = path.rstrip("/") + ".md"
    else:
        md_path = path
    md_url = urlunsplit(parsed._replace(path=md_path, fragment=""))

    text = fetch(md_url, max_bytes=DOC_MAX_BYTES)
    md_ok = not _is_err(text) and text.strip() and not _looks_like_html(text)

    if md_ok:
        if len(text.encode("utf-8", errors="replace")) >= DOC_MAX_BYTES:
            print(f"WARN[oversize]: the document body reached the {DOC_MAX_BYTES // (1024 * 1024)} MB "
                  f"size limit; the output may be incomplete", file=sys.stderr)
        if not args.raw:
            text = _convert_html_tables(text)
            text = _fold_code_escape_marker(text)
        return _emit_doc(text, args.max_lines)

    # .md unavailable: fall back to document_detail.json API
    cn_alias = path.rstrip("/").removesuffix(".md")
    _, url_lang = _url_scope(url)
    lang = url_lang or SITES["cn"]["default_lang"]
    content, rc = _fetch_cn_doc(cn_alias, lang)
    if rc != 0:
        print(f"[warning] the China-site document body could not be read.")
        print(f"URL: {url}")
        print("Suggestion: use search/list-docs --site cn to find the current URL of this doc.")
        return rc
    if args.raw:
        return _emit_doc(content, args.max_lines)
    body = _html_to_markdown(content, url)
    if not body.strip():
        print(f"[warning] the China-site document body held no readable content after conversion.")
        print(f"URL: {url}")
        print("Suggestion: append --raw to inspect the original HTML fragment.")
        return 1
    return _emit_doc(body, args.max_lines)


def read_product_llms(args) -> int:
    """Read a product's raw llms.txt (via the local cache layer, scoped by site and language).

    Returns 0 for an index body, 1 for no usable index, or 2 when the index could not be verified.
    """
    site, lang = _resolve_site_lang(args)
    product = args.product
    text, from_cache = _get_llms_text(product, site, lang)
    if from_cache:
        print(f"INFO: llms.txt served from local cache {_llms_cache_path(product, site, lang)}", file=sys.stderr)
    if not _is_index_corpus(text):
        code = _index_failure_code(text)
        print(f"WARN[{'index-unavailable' if code == 2 else 'no-index'}]: no usable llms.txt "
              f"was returned for '{product}' on the {SITES[site]['label']} ({lang}) "
              f"({_non_corpus_reason(text)}); "
              f"use list-products/search on the same site to check the documentation scope. "
              f"Missing index data does not prove missing documentation.", file=sys.stderr)
        return code

    return _emit_doc(text, args.max_lines)
