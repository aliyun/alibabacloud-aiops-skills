"""Manifest loader — reads ops/ directory once per process.

ops/_manifest.json is the registry; each <Op>.json holds the full contract.
"""
from __future__ import annotations

import difflib
import json
import os
from functools import lru_cache
from typing import Any, Dict, List

from .errors import CadtError, OpNotFound

# Resolved at import time; ops/ lives at project root (two levels above scripts/cli/).
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/cli/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))  # project root
OPS_DIR = os.path.join(_PROJECT_ROOT, "ops")
MANIFEST_PATH = os.path.join(OPS_DIR, "_manifest.json")


@lru_cache(maxsize=1)
def load_manifest() -> Dict[str, Any]:
    """Load ops/_manifest.json. Cached for process lifetime."""
    if not os.path.isfile(MANIFEST_PATH):
        raise CadtError(
            f"manifest not found: {MANIFEST_PATH}",
            fix_hint="Verify cadt_deploy_on_aliyun installation is intact: cadt_deploy_on_aliyun -doctor",
        )
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def list_ops(
    *,
    category: str = "",
    exec_mode: str = "",
    search: str = "",
    source: str = "",
) -> List[Dict[str, Any]]:
    """Return manifest.operations filtered by category/exec_mode/search/source."""
    items = list(load_manifest().get("operations", []))
    if category:
        items = [x for x in items if x.get("category") == category]
    if exec_mode:
        items = [x for x in items if x.get("exec_mode") == exec_mode]
    if source:
        items = [x for x in items if x.get("source", "deploy") == source]
    if search:
        s = search.lower()
        items = [
            x
            for x in items
            if s in x.get("name", "").lower() or s in x.get("summary", "").lower()
        ]
    return items


def resolve_op_name(name: str) -> str:
    """Resolve user-supplied op name to the canonical name in manifest.

    Matching strategy (case-insensitive fallback):
      1. Exact match — return as-is
      2. Case-insensitive match — return canonical name
      3. No match — raise OpNotFound with did-you-mean suggestions
    """
    ops = load_manifest().get("operations", [])
    names = [x.get("name", "") for x in ops]

    # 1. exact
    if name in names:
        return name

    # 2. case-insensitive
    lower = name.lower()
    for n in names:
        if n.lower() == lower:
            return n

    # 3. did-you-mean
    suggestions = difflib.get_close_matches(name, names, n=3, cutoff=0.6)
    hint = (
        f"Did you mean: {', '.join(suggestions)}"
        if suggestions
        else f"Run cadt_deploy_on_aliyun -l to list valid Op names ({len(names)} total)"
    )
    raise OpNotFound(
        f"unknown operation: {name}",
        fix_hint=hint,
        fields=[{"suggestions": suggestions}] if suggestions else None,
    )


@lru_cache(maxsize=64)
def load_op(name: str) -> Dict[str, Any]:
    """Load a single ops/<Name>.json contract (case-insensitive)."""
    canonical = resolve_op_name(name)
    manifest = load_manifest()
    entry = next(
        (x for x in manifest.get("operations", []) if x.get("name") == canonical),
        None,
    )
    # entry guaranteed non-None thanks to resolve_op_name
    assert entry is not None
    file_name = entry.get("file") or f"{canonical}.json"
    spec_path = os.path.join(OPS_DIR, file_name)
    if not os.path.isfile(spec_path):
        raise CadtError(
            f"op spec file missing: {spec_path}",
            fix_hint=f"manifest registered {canonical} but spec file is missing; check ops/ directory",
        )
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def manifest_meta() -> Dict[str, Any]:
    m = load_manifest()
    return {
        "version": m.get("version", "unknown"),
        "ops_count": len(m.get("operations", [])),
        "generated_at": m.get("generated_at", ""),
    }


def ops_source_info() -> Dict[str, Any]:
    project_root = os.path.dirname(os.path.dirname(MANIFEST_PATH))
    version_file = os.path.join(project_root, "VERSION")
    actual = load_manifest().get("version", "unknown")
    expected = ""
    if os.path.isfile(version_file):
        with open(version_file, "r", encoding="utf-8") as f:
            expected = f.read().strip()
    return {
        "ops_dir": OPS_DIR,
        "manifest_version": actual,
        "skill_version": expected or "unknown",

    }
