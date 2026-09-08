# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import subprocess
import sys

# module import name -> pip package name
_DEPS = {
    "requests": "requests",
    "alibabacloud_tea_openapi": "alibabacloud-tea-openapi",
    "alibabacloud_tea_util": "alibabacloud-tea-util",
}


def _ensure_deps() -> None:
    missing = {
        pip_name
        for mod_name, pip_name in _DEPS.items()
        if importlib.util.find_spec(mod_name) is None
    }
    if not missing:
        return

    print(
        f"[Setup] Installing missing dependencies: {', '.join(sorted(missing))}", file=sys.stderr)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install",
                "--quiet", *sorted(missing)],
        )
    except Exception:
        print(
            f"[ERROR] Failed to install dependencies automatically.\n"
            f"\n"
            f"Please install them manually:\n"
            f"  cd scripts && bash init.sh\n"
            f"\n"
            f"Or:\n"
            f"  pip install {' '.join(sorted(missing))}\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # Verify installation succeeded.
    importlib.invalidate_caches()
    still_missing = []
    for mod_name, pip_name in _DEPS.items():
        if importlib.util.find_spec(mod_name) is None:
            still_missing.append(pip_name)
    if still_missing:
        print(
            f"[ERROR] Dependencies still missing after install: {', '.join(still_missing)}\n"
            f"\n"
            f"Please initialize the environment:\n"
            f"  cd scripts && bash init.sh\n",
            file=sys.stderr,
        )
        raise SystemExit(1)


_ensure_deps()

try:
    from sysom_cli.inspection.command import add_inspection_subparser, run_inspection
    from sysom_cli.lib.auth import SysomAuthError
except ImportError as e:
    missing = e.name or str(e).split("'")[1] if "'" in str(e) else str(e)
    print(
        f"[ERROR] Missing dependency: {missing}\n"
        f"\n"
        f"Please initialize the environment:\n"
        f"  cd scripts && bash init.sh\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sysom_cli", description="SysOM inspection CLI")
    sub = parser.add_subparsers(dest="top_cmd", required=True)
    add_inspection_subparser(sub)
    return parser


def _print_human(result: dict) -> None:
    print(
        f"[Target] instance={result['instance_id']} region={result['region_id']}")
    if result.get("inspection_metric_source"):
        print(
            f"[Metric Source] metricSource={result['inspection_metric_source']}")
    print(
        f"[InitialSysom] {'Ready' if result.get('initial_sysom_ready') else 'Not Ready'}")
    initial_check = result.get("initial_sysom_check")
    if isinstance(initial_check, dict) and not result.get("initial_sysom_ready"):
        if initial_check.get("message"):
            print(f"[InitialSysom Details] {initial_check['message']}")
        if initial_check.get("activation_prompt"):
            print(
                f"[Activation Confirmation] {initial_check['activation_prompt']}")
        if initial_check.get("activation_hint"):
            print(f"[Hint] {initial_check['activation_hint']}")
        return
    print(
        f"[Inspection Task] {'Started' if result.get('inspection_invoked') else 'Not Started'}")
    if result.get("inspection_api_available") is False and result.get("inspection_api_unavailable_reason"):
        print(
            f"[Inspection API] Unavailable: {result['inspection_api_unavailable_reason']}")
        return
    if result.get("inspection_report_id"):
        print(f"[Report] report_id={result['inspection_report_id']}")
    if "memory_usage_issue_detected" in result:
        print(
            f"[High Memory Issue] {'Detected' if result['memory_usage_issue_detected'] else 'Not Detected'}")
    if result.get("memgraph_diagnosis_invoked"):
        print("[memgraph Diagnosis] Started")
    if result.get("memgraph_diagnosis_task_id"):
        print(
            f"[Diagnosis Task] task_id={result['memgraph_diagnosis_task_id']}")
    diag_result = result.get("memgraph_diagnosis_result")
    if isinstance(diag_result, dict):
        print(
            f"[Diagnosis Result] code={diag_result.get('code', '')} message={diag_result.get('message', '')}")
    if result.get("memgraph_diagnosis_skipped_reason"):
        print(f"[Reason] {result['memgraph_diagnosis_skipped_reason']}")
    conclusion = result.get("inspection_conclusion")
    if isinstance(conclusion, dict):
        if conclusion.get("inspection_report_result"):
            print(
                f"[Inspection Report Conclusion] {conclusion['inspection_report_result']}")
        if conclusion.get("diagnosis_report_result"):
            print(
                f"[Diagnosis Report Conclusion] {conclusion['diagnosis_report_result']}")
        if conclusion.get("final_conclusion"):
            print(f"[Inspection Conclusion] {conclusion['final_conclusion']}")
        if conclusion.get("report_file_path") and conclusion.get("report_file_path") != "-":
            print(f"[Report File] {conclusion['report_file_path']}")
        if conclusion.get("report_file_write_error"):
            print(
                f"[Report File Write Failed] {conclusion['report_file_write_error']}")
        if conclusion.get("report_markdown"):
            print("[Full Inspection Report]")
            print(conclusion["report_markdown"])


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
        print(f"[Authentication Failed] {e}", file=sys.stderr)
        return 3
    except Exception as e:  # noqa: BLE001
        print(f"[Execution Failed] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
