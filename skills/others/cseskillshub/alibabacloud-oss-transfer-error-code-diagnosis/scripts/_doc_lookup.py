#!/usr/bin/env python3
"""
_doc_lookup.py -- Runtime official-doc verification for this OSS skill
=======================================================================
SECURITY / COMPLIANCE:
  * Pure standard library (urllib/re/json/os/time/argparse/sys only); no
    requirements.txt additions, no data files (MUST 1.1.2: the topic
    vocabulary below is an embedded constant).
  * Zero credentials: never reads env credentials, never calls STS, never
    touches the aliyun CLI; only fetches PUBLIC content from
    help.aliyun.com (domain whitelist enforced).
  * Read-only enhancement: every failure path degrades instead of raising.
    Offline or unreachable docs yield matched=False + a DEGRADED note plus a
    stderr [WARN] trace; the caller's main diagnosis is never blocked.
  * Timeouts (platform 7.6.1): index leg 15s, each body fetch 15s, total
    body-leg budget 45s.

Mechanism (two legs, distilled from aliyun-help-search):
  Index leg: fetch https://help.aliyun.com/zh/oss/llms.txt once and cache
    it under ~/.cache/oss-skill-docs/oss-llms.txt (TTL 3 days, atomic
    write). Cache hit => zero network requests for the index leg. A fetch
    failure with an expired cache still uses the stale cache (noted);
    without any cache it degrades offline.
  Body leg: for the top-scored hits only, read the .md URL directly and
    extract a cleaned first-paragraph excerpt (<= 500 Unicode chars); a
    failed body leg falls back to the index-line description excerpt.

Matching is deterministic: activated keywords (case-insensitive substring
hits of SKILL_DOC_TOPICS inside the question) score every index entry as
2 x (keyword in title) + 1 x (keyword in description); the top 3 by
(score desc, index order) are returned.

Self-test entry (standalone):
    python3 _doc_lookup.py --question "<customer original wording>"
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

LLMS_INDEX_URL = "https://help.aliyun.com/zh/oss/llms.txt"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "oss-skill-docs")
CACHE_FILE = os.path.join(CACHE_DIR, "oss-llms.txt")
CACHE_TTL_SECONDS = 3 * 24 * 3600  # 3 days, judged by file mtime
FETCH_TIMEOUT = 15                 # seconds, per single request
BODY_TOTAL_BUDGET = 45             # seconds, total for the body leg
MAX_DOCS = 3
EXCERPT_LIMIT = 500                # Unicode characters
ALLOWED_BODY_HOST = "help.aliyun.com"
# UA carried over from aliyun_help.py (the measured-working implementation).
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QoderWork/1.0"

# Only '.md' entries are collected (same regex as aliyun_help.py list-docs).
_INDEX_LINE_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\):\s*(.*)",
                            re.MULTILINE)

# ---------------------------------------------------------------------------
# Skill topic vocabulary (embedded constant, MUST 1.1.2: no data files).
# keywords: case-insensitive substring matched against the customer question;
# hint: human label of the topic (documentation aid only, not used for
# scoring). Tailored to the transfer-error-code-diagnosis scenario.
# NOTE (platform MUST 4.1.2): the Chinese strings inside SKILL_DOC_TOPICS are
# functional match tokens for Chinese-speaking customers' questions (this
# skill runs on Chinese tickets); they are runtime data, not documentation
# prose. All documentation prose (SKILL.md body / references/*.md) is
# English-only, and the inline boundary assertions below use ASCII fixtures
# because the matching logic is language-neutral.
# ---------------------------------------------------------------------------
SKILL_DOC_TOPICS = [
    {"keywords": ["\u8de8\u57df", "cors"], "hint": "cross-origin"},
    {"keywords": ["\u4e0a\u4f20", "upload"], "hint": "upload"},
    {"keywords": ["\u4e0b\u8f7d", "download"], "hint": "download"},
    {"keywords": ["403", "accessdenied", "accessforbidden", "\u62d2\u7edd"],
     "hint": "permission-denied"},
    {"keywords": ["\u8d85\u65f6", "timeout"], "hint": "timeout"},
    {"keywords": ["\u7b7e\u540d", "signature"], "hint": "signature"},
    {"keywords": ["\u62a5\u9519", "\u9519\u8bef", "\u5931\u8d25"], "hint": "error-troubleshooting"},
    {"keywords": ["\u5206\u7247", "\u7eed\u4f20", "multipart"], "hint": "multipart"},
    {"keywords": ["\u9650\u5236", "\u5927\u5c0f"], "hint": "limits"},
]


# ---------------------------------------------------------------------------
# Pure helpers (normal / boundary / invalid assertions below each)
# ---------------------------------------------------------------------------

def _truncate(text, limit=EXCERPT_LIMIT):
    """Strip and truncate to `limit` Unicode chars; non-str degrades to ''."""
    if not isinstance(text, str):
        return ""
    return text.strip()[:limit]


assert _truncate("abc") == "abc"                                   # normal
assert _truncate("  padded  ") == "padded"                         # boundary
assert _truncate("x" * 500) == "x" * 500                           # boundary: exact limit
assert _truncate("x" * 601) == "x" * 500                           # normal: over limit
assert _truncate("") == ""                                         # invalid: empty
assert _truncate(None) == ""                                       # invalid: non-str
assert _truncate(123) == ""                                        # invalid: non-str


def _is_degraded_url(url):
    """True => the URL must NOT be fetched (whitelist guard vs URL
    injection). Only https:// URLs on help.aliyun.com ending in .md pass."""
    if not isinstance(url, str) or not url.strip():
        return True
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except ValueError:
        return True
    if parsed.scheme != "https":
        return True
    if parsed.netloc.lower() != ALLOWED_BODY_HOST:
        return True
    if not parsed.path.endswith(".md"):
        return True
    return False


assert _is_degraded_url("https://help.aliyun.com/zh/oss/user-guide.md") is False  # normal
assert _is_degraded_url("HTTPS://HELP.ALIYUN.COM/zh/oss/a.md") is False            # boundary: case
assert _is_degraded_url("http://help.aliyun.com/zh/oss/a.md") is True              # invalid: scheme
assert _is_degraded_url("https://help.aliyun.com.evil.com/a.md") is True           # invalid: host spoof
assert _is_degraded_url("https://evil.com/help.aliyun.com/a.md") is True           # invalid: host path
assert _is_degraded_url("https://help.aliyun.com/zh/oss/page.html") is True        # invalid: not .md
assert _is_degraded_url("") is True                                                # invalid: empty
assert _is_degraded_url(None) is True                                              # invalid: non-str


def _score_entry(title, desc, activated):
    """Deterministic entry score: 2 x (#activated keywords in title)
    + 1 x (#activated keywords in description). Pure."""
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


assert _score_entry("OSS upload objects", "how to upload files", ["upload"]) == 3  # normal: title+desc
assert _score_entry("upload objects", "", ["upload"]) == 2                      # normal: title only
assert _score_entry("download objects", "upload files", ["upload"]) == 1        # normal: desc only
assert _score_entry("download objects", "download files", ["upload"]) == 0      # boundary: no hit
assert _score_entry("upload", "upload", []) == 0                                # invalid: no activated
assert _score_entry("", "", ["upload"]) == 0                                    # invalid: empty entry
assert _score_entry(None, None, ["upload"]) == 0                                # invalid: None fields
assert _score_entry("Upload objects", "how to upload", ["upload"]) == 3  # normal: ascii


def _activate(question, skill_topics):
    """Activated keyword set: keywords of skill_topics occurring in the
    question (case-insensitive substring, first-seen order, deduplicated)."""
    q = question.lower() if isinstance(question, str) else ""
    activated = []
    seen = set()
    for topic in skill_topics or []:
        for kw in topic.get("keywords", []):
            k = kw.lower()
            if k and k in q and k not in seen:
                seen.add(k)
                activated.append(k)
    return activated


assert _activate("OSS upload failed what to do",
                 [{"keywords": ["upload", "failed"]}, {"keywords": ["download"]}]) == ["upload", "failed"]  # normal
assert _activate("CORS issue", [{"keywords": ["cors"]}]) == ["cors"]                          # normal: case
assert _activate("upload upload", [{"keywords": ["upload"]}]) == ["upload"]                   # boundary: dedupe
assert _activate("", [{"keywords": ["upload"]}]) == []                                         # invalid: empty q
assert _activate(None, None) == []                                                           # invalid: None
assert _activate("upload", [{"keywords": [""]}]) == []                                         # invalid: empty kw


def _clean_excerpt(md_text, limit=EXCERPT_LIMIT):
    """Clean a Markdown body into a <= limit excerpt: drop image syntax,
    resolve link syntax to the anchor text, strip inline HTML tags
    (measured: OSS docs open with <br /> lines), collapse consecutive
    blank lines, then take the first non-empty non-heading paragraph."""
    if not isinstance(md_text, str):
        return ""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md_text)        # images out
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # links -> text
    text = re.sub(r"<[^>\n]+>", "", text)                      # html tags out
    text = re.sub(r"\n{3,}", "\n\n", text)                     # collapse blanks
    for para in text.split("\n\n"):
        lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
        lines = [ln for ln in lines if not ln.startswith("#")]
        if not lines:
            continue
        return _truncate(" ".join(lines), limit)
    return ""


assert _clean_excerpt("# Title\n\nFirst paragraph.\nSecond line.") == "First paragraph. Second line."  # normal
assert _clean_excerpt("![img](https://a/b.png)\n\nBody.") == "Body."                  # boundary: image stripped
assert _clean_excerpt("[anchor text](https://x.y/z)\n") == "anchor text"              # boundary: link resolved
assert _clean_excerpt("<br />\n\nBody.") == "Body."                                   # boundary: html tag skipped
assert _clean_excerpt("# Heading only") == ""                                         # boundary: heading only
assert _clean_excerpt("") == ""                                                    # invalid: empty
assert _clean_excerpt(None) == ""                                                  # invalid: non-str
assert len(_clean_excerpt("w" * 600)) == 500                                      # normal: limit cut


# ---------------------------------------------------------------------------
# Network helpers (all failures degrade; nothing here may raise upward)
# ---------------------------------------------------------------------------

def _is_err(text):
    """Error-marker check carried over from aliyun_help.py."""
    return text.startswith("[HTTP ") or text.startswith("[Error]")


def _looks_like_html(text):
    """200-but-SPA detection carried over from aliyun_help.py: help.aliyun
    .com returns an HTML shell for dead slugs; never use that as excerpt."""
    head = text.lstrip()[:300].lower()
    return head.startswith("<!doctype") or head.startswith("<html") \
        or "<html" in head


def _fetch_text(url, timeout=FETCH_TIMEOUT):
    """Fetch one URL as UTF-8 text. Raises on any failure (callers catch)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_index(text):
    """Parse llms.txt into [(title, url, desc)] (.md entries only)."""
    return [(t, u, d) for t, u, d in _INDEX_LINE_RE.findall(text or "")]


def _atomic_write_cache(text):
    """Write-then-rename so a partial write can never corrupt the cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = "%s.tmp.%d" % (CACHE_FILE, os.getpid())
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, CACHE_FILE)


def _load_index():
    """Index leg. Returns (entries|None, note).

    entries=None means the index is unusable (offline, no cache at all);
    note carries the DEGRADED reason when one applies (stale-cache reuse).
    A fresh cache hit performs zero network requests.
    """
    cache_text = None
    cache_mtime = None
    try:
        if os.path.isfile(CACHE_FILE):
            cache_mtime = os.path.getmtime(CACHE_FILE)
            with open(CACHE_FILE, "r", encoding="utf-8",
                      errors="replace") as handle:
                cache_text = handle.read()
    except OSError:
        cache_text = None

    if cache_text and cache_mtime is not None \
            and (time.time() - cache_mtime) < CACHE_TTL_SECONDS:
        return _parse_index(cache_text), None

    try:
        text = _fetch_text(LLMS_INDEX_URL)
        if not text.strip():
            raise RuntimeError("empty index response")
        entries = _parse_index(text)
        if not entries:
            raise RuntimeError("no .md entries parsed from index")
        _atomic_write_cache(text)
        return entries, None
    except Exception as exc:
        if cache_text:
            return _parse_index(cache_text), (
                "DEGRADED: stale-cache (index fetch failed: %s)" % exc)
        return None, "DEGRADED: offline or index fetch failed"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_config_topic(question, skill_topics):
    """Verify a customer question against the official OSS doc index.

    Returns a dict with the constant four keys, never raises:
      {"matched": bool, "docs": [{title,url,excerpt}] (<=3),
       "source": "llms-index", "note": None | "DEGRADED: <reason>"}
    """
    result = {"matched": False, "docs": [], "source": "llms-index",
              "note": None}
    q = question.strip() if isinstance(question, str) else ""
    if not q:
        return result
    try:
        activated = _activate(q, skill_topics)
        if not activated:
            return result

        entries, note = _load_index()
        if entries is None:
            result["note"] = note
            print("[WARN] doc lookup degraded: %s" % note, file=sys.stderr)
            return result

        scored = []
        for order, (title, url, desc) in enumerate(entries):
            score = _score_entry(title, desc, activated)
            if score > 0:
                scored.append((score, order, title, url, desc))
        # Deterministic: score desc, then original index order (stable).
        scored.sort(key=lambda row: (-row[0], row[1]))
        top = scored[:MAX_DOCS]
        if not top:
            result["note"] = note
            if note:
                print("[WARN] doc lookup degraded: %s" % note,
                      file=sys.stderr)
            return result

        body_failed = False
        start = time.monotonic()
        docs = []
        for _score, _order, title, url, desc in top:
            excerpt = ""
            got_body = False
            within_budget = (time.monotonic() - start) <= (
                BODY_TOTAL_BUDGET - FETCH_TIMEOUT)
            if not _is_degraded_url(url) and within_budget:
                try:
                    body = _fetch_text(url)
                    if not _is_err(body) and not _looks_like_html(body):
                        excerpt = _clean_excerpt(body)
                        got_body = bool(excerpt)
                except Exception:
                    got_body = False
            if not got_body:
                body_failed = True
                excerpt = _truncate(desc)
            docs.append({"title": title, "url": url, "excerpt": excerpt})

        result["matched"] = True
        result["docs"] = docs
        result["note"] = note
        if result["note"] is None and body_failed:
            result["note"] = "DEGRADED: body fetch failed, excerpt from index"
        if result["note"]:
            print("[WARN] doc lookup degraded: %s" % result["note"],
                  file=sys.stderr)
        return result
    except Exception as exc:  # last-resort guard: never raise to the caller
        note = "DEGRADED: %s" % exc
        print("[WARN] doc lookup degraded: %s" % exc, file=sys.stderr)
        result["note"] = note
        return result


# ---------------------------------------------------------------------------
# Self-test entry (standalone usage)
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Runtime official-doc verification (llms-index) for "
                    "this OSS skill; pure stdlib, read-only, never blocks.")
    parser.add_argument("--question", required=True,
                        help="Customer original wording to verify")
    args = parser.parse_args(argv)
    outcome = lookup_config_topic(args.question, SKILL_DOC_TOPICS)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
