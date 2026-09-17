#!/usr/bin/env python3
"""
_doc_lookup.py -- official-doc verification leg for this OSS skill
===================================================================
Read-only enhancement, ZERO cloud API calls, ZERO credentials: this module
only reads public help-center content on help.aliyun.com. It never blocks
the main diagnosis -- any failure degrades to a documented DEGRADED result.

Mechanism (same two-leg design as aliyun-help-search, help-center leg only):
  * index leg : fetch https://help.aliyun.com/zh/oss/llms.txt once, cache it
                at ~/.cache/oss-skill-docs/oss-llms.txt for 3 days (a cache
                hit performs ZERO network requests);
  * body leg  : for the top-3 scored hits only, read the .md body directly
                (1 request per doc, 15 s timeout each, 45 s total budget)
                and take the first non-empty paragraph as the excerpt.

Public API:
  lookup_config_topic(question, skill_topics) -> dict with constant keys
    {"matched": bool,
     "docs": [{"title", "url", "excerpt"}],   # at most 3, .md URLs only
     "source": "llms-index",
     "note": None | "DEGRADED: <reason>"}
The function NEVER raises; the caller attaches the dict to the output JSON
as the doc_verification section.

Compliance: pure standard library (urllib/re/json/os/time); data is fetched
at runtime, no data files are added (platform MUST 1.1.2); index fetch 15 s,
per-body fetch 15 s, body-leg total budget 45 s (platform 7.6.1); only the
help.aliyun.com host is ever requested (URL whitelist).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

INDEX_URL = "https://help.aliyun.com/zh/oss/llms.txt"
ALLOWED_HOST = "help.aliyun.com"
CACHE_PATH = os.path.expanduser("~/.cache/oss-skill-docs/oss-llms.txt")
CACHE_TTL_SECONDS = 3 * 24 * 3600  # 3 days
FETCH_TIMEOUT = 15                 # seconds, index leg and each body fetch
BODY_BUDGET_SECONDS = 45           # total budget of the body leg
MAX_DOCS = 3
EXCERPT_CHARS = 500
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QoderWork/1.0"

# Index entry line: - [title](https://.../*.md): description
_INDEX_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\):\s*(.*)", re.MULTILINE)

# Scenario-specific topic table for the presigned-URL diagnosis skill
# (embedded constant: platform MUST 1.1.2, no data files). Keywords are
# case-insensitive substrings of the customer's original question.
SKILL_TOPICS = [
    {"keywords": ["签名url", "签名连接", "签名链接", "预签名", "签名", "presigned", "sign_url"],
     "hint": "presigned-url"},
    {"keywords": ["ossaccesskeyid", "share link", "分享链接", "共享链接", "分享",
                  "临时访问", "安全", "不安全"],
     "hint": "share-link-security"},
    {"keywords": ["过期", "有效期", "失效", "过期时间", "expired", "expiration"],
     "hint": "url-expiry"},
    {"keywords": ["v4", "v1", "signatureversion", "签名版本", "x-oss-credential", "signaturedoesnotmatch"],
     "hint": "signature-version"},
    # Eval fix PR-5/PR-6: custom-domain and certificate/hotlink wording
    # activates the doc leg (tickets 0001FRR89N / 0005PPPX5W / 0001ZRG446).
    {"keywords": ["域名", "endpoint", "自定义域名", "cname", "绑定域名", "指定域名"],
     "hint": "custom-domain"},
    {"keywords": ["证书", "證書", "ssl", "https", "防盗链", "referer", "防盗鍊"],
     "hint": "domain-security"},
]

# Question-side keyword aliases (eval fix PR-6): SDK function names and
# URL parameter names in a customer question should also activate the
# conceptual signature keywords so the doc leg can surface conceptual
# pages (e.g. 在URL中包含签名) instead of only error-code references.
_KEYWORD_ALIASES = {
    "sign_url": ("签名",),
    "ossaccesskeyid": ("签名",),
}

# Context guards (eval fix PR-6): in an SSL-certificate context the words
# 过期/有效期/失效/到期 refer to the certificate, not the presigned URL;
# the guarded keywords are dropped from the activation set so the doc leg
# does not drift to URL-expiry pages (ticket 0001ZRG446).
_CONTEXT_GUARDS = (
    (("证书", "證書", "ssl"), ("过期", "有效期", "失效", "到期")),
)

# Advisory question signals for the doc-leg drift guard (eval fix PR-6):
# a how-to/safety consult should surface conceptual pages, not error-code
# reference pages (ticket 000EAR5FN7 wording).
_ADVISORY_QUESTION_SIGNALS = (
    "吗", "呢", "怎么", "怎样", "如何", "是否", "能否", "可以", "建议",
    "反驳", "安全", "不安全", "怎么办", "还是", "?", "？",
)

# Error-code reference pages (llms-index titles such as 'OSS 错误
# 0002-00000069 ...' / '02-AUTH-0002-00000117' / 'CNAME 错误 0018-...').
# Numeric prefixes cover both '02-...' (1 digit) and '0002-...' (3 digits)
# error-code families found in the llms index.
_ERROR_DOC_TITLE_RE = re.compile(r"^(oss\s*)?(错误码?|cname 错误|0\d{1,3}-)")


# ---------------------------------------------------------------------------
# Pure helpers (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def _is_err(text: str) -> bool:
    """True when a fetch returned an error marker, not document content."""
    return text.startswith("[HTTP ") or text.startswith("[Error]")


assert _is_err("[HTTP 404] Not Found") is True          # normal: HTTP error
assert _is_err("[Error] timeout") is True               # normal: transport error
assert _is_err("# OSS docs") is False                   # boundary: real content
assert _is_err("") is False                             # invalid: empty body


def _looks_like_html(text: str) -> bool:
    """True when HTTP 200 returned an SPA/HTML page instead of Markdown
    (moved doc / dead slug); such bodies must not feed the excerpt."""
    head = text.lstrip()[:300].lower()
    return head.startswith("<!doctype") or head.startswith("<html") \
        or "<html" in head


assert _looks_like_html("<!doctype html><html>") is True   # normal: SPA page
assert _looks_like_html("  <HTML lang=zh>") is True        # boundary: case+ws
assert _looks_like_html("# 图片处理\n正文") is False         # boundary: markdown
assert _looks_like_html("") is False                       # invalid: empty


def _is_degraded_url(url) -> bool:
    """URL whitelist: only https .md URLs on help.aliyun.com may be fetched.
    Protects the body leg from index poisoning / URL injection."""
    if not isinstance(url, str) or not url:
        return True
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return True
    host = (parts.hostname or "").lower()
    return not (parts.scheme == "https" and host == ALLOWED_HOST
                and url.endswith(".md"))


assert _is_degraded_url("https://help.aliyun.com/zh/oss/user-guide.md") is False  # normal: allowed
assert _is_degraded_url("http://help.aliyun.com/zh/oss/user-guide.md") is True    # boundary: http rejected
assert _is_degraded_url("https://evil.example.com/x.md") is True                  # invalid: foreign host
assert _is_degraded_url("https://help.aliyun.com/zh/oss/page.html") is True       # boundary: non-.md
assert _is_degraded_url("") is True                                               # invalid: empty
assert _is_degraded_url(None) is True                                             # invalid: missing


def _truncate(text, limit: int = EXCERPT_CHARS) -> str:
    """Truncate to at most `limit` Unicode characters ('' for non-str)."""
    if not isinstance(text, str):
        return ""
    return text[:limit]


assert _truncate("abc") == "abc"                       # normal: below limit
assert _truncate("a" * 600) == "a" * 500               # boundary: exact cap
assert len(_truncate("汉" * 600, 500)) == 500          # normal: Unicode chars
assert _truncate("", 10) == ""                         # boundary: empty
assert _truncate(None) == ""                           # invalid: non-str
assert _truncate(123) == ""                            # invalid: wrong type


def _is_error_doc_title(title: str) -> bool:
    """True when an llms-index entry title marks an error-code reference
    page (e.g. 'OSS 错误 0002-00000069 ...', '02-AUTH-0002-00000117')."""
    return bool(_ERROR_DOC_TITLE_RE.match((title or "").strip().lower()))


assert _is_error_doc_title("OSS 错误 0002-00000069 URL 签名已过期") is True   # normal
assert _is_error_doc_title("OSS 错误码 0002-00000039") is True               # normal
assert _is_error_doc_title("02-AUTH-0002-00000117") is True                  # boundary: bare code
assert _is_error_doc_title("CNAME 错误 0018-00000002") is True                # boundary: cname family
assert _is_error_doc_title("在URL中包含签名") is False                        # normal: conceptual
assert _is_error_doc_title("OSS 防盗链") is False                             # boundary: guide page
assert _is_error_doc_title("") is False                                      # invalid: empty


def _is_advisory_question_text(question: str) -> bool:
    """True when the wording looks like a how-to/safety consult rather than
    an error report (used by the doc-leg drift guard)."""
    if not isinstance(question, str):
        return False
    return any(sig in question for sig in _ADVISORY_QUESTION_SIGNALS)


assert _is_advisory_question_text("这个参数安全吗") is True           # normal: zh signal
assert _is_advisory_question_text("如何在OSS配置？") is True           # normal: how-to
assert _is_advisory_question_text("SignatureDoesNotMatch 403") is False  # boundary: error report
assert _is_advisory_question_text("") is False                        # boundary: empty
assert _is_advisory_question_text(None) is False                      # invalid: non-str


def _apply_context_guards(question: str, activated: set) -> set:
    """Drop guarded keywords when their guard context is present (pure).

    Example (ticket 0001ZRG446): 'ssl證書已過期' -- here 过期/到期 describe
    the certificate, so the url-expiry keywords must not drive scoring."""
    q = (question or "").lower()
    for guard_words, guarded in _CONTEXT_GUARDS:
        if any(w in q for w in guard_words):
            activated = activated - set(guarded)
    return activated


assert _apply_context_guards("ssl證書已過期", {"ssl", "證書", "过期"}) == \
    {"ssl", "證書"}                                                     # normal: cert ctx
assert _apply_context_guards("签名url过期了", {"签名", "过期"}) == \
    {"签名", "过期"}                                                   # boundary: no guard ctx
assert _apply_context_guards("", {"过期"}) == {"过期"}                 # boundary: empty question
assert _apply_context_guards(None, set()) == set()                    # invalid: non-str


def _expand_aliases(activated: set) -> set:
    """Add conceptual keywords activated via question-side aliases (pure).

    Only keywords that actually exist in SKILL_TOPICS are added."""
    all_keywords = {kw.lower()
                    for topic in SKILL_TOPICS
                    for kw in (topic or {}).get("keywords", [])}
    for alias_of, aliases in _KEYWORD_ALIASES.items():
        if alias_of in activated:
            activated = activated | {a for a in aliases if a in all_keywords}
    return activated


assert "签名" in _expand_aliases({"sign_url"})                          # normal: sdk fn alias
assert "签名" in _expand_aliases({"ossaccesskeyid"})                   # normal: param alias
assert _expand_aliases({"域名"}) == {"域名"}                           # boundary: no alias
assert _expand_aliases(set()) == set()                                # invalid: empty


def _score_entry(title, desc, activated):
    """Deterministic entry score: 2 points per activated keyword found in
    the title, 1 point per activated keyword found in the description.
    Case-insensitive substring match (same convention as the help search)."""
    if not activated:
        return 0
    t = (title or "").lower()
    d = (desc or "").lower()
    score = 0
    for kw in activated:
        if kw in t:
            score += 2
        if kw in d:
            score += 1
    return score


assert _score_entry("签名URL概述", "使用签名", {"签名"}) == 3        # normal: title+desc
assert _score_entry("签名URL概述", "无关", {"签名"}) == 2            # normal: title only
assert _score_entry("无关标题", "使用签名", {"签名"}) == 1           # normal: desc only
assert _score_entry("无关标题", "无关", {"签名"}) == 0              # boundary: no hit
assert _score_entry("abc", "abc", set()) == 0                       # boundary: empty set
assert _score_entry("", "", {"签名"}) == 0                          # invalid: empty entry
assert _score_entry("SIGN url", "sign", {"sign"}) == 3              # boundary: case-insensitive


def _clean_excerpt(text: str) -> str:
    """Strip Markdown/HTML syntax and collapse blank lines; return the
    first non-empty paragraph truncated to EXCERPT_CHARS ('' when unusable).

    Eval fix PR-11: stray HTML fragments such as '<br />' used to leak
    into the excerpt because only Markdown decorations were stripped;
    inline breaks and stray tags are now removed too."""
    if not isinstance(text, str) or _is_err(text) or _looks_like_html(text):
        return ""
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)       # images
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)   # links -> label
    body = re.sub(r"(?m)^#{1,6}\s.*$", "", body)           # heading lines
    body = re.sub(r"(?m)^\s*>\s?", "", body)               # blockquotes
    body = re.sub(r"<br\s*/?>", " ", body, flags=re.IGNORECASE)  # inline HTML breaks
    body = re.sub(r"<[^>\s][^>]{0,120}", " ", body)       # stray HTML tags
    body = re.sub(r"[#>*`|<>]", " ", body)                   # md decorations
    paragraphs = [re.sub(r"\s+", " ", p).strip()
                  for p in re.split(r"\n\s*\n", body)]
    for para in paragraphs:
        if para:
            return _truncate(para)
    return ""


assert _clean_excerpt("# 标题\n\n第一段正文。") == "第一段正文。"          # normal: first paragraph
assert _clean_excerpt("[链接文字](https://x) 后续") == "链接文字 后续"     # normal: link label kept
assert _clean_excerpt("![alt](https://x/i.png)图后文字") == "图后文字"     # normal: image dropped
assert _clean_excerpt("前文<br />后文继续") == "前文 后文继续"             # normal: PR-11 inline break
assert _clean_excerpt("段落<div class='x'>内容</div>结束") == "段落 内容 结束"  # normal: PR-11 stray tags
assert _clean_excerpt("") == ""                                           # boundary: empty
assert _clean_excerpt(None) == ""                                         # invalid: non-str
assert _clean_excerpt("[HTTP 404] Not Found") == ""                       # invalid: err marker
assert len(_clean_excerpt("字" * 900)) <= EXCERPT_CHARS                   # boundary: capped


# ---------------------------------------------------------------------------
# Network legs (each failure path degrades; nothing here may raise outward)
# ---------------------------------------------------------------------------

def _fetch(url: str) -> str:
    """Fetch a URL as text with the fixed UA and FETCH_TIMEOUT.
    Returns '[HTTP <code>] <reason>' / '[Error] <msg>' markers on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] {e.reason}"
    except Exception as e:  # URLError / timeout / DNS / socket errors
        return f"[Error] {e}"


def _cache_fresh() -> bool:
    """True when the index cache exists and is younger than the TTL."""
    try:
        return time.time() - os.path.getmtime(CACHE_PATH) < CACHE_TTL_SECONDS
    except OSError:
        return False


def _read_cache() -> str:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _write_cache(text: str) -> None:
    """Atomic cache write (tmp file + rename); failures are tolerated."""
    try:
        cache_dir = os.path.dirname(CACHE_PATH)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, CACHE_PATH)
    except OSError:
        pass


def _load_index():
    """Index leg. Returns (entries, note):
      entries -- [{'title','url','desc'}, ...] (empty list on full failure);
      note    -- None | 'DEGRADED: ...' (stale cache is flagged)."""
    text = ""
    note = None
    if _cache_fresh():
        text = _read_cache()  # zero network requests on a cache hit
    if not text.strip():
        fetched = _fetch(INDEX_URL)
        if not _is_err(fetched) and not _looks_like_html(fetched) \
                and fetched.strip():
            text = fetched
            _write_cache(text)
    if not text.strip():
        stale = _read_cache()  # expired cache is better than nothing
        if stale.strip():
            text = stale
            note = "DEGRADED: index fetch failed, stale-cache used"
        else:
            return [], "DEGRADED: offline or index fetch failed"
    entries = [{"title": t, "url": u, "desc": d}
               for t, u, d in _INDEX_RE.findall(text)]
    if not entries:
        return [], "DEGRADED: index parsed zero entries"
    return entries, note


def _body_excerpt(url: str) -> str:
    """Body leg for ONE document: fetch the .md body and return its cleaned
    first paragraph ('' when the fetch/body is unusable)."""
    if _is_degraded_url(url):
        return ""
    text = _fetch(url)
    return _clean_excerpt(text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_config_topic(question, skill_topics) -> dict:
    """Verify a customer question against the official OSS doc index.

    question     -- customer original wording (caller strips whitespace).
    skill_topics -- list of {"keywords": [str,...], "hint": str}; keywords
                    are matched case-insensitively as substrings.

    Never raises; always returns the four-key contract dict.
    """
    def _offline(reason: str):
        print(f"[WARN] doc lookup degraded: {reason}", file=sys.stderr)
        return {"matched": False, "docs": [], "source": "llms-index",
                "note": f"DEGRADED: {reason}"}

    try:
        q = question.strip() if isinstance(question, str) else ""
        topics = skill_topics if isinstance(skill_topics, list) else []
        if not q or not topics:
            return {"matched": False, "docs": [], "source": "llms-index",
                    "note": None}

        # Step 1: activated keywords = topic keywords present in question;
        # then context guards (SSL-certificate wording drops URL-expiry
        # keys) and conceptual aliases (sign_url/ossaccesskeyid -> 签名)
        # so conceptual pages can outscore error-code references.
        activated = set()
        for topic in topics:
            kws = (topic or {}).get("keywords") or []
            for kw in kws:
                if isinstance(kw, str) and kw and kw.lower() in q.lower():
                    activated.add(kw.lower())
        activated = _apply_context_guards(q, activated)
        activated = _expand_aliases(activated)
        if not activated:
            return {"matched": False, "docs": [], "source": "llms-index",
                    "note": None}

        # Step 2: index leg (cached or fetched).
        entries, note = _load_index()
        if not entries:
            return _offline(note.replace("DEGRADED: ", "")
                            if note else "offline or index fetch failed")

        # Step 3: score, stable order (score desc, then index order).
        # Advisory drift guard (eval fix PR-6): a how-to/safety consult
        # should surface conceptual pages, so error-code reference pages
        # are filtered out of the candidate pool before the top-N cut.
        scored = []
        for idx, entry in enumerate(entries):
            score = _score_entry(entry["title"], entry["desc"], activated)
            if score > 0:
                scored.append((-score, idx, entry))
        scored.sort()
        if _is_advisory_question_text(q):
            scored = [item for item in scored
                      if not _is_error_doc_title(item[2]["title"])]
        hits = [entry for _, _, entry in scored[:MAX_DOCS]]
        if not hits:
            return {"matched": False, "docs": [], "source": "llms-index",
                    "note": note}

        # Step 4: body leg with a hard total budget; excerpt degrades to the
        # index description when a body fetch fails. matched depends ONLY on
        # the index leg, never on the body leg.
        docs = []
        deadline = time.time() + BODY_BUDGET_SECONDS
        body_degraded = False
        for entry in hits:
            excerpt = ""
            if time.time() < deadline:
                excerpt = _body_excerpt(entry["url"])
            if not excerpt:
                excerpt = _truncate(entry["desc"])
                body_degraded = True
            docs.append({"title": entry["title"], "url": entry["url"],
                         "excerpt": excerpt})
        if body_degraded and note is None:
            note = "DEGRADED: body fetch failed, excerpt from index"
        return {"matched": True, "docs": docs, "source": "llms-index",
                "note": note}
    except Exception as exc:  # final guard: never break the main diagnosis
        return _offline(f"unexpected error: {exc.__class__.__name__}")


# Inline boundary assertions of the public API (normal / boundary / invalid).
_NO_TOPIC = lookup_config_topic("签名URL过期了", [])
assert _NO_TOPIC == {"matched": False, "docs": [], "source": "llms-index",
                     "note": None}                       # boundary: no topics
_EMPTY_Q = lookup_config_topic("   ", [{"keywords": ["签名"], "hint": "x"}])
assert _EMPTY_Q["matched"] is False and _EMPTY_Q["note"] is None  # boundary: blank question
_NONE_Q = lookup_config_topic(None, [{"keywords": ["签名"], "hint": "x"}])
assert _NONE_Q["matched"] is False                       # invalid: non-str question
_NO_KW = lookup_config_topic("完全无关的问题",
                             [{"keywords": ["签名"], "hint": "x"}])
assert _NO_KW["matched"] is False and _NO_KW["note"] is None  # normal: nothing activated
_BAD_TOPICS = lookup_config_topic("签名URL", "not-a-list")
assert _BAD_TOPICS["matched"] is False                   # invalid: topics not a list


# ---------------------------------------------------------------------------
# Self-test entry (manual smoke test only; never used by the entry scripts)
# ---------------------------------------------------------------------------

def _self_test(skill_topics) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test the doc lookup leg against the live index")
    parser.add_argument("--question", required=True)
    args = parser.parse_args()
    result = lookup_config_topic(args.question, skill_topics)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_self_test(SKILL_TOPICS))
