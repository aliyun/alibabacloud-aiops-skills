#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LHM 调度迁移部署 CLI 入口与阶段编排。

流程：
  Phase 1: 触发部署（GetBwmMigrationWorkflowSubmitStart）
  Phase 2: 轮询等待完成（GetBwmMigrationSubmitInstanceList，取首条记录）
  Phase 3: 获取工作流结果（GetBwmMigrationTaskWriterWorkflowList）
  Phase 4: 生成报告（JSON + Markdown）
  Phase 5: 下载并解析结果包（预签名 OSS URL）
  Phase 6: 生成详细报告

退出码：
  0 - 部署成功
  1 - 配置/凭据/网络错误
  2 - 轮询超时
  3 - 部署失败（非 ALL_SUCCESS 的终止状态）

用法（经 install.sh 安装后）：
  lhm-sch-deploy --task-id <TASK_ID> [--config config/deploy_config.json] [--skip-start]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from lhm_deploy_cli import credentials as credential_file
from lhm_deploy_cli.client import (
    DEFAULT_ENDPOINT,
    create_client,
    fetch_all_workflows,
    list_submit_instances,
    resolve_session_endpoint,
    resolve_session_task_id,
    start_submit,
)
from lhm_deploy_cli.report import (
    build_summary_report,
    download_and_parse_package,
    format_detailed_report,
)
from lhm_deploy_cli.ui import (
    DIM,
    GREEN,
    RED,
    STATUS_CN,
    TERMINAL_STATES,
    YELLOW,
    banner,
    fmt_elapsed,
    fmt_status,
    is_success_status,
    log,
)

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_TIMEOUT = 2
EXIT_DEPLOY_FAILED = 3


# ---------------------------------------------------------------------------
# Phase 1: 触发部署
# ---------------------------------------------------------------------------

def phase1_trigger(client, task_id: str) -> Dict[str, Any]:
    banner("[1/4] 触发部署...")
    try:
        result = start_submit(client, task_id)
    except Exception as e:
        log(f"{RED('❌')} 无法连接 LHM 服务: {e}")
        sys.exit(EXIT_CONFIG_ERROR)

    if not result.get("success"):
        log(f"{RED('❌')} 部署触发失败 [{result.get('err_code')}]: {result.get('err_message')}")
        log(f"    请检查 task_id 是否正确：{task_id}")
        sys.exit(EXIT_CONFIG_ERROR)

    log(f"  {GREEN('✅')} 部署已触发")
    return result


# ---------------------------------------------------------------------------
# Phase 2: 轮询等待
# ---------------------------------------------------------------------------

def phase2_poll(
    client,
    task_id: str,
    poll_interval: int,
    timeout: int,
) -> Dict[str, Any]:
    banner("[2/4] 等待部署完成...")
    log(f"  任务ID: {task_id}")
    log(f"  轮询间隔: {poll_interval}s / 超时: {timeout}s")

    start = time.time()
    last_instance = None
    empty_polls = 0
    api_errors = 0
    max_api_errors = 3

    while True:
        elapsed = int(time.time() - start)
        elapsed_str = fmt_elapsed(elapsed)

        # 超时检查
        if elapsed > timeout:
            status_info = last_instance.get("status", "未知") if last_instance else "未开始"
            log(f"\n{YELLOW('⏰')} 部署等待超时（{timeout}s），当前状态: {fmt_status(status_info)}")
            log(f"  提示: 部署仍在进行中，可稍后用 --skip-start 重新查询")
            sys.exit(EXIT_TIMEOUT)

        # 调用 API
        try:
            result = list_submit_instances(client, task_id, page_index=1, page_size=10)
            api_errors = 0  # 成功则重置
        except Exception as e:
            api_errors += 1
            log(f"\n{YELLOW('⚠️')} [{elapsed_str}] API 临时错误 ({api_errors}/{max_api_errors}): {e}")
            if api_errors >= max_api_errors:
                log(f"{RED('❌')} API 连续失败，中止")
                sys.exit(EXIT_CONFIG_ERROR)
            time.sleep(poll_interval)
            continue

        if not result.get("success"):
            log(f"{RED('❌')} 查询失败 [{result.get('err_code')}]: {result.get('err_message')}")
            sys.exit(EXIT_CONFIG_ERROR)

        instances = result.get("data") or []
        if not instances:
            empty_polls += 1
            if empty_polls <= 3 or empty_polls % 10 == 0:
                log(f"  {DIM(f'[{elapsed_str}]')} 尚未发现部署实例，继续等待...")
            time.sleep(poll_interval)
            continue

        # 取首条记录
        instance = instances[0]
        last_instance = instance
        status = instance.get("status") or "UNKNOWN"
        icon, text = STATUS_CN.get(status, ("❓", status))

        # 进度打印（状态变化时才输出，避免刷屏）
        log(f"  {DIM(f'[{elapsed_str}]')} {icon} 状态: {text}" +
            (f"  ({instance.get('instance_name', '')})" if instance.get("instance_name") else ""))

        # 判断终止
        if status in TERMINAL_STATES:
            if status in ("ALL_SUCCESS", "SUCCESS"):
                log(f"\n  {GREEN('✅')} 部署完成！")
                return instance
            else:
                detail = instance.get("detail") or "无详情"
                log(f"\n  {RED('❌')} 部署终止: {text}")
                log(f"    详情: {detail}")
                sys.exit(EXIT_DEPLOY_FAILED)

        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Phase 3: 获取工作流结果
# ---------------------------------------------------------------------------

def phase3_fetch_workflows(client, instance_id: str) -> list:
    banner("[3/4] 获取工作流部署结果...")
    log(f"  实例ID: {instance_id}")

    try:
        workflows = fetch_all_workflows(client, instance_id)
    except Exception as e:
        log(f"{RED('❌')} 获取工作流结果失败: {e}")
        log(f"  提示: 可稍后手动查询（instance_id={instance_id}）")
        return []

    if not workflows:
        log(f"  {YELLOW('⚠️')} 该部署实例无工作流数据（可能为空部署）")
        return workflows

    total = len(workflows)
    success = sum(1 for w in workflows if is_success_status(w.get("submit_status")))
    failed = total - success
    total_nodes = sum(w.get("task_node_count") or 0 for w in workflows)

    log(f"  共 {total} 个工作流，{GREEN(str(success))} 个成功，"
        f"{RED(str(failed)) if failed else '0'} 个失败，合计 {total_nodes} 个节点")

    return workflows


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_RELPATH = Path("config") / "deploy_config.json"


def load_config(config_path: Optional[Path]) -> Dict[str, Any]:
    if not config_path or not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"{YELLOW('⚠️')} 配置文件读取失败: {e}")
        return {}


def resolve_task_id(args, config: Dict[str, Any]) -> str:
    """
    Task ID 解析优先级（从高到低）：
      1. CLI --task-id 参数（Agent 编排时传递）
      2. 会话配置 migration.convert_task_id（阶段③ convert-start 成功后自动回写）
      3. 环境变量 TASK_ID（流水线集成时使用）
      4. 配置文件中的 task_id（手动运行时使用）
      5. 工作区状态文件 .claude/task_id.txt（可选，共享工作区模式）
    """
    # 1. CLI 参数（最高优先级）
    if args.task_id:
        log(f"📝 使用 CLI 参数 task_id: {args.task_id}")
        return args.task_id

    # 2. 会话配置（阶段③ 的产物，比环境变量/配置文件更贴近本次会话）
    session_task_id = resolve_session_task_id()
    if session_task_id:
        log(f"📝 从会话配置读取 task_id: {session_task_id}")
        return session_task_id

    # 3. 环境变量
    env_task_id = os.environ.get("TASK_ID")
    if env_task_id:
        log(f"📝 从环境变量 TASK_ID 读取: {env_task_id}")
        return env_task_id

    # 4. 配置文件
    config_task_id = config.get("task_id")
    if config_task_id and not config_task_id.startswith("<"):
        log(f"📝 从配置文件读取: {config_task_id}")
        return config_task_id

    # 5. 工作区状态文件（可选）
    workspace_file = Path(".claude/task_id.txt")
    if workspace_file.exists():
        workspace_task_id = workspace_file.read_text().strip()
        if workspace_task_id:
            log(f"📝 从工作区状态文件读取: {workspace_task_id}")
            return workspace_task_id

    # 都没有，报错退出
    log(f"{RED('❌')} 未指定 task_id")
    log(f"请通过以下方式之一提供:")
    log(f"  • CLI 参数: --task-id <ID>")
    log(f"  • 先完成阶段③ 转换（会自动回写会话配置）")
    log(f"  • 环境变量: export TASK_ID=<ID>")
    log(f"  • 配置文件: {DEFAULT_CONFIG_RELPATH} 中的 task_id 字段")
    log(f"  • 工作区文件: .claude/task_id.txt")
    sys.exit(EXIT_CONFIG_ERROR)


def resolve_output_dir(args, config: Dict[str, Any]) -> Path:
    """
    输出目录优先级：CLI --output-dir > 配置文件 output_dir
    > 会话临时目录 <会话目录>/output/deploy/result/

    默认输出与会话配置（session.json）共用同一临时目录（每次会话独立，
    经指针文件定位），不再落在当前工作目录，与 lhm-sch-read-exec 的结果产物位置约定保持一致。
    """
    if args.output_dir:
        return Path(args.output_dir)
    configured_dir = config.get("output_dir") or config.get("output", {}).get("report_dir")
    base = (
        Path(configured_dir)
        if configured_dir
        else credential_file.session_dir_path() / "output" / "deploy" / "result"
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base / ts


def resolve_endpoint(args, config: Dict[str, Any]) -> str:
    """
    Endpoint 优先级（与 lhm-sch-ds 对齐）：
      1. CLI --endpoint
      2. 会话配置 lhm.endpoint（由 lhm-sch-env 转写）
      3. config.lhm.endpoint（deploy_config.json）
      4. 环境变量 LHM_ENDPOINT
      5. 默认 lhm.cn-hangzhou.aliyuncs.com
    """
    session_endpoint, _ = resolve_session_endpoint()
    return (
        args.endpoint
        or session_endpoint
        or config.get("lhm", {}).get("endpoint")
        or os.environ.get("LHM_ENDPOINT")
        or DEFAULT_ENDPOINT
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lhm-sch-deploy",
        description="LHM 调度迁移部署：触发 → 轮询 → 取结果 → 生成报告",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--task-id", help="迁移任务 ID（也可从 --config 读取）")
    parser.add_argument(
        "--config",
        default=None,
        help="配置文件路径（默认当前目录下 config/deploy_config.json）",
    )
    parser.add_argument("--output-dir", help="结果输出目录（默认 <会话目录>/output/deploy/result/<timestamp>/）")
    parser.add_argument("--endpoint", help="LHM 服务端点")
    parser.add_argument("--region", help="地域（默认 REGION_ID 环境变量或 cn-hangzhou）")
    parser.add_argument(
        "--poll-interval", type=int, default=None,
        help="轮询间隔秒数（默认 15）",
    )
    parser.add_argument(
        "--timeout", type=int, default=None,
        help="超时秒数（默认 1800）",
    )
    parser.add_argument(
        "--skip-start", action="store_true",
        help="跳过触发部署，直接轮询已有实例（断线重连场景）",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 配置文件：优先用户指定，其次当前目录下的默认位置
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_RELPATH
    config = load_config(config_path if config_path.exists() else None)

    task_id = resolve_task_id(args, config)
    output_dir = resolve_output_dir(args, config)
    endpoint = resolve_endpoint(args, config)
    _, session_region = resolve_session_endpoint()
    region = args.region or session_region or config.get("lhm", {}).get("region_id")
    poll_interval = args.poll_interval or config.get("poll_interval_seconds") or config.get("deploy", {}).get("poll_interval_seconds") or 15
    timeout = args.timeout or config.get("timeout_seconds") or config.get("deploy", {}).get("timeout_seconds") or 1800

    banner("LHM 调度迁移部署")
    log(f"  任务ID:  {task_id}")
    log(f"  端点:    {endpoint}")
    log(f"  输出目录: {output_dir}")

    # 创建客户端（凭据由 aliyun CLI 默认凭证链在调用时解析）
    client = create_client(endpoint, region)

    # Phase 1: 触发（可跳过）
    if not args.skip_start:
        phase1_trigger(client, task_id)
    else:
        log(f"\n{YELLOW('⏩')} 跳过触发，直接轮询已有实例")

    # Phase 2: 轮询
    instance = phase2_poll(client, task_id, poll_interval, timeout)
    instance_id = instance.get("instance_id")
    if not instance_id:
        log(f"{RED('❌')} 部署实例缺少 instance_id，无法继续")
        return EXIT_DEPLOY_FAILED

    # Phase 3: 获取工作流结果
    workflows = phase3_fetch_workflows(client, instance_id)

    # Phase 4: 生成基础报告
    summary = build_summary_report(task_id, instance, workflows, output_dir)

    # Phase 5: 下载结果包（预签名 URL）
    banner("[5/6] 下载结果包...")
    package_info = download_and_parse_package(client, task_id, instance_id, output_dir)

    # Phase 6: 生成详细报告
    if package_info:
        banner("[6/6] 生成详细报告...")
        report_path = format_detailed_report(
            task_id=task_id,
            instance=instance,
            workflows=workflows,
            package_info=package_info,
            output_dir=output_dir,
        )
        log(f"  {GREEN('✅')} 详细报告已生成: {report_path}")
    else:
        log(f"\n{YELLOW('⚠️')} 无法下载结果包，跳过详细报告生成")

    # 最终退出码
    failed = summary["statistics"]["failed_workflows"]
    if failed > 0:
        log(f"\n{YELLOW('⚠️')} 部署完成，但有 {failed} 个工作流失败，请查看详情")
        return EXIT_OK  # 部署本身成功，部分工作流失败属于业务结果
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
