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

# Scenario-specific topic table for the image-processing diagnosis skill
# (embedded constant: platform MUST 1.1.2, no data files). Keywords are
# case-insensitive substrings of the customer's original question.
# Eval IPM-4 recipe A: the generic single word 图片 stays (real ticket
# wording often carries nothing more specific), but industry wording of
# actual tickets (压缩/放大/白名单/QPS/计费/抽帧/动图) is added so the
# activated-keyword set is more specific and scores can differentiate.
# Eval IPM-5: the bare "404" keyword was removed -- a generic upload
# failure ticket ("oss上传文件失败报404") falsely activated this skill's
# doc leg; "400" stays because a 400 on a processing URL is IMG-specific.
# Eval IPM-6: CDN ignore-parameters / cache-refresh wording added -- the
# CDN cross-contamination chapter is this skill's differentiating
# knowledge (references/image-processing-playbook.md).
SKILL_TOPICS = [
    {"keywords": ["图片处理", "图片", "水印", "缩放", "裁剪", "旋转", "格式转换", "原图保护", "x-oss-process", "image processing"],
     "hint": "image-processing"},
    {"keywords": ["webp", "heic", "avif", "gif", "原图", "质量", "缩略图", "quality", "resize", "watermark"],
     "hint": "image-format-style"},
    {"keywords": ["样式", "图片样式", "分隔符", "风格", "自定义样式", "style", "separator"],
     "hint": "image-style"},
    {"keywords": ["处理失败", "无效图片", "不支持", "损坏", "报错", "不生效", "参数错误", "invalidimage", "400"],
     "hint": "image-error"},
    {"keywords": ["压缩", "放大", "缩小", "白名单", "qps", "限额", "配额", "计费", "费用", "抽帧", "动图"],
     "hint": "image-advisory"},
    {"keywords": ["忽略参数", "缓存刷新", "刷新", "缓存", "回源"],
     "hint": "cdn-cross-contamination"},
]


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


# Eval IPM-4 recipe B: IMG-domain strong-signal title terms. When the
# activated keyword is the generic single word 图片, every title that
# merely CONTAINS 图片 scores, so OSS image-processing docs used to tie
# with IMM docs; the tie then degraded to index order, letting IMM docs
# (多模态图片语义检索实践 / OSS 身份证图片脱敏 / 旧版 IMM 图片识别)
# dominate the top-3 (live eval E06/E07/E08/E13). A title that carries ANY
# of these terms gets a flat +1 bonus, but ONLY for an entry that already
# matched at least one activated keyword: the bonus separates the IMG
# domain from IMM/out-of-domain entries and must NOT compete with the
# activated-keyword score inside the IMG domain (small and flat on
# purpose -- a larger/stacked bonus let marginal IMG docs outrank the docs
# that actually match the specific industry wording, e.g. 压缩).
_IMG_STRONG_TITLE_TERMS = (
    "图片处理", "图片样式", "水印", "裁剪", "缩放", "旋转", "翻转",
    "格式转换", "质量", "样式", "原图", "内切圆", "圆角", "模糊",
    "锐化", "亮度", "对比度", "渐进显示", "主色调", "自适应", "获取图片",
    "x-oss-process",
)

# Eval IPM-4 root cause: the single generic word 图片 is kept as a trigger
# (real ticket wording often carries nothing more specific) but is scored
# at HALF weight (title +1 instead of +2) so that a doc matching a
# specific industry word (压缩/水印/裁剪...) outranks a doc that merely
# shares the generic word with every other 图片-titled doc.
_GENERIC_KEYWORDS = frozenset({"图片"})

# Eval IPM-4 recipe B/C: IMM / out-of-domain demotion terms. An entry whose
# TITLE carries one of these drops 6 points -- below every reachable
# positive score -- and is therefore filtered out of the results (recipe
# C) even when its title shares the generic word 图片. TITLE-only matching
# on purpose: real IMG docs may legitimately mention IMM in their
# DESCRIPTION text.
_IMM_DEMOTE_TERMS = (
    "imm", "智能媒体", "多模态", "脱敏", "语义检索",
)


def _score_entry(title: str, desc: str, activated: set) -> int:
    """Deterministic tiered entry score (eval IPM-4 recipe A+B):
      * +2 per activated keyword found in the title, +1 per activated
        keyword found in the description (case-insensitive substrings);
        the single generic word 图片 scores at half weight (title +1)
        because it alone cannot differentiate IMG docs from IMM docs;
      * flat +1 when the title carries any IMG-domain strong-signal term,
        applied ONLY when the entry already matched at least one activated
        keyword (a doc that matches nothing must not enter the results on
        the bonus alone; inside the IMG domain the bonus stays small and
        flat so the activated-keyword score decides the ranking);
      * -6 when the title carries an IMM / out-of-domain signal, which
        pushes such entries below every positive score (effective filter).
    """
    if not activated:
        return 0
    t = (title or "").lower()
    d = (desc or "").lower()
    score = 0
    for kw in activated:
        weight = 1 if kw in _GENERIC_KEYWORDS else 2
        if kw in t:
            score += weight
        if kw in d:
            score += 1
    if score > 0 and any(term in t for term in _IMG_STRONG_TITLE_TERMS):
        score += 1
    if any(term in t for term in _IMM_DEMOTE_TERMS):
        score -= 6
    return score


assert _score_entry("签名URL概述", "使用签名", {"签名"}) == 3        # normal: title+desc
assert _score_entry("签名URL概述", "无关", {"签名"}) == 2            # normal: title only
assert _score_entry("无关标题", "使用签名", {"签名"}) == 1           # normal: desc only
assert _score_entry("无关标题", "无关", {"签名"}) == 0              # boundary: no hit
assert _score_entry("abc", "abc", set()) == 0                       # boundary: empty set
assert _score_entry("", "", {"签名"}) == 0                          # invalid: empty entry
assert _score_entry("SIGN url", "sign", {"sign"}) == 3              # boundary: case-insensitive

# IPM-4 contract: generic 图片 activation -- IMG docs outrank IMM docs
# via the flat strong-signal bonus; IMM docs drop below every positive
# score.
assert _score_entry("图片处理", "任意描述", {"图片"}) == 2       # 1 base + 1 strong (flat)
assert _score_entry("图片样式", "任意", {"图片"}) == 2         # 1 base + 1 strong (flat)
assert _score_entry("多模态图片语义检索实践", "任意", {"图片"}) == -5  # 1 - 6 demote (多模态/语义检索)
assert _score_entry("旧版 imm 图片识别", "任意", {"图片"}) == -5       # 1 - 6 demote (imm, lowercased)
assert _score_entry("OSS 身份证图片脱敏", "任意", {"图片"}) == -5     # 1 - 6 demote (脱敏)
# inside the IMG domain the SPECIFIC keyword outranks the generic one:
# a doc whose title matches 压缩 (1+2) beats a doc that only shares 图片
# and the strong-signal bonus (1+1).
assert _score_entry("HEIF 或 AVIF 图片高级压缩", "任意", {"图片", "压缩"}) \
    > _score_entry("获取图片主色调", "任意", {"图片", "压缩"})
# boundary: the strong-signal bonus never fires without an activated-
# keyword match (a doc matching nothing must stay at 0).
assert _score_entry("图片水印", "无关描述", {"压缩"}) == 0     # boundary: no base match, no bonus
# boundary: demotion is TITLE-only -- a real IMG doc whose description
# legitimately mentions IMM must not be demoted.
assert _score_entry("图片处理", "更复杂场景请使用智能媒体管理 IMM", {"图片"}) == 2


def _clean_excerpt(text: str) -> str:
    """Strip Markdown image/link syntax and collapse blank lines; return the
    first non-empty paragraph truncated to EXCERPT_CHARS ('' when unusable)."""
    if not isinstance(text, str) or _is_err(text) or _looks_like_html(text):
        return ""
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)       # images
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)   # links -> label
    body = re.sub(r"(?m)^#{1,6}\s.*$", "", body)           # heading lines
    body = re.sub(r"(?m)^\s*>\s?", "", body)               # blockquotes
    body = re.sub(r"[#>*`|]", " ", body)                   # md decorations
    paragraphs = [re.sub(r"\s+", " ", p).strip()
                  for p in re.split(r"\n\s*\n", body)]
    for para in paragraphs:
        if para:
            return _truncate(para)
    return ""


assert _clean_excerpt("# 标题\n\n第一段正文。") == "第一段正文。"          # normal: first paragraph
assert _clean_excerpt("[链接文字](https://x) 后续") == "链接文字 后续"     # normal: link label kept
assert _clean_excerpt("![alt](https://x/i.png)图后文字") == "图后文字"     # normal: image dropped
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

        # Step 1: activated keywords = topic keywords present in question.
        activated = set()
        for topic in topics:
            kws = (topic or {}).get("keywords") or []
            for kw in kws:
                if isinstance(kw, str) and kw and kw.lower() in q.lower():
                    activated.add(kw.lower())
        if not activated:
            return {"matched": False, "docs": [], "source": "llms-index",
                    "note": None}

        # Step 2: index leg (cached or fetched).
        entries, note = _load_index()
        if not entries:
            return _offline(note.replace("DEGRADED: ", "")
                            if note else "offline or index fetch failed")

        # Step 3: score, stable order (score desc, then index order).
        scored = []
        for idx, entry in enumerate(entries):
            score = _score_entry(entry["title"], entry["desc"], activated)
            if score > 0:
                scored.append((-score, idx, entry))
        scored.sort()
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
