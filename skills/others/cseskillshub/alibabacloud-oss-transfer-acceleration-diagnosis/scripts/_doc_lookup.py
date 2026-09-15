#!/usr/bin/env python3
"""
_doc_lookup.py -- runtime official-doc verification for alibabacloud-oss-transfer-acceleration-diagnosis
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
    "note": null | "DEGRADED: <reason>" |
            "OUT-OF-SCOPE (CDN|GA|ESA): <referral>"   # TAC-4 guard
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
#
# TAC-1 (ticket-language recall, eval fix mirroring the presigned PR-10
# precedent): real tickets say 国外/上传慢/下载慢 -- not only 跨境/访问慢
# -- so those phrasings are first-class routing keys now (measured baseline:
# '美国服务器上传杭州的oss上传慢' / '传国外快国内慢' / '国外上传慢怎么解决'
# all activated ZERO keys).
#
# TAC-4 (cross-domain false activation): generic keys (加速/CDN/缓存/速度)
# absorb sibling-product wording (GA / ESA / CDN back-to-origin), so they
# carry context_required=True and only activate when an OSS context token
# co-occurs; sibling-product wording without transfer-acceleration context
# is transferred out via DOMAIN_TRANSFER_GUARDS below instead.
#
# doc_keys (TAC-1): proxy scoring keywords injected when a topic's keyword
# activates. Ticket symptom words (国外/上传慢/...) never literally appear
# in any index title, so without the proxy the activated question would
# still match zero docs; the proxy routes the symptom to the authoritative
# transfer-acceleration guide family.
SKILL_TOPICS = [
    {"keywords": ["传输加速", "加速域名", "oss-accelerate", "accelerate",
                  "transfer acceleration"],
     "hint": "transfer acceleration"},
    {"keywords": ["跨境", "海外", "国外"], "hint": "cross-border",
     "doc_keys": ["传输加速"]},
    {"keywords": ["费用", "收费"], "hint": "acceleration fee"},
    {"keywords": ["上传慢", "下载慢", "拉取慢", "速度慢", "上传速度慢",
                  "下载速度慢", "提速", "美国", "硅谷"],
     "hint": "slow transfer (context-guarded)", "context_required": True,
     "doc_keys": ["传输加速"]},
    {"keywords": ["加速", "cdn", "缓存", "速度", "访问慢"],
     "hint": "generic acceleration (context-guarded)",
     "context_required": True},
]

# OSS context tokens: when present in the question, generic symptom keys
# may activate (the wording is about OSS, not a sibling product).
_OSS_CONTEXT_TOKENS = (
    "oss", "bucket", "存储桶", "对象存储", "oss-accelerate",
    "传输", "endpoint", "阿里云",
)

# Strong in-domain tokens: their presence exempts a question from the
# DOMAIN_TRANSFER_GUARDS below -- the customer explicitly asks about OSS
# transfer acceleration even though sibling-product words co-occur
# (e.g. "传输加速和CDN能否同时使用" stays in scope).
_TA_STRONG_TOKENS = ("传输加速", "oss-accelerate", "transfer acceleration")

# Out-of-domain transfer guards (TAC-4, presigned PR-4 precedent): wording
# that marks the case for a sibling product produces NO doc candidates here
# and returns an OUT-OF-SCOPE note so the Agent defers the customer to the
# right direction instead of returning loosely-related OSS docs. Each guard
# is a tuple of word groups; EVERY group must contribute at least one word
# present in the lowercased question. Guards apply only WITHOUT a strong
# transfer-acceleration token in the question.
DOMAIN_TRANSFER_GUARDS = (
    # CDN back-to-origin / CDN cache-refresh wording -> CDN direction.
    (("回源", "自动刷新", "刷新预热"), "CDN"),
    # Global Accelerator instance/listener configuration -> GA direction.
    (("全球加速", "global accelerator", "ga实例"), "GA"),
    # ESA (Edge Security Acceleration) wording -> ESA direction.
    (("边缘安全加速", "esa边缘"), "ESA"),
)

# Guard -> referral note text (deferred directions, mirrors the official
# five-option acceleration portfolio in references/
# accelerator-vs-transfer-acceleration.md).
_GUARD_REFERRALS = {
    "CDN": ("CDN back-to-origin / cache-refresh configuration belongs to "
            "the CDN product direction (CDN origin-config diagnosis / CDN "
            "docs), not OSS transfer acceleration"),
    "GA": ("Global Accelerator (GA) instance/listener configuration "
           "belongs to the GA product direction (GA docs), not OSS "
           "transfer acceleration"),
    "ESA": ("ESA (Edge Security Acceleration) wording belongs to the ESA "
            "product direction (ESA docs), not OSS transfer acceleration"),
}

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
    (case-insensitive substring, same semantics as the help search leg)."""
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
    return score


assert _score_entry("生命周期规则介绍", "", ["生命周期"]) == 2  # normal: title hit
assert _score_entry("概述", "配置生命周期规则", ["生命周期"]) == 1  # normal: desc hit
assert _score_entry("生命周期", "生命周期", ["生命周期"]) == 3  # boundary: both
assert _score_entry("", "", []) == 0  # invalid: no activated words
assert _score_entry(None, None, ["生命周期"]) == 0  # invalid: missing fields


def _activated_keywords(question: str, skill_topics: list) -> list:
    """Keywords of the topic table that appear in the question
    (case-insensitive substring). Empty list -> matched=False.

    Topics carrying context_required=True (the generic symptom keys)
    only contribute their keywords when an OSS context token also
    appears in the question (TAC-4: GA/ESA/CDN-domain absorption guard).
    """
    q = (question or "").lower()
    acts = []
    for topic in skill_topics or []:
        kws = topic.get("keywords", []) or []
        if not kws:
            continue
        if topic.get("context_required") and \
                not any(tok in q for tok in _OSS_CONTEXT_TOKENS):
            continue
        for kw in kws:
            if kw and kw.lower() in q and kw.lower() not in acts:
                acts.append(kw.lower())
    return acts


assert _activated_keywords("传输加速怎么开通", SKILL_TOPICS) == \
    ["传输加速", "加速"]  # normal: strong + generic (ctx via 传输)
assert _activated_keywords("国外上传慢怎么解决", SKILL_TOPICS) == \
    ["国外"]  # normal (TAC-1): ticket phrasing activates; slow-transfer
# topic is context-guarded (no OSS token in this wording), 国外 is strong
assert _activated_keywords("美国服务器上传杭州的oss上传慢", SKILL_TOPICS) == \
    ["上传慢", "美国"]  # normal (TAC-1): oss context unlocks symptom keys
assert _activated_keywords("传国外快国内慢", SKILL_TOPICS) == ["国外"]  # boundary
assert _activated_keywords("全球加速GA实例怎么配置", SKILL_TOPICS) == []  # boundary: GA wording, generic key stays locked (no OSS ctx)
assert _activated_keywords("这速度是认真的吗", SKILL_TOPICS) == []  # boundary: speed wording without OSS ctx -> silent (Q4 fix)
assert _activated_keywords("", SKILL_TOPICS) == []  # invalid: empty
assert _activated_keywords(None, SKILL_TOPICS) == []  # invalid: missing


def _match_transfer_guard(question: str):
    """TAC-4 guard: return the referral direction ("CDN"/"GA"/"ESA")
    when the wording marks a sibling-product case, else None.

    Every word of a guard's single group must be absent-or-present logic:
    the group matches when ANY of its words appears in the lowercased
    question. Guards apply only when no strong transfer-acceleration
    token co-occurs (checked by the caller)."""
    q = (question or "").lower()
    if not q:
        return None
    for group, direction in DOMAIN_TRANSFER_GUARDS:
        if any(word in q for word in group):
            return direction
    return None


assert _match_transfer_guard("CDN加速域名打不开 回源OSS失败") == "CDN"  # normal: 回源
assert _match_transfer_guard("全球加速GA实例怎么配置监听和终端节点") == "GA"  # normal
assert _match_transfer_guard("ESA边缘安全加速怎么开启缓存加速") == "ESA"  # normal
assert _match_transfer_guard("OSS侧开通CDN缓存自动刷新功能") == "CDN"  # normal: refresh
assert _match_transfer_guard("CEN transit router 跨地域带宽怎么配置") is None  # boundary: no guard
assert _match_transfer_guard("") is None  # invalid: empty
assert _match_transfer_guard(None) is None  # invalid: missing


def _dedupe_family_keys(keys: list) -> list:
    """TAC-3 same-family dedup: a keyword that is a substring of another
    activated keyword is absorbed by it and stops scoring.

    Measured baseline: '0048-00000002 传输加速域名 HTML 强制下载' scored
    2+2 (title) via BOTH 传输加速 and 加速 and crowded out the
    authoritative 《OSS 传输加速》 guide (single-family ~3). With the
    dedup, '加速' collapses into '传输加速' and both docs score once
    per family."""
    clean = [k for k in (keys or []) if k]
    return [k for k in clean
            if not any(k != o and k in o for o in clean)]


assert _dedupe_family_keys(["传输加速", "加速"]) == ["传输加速"]  # normal: absorb
assert _dedupe_family_keys(["传输加速", "加速", "加速域名", "cdn"]) == \
    ["传输加速", "加速域名", "cdn"]  # normal: 加速 absorbed by both superstrings
assert _dedupe_family_keys(["加速"]) == ["加速"]  # boundary: standalone survives
assert _dedupe_family_keys(["费用", "收费"]) == ["费用", "收费"]  # boundary: no containment
assert _dedupe_family_keys([]) == []  # invalid: empty
assert _dedupe_family_keys(None) == []  # invalid: missing


def _scoring_keywords(skill_topics: list, activated: list) -> list:
    """Scoring keyword set = activated keywords + doc proxy keys of the
    topics whose keywords activated (TAC-1), then same-family dedup
    (TAC-3). Ticket symptom words (国外/上传慢) never appear in index
    titles, so their topics carry doc_keys=["传输加速"] proxies that
    route the symptom to the authoritative guide family."""
    keys = list(activated or [])
    for topic in skill_topics or []:
        kws = topic.get("keywords", []) or []
        if any(k in keys for k in kws):
            for dk in topic.get("doc_keys", []) or []:
                if dk not in keys:
                    keys.append(dk)
    return _dedupe_family_keys(keys)


assert _scoring_keywords(SKILL_TOPICS, ["国外"]) == ["国外", "传输加速"]  # normal: proxy injected
assert _scoring_keywords(SKILL_TOPICS, ["传输加速"]) == ["传输加速"]  # normal: no dup
assert _scoring_keywords(SKILL_TOPICS, ["上传慢", "美国"]) == \
    ["上传慢", "美国", "传输加速"]  # boundary: one proxy per topic
assert _scoring_keywords(SKILL_TOPICS, []) == []  # invalid: empty
assert _scoring_keywords(None, ["传输加速"]) == ["传输加速"]  # invalid: no topics


# TAC-3 EC-doc gate: error-code reference docs (titles like
# '0048-00000002 传输加速域名 HTML 强制下载') only score when the question
# itself carries an error-code signal; advisory questions (怎么开通/绑定/
# 能否同时使用) must not be answered by forced-download EC entries.
_EC_DOC_TITLE_RE = re.compile(r"^\d{4}-\d{6,8}\b")
_EC_SIGNAL_RE = re.compile(r"\d{4}-\d{6,8}")
_EC_SIGNAL_TOKENS = ("错误码", "报错", "强制下载", "error code", "errorcode")


def _is_ec_doc(title: str) -> bool:
    """True when the index entry is an error-code reference doc."""
    return bool(_EC_DOC_TITLE_RE.match((title or "").strip()))


def _has_ec_signal(question: str) -> bool:
    """True when the question carries an error-code signal (an EC code
    pattern or an error-wording token)."""
    q = (question or "").lower()
    if not q:
        return False
    return bool(_EC_SIGNAL_RE.search(q)) or \
        any(tok in q for tok in _EC_SIGNAL_TOKENS)


assert _is_ec_doc("0048-00000002 传输加速域名 HTML 强制下载") is True  # normal
assert _is_ec_doc("OSS 传输加速") is False  # normal: guide, not EC doc
assert _is_ec_doc("") is False  # invalid: empty
assert _is_ec_doc(None) is False  # invalid: missing
assert _has_ec_signal("报错 0048-00000002") is True  # normal: EC code
assert _has_ec_signal("上传报错 TransferAcceleration not configured") is True  # normal: 报错
assert _has_ec_signal("文件被强制下载怎么解决") is True  # normal: 强制下载
assert _has_ec_signal("oss传输加速怎么开通") is False  # boundary: advisory
assert _has_ec_signal("") is False  # invalid: empty
assert _has_ec_signal(None) is False  # invalid: missing


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
    least one index entry scores > 0 on the scoring keyword set
    (activated keywords + doc proxy keys, same-family deduped -- TAC-3).
    Out-of-domain sibling-product wording WITHOUT a strong
    transfer-acceleration token returns matched=False with an
    "OUT-OF-SCOPE (...)" referral note (TAC-4). Body-leg failures never
    flip `matched`; the excerpt degrades to the index-line summary with
    a DEGRADED note.
    """
    try:
        topics = SKILL_TOPICS if skill_topics is None else skill_topics
        q = (question or "").strip()
        if not q:
            _warn("empty question")
            return _offline_result("empty question")
        acts = _activated_keywords(q, topics)
        # TAC-4 out-of-domain guard: without a strong transfer-acceleration
        # token, sibling-product wording (CDN back-to-origin / GA / ESA)
        # transfers out with a referral note instead of loosely-related
        # OSS docs being returned as candidates.
        if not any(tok in q.lower() for tok in _TA_STRONG_TOKENS):
            direction = _match_transfer_guard(q)
            if direction is not None:
                _warn(f"out-of-scope ({direction}) wording, referral returned")
                return {"matched": False, "docs": [], "source": "llms-index",
                        "note": f"OUT-OF-SCOPE ({direction}): "
                                f"{_GUARD_REFERRALS[direction]}"}
        if not acts:
            # No topic keyword present in the question: not a doc-lookup
            # target. This is NOT a degradation (matched=False, note=None).
            return {"matched": False, "docs": [], "source": "llms-index",
                    "note": None}
        text, index_note = _load_index()
        if not text:
            _warn(index_note)
            return _offline_result(index_note)
        # TAC-1/TAC-3: scoring keys = activated keywords + doc proxy keys
        # (symptom wording routes to the authoritative guide family), then
        # same-family dedup so single-family guides are not crowded out by
        # same-family EC docs double-counting sub-keys.
        scoring_keys = _scoring_keywords(topics, acts)
        ec_signal = _has_ec_signal(q)
        scored = []
        for order, (title, url, desc) in enumerate(ENTRY_RE.findall(text)):
            # TAC-3 EC gate: error-code reference docs (titles like
            # '0048-00000002 ...') only participate when the question
            # itself carries an error-code signal.
            if _is_ec_doc(title) and not ec_signal:
                continue
            s = _score_entry(title, desc, scoring_keys)
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
        description="Official-doc lookup self-test for alibabacloud-oss-transfer-acceleration-diagnosis")
    parser.add_argument("--question", default="",
                        help="optional live lookup with this wording")
    args = parser.parse_args()
    if args.question.strip():
        print(json.dumps(lookup_config_topic(args.question),
                         ensure_ascii=False, indent=2))
