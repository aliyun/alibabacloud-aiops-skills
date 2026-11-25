#!/usr/bin/env python3
"""(site, language) scope resolution and the URL algebra built on it.

Every URL the tool fetches is constructed here from the site matrix in help_const, and every
guard that decides whether a returned URL really belongs to the requested scope lives here too.
The two sites document different products, regions and prices, so a scope is resolved once and
never crossed afterwards.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse

from help_const import (
    DEFAULT_SITE,
    LANG_ALIASES,
    SCOPE_CACHE_PATH,
    SITES,
    UNSUPPORTED_LANGS,
    _KNOWN_LANG_SEGMENTS,
    _UsageError,
)


def _remembered_scope() -> tuple:
    """The (site, lang) this installation last resolved, or ('', '') when none is usable.

    The file is tiny and read on every unscoped run, so there is no in-process memo to go stale
    between two commands of one session.
    """
    try:
        with open(SCOPE_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return "", ""
    if not isinstance(data, dict):
        return "", ""
    site, lang = data.get("site"), data.get("lang")
    if not isinstance(site, str) or not isinstance(lang, str) or site not in SITES:
        return "", ""
    return (site, lang) if lang in SITES[site]["langs"] else ("", "")


def _remember_scope(site: str, lang: str) -> None:
    """Persist an explicitly resolved (site, lang) atomically; a write failure only WARNs."""
    try:
        os.makedirs(os.path.dirname(SCOPE_CACHE_PATH), exist_ok=True)
        tmp_path = f"{SCOPE_CACHE_PATH}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"site": site, "lang": lang}, f)
        os.replace(tmp_path, SCOPE_CACHE_PATH)
    except OSError as e:
        print(f"WARN[scope-cache]: failed to remember the site and language ({e}); "
              f"the next run falls back to the default scope", file=sys.stderr)


def show_scope(args) -> int:
    """Print the remembered scope without changing it, so a new session can adopt it first."""
    site, lang = _remembered_scope()
    if not site:
        print("none: no remembered scope")
        return 1
    print(json.dumps({"site": site, "lang": lang}))
    return 0


def _apply_remembered_scope(args) -> None:
    """Fill an unscoped invocation from the remembered scope; explicit flags always win.

    Only an invocation without either flag is filled, so an explicit --lang still infers
    through _infer_site. Legs that read args.site/args.lang directly (announcements, skills,
    trials) now inherit the same scope instead of silently resetting to the default. An
    unscoped invocation sends no flag at all, so the scope-keyed caches need no change.
    """
    if _scope_explicit(args):
        return
    site, lang = _remembered_scope()
    if not site:
        return
    args.site = site
    if hasattr(args, "lang"):
        args.lang = lang
    print(f"INFO: reusing the previously confirmed scope ({site}, {lang}); "
          f"pass --site/--lang to switch", file=sys.stderr)


def _normalize_lang(raw) -> str:
    """Normalize a --lang value: strip, lowercase, apply LANG_ALIASES; return '' when unset.

    Normalization happens before any request so that 'pt' becomes the real code 'pt-br'
    ('pt' would 302-redirect to an empty body) and 'zh-CN'/'EN' collapse to 'zh'/'en'.
    """
    if not raw:
        return ""
    lang = str(raw).strip().lower()
    return LANG_ALIASES.get(lang, lang)


def _infer_site(lang: str) -> str:
    """Infer the site from an explicit --lang when --site was omitted.

    'zh' keeps the historical default (cn) so an unchanged invocation behaves as before;
    'en' selects the international site, whose English corpus is the one with a real
    full-text leg; tc/ja/id/pt-br/fr exist only on the international site.
    """
    if lang == "en":
        return "intl"
    if lang in SITES["cn"]["langs"]:
        return "cn"
    return "intl"


def _resolve_site_lang(args) -> tuple:
    """Resolve and validate the (site, lang) pair from CLI arguments.

    Returns (site, lang). Raises _UsageError for an unknown --site/--lang value or for a
    language the target site does not host (no network request is issued in that case).
    A language that exists in the front end but has no corpus of its own (ko/de/es/th/vi/
    tr/ru/it) is not an error: it WARNs and falls back to the site default language.
    An explicit scope is remembered for later unscoped runs; an unscoped one uses the
    remembered scope when there is one, and the default scope otherwise.
    """
    site = (getattr(args, "site", None) or "").strip().lower() or DEFAULT_SITE
    if site not in SITES:
        raise _UsageError(
            f"ERROR: invalid --site value '{site}'. Supported values: {', '.join(SITES)}.")
    raw_lang = getattr(args, "lang", None)
    raw_lower = str(raw_lang).strip().lower() if raw_lang else ""
    lang = _normalize_lang(raw_lang)
    site_explicit = bool((getattr(args, "site", None) or "").strip())
    if not lang:
        if site_explicit:
            return _confirm_scope(site)
        remembered = _remembered_scope()
        if not remembered[0]:
            return site, SITES[site]["default_lang"]
        site, lang = remembered
        print(f"INFO: reusing the previously confirmed scope ({site}, {lang}); "
              f"pass --site/--lang to switch", file=sys.stderr)
        return site, lang
    if lang != raw_lower:
        # Traced, never an error: 'pt' is the common mistake for the real code 'pt-br' (the bare
        # form 302-redirects to an empty body), and 'zh-CN'/'EN' collapse to 'zh'/'en'.
        print(f"INFO: language '{raw_lower}' normalized to '{lang}'", file=sys.stderr)
    if not site_explicit:
        site = _infer_site(lang)
    supported = SITES[site]["langs"]
    if lang in supported:
        return _confirm_scope(site, lang)
    if lang in UNSUPPORTED_LANGS:
        fallback = SITES[site]["default_lang"]
        print(f"WARN[lang-fallback]: language '{lang}' is not supported (supported: {', '.join(supported)}); "
              f"falling back to '{fallback}'. Results are in {fallback}, not {lang}.",
              file=sys.stderr)
        return _confirm_scope(site, fallback)
    # Name the site only when the user actually passed --site; otherwise the site was inferred
    # from --lang and quoting it would claim a flag the user never wrote.
    scope = f" for --site {site}" if site_explicit else ""
    raise _UsageError(
        f"ERROR: unsupported --lang '{lang}'{scope}. "
        f"Supported languages for cn: {', '.join(SITES['cn']['langs'])}. "
        f"Supported languages for intl: {', '.join(SITES['intl']['langs'])}.")


def _llms_base(site: str, lang: str) -> str:
    """Root URL of a site+language llms.txt tree, e.g. https://help.aliyun.com/zh."""
    return SITES[site]["llms_base"].format(lang=lang)


def _path_prefix(site: str, lang: str) -> str:
    """URL path segment preceding a product slug, e.g. '/zh/' (cn) or '/help/en/' (intl)."""
    return SITES[site]["path_prefix"].format(lang=lang)


def _product_llms_url(site: str, lang: str, product: str) -> str:
    """Product-level llms.txt URL of a site+language pair."""
    return f"{_llms_base(site, lang)}/{product}/llms.txt"


def _needle(site: str, lang: str, product: str) -> str:
    """URL substring that identifies a product on a given site+language, e.g. '/zh/oss/'.

    Site-scoped on purpose: the same slug on the two sites is a different corpus, so a
    needle built for one site must never match the other site's URLs.
    """
    return f"{_path_prefix(site, lang)}{product}/"


def _semantic_alias(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.rstrip("/") if re.fullmatch(r"/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*/?", value) else ""


def _url_in_product(url: str, product: str, site: str, lang: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        path = urllib.parse.unquote(parsed.path)
        return (parsed.scheme in ("http", "https")
                and parsed.hostname == SITES[site]["result_host"]
                and not parsed.username and not parsed.password
                and "\\" not in path and "\x00" not in path
                and not any(part in (".", "..") for part in path.split("/"))
                and path.startswith(_needle(site, lang, product)))
    except ValueError:
        return False


def _url_host(url: str) -> str:
    """Lowercase host of a URL ('' when unparsable); used by the site-purity guard S1."""
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _url_lang_segment(url: str, site: str) -> str:
    """Language segment of a result URL on a given site ('' when the shape is unexpected).

    cn shape:   https://help.aliyun.com/{lang}/{product}/...
    intl shape: https://www.alibabacloud.com/help/{lang}/{product}/...
    Used by guard S2 to detect the silent server-side fallback to English.

    The candidate segment is accepted only when it is a known language code: the China site also
    serves the legacy 'https://help.aliyun.com/document_detail/{id}.html' shape (measured 2/119
    items), whose first path segment is not a language. Such an URL carries no evidence
    of a language fallback, so '' means 'no opinion' and S2 keeps the item.
    """
    head, _, _tail = _path_prefix(site, "{lang}").partition("{lang}")
    path = urllib.parse.urlsplit(url).path
    if not path.startswith(head):
        return ""
    rest = path[len(head):]
    if "/" not in rest:
        return ""
    candidate = rest.split("/")[0]
    return candidate if candidate in _KNOWN_LANG_SEGMENTS else ""


def _url_scope(url: str) -> tuple:
    """(site, lang) a document URL belongs to, or ('', '') when it carries no such evidence.

    The URL is the one signal no flag can contradict: a doc read by its URL is read in the
    language of that URL, so confirming it keeps later unscoped runs on the corpus the answer
    actually came from. The legacy cn shape 'help.aliyun.com/document_detail/{id}.html' has no
    language segment and yields the site only.
    """
    host = _url_host(url)
    for site, cfg in SITES.items():
        if host != cfg["result_host"]:
            continue
        lang = _url_lang_segment(url, site)
        return site, lang if lang in cfg["langs"] else ""
    return "", ""


def _strip_help_prefix(value) -> str:
    """Strip the 'help@@' namespace prefix both search backends put on categoryName.

    Returns '' for a missing/non-string value. Without this the customer-facing output
    would read 'help@@Object Storage Service'.
    """
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if "@@" in text:
        text = text.split("@@")[-1].strip()
    return text


# CJK ranges used by guard S12; the check is a plain range test so no segmentation dependency
# is needed (and the ranges are functional retrieval data, not user-facing copy).
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


def _has_cjk(text: str) -> bool:
    """True when the text contains a Chinese/Japanese/Korean character (guard S12)."""
    return bool(_CJK_RE.search(text or ""))


def _remember(args) -> None:
    """Confirm an explicitly scoped invocation that resolves without _resolve_site_lang.

    The search/read/API legs confirm inside their own resolver; legs like announcements,
    trials and skills read args.site themselves, so an invalid explicit value is skipped
    (the leg reports it) rather than cached.
    """
    if not _scope_explicit(args):
        return
    site = (getattr(args, "site", None) or "").strip().lower() or DEFAULT_SITE
    if site not in SITES:
        return
    lang = _normalize_lang(getattr(args, "lang", None))
    if lang and lang not in SITES[site]["langs"]:
        return
    _remember_scope(site, lang or SITES[site]["default_lang"])


def _confirm_scope(site: str, lang: str = "") -> tuple:
    """Remember an explicitly resolved scope and return it unchanged."""
    lang = lang or SITES[site]["default_lang"]
    _remember_scope(site, lang)
    return site, lang


def _scope_explicit(args) -> bool:
    """True when the user passed --site or --lang explicitly.

    Only an explicitly scoped invocation annotates its output with the site and the language:
    a default invocation keeps the unannotated output shape, which predates any scope
    annotation.
    """
    return bool((getattr(args, "site", None) or "").strip()
                or (getattr(args, "lang", None) or "").strip())


def _annotate_scope(records: list, site: str, lang: str) -> list:
    """Tag every output record with its (site, lang) so a result set can never be mistaken for
    the other site's corpus (the two sites document different products, regions and prices)."""
    for rec in records:
        if isinstance(rec, dict):
            rec["site"] = site
            rec["lang"] = lang
    return records


def _normalize_url(url: str) -> str:
    """URL normalization: strip the query/fragment, the .md suffix and the trailing slash, and fold case at path level
    (improves cross-leg dedup robustness)."""
    u = url.split("#", 1)[0].split("?", 1)[0].lower()
    if u.endswith(".md"):
        u = u[:-3]
    return u.rstrip("/")
