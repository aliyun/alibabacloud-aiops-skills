#!/usr/bin/env python3
"""Query construction and relevance: product-code aliases, synonym expansion, error-code
detection, index scoring and cross-leg fusion.

Pure string work plus stderr traces; it never issues a request (the caller injects the
search callable used by the low-result expansion retry).

Two rankings meet in the second half. The index leg has only a title and a one-line summary
to go on, so its score is a small ordinal weighting of exact and partial coverage; the
full-text leg arrives pre-ranked by the endpoint and is represented by its rank alone. Fusion
turns the two into a single order. All of it is pure arithmetic over records: no request, no
I/O, and no randomness, so the same inputs always produce the same output.
"""

from __future__ import annotations

import re
import sys

from help_const import (
    _DOC_ENTRY_RE,
)
from help_scope import (
    _normalize_url,
)


# Bidirectional query alias/synonym dictionary (high-frequency product aliases, Chinese-English pairs):
# alias-level expansion only, no general translation. When any alias of a group appears in the query,
# the other aliases of the group can drive an expansion retry (see _expand_query).
# Confirm official naming before adding entries, and keep the expansion note in references/doc-retrieval.md in sync.
QUERY_SYNONYMS = [
    ("EIP", "弹性公网IP"),
    # Common truncated form (without the IP suffix); works together with the group above: longest match wins, no duplicate expansion
    ("EIP", "弹性公网"),
    ("SLB", "负载均衡"),
    ("OSS", "对象存储"),
    ("ECS", "云服务器"),
    ("CDN", "内容分发网络"),
    ("VPC", "专有网络"),
    ("RDS", "云数据库RDS"),
    ("serverless", "函数计算"),
    ("NAS", "文件存储NAS"),
    ("ACK", "容器服务Kubernetes版"),
    ("SLS", "日志服务"),
    ("RAM", "访问控制"),
    ("KMS", "密钥管理服务"),
    ("WAF", "Web应用防火墙"),
    ("DNS", "域名解析"),
    ("PolarDB", "云原生数据库PolarDB"),
    ("MaxCompute", "ODPS"),
    ("MaxCompute", "大数据计算"),
    # High-frequency concept terms (document titles may use either form)
    ("CORS", "跨域"),
    ("security group", "安全组"),
    ("snapshot", "快照"),
]


# Low-result expansion retry threshold: when the first round returns fewer items than this value and the dictionary can generate a different expanded query, retry once with the expanded term
EXPAND_RETRY_THRESHOLD = 2


# CamelCase error-code shape (e.g. SignatureDoesNotMatch / InvalidAccessKeyId):
# at least two capitalized segments, naturally containing internal capitals
ERROR_CODE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+$")


# Chinese colloquial error wording -> canonical CamelCase error code (hint bridge only):
# users often paste a translated/colloquial description instead of the code; the hint points
# them at the verbatim code form, which is what documentation search actually matches.
ERROR_CODE_CN_HINTS = [
    ("签名不匹配", "SignatureDoesNotMatch"),
    ("签名错误", "SignatureDoesNotMatch"),
    ("访问密钥不存在", "InvalidAccessKeyId.NotFound"),
    ("密钥不存在", "InvalidAccessKeyId.NotFound"),
    ("请求被限流", "Throttling"),
    ("没有权限", "Forbidden.RAM"),
    ("资源不存在", "InvalidParameter.NotFound"),
]


def _build_synonym_lookup(pairs) -> dict:
    """Build a bidirectional dictionary from alias pairs: each alias (lowercased key) maps to all aliases of its group (original casing preserved)."""
    lookup = {}
    for a, b in pairs:
        for alias in (a, b):
            lookup.setdefault(alias.lower(), set()).update((a, b))
    return lookup


_SYNONYM_LOOKUP = _build_synonym_lookup(QUERY_SYNONYMS)


# ASCII alphanumeric boundary check: avoids false matches inside English words ("words" does not match rds),
# while still allowing direct adjacency to CJK text (the alias still matches inside a longer Chinese phrase)
_SYNONYM_PATTERNS = {
    key: re.compile(r"(?<![A-Za-z0-9])" + re.escape(key) + r"(?![A-Za-z0-9])", re.IGNORECASE)
    for key in _SYNONYM_LOOKUP
}


def _expand_query(keyword: str) -> str | None:
    """Alias-level expansion: generate one expanded query different from the original; return None on no dictionary hit.

    Deterministic strategy: take the longest alias matched in the query, then append the first not-yet-present
    alias of the same group (shortest first; sorted to guarantee determinism) to the end of the original query
    (append-only; the original text is never removed; no general translation).
    """
    matched = [key for key, pat in _SYNONYM_PATTERNS.items() if pat.search(keyword)]
    if not matched:
        return None
    best = max(matched, key=len)
    for alias in sorted(_SYNONYM_LOOKUP[best], key=lambda a: (len(a), a)):
        if alias.lower() == best:
            continue
        if _SYNONYM_PATTERNS[alias.lower()].search(keyword):
            continue
        return keyword.strip() + " " + alias
    return None


def _error_code_hint(keyword: str) -> None:
    """CamelCase error-code detection: when the whole query or any token matches the error-code shape, emit an INFO hint on stderr.
    Hint only; the search behavior itself is unchanged (error codes are still searched verbatim).
    All-uppercase abbreviations (e.g. KMS/WAF) are not CamelCase error-code shapes and never trigger the hint.
    Chinese colloquial error wording triggers the hint bridge: it suggests the canonical CamelCase
    code but never rewrites the query (error codes must be searched verbatim)."""
    stripped = keyword.strip()
    tokens = [t for t in re.split(r"\s+", stripped) if t]
    for cand in [stripped] + tokens:
        if ERROR_CODE_RE.match(cand) and not cand.isupper():
            print("INFO: suspected error code detected; it will be searched verbatim as an error code. "
                  "For the contract-level error code list of a specific API, use api-info <product> <ApiName>",
                  file=sys.stderr)
            return
    for phrase, code in ERROR_CODE_CN_HINTS:
        if phrase in stripped:
            print(f"INFO: colloquial error wording detected; if it refers to the '{code}' error, "
                  f"search the code verbatim (e.g. search \"{code}\") for narrative troubleshooting docs",
                  file=sys.stderr)
            return


def _merge_unique(primary: list, extra: list) -> list:
    """Merge two rounds of search results and dedupe by normalized URL (first-round order preserved; new second-round entries appended)."""
    seen = set()
    merged = []
    for rec in list(primary) + list(extra):
        key = _normalize_url(rec["url"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(rec)
    return merged


def _expand_retry(initial: list, keyword: str, run_search) -> list:
    """Low-result expansion retry: when the first round has fewer than EXPAND_RETRY_THRESHOLD results and
    _expand_query can generate a different expanded query, retry once with the expanded term, then merge and
    dedupe with the first-round results; on no dictionary hit or retry failure/empty result, return unchanged.
    The retry inherits the current path semantics (carried by the run_search(kw) closure)."""
    if len(initial) >= EXPAND_RETRY_THRESHOLD:
        return initial
    expanded = _expand_query(keyword)
    if expanded is None:
        return initial
    print(f"INFO: insufficient results for the original query ({len(initial)}); retried with expanded term: {expanded}", file=sys.stderr)
    retry = run_search(expanded.lower())
    return _merge_unique(initial, retry or [])


# Numeric help-center error codes (the OSS shapes 0003-00001104 and a bare 8-digit code) and
# quota/parameter/permission phrasing: these are answered authoritatively by the OpenAPI
# metadata leg rather than by narrative documentation, and none of them is reliably present in
# an llms.txt title or summary.
_NUMERIC_CODE_RE = re.compile(r"(?:^|[\s/,])(?:\d{4}-\d{8}|\d{8})(?=$|[\s,.])")
_PRECISION_TERM_RE = re.compile(
    r"\b(?:quota|quotas|limit|limits|parameter|parameters|permission point|ram action|"
    r"error code|request id|throttl\w*|qps)\b", re.IGNORECASE)


# An error code may carry a dotted suffix (InvalidAccessKeyId.NotFound); ERROR_CODE_RE above is
# the stricter shape used to decide whether to hint at a verbatim code search, and the boundary
# hint needs the wider one.
_CODEISH_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(?:[A-Z][A-Za-z0-9]*)+(?:\.[A-Za-z0-9]+)*$")


def is_precision_query(keyword: str) -> bool:
    """Whether a query asks for contract-level detail an index scan structurally cannot answer.

    Used by the empty-result advice (F7): CamelCase codes (AccessDenied,
    InvalidAccessKeyId.NotFound), numeric help-center codes (0003-00001104) and
    quota/parameter/permission phrasing are exactly the classes measured to recall nothing from
    a title+summary substring scan, so a caller left with "no results" must be pointed at the
    metadata leg instead of concluding that the documentation is missing.
    """
    text = (keyword or "").strip()
    if not text:
        return False
    if _NUMERIC_CODE_RE.search(text):
        return True
    if _PRECISION_TERM_RE.search(text):
        return True
    for token in (t for t in re.split(r"[\s,;:()]+", text) if t):
        if _CODEISH_RE.match(token) and not token.isupper():
            return True
        if ERROR_CODE_RE.match(token) and not token.isupper():
            return True
    return False


# ---------------------------------------------------------------------------
# F6: bilingual query vocabulary (zero-credential, no translation service)
# ---------------------------------------------------------------------------

# Chinese documentation term -> the term the English corpus actually uses. Only high-confidence
# pairs belong here: a wrong mapping silently changes what is being asked for, which is worse
# than no mapping at all, so every entry below names a product concept rather than a general word.
CN_EN_TERMS = {
    "\u8de8\u57df\u8bbf\u95ee": "cross-origin resource sharing",
    "\u8de8\u57df": "CORS",
    "\u9884\u7b7e\u540d": "presigned URL",
    "\u7b7e\u540d\u9519\u8bef": "signature does not match",
    "\u7b7e\u540d": "signature",
    "\u4f20\u8f93\u52a0\u901f": "transfer acceleration",
    "\u751f\u547d\u5468\u671f": "lifecycle",
    "\u5b58\u50a8\u7c7b\u578b": "storage class",
    "\u6301\u4e45\u6027": "durability",
    "\u5bb9\u707e": "disaster recovery",
    "\u591a\u7248\u672c": "versioning",
    "\u5206\u7247\u4e0a\u4f20": "multipart upload",
    "\u65ad\u70b9\u7eed\u4f20": "resumable upload",
    "\u76d1\u542c\u89c4\u5219": "event notification rule",
    "\u8bbf\u95ee\u63a7\u5236": "access control",
    "\u6743\u9650\u7b56\u7565": "RAM policy",
    "\u4e34\u65f6\u51ed\u8bc1": "Security Token Service credentials",
    "\u5b89\u5168\u7ec4": "security group",
    "\u5f39\u6027\u516c\u7f51IP": "elastic IP address",
    "\u5e26\u5bbd": "bandwidth",
    "\u6d41\u91cf": "traffic",
    "\u5e26\u5bbd\u5c01\u9876": "bandwidth cap",
    "\u8d44\u6e90\u7ec4": "resource group",
    "\u6807\u7b7e": "tag",
    "\u5feb\u7167": "snapshot",
    "\u81ea\u5b9a\u4e49\u955c\u50cf": "custom image",
    "\u5b9e\u4f8b\u89c4\u683c": "instance type",
    "\u4e91\u76d8": "cloud disk",
    "\u6269\u5bb9": "resize",
    "\u8d1f\u8f7d\u5747\u8861": "load balancing",
    "\u76d1\u542c": "listener",
    "\u5065\u5eb7\u68c0\u67e5": "health check",
    "\u57df\u540d\u89e3\u6790": "DNS resolution",
    "\u5907\u6848": "ICP filing",
    "\u8bc1\u4e66": "certificate",
    "\u52a0\u5bc6": "encryption",
    "\u65e5\u5fd7": "logs",
    "\u5ba1\u8ba1": "audit",
    "\u62a5\u9519": "error",
    "\u9519\u8bef\u7801": "error code",
    "\u914d\u989d": "quota",
    "\u9650\u6d41": "throttling",
}

# Longest terms first: a shorter term must never cut a longer one in half.
_CN_EN_SORTED = sorted(CN_EN_TERMS, key=len, reverse=True)


def translate_query_for_english(keyword: str):
    """Rewrite a Chinese query with English documentation vocabulary (F6).

    Returns (rewritten_query, mapped_terms). A query nothing can be mapped for keeps
    mapped_terms=0, and the caller must then refuse the English full-text leg rather than send a
    Chinese query at it: measured on 2026-09-08, that combination is accepted by the endpoint
    without an error and answers with unrelated hits or a fake whole-corpus match.
    """
    text = (keyword or "").strip()
    if not text:
        return "", 0
    mapped = 0
    out = text
    for term in _CN_EN_SORTED:
        if term in out:
            out = out.replace(term, CN_EN_TERMS[term])
            mapped += 1
    out = re.sub(r"\s+", " ", out).strip()
    return out, mapped


# ---------------------------------------------------------------------------
# Relevance: scoring one index entry, ranking across products, fusing the two legs.
# ---------------------------------------------------------------------------

_INDEX_TITLE_EXACT = 4.0
_INDEX_DESC_EXACT = 2.0
_INDEX_TITLE_COVERAGE = 3.0
_INDEX_DESC_COVERAGE = 1.5
_INDEX_HAS_SUMMARY = 0.5
# A partial match must cover at least this share of the query's tokens. Without the floor, a
# single common bigram ("配置", "管理") matches a whole product index: measured 2026-09-09, a
# four-character Chinese query matched 3881 of 4359 OSS entries on the English index.
_INDEX_MIN_COVERAGE = 0.34
# Reference scale for the fusion leg: the index score that earns the full cross-leg bonus. The
# theoretical maximum of `_index_score` is 9.0 (4.0 title-exact + 3.0 full title coverage + 1.5
# full summary coverage + 0.5 has-summary); a title-exact hit with complete title coverage
# measures 7.5, so 8.0 keeps a genuinely on-topic entry at the whole bonus while a weak
# bigram-only match (around 2.0) earns a quarter of it.
_INDEX_FUSION_FULL_SCORE = 8.0
# Tokens of a query that carry no topical meaning; matching on them produces noise.
_INDEX_STOP_TOKENS = {"the", "a", "an", "of", "to", "for", "and", "in", "on", "with", "how",
                     "do", "i", "is", "are", "what", "please", "一下", "如何", "怎么", "什么是"}


def _index_tokens(query: str) -> list:
    """Meaningful matching units of a query: latin words, and CJK character bigrams.

    CJK text is split into overlapping two-character units because Chinese documents have no word
    boundaries and a whole-string substring match misses every query that is phrased differently
    from the title (measured: '什么是传输加速' and '跨域访问怎么配' recalled zero entries before F3,
    while the individual characters appear all over the index). Bigrams keep the match localised
    instead of degrading into single-character noise.
    """
    text = (query or "").strip().lower()
    if not text:
        return []
    tokens = [t for t in re.split(r"[^0-9a-z_\u4e00-\u9fff]+", text) if t]
    out = []
    for token in tokens:
        if token in _INDEX_STOP_TOKENS:
            continue
        if re.search(r"[\u4e00-\u9fff]", token):
            if len(token) == 1:
                out.append(token)
            else:
                out.extend(token[i:i + 2] for i in range(len(token) - 1))
        else:
            out.append(token)
    return out


def _index_matches(term: str, text: str) -> bool:
    """Match literal terms with ASCII word edges; CJK substring matching stays unchanged."""
    if not term:
        return False
    pattern = re.escape(term)
    if re.match(r"[a-z0-9_]", term[0], re.IGNORECASE):
        pattern = r"(?<![a-z0-9_])" + pattern
    if re.match(r"[a-z0-9_]", term[-1], re.IGNORECASE):
        pattern += r"(?![a-z0-9_])"
    return re.search(pattern, text, re.IGNORECASE | re.ASCII) is not None


def _index_score(query: str, title: str, desc: str) -> float:
    """Relevance of one index entry to a query (0.0 means "not a hit", same as before F3)."""
    title_l = (title or "").lower()
    desc_l = (desc or "").lower()
    whole = (query or "").strip().lower()
    score = 0.0
    if _index_matches(whole, title_l):
        score += _INDEX_TITLE_EXACT
    elif _index_matches(whole, desc_l):
        score += _INDEX_DESC_EXACT
    tokens = _index_tokens(whole)
    if tokens:
        uniq = list(dict.fromkeys(tokens))
        title_hits = sum(1 for t in uniq if _index_matches(t, title_l))
        desc_hits = sum(1 for t in uniq if _index_matches(t, desc_l))
        # A pure partial match has to carry enough of the query to be about it at all; an exact
        # hit on the whole query is already scored above and is kept whatever the coverage is.
        best_ratio = max(title_hits, desc_hits) / len(uniq)
        if score == 0.0 and best_ratio < _INDEX_MIN_COVERAGE:
            return 0.0
        score += _INDEX_TITLE_COVERAGE * title_hits / len(uniq)
        score += _INDEX_DESC_COVERAGE * desc_hits / len(uniq)
    if score and (desc or "").strip():
        score += _INDEX_HAS_SUMMARY
    return round(score, 4)


def _index_scored_hits(product: str, text: str, keyword: str) -> list:
    """Collect the matching entries of one index as `[(score, record)]`, best first (F3).

    The score is kept here because two callers need different things from it: the unscoped scan
    has to compare candidates across products, and the fusion leg has to weigh an index-leg hit
    against a full-text rank. Records themselves stay score-free so `--json` keeps its shape.
    The sort is stable, so equally scored entries keep their catalogue order.
    """
    scored = []
    for title, url, desc in _DOC_ENTRY_RE.findall(text):
        score = _index_score(keyword, title, desc)
        if score > 0:
            scored.append((score, {"product": product, "title": title, "url": url,
                                   "desc": desc[:120], "source": "index"}))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


def _index_hits(product: str, text: str, keyword: str) -> list:
    """The matching entries of one index, ordered by relevance; records only, no score field.

    Records are truncated by the caller after this ordering.
    """
    return [record for _score, record in _index_scored_hits(product, text, keyword)]


def _merge_scored_scans(batches: list) -> list:
    """Merge per-product scored scans of an unscoped search into one relevance-ordered list.

    Before this existed the unscoped index leg concatenated products in master-index order, so a
    weak bigram match inside an early product outranked an exact title hit in a later one (measured
    2026-09-09: an unscoped Chinese query for "server side encryption" ranked an API endpoint-list
    page above the object-storage encryption documents). The sort is stable, so equal scores keep
    the previous catalogue order and a rerun of the same candidates is deterministic.
    """
    pooled = []
    for batch in batches:
        pooled.extend(batch or [])
    pooled.sort(key=lambda pair: pair[0], reverse=True)
    return [record for _score, record in pooled]


def _fuse_results(fulltext_hits: list, index_hits: list, index_scores: dict | None = None,
                  score_reference: float = 0.0) -> list:
    """Fuse full-text leg and index leg results (deterministic, no randomness).

    Score = full-text leg rank-decaying base score (N-i) + an index-leg bonus; entries hit by both
    legs score highest (source=both). Sort by score descending first; on ties, by full-text leg
    original order (index-only hits come after full-text entries, keeping index order).

    The bonus is content-aware when the caller supplies `index_scores` (index-leg url -> relevance
    score, matched against each record's own url) together with a `score_reference` scale: an index
    hit earns `bonus * (0.5 + 0.5 * min(1, score / reference))`, so a title-exact match rises above
    the tail of the full-text list while a bigram-only match cannot dominate it. The half-bonus
    floor is deliberate: the index leg matches title and summary lexically and cannot see semantic
    equivalence, so a limits/quota page whose heading omits the query words (measured 2026-09-09,
    an "ECS limits and quotas" document for a rule-count query) is still a real retrieval signal
    and must not be pushed out of the visible window by an API reference page that the full-text
    backend ranked last. Without the map every index hit earns the flat bonus, which is the
    historical behaviour and stays available for any caller that has no scores to offer. A url
    missing from the map also earns the flat bonus: an index hit is still an index hit, and
    silently dropping it would lose recall.
    """
    bonus = max(len(fulltext_hits), 1)
    weighted = bool(index_scores) and score_reference > 0
    scores = {}
    ranks = {}
    records = {}
    for i, h in enumerate(fulltext_hits):
        key = _normalize_url(h["url"])
        scores[key] = scores.get(key, 0) + (len(fulltext_hits) - i)
        ranks.setdefault(key, i)
        records[key] = {"product": h["product"], "title": h["title"],
                        "url": h["url"], "desc": h["desc"], "source": "fulltext"}
        if h.get("updated"):
            records[key]["updated"] = h["updated"]
    for h in index_hits:
        key = _normalize_url(h["url"])
        gain = bonus
        if weighted:
            raw = index_scores.get(h["url"])
            if raw is not None:
                gain = round(bonus * (0.5 + 0.5 * min(1.0, max(0.0, raw / score_reference))), 4)
        scores[key] = scores.get(key, 0) + gain
        ranks.setdefault(key, len(fulltext_hits))
        if key not in records:
            records[key] = {"product": h["product"], "title": h["title"],
                            "url": h["url"], "desc": h["desc"], "source": "index"}
        else:
            records[key]["source"] = "both"
            if not records[key]["desc"]:
                records[key]["desc"] = h["desc"]
    order = sorted(scores.keys(), key=lambda k: (-scores[k], ranks[k]))
    return [records[k] for k in order]
