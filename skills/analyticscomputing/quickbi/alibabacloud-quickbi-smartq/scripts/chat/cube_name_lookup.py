# -*- coding: utf-8 -*-
"""
数据集名称直查 CLI 脚本。

根据用户提及的数据集名称，在有权限的数据集中进行精确/相似匹配，
通过 stdout 输出纯 JSON 结果，日志信息走 stderr。

用法：
    python3 scripts/chat/cube_name_lookup.py \
      --cube-name "销售数据集" --workspace-dir '/path/to/workspace'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 确保能找到同级和上级模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config_loader import set_workspace_dir
from common.messages import msg
from chat.cube_resolver import match_cube_by_name, query_accessible_cubes


def log(msg: str) -> None:
    """日志输出到 stderr，不污染 stdout 的 JSON。"""
    print(msg, file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="数据集名称直查")
    parser.add_argument("--cube-name", required=True, help="用户提及的数据集名称")
    parser.add_argument("--workspace-dir", required=True, help="工作目录绝对路径")
    args = parser.parse_args()

    set_workspace_dir(args.workspace_dir)

    cube_name = args.cube_name.strip()
    if not cube_name:
        print(json.dumps({"status": "error", "message": msg("cube_lookup_empty_name")}, ensure_ascii=False))
        sys.exit(1)

    log(msg("cube_lookup_searching", name=cube_name))

    # Step 1: 查询用户有权限的数据集
    try:
        cubes = query_accessible_cubes()
    except Exception as e:
        log(msg("cube_lookup_permission_failed", exc=e))
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)

    if not cubes:
        log(msg("cube_lookup_no_datasets"))
        print(json.dumps({"status": "not_found", "candidates": []}, ensure_ascii=False))
        return

    log(msg("cube_lookup_count", count=len(cubes)))

    # Step 2: 名称匹配
    result = match_cube_by_name(cube_name, cubes)

    # Step 3: 格式化输出
    if result["status"] == "exact":
        cube = result["cube"]
        output = {
            "status": "exact",
            "cube_id": cube["cubeId"],
            "cube_name": cube["cubeName"],
        }
    elif result["status"] == "similar":
        output = {
            "status": "similar",
            "candidates": [
                {"cube_id": c["cubeId"], "cube_name": c["cubeName"], "score": c["score"]}
                for c in result["candidates"]
            ],
        }
    else:
        output = {"status": "not_found", "candidates": []}

    log(msg("cube_lookup_result", status=output['status']))
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
