#!/usr/bin/env python3
"""External llms.txt source search: standalone corpuses outside the Alibaba Cloud help center."""

from __future__ import annotations

import json
import os
import sys
import time

from help_const import (
    EXT_CACHE_DIR,
    EXT_SOURCES,
    LLMS_CACHE_TTL_DAYS,
    LLMS_MAX_BYTES,
    _DOC_ENTRY_RE,
)
from help_http import (
    fetch_response,
    _is_index_corpus,
    _non_corpus_reason,
)
from help_query import _index_scored_hits


def _ext_cache_path(source: str) -> str:
    return os.path.join(EXT_CACHE_DIR, f"{source}.txt")


def _fetch_ext_index(source: str) -> str:
    """Fetch an external llms.txt with cache-first semantics; returns the text body."""
    cfg = EXT_SOURCES[source]
    path = _ext_cache_path(source)
    try:
        st = os.stat(path)
        if (st.st_size < LLMS_MAX_BYTES
                and time.time() - st.st_mtime <= LLMS_CACHE_TTL_DAYS * 86400):
            with open(path, encoding="utf-8") as f:
                cached = f.read()
            if _is_index_corpus(cached):
                print(f"INFO[ext-cache]: using {source} llms.txt cached on "
                      f"{time.strftime('%Y-%m-%d', time.localtime(st.st_mtime))}", file=sys.stderr)
                return cached
    except OSError:
        pass

    text, meta = fetch_response(cfg["llms_url"], allow_redirects=True,
                                timeout=cfg["timeout"],
                                max_bytes=LLMS_MAX_BYTES, attempts=2)
    if meta.get("truncated"):
        print(f"WARN[ext-oversize]: {source} llms.txt exceeds "
              f"{LLMS_MAX_BYTES // (1024 * 1024)} MB; discarded", file=sys.stderr)
        return "[Error] response exceeded size limit"

    if _is_index_corpus(text):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = f"{path}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp_path, path)
        except OSError as e:
            print(f"WARN[ext-cache-write]: failed to cache {source} ({e})", file=sys.stderr)
    else:
        try:
            with open(path, encoding="utf-8") as f:
                stale = f.read(LLMS_MAX_BYTES)
            if _is_index_corpus(stale):
                print(f"WARN[ext-stale]: {source} fetch returned no usable index "
                      f"({_non_corpus_reason(text)}); using expired cache", file=sys.stderr)
                return stale
        except OSError:
            pass
    return text


def ext_list_sources(args) -> int:
    """List available external documentation sources."""
    if getattr(args, "json", False):
        entries = [{"name": k, **v} for k, v in EXT_SOURCES.items()]
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0
    print("Available external documentation sources:\n")
    for name, cfg in EXT_SOURCES.items():
        print(f"  {name:<12s}  {cfg['label']}")
        print(f"  {'':12s}  {cfg['llms_url']}")
        print()
    return 0


def ext_search(args) -> int:
    """Search an external llms.txt source by keyword, or list all entries when no keyword is given."""
    source = args.source
    if source not in EXT_SOURCES:
        print(f"ERROR: unknown source '{source}'. Available: {', '.join(EXT_SOURCES)}", file=sys.stderr)
        return 2

    keyword = (getattr(args, "keyword", None) or "").strip().lower()
    limit = args.max_results if args.max_results > 0 else None

    text = _fetch_ext_index(source)
    if not _is_index_corpus(text):
        print(f"ERROR: no usable llms.txt for '{source}' ({_non_corpus_reason(text)})", file=sys.stderr)
        return 2

    entries = _DOC_ENTRY_RE.findall(text)
    if not entries:
        print(f"No entries found in {source} llms.txt.")
        return 1

    if not keyword:
        if getattr(args, "json", False):
            records = [{"title": t, "url": u, "desc": d} for t, u, d in entries]
            print(json.dumps(records if limit is None else records[:limit],
                             ensure_ascii=False, indent=2))
        else:
            shown = len(entries) if limit is None else min(len(entries), limit)
            print(f"# {EXT_SOURCES[source]['label']} llms.txt ({len(entries)} entries, showing {shown})\n")
            for i, (title, url, desc) in enumerate(entries[:limit] if limit else entries, 1):
                print(f"{i}. {title}")
                print(f"   {url}")
                if desc:
                    print(f"   {desc[:120]}")
                print()
        return 0

    scored = _index_scored_hits(source, text, keyword)
    if not scored:
        print(f"No matches for '{keyword}' in {EXT_SOURCES[source]['label']}.")
        return 1

    results = [record for _score, record in scored]
    if getattr(args, "json", False):
        print(json.dumps(results if limit is None else results[:limit],
                         ensure_ascii=False, indent=2))
    else:
        shown = len(results) if limit is None else min(len(results), limit)
        print(f"Found {len(results)} matching docs in {EXT_SOURCES[source]['label']} "
              f"(showing first {shown}):\n")
        for i, doc in enumerate(results[:limit] if limit else results, 1):
            print(f"{i}. {doc['title']}")
            print(f"   {doc['url']}")
            if doc.get("desc"):
                print(f"   {doc['desc']}")
            print()
    return 0
