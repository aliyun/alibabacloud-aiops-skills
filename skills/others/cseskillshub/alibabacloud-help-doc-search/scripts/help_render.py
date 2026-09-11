#!/usr/bin/env python3
"""Result rendering and document-body cleaning.

HTML tables become Markdown, titles go through one fallback chain, and the
capability-boundary hints are emitted here so every leg shares the same wording.
"""

from __future__ import annotations

import json
import re
import sys
import time
import html
from html.parser import HTMLParser

from help_core import (
    DEFAULT_SITE,
    SITES,
    _annotate_scope,
    _strip_help_prefix,
)


def _strip_html(text: str) -> str:
    """Strip HTML tags, unescape entities and collapse consecutive whitespace; used to clean search snippets."""
    s = re.sub(r"<[^>]+>", "", text or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _format_updated(ts) -> str:
    """Convert gmtModifiedOrigin (millisecond timestamp) to YYYY-MM-DD; return '' when the value is missing/invalid."""
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return ""
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
    except (OverflowError, OSError, ValueError):
        return ""


class _TableHTMLParser(HTMLParser):
    """Parse a single <table> fragment into rows: list[list[str]].

    Inside cells: <a> becomes [text](href), <li> becomes a "- " line, <p>/<div>/<br> become line breaks,
    all other tags (<b>/<strong>/<code>/<span>, etc.) keep plain text only.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell = None
        self._link_href = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []
        elif self._cell is None:
            return
        elif tag == "a":
            self._link_href = dict(attrs).get("href") or ""
        elif tag == "li":
            self._cell.append("\n- ")
        elif tag in ("p", "div"):
            # <li><p> combination: a <p> immediately following the start of a list item does not add a newline, so "- " stays attached to its text
            if not (self._cell and self._cell[-1] == "\n- "):
                self._cell.append("\n")
        elif tag == "br":
            self._cell.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            if self._row is not None and self._cell is not None:
                self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr":
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "a":
            self._link_href = None

    def handle_data(self, data):
        if self._cell is None or not data:
            return
        if self._link_href is not None:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self._cell.append(f"[{text}]({self._link_href})")
        else:
            self._cell.append(data)


def _clean_table_cell(raw: str) -> str:
    """Clean cell text: fold by line, collapse whitespace within a line, join lines with <br>;
    escape pipes so the Markdown table structure is not broken."""
    lines = []
    for seg in re.sub(r"[ \t]*\n[ \t]*", "\n", raw).split("\n"):
        seg = re.sub(r"\s+", " ", seg).strip()
        if seg:
            lines.append(seg)
    return "<br>".join(lines).replace("|", "\\|")


def _table_to_markdown(table_html: str) -> str:
    """Convert a single <table> fragment to a Markdown table; on structural anomalies (parse failure or too few rows)
    raise ValueError so the caller can degrade to plain text. The first row becomes the header (actual doc header rows carry <b>)."""
    parser = _TableHTMLParser()
    parser.feed(table_html)
    parser.close()
    rows = parser.rows
    if len(rows) < 2:
        raise ValueError("table rows insufficient")
    width = max(len(r) for r in rows)
    lines = []
    for i, row in enumerate(rows):
        cells = [_clean_table_cell(c) for c in row]
        cells += [""] * (width - len(cells))
        lines.append("| " + " | ".join(cells) + " |")
        if i == 0:
            lines.append("|" + "---|" * width)
    return "\n".join(lines)


_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.DOTALL | re.IGNORECASE)


def _convert_html_tables(text: str) -> str:
    """Convert all <table> fragments in the body to Markdown tables; when a single table fails to convert,
    degrade it to _strip_html plain text without affecting the rest of the content."""
    def _repl(m):
        try:
            return _table_to_markdown(m.group(0))
        except Exception:
            return _strip_html(m.group(0))
    return _TABLE_RE.sub(_repl, text)


_NUMERIC_TITLE_RE = re.compile(r"^\d{4}-\d{8}$")


def _readable_title(item: dict) -> str:
    """Get a readable title: for purely numeric titles (e.g. 2024-12345678), fall back to
    seoTitle/originTitle/categoryName (take the first non-empty, non-numeric one); if no fallback is usable,
    keep the original title.

    Every fallback candidate goes through _strip_help_prefix: categoryName carries a 'help@@'
    namespace prefix on both sites (measured 'help@@Object Storage Service' on search.json and
    'help@@对象存储' on doSearch), and seoTitle is None on every doSearch item measured (217/217)
    while search.json has no such field at all, so in practice the chain ends at categoryName.
    seoTitle/originTitle are kept for forward compatibility with future payloads.
    """
    title = item.get("title") or ""
    if " | " in title:
        title = title.split(" | ")[0]
    # Server-side highlight markers (<em>keyword</em>) are not part of the title itself; always strip them
    title = _strip_html(title)
    if not _NUMERIC_TITLE_RE.match(title):
        return title
    for field in ("seoTitle", "originTitle", "categoryName"):
        cand = _strip_help_prefix(item.get(field))
        if " | " in cand:
            cand = cand.split(" | ")[0]
        if cand and not _NUMERIC_TITLE_RE.match(cand):
            return _strip_html(cand)
    return title


def _normalize_url(url: str) -> str:
    """URL normalization: strip the query/fragment, the .md suffix and the trailing slash, and fold case at path level
    (improves cross-leg dedup robustness)."""
    u = url.split("#", 1)[0].split("?", 1)[0].lower()
    if u.endswith(".md"):
        u = u[:-3]
    return u.rstrip("/")


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


def _render_search_results(found: list, keyword: str, max_results) -> None:
    """Render search results in the existing format (shared by the full-text and index legs); max_results=None means unlimited.
    When a full-text leg entry carries an updated timestamp field, append (updated: YYYY-MM-DD) after the snippet line."""
    shown = len(found) if max_results is None else min(len(found), max_results)
    print(f"Found {len(found)} matching docs (showing first {shown}):\n")
    for i, doc in enumerate(found[:max_results] if max_results is not None else found, 1):
        print(f"{i}. [{doc['product']}] {doc['title']}")
        print(f"   {doc['url']}")
        desc_line = f"   {doc['desc']}" if doc['desc'] else ""
        updated = f" (updated: {doc['updated']})" if doc.get('updated') else ""
        if desc_line or updated:
            print(desc_line + updated)
        print()


def _render_no_result(keyword: str, site: str = DEFAULT_SITE, lang: str = "",
                      explicit: bool = False, precision_query: bool = False) -> None:
    """Empty-result advice (C10): the WebSearch hint names the site that was actually queried.

    The first three lines are byte-identical to the pre-i18n output for the default cn+zh scope.
    The fourth line appears only for an explicitly scoped invocation and states that no
    cross-site fallback was performed: the two sites document different products, regions and
    prices, so "no result on the international site" must never be silently answered from the
    China site corpus.
    The fifth line is the capability boundary of a precision query (F7): error codes, API
    operation names and quota/parameter identifiers are the classes an llms.txt title+summary
    substring scan provably cannot recall, so an empty answer says so and points at the
    metadata leg instead of leaving the reader to conclude the documentation does not exist.
    """
    cfg = SITES[site]
    print(f"No docs found containing '{keyword}'.")
    print(f"Suggestion: use the WebSearch tool with 'keyword site:{cfg['result_host']}' for broader results.")
    print("Hint: if this was a query with -p, retry without -p, or use list-products to verify the product code.")
    if explicit and (site, lang) != (DEFAULT_SITE, SITES[DEFAULT_SITE]["default_lang"]):
        print(f"Note: the query was scoped to the {cfg['label']} ({cfg['result_host']}, language "
              f"'{lang}'); an empty result means this product or topic has no documentation on "
              f"this site. No cross-site fallback is performed.")
    if precision_query:
        print("Boundary: this looks like an error code, API operation, parameter or quota query. "
              "The llms.txt index leg matches titles and summaries only, so such queries recall "
              "nothing from it even when the documentation exists, and the international site "
              "documents them more sparsely than the China site. For the authoritative list use "
              "the OpenAPI metadata leg: api-info <product> <ApiName> (see api-list for the names).")


def _render_found(args, found: list, limit, site: str = DEFAULT_SITE,
                  lang: str = "", explicit: bool = False,
                  precision_query: bool = False) -> int:
    """Unified output entry for search results: --json / empty-result advice / normal rendering.

    limit=None means unlimited. Returns the process exit code: 0 when at least one document is
    reported (a degraded leg that still produced results counts as success), 1 when the scoped
    corpus produced nothing at all.

    Scope annotation happens only for an explicitly scoped invocation, and only on stderr, so
    stdout - including the --json payload - stays byte-for-byte identical for a default call.
    """
    if explicit:
        cfg = SITES[site]
        _annotate_scope(found, site, lang)
        print(f"INFO: results are scoped to the {cfg['label']} ({cfg['result_host']}), "
              f"language '{lang}'", file=sys.stderr)
    if args.json:
        print(json.dumps(found if limit is None else found[:limit],
                         ensure_ascii=False, indent=2))
        return 0 if found else 1
    if not found:
        _render_no_result(args.keyword, site, lang, explicit, precision_query)
        return 1
    _render_search_results(found, args.keyword, limit)
    if explicit and not any(rec.get("updated") for rec in found):
        # Q5: only doSearch returns gmtModifiedOrigin. search.json has no timestamp field at all
        # and the llms.txt index leg never had one, so a scoped result set may legitimately carry
        # no modification date. The field is display-only (it never enters the fusion score), but
        # the absence must be stated instead of leaving the caller guessing.
        print("INFO: no result above carries an 'updated' date: only the China-site doSearch "
              "backend returns modification timestamps, the search.json backend and the llms.txt "
              "index leg do not (display-only; ranking is unaffected)", file=sys.stderr)
    return 0
