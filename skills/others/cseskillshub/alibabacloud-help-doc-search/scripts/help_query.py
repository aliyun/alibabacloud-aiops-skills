#!/usr/bin/env python3
"""Query construction: product-code aliases, synonym expansion, error-code detection.

Pure string work plus stderr traces; it never issues a request (the caller injects the
search callable used by the low-result expansion retry).
"""

from __future__ import annotations

import re
import sys

from help_core import (
    PRODUCT_CODE_ALIASES,
)
from help_render import (
    _normalize_url,
)


# Bidirectional query alias/synonym dictionary (high-frequency product aliases, Chinese-English pairs):
# alias-level expansion only, no general translation. When any alias of a group appears in the query,
# the other aliases of the group can drive an expansion retry (see _expand_query).
# Confirm official naming before adding entries, and keep the mechanism notes in references/query-construction.md in sync.
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


def _normalize_product_code(product) -> str:
    """Normalize product code aliases (e.g. fc -> functioncompute).

    The alias table only contains empirically verified entries; the single source of truth is references/product-codes.md.
    When normalization happens, emit an INFO on stderr for traceability.
    """
    if not product:
        return product
    canonical = PRODUCT_CODE_ALIASES.get(product)
    if canonical:
        print(f"INFO: product code {product} normalized to {canonical}", file=sys.stderr)
        return canonical
    return product


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
