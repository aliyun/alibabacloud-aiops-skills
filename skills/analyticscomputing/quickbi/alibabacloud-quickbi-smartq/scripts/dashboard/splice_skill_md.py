#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 fragment 文件 + render 脚本输出拼接至 SKILL.md，替换所有占位符。

调用方式：
    # stdin JSON → stdout JSON
    cat input.json | python3 splice_skill_md.py

    input.json = {
        "skill_file":      "/abs/path/to/SKILL.md",       # 必填
        "fragment_dir":    "/abs/path/to/fragments",       # 必填
        "render_output":   {                               # 必填
            "dataset_list_md": "...",
            "field_mapping_md": "...",
            "chart_components_md": "..."
        },
        "substitutions":   {                               # 必填
            "__SKILL_DIR__": "...",
            "__PAGE_ID__": "...",
            "__SKILL_GENERATED_AT": "...",
            "__DASHBOARD_NAME__": "...",
            "__SKILL_NAME__": "...",
            "__DASHBOARD_URL__": "..."
        },
        "lang":            "zh"                            # 可选，默认 zh
    }

    output = {"success": true, "message": "..."}
"""

import json
import pathlib
import sys
from typing import Any, Dict, List


# ---------- 语言 → fragment 文件映射 ----------

_FRAGMENT_FILES: Dict[str, Dict[str, List[str]]] = {
    "zh": {
        "entry_check_and_language": ["entry_check.zh.md", "language_rules.zh.md"],
        "prerequisites":            ["prerequisites.zh.md"],
        "workflow":                 ["workflow.zh.md"],
    },
    "en": {
        "entry_check_and_language": ["entry_check.md", "language_rules.md"],
        "prerequisites":            ["prerequisites.md"],
        "workflow":                 ["workflow.md"],
    },
}

# render_output key → FRAGMENT_PLACEHOLDER key
_RENDER_KEY_TO_PLACEHOLDER = {
    "dataset_list_md":      "dataset_list",
    "field_mapping_md":     "field_mapping",
    "chart_components_md":  "chart_components",
}


def splice(
    skill_file: pathlib.Path,
    fragment_dir: pathlib.Path,
    render_output: Dict[str, Any],
    substitutions: Dict[str, str],
    lang: str = "zh",
) -> None:
    """读取 SKILL.md，替换文件型 fragment + 渲染型 fragment，写回文件。"""

    content = skill_file.read_text(encoding="utf-8")

    # ---- 1. 替换文件型 fragment ----
    fragment_files = _FRAGMENT_FILES.get(lang, _FRAGMENT_FILES["zh"])
    for placeholder_key, files in fragment_files.items():
        merged = "\n\n".join(
            (fragment_dir / f).read_text(encoding="utf-8") for f in files
        )
        for k, v in substitutions.items():
            merged = merged.replace(k, str(v))
        anchor = f"<!-- FRAGMENT_PLACEHOLDER:{placeholder_key} -->"
        content = content.replace(anchor, merged)

    # ---- 2. 替换渲染脚本型 fragment ----
    for render_key, placeholder_key in _RENDER_KEY_TO_PLACEHOLDER.items():
        rendered_md = render_output.get(render_key, "")
        anchor = f"<!-- FRAGMENT_PLACEHOLDER:{placeholder_key} -->"
        content = content.replace(anchor, rendered_md)

    skill_file.write_text(content, encoding="utf-8")


# ---------- CLI ----------

def _main_cli() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        json.dump(
            {"success": False, "error": f"stdin JSON decode error: {e}"},
            sys.stdout, ensure_ascii=False,
        )
        return 1

    # 必填字段校验
    for key in ("skill_file", "fragment_dir", "render_output", "substitutions"):
        if key not in payload:
            json.dump(
                {"success": False, "error": f"missing required field: {key}"},
                sys.stdout, ensure_ascii=False,
            )
            return 1

    skill_file = pathlib.Path(payload["skill_file"])
    fragment_dir = pathlib.Path(payload["fragment_dir"])
    render_output = payload["render_output"]
    substitutions = payload["substitutions"]
    lang = (payload.get("lang") or "zh").lower()
    if lang not in ("zh", "en"):
        lang = "zh"

    if not skill_file.exists():
        json.dump(
            {"success": False, "error": f"skill_file not found: {skill_file}"},
            sys.stdout, ensure_ascii=False,
        )
        return 1

    if not fragment_dir.is_dir():
        json.dump(
            {"success": False, "error": f"fragment_dir not found: {fragment_dir}"},
            sys.stdout, ensure_ascii=False,
        )
        return 1

    splice(skill_file, fragment_dir, render_output, substitutions, lang)

    json.dump(
        {
            "success": True,
            "message": f"SKILL.md fragments merged (files + rendered), lang={lang}.",
        },
        sys.stdout, ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
