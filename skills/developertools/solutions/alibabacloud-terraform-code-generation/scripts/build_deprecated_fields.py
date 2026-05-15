#!/usr/bin/env python3
# ruff: noqa
r"""Build references/deprecated-fields.md from the terraform-provider-alicloud repo.

Scans website/docs/r/*.html.markdown for three kinds of field-level
deprecations and emits a merged markdown table.

Categories detected:

1. **Rename** — field's Argument Reference line has `(Deprecated since vX.Y.Z)`
   and a description like `New field \`<Y>\` instead.` → emit `field → Y`.

2. **Hard split** — field's Argument Reference line has `(Deprecated since …)`
   and description like `please use the resource \`alicloud_<X>\` instead` →
   emit `field → alicloud_<X>` (separate resource).

3. **Soft split** — field is NOT marked deprecated in its own Argument
   Reference line, BUT the parent resource has a NOTE block like
   `-> **NOTE:** ... standalone sub-resources ... (alicloud_X_Y, …)` AND
   `alicloud_<parent>_<field>` exists as a separate resource file. Typical
   example: `alicloud_oss_bucket.logging` / `alicloud_oss_bucket.versioning`
   (the doc never uses the word "Deprecated" for these fields, but the NOTE
   tells users to use the standalone resources instead).

Case 4 — unclassified `Deprecated since` lines with no clear replacement —
is emitted in a tail section so maintainers can hand-curate.

Hand-curated supplement (optional):
    references/deprecated-fields-manual.yaml

If present, its entries are merged into the output. Structure:
    entries:
      - resource: alicloud_X
        field: Y
        replacement: Z           # optional; either a field name or alicloud_Z
        kind: rename|split|soft  # optional; defaults based on replacement
        since: v1.A.B            # optional
        note: free-form          # optional

Usage:
    scripts/build_deprecated_fields.py                 # clone or pull, regen
    scripts/build_deprecated_fields.py --no-refresh    # reuse existing clone
    scripts/build_deprecated_fields.py --repo PATH
    scripts/build_deprecated_fields.py --out PATH
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

PROVIDER_REPO = "https://github.com/aliyun/terraform-provider-alicloud.git"
DEFAULT_CLONE = "/tmp/terraform-provider-alicloud"
DOC_URL_PREFIX = (
    "https://github.com/aliyun/terraform-provider-alicloud/blob/master/website/docs/r"
)
SUFFIX = ".html.markdown"

# Field line in Argument Reference, e.g.:
#   * `name` - (Optional, Deprecated since v1.239.0) Field `name` has been ...
FIELD_LINE_RE = re.compile(
    r"^\*\s+`([a-z_][a-z0-9_]*)`\s*-\s*\(([^)]*)\)\s*(.*)$",
    re.MULTILINE,
)
# Version inside the parentheses, e.g. "Deprecated since v1.239.0", or
# "Deprecated since 1.220.0", "Deprecated from 1.37.0", "Deprecated from v1.166.0+"
DEPRECATED_VER_RE = re.compile(
    r"Deprecated\s+(?:since|from)\s+v?(\d+\.\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Replacement extraction from the description text:
# (a) "New field `<X>` instead" / "New attribute `<X>` instead" — rename
NEW_FIELD_RE = re.compile(
    r"[Nn]ew\s+(?:field|attribute)\s+`([a-z_][a-z0-9_]*)`\s+(?:and\s+)?instead",
    re.IGNORECASE,
)
# (b) Hard split — field → separate resource. Covers:
#     "please use the resource `alicloud_X` instead"
#     "please use the new resource `alicloud_X`"
#     "please use resource alicloud_X"
HARD_SPLIT_RE = re.compile(
    r"[Pp]lease\s+use\s+(?:the\s+)?(?:new\s+)?(?:standalone\s+)?resource\s+"
    r"`?(alicloud_[a-z0-9_]+)`?",
    re.IGNORECASE,
)
# (c) Generic rename fallbacks:
#     "use `<X>` instead" / "using `<X>` instead" / "Use `X` and instead"
#     "Please use `<X>` instead"
#     "Please use `<X>` to (instead|replace|managed ...)"
#     "replaced by `<X>`"
USE_FIELD_RE = re.compile(
    r"(?:[Pp]lease\s+)?[Uu]s(?:e|ing)\s+`([a-z_][a-z0-9_]*)`\s+(?:and\s+)?instead",
    re.IGNORECASE,
)
USE_TO_RE = re.compile(
    r"[Pp]lease\s+use\s+`([a-z_][a-z0-9_]*)`\s+to\s+(?:instead|replace|managed?)",
    re.IGNORECASE,
)
REPLACED_BY_RE = re.compile(
    r"replaced\s+by\s+`([a-z_][a-z0-9_]*)`",
    re.IGNORECASE,
)

# NOTE block mentioning standalone sub-resources. We match the whole
# paragraph then extract `alicloud_*` tokens from it.
NOTE_STANDALONE_RE = re.compile(
    r"->\s*\*\*NOTE:\*\*[^\n]*standalone\s+(?:sub-)?resource[^\n]*",
    re.IGNORECASE,
)
ALICLOUD_TOKEN_RE = re.compile(r"`(alicloud_[a-z0-9_]+)`")


def ensure_repo(clone_dir: Path) -> None:
    if (clone_dir / ".git").exists():
        print(f"[info] refreshing existing clone at {clone_dir}", file=sys.stderr)
        subprocess.run(
            ["git", "-C", str(clone_dir), "pull", "--ff-only"], check=False,
            timeout=300,
        )
        return
    clone_dir.parent.mkdir(parents=True, exist_ok=True)
    print(f"[info] cloning provider repo to {clone_dir}", file=sys.stderr)
    subprocess.run(
        [
            "git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
            PROVIDER_REPO, str(clone_dir),
        ],
        check=True,
        timeout=600,
    )
    subprocess.run(
        ["git", "-C", str(clone_dir), "sparse-checkout", "set", "website/docs"],
        check=True,
        timeout=60,
    )


def extract_fields(path: Path) -> list[dict]:
    """Return list of {field, annots, desc} for every Argument Reference field."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for m in FIELD_LINE_RE.finditer(text):
        out.append({
            "field": m.group(1),
            "annots": m.group(2),
            "desc": m.group(3) or "",
            "_text_start": m.start(),
        })
    return out


def extract_note_standalone(path: Path) -> list[str]:
    """Return list of alicloud_* resource names referenced in NOTE-standalone blocks."""
    text = path.read_text(encoding="utf-8", errors="replace")
    tokens: list[str] = []
    for m in NOTE_STANDALONE_RE.finditer(text):
        # Take a window of ~1500 chars after the NOTE start to capture the list
        window = text[m.start(): m.start() + 1500]
        # Stop at next heading or blank-line-separated paragraph
        # Simple approach: collect all alicloud_X in the window up to first "\n\n" or "\n##"
        stop = min(
            (s for s in [window.find("\n\n"), window.find("\n##")] if s != -1),
            default=len(window),
        )
        chunk = window[:stop]
        for tm in ALICLOUD_TOKEN_RE.finditer(chunk):
            tokens.append(tm.group(1))
    return tokens


def build_entries(docs_r: Path, all_resources: set[str]) -> list[dict]:
    """Emit a flat list of entries classified by kind."""
    entries: list[dict] = []

    for md in sorted(docs_r.glob(f"*{SUFFIX}")):
        parent = md.name[: -len(SUFFIX)]
        parent_full = f"alicloud_{parent}"
        text = md.read_text(encoding="utf-8", errors="replace")

        fields = extract_fields(md)
        hard_deprecated_field_names: set[str] = set()

        # Pass A — field lines marked Deprecated
        for f in fields:
            if "Deprecated" not in f["annots"]:
                continue
            hard_deprecated_field_names.add(f["field"])
            ver_m = DEPRECATED_VER_RE.search(f["annots"])
            version = f"v{ver_m.group(1)}" if ver_m else None

            # Prefer hard-split phrasing first (more specific), then rename.
            split_m = HARD_SPLIT_RE.search(f["desc"])
            rename_m = NEW_FIELD_RE.search(f["desc"])
            fallback_m = (
                USE_FIELD_RE.search(f["desc"])
                or USE_TO_RE.search(f["desc"])
                or REPLACED_BY_RE.search(f["desc"])
            )

            if split_m:
                entries.append({
                    "resource": parent_full,
                    "field": f["field"],
                    "replacement": split_m.group(1),
                    "kind": "split",
                    "since": version,
                    "source": "doc:field-annotation",
                })
            elif rename_m:
                entries.append({
                    "resource": parent_full,
                    "field": f["field"],
                    "replacement": rename_m.group(1),
                    "kind": "rename",
                    "since": version,
                    "source": "doc:field-annotation",
                })
            elif fallback_m:
                entries.append({
                    "resource": parent_full,
                    "field": f["field"],
                    "replacement": fallback_m.group(1),
                    "kind": "rename",
                    "since": version,
                    "source": "doc:field-annotation",
                })
            else:
                entries.append({
                    "resource": parent_full,
                    "field": f["field"],
                    "replacement": None,
                    "kind": "deprecated-no-replacement",
                    "since": version,
                    "source": "doc:field-annotation",
                })

        # Pass B — soft splits. Trigger when the parent doc has ANY
        # "NOTE: ... standalone (sub-)resource ..." block. Within such
        # a parent, any non-deprecated field whose name matches an existing
        # `{parent}_{field}` resource is flagged as a soft-split candidate.
        # This catches cases the NOTE explicitly names AND adjacent cases
        # the NOTE happens to omit (e.g. alicloud_oss_bucket.access_monitor).
        note_tokens = extract_note_standalone(md)
        has_standalone_note = bool(NOTE_STANDALONE_RE.search(text))
        note_named = {t for t in note_tokens if t.startswith(f"{parent_full}_")}

        if has_standalone_note:
            for f in fields:
                if f["field"] in hard_deprecated_field_names:
                    continue  # already covered as hard deprecation
                sub_guess = f"{parent_full}_{f['field']}"
                if sub_guess in all_resources:
                    entries.append({
                        "resource": parent_full,
                        "field": f["field"],
                        "replacement": sub_guess,
                        "kind": "soft-split",
                        "since": None,
                        "source": (
                            "doc:NOTE-standalone"
                            if sub_guess in note_named
                            else "doc:NOTE-standalone+collision"
                        ),
                    })

    return entries


# --- manual supplement ---------------------------------------------------

def load_manual(manual_path: Path) -> list[dict]:
    if not manual_path.exists():
        return []
    try:
        import yaml  # type: ignore
    except ImportError:
        print(
            f"[warn] pyyaml not installed; skipping {manual_path}. "
            f"Install with: pip install pyyaml",
            file=sys.stderr,
        )
        return []
    data = yaml.safe_load(manual_path.read_text()) or {}
    entries = []
    for e in data.get("entries", []):
        kind = e.get("kind")
        if not kind:
            repl = e.get("replacement", "")
            if repl.startswith("alicloud_"):
                kind = "split"
            else:
                kind = "rename" if repl else "deprecated-no-replacement"
        entries.append({
            "resource": e["resource"],
            "field": e["field"],
            "replacement": e.get("replacement"),
            "kind": kind,
            "since": e.get("since"),
            "source": f"manual:{manual_path.name}",
            "note": e.get("note"),
        })
    return entries


# --- rendering -----------------------------------------------------------

# This file is consumed via grep, not read front-to-back. One line per
# (resource, field) — the "Action" column is self-contained so any matched
# row tells the reader exactly what to do.

HEADER_V2 = (
    "<!-- Auto-generated by scripts/build_deprecated_fields.py. "
    "Do not edit by hand; re-run the script to refresh. "
    "Manual supplements via references/deprecated-fields-manual.yaml. -->\n"
    "\n"
    "| Resource | Field | Kind | Action | Since |\n"
    "| --- | --- | --- | --- | --- |\n"
)


def _action_cell(e: dict) -> str:
    """Self-contained instruction that tells you what to do when this row grep-matches."""
    kind = e.get("kind")
    repl = e.get("replacement")
    field = e.get("field")
    note = (e.get("note") or "").strip()

    if kind == "rename" and repl:
        msg = f"Use `{repl}` instead; value semantics unchanged."
    elif kind == "split" and repl:
        msg = (
            f"Inline argument deprecated — declare separate `{repl}` resource "
            f"alongside the parent and remove inline `{field} = …`."
        )
    elif kind == "soft-split" and repl:
        msg = (
            f"Inline field still works, but conflicts with the standalone "
            f"`{repl}` resource (drift loop on every apply). Prefer declaring "
            f"`{repl}` and dropping the inline field; if the inline field is "
            f"kept, add `lifecycle {{ ignore_changes = [{field}] }}` to the parent."
        )
    elif kind == "deprecated-no-replacement":
        msg = "Deprecated without a documented replacement — stop using this field."
    else:
        msg = "Deprecated."

    if note:
        msg += f" — {note}"
    return msg


def render(entries: list[dict]) -> str:
    # Deduplicate by (resource, field); first occurrence wins.
    seen: dict[tuple[str, str], dict] = {}
    for e in entries:
        key = (e["resource"], e["field"])
        if key in seen:
            existing = seen[key]
            if not existing.get("note") and e.get("note"):
                existing["note"] = e["note"]
            continue
        seen[key] = dict(e)

    rows = sorted(seen.values(), key=lambda x: (x["resource"], x["field"]))

    out: list[str] = [HEADER_V2]
    for e in rows:
        since = e.get("since") or ""
        kind = e.get("kind", "")
        action = _action_cell(e)
        out.append(
            f"| `{e['resource']}` | `{e['field']}` | {kind} | {action} | {since} |"
        )
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo", default=DEFAULT_CLONE)
    parser.add_argument("--out", default=None)
    parser.add_argument("--no-refresh", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not args.no_refresh:
        ensure_repo(repo)

    docs_r = repo / "website" / "docs" / "r"
    if not docs_r.is_dir():
        print(f"[error] {docs_r} not found", file=sys.stderr)
        sys.exit(1)

    all_resources = {f"alicloud_{p.name[:-len(SUFFIX)]}" for p in docs_r.glob(f"*{SUFFIX}")}

    entries = build_entries(docs_r, all_resources)

    skill_root = Path(__file__).resolve().parent.parent
    manual_path = skill_root / "references" / "deprecated-fields-manual.yaml"
    entries.extend(load_manual(manual_path))

    out_path = (
        Path(args.out).expanduser().resolve()
        if args.out
        else skill_root / "references" / "deprecated-fields.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(entries), encoding="utf-8")

    by_kind: dict[str, int] = defaultdict(int)
    for e in entries:
        by_kind[e["kind"]] += 1
    print(
        f"[ok] wrote {out_path} "
        f"({len(entries)} entries: "
        f"{by_kind.get('rename', 0)} rename, "
        f"{by_kind.get('split', 0)} split, "
        f"{by_kind.get('soft-split', 0)} soft-split, "
        f"{by_kind.get('deprecated-no-replacement', 0)} no-replacement)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
