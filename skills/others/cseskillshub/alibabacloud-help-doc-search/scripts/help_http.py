#!/usr/bin/env python3
"""Transport layer: the shared GET helper, the redirect policy and corpus guards.

Both portals answer HTTP 200 for several failure modes (an empty body, a WAF
interstitial, an HTML 404 shell), so a status code proves nothing: every caller must run
the body through the guards exported here.
"""

from __future__ import annotations

import json
import re
import sys
import time
import random
import urllib.error
import urllib.parse
import urllib.request

from help_core import (
    LLMS_MAX_BYTES,
    SITES,
    TIMEOUT,
    UA,
    effective_timeout,
)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that never follows: a 3xx surfaces as an HTTPError instead.

    Needed by the llms.txt index leg (guard S13). The international site answers an
    unsupported language with a 302 to the English master (ko/de/es/th/vi/tr) or to an
    empty body (pt/ru/it); both look like a perfectly successful English fetch when
    redirects are followed, so the language fallback would go completely unnoticed.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def fetch_response(url: str, *, allow_redirects: bool = True, timeout: int = 0,
                   max_bytes: int = 0, attempts: int = 2, backoff_base: float = 1.0):
    """Fetch one URL with a retry budget and report why it failed (N2/N4).

    Returns (text, meta) where meta carries the HTTP status (None when no response was ever
    received), a parsed Retry-After delay and a truncated flag. Unlike fetch() this never folds
    a failure into a string, so a caller can tell a rate limit from an outage and honour the
    server's own pacing hint instead of hammering it.

    Retry policy: network-level failures and HTTP 429/5xx are retried up to 'attempts' times
    with exponential backoff (backoff_base * 2**i, plus up to 250 ms of jitter); a 4xx other
    than 429 is final, because a bad path or a bad parameter will not fix itself.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    opener = urllib.request.urlopen if allow_redirects else _NO_REDIRECT_OPENER.open
    deadline = effective_timeout(timeout or TIMEOUT)
    meta = {"status": None, "retry_after": None, "truncated": False, "error": ""}
    for i in range(max(1, attempts)):
        try:
            with opener(req, timeout=deadline) as resp:
                meta["status"] = resp.status
                data = resp.read()
                if max_bytes > 0 and len(data) > max_bytes:
                    data = data[:max_bytes]
                    meta["truncated"] = True
                return data.decode("utf-8", errors="replace"), meta
        except urllib.error.HTTPError as e:
            meta["status"] = e.code
            meta["retry_after"] = _parse_retry_after(getattr(e, "headers", None))
            meta["error"] = f"[HTTP {e.code}] {e.reason}"
            retryable = e.code == 429 or 500 <= e.code < 600
            if not retryable or i + 1 >= attempts:
                return meta["error"], meta
        except Exception as e:
            meta["status"] = None
            meta["error"] = f"[Error] {e}"
            if i + 1 >= attempts:
                return meta["error"], meta
        delay = meta["retry_after"] if meta["retry_after"] else backoff_base * (2 ** i)
        time.sleep(min(float(delay), 8.0) + random.uniform(0, 0.25))
    return meta["error"] or "[Error] unreachable", meta


def _parse_retry_after(headers):
    """Seconds advertised by a Retry-After header (delay form only), or None."""
    if not headers:
        return None
    raw = headers.get("Retry-After")
    if not raw:
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def fetch(url: str, max_bytes: int = 0, allow_redirects: bool = True, timeout: int = 0) -> str:
    """Fetch URL content as text.

    allow_redirects=False is used by the llms.txt index leg so that a 302 language fallback
    is reported as an error instead of silently serving English content (guard S13).
    timeout defaults to TIMEOUT (15 s for the China site); the international index leg passes
    its own larger value because its indexes are 4-6 times slower to serve.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    opener = urllib.request.urlopen if allow_redirects else _NO_REDIRECT_OPENER.open
    try:
        with opener(req, timeout=effective_timeout(timeout or TIMEOUT)) as resp:
            data = resp.read()
            if max_bytes > 0:
                data = data[:max_bytes]
            return data.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] {e.reason}"
    except Exception as e:
        return f"[Error] {e}"


def _is_err(text: str) -> bool:
    """Determine whether a fetch result is an error marker (avoids the legacy startswith('[') falsely matching normal Markdown)."""
    return text.startswith("[HTTP ") or text.startswith("[Error]")


def _fetch_index(url: str, site: str, lang: str) -> str:
    """Fetch an llms.txt index with the per-site timeout, redirect policy and retry budget.

    Redirects are never followed on the international site (guard S13): it answers an
    unsupported language with a 302 to the English master (ko/de/es/th/vi/tr) or to an empty
    body (pt/ru/it), and urllib follows redirects by default, so the fallback would otherwise
    be served as if it were the requested language with no HTTP signal at all. A 3xx is
    reported explicitly instead. The China site keeps following redirects because its slug
    space contains legitimate 301s to a canonical slug and it hosts no language that silently
    falls back to another one.

    The international indexes are 4-6 times slower to serve (ja/oss measured avg 5.18 s,
    max 5.53 s), hence the larger per-site timeout. Since N2 the retry budget is shared with
    the search legs: a network failure, a 429 or a 5xx is retried once with exponential backoff
    (honouring Retry-After when the server advertises it), while a 302 on the international site
    and any other 4xx are final because repeating them cannot change the answer. The body is
    capped at LLMS_MAX_BYTES (N4) so an unexpected giant response cannot exhaust memory.
    """
    no_redirect = site == "intl"
    text, meta = fetch_response(url, allow_redirects=not no_redirect,
                                 timeout=SITES[site]["index_timeout"],
                                 max_bytes=LLMS_MAX_BYTES, attempts=2)
    if meta.get("truncated"):
        print(f"WARN[oversize]: the llms.txt index at {url} is larger than "
              f"{LLMS_MAX_BYTES // (1024 * 1024)} MB and was truncated; entries beyond the cap "
              f"are missing from this run", file=sys.stderr)
    if no_redirect and text.startswith("[HTTP 3"):
        print(f"WARN[lang-fallback]: {url} answered '{text.splitlines()[0]}'; this language or product slug has "
              f"no corpus of its own on the international site. Redirects are never followed here, "
              f"so English content is not silently served as another language.", file=sys.stderr)
    elif _is_err(text) and (meta.get("status") == 429 or (meta.get("status") or 0) >= 500):
        print(f"WARN[rate-limit]: {url} answered HTTP {meta.get('status')} after the backoff "
              f"retry; degrading this leg rather than retrying further", file=sys.stderr)
    return text


def _looks_like_html(text: str) -> bool:
    """Detect the HTTP 200-but-HTML-page case (help.aliyun.com falls back to an SPA page when a doc moves or a slug is dead)."""
    head = text.lstrip()[:300].lower()
    return head.startswith("<!doctype") or head.startswith("<html") or "<html" in head


# The international portal answers a slug that has no llms.txt corpus with this exact 51-byte
# sentence and HTTP 200 (measured 2026-09-08 on /help/en/ahas/llms.txt and /help/en/dbfs/llms.txt).
_NO_CORPUS_RE = re.compile(r"^sorry, this product does not have llms content yet", re.IGNORECASE)


def _is_index_corpus(text: str) -> bool:
    """True only when a fetched body can really serve as an llms.txt index.

    Both portals answer a dead slug with HTTP 200 and a body that is not a corpus, in three
    shapes: an empty body (the China site, and the international site for some languages),
    the 51-byte placeholder above (the international site), and - intermittently, under rate
    limiting - the ~92 KB WAF interstitial HTML page, which the international portal also
    serves on '/help/**' paths and not only on the www root. Caching any of them would keep a
    slug dead for the whole TTL and would hide a transient WAF answer behind a cached corpus,
    so they are recognised here and never written to the cache.
    """
    if _is_err(text) or not text.strip():
        return False
    if _looks_like_html(text):
        return False
    return not _NO_CORPUS_RE.match(text.strip())


def _non_corpus_reason(text: str) -> str:
    """Short English reason why a fetched body is not a usable index; used in WARN traces."""
    if _is_err(text):
        return text.splitlines()[0] if text else "unknown fetch error"
    if not text.strip():
        return "HTTP 200 with an empty body"
    if _looks_like_html(text):
        return "HTTP 200 with an HTML interstitial page instead of an index (rate limiting)"
    if _NO_CORPUS_RE.match(text.strip()):
        return "HTTP 200 with the 'no LLMS content yet' placeholder instead of an index"
    return "unusable body"


def fetch_json(url: str):
    """Fetch and parse JSON; return None on failure and print the reason to stderr."""
    text = fetch(url)
    if _is_err(text):
        print(f"[request failed] {url} -> {text}", file=sys.stderr)
        return None
    if _looks_like_html(text):
        print(f"[request failed] {url} returned an HTML page (the path may not exist)", file=sys.stderr)
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[JSON parse failed] {url}: {e}", file=sys.stderr)
        return None
