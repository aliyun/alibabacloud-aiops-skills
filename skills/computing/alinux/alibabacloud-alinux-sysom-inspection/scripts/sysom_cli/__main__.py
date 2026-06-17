# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sysom_cli.inspection.command import add_inspection_subparser, run_inspection
from sysom_cli.lib.auth import SysomAuthError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sysom_cli", description="SysOM inspection CLI")
    sub = parser.add_subparsers(dest="top_cmd", required=True)
    add_inspection_subparser(sub)
    return parser


def _print_human(result: dict) -> None:
    print(f"[目标] instance={result['instance_id']} region={result['region_id']}")
    if result.get("inspection_metric_source"):
        print(f"[指标来源] metricSource={result['inspection_metric_source']}")
    print(f"[InitialSysom] {'通过' if result.get('initial_sysom_ready') else '未通过'}")
    initial_check = result.get("initial_sysom_check")
    if isinstance(initial_check, dict) and not result.get("initial_sysom_ready"):
        if initial_check.get("message"):
            print(f"[InitialSysom说明] {initial_check['message']}")
        if initial_check.get("activation_prompt"):
            print(f"[开通确认] {initial_check['activation_prompt']}")
        if initial_check.get("activation_hint"):
            print(f"[说明] {initial_check['activation_hint']}")
        return
    print(f"[巡检任务] {'已发起' if result.get('inspection_invoked') else '未发起'}")
    if result.get("inspection_api_available") is False and result.get("inspection_api_unavailable_reason"):
        print(f"[巡检API状态] 不可用：{result['inspection_api_unavailable_reason']}")
        return
    if result.get("inspection_report_id"):
        print(f"[报告] report_id={result['inspection_report_id']}")
    if "memory_usage_issue_detected" in result:
        print(f"[内存高问题] {'命中' if result['memory_usage_issue_detected'] else '未命中'}")
    print(f"[memgraph 诊断] {'已发起' if result.get('memgraph_diagnosis_invoked') else '未发起'}")
    if result.get("memgraph_diagnosis_task_id"):
        print(f"[诊断任务] task_id={result['memgraph_diagnosis_task_id']}")
    diag_result = result.get("memgraph_diagnosis_result")
    if isinstance(diag_result, dict):
        print(f"[诊断结果] code={diag_result.get('code', '')} message={diag_result.get('message', '')}")
    if result.get("memgraph_diagnosis_skipped_reason"):
        print(f"[说明] {result['memgraph_diagnosis_skipped_reason']}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.top_cmd == "inspection":
            result = asyncio.run(run_inspection(args))
            if getattr(args, "json", False):
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                _print_human(result)
            if not result.get("initial_sysom_ready", True):
                return 4
            if result.get("inspection_api_available") is False:
                return 5
            return 2 if result.get("memory_usage_issue_detected") else 0
        parser.print_help()
        return 1
    except SysomAuthError as e:
        print(f"[认证失败] {e}", file=sys.stderr)
        return 3
    except Exception as e:  # noqa: BLE001
        print(f"[执行失败] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
