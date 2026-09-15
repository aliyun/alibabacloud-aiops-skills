#!/usr/bin/env python3
"""
_doc_lookup.py -- runtime official-doc verification for alibabacloud-oss-cross-account-auth-diagnosis
=======================================================================
Read-only augmentation module. Given the customer's original wording
(--question), it matches the skill's embedded topic table against the
official OSS help-center document index
(https://help.aliyun.com/zh/oss/llms.txt) and returns up to 3 candidate
docs with excerpts fetched from the index-hit .md URLs.

Two-leg mechanism (help-center leg only, no OpenAPI metadata leg):
  * index leg: one fetch of /zh/oss/llms.txt with a 3-day local cache
    (~/.cache/oss-skill-docs/oss-llms.txt); a fresh cache means ZERO
    network requests for the index leg.
  * body leg: on-demand direct read of at most 3 index-hit .md docs,
    15s timeout each, 45s total budget.

Hard guarantees:
  * NEVER raises: every failure path returns a four-key dict with a
    "DEGRADED: ..." note and logs "[WARN] doc lookup degraded: ..." to
    stderr so degradation is always evidenced.
  * NEVER blocks the main diagnosis: offline/failed lookups just leave
    matched=False.
  * Zero credentials: this module reads no environment credentials,
    never touches the aliyun CLI or STS; it only reads public content
    on help.aliyun.com (URL whitelist enforced).

Return contract (constant four keys):
  {
    "matched": bool,
    "docs": [{"title": str, "url": str, "excerpt": str}],  # <= 3, .md URLs
    "source": "llms-index",
    "note": null | "DEGRADED: <reason>"
  }

Self-test:
  python3 _doc_lookup.py                      # inline assertions only
  python3 _doc_lookup.py --question "<text>"  # assertions + live lookup
"""
from __future__ import annotations

import os
import re
import sys
import time
import urllib.error
import urllib.request

INDEX_URL = "https://help.aliyun.com/zh/oss/llms.txt"
ALLOWED_HOST = "help.aliyun.com"
CACHE_DIR = os.path.expanduser("~/.cache/oss-skill-docs")
CACHE_PATH = os.path.join(CACHE_DIR, "oss-llms.txt")
CACHE_TTL_SECONDS = 3 * 24 * 3600  # 3 days (judged by file mtime)
TIMEOUT_SECONDS = 15               # per-request timeout (index + each body)
BODY_BUDGET_SECONDS = 45           # total budget for the body leg
MAX_DOCS = 3
EXCERPT_LIMIT = 500                # Unicode characters
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QoderWork/1.0"

# Index line shape: - [title](https://help.aliyun.com/zh/oss/xxx.md): desc
ENTRY_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\):\s*(.*)", re.MULTILINE)

# Skill-specific topic table (embedded constant; MUST 1.1.2 -- no data files).
# keywords are case-insensitive substring-matched against the question;
# hint is a short label for observability.
SKILL_TOPICS = [
    {"keywords": ["跨账号", "另一个账号", "对方账号", "b账号", "a账号", "账号间"], "hint": "cross-account"},
    {"keywords": ["授权", "ram角色", "assumerole", "role", "信任策略"], "hint": "RAM role auth"},
    {"keywords": ["迁移", "转移", "数据迁移"], "hint": "migration"},
    {"keywords": ["bucket policy", "policy", "策略", "acl"], "hint": "bucket policy"},
    {"keywords": ["复制", "同步"], "hint": "replication auth"},
]

# CAA-2 lexical-gap bridge (plan A, image-skill IPM-4 family): colloquial
# customer wording that the official-doc vocabulary never uses, mapped to
# the doc terms. Measured root cause: "oss 转移到另一个账号" activates
# ['另一个账号','转移'] while the CORRECT docs are titled "跨账号/数据迁移"
# (activation hit count 0), so unrelated docs riding single desc hits won
# (T4 "请求者付费模式（C# SDK V1）"; T7 IMM x 3). These expansions are
# unioned into the activated set on top of SKILL_TOPICS.
VOCAB_MAP = {
    "转移": ("迁移",),               # 账号转移/数据转移 -> doc term 迁移
    "另一个账号": ("跨账号",), "另一账号": ("跨账号",),
    "对方账号": ("跨账号",), "别的账号": ("跨账号",),
    "其他账号": ("跨账号",), "账号间": ("跨账号",),
    "公司账号": ("跨账号",), "合作伙伴账号": ("跨账号",),
    "两个账号": ("跨账号",),      # ticket wording "两个账号之间"
    "账号之间": ("跨账号",),      # ticket wording "两个阿里云账号之间"
    "两个阿里云账号": ("跨账号",),  # ticket wording without 之间
    "同步": ("复制",),            # cross-account data sync -> doc term 复制
}

# CAA-2 relevance tuning (plan B, same IPM-4 family): on keyword-score
# ties the sort used to degrade to index order, letting IMM x N crowd out
# "数据迁移概述" (measured T7) and per-language SDK docs ride "授权"/
# "同步" title hits (measured E2-7/9/10). Strong in-domain title signals
# are boosted and strong off-domain ones penalized inside _score_entry.
_TITLE_BOOST = ("跨账号", "数据迁移", "迁移概述", "跨区域复制", "复制规则")
_TITLE_PENALTY = ("sdk", "imm", "智能媒体", "多模态", "hdfs")

# Configuration/usage consultation signal words (Step B condition 2).
_CONSULT_SIGNALS = (
    "怎么", "如何", "怎样", "是否", "能否", "能不能", "可以", "支持",
    "配置", "开通", "设置", "咨询", "请问", "方案", "建议", "吗",
    "多少", "费用", "收费", "价格", "？", "?",
    "how ", "how?", "can ", "whether", "configure", "enable",
)


# ---------------------------------------------------------------------------
# Pure helpers (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def _warn(reason: str) -> None:
    print(f"[WARN] doc lookup degraded: {reason}", file=sys.stderr)


def _is_err(text: str) -> bool:
    """fetch() error-marker detection (avoid treating Markdown '[' as error)."""
    return text.startswith("[HTTP ") or text.startswith("[Error]")


def _looks_like_html(text: str) -> bool:
    """HTTP 200 but SPA/HTML page (migrated doc / dead slug) -> unusable."""
    head = text.lstrip()[:300].lower()
    return (head.startswith("<!doctype") or head.startswith("<html")
            or "<html" in head)


def _is_degraded_url(url: str) -> bool:
    """URL whitelist guard: anything off help.aliyun.com (or malformed) is
    degraded and MUST NOT be fetched (URL-injection defense)."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return True
    host = (url.split("/", 3)[2] if len(url.split("/", 3)) > 2 else "").lower()
    return host != ALLOWED_HOST


assert _is_degraded_url("https://help.aliyun.com/zh/oss/user-guide.md") is False  # normal
assert _is_degraded_url("https://help.aliyun.com/") is False  # boundary: host only
assert _is_degraded_url("http://help.aliyun.com/x.md") is True  # boundary: not https
assert _is_degraded_url("https://evil.example.com/x.md") is True  # invalid: other host
assert _is_degraded_url("") is True  # invalid: empty


def _truncate(text: str, limit: int = EXCERPT_LIMIT) -> str:
    """Truncate to at most `limit` Unicode characters."""
    t = text if isinstance(text, str) else ""
    return t[:limit]


assert _truncate("abc") == "abc"  # normal: short text unchanged
assert _truncate("a" * 600) == "a" * 500  # boundary: cut at 500
assert _truncate("") == ""  # invalid: empty


def _score_entry(title: str, desc: str, activated: list) -> int:
    """Deterministic entry score: 2 per activated keyword found in the
    title + 1 per activated keyword found in the description
    (case-insensitive substring, same semantics as the help search leg),
    PLUS the CAA-2 relevance adjustment: +2 per strong in-domain title
    signal (_TITLE_BOOST) and -3 per strong off-domain title signal
    (_TITLE_PENALTY), so conceptual docs (跨账号授权 / 数据迁移概述 /
    跨区域复制) stay ahead of per-language SDK docs and IMM-family docs
    on keyword ties instead of degrading to index order."""
    tl = (title or "").lower()
    dl = (desc or "").lower()
    score = 0
    for kw in activated:
        k = (kw or "").lower()
        if not k:
            continue
        if k in tl:
            score += 2
        if k in dl:
            score += 1
    score += 2 * sum(1 for b in _TITLE_BOOST if b in tl)
    score -= 3 * sum(1 for p in _TITLE_PENALTY if p in tl)
    return score


assert _score_entry("生命周期规则介绍", "", ["生命周期"]) == 2  # normal: title hit
assert _score_entry("概述", "配置生命周期规则", ["生命周期"]) == 1  # normal: desc hit
assert _score_entry("生命周期", "生命周期", ["生命周期"]) == 3  # boundary: both
assert _score_entry("", "", []) == 0  # invalid: no activated words
assert _score_entry(None, None, ["生命周期"]) == 0  # invalid: missing fields
# CAA-2 plan B: boost/penalty ordering guards (offline pure-function layer).
assert _score_entry("数据迁移概述", "", ["迁移"]) == 6  # 2 title hit + 2 boosts (数据迁移 AND 迁移概述 substrings)
assert _score_entry("跨账号授权", "", ["授权"]) == 4  # 2 title hit + 2 boost
assert _score_entry("旧版IMM文档预览迁移", "", ["迁移"]) == -1  # 2 - 3 IMM penalty -> filtered (s>0)
assert _score_entry("请求者付费模式（C# SDK V1）", "另一个账号", ["另一个账号", "转移"]) == -2  # T4: 1 desc hit - 3 SDK penalty -> filtered
assert _score_entry("Ruby SDK授权访问", "", ["授权"]) == -1  # E2-7/9 shape: SDK title penalized out
assert _score_entry("SDK同步处理", "", ["同步"]) == -1  # E2-10 shape: SDK title penalized out
assert _score_entry("跨区域复制介绍", "", ["复制", "同步"]) == 4  # 1 title hit (复制) + 2 boost (同步 not in title)


def _activated_keywords(question: str, skill_topics: list) -> list:
    """Keywords of the topic table that appear in the question
    (case-insensitive substring). Empty list -> matched=False."""
    q = (question or "").lower()
    acts = []
    for topic in skill_topics or []:
        for kw in topic.get("keywords", []) or []:
            if kw and kw.lower() in q and kw.lower() not in acts:
                acts.append(kw.lower())
    return acts


def _expand_vocab(question: str) -> list:
    """CAA-2 plan A: doc-vocabulary expansions for colloquial customer
    wording (VOCAB_MAP). Runs independently of SKILL_TOPICS activation
    so ticket phrasings like "两个账号之间" / "公司账号" (which contain no
    SKILL_TOPICS keyword) still reach the 跨账号 docs."""
    q = (question or "").lower()
    out = []
    for src, dsts in VOCAB_MAP.items():
        if src in q:
            for d in dsts:
                if d not in out:
                    out.append(d)
    return out


assert _expand_vocab("oss 转移，可以把另一个账号下的 oss 转移到这个账号下吗") == ["迁移", "跨账号"]  # T4 shape
assert _expand_vocab("bucket 迁移到另一账号怎么无损迁移") == ["跨账号"]  # T7 shape: 另一账号 (no 个)
assert _expand_vocab("两个账号之间怎么同步数据") == ["跨账号", "复制"]  # E2 ticket synonym shape
assert _expand_vocab("两个阿里云账号之间做数据同步") == ["跨账号", "复制"]  # E2-10 exact ticket wording
assert _expand_vocab("zzz-no-vocab-zzz") == []  # invalid: nothing maps
assert _expand_vocab("") == []  # boundary: empty


def is_consult_question(question: str) -> bool:
    """True when the wording carries configuration/usage consultation
    signals (Step B condition 2 of the integration spec)."""
    low = (question or "").lower()
    return any(sig in low for sig in _CONSULT_SIGNALS)


assert is_consult_question("这个怎么配置？") is True  # normal
assert is_consult_question("does oss support lifecycle?") is True  # normal: en
assert is_consult_question("InvalidObjectState 报错") is False  # boundary: pure error
assert is_consult_question("") is False  # invalid: empty


def _clean_excerpt(markdown: str) -> str:
    """Strip Markdown image/link syntax and consecutive blank lines, take
    the first non-empty paragraph, truncate to EXCERPT_LIMIT characters."""
    text = markdown or ""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # links -> text
    text = re.sub(r"^[#>\-\*\|\s`]+", "", text, flags=re.M)   # md markers
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    first = paragraphs[0] if paragraphs else ""
    first = re.sub(r"\s+", " ", first)
    return _truncate(first)


# ---------------------------------------------------------------------------
# Network legs
# ---------------------------------------------------------------------------

def _fetch(url: str) -> str:
    """GET a URL with the fixed UA and a 15s timeout; errors are returned
    as '[HTTP ...]' / '[Error] ...' markers (never raises)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] {e.reason}"
    except Exception as e:  # noqa: BLE001 -- degradation must never raise
        return f"[Error] {e}"


def _load_index():
    """Index leg. Returns (text, note_fragment):
      note_fragment '' -> clean path (fresh cache or fresh fetch)
      'stale-cache'     -> fetch failed, expired cache reused
      'offline or index fetch failed' -> nothing usable, text == ''
    A fresh cache hit performs ZERO network requests.
    """
    cached = ""
    cache_fresh = False
    try:
        st = os.stat(CACHE_PATH)
        with open(CACHE_PATH, encoding="utf-8") as f:
            cached = f.read()
        cache_fresh = (time.time() - st.st_mtime) < CACHE_TTL_SECONDS
    except OSError:
        cached = ""
    if cache_fresh and cached.strip():
        return cached, ""
    text = _fetch(INDEX_URL)
    if not _is_err(text) and not _looks_like_html(text) and text.strip():
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = CACHE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, CACHE_PATH)  # atomic write
        except OSError:
            pass  # cache write failure never degrades the lookup itself
        return text, ""
    if cached.strip():
        return cached, "stale-cache"
    return "", "offline or index fetch failed"


def _fetch_body_excerpt(url: str, deadline: float):
    """Body leg for one doc: returns the cleaned first paragraph, or None
    when the URL is off-whitelist, the budget is exhausted, or the fetch
    failed / returned HTML."""
    if _is_degraded_url(url):
        return None
    if time.time() >= deadline:
        return None
    text = _fetch(url)
    if _is_err(text) or _looks_like_html(text) or not text.strip():
        return None
    excerpt = _clean_excerpt(text)
    return excerpt or None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _offline_result(reason: str) -> dict:
    return {"matched": False, "docs": [], "source": "llms-index",
            "note": f"DEGRADED: {reason}"}


def lookup_config_topic(question: str, skill_topics: list = None) -> dict:
    """Verify the customer's original wording against official OSS docs.

    Constant four-key return; NEVER raises. `matched=True` only when at
    least one index entry scores > 0 on keywords that also appear in the
    question. Body-leg failures never flip `matched`; the excerpt degrades
    to the index-line summary with a DEGRADED note.
    """
    try:
        topics = SKILL_TOPICS if skill_topics is None else skill_topics
        q = (question or "").strip()
        if not q:
            _warn("empty question")
            return _offline_result("empty question")
        acts = _activated_keywords(q, topics)
        for w in _expand_vocab(q):
            if w not in acts:
                acts.append(w)  # CAA-2 plan A: bridge the lexical gap
        if not acts:
            # No topic keyword present in the question: not a doc-lookup
            # target. This is NOT a degradation (matched=False, note=None).
            return {"matched": False, "docs": [], "source": "llms-index",
                    "note": None}
        text, index_note = _load_index()
        if not text:
            _warn(index_note)
            return _offline_result(index_note)
        scored = []
        for order, (title, url, desc) in enumerate(ENTRY_RE.findall(text)):
            s = _score_entry(title, desc, acts)
            if s > 0:
                scored.append((s, order, title, url, desc))
        scored.sort(key=lambda item: (-item[0], item[1]))
        top = scored[:MAX_DOCS]
        if not top:
            note = f"DEGRADED: {index_note}" if index_note else None
            return {"matched": False, "docs": [], "source": "llms-index",
                    "note": note}
        deadline = time.time() + BODY_BUDGET_SECONDS
        docs = []
        body_degraded = False
        for _s, _o, title, url, desc in top:
            excerpt = _fetch_body_excerpt(url, deadline)
            if excerpt is None:
                body_degraded = True
                excerpt = _truncate((desc or "").strip()) or title
            docs.append({"title": title, "url": url, "excerpt": excerpt})
        reasons = []
        if index_note:
            reasons.append(index_note)
        if body_degraded:
            reasons.append("body fetch failed, excerpt from index")
        note = ("DEGRADED: " + "; ".join(reasons)) if reasons else None
        return {"matched": True, "docs": docs, "source": "llms-index",
                "note": note}
    except Exception as e:  # noqa: BLE001 -- contract: never raise
        _warn(f"unexpected error: {e}")
        return {"matched": False, "docs": [], "source": "llms-index",
                "note": f"DEGRADED: unexpected error {e}"}


def _selftest() -> None:
    """Inline boundary assertions for the activated-keyword selection."""
    acts = _activated_keywords("OSS生命周期怎么配置", SKILL_TOPICS)
    assert isinstance(acts, list)  # normal: returns list
    assert _activated_keywords("", SKILL_TOPICS) == []  # invalid: empty
    assert _activated_keywords("zzz-not-a-topic-zzz", SKILL_TOPICS) == []
    low_join = " ".join(acts)
    assert low_join == low_join.lower()  # boundary: lowercase normalized
    print(f"[selftest] _doc_lookup OK: {len(SKILL_TOPICS)} topics, "
          f"activated sample={acts[:4]}")


if __name__ == "__main__":
    import argparse
    import json

    _selftest()
    parser = argparse.ArgumentParser(
        description="Official-doc lookup self-test for alibabacloud-oss-cross-account-auth-diagnosis")
    parser.add_argument("--question", default="",
                        help="optional live lookup with this wording")
    args = parser.parse_args()
    if args.question.strip():
        print(json.dumps(lookup_config_topic(args.question),
                         ensure_ascii=False, indent=2))
