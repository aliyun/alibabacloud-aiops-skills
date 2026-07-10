#!/usr/bin/env python3
"""Fetch and parse the Aliyun "AI 工具尝鲜实验室" landing page.

Source : https://www.aliyun.com/daily-act/ecs/ai-innovation-lab
Output : structured project list — title / description / tags / view_count /
         deploy_minutes / deploy_time_label / deploy_url / deploy_type /
         service_id / section.

The page was rebuilt in mid-2026. Project cards now live inside a
two-level tab structure:

  Top-level tabs:      近30天上新 (N) | 往期精选 (M)
  Sub-tabs (近30天上新):  全部 / AI 办公 / AI 编程 / 设计创作 / ...

Only the currently active panel is statically rendered (cards from
`近30天上新 / 全部`). The 往期精选 tab's cards are loaded client-side
via the low-code engine and can't be scraped statically — its count is
still parsed from the tab label so callers can report it.

Each visible card uses CSS-module class names like:
    _5bea61f1af1643a5621f7c8f94fb9622_card / _cardTextHead / _cardDesc / _tag / _button

This script parses that DOM with the standard library — no external
dependencies.

Usage:
    python fetch_ai_lab.py                       # Markdown table to stdout
    python fetch_ai_lab.py -o lab.json           # JSON
    python fetch_ai_lab.py -o lab.csv            # CSV
    python fetch_ai_lab.py -o lab.md             # Markdown
    python fetch_ai_lab.py --tag 一键部署
    python fetch_ai_lab.py --section 编程
    python fetch_ai_lab.py --type computenest
    python fetch_ai_lab.py --top 5
    python fetch_ai_lab.py --from-file ailab.html  # parse a local copy

Network notes:
    Some macOS Python installs ship without an SSL CA bundle and fail with
    `CERTIFICATE_VERIFY_FAILED`. In that case download the page with curl
    first and pass it via `--from-file`:
        curl -sA 'Mozilla/5.0' \\
          'https://www.aliyun.com/daily-act/ecs/ai-innovation-lab' \\
          -o /tmp/ailab.html
        python fetch_ai_lab.py --from-file /tmp/ailab.html
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

PAGE_URL = "https://www.aliyun.com/daily-act/ecs/ai-innovation-lab"
# Pre-computed snapshot mirrored to OSS; use as fallback when the live page is
# unreachable or the DOM-scrape returns 0 cards. v2 schema (English keys,
# meta + projects). See ai-innovation-lab.json for full layout.
OSS_FALLBACK_URL = (
    "https://ai-innovation-lab.oss-cn-beijing.aliyuncs.com/ai-innovation-lab.json"
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# ---- regexes -----------------------------------------------------------------
# New (2026-06+) DOM: cards live inside a `_card data-card="true"` div whose
# button anchor carries `rel="nofollow"` and a "立即体验" label.
CARD_TITLE_RE = re.compile(r'_cardTextHead">([^<]+)</div>')
CARD_DESC_RE = re.compile(r'_cardDesc"><p>([^<]+)</p>')
TAG_RE = re.compile(r'</svg></div>([^<]+)</span>')
DEPLOY_LINK_RE = re.compile(
    r'href="(https?://[^"]+)"[^>]*rel="nofollow"', re.S
)
DEPLOY_LINK_FALLBACK_RE = re.compile(
    r'href="([^"]*(?:computenest|developer\.aliyun|tech-solution-deploy)[^"]*)"'
)

# Tab labels carry the section name + visible-count badge.
TAB_LABEL_RE = re.compile(
    r'_tabText">([^<]+)</span><span[^>]*_badge[^>]*>(\d+)</span>'
)
# Sub-tabs (`AI 办公` / `AI 编程` / ...) come *after* the parent tabs
# (`近30天上新` / `往期精选`). We separate them by detecting the second
# tablist group.
PARENT_TABS = {"近30天上新", "往期精选"}


@dataclass
class Project:
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    view_count: int = 0  # always 0 on the new page; kept for back-compat.
    deploy_minutes: Optional[int] = None  # not exposed any more either.
    deploy_time_label: str = ""
    deploy_url: str = ""
    deploy_type: str = ""  # computenest | developer-scenario | tech-solution | developer-article | other
    service_id: Optional[str] = None
    section: str = ""
    # New (2026-06) — derived from the parent tab the card lives in.
    parent_tab: str = ""  # 近30天上新 / 往期精选

    def hotness_score(self) -> int:
        """Heuristic ranking. The new page doesn't expose view counts, so we
        fall back to a small bonus for "最新" tags + a strong bonus for the
        `近30天上新` parent tab so listings stay deterministic.
        """
        bonus = 0
        if "最热" in self.tags:
            bonus += 500
        if "最新" in self.tags:
            bonus += 200
        if self.parent_tab == "近30天上新":
            bonus += 100
        return self.view_count + bonus


# ---- network -----------------------------------------------------------------
def _http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLError):
            ctx = ssl._create_unverified_context()  # noqa: SLF001
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        raise


def parse_oss_snapshot(text: str) -> Tuple[List["Project"], Dict[str, object]]:
    """Parse the OSS JSON fallback snapshot (v2 schema).

    Returns (projects, meta). `meta` mirrors the snapshot's top-level meta
    block — callers use it for the summary path so they don't have to
    re-derive totals. If parsing fails, returns ([], {}).
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [], {}
    if not isinstance(payload, dict):
        return [], {}

    meta = payload.get("meta") or {}
    raw_projects = payload.get("projects") or []
    if not isinstance(raw_projects, list):
        return [], meta if isinstance(meta, dict) else {}

    # Optional explicit recommendation order; respect it when ranking.
    recommend_order = (
        meta.get("recommend_order") if isinstance(meta, dict) else None
    ) or []
    rank_index = {sid: i for i, sid in enumerate(recommend_order)}

    projects: List[Project] = []
    for raw in raw_projects:
        if not isinstance(raw, dict):
            continue
        title = _normalize_text(str(raw.get("title", "")))
        if not title:
            continue
        description = _normalize_text(str(raw.get("description", "")))
        tags_raw = raw.get("tags") or []
        tags = [_normalize_text(str(t)) for t in tags_raw if t]
        parent_tab = _normalize_text(str(raw.get("parent_tab", ""))) or "近30天上新"
        if parent_tab not in PARENT_TABS:
            parent_tab = "近30天上新"
        section = _normalize_text(str(raw.get("section", ""))) or parent_tab

        deploy = raw.get("deploy") or {}
        if isinstance(deploy, dict):
            deploy_url = html.unescape(str(deploy.get("url") or ""))
            deploy_type = str(deploy.get("type") or "")
            service_id = deploy.get("service_id") or None
        else:
            deploy_url = ""
            deploy_type = ""
            service_id = None

        # Backfill deploy_type if it's missing in the snapshot.
        if deploy_url and not deploy_type:
            deploy_type, _sid = _classify_url(deploy_url)
            service_id = service_id or _sid

        projects.append(
            Project(
                title=title,
                description=description,
                tags=tags,
                view_count=0,
                deploy_minutes=None,
                deploy_time_label="",
                deploy_url=deploy_url,
                deploy_type=deploy_type,
                service_id=service_id,
                section=section,
                parent_tab=parent_tab,
            )
        )

    # Re-rank using the snapshot's recommend_order when present, otherwise
    # keep the input order (which is the page-original order).
    if rank_index:
        projects.sort(
            key=lambda p: rank_index.get(p.service_id or "", 10_000)
        )
    return projects, meta if isinstance(meta, dict) else {}


# ---- parsing -----------------------------------------------------------------
def _classify_url(url: str) -> Tuple[str, Optional[str]]:
    if "computenest.console.aliyun.com" in url:
        m = re.search(r"/(service-[a-z0-9]+)", url)
        return ("computenest", m.group(1) if m else None)
    if "/adc/scenario/" in url or "/adc/university/" in url:
        return ("developer-scenario", None)
    if "tech-solution-deploy" in url:
        return ("tech-solution", None)
    if "developer.aliyun.com/article" in url:
        return ("developer-article", None)
    return ("other", None)


def _normalize_text(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\u00a0", " ")  # &nbsp; → regular space
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _canonicalize_tab_label(label: str) -> str:
    """Map real-world tab labels to the canonical name used by this skill.

    The page has used "本月上新" and "近30天更新" historically; the skill
    canonical name is "近30天上新". Anything else is left as-is.
    """
    label = _normalize_text(label)
    if label in ("近30天更新", "本月上新"):
        return "近30天上新"
    return label


def _extract_tab_taxonomy(html_text: str) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Return (parent_tab_counts, sub_tab_counts).

    Parent tabs are `近30天上新` / `往期精选`. Anything else with a badge is a sub-tab.
    """
    parent_counts: Dict[str, int] = {}
    sub_counts: Dict[str, int] = {}
    for label, count in TAB_LABEL_RE.findall(html_text):
        label = _canonicalize_tab_label(label)
        n = int(count)
        if label in PARENT_TABS:
            parent_counts[label] = n
        else:
            sub_counts[label] = n
    return parent_counts, sub_counts


def parse_projects(html_text: str) -> List[Project]:
    """Parse all statically rendered cards.

    Strategy: find every `_cardTextHead">` anchor (each card has exactly one),
    then slice from that anchor to the next as the card body. Tags / desc /
    deploy link are recovered from the slice.
    """
    head_positions = [m.start() for m in re.finditer(r'_cardTextHead">', html_text)]
    if not head_positions:
        return []
    head_positions.append(len(html_text))

    parent_counts, _sub_counts = _extract_tab_taxonomy(html_text)
    # Cards under the active parent tab. The new (2026-06) page renders only
    # the first parent panel statically; treat all visible cards as "近30天上新"
    # if that tab is present, else fall back to whichever parent tab the page
    # exposes.
    parent_tab = (
        "近30天上新" if "近30天上新" in parent_counts
        else (next(iter(parent_counts.keys()), ""))
    )

    projects: List[Project] = []
    for i in range(len(head_positions) - 1):
        block = html_text[head_positions[i] : head_positions[i + 1]]

        title_m = CARD_TITLE_RE.search(block)
        if not title_m:
            continue
        title = _normalize_text(title_m.group(1))

        desc_m = CARD_DESC_RE.search(block)
        description = _normalize_text(desc_m.group(1)) if desc_m else ""

        tags: List[str] = []
        for raw in TAG_RE.findall(block):
            tag = _normalize_text(raw)
            if tag and tag not in tags:
                tags.append(tag)

        link_m = DEPLOY_LINK_RE.search(block) or DEPLOY_LINK_FALLBACK_RE.search(block)
        deploy_url = html.unescape(link_m.group(1)) if link_m else ""
        deploy_type, service_id = (
            _classify_url(deploy_url) if deploy_url else ("", None)
        )

        # `section` reflects the sub-category we can infer from the card's
        # tag list. The page's last tag is typically the difficulty level
        # (初阶 / 中阶 / 高阶); the first tag is usually a capability tag.
        # We treat the deepest-known category keyword found in tags as
        # section; otherwise we fall back to the parent tab name.
        section = ""
        for category in ("AI 办公", "AI 编程", "设计创作", "AI办公", "AI编程"):
            if any(category in t for t in tags) or category in title:
                section = category
                break
        if not section:
            section = parent_tab

        projects.append(
            Project(
                title=title,
                description=description,
                tags=tags,
                view_count=0,
                deploy_minutes=None,
                deploy_time_label="",
                deploy_url=deploy_url,
                deploy_type=deploy_type,
                service_id=service_id,
                section=section,
                parent_tab=parent_tab,
            )
        )
    return projects


def page_summary(html_text: str) -> Dict[str, object]:
    """Lightweight metadata snapshot for callers that just want counts."""
    parent_counts, sub_counts = _extract_tab_taxonomy(html_text)
    return {
        "parent_tabs": parent_counts,
        "sub_tabs": sub_counts,
        "static_projects": len(parse_projects(html_text)),
        "total_projects": sum(parent_counts.values()) or len(parse_projects(html_text)),
    }


# ---- output formats ----------------------------------------------------------
def to_markdown(projects: List[Project]) -> str:
    lines = [
        f"# 阿里云 AI 工具尝鲜实验室 — 项目清单（共 {len(projects)} 项）",
        "",
        "| # | 项目 | 分组 | 标签 | 一键体验 |",
        "|---|------|------|------|---------|",
    ]
    for i, p in enumerate(projects, 1):
        tag_text = "、".join(p.tags) if p.tags else "-"
        lines.append(
            f"| {i} | **{p.title}**<br/>{p.description} | {p.section or '-'} | "
            f"{tag_text} | [立即体验]({p.deploy_url}) |"
        )
    return "\n".join(lines) + "\n"


def to_csv(projects: List[Project]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "title", "description", "tags", "section", "parent_tab", "view_count",
        "deploy_minutes", "deploy_time_label",
        "deploy_type", "service_id", "deploy_url",
    ])
    for p in projects:
        writer.writerow([
            p.title, p.description, "|".join(p.tags), p.section, p.parent_tab,
            p.view_count,
            p.deploy_minutes if p.deploy_minutes is not None else "",
            p.deploy_time_label, p.deploy_type, p.service_id or "", p.deploy_url,
        ])
    return buf.getvalue()


def to_json(projects: List[Project]) -> str:
    return json.dumps([asdict(p) for p in projects], ensure_ascii=False, indent=2)


# ---- CLI ---------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("-o", "--output",
                   help="Output file path. Format inferred from extension (.md/.json/.csv).")
    p.add_argument("--format", choices=["md", "json", "csv"],
                   help="Force output format. Overrides extension inference.")
    p.add_argument("--tag", action="append", default=[],
                   help="Keep only projects whose tag list contains this tag (repeatable).")
    p.add_argument("--section",
                   help="Substring filter on section, e.g. '编程'.")
    p.add_argument("--type", dest="deploy_type",
                   choices=["computenest", "developer-scenario", "tech-solution",
                            "developer-article", "other"],
                   help="Filter by deploy URL type.")
    p.add_argument("--top", type=int, help="Keep only the top-N projects after sort.")
    p.add_argument("--sort", choices=["hot", "title"], default="hot",
                   help=("Sort order. hot=tag/tab bonus desc (default); "
                         "title=alphabetical."))
    p.add_argument("--source", default=PAGE_URL,
                   help="Override page URL (defaults to the official one).")
    p.add_argument("--from-file",
                   help="Parse a previously saved HTML file instead of fetching.")
    p.add_argument("--use-oss", action="store_true",
                   help=(f"Skip the live page and pull the pre-computed snapshot "
                         f"from {OSS_FALLBACK_URL} instead. Also used automatically "
                         f"as a fallback when the live page is unreachable or its "
                         f"DOM scrape returns 0 cards."))
    p.add_argument("--summary", action="store_true",
                   help="Print only the page-level summary (tab counts) as JSON.")
    return p


def _resolve_format(args) -> str:
    if args.format:
        return args.format
    if args.output:
        ext = args.output.rsplit(".", 1)[-1].lower()
        return {"json": "json", "csv": "csv"}.get(ext, "md")
    return "md"


def _oss_summary(
    projects: List["Project"], meta: Optional[Dict[str, object]] = None
) -> Dict[str, object]:
    """Summary shape compatible with page_summary() but sourced from OSS.

    Prefer the snapshot's own `meta.totals` (authoritative) when present;
    otherwise recompute from the project list.
    """
    parent_counts: Dict[str, int] = {}
    if meta and isinstance(meta.get("totals"), dict):
        totals = meta["totals"]  # type: ignore[index]
        by_parent = totals.get("by_parent_tab") if isinstance(totals, dict) else None
        if isinstance(by_parent, dict):
            parent_counts = {str(k): int(v) for k, v in by_parent.items()}
    if not parent_counts:
        for p in projects:
            key = p.parent_tab or "近30天上新"
            parent_counts[key] = parent_counts.get(key, 0) + 1
    n = sum(parent_counts.values()) or len(projects)
    return {
        "parent_tabs": parent_counts,
        "sub_tabs": {},
        "static_projects": len(projects),
        "total_projects": n,
        "source": "oss-fallback",
        "snapshot_meta": meta or {},
    }


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    page: Optional[str] = None
    oss_projects: Optional[List[Project]] = None
    oss_meta: Dict[str, object] = {}

    def _try_oss() -> Optional[List[Project]]:
        nonlocal oss_meta
        try:
            print(f"[info] falling back to OSS snapshot: {OSS_FALLBACK_URL}",
                  file=sys.stderr)
            text = _http_get(OSS_FALLBACK_URL)
            projects, meta = parse_oss_snapshot(text)
            oss_meta = meta
            return projects
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"[error] OSS fallback failed: {exc}", file=sys.stderr)
            return None

    try:
        if args.use_oss:
            oss_projects = _try_oss()
            if oss_projects is None:
                return 2
        elif args.from_file:
            with open(args.from_file, encoding="utf-8") as fh:
                page = fh.read()
        else:
            page = _http_get(args.source)
    except FileNotFoundError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"[warn] failed to fetch {args.source}: {exc}", file=sys.stderr)
        oss_projects = _try_oss()
        if oss_projects is None:
            print("        tip: download with curl and pass --from-file",
                  file=sys.stderr)
            return 2

    if args.summary:
        if oss_projects is not None:
            sys.stdout.write(json.dumps(
                _oss_summary(oss_projects, oss_meta),
                ensure_ascii=False, indent=2,
            ))
        else:
            sys.stdout.write(json.dumps(page_summary(page or ""),
                                        ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        return 0

    if oss_projects is not None:
        projects = oss_projects
    else:
        projects = parse_projects(page or "")
        if not projects:
            print("[warn] no projects parsed — page DOM may have changed, "
                  "trying OSS fallback.", file=sys.stderr)
            oss_projects = _try_oss()
            if oss_projects:
                projects = oss_projects
            else:
                return 1

    if args.tag:
        wanted = set(args.tag)
        projects = [p for p in projects if wanted.intersection(p.tags)]
    if args.section:
        key = args.section
        projects = [p for p in projects if key in p.section]
    if args.deploy_type:
        projects = [p for p in projects if p.deploy_type == args.deploy_type]

    if args.sort == "hot":
        projects.sort(key=lambda p: p.hotness_score(), reverse=True)
    else:
        projects.sort(key=lambda p: p.title)

    if args.top:
        projects = projects[: args.top]

    fmt = _resolve_format(args)
    if fmt == "json":
        rendered = to_json(projects)
    elif fmt == "csv":
        rendered = to_csv(projects)
    else:
        rendered = to_markdown(projects)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered)
        print(f"[ok] wrote {len(projects)} projects -> {args.output}",
              file=sys.stderr)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
