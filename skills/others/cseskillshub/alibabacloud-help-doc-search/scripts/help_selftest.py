#!/usr/bin/env python3
"""Offline boundary assertions, run through ALIYUN_HELP_SELFTEST=1.

No network access and no new subcommand: each helper is exercised with a normal, a
boundary and an illegal input, and the guard traces its callers are expected to emit are
asserted too.
"""

from __future__ import annotations

import contextlib
import os
import re
import io

from help_cache import (
    SEARCH_CACHE_DIR,
    _category_cache_key,
    _llms_cache_path,
    search_cache_key,
)
from help_http import (
    _parse_retry_after,
)
from help_llms_index import (
    _INDEX_FUSION_FULL_SCORE,
    _index_hits,
    _index_score,
    _index_scored_hits,
    _index_tokens,
    _merge_scored_scans,
)
from help_llms_index import (
    parse_site_matrix,
)
from help_query import (
    is_precision_query,
    translate_query_for_english,
)
from help_core import (
    INTL_SEARCH_PAGESIZE_DEFAULT,
    INTL_SEARCH_PAGESIZE_MAX,
    INTL_SEARCH_PAGESIZE_MIN,
    LLMS_BASE,
    LLMS_CACHE_DIR,
    MAX_QUERY_LEN,
    SEARCH_LANG_WHITELIST,
    _DOC_ENTRY_RE,
    _MASTER_ENTRY_RE,
    _UsageError,
    _annotate_scope,
    _clamp_page_size,
    _clamp_query,
    _doc_url_regex,
    _extract_items,
    _extract_total,
    _has_cjk,
    _llms_base,
    _master_llms_url,
    _needle,
    _normalize_lang,
    _parse_category_id,
    _path_prefix,
    effective_timeout,
    set_cli_timeout,
    _product_code_from_llms_url,
    _product_code_regexes,
    _product_llms_url,
    _resolve_site_lang,
    _scope_explicit,
    _search_backend,
    _strip_help_prefix,
    _url_host,
    _url_lang_segment,
)
from help_http import (
    _NoRedirectHandler,
    _is_index_corpus,
    _non_corpus_reason,
)
from help_render import (
    _fuse_results,
    _readable_title,
)
from help_search import (
    _discover_category_id,
    _drop_shell_items,
    _post_filter_by_product,
    _search_parse_items,
    _validate_site_purity,
)
from help_search_intl import (
    _catmap_name_matches,
    _detect_degraded_envelope,
)


class _StubArgs:
    """Minimal stand-in for argparse.Namespace; used only by _selftest (no CLI surface added)."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def _selftest() -> int:
    """Offline boundary assertions for every helper the site/language scoping added or changed.

    Triggered by ALIYUN_HELP_SELFTEST=1 instead of a CLI subcommand, so the public command shape
    - and with it every eval command_pattern - stays untouched. No network access, no file write.
    Each helper is exercised with normal, boundary and invalid input; the guard functions are
    contractually required to leave a WARN/INFO trace on stderr, so stderr is captured and echoed
    as evidence rather than being treated as noise.
    Returns 0 when every assertion holds and 1 otherwise.
    """
    passed = 0
    failures = []
    trace = io.StringIO()

    def eq(label, got, want):
        nonlocal passed
        if got == want:
            passed += 1
        else:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    def raises(label, exc, fn, *a, **kw):
        nonlocal passed
        try:
            fn(*a, **kw)
        except exc:
            passed += 1
        except Exception as e:
            failures.append(f"{label}: raised {type(e).__name__} ({e}), want {exc.__name__}")
        else:
            failures.append(f"{label}: returned normally, want {exc.__name__}")

    def raises_msg(label, exc, must_have, must_not_have, fn, *a, **kw):
        """Like raises(), plus assertions on the user-visible message text."""
        nonlocal passed
        try:
            fn(*a, **kw)
        except exc as e:
            text = str(e)
            missing = [s for s in must_have if s not in text]
            leaked = [s for s in must_not_have if s in text]
            if missing or leaked:
                failures.append(f"{label}: message {text!r} missing {missing} leaked {leaked}")
            else:
                passed += 1
        except Exception as e:
            failures.append(f"{label}: raised {type(e).__name__} ({e}), want {exc.__name__}")
        else:
            failures.append(f"{label}: returned normally, want {exc.__name__}")

    with contextlib.redirect_stderr(trace):
        # ---- site dictionary lookup (C1) ----
        eq("path_prefix cn/zh", _path_prefix("cn", "zh"), "/zh/")
        eq("path_prefix intl/en", _path_prefix("intl", "en"), "/help/en/")
        eq("llms_base intl/ja", _llms_base("intl", "ja"), "https://www.alibabacloud.com/help/ja")
        # boundary: the cn/zh master URL must equal the pre-scoping hard-coded constant
        eq("master url cn/zh == legacy", _master_llms_url("cn", "zh"), f"{LLMS_BASE}/llms.txt")
        eq("product url intl/pt-br", _product_llms_url("intl", "pt-br", "oss"),
           "https://www.alibabacloud.com/help/pt-br/oss/llms.txt")
        raises("path_prefix unknown site", KeyError, _path_prefix, "us", "en")

        # ---- product needle (C18) ----
        eq("needle cn/zh", _needle("cn", "zh", "oss"), "/zh/oss/")
        eq("needle intl/en", _needle("intl", "en", "oss"), "/help/en/oss/")
        eq("needle cross-site isolation",
           _needle("cn", "zh", "oss") in "https://www.alibabacloud.com/help/en/oss/cors", False)

        # ---- llms.txt cache path (C17) ----
        eq("cache path default", _llms_cache_path("oss"),
           os.path.join(LLMS_CACHE_DIR, "cn", "zh", "oss.txt"))
        eq("cache path scoped", _llms_cache_path("oss", "intl", "ja"),
           os.path.join(LLMS_CACHE_DIR, "intl", "ja", "oss.txt"))
        eq("cache paths differ per site",
           _llms_cache_path("oss", "cn", "zh") == _llms_cache_path("oss", "intl", "zh"), False)
        # invalid: a separator inside the product code must not create a subdirectory
        eq("cache path escapes separator",
           os.path.basename(_llms_cache_path("product/123.html", "cn", "zh")),
           "product_123.html.txt")

        # ---- categoryId cache key (C19) ----
        eq("cache key cn/zh is bare", _category_cache_key("cn", "zh", "oss"), "oss")
        eq("cache key intl/en", _category_cache_key("intl", "en", "oss"), "intl:en:oss")
        eq("cache key cn/en", _category_cache_key("cn", "en", "oss"), "cn:en:oss")

        # ---- pageSize clamp (S7) ----
        eq("clamp normal", _clamp_page_size(50), 50)
        eq("clamp lower boundary", _clamp_page_size(2), 2)
        eq("clamp below lower", _clamp_page_size(1), INTL_SEARCH_PAGESIZE_MIN)
        eq("clamp upper boundary", _clamp_page_size(200), 200)
        eq("clamp above upper", _clamp_page_size(201), INTL_SEARCH_PAGESIZE_MAX)
        eq("clamp zero", _clamp_page_size(0), INTL_SEARCH_PAGESIZE_MIN)
        eq("clamp None", _clamp_page_size(None), INTL_SEARCH_PAGESIZE_DEFAULT)
        eq("clamp non-numeric", _clamp_page_size("abc"), INTL_SEARCH_PAGESIZE_DEFAULT)

        # ---- query clamp ----
        eq("query normal", _clamp_query("  oss cors  "), "oss cors")
        eq("query boundary", _clamp_query("a" * MAX_QUERY_LEN), "a" * MAX_QUERY_LEN)
        eq("query over-long truncated", _clamp_query("a" * (MAX_QUERY_LEN + 30)), "a" * MAX_QUERY_LEN)
        eq("query empty", _clamp_query(None), "")

        # ---- full-text backend routing / language whitelist (S3) ----
        eq("backend cn/zh", _search_backend("cn", "zh"), "doSearch")
        eq("backend cn/en", _search_backend("cn", "en"), "search_json")
        eq("backend intl/en", _search_backend("intl", "en"), "search_json")
        eq("backend intl/zh", _search_backend("intl", "zh"), "search_json")
        eq("backend intl/ja skipped", _search_backend("intl", "ja"), None)
        eq("backend cn/tc skipped", _search_backend("cn", "tc"), None)
        eq("backend intl/ko skipped", _search_backend("intl", "ko"), None)
        eq("whitelist", sorted(SEARCH_LANG_WHITELIST), ["en", "zh"])

        # ---- language normalization and (site, lang) resolution ----
        eq("normalize pt", _normalize_lang("pt"), "pt-br")
        eq("normalize case and space", _normalize_lang(" PT-BR "), "pt-br")
        eq("normalize zh-CN", _normalize_lang("zh-CN"), "zh")
        eq("normalize unset", _normalize_lang(None), "")
        eq("normalize unknown passthrough", _normalize_lang("xx"), "xx")
        eq("resolve default", _resolve_site_lang(_StubArgs()), ("cn", "zh"))
        eq("resolve lang only en", _resolve_site_lang(_StubArgs(lang="en")), ("intl", "en"))
        eq("resolve lang only ja", _resolve_site_lang(_StubArgs(lang="ja")), ("intl", "ja"))
        eq("resolve site+lang cn/en", _resolve_site_lang(_StubArgs(site="cn", lang="en")), ("cn", "en"))
        eq("resolve site only intl", _resolve_site_lang(_StubArgs(site="intl")), ("intl", "en"))
        eq("resolve pt alias", _resolve_site_lang(_StubArgs(site="intl", lang="pt")), ("intl", "pt-br"))
        eq("resolve bare pt", _resolve_site_lang(_StubArgs(lang="pt")), ("intl", "pt-br"))
        eq("resolve ko falls back", _resolve_site_lang(_StubArgs(lang="ko")), ("intl", "en"))
        raises("resolve unsupported lang", _UsageError, _resolve_site_lang, _StubArgs(lang="xx"))
        raises("resolve cn/ja", _UsageError, _resolve_site_lang, _StubArgs(site="cn", lang="ja"))
        raises("resolve unknown site", _UsageError, _resolve_site_lang, _StubArgs(site="us"))
        # The usage message must list both supported-language sets, and must name a site only
        # when the caller actually passed --site (otherwise it would advertise an inferred flag).
        raises_msg("usage msg without explicit site", _UsageError,
                   ["unsupported --lang 'xx'", "for cn: zh, en",
                    "for intl: en, zh, tc, ja, id, pt-br, fr"],
                   ["--site "], _resolve_site_lang, _StubArgs(lang="xx"))
        raises_msg("usage msg with explicit site", _UsageError,
                   ["unsupported --lang 'xx' for --site cn", "for intl: en, zh, tc, ja, id, pt-br, fr"],
                   [], _resolve_site_lang, _StubArgs(site="cn", lang="xx"))
        raises_msg("usage msg site/lang mismatch", _UsageError,
                   ["--lang 'ja' for --site cn", "for cn: zh, en"],
                   [], _resolve_site_lang, _StubArgs(site="cn", lang="ja"))

        # ---- URL host / language segment (S1, S2) ----
        eq("host cn", _url_host("https://help.aliyun.com/zh/oss/x"), "help.aliyun.com")
        eq("host case folded", _url_host("https://WWW.AlibabaCloud.COM/help/en/oss"),
           "www.alibabacloud.com")
        eq("host unparsable", _url_host("://bad"), "")
        eq("lang segment cn", _url_lang_segment("https://help.aliyun.com/zh/oss/x", "cn"), "zh")
        eq("lang segment intl", _url_lang_segment("https://www.alibabacloud.com/help/en/oss/x", "intl"), "en")
        # boundary: the legacy document_detail shape carries no language segment at all
        eq("lang segment absent",
           _url_lang_segment("https://help.aliyun.com/document_detail/123.html", "cn"), "")
        eq("lang segment foreign shape",
           _url_lang_segment("https://www.alibabacloud.com/product/oss", "intl"), "")
        eq("lang segment known unsupported code",
           _url_lang_segment("https://www.alibabacloud.com/help/ko/oss/x", "intl"), "ko")

        # ---- site purity + language guard (S1, S2) ----
        mixed = [{"url": "https://www.alibabacloud.com/help/en/oss/a"},
                 {"url": "https://help.aliyun.com/zh/oss/b"},
                 {"url": "https://www.alibabacloud.com/help/zh/oss/c"},
                 {"url": "https://www.alibabacloud.com/help/en/oss/d"}]
        eq("purity keeps matching", len(_validate_site_purity(mixed, "intl", "en")), 2)
        eq("purity legacy url kept", len(_validate_site_purity(
            [{"url": "https://help.aliyun.com/document_detail/9.html"}], "cn", "zh")), 1)
        eq("purity empty input", _validate_site_purity([], "cn", "zh"), [])
        eq("purity no cross-site leak",
           _validate_site_purity([{"url": "https://help.aliyun.com/zh/oss/b"}], "intl", "en"), [])

        # ---- empty-shell item guard (S8) ----
        shells = [{"url": "https://www.alibabacloud.com/help/en/oss/a", "content": "c"},
                  {"url": "https://www.alibabacloud.com/help/en/oss/b", "content": ""},
                  {"url": "", "content": "c"},
                  {"content": "c"},
                  "not-a-dict"]
        eq("shell drop strict", len(_drop_shell_items(shells, require_content=True)), 1)
        eq("shell drop lenient", len(_drop_shell_items(shells, require_content=False)), 2)
        eq("shell drop empty input", _drop_shell_items([], True), [])

        # ---- degraded envelope detection (S9 / C26) ----
        env_b = {"success": True, "data": {"categoryMap": {"category_id": [{"id": 1, "name": "n"}]},
                                           "documents": {"data": [{"url": "u", "content": "c"}],
                                                         "pageNum": 1, "pageSize": 20,
                                                         "totalCount": 1}}}
        eq("envelope B accepted", _detect_degraded_envelope(env_b, "search_json", 20, 1), False)
        # boundary: a genuine zero-result answer is field-identical to envelope C except that the
        # server echoes the requested paging values back - the only usable discriminator
        env_empty = {"success": True, "data": {"categoryMap": {},
                                               "documents": {"pageNum": 1, "pageSize": 20,
                                                             "totalCount": 0}}}
        eq("real empty result accepted", _detect_degraded_envelope(env_empty, "search_json", 20, 1), False)
        eq("envelope C detected", _detect_degraded_envelope(env_empty, "search_json", 50, 1), True)
        env_d = {"success": True, "code": 200, "data": {"documents": {"data": []}, "products": []}}
        eq("envelope D detected", _detect_degraded_envelope(env_d, "search_json", 20, 1), True)
        eq("envelope pageNum mismatch", _detect_degraded_envelope(env_b, "search_json", 20, 2), True)
        eq("envelope no data object", _detect_degraded_envelope({"success": True}, "search_json", 20, 1), True)
        eq("doSearch never inspected", _detect_degraded_envelope({"data": {"info": []}}, "doSearch", 0, 1), False)

        # ---- result path extraction (C16) ----
        dosearch = {"data": {"info": [{"url": "u"}], "totalCount": 7}}
        eq("items doSearch", len(_extract_items(dosearch, "doSearch")), 1)
        eq("total doSearch", _extract_total(dosearch, "doSearch"), 7)
        eq("items search_json", len(_extract_items(env_b, "search_json")), 1)
        eq("total search_json", _extract_total(env_b, "search_json"), 1)
        eq("items wrong path", _extract_items(dosearch, "search_json"), [])
        eq("items None input", _extract_items(None, "doSearch"), [])
        eq("total non-numeric", _extract_total({"data": {"totalCount": "abc"}}, "doSearch"), 0)
        eq("total bool", _extract_total({"data": {"totalCount": True}}, "doSearch"), 0)
        eq("total negative", _extract_total({"data": {"totalCount": -5}}, "doSearch"), 0)

        # ---- 'help@@' prefix stripping (C22) ----
        eq("strip prefix en", _strip_help_prefix("help@@Object Storage Service"), "Object Storage Service")
        eq("strip prefix cn", _strip_help_prefix("help@@\u5bf9\u8c61\u5b58\u50a8"), "\u5bf9\u8c61\u5b58\u50a8")
        eq("strip no prefix", _strip_help_prefix("OSS"), "OSS")
        eq("strip multi", _strip_help_prefix("a@@b@@c"), "c")
        eq("strip None", _strip_help_prefix(None), "")

        # ---- non-corpus index bodies: the three HTTP 200 shapes both portals serve for a dead slug ----
        eq("corpus accepted", _is_index_corpus("# OSS\n\n- [What is OSS?](https://x/zh/oss/a.md): d\n"), True)
        eq("corpus empty rejected", _is_index_corpus(""), False)
        eq("corpus blank rejected", _is_index_corpus("   \n\t\n"), False)
        eq("corpus error marker rejected", _is_index_corpus("[HTTP 404] Not Found"), False)
        eq("corpus html rejected",
           _is_index_corpus("\n\n<!DOCTYPE html>\n<html>\n<head>"), False)
        eq("corpus placeholder rejected",
           _is_index_corpus("Sorry, this product does not have LLMS content yet.\n"), False)
        eq("corpus placeholder case-insensitive",
           _is_index_corpus("sorry, THIS product does not have llms content yet."), False)
        eq("reason placeholder",
           _non_corpus_reason("Sorry, this product does not have LLMS content yet."),
           "HTTP 200 with the 'no LLMS content yet' placeholder instead of an index")
        eq("reason html",
           _non_corpus_reason("<!DOCTYPE html><html>"),
           "HTTP 200 with an HTML interstitial page instead of an index (rate limiting)")
        eq("reason empty", _non_corpus_reason("  "), "HTTP 200 with an empty body")
        eq("reason healthy corpus", _non_corpus_reason("# OSS\n"), "unusable body")
        eq("strip non-string", _strip_help_prefix(31815), "")

        # ---- CJK detection (S12) ----
        eq("cjk chinese", _has_cjk("\u5b58\u50a8\u8d39\u7528"), True)
        eq("cjk japanese", _has_cjk("\u30aa\u30d6\u30b8\u30a7\u30af\u30c8"), True)
        eq("cjk mixed boundary", _has_cjk("OSS \u5bf9\u8c61"), True)
        eq("cjk english", _has_cjk("object storage"), False)
        eq("cjk empty", _has_cjk(""), False)
        eq("cjk None", _has_cjk(None), False)

        # ---- scope annotation (C11) ----
        eq("scope implicit", _scope_explicit(_StubArgs()), False)
        eq("scope explicit site", _scope_explicit(_StubArgs(site="intl")), True)
        eq("scope explicit lang", _scope_explicit(_StubArgs(lang="ja")), True)
        eq("scope blank strings", _scope_explicit(_StubArgs(site="  ", lang="")), False)
        tagged = _annotate_scope([{"url": "u"}, "not-a-dict"], "intl", "en")
        eq("annotate tags dicts", tagged[0], {"url": "u", "site": "intl", "lang": "en"})
        eq("annotate skips non-dicts", tagged[1], "not-a-dict")

        # ---- index-leg regexes (C20) ----
        legacy = re.compile(r"\((https://help\.aliyun\.com/zh/[^)]+/llms\.txt)\)")
        eq("doc url regex cn/zh == legacy", _doc_url_regex("cn", "zh").pattern, legacy.pattern)
        master = ("see [OSS](https://www.alibabacloud.com/help/en/oss/llms.txt) and "
                  "[ECS](https://help.aliyun.com/zh/ecs/llms.txt)")
        eq("doc url regex intl only", _doc_url_regex("intl", "en").findall(master),
           ["https://www.alibabacloud.com/help/en/oss/llms.txt"])
        html_re, dd_re, slug_re = _product_code_regexes("cn", "zh")
        eq("slug regex cn/zh == legacy", slug_re.pattern, r"/zh/([^/]+)/llms\.txt")
        eq("product html regex", html_re.search("/zh/product/123.html/llms.txt").group(1), "123")
        eq("document_detail regex",
           dd_re.search("/zh/document_detail/2590669.html/llms.txt").group(1),
           "document_detail/2590669.html")
        intl_html_re, intl_dd_re, intl_slug_re = _product_code_regexes("intl", "en")
        eq("intl product html regex",
           intl_html_re.search("/help/en/product/123.html/llms.txt").group(1), "123")
        eq("intl slug regex", intl_slug_re.search("/help/en/oss/llms.txt").group(1), "oss")
        eq("intl slug regex rejects cn", intl_slug_re.search("/zh/oss/llms.txt"), None)
        eq("intl document_detail regex",
           intl_dd_re.search("/help/en/document_detail/2590669.html/llms.txt").group(1),
           "document_detail/2590669.html")

        # ---- product code extraction from a master URL (A4/A5: all three shapes) ----
        # normal: the shapes the cn/zh master actually uses (218 slug / 64 product-html / 178 dd)
        eq("code from slug url",
           _product_code_from_llms_url("https://help.aliyun.com/zh/oss/llms.txt", "cn", "zh"),
           "oss")
        eq("code from product-html url",
           _product_code_from_llms_url("https://help.aliyun.com/zh/product/435019.html/llms.txt",
                                       "cn", "zh"),
           "product/435019.html")
        eq("code from document_detail url",
           _product_code_from_llms_url(
               "https://help.aliyun.com/zh/document_detail/2590669.html/llms.txt", "cn", "zh"),
           "document_detail/2590669.html")
        # boundary: the extracted code must rebuild exactly the URL it came from, and must not
        # collide in the cache file name (the '/' is escaped by _llms_cache_path)
        _dd_code = _product_code_from_llms_url(
            "https://help.aliyun.com/zh/document_detail/2590669.html/llms.txt", "cn", "zh")
        eq("code round-trips to url",
           _product_llms_url("cn", "zh", _dd_code),
           "https://help.aliyun.com/zh/document_detail/2590669.html/llms.txt")
        eq("code cache path is one flat file",
           os.path.basename(_llms_cache_path(_dd_code, "cn", "zh")),
           "document_detail_2590669.html.txt")
        eq("intl needle for a document_detail code",
           _needle("intl", "en", _dd_code), "/help/en/document_detail/2590669.html/")
        # invalid: a cross-site link and the master preamble entry are both 'not a product here'
        eq("cross-site url yields no code",
           _product_code_from_llms_url("https://www.alibabacloud.com/help/en/oss/llms.txt",
                                       "cn", "zh"), "")
        eq("master preamble link yields no code",
           _product_code_from_llms_url("https://help.aliyun.com/zh/llms.txt", "cn", "zh"), "")

        # ---- entry regexes: the ': summary' part is optional (A17/F5) ----
        _sample = ("- [导航节点](https://help.aliyun.com/zh/oss/user-guide.md)\n"
                   "- [有摘要条目](https://help.aliyun.com/zh/oss/limits.md): 限制与性能指标\n")
        eq("doc entries without a summary are kept",
           _DOC_ENTRY_RE.findall(_sample),
           [("导航节点", "https://help.aliyun.com/zh/oss/user-guide.md", ""),
            ("有摘要条目", "https://help.aliyun.com/zh/oss/limits.md", "限制与性能指标")])
        eq("master entries without a summary are kept",
           len(_MASTER_ENTRY_RE.findall("- [X](https://help.aliyun.com/zh/x/llms.txt)\n")), 1)
        # invalid: a non-entry line and a link that is not a .md document are never parsed as docs
        eq("plain text line is not an entry", _DOC_ENTRY_RE.findall("- 一个普通列表项\n"), [])
        eq("html link is not a doc entry",
           _DOC_ENTRY_RE.findall("- [X](https://help.aliyun.com/zh/x.html): d\n"), [])
        # the exact defect this guard pins: match() answers None (not '') for a group that did not
        # participate, so a summary-less line used to raise TypeError while rendering the catalog
        _sum_less = _DOC_ENTRY_RE.match("- [导航节点](https://help.aliyun.com/zh/oss/user-guide.md)")
        eq("match reports an absent summary as None", _sum_less.group(3), None)
        eq("coerced summary renders as empty", (_sum_less.group(3) or "")[:80], "")

        # ---- categoryMap name gate (C25) ----
        eq("catmap initials", _catmap_name_matches("oss", "Object Storage Service"), True)
        eq("catmap prefixed", _catmap_name_matches("oss", "help@@\u5bf9\u8c61\u5b58\u50a8 OSS"), True)
        eq("catmap hyphen slug", _catmap_name_matches("security-center", "Security Center"), True)
        eq("catmap alias sas", _catmap_name_matches("sas", "Security Center"), True)
        eq("catmap alias alb", _catmap_name_matches("alb", "Server Load Balancer"), True)
        eq("catmap synonym", _catmap_name_matches("oss", "\u5bf9\u8c61\u5b58\u50a8"), True)
        # invalid: the measured false positive the gate exists to reject
        eq("catmap rejects wrong product", _catmap_name_matches("oss", "ApsaraDB RDS"), False)
        eq("catmap rejects empty slug", _catmap_name_matches("", "Object Storage"), False)
        eq("catmap rejects empty name", _catmap_name_matches("oss", ""), False)
        eq("catmap rejects one char", _catmap_name_matches("o", "Object Storage"), False)

        # ---- categoryId parsing and mode-vote discovery ----
        eq("parse int", _parse_category_id(31815), 31815)
        eq("parse prefixed", _parse_category_id("help@@31815"), 31815)
        eq("parse zero", _parse_category_id(0), None)
        eq("parse bool", _parse_category_id(True), None)
        eq("parse None", _parse_category_id(None), None)
        eq("parse non-numeric", _parse_category_id("abc"), None)
        votes = [{"url": "https://www.alibabacloud.com/help/en/oss/a", "categoryId": 31815},
                 {"url": "https://www.alibabacloud.com/help/en/oss/b", "categoryId": "help@@31815"},
                 {"url": "https://www.alibabacloud.com/help/en/ecs/c", "categoryId": 25365}]
        eq("discover mode", _discover_category_id(votes, "oss", "intl", "en"), 31815)
        eq("discover single vote rejected",
           _discover_category_id([votes[0], votes[2]], "oss", "intl", "en"), None)
        eq("discover empty", _discover_category_id([], "oss", "intl", "en"), None)
        eq("discover cross-site rejected", _discover_category_id(votes, "oss", "cn", "zh"), None)
        eq("post filter keeps needle", len(_post_filter_by_product(votes, "oss", "intl", "en")), 2)
        eq("post filter cross-site empty", _post_filter_by_product(votes, "oss", "cn", "zh"), [])

        # ---- S13: the redirect handler must never follow ----
        eq("no redirect",
           _NoRedirectHandler().redirect_request(None, None, 302, "Found", {}, "https://x"), None)

        # ---- readable title fallback chain (C22) ----
        eq("title plain", _readable_title({"title": "CORS"}), "CORS")
        eq("title strips suffix", _readable_title({"title": "CORS | Object Storage"}), "CORS")
        eq("title strips highlight", _readable_title({"title": "<em>cors</em> sharing"}), "cors sharing")
        eq("title numeric falls back", _readable_title(
            {"title": "2024-12345678", "categoryName": "help@@Object Storage Service"}),
            "Object Storage Service")
        eq("title numeric no fallback", _readable_title({"title": "2024-12345678"}), "2024-12345678")
        eq("title missing", _readable_title({}), "")

        # ---- parse items: per-backend product extraction (C21) ----
        sj_item = {"url": "https://www.alibabacloud.com/help/en/oss/developer-reference/cors-11",
                   "title": "<em>cors</em>", "content": "cross-origin",
                   "categoryName": "help@@Object Storage Service"}
        rec = _search_parse_items([sj_item], False, "intl", "en", "search_json")[0]
        eq("parse search_json product", rec["product"], "Object Storage Service")
        eq("parse search_json has no updated", "updated" in rec, False)
        do_item = {"url": "https://help.aliyun.com/zh/oss/a", "title": "\u5bf9\u8c61\u5b58\u50a8",
                   "content": "c", "productName": "\u5bf9\u8c61\u5b58\u50a8",
                   "categoryId": "help@@31815", "gmtModifiedOrigin": 1700000000000}
        rec2 = _search_parse_items([do_item], True, "cn", "zh", "doSearch")[0]
        eq("parse doSearch product", rec2["product"], "\u5bf9\u8c61\u5b58\u50a8")
        eq("parse doSearch updated", rec2.get("updated"), "2023-11-14")
        eq("parse categoryId passthrough", rec2["categoryId"], "help@@31815")
        # invalid: the URL fallback regex must stay site-scoped
        eq("parse url fallback intl", _search_parse_items(
            [{"url": "https://www.alibabacloud.com/help/en/oss/x", "title": "t", "content": "c"}],
            False, "intl", "en", "search_json")[0]["product"], "oss")
        eq("parse url fallback cn", _search_parse_items(
            [{"url": "https://help.aliyun.com/zh/oss/x", "title": "t", "content": "c"}],
            False, "cn", "zh", "doSearch")[0]["product"], "oss")
        eq("parse non-dict skipped", _search_parse_items(["x"], False, "cn", "zh"), [])

        # ---- index-leg relevance scoring (F3) ----
        # normal: an exact title hit outranks partial coverage, coverage outrans summary coverage
        exact = _index_score("\u4f20\u8f93\u52a0\u901f", "\u4f20\u8f93\u52a0\u901f\u57df\u540d", "x")
        partial = _index_score("\u4f20\u8f93\u52a0\u901f", "\u4f20\u8f93\u52a0\u901f", "")
        cover_title = _index_score("\u4ec0\u4e48\u662f\u4f20\u8f93\u52a0\u901f", "\u4f20\u8f93\u52a0\u901f\u6982\u8ff0", "")
        cover_desc = _index_score("\u4ec0\u4e48\u662f\u4f20\u8f93\u52a0\u901f", "\u57df\u540d", "\u4f20\u8f93\u52a0\u901f")
        eq("score exact beats coverage", exact > cover_title, True)
        eq("score title coverage beats summary coverage", cover_title > cover_desc, True)
        eq("score exact title has summary bonus", exact > partial, True)
        # boundary: single character query, and a query made only of stop words
        eq("score single char", _index_score("x", "x y", "") > 0, True)
        eq("score stop words only", _index_score("the of and", "the docs", "of"), 0.0)
        eq("score no match", _index_score("bucket", "snapshot", ""), 0.0)
        eq("score empty query", _index_score("", "", ""), 0.0)
        # illegal inputs: None must not raise anywhere on this path
        eq("tokens None", _index_tokens(None), [])
        eq("score None inputs", _index_score(None, None, None), 0.0)
        toks = _index_tokens("cross region")
        eq("tokens latin words", toks, ["cross", "region"])
        eq("tokens cjk bigrams", _index_tokens("\u4f20\u8f93\u52a0\u901f"),
           ["\u4f20\u8f93", "\u8f93\u52a0", "\u52a0\u901f"])
        eq("tokens drop stop words", _index_tokens("how to"), [])
        sample = ("- [CDN \u52a0\u901f](https://x/a.md): \u8de8\u57df\u8bbf\u95ee\u914d\u7f6e\u8be6\u60c5\n"
                  "- [\u8de8\u57df\u8bbf\u95ee\u603b\u7ed3](https://x/b.md)\n"
                  "- [\u5b89\u5168\u7ec4](https://x/c.md): \u65e0\u5173\n")
        hits = _index_hits("oss", sample, "\u8de8\u57df\u8bbf\u95ee")
        # a title that names the query outranks an entry that only mentions it in the summary
        eq("hits ordered by relevance", [h["title"] for h in hits][0], "\u8de8\u57df\u8bbf\u95ee\u603b\u7ed3")
        eq("hits keep the record shape", sorted(hits[0]),
           ["desc", "product", "source", "title", "url"])
        eq("hits mark source index", hits[0]["source"], "index")
        eq("hits drop unrelated", len(hits), 2)
        eq("hits empty index", _index_hits("oss", "", "x"), [])

        # ---- cross-product ranking of the unscoped scan (F3 increment) ----
        # The scores used to be thrown away at the product boundary, so an unscoped scan answered
        # in master-index order. Both facts have to hold: scores come back ordered, records do not
        # carry them.
        scored = _index_scored_hits("oss", sample, "\u8de8\u57df\u8bbf\u95ee")
        eq("scored hits are score-record pairs", len(scored[0]), 2)
        eq("scored hits descend", all(a >= b for (a, _x), (b, _y) in zip(scored, scored[1:])), True)
        eq("scored records carry no score field", sorted(scored[0][1]),
           ["desc", "product", "source", "title", "url"])
        eq("scored wrapper matches hits", [r["url"] for r in _index_hits("oss", sample, "\u8de8\u57df\u8bbf\u95ee")],
           [r["url"] for _s, r in scored])
        eq("scored empty index", _index_scored_hits("oss", "", "x"), [])
        _rec = lambda prod, title, url: {"product": prod, "title": title, "url": url,
                                         "desc": "", "source": "index"}
        merged = _merge_scored_scans([[(2.0, _rec("a", "weak early", "u1"))],
                                      [],
                                      [(7.5, _rec("z", "exact late", "u2"))]])
        eq("merge ranks across products", [m["title"] for m in merged], ["exact late", "weak early"])
        eq("merge loses no candidate", len(merged), 2)
        eq("merge tolerates empty and None batches",
           len(_merge_scored_scans([[], None, [(1.0, _rec("a", "t", "u"))]])), 1)
        eq("merge keeps catalogue order on a tie",
           [m["product"] for m in _merge_scored_scans([[(5.0, _rec("a", "t1", "x1"))],
                                                       [(5.0, _rec("b", "t2", "x2"))]])], ["a", "b"])
        eq("merge of nothing", _merge_scored_scans([]), [])

        # ---- content-aware fusion (F3 increment) ----
        ft = [{"product": "oss", "title": f"ft{i}", "url": f"http://h/ft{i}.md", "desc": ""}
              for i in range(6)]
        strong = _rec("oss", "exact index hit", "http://h/exact.md")
        weak = _rec("oss", "bigram only", "http://h/weak.md")
        flat = _fuse_results(ft, [strong, weak])
        eq("flat fusion puts both index hits above the tail", [d["title"] for d in flat][:3],
           ["ft0", "exact index hit", "bigram only"])
        weighted = _fuse_results(ft, [strong, weak],
                                 {"http://h/exact.md": 7.5, "http://h/weak.md": 2.0},
                                 _INDEX_FUSION_FULL_SCORE)
        eq("weighted fusion demotes a bigram-only hit",
           [d["title"] for d in weighted].index("bigram only"),
           4)  # flat fusion parked it at rank 2; scoring moves it behind three full-text entries
        eq("flat fusion overrates a bigram-only hit",
           [d["title"] for d in flat].index("bigram only"), 2)
        # the half-bonus floor: even a near-zero index score keeps the entry above the tail of the
        # full-text list, because the index leg cannot see semantic equivalence and must not be
        # silenced by a document the backend ranked last
        ft10 = [{"product": "ecs", "title": f"f{i}", "url": f"http://h/f{i}.md", "desc": ""}
                for i in range(10)]
        floor_pos = [d["url"] for d in _fuse_results(ft10, [_rec("ecs", "limits", "http://h/l.md")],
                                                    {"http://h/l.md": 0.01},
                                                    _INDEX_FUSION_FULL_SCORE)].index("http://h/l.md")
        eq("the half-bonus floor keeps a weak index hit off the tail", floor_pos, 5)
        # 5.006 beats the six full-text entries scoring 5 or less and loses to the five above 5.006,
        # so an index hit can never be buried by the full-text tail it was fetched alongside.
        eq("a zero index score still beats half the full-text list",
           floor_pos < len(ft10) / 2 + 1, True)
        eq("weighted fusion keeps a title-exact hit near the top",
           [d["title"] for d in weighted][:2], ["ft0", "exact index hit"])
        eq("weighted fusion output shape unchanged", sorted(weighted[0]),
           ["desc", "product", "source", "title", "url"])
        both = _fuse_results(ft[:2], [_rec("oss", "ft1 dup", "http://h/ft1.md"), strong])
        # the full-text title survives the merge, the source flag records the second leg, and a
        # two-leg entry beats a single-leg one
        eq("fusion marks a two-leg entry",
           [(d["title"], d["source"]) for d in both[:2]],
           [("ft1", "both"), ("ft0", "fulltext")])
        eq("a zero reference disables weighting and restores the flat order",
           [d["title"] for d in _fuse_results(ft, [strong, weak],
                                              {"http://h/weak.md": 2.0}, 0.0)][:3],
           [d["title"] for d in flat][:3])
        # a non-empty map that does not know this url must not silently drop its contribution
        eq("an unscored url keeps the flat bonus",
           [d["title"] for d in _fuse_results(ft, [strong],
                                              {"http://h/other.md": 1.0}, _INDEX_FUSION_FULL_SCORE)][1],
           "exact index hit")
        eq("fusion reference covers a title-exact score", _INDEX_FUSION_FULL_SCORE >= 7.5, True)

        # ---- search-result cache key and TTL guard (N8) ----
        params_a = {"keywords": "oss", "pageNum": 1, "pageSize": 20, "website": "intl",
                    "language": "en"}
        params_b = {"language": "en", "pageSize": 20, "website": "intl", "pageNum": 1,
                    "keywords": "oss"}
        eq("cache key ignores parameter order",
           search_cache_key("intl", "en", "search_json", params_a),
           search_cache_key("intl", "en", "search_json", params_b))
        eq("cache key separates sites",
           search_cache_key("cn", "zh", "doSearch", params_a)
           != search_cache_key("intl", "zh", "doSearch", params_a), True)
        eq("cache key separates languages",
           search_cache_key("intl", "en", "search_json", params_a)
           != search_cache_key("intl", "zh", "search_json", params_a), True)
        eq("cache key separates categoryId",
           search_cache_key("intl", "en", "search_json", dict(params_a, categoryId=31815))
           != search_cache_key("intl", "en", "search_json", params_a), True)
        eq("cache key is short hex", bool(re.fullmatch(r"[0-9a-f]{20}",
           search_cache_key("cn", "zh", "doSearch", params_a))), True)
        # boundary / illegal: an empty request still produces a usable distinct key
        eq("cache key empty params", len(search_cache_key("cn", "zh", "doSearch", {})), 20)
        eq("search cache lives outside the skill dir",
           SEARCH_CACHE_DIR.startswith(os.path.expanduser("~")), True)

        # ---- bilingual query vocabulary (F6) ----
        eq("translate maps CORS", translate_query_for_english("OSS \u8de8\u57df\u8bbf\u95ee")[1] >= 1, True)
        eq("translate keeps unmapped words",
           "OSS" in translate_query_for_english("OSS \u8de8\u57df")[0], True)
        eq("translate longest term wins",
           translate_query_for_english("\u7b7e\u540d\u9519\u8bef")[0],
           "signature does not match")
        eq("translate nothing mapped", translate_query_for_english("\u5b8c\u5168\u6ca1\u89c1\u8fc7")[1], 0)
        eq("translate empty", translate_query_for_english(""), ("", 0))
        eq("translate None", translate_query_for_english(None), ("", 0))

        # ---- master site/language matrix display (F10) ----
        matrix_master = ("## \u53ef\u7528\u7ad9\u70b9\u4e0e\u8bed\u8a00\n"
                         "- [\u4e2d\u56fd\u7ad9 (\u4e2d\u6587)](https://help.aliyun.com/zh/llms.txt)\n"
                         "- [\u56fd\u9645\u7ad9 (\u82f1\u6587)](https://www.alibabacloud.com/help/en/llms.txt)\n\n"
                         "## \u4eba\u5de5\u667a\u80fd\n- [PAI](https://help.aliyun.com/zh/pai/llms.txt)\n")
        rows = parse_site_matrix(matrix_master)
        eq("matrix parses the site block only", len(rows), 2)
        eq("matrix keeps urls", rows[0]["url"].endswith("/zh/llms.txt"), True)
        eq("matrix absent yields empty", parse_site_matrix("## Products\n- [X](u)\n"), [])
        eq("matrix None input", parse_site_matrix(None), [])

        # ---- CLI timeout override (N3) ----
        eq("timeout default passes through", effective_timeout(15), 15)
        set_cli_timeout(30)
        eq("timeout override applies", effective_timeout(15), 30)
        set_cli_timeout(0)
        eq("timeout zero restores default", effective_timeout(15), 15)
        set_cli_timeout(-5)
        eq("timeout negative is ignored", effective_timeout(8), 8)
        set_cli_timeout("abc")
        eq("timeout unparsable is ignored", effective_timeout(8), 8)
        set_cli_timeout(None)
        eq("timeout None is ignored", effective_timeout(20), 20)

        # ---- Retry-After parsing (N2) ----
        class _Headers:
            def __init__(self, value):
                self._value = value

            def get(self, _key, default=None):
                return self._value

        eq("retry-after seconds", _parse_retry_after(_Headers("12")), 12.0)
        eq("retry-after absent", _parse_retry_after(_Headers(None)), None)
        eq("retry-after no headers", _parse_retry_after(None), None)
        eq("retry-after garbage", _parse_retry_after(_Headers("Wed, 21 Oct")), None)
        eq("retry-after negative", _parse_retry_after(_Headers("-3")), None)

        # ---- precision-query detection for the boundary hint (F7) ----
        eq("precision CamelCase code", is_precision_query("InvalidAccessKeyId.NotFound"), True)
        eq("precision numeric code", is_precision_query("0003-00001104"), True)
        eq("precision quota wording", is_precision_query("OSS bucket quota limits"), True)
        eq("precision plain doc question", is_precision_query("\u5feb\u7167 \u81ea\u5b9a\u4e49\u955c\u50cf"), False)
        eq("precision all-caps abbreviation", is_precision_query("KMS"), False)
        eq("precision empty", is_precision_query(""), False)
        eq("precision None", is_precision_query(None), False)

    trace_lines = [line for line in trace.getvalue().splitlines() if line.strip()]
    print(f"_selftest: {passed} assertions passed, {len(failures)} failed, "
          f"{len(trace_lines)} expected guard trace line(s) emitted on stderr")
    for line in trace_lines:
        print(f"  trace| {line}")
    for line in failures:
        print(f"  FAIL: {line}")
    print("SELFTEST RESULT: PASS" if not failures else "SELFTEST RESULT: FAIL")
    return 1 if failures else 0
