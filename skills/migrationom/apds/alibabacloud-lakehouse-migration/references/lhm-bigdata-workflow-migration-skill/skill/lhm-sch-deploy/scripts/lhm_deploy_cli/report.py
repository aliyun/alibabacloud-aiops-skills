"""部署结果包下载解析与报告生成（JSON + Markdown）。"""

from __future__ import annotations

import json
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lhm_deploy_cli.client import get_result_package_url, list_submit_instances
from lhm_deploy_cli.ui import (
    GREEN,
    RED,
    YELLOW,
    banner,
    fmt_status,
    is_success_status,
    log,
)


def get_deployment_history(client, task_id: str) -> List[Dict[str, Any]]:
    """
    获取任务的完整部署历史（所有实例）。

    Args:
        client: LHM Client
        task_id: 任务 ID

    Returns:
        部署实例列表（按时间倒序）
    """
    all_instances = []
    page_index = 1
    page_size = 50

    while True:
        result = list_submit_instances(
            client, task_id,
            page_index=page_index,
            page_size=page_size
        )

        if not result.get("data"):
            break

        all_instances.extend(result["data"])

        if page_index >= result.get("total_pages", 1):
            break
        page_index += 1

    return all_instances


def download_and_parse_package(
    client,
    task_id: str,
    instance_id: str,
    output_dir: Path,
) -> Optional[Dict[str, Any]]:
    """
    下载并解析结果包，提取详细信息。

    流程：
    1. 调用 get_result_package_url 获取预签名 OSS URL
    2. 使用 urllib 直接 HTTP GET 下载 zip 文件
    3. 解压并解析关键文件（write_verify_report.json, workflow.json 等）

    Args:
        client: LHM Client
        task_id: 任务 ID
        instance_id: 部署实例 ID
        output_dir: 输出目录

    Returns:
        dict: 解析后的包信息，包含 verify_report, workflows_detail 等
    """
    try:
        # 1. 获取预签名下载 URL
        log(f"  📦 正在获取结果包下载链接...")
        url_result = get_result_package_url(client, instance_id)

        if not url_result.get("success") or not url_result.get("url"):
            log(f"{YELLOW('⚠️')} 无法获取结果包下载链接: {url_result.get('err_message', '未知错误')}")
            return None

        download_url = url_result["url"]

        # 2. 下载 zip 文件
        local_zip = output_dir / "package.zip"
        log(f"  📦 正在下载结果包...")
        # urlretrieve 不支持 timeout，网络异常时会无限挂起，改用 urlopen 显式设置超时
        with urllib.request.urlopen(download_url, timeout=60) as response, \
                open(local_zip, "wb") as out_file:
            out_file.write(response.read())
        log(f"  {GREEN('✅')} 结果包下载成功: {local_zip}")

        # 3. 解压
        extract_dir = output_dir / "package"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(local_zip, 'r') as z:
            z.extractall(extract_dir)
        log(f"  📦 结果包已解压至: {extract_dir}")

        # 4. 解析关键文件
        result = {
            "package_path": extract_dir,
            "verify_report": None,
            "workflows_detail": [],
            "node_specs": [],
            "triggers": [],
            "node_relations": [],
            "scripts": [],
        }

        # 解析 write_verify_report.json（通常在包根目录）
        verify_file = extract_dir / "write_verify_report.json"
        if not verify_file.exists() and (extract_dir / "package").is_dir():
            verify_file = extract_dir / "package" / "write_verify_report.json"

        if verify_file.exists():
            with open(verify_file, 'r', encoding='utf-8') as f:
                result["verify_report"] = json.load(f)
            log(f"  ✅ 已解析回读校验报告: {verify_file}")

        # 解析每个工作流的 workflow.json（在 package/data/project/workflow 下）
        workflows_dir = extract_dir / "package" / "data" / "project" / "workflow"
        if not workflows_dir.exists():
            workflows_dir = extract_dir / "data" / "project" / "workflow"

        if workflows_dir.exists():
            for wf_dir in workflows_dir.iterdir():
                if wf_dir.is_dir():
                    # workflow.json
                    wf_json_file = wf_dir / "workflow.json"
                    if wf_json_file.exists():
                        with open(wf_json_file, 'r', encoding='utf-8') as f:
                            wf_data = json.load(f)
                            result["workflows_detail"].append(wf_data)

                    # nodeSpec.json
                    node_spec_file = wf_dir / "nodeSpec.json"
                    if node_spec_file.exists():
                        with open(node_spec_file, 'r', encoding='utf-8') as f:
                            node_data = json.load(f)
                            result["node_specs"].extend(node_data if isinstance(node_data, list) else [node_data])

                    # nodeRelationSpec.json
                    node_rel_file = wf_dir / "nodeRelationSpec.json"
                    if node_rel_file.exists():
                        with open(node_rel_file, 'r', encoding='utf-8') as f:
                            rel_data = json.load(f)
                            result["node_relations"].extend(rel_data if isinstance(rel_data, list) else [rel_data])

                    # trigger.json
                    trigger_file = wf_dir / "trigger.json"
                    if trigger_file.exists():
                        with open(trigger_file, 'r', encoding='utf-8') as f:
                            trigger_data = json.load(f)
                            result["triggers"].extend(trigger_data if isinstance(trigger_data, list) else [trigger_data])

                    # 脚本文件
                    script_dir = wf_dir / "script"
                    if script_dir.exists():
                        for script_file in script_dir.glob("**/*"):
                            if script_file.is_file():
                                try:
                                    with open(script_file, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    result["scripts"].append({
                                        "name": script_file.name,
                                        "path": str(script_file.relative_to(extract_dir)),
                                        "content": content,
                                    })
                                except Exception:
                                    result["scripts"].append({
                                        "name": script_file.name,
                                        "path": str(script_file.relative_to(extract_dir)),
                                        "content": "(无法读取)",
                                    })

        log(f"  {GREEN('✅')} 结果包解析完成:")
        log(f"     - 工作流: {len(result['workflows_detail'])} 个")
        log(f"     - 节点: {len(result['node_specs'])} 个")
        log(f"     - 脚本: {len(result['scripts'])} 个")

        return result

    except Exception as e:
        log(f"{YELLOW('⚠️')} 结果包下载/解析失败: {e}")
        return None


def get_diff_icon(diff_type: str) -> str:
    """根据差异类型返回对应的图标"""
    icon_map = {
        "NODE_COUNT_MISMATCH": "🔢",
        "NODE_MISSING": "🚫",
        "NODE_TYPE_MISMATCH": "🔄",
        "DEPENDENCY_MISSING": "🔗",
        "WORKFLOW_NOT_FOUND": "❓",
        "SPEC_PARSE_FAILED": "💥",
        "VERIFY_EXCEPTION": "⚡",
        "NODE_EXTRA": "➕",
        "DEPENDENCY_EXTRA": "➕",
        "LOCAL_SPEC_MISSING": "📭",
    }
    return icon_map.get(diff_type, "•")


def get_suggestion_for_diffs(diffs: list) -> str:
    """根据差异类型给出修复建议"""
    if not diffs:
        return ""

    diff_types = {d.get("diffType") for d in diffs}

    # 根据差异类型组合给出建议
    if "WORKFLOW_NOT_FOUND" in diff_types:
        return "工作流在远端不存在，请检查部署是否成功完成"
    elif "SPEC_PARSE_FAILED" in diff_types or "VERIFY_EXCEPTION" in diff_types:
        return "校验过程出现异常，建议重试或检查网络连接"
    elif "NODE_COUNT_MISMATCH" in diff_types or "NODE_MISSING" in diff_types:
        return "节点数量或节点缺失，请检查远端是否完整导入了所有节点"
    elif "NODE_TYPE_MISMATCH" in diff_types:
        return "节点类型不匹配，请检查节点类型映射是否正确"
    elif "DEPENDENCY_MISSING" in diff_types:
        return "依赖关系缺失，请检查节点间的依赖是否正确建立"
    elif "LOCAL_SPEC_MISSING" in diff_types:
        return "本地 spec 文件不可用，无法进行对比"
    else:
        return "请在 DataWorks 控制台查看详细差异信息"


def format_detailed_report(
    task_id: str,
    instance: Dict[str, Any],
    workflows: list,
    package_info: Optional[Dict[str, Any]],
    output_dir: Path,
) -> str:
    """
    生成详细的 Markdown 报告，包含结果包中的丰富信息。
    """
    lines = []
    lines.append("# LHM 调度迁移部署报告")
    lines.append("")
    lines.append(f"**任务 ID**: {task_id}")
    lines.append(f"**部署时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**实例名称**: {instance.get('instance_name', 'N/A')}")
    lines.append(f"**部署状态**: {fmt_status(instance.get('status', 'UNKNOWN'))}")
    lines.append(f"**源端元数据**: {instance.get('src_meta_info', 'N/A')}")
    lines.append("")

    # 统计信息
    success_wfs = [w for w in workflows if is_success_status(w.get("submit_status"))]
    failed_wfs = [w for w in workflows if not is_success_status(w.get("submit_status"))]
    total_nodes = sum(w.get("task_node_count") or 0 for w in workflows)

    lines.append("## 部署统计")
    lines.append("")
    lines.append(f"- **工作流总数**: {len(workflows)}")
    lines.append(f"- **成功**: {len(success_wfs)} 个")
    lines.append(f"- **失败**: {len(failed_wfs)} 个")
    lines.append(f"- **节点总数**: {total_nodes} 个")
    lines.append("")

    # 回读校验结果（来自 write_verify_report.json）
    if package_info and package_info.get("verify_report"):
        verify = package_info["verify_report"]
        lines.append("## 回读校验结果")
        lines.append("")

        summary = verify.get("summary", {})
        total_match = summary.get("match", 0)
        total_warning = summary.get("warning", 0)
        total_critical = summary.get("critical", 0)

        lines.append("### 校验统计")
        lines.append("")
        lines.append(f"- ✅ **完全匹配**: {total_match} 个工作流")
        lines.append(f"- ⚠️ **警告**: {total_warning} 个工作流（有差异但可接受）")
        lines.append(f"- ❌ **严重问题**: {total_critical} 个工作流（需要关注）")
        lines.append("")

        # 根据场景给出总体建议
        if total_critical > 0:
            lines.append("### ⚠️ 发现严重问题")
            lines.append("")
            lines.append("以下工作流存在关键差异，建议检查并修复：")
            lines.append("")
        elif total_warning > 0:
            lines.append("### ℹ️ 发现轻微差异")
            lines.append("")
            lines.append("以下工作流有轻微差异，通常不影响功能：")
            lines.append("")
        else:
            lines.append("### ✅ 全部匹配")
            lines.append("")
            lines.append("所有工作流的本地配置与远端完全一致，部署成功！")
            lines.append("")

        if verify.get("workflows"):
            lines.append("### 工作流校验详情")
            lines.append("")

            # 按状态分组显示
            critical_wfs = []
            warning_wfs = []
            match_wfs = []

            for wf_verify in verify["workflows"]:
                status = wf_verify.get("overallStatus", "UNKNOWN")
                if status == "CRITICAL":
                    critical_wfs.append(wf_verify)
                elif status == "WARNING":
                    warning_wfs.append(wf_verify)
                else:
                    match_wfs.append(wf_verify)

            # 1. 先显示 CRITICAL 问题
            if critical_wfs:
                lines.append("#### ❌ 严重问题（需要修复）")
                lines.append("")
                for wf_verify in critical_wfs:
                    wf_name = wf_verify.get("workflowName", "unknown")
                    remote_id = wf_verify.get("remoteWorkflowId", "N/A")
                    diffs = wf_verify.get("diffs", [])

                    lines.append(f"**{wf_name}** (远端 ID: `{remote_id}`)")
                    lines.append("")

                    # 按差异类型分组
                    critical_diffs = [d for d in diffs if d.get("severity") == "CRITICAL"]
                    warning_diffs = [d for d in diffs if d.get("severity") == "WARNING"]

                    if critical_diffs:
                        lines.append("**严重差异**:")
                        lines.append("")
                        for diff in critical_diffs:
                            diff_type = diff.get("diffType", "unknown")
                            description = diff.get("description", "")
                            icon = get_diff_icon(diff_type)
                            lines.append(f"- {icon} **{diff_type}**: {description}")
                        lines.append("")

                    if warning_diffs:
                        lines.append("**轻微差异**:")
                        lines.append("")
                        for diff in warning_diffs:
                            diff_type = diff.get("diffType", "unknown")
                            description = diff.get("description", "")
                            lines.append(f"- ⚠️ {diff_type}: {description}")
                        lines.append("")

                    # 给出建议
                    suggestion = get_suggestion_for_diffs(critical_diffs)
                    if suggestion:
                        lines.append(f"💡 **建议**: {suggestion}")
                        lines.append("")

            # 2. 再显示 WARNING 问题
            if warning_wfs:
                lines.append("#### ⚠️ 轻微差异（通常可接受）")
                lines.append("")
                for wf_verify in warning_wfs:
                    wf_name = wf_verify.get("workflowName", "unknown")
                    remote_id = wf_verify.get("remoteWorkflowId", "N/A")
                    diffs = wf_verify.get("diffs", [])

                    lines.append(f"**{wf_name}** (远端 ID: `{remote_id}`)")
                    lines.append("")

                    for diff in diffs:
                        diff_type = diff.get("diffType", "unknown")
                        description = diff.get("description", "")
                        lines.append(f"- {diff_type}: {description}")
                    lines.append("")

            # 3. 最后显示完全匹配的工作流（简要列出）
            if match_wfs:
                lines.append("#### ✅ 完全匹配")
                lines.append("")
                lines.append("以下工作流本地配置与远端完全一致：")
                lines.append("")
                for wf_verify in match_wfs:
                    wf_name = wf_verify.get("workflowName", "unknown")
                    remote_id = wf_verify.get("remoteWorkflowId", "N/A")
                    lines.append(f"- {wf_name} (`{remote_id}`)")
                lines.append("")

    # 工作流详细信息（来自 workflow.json）
    if package_info and package_info.get("workflows_detail"):
        lines.append("## 工作流详细信息")
        lines.append("")

        for wf_detail in package_info["workflows_detail"]:
            wf_name = wf_detail.get("workflowName", "unknown")
            project_name = wf_detail.get("projectName", "N/A")
            project_id = wf_detail.get("projectId", "N/A")
            owner = wf_detail.get("owner", "N/A")
            category = wf_detail.get("categoryValue", "N/A")

            lines.append(f"### {wf_name}")
            lines.append("")
            lines.append(f"- **DataWorks 项目**: {project_name} (ID: {project_id})")
            lines.append(f"- **所属目录**: {category}")
            lines.append(f"- **责任人**: {owner}")

            # 解析节点信息
            spec_str = wf_detail.get("customProperties", {}).get("spec", "{}")
            try:
                spec = json.loads(spec_str) if isinstance(spec_str, str) else spec_str
                workflows_data = spec.get("spec", {}).get("workflows", [])
                nodes = workflows_data[0].get("nodes", []) if workflows_data else []
                dependencies = workflows_data[0].get("dependencies", []) if workflows_data else []

                if nodes:
                    lines.append(f"- **节点数量**: {len(nodes)}")
                    lines.append("")
                    lines.append("#### 节点列表")
                    lines.append("")
                    lines.append("| 节点名称 | 类型 | 远端 ID | Cron | 资源组 |")
                    lines.append("|---------|------|---------|------|--------|")

                    for node in nodes:
                        node_name = node.get("name", "unknown")
                        # 节点类型从 script.runtime.command 获取
                        node_type = node.get("script", {}).get("runtime", {}).get("command", "N/A")
                        # 远端 ID 是 id 字段
                        remote_id = node.get("id", "N/A")
                        trigger = node.get("trigger", {})
                        cron = trigger.get("cron", "N/A")
                        runtime = node.get("runtimeResource", {})
                        res_group = runtime.get("resourceGroup", "N/A")
                        res_group_short = res_group[:30] + "..." if len(res_group) > 30 else res_group

                        lines.append(f"| {node_name} | {node_type} | `{remote_id}` | {cron} | {res_group_short} |")

                    lines.append("")

                    # 依赖关系
                    if dependencies:
                        lines.append("#### 依赖关系")
                        lines.append("")
                        lines.append("```")
                        for dep in dependencies:
                            node_id = dep.get("nodeId", "unknown")
                            depends_on = dep.get("depends", [])
                            if depends_on:
                                for d in depends_on:
                                    upstream_output = d.get("output", "")
                                    # 从 output 字段提取上游节点名
                                    upstream = upstream_output.split(".")[-1] if upstream_output else "?"
                                    lines.append(f"{upstream} → {node_id}")
                            else:
                                lines.append(f"{node_id} (根节点)")
                        lines.append("```")
                        lines.append("")

                    # 脚本预览（前3个节点）
                    lines.append("#### 脚本预览")
                    lines.append("")
                    for node in nodes[:3]:
                        node_name = node.get("name", "unknown")
                        script = node.get("script", {})
                        content = script.get("content", "")
                        if content:
                            preview = content[:200] + "..." if len(content) > 200 else content
                            lines.append(f"**{node_name}**:")
                            lines.append("```bash")
                            lines.append(preview)
                            lines.append("```")
                            lines.append("")

            except Exception as e:
                lines.append(f"⚠️ 无法解析节点详情: {e}")
                lines.append("")

    # 失败工作流详情
    if failed_wfs:
        lines.append("## 失败工作流详情")
        lines.append("")
        for w in failed_wfs:
            wf_name = w.get("workflow_name", "unknown")
            status = w.get("submit_status", "unknown")
            detail = w.get("submit_detail", "无详情")
            lines.append(f"### ❌ {wf_name}")
            lines.append("")
            lines.append(f"- **状态**: {status}")
            lines.append(f"- **详情**: {detail}")
            lines.append("")

    # 输出文件
    lines.append("## 输出文件")
    lines.append("")
    lines.append(f"- `deploy_result_summary.json` - 部署结果 JSON")
    lines.append(f"- `workflow_list.json` - 工作流列表")
    if package_info and package_info.get("package_path"):
        lines.append(f"- `package/` - 完整结果包（已解压）")
        lines.append(f"- `package/write_verify_report.json` - 回读校验报告")
    lines.append("")

    report_path = output_dir / "deploy_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    log(f"  📄 详细报告: {report_path}")
    return str(report_path)


def build_summary_report(
    task_id: str,
    instance: Dict[str, Any],
    workflows: list,
    output_dir: Path,
) -> Dict[str, Any]:
    """生成 JSON 结构化报告并打印控制台汇总表（原 Phase 4）。"""
    banner("[4/4] 生成报告...")

    output_dir.mkdir(parents=True, exist_ok=True)

    # 构建汇总数据
    success_wfs = [w for w in workflows if is_success_status(w.get("submit_status"))]
    failed_wfs = [w for w in workflows if not is_success_status(w.get("submit_status"))]
    total_nodes = sum(w.get("task_node_count") or 0 for w in workflows)

    summary = {
        "task_id": task_id,
        "deploy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "instance": {
            "instance_id": instance.get("instance_id"),
            "instance_name": instance.get("instance_name"),
            "status": instance.get("status"),
            "gmt_convert": instance.get("gmt_convert"),
            "detail": instance.get("detail"),
            "src_meta_info": instance.get("src_meta_info"),
        },
        "statistics": {
            "total_workflows": len(workflows),
            "success_workflows": len(success_wfs),
            "failed_workflows": len(failed_wfs),
            "total_nodes": total_nodes,
        },
        "workflows": workflows,
        "failed_workflows": [
            {
                "workflow_name": w.get("workflow_name"),
                "submit_status": w.get("submit_status"),
                "submit_detail": w.get("submit_detail"),
                "target_workflow_name": w.get("target_workflow_name"),
            }
            for w in failed_wfs
        ],
    }

    # 保存 JSON
    summary_file = output_dir / "deploy_result_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log(f"  📄 {summary_file}")

    # 保存工作流列表原始数据
    workflows_file = output_dir / "workflow_list.json"
    with open(workflows_file, "w", encoding="utf-8") as f:
        json.dump(workflows, f, ensure_ascii=False, indent=2)
    log(f"  📄 {workflows_file}")

    # 打印 Markdown 汇总表
    log("")
    log("")
    banner("部署结果汇总")
    log(f"任务ID: {task_id}")
    log(f"状态:   {fmt_status(instance.get('status') or 'UNKNOWN')}")
    log(f"时间:   {summary['deploy_time']}")
    log("")

    if workflows:
        # 表头
        log(f"| {'工作流名称':<24} | {'目标工作流':<24} | {'状态':<8} | {'节点数':>6} | {'调度':<20} |")
        log(f"|{'-' * 26}|{'-' * 26}|{'-' * 10}|{'-' * 8}|{'-' * 22}|")
        for w in workflows:
            name = (w.get("workflow_name") or "")[:24]
            target = (w.get("target_workflow_name") or "")[:24]
            status_str = fmt_status(w.get("submit_status") or "UNKNOWN")
            nodes = str(w.get("task_node_count") or 0)
            cron = (w.get("cron") or "")[:20]
            log(f"| {name:<24} | {target:<24} | {status_str:<8} | {nodes:>6} | {cron:<20} |")

    # 失败详情
    if failed_wfs:
        log("")
        log(f"\n{RED('失败工作流详情：')}")
        for w in failed_wfs:
            log(f"  {RED('❌')} {w.get('workflow_name')}: "
                f"{w.get('submit_detail') or '无详情'}")

    log("")
    log(f"结果文件已保存至: {output_dir}")

    return summary
