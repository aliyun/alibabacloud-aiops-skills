#!/usr/bin/env python3
"""Search-result output and HTML-to-Markdown conversion for document bodies.

Titles go through one fallback chain and the capability-boundary hints are emitted here so
every leg shares the same wording.

The conversion half is self-contained: only the HTML handed in is used, with no script
execution and no external fetching. Tables are lifted out and converted separately so
unsupported table structure is preserved as inert fenced HTML source.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit

from help_const import (
    DEFAULT_SITE,
    SITES,
)
from help_scope import (
    _annotate_scope,
    _strip_help_prefix,
)


def _format_updated(ts) -> str:
    """Convert gmtModifiedOrigin (millisecond timestamp) to YYYY-MM-DD; return '' when the value is missing/invalid."""
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return ""
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
    except (OverflowError, OSError, ValueError):
        return ""


_NUMERIC_TITLE_RE = re.compile(r"^\d{4}-\d{8}$")

def _readable_title(item: dict) -> str:
    """Get a readable title: for purely numeric titles (e.g. 2024-12345678), fall back to
    seoTitle/originTitle/categoryName (take the first non-empty, non-numeric one); if no fallback is usable,
    keep the original title.

    Every fallback candidate goes through _strip_help_prefix: categoryName carries a 'help@@'
    namespace prefix on both sites (measured 'help@@Object Storage Service' on the English corpus
    and 'help@@对象存储' on the Chinese one), while search.json carries no seoTitle field at all,
    so in practice the chain ends at categoryName. seoTitle/originTitle are kept for forward
    compatibility with future payloads.
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

    An empty result describes only the searched candidates, not document availability.
    The scope note appears only for an explicitly scoped invocation and states that no
    cross-site fallback was performed: the two sites document different products, regions and
    prices, so "no result on the international site" must never be silently answered from the
    China site corpus.
    Precision queries get a capability-boundary hint (F7): error codes, API operation names
    and quota/parameter identifiers may be absent from llms.txt titles and summaries, so an
    empty answer points at the metadata leg instead of implying the documentation does not exist.
    """
    cfg = SITES[site]
    print(f"No matches for '{keyword}' within the searched candidates.")
    print(f"Suggestion: use the WebSearch tool with 'keyword site:{cfg['result_host']}' for broader results.")
    print("Hint: if this was a query with -p, retry without -p, or use list-products to verify the product code.")
    if explicit and (site, lang) != (DEFAULT_SITE, SITES[DEFAULT_SITE]["default_lang"]):
        print(f"Note: the query was scoped to the {cfg['label']} ({cfg['result_host']}, language "
              f"'{lang}'); no matches were found within the searched candidates. "
              f"No cross-site fallback is performed.")
    if precision_query:
        print("Boundary: this looks like an error code, API operation, parameter or quota query. "
              "The llms.txt index leg matches titles and summaries only, so it can miss these "
              "queries even when the documentation exists, and the international site "
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
        # Q5: neither leg reports modification timestamps - search.json has no such field and the
        # llms.txt index leg never had one - so a scoped result set legitimately carries no date.
        # The field is display-only (it never enters the fusion score), but the absence must be
        # stated instead of leaving the caller guessing.
        print("INFO: no result above carries an 'updated' date: neither the search.json backend "
              "nor the llms.txt index leg reports modification timestamps (display-only; "
              "ranking is unaffected)", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# HTML to Markdown: the international portal serves document bodies as an HTML
# fragment, so a reader needs the same conversion the cn leg gets for free.
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Strip HTML tags, unescape entities and collapse consecutive whitespace; used to clean search snippets."""
    s = re.sub(r"<[^>]+>", "", text or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


_HTML_SKIP_TAGS = frozenset((
    "script", "style", "template", "noscript", "svg", "math", "iframe",
    "object", "canvas", "head", "link", "meta", "button", "select",
))

_HTML_VOID_TAGS = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
))

_HTML_SAFE_SCHEMES = frozenset(("http", "https", "mailto"))

_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")


def _markdown_text(s: str) -> str:
    # Literal < and & stay as written; only the link/image brackets are ambiguous in Markdown.
    return s.replace("[", "\\[").replace("]", "\\]")


def _markdown_url(url: str, base_url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    probe = re.sub(r"[\x00-\x1f\x7f]", "", raw)
    if not probe:
        return ""
    if probe.startswith("#"):
        return _escape_markdown_url(probe)
    m = _SCHEME_RE.match(probe)
    if m:
        if m.group(1).lower() not in _HTML_SAFE_SCHEMES:
            return ""
    elif base_url:
        try:
            probe = urljoin(base_url, probe)
        except ValueError:
            return ""
        if urlsplit(probe).scheme.lower() not in _HTML_SAFE_SCHEMES:
            return ""
    return _escape_markdown_url(probe)


def _escape_markdown_url(u: str) -> str:
    return quote(u, safe="/:?#[]@!$&'*+,;=%~._-")


class _TableHTMLParser(HTMLParser):
    """Parse a single <table> fragment into rows: list[list[str]].

    Inside cells: <a> becomes [text](href), <li> becomes a "- " line, <p>/<div>/<br> become line breaks,
    all other tags (<b>/<strong>/<code>/<span>, etc.) keep plain text only.
    """

    def __init__(self, base_url: str | None = None):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell = None
        self._link_href = None
        self._base_url = base_url
        self._skip = []
        self._table_depth = 0
        self._cell_tag = None
        self._structure_error = False

    def handle_starttag(self, tag, attrs):
        if self._base_url is not None:
            if self._skip or tag in _HTML_SKIP_TAGS:
                if tag not in _HTML_VOID_TAGS:
                    self._skip.append(tag)
                return
        if tag == "table":
            self._table_depth += 1
            if self._table_depth != 1:
                self._structure_error = True
        elif tag == "tr":
            if self._row is not None or self._cell is not None:
                self._structure_error = True
            self._row = []
        elif tag in ("td", "th"):
            if self._row is None or self._cell is not None:
                self._structure_error = True
            for name, value in attrs:
                if name in ("colspan", "rowspan"):
                    try:
                        if int(value) != 1:
                            self._structure_error = True
                    except (TypeError, ValueError):
                        self._structure_error = True
            self._cell = []
            self._cell_tag = tag
        elif self._cell is None:
            return
        elif tag == "a":
            self._link_href = dict(attrs).get("href") or ""
            if self._base_url is not None:
                self._link_href = _markdown_url(self._link_href, self._base_url) or None
        elif tag == "img" and self._base_url is not None:
            attrs = dict(attrs)
            alt = _markdown_text(attrs.get("alt") or "")
            src = _markdown_url(attrs.get("src") or "", self._base_url)
            self._cell.append(f"![{alt}]({src})" if src else alt)
        elif tag == "li":
            self._cell.append("\n- ")
        elif tag in ("p", "div"):
            # <li><p> combination: a <p> immediately following the start of a list item does not add a newline, so "- " stays attached to its text
            if not (self._cell and self._cell[-1] == "\n- "):
                self._cell.append("\n")
        elif tag == "br":
            self._cell.append("\n")

    def handle_endtag(self, tag):
        if self._base_url is not None and self._skip:
            if tag in self._skip:
                del self._skip[len(self._skip) - 1 - self._skip[::-1].index(tag):]
            return
        if tag == "table":
            if self._table_depth != 1 or self._row is not None or self._cell is not None:
                self._structure_error = True
            self._table_depth = max(0, self._table_depth - 1)
        elif tag in ("td", "th"):
            if self._row is None or self._cell is None or tag != self._cell_tag:
                self._structure_error = True
            if self._row is not None and self._cell is not None:
                self._row.append("".join(self._cell))
            self._cell = None
            self._cell_tag = None
        elif tag == "tr":
            if not self._row or self._cell is not None:
                self._structure_error = True
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "a":
            self._link_href = None

    def handle_data(self, data):
        if not data or self._skip:
            return
        if self._cell is None:
            if data.strip():
                self._structure_error = True
            return
        if self._link_href is not None:
            text = re.sub(r"\s+", " ", data).strip()
            if self._base_url is not None:
                text = _markdown_text(text)
            if text:
                self._cell.append(f"[{text}]({self._link_href})")
        else:
            self._cell.append(_markdown_text(data) if self._base_url is not None else data)


def _clean_table_cell(raw: str) -> str:
    """Clean cell text: fold by line, collapse whitespace within a line, join lines with <br>;
    escape pipes so the Markdown table structure is not broken."""
    lines = []
    for seg in re.sub(r"[ \t]*\n[ \t]*", "\n", raw).split("\n"):
        seg = re.sub(r"\s+", " ", seg).strip()
        if seg:
            lines.append(seg)
    return "<br>".join(lines).replace("|", "\\|")


def _table_to_markdown(table_html: str, base_url: str | None = None) -> str:
    """Convert simple rectangular tables; preserve unsupported structure as inert HTML source.

    The first row becomes the header (actual doc header rows carry <b>).
    """
    try:
        parser = _TableHTMLParser(base_url=base_url)
        parser.feed(table_html)
        parser.close()
        rows = parser.rows
        if (parser._structure_error or parser._table_depth or parser._row is not None
                or parser._cell is not None or len(rows) < 2):
            raise ValueError("merged or malformed table structure")
        width = len(rows[0])
        if not width or any(len(row) != width for row in rows):
            raise ValueError("nonrectangular table structure")
        lines = []
        for i, row in enumerate(rows):
            cells = [_clean_table_cell(c) for c in row]
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                lines.append("|" + "---|" * width)
        return "\n".join(lines)
    except Exception:
        print("WARN[table-structure]: merged, malformed or unsupported table structure; "
              "original HTML preserved as fenced source", file=sys.stderr)
        fence = _code_fence(table_html)
        return f"\n\n{fence}html\n{table_html}\n{fence}\n\n"


_TABLE_TAG_RE = re.compile(r"</?table\b[^>]*>", re.IGNORECASE)


def _replace_html_tables(text: str, replace) -> str:
    """Replace entire outer tables, retaining nested and unclosed tables for safe fallback."""
    parts = []
    depth = 0
    start = 0
    cursor = 0
    for match in _TABLE_TAG_RE.finditer(text):
        if match.group(0).startswith("</"):
            if not depth:
                continue
            depth -= 1
            if not depth:
                parts.append(replace(text[start:match.end()]))
                cursor = match.end()
        else:
            if not depth:
                parts.append(text[cursor:match.start()])
                start = match.start()
            depth += 1
    if depth:
        parts.append(replace(text[start:]))
    else:
        parts.append(text[cursor:])
    return "".join(parts)


def _convert_html_tables(text: str) -> str:
    """Convert simple HTML tables; preserve merged or malformed ones as fenced HTML source."""
    return _replace_html_tables(text, _table_to_markdown)


# The China-site Markdown marks a fenced block's language on its own line right after the
# opening fence ("```\nHELPCODEESCAPE-java\n"), which would otherwise be read as the first
# line of the snippet and copied into real code.
_CODE_ESCAPE_RE = re.compile(r"(?m)^(?P<indent>[ \t>]*)```[ \t]*\n[ \t>]*HELPCODEESCAPE-(?P<lang>[A-Za-z0-9_+-]*)[ \t]*$")


def _fold_code_escape_marker(text: str) -> str:
    """Move a HELPCODEESCAPE-<lang> marker line onto its opening code fence."""
    return _CODE_ESCAPE_RE.sub(lambda m: f"{m.group('indent')}```{m.group('lang')}", text)


_HEADING_TAGS = frozenset(("h1", "h2", "h3", "h4", "h5", "h6"))

_BLOCK_TAGS = frozenset((
    "p", "div", "main", "section", "article", "aside", "header", "footer",
    "nav", "figure", "figcaption", "dl", "dt", "dd", "details", "summary",
    "address", "form", "fieldset", "legend", "body", "html",
))

_EMPHASIS_TAGS = {
    "b": "**", "strong": "**",
    "i": "*", "em": "*", "cite": "*", "var": "*",
    "del": "~~", "s": "~~", "strike": "~~",
}

_CODE_TAGS = frozenset(("code", "kbd", "samp", "tt"))

_PRE_MARKUP_TAGS = frozenset((
    "span", "code", "a", "b", "strong", "i", "em", "u", "font", "small", "big",
    "sup", "sub", "mark", "var", "samp", "kbd", "tt", "abbr", "label", "div",
    "p", "br", "tr", "td", "th", "li", "ul", "ol", "table", "tbody", "pre",
))

_CODE_LANG_PREFIXES = ("language-", "lang-", "brush:", "highlight-")


def _code_language(attrs: dict) -> str:
    tokens = f"{attrs.get('class') or ''} {attrs.get('data-lang') or ''} {attrs.get('lang') or ''}"
    for tok in tokens.split():
        low = tok.lower()
        for prefix in _CODE_LANG_PREFIXES:
            if low.startswith(prefix) and len(low) > len(prefix):
                return re.sub(r"[^0-9a-z+#.\-]", "", low[len(prefix):])
    return ""


def _code_fence(code: str) -> str:
    runs = [len(r) for r in re.findall(r"`+", code)]
    return "`" * max(3, (max(runs) + 1) if runs else 0)


class _BodyHTMLParser(HTMLParser):
    """Parse a document body fragment into Markdown blocks.

    Wrapper elements (div/main/section) only act as block separators; inline markup is rebuilt
    through a wrapper stack so emphasis, links and code spans survive nesting. <pre> content is
    captured verbatim (indentation and newlines kept, highlight <span>s dropped) and tables are
    expected to have been lifted out by the caller.
    """

    def __init__(self, base_url: str = ""):
        super().__init__(convert_charrefs=True)
        self._base = base_url
        self._blocks = []
        self._inline = []
        self._wrappers = []
        self._lists = []
        self._serial = 0
        self._quote = 0
        self._marker = ""
        self._heading = 0
        self._pre = None
        self._pre_lang = ""
        self._skip = []

    def handle_starttag(self, tag, attrs):
        if self._skip or tag in _HTML_SKIP_TAGS:
            if tag not in _HTML_VOID_TAGS:
                self._skip.append(tag)
            return
        a = dict(attrs)
        if self._pre is not None:
            if tag in ("br", "p", "div", "tr", "li"):
                self._pre.append("\n")
            elif tag in _CODE_TAGS and not self._pre_lang:
                self._pre_lang = _code_language(a)
            elif tag not in _PRE_MARKUP_TAGS:
                # unescaped '<' in a code sample: HTMLParser read it as a tag, keep it verbatim
                self._pre.append(self.get_starttag_text() or "")
            return
        if tag == "pre":
            self._flush()
            self._pre = []
            self._pre_lang = _code_language(a)
            return
        if tag in _HEADING_TAGS:
            self._flush()
            self._heading = int(tag[1])
            return
        if tag in ("ul", "ol"):
            self._flush()
            start = 0
            if tag == "ol":
                try:
                    start = int(a.get("start") or 0) - 1
                except ValueError:
                    start = 0
            self._serial += 1
            self._lists.append([tag, max(0, start), self._serial, 2])
            return
        if tag == "li":
            self._flush()
            if not self._lists:
                self._serial += 1
                self._lists.append(["ul", 0, self._serial, 2])
            lst = self._lists[-1]
            lst[1] += 1
            self._marker = f"{lst[1]}. " if lst[0] == "ol" else "- "
            lst[3] = len(self._marker)
            return
        if tag == "blockquote":
            self._flush()
            self._quote += 1
            return
        if tag == "br":
            self._inline.append("\n")
            return
        if tag == "hr":
            self._flush()
            self._decorate(["---"])
            return
        if tag in _BLOCK_TAGS:
            self._flush()
            return
        if tag == "a":
            self._open("a", _markdown_url(a.get("href") or "", self._base))
            return
        if tag == "img":
            alt = _markdown_text(re.sub(r"\s+", " ", a.get("alt") or "").strip())
            src = _markdown_url(a.get("src") or a.get("data-src") or "", self._base)
            if src:
                self._inline.append(f"![{alt}]({src})")
            elif alt:
                self._inline.append(alt)
            return
        if tag in _CODE_TAGS:
            self._open("code", "")
            return
        if tag in _EMPHASIS_TAGS:
            self._open("emphasis", _EMPHASIS_TAGS[tag])

    def handle_endtag(self, tag):
        if self._skip:
            if tag in self._skip:
                idx = len(self._skip) - 1 - self._skip[::-1].index(tag)
                del self._skip[idx:]
            return
        if self._pre is not None:
            if tag == "pre":
                self._emit_code()
            elif tag not in _PRE_MARKUP_TAGS:
                self._pre.append(f"</{tag}>")
            return
        if tag in _HEADING_TAGS:
            self._flush()
            self._heading = 0
            return
        if tag in ("ul", "ol"):
            self._flush()
            if self._lists:
                self._lists.pop()
            return
        if tag == "li":
            self._flush()
            return
        if tag == "blockquote":
            self._flush()
            self._quote = max(0, self._quote - 1)
            return
        if tag in _BLOCK_TAGS:
            self._flush()
            return
        if tag == "a" or tag in _CODE_TAGS or tag in _EMPHASIS_TAGS:
            self._close()

    def handle_data(self, data):
        if self._skip or not data:
            return
        if self._pre is not None:
            self._pre.append(data)
            return
        self._inline.append(data if self._in_code() else _markdown_text(data))

    def _open(self, kind, data):
        self._wrappers.append((len(self._inline), kind, data))

    def _in_code(self) -> bool:
        return any(kind == "code" for _, kind, _ in self._wrappers)

    def _close(self):
        if not self._wrappers:
            return
        idx, kind, data = self._wrappers.pop()
        idx = min(idx, len(self._inline))
        seg = "".join(self._inline[idx:])
        del self._inline[idx:]
        if kind == "code":
            body = re.sub(r"\s+", " ", seg).strip()
            if not body:
                return
            tick = "`" * (max((len(r) for r in re.findall(r"`+", body)), default=0) + 1)
            pad = " " if body.startswith("`") or body.endswith("`") else ""
            self._inline.append(f"{tick}{pad}{body}{pad}{tick}")
            return
        if kind == "a":
            text = seg.strip()
            if not text:
                return
            self._inline.append(f"[{text}]({data})" if data else text)
            return
        stripped = seg.strip()
        if not stripped:
            self._inline.append(seg)
            return
        lead = seg[:len(seg) - len(seg.lstrip())]
        trail = seg[len(seg.rstrip()):]
        self._inline.append(f"{lead}{data}{stripped}{data}{trail}")

    def _close_wrappers(self):
        while self._wrappers:
            self._close()

    def _decorate(self, lines, keep_blank: bool = False) -> None:
        depth = len(self._lists)
        marker = self._marker
        self._marker = ""
        quote = "> " * self._quote
        first = self._indent(depth - 1) + marker if marker else self._indent(depth)
        rest = self._indent(depth)
        out = []
        for i, line in enumerate(lines):
            prefix = first if (marker and i == 0) else rest
            if not line and not keep_blank:
                out.append(quote.rstrip())
            else:
                out.append((quote + prefix + line).rstrip())
        kind = "item" if marker else ("list" if depth else "block")
        self._blocks.append(("\n".join(out), kind, self._lists[0][2] if self._lists else 0))

    def _indent(self, levels: int) -> str:
        return "".join(" " * lv[3] for lv in self._lists[:max(0, levels)])

    def _flush(self):
        self._close_wrappers()
        text = "".join(self._inline).replace("\r", "")
        self._inline = []
        lines = [re.sub(r"\s+", " ", seg).strip() for seg in text.split("\n")]
        lines = [s for i, s in enumerate(lines) if s or (i and lines[i - 1])]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        if not lines:
            return
        if self._heading:
            lines = ["#" * self._heading + " " + " ".join(s for s in lines if s)]
        self._decorate(lines)

    def _emit_code(self):
        code = "".join(self._pre).replace("\r\n", "\n").replace("\r", "\n")
        self._pre = None
        lang = self._pre_lang
        self._pre_lang = ""
        code = re.sub(r"^[ \t]*\n+", "", code).rstrip()
        if not code.strip():
            return
        fence = _code_fence(code)
        self._decorate([fence + lang] + code.split("\n") + [fence], keep_blank=True)

    def result(self) -> str:
        self._flush()
        blocks = [b for b in self._blocks if b[0].strip()]
        if not blocks:
            return ""
        out = [blocks[0][0]]
        for prev, cur in zip(blocks, blocks[1:]):
            tight = (cur[1] == "item" and prev[1] in ("item", "list")
                     and cur[2] == prev[2] and cur[2])
            out.append(("\n" if tight else "\n\n") + cur[0])
        return "".join(out)


_TABLE_SLOT_RE = re.compile(r"\x00T(\d+)\x00")
_TABLE_SLOT_LINE_RE = re.compile(r"(?m)^[ \t>]*(?:[-*+] |\d+\. )?(\x00T\d+\x00)[ \t]*$")


def _html_to_markdown(text: str, base_url: str) -> str:
    """Convert an HTML document body (international-site JSON detail) to Markdown.

    Only the HTML that was handed in is used: no script execution and no external fetching, with
    script/style/template content dropped. Tables are lifted out first so the existing
    _table_to_markdown helper keeps owning them (preserving unsupported structure as fenced HTML).
    """
    if not text:
        return ""
    base = base_url or ""
    tables = []

    def _hold(raw):
        tables.append(raw)
        return f"\x00T{len(tables) - 1}\x00"

    body = _replace_html_tables(text, _hold)
    parser = _BodyHTMLParser(base)
    try:
        parser.feed(body)
        parser.close()
        out = parser.result()
    except Exception:
        out = _strip_html(body)

    def _restore(m):
        raw = tables[int(m.group(1))]
        return _table_to_markdown(raw, base_url=base)

    out = _TABLE_SLOT_LINE_RE.sub(r"\1", out)
    out = _TABLE_SLOT_RE.sub(_restore, out)
    return out.strip()
