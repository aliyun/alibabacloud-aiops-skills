#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一仪表板技能生成器 — 两阶段 CLI 模式。

Phase 1: 获取仪表板数据并输出结构化 JSON（供 LLM 分析）
Phase 2: 接收 LLM 生成的动态内容，组装并输出完整 SKILL.md

使用方式：
    # Phase 1: 获取并渲染仪表板数据
    python3 generate_skill.py phase1 <url> [--workspace-dir <path>] [--lang zh|en] [--skill-name <name>]

    # Phase 2: 组装最终 SKILL.md
    cat dynamic_content.json | python3 generate_skill.py phase2 [--output-dir <path>]
"""

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = SCRIPT_DIR.parent  # scripts/
SKILL_ROOT = SCRIPTS_ROOT.parent  # quickbi-smartq-chat/
FRAGMENT_DIR = SKILL_ROOT / "references" / "dashboard" / "fragments"
COMMON_DIR = SCRIPTS_ROOT / "common"
REFERENCES_COMMON_DIR = SKILL_ROOT / "references" / "common"

# ---------------------------------------------------------------------------
# sys.path 调整以支持 import
# ---------------------------------------------------------------------------

sys.path.insert(0, str(SCRIPTS_ROOT))

from common.config_loader import load_config, set_workspace_dir
from dashboard.fetch_dashboard_data import fetch_dashboard_data
from dashboard.render_skill_sections import (
    render_chart_components_table,
    render_dataset_list,
    render_field_mapping,
)
from dashboard.splice_skill_md import splice


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _log(msg: str):
    """输出日志到 stderr，保持 stdout 纯净用于 JSON 输出。"""
    print(msg, file=sys.stderr, flush=True)


def _error_json(phase: int, error: str, error_code: str = "UNKNOWN_ERROR") -> dict:
    """构建错误响应 JSON。"""
    return {
        "success": False,
        "phase": phase,
        "error": error,
        "error_code": error_code,
    }


def _to_kebab_case(text: str) -> str:
    """将文本转为 kebab-case（小写字母、数字、连字符）。

    中文字符使用拼音首字母或直接保留（简单实现：移除非 ASCII 非数字字符）。
    """
    # 替换空格/下划线/特殊字符为连字符
    result = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '-', text)
    # 中文字符保留（kebab-case 不处理中文，移除中文）
    result = re.sub(r'[\u4e00-\u9fff]+', '', result)
    # CamelCase → kebab
    result = re.sub(r'([a-z])([A-Z])', r'\1-\2', result)
    result = result.lower().strip('-')
    # 压缩连续连字符
    result = re.sub(r'-+', '-', result)
    return result or "dashboard"


def _infer_skill_name(dashboard_name: str, page_id: str) -> str:
    """自动推断技能名称：qbi- + 仪表板标题 kebab-case + - + pageId前8字符。"""
    kebab = _to_kebab_case(dashboard_name)
    # 截取 pageId 前8字符
    short_id = page_id[:8] if page_id else "00000000"
    name = f"qbi-{kebab}-{short_id}" if kebab else f"qbi-{short_id}"
    # 确保不超过64字符
    if len(name) > 64:
        name = name[:64].rstrip('-')
    return name


def _build_chart_summary(dashboard_data: dict) -> List[dict]:
    """从 dashboardData 构建简化版图表信息供 LLM 分析。"""
    chart_components = dashboard_data.get("chartComponents") or []
    summary = []
    for chart in chart_components:
        measures = [
            m.get("caption", "") for m in (chart.get("measures") or [])
        ]
        dimensions = [
            d.get("caption", "") for d in (chart.get("dimensions") or [])
        ]
        # 过滤条件描述（含 complexFilter 详情供 LLM 生成可读描述）
        filters_desc = []
        for f in (chart.get("defaultFilters") or []):
            caption = f.get("caption", "")
            if not caption:
                continue
            filter_info = {"caption": caption}
            complex_filter = f.get("complexFilter")
            if complex_filter and isinstance(complex_filter, dict):
                # 精简 complexFilter，只保留 LLM 需要的字段
                slim_filter = {}
                if complex_filter.get("operator"):
                    slim_filter["operator"] = complex_filter["operator"]
                raw_filters = complex_filter.get("filters")
                if raw_filters and isinstance(raw_filters, list):
                    slim_filters = []
                    for rf in raw_filters:
                        if isinstance(rf, dict):
                            slim_entry = {}
                            if rf.get("attributeName"):
                                slim_entry["attributeName"] = rf["attributeName"]
                            if rf.get("oper"):
                                slim_entry["oper"] = rf["oper"]
                            if rf.get("values"):
                                slim_entry["values"] = rf["values"]
                            if slim_entry:
                                slim_filters.append(slim_entry)
                    if slim_filters:
                        slim_filter["filters"] = slim_filters
                if slim_filter:
                    filter_info["complexFilter"] = slim_filter
            item_type = f.get("itemType")
            if item_type:
                filter_info["itemType"] = item_type
            filters_desc.append(filter_info)

        summary.append({
            "name": chart.get("componentName", ""),
            "type": chart.get("componentType", ""),
            "componentId": chart.get("componentId", ""),
            "sourceId": chart.get("sourceId", ""),
            "measures": measures,
            "dimensions": dimensions,
            "filters": filters_desc,
        })
    return summary


def _build_dataset_summary(dataset_name_map: dict) -> dict:
    """构建数据集摘要：{cube_id: 数据集名称}。"""
    return dict(dataset_name_map) if dataset_name_map else {}


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------

def run_phase1(args: argparse.Namespace) -> dict:
    """Phase 1: 获取仪表板数据，渲染 Markdown 片段，输出结构化 JSON。"""
    url = args.url
    lang = getattr(args, 'lang', 'zh') or 'zh'
    skill_name_override = getattr(args, 'skill_name', None)

    # 1. 设置工作目录
    workspace_dir = getattr(args, 'workspace_dir', None)
    if workspace_dir:
        set_workspace_dir(workspace_dir)

    # 2. 加载配置
    _log("[phase1] 加载配置...")
    try:
        config = load_config()
    except Exception as e:
        return _error_json(1, f"配置加载失败: {e}", "CONFIG_LOAD_ERROR")

    if not config:
        return _error_json(1, "配置加载失败", "CONFIG_LOAD_ERROR")

    # 3. 获取仪表板数据
    _log(f"[phase1] 获取仪表板数据: {url}")
    result = fetch_dashboard_data(url, config=config)

    if not result.get("success"):
        return _error_json(
            1,
            result.get("error", "未知错误"),
            result.get("error_code", "FETCH_ERROR"),
        )

    dashboard_data = result["dashboardData"]
    dataset_name_map = result["datasetNameMap"]
    page_id = result["pageId"]
    dashboard_url = result.get("dashboardUrl", "")

    # 4. 提取基本信息
    basic_info = dashboard_data.get("basicInfo") or {}
    dashboard_name = basic_info.get("name", "")
    gmt_modified = basic_info.get("gmtModified", "")

    # 5. 推断技能名称
    if skill_name_override:
        skill_name = skill_name_override
    else:
        skill_name = _infer_skill_name(dashboard_name, page_id)

    _log(f"[phase1] 技能名称: {skill_name}")

    # 6. 渲染 3 块 Markdown
    _log("[phase1] 渲染 Markdown 片段...")
    dataset_list_md = render_dataset_list(
        dashboard_data, dataset_name_map=dataset_name_map, lang=lang
    )
    field_mapping_md = render_field_mapping(
        dashboard_data, dataset_name_map, lang=lang
    )
    chart_components_md = render_chart_components_table(
        dashboard_data, lang=lang
    )

    # 7. 构建 chart_summary
    chart_summary = _build_chart_summary(dashboard_data)
    dataset_summary = _build_dataset_summary(dataset_name_map)

    # 8. 输出结构化 JSON
    gmt_modified_str = str(gmt_modified) if gmt_modified else ""
    return {
        "success": True,
        "phase": 1,
        "skill_name": skill_name,
        "page_id": page_id,
        "dashboard_url": dashboard_url,
        "dashboard_name": dashboard_name,
        "gmt_modified": gmt_modified_str,
        "lang": lang,
        "chart_summary": chart_summary,
        "dataset_summary": dataset_summary,
        "render_output": {
            "dataset_list_md": dataset_list_md,
            "field_mapping_md": field_mapping_md,
            "chart_components_md": chart_components_md,
        },
        "next_step": {
            "description": "使用以下命令调用 phase2 完成技能文件生成。将 LLM 生成的动态内容填入 stdin JSON。",
            "command": f"cat phase2_input.json | python3 '{Path(__file__).resolve()}' phase2 --output-dir '{workspace_dir}/skills/<skill_name>'" if workspace_dir else f"cat phase2_input.json | python3 '{Path(__file__).resolve()}' phase2 --output-dir '<workspace_dir>/skills/<skill_name>'",
            "command_note": "将 <skill_name> 替换为步骤 3.1 确定的技能名称" if workspace_dir else "将 <workspace_dir> 替换为实际工作目录路径，将 <skill_name> 替换为步骤 3.1 确定的技能名称",
            "stdin_schema": {
                "phase1_result": "将本 JSON 中除 next_step 外的所有字段原样放入此对象",
                "dynamic_sections": {
                    "frontmatter_yaml": f"YAML frontmatter，格式：---\\nname: {skill_name}\\ndescription: >\\n  针对 QuickBI「{dashboard_name}」仪表板的专属查询技能...\\n---",
                    "metadata_comment": f"HTML注释块，格式：<!-- SKILL_METADATA\\ndashboard_page_id: {page_id}\\nskill_generated_at: {gmt_modified_str}\\ndashboard_name: {dashboard_name}\\ngenerator_skill: quickbi-smartq-chat\\n-->",
                    "title_and_desc": f"一级标题 + 描述段落，格式：# {dashboard_name} - 数据查询\\n\\n针对「{dashboard_name}」仪表板的专属查询技能，支持自然语言查询（中英文）仪表板相关数据。",
                    "basic_info_table": f"Markdown 表格，3行：名称/{dashboard_name}、URL/{dashboard_url}、pageId/{page_id}",
                    "business_context": "业务背景列表，包含：业务主题、核心指标（从 chart_summary.measures 提取）、分析维度（从 chart_summary.dimensions 提取）、统计口径、筛选条件（从 chart_summary[].filters[].complexFilter 提取可读描述，格式如：图表名: 条件描述）",
                    "intent_routing_matrix": "意图路由表格，表头：| EN 关键词 | CN 关键词 | 目标图表 | 组件 ID | 数据集 ID | 分析主题 | 分析层级 | 路由说明 |\\n每个图表至少一行，基于 chart_summary 中的 measures/dimensions 推断关键词",
                    "analysis_insights": "包含两个子章节：\n### 指标关系\n从 measures 字段名推断计算关系（如：利润=销售额-成本）\n### 联动与下钻路径\n表格：| 来源层级 | 来源图表 | 交互方式 | 目标层级 | 目标图表 | 分析用途 |",
                    "chart_filter_conditions": "数组，按图表顺序（与 chart_summary 顺序一致）为每个有过滤条件的图表生成可读的过滤描述。格式示例：['province = 上海, report_date(year) = 2021', 'area = 华东', 'order_level contain 中级 or = 低级', ...]。从 chart_summary[].filters[].complexFilter 中解析生成。无过滤条件的图表对应位置填 'none'。",
                },
                "output_dir": "技能文件的输出目录路径",
            },
        },
    }


# ---------------------------------------------------------------------------
# Phase 2
# ---------------------------------------------------------------------------

_SKILL_MD_TEMPLATE = """\
{frontmatter_yaml}

{metadata_comment}

{title_and_desc}

<!-- FRAGMENT_PLACEHOLDER:entry_check_and_language -->

<!-- FRAGMENT_PLACEHOLDER:prerequisites -->

## 仪表板知识库

### 基本信息

{basic_info_table}

> ⚠️ 上述 pageId 和 URL 均来自步骤 2.1 脚本返回值（`result["pageId"]` / `result["dashboardUrl"]`），而非用户提供的原始 URL 参数。

### 业务背景与统计口径

{business_context}

### 数据集列表

<!-- FRAGMENT_PLACEHOLDER:dataset_list -->

### 图表组件（完整列表）

<!-- FRAGMENT_PLACEHOLDER:chart_components -->

### 意图路由矩阵

> 映射关系：用户问题 → 目标图表 → 数据集 ID
> **必须包含中英文关键词**，以支持双语用户查询

{intent_routing_matrix}

**路由规则**：
1. 优先匹配度量字段名（如"sales amount"或"销售额" → 包含销售额度量的图表）
2. 其次匹配维度字段名（如"by region"或"按区域" → 包含区域维度的图表）
3. 再匹配图表类型特征（如"ranking"或"排行" → `ranking-list` 图表类型）
4. 最后匹配分析主题（如"trend"或"趋势" → 分析主题包含趋势的图表）
5. 如匹配失败，使用所有数据集 ID，由 `query_openapi` 自行判断结果

## 仪表板分析思路

{analysis_insights}

## 字段映射

<!-- FRAGMENT_PLACEHOLDER:field_mapping -->

**字段映射使用规则**：
- 用户查询时使用的名称 → 先按「图表展示名」匹配 → 再按「数据集原名」匹配
- 当两个字段名不同时（如"销售额" vs "销售金额"），SmartQ 查询建议使用「数据集原名」以提高匹配精度
- 如果当前查询涉及的数据集未出现在映射表中，说明该数据集无需映射，直接使用原始名称构建查询

<!-- FRAGMENT_PLACEHOLDER:workflow -->
"""


def _generate_config_yaml(output_dir: Path, config_template: Optional[dict] = None):
    """生成技能的 config.yaml 文件。"""
    config_content = """\
# Quick BI 专属技能配置
# 用户配置文件路径:
#   <workspace>/.qbi/smartq-chat/config.yaml  — 工作目录级（最高优先级）
#   ~/.qbi/config.yaml                         — 全局配置

# QBI 服务域名
server_domain: https://bi.aliyun.com

# OpenAPI 凭证（需用户填写）
api_key:
api_secret:

# 用户 token（需用户填写）
user_token:

# 语言设置
language: zh
"""
    config_path = output_dir / "config.yaml"
    config_path.write_text(config_content, encoding="utf-8")
    return config_path


def _copy_runtime_scripts(output_dir: Path) -> List[str]:
    """复制运行时脚本到 output_dir/scripts/，并调整导入路径。"""
    scripts_dir = output_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    copied_files = []

    # 1. 复制 quickbi_openapi.py 并调整导入
    src_openapi = SCRIPT_DIR / "quickbi_openapi.py"
    if src_openapi.exists():
        content = src_openapi.read_text(encoding="utf-8")
        # 调整导入：from common.config_loader → from config_loader
        content = content.replace("from common.config_loader", "from config_loader")
        content = content.replace("from common.messages", "from messages")
        dst = scripts_dir / "quickbi_openapi.py"
        dst.write_text(content, encoding="utf-8")
        copied_files.append("scripts/quickbi_openapi.py")

    # 2. 复制 config_loader.py 并调整导入 + 末尾注入 trial_reminder 钩子加载
    src_config = COMMON_DIR / "config_loader.py"
    if src_config.exists():
        content = src_config.read_text(encoding="utf-8")
        # 调整导入：from common.messages → from messages
        content = content.replace("from common.messages", "from messages")
        # 调整 DEFAULT_CONFIG_PATH：指向同级 config.yaml
        content = content.replace(
            'DEFAULT_CONFIG_PATH = BASE_DIR.parent.parent / "default_config.yaml"',
            'DEFAULT_CONFIG_PATH = BASE_DIR.parent / "config.yaml"',
        )
        # 注入：output skill 没有 common/__init__.py 来挂钩，靠 config_loader 触发
        # 任何 import config_loader 都会顺带加载 trial_reminder → 注册 atexit
        content += (
            "\n\n# 注册退出时的试用提醒钩子（依赖同目录的 trial_reminder.py）\n"
            "try:\n"
            "    import trial_reminder  # noqa: F401\n"
            "except Exception:\n"
            "    pass\n"
        )
        dst = scripts_dir / "config_loader.py"
        dst.write_text(content, encoding="utf-8")
        copied_files.append("scripts/config_loader.py")

    # 3. 复制 messages.py 直接复制
    src_messages = COMMON_DIR / "messages.py"
    if src_messages.exists():
        shutil.copy2(src_messages, scripts_dir / "messages.py")
        copied_files.append("scripts/messages.py")

    # 4. 复制 trial_reminder.py 并调整导入（output skill 扁平结构）
    src_trial = COMMON_DIR / "trial_reminder.py"
    if src_trial.exists():
        content = src_trial.read_text(encoding="utf-8")
        content = content.replace("from common.config_loader", "from config_loader")
        content = content.replace("from common.messages", "from messages")
        dst = scripts_dir / "trial_reminder.py"
        dst.write_text(content, encoding="utf-8")
        copied_files.append("scripts/trial_reminder.py")

    return copied_files


def _copy_config_image(output_dir: Path, lang: str) -> Optional[str]:
    """复制配置引导图片到 output_dir/example/。"""
    example_dir = output_dir / "example"
    example_dir.mkdir(parents=True, exist_ok=True)

    if lang == "zh":
        src_img = REFERENCES_COMMON_DIR / "copy_skill_config_zh.png"
    else:
        src_img = REFERENCES_COMMON_DIR / "copy_skill_config_en.png"

    if src_img.exists():
        dst_name = "copy_skill_config.png"
        shutil.copy2(src_img, example_dir / dst_name)
        return f"example/{dst_name}"
    return None


def _validate_no_placeholders(content: str) -> bool:
    """检查 SKILL.md 中无 __xxx__ 或 FRAGMENT_PLACEHOLDER 残留。"""
    has_dunder = bool(re.search(r'__[A-Z][A-Z0-9_]+__', content))
    has_fragment = "FRAGMENT_PLACEHOLDER" in content
    return not has_dunder and not has_fragment


def _call_splice(
    skill_file: Path,
    fragment_dir: Path,
    render_output: dict,
    substitutions: dict,
    lang: str,
) -> dict:
    """调用 splice 函数进行 fragment 拼接。"""
    try:
        splice(skill_file, fragment_dir, render_output, substitutions, lang)
        return {"success": True, "message": f"SKILL.md fragments merged, lang={lang}."}
    except FileNotFoundError as e:
        return {"success": False, "error": f"fragment 文件未找到: {e}"}
    except Exception as e:
        return {"success": False, "error": f"splice 异常: {e}"}


def run_phase2(args: argparse.Namespace) -> dict:
    """Phase 2: 从 stdin 读取 JSON，组装并输出 SKILL.md。"""
    # 1. 从 stdin 读取 JSON
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        return _error_json(2, f"stdin JSON 解析失败: {e}", "JSON_DECODE_ERROR")

    phase1_result = payload.get("phase1_result")
    dynamic_sections = payload.get("dynamic_sections")

    if not phase1_result:
        return _error_json(2, "缺少 phase1_result 字段", "MISSING_FIELD")
    if not dynamic_sections:
        return _error_json(2, "缺少 dynamic_sections 字段", "MISSING_FIELD")

    # 确定输出目录
    output_dir_str = (
        getattr(args, 'output_dir', None)
        or payload.get("output_dir")
    )
    if not output_dir_str:
        # 默认输出到工作目录下
        skill_name = phase1_result.get("skill_name", "qbi-unknown")
        output_dir = Path.cwd() / skill_name
    else:
        output_dir = Path(output_dir_str)

    # 若目标已存在且非空，重命名为 .bak.<timestamp> 备份目录
    # ——— 这样 agent 不需要在 shell 层 rm，目标路径可直接复用为技能中心安装位置
    if output_dir.exists() and output_dir.is_dir() and any(output_dir.iterdir()):
        backup_dir = output_dir.parent / f"{output_dir.name}.bak.{int(time.time())}"
        output_dir.rename(backup_dir)
        _log(f"[phase2] 目标已存在，旧版本备份至: {backup_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    _log(f"[phase2] 输出目录: {output_dir}")

    # 2. 组装 SKILL.md 内容
    skill_md_content = _SKILL_MD_TEMPLATE.format(
        frontmatter_yaml=dynamic_sections.get("frontmatter_yaml", ""),
        metadata_comment=dynamic_sections.get("metadata_comment", ""),
        title_and_desc=dynamic_sections.get("title_and_desc", ""),
        basic_info_table=dynamic_sections.get("basic_info_table", ""),
        business_context=dynamic_sections.get("business_context", ""),
        intent_routing_matrix=dynamic_sections.get("intent_routing_matrix", ""),
        analysis_insights=dynamic_sections.get("analysis_insights", ""),
    )

    # 3. 写入 SKILL.md
    skill_md_path = output_dir / "SKILL.md"
    skill_md_path.write_text(skill_md_content, encoding="utf-8")
    _log(f"[phase2] SKILL.md 已写入: {skill_md_path}")

    # 4. 调用 splice 逻辑替换 fragment 占位符
    render_output = phase1_result.get("render_output", {})
    lang = phase1_result.get("lang", "zh")
    page_id = phase1_result.get("page_id", "")
    dashboard_name = phase1_result.get("dashboard_name", "")
    skill_name = phase1_result.get("skill_name", "")
    dashboard_url = phase1_result.get("dashboard_url", "")
    gmt_modified = phase1_result.get("gmt_modified", "")

    substitutions = {
        "__SKILL_DIR__": str(output_dir),
        "__PAGE_ID__": page_id,
        "__SKILL_GENERATED_AT__": str(gmt_modified),
        "__DASHBOARD_NAME__": dashboard_name,
        "__SKILL_NAME__": skill_name,
        "__DASHBOARD_URL__": dashboard_url,
    }

    splice_result = _call_splice(
        skill_file=skill_md_path,
        fragment_dir=FRAGMENT_DIR,
        render_output=render_output,
        substitutions=substitutions,
        lang=lang,
    )

    if not splice_result.get("success"):
        return _error_json(
            2,
            f"splice 失败: {splice_result.get('error', '未知错误')}",
            "SPLICE_ERROR",
        )

    _log("[phase2] fragment 拼接完成")

    # 5. 替换 filter 占位符
    final_content = skill_md_path.read_text(encoding="utf-8")
    chart_filters = dynamic_sections.get("chart_filter_conditions", [])
    for i, filter_desc in enumerate(chart_filters):
        placeholder = f"__FILTER_{i}__"
        final_content = final_content.replace(placeholder, filter_desc or "none")
    skill_md_path.write_text(final_content, encoding="utf-8")

    # 6. 占位符校验
    final_content = skill_md_path.read_text(encoding="utf-8")
    placeholder_clean = _validate_no_placeholders(final_content)

    if not placeholder_clean:
        remaining = re.findall(r'__[A-Z][A-Z0-9_]+__', final_content)
        remaining += [m.strip() for m in final_content.split('\n') if 'FRAGMENT_PLACEHOLDER' in m]
        return _error_json(2, f"SKILL.md 中残留占位符未替换: {remaining[:5]}", "PLACEHOLDER_VALIDATION_ERROR")

    # 6. 复制运行时脚本
    _log("[phase2] 复制运行时脚本...")
    script_files = _copy_runtime_scripts(output_dir)

    # 7. 复制配置引导图片
    img_file = _copy_config_image(output_dir, lang)

    # 8. 生成 config.yaml
    _generate_config_yaml(output_dir)

    # 9. 构建文件列表
    files_created = ["SKILL.md", "config.yaml"] + script_files
    if img_file:
        files_created.append(img_file)

    # 10. 统计信息
    chart_count = len((phase1_result.get("render_output", {}).get("chart_components_md", "")).split("\n")) - 3
    # 更准确地统计图表数
    chart_components = render_output.get("chart_components_md", "")
    # 表格行数（减去表头2行和引用块）
    table_lines = [l for l in chart_components.split("\n") if l.startswith("|") and not l.startswith("|--")]
    chart_count = max(0, len(table_lines) - 1)  # 减去表头行

    dataset_summary = phase1_result.get("dataset_summary", {})
    dataset_count = len(dataset_summary)
    line_count = len(final_content.split("\n"))

    _log(f"[phase2] 完成! 图表: {chart_count}, 数据集: {dataset_count}, 行数: {line_count}")

    return {
        "success": True,
        "phase": 2,
        "skill_path": str(output_dir),
        "skill_md_path": str(skill_md_path),
        "files_created": files_created,
        "validation": {
            "placeholder_clean": placeholder_clean,
            "chart_count": chart_count,
            "dataset_count": dataset_count,
            "line_count": line_count,
        },
    }


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    """主入口：解析子命令并执行对应 phase。"""
    parser = argparse.ArgumentParser(
        description="仪表板技能生成器（两阶段 CLI）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例：
  # Phase 1: 获取仪表板数据
  python3 generate_skill.py phase1 "https://bi.aliyun.com/..." --workspace-dir /path/to/ws

  # Phase 2: 组装 SKILL.md
  cat dynamic.json | python3 generate_skill.py phase2 --output-dir /path/to/output
""",
    )
    subparsers = parser.add_subparsers(dest="phase", help="执行阶段")

    # Phase 1 子命令
    p1 = subparsers.add_parser("phase1", help="获取仪表板数据并输出结构化 JSON")
    p1.add_argument("url", help="仪表板 URL 或数据门户 URL")
    p1.add_argument("--workspace-dir", dest="workspace_dir", default=None,
                    help="用户工作目录路径")
    p1.add_argument("--lang", choices=["zh", "en"], default="zh",
                    help="输出语言（默认 zh）")
    p1.add_argument("--skill-name", dest="skill_name", default=None,
                    help="手动指定技能名称（覆盖自动推断）")

    # Phase 2 子命令
    p2 = subparsers.add_parser("phase2", help="从 stdin 读取 JSON，组装 SKILL.md")
    p2.add_argument("--output-dir", dest="output_dir", default=None,
                    help="输出目录路径（覆盖 stdin 中的 output_dir）")

    args = parser.parse_args()

    if not args.phase:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # 执行对应阶段
    if args.phase == "phase1":
        result = run_phase1(args)
    elif args.phase == "phase2":
        result = run_phase2(args)
    else:
        result = _error_json(0, f"未知阶段: {args.phase}", "UNKNOWN_PHASE")

    # 输出 JSON 到 stdout
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")

    # 以退出码反映成功/失败
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
