#!/usr/bin/env python3
"""
场景管理工具 - 查看场景配置、生成控制台操作指南、生成测试方案
用法:
  python scenario_manager.py list                         # 列出所有场景
  python scenario_manager.py show <场景ID>                # 查看场景详情
  python scenario_manager.py matrix <场景ID>              # 导出标签配置矩阵
  python scenario_manager.py guide <场景ID>               # 生成控制台操作指南
  python scenario_manager.py plan <场景ID>                # 生成测试方案
  python scenario_manager.py compare <场景1> <场景2> ...  # 多场景对比
  python scenario_manager.py export-all                   # 导出所有场景配置
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.markdown import Markdown

from config import OUTPUT_DIR
from scenarios import (
    ALL_LABELS,
    LABEL_MAP,
    LabelCategory,
    LabelSwitch,
    BusinessScenario,
    get_scenario,
    list_scenarios,
)

console = Console()


def cmd_list(args):
    """列出所有可用场景"""
    scenarios = list_scenarios()

    table = Table(title="可用业务场景模板", show_lines=True)
    table.add_column("场景ID", style="bold cyan")
    table.add_column("名称", style="bold")
    table.add_column("行业")
    table.add_column("基础Service")
    table.add_column("风险容忍度")

    for s in scenarios:
        table.add_row(
            s.id, s.name, s.industry, s.base_service,
            s.risk_tolerance[:20] + "..." if len(s.risk_tolerance) > 20 else s.risk_tolerance,
        )

    console.print(table)
    console.print(f"\n使用 [bold]python scenario_manager.py show <场景ID>[/bold] 查看详情")


def cmd_show(args):
    """查看场景详情"""
    scenario = get_scenario(args.scenario_id)
    if not scenario:
        console.print(f"[red]未找到场景: {args.scenario_id}[/red]")
        console.print("可用场景: " + ", ".join(s.id for s in list_scenarios()))
        return

    # 基本信息
    console.print(Panel(
        f"[bold]{scenario.name}[/bold]\n\n{scenario.description}",
        title=f"场景: {scenario.id}",
        border_style="blue",
    ))

    info_table = Table(show_header=False, box=None)
    info_table.add_column("", style="bold")
    info_table.add_column("")
    info_table.add_row("行业", scenario.industry)
    info_table.add_row("基础Service", scenario.base_service)
    info_table.add_row("建议自定义Service", f"{scenario.base_service}_{scenario.recommended_service_suffix}")
    info_table.add_row("风险容忍度", scenario.risk_tolerance)
    console.print(info_table)

    # 标签配置矩阵
    _print_label_matrix(scenario)

    # 配置说明
    if scenario.config_notes:
        console.print("\n[bold]配置说明:[/bold]")
        for i, note in enumerate(scenario.config_notes, 1):
            console.print(f"  {i}. {note}")

    # 特殊要求
    if scenario.special_requirements:
        console.print("\n[bold]场景特殊要求:[/bold]")
        for req in scenario.special_requirements:
            console.print(f"  - {req}")

    # 测试计划摘要
    if scenario.test_plan:
        console.print(f"\n[dim]使用 python scenario_manager.py plan {scenario.id} 查看完整测试方案[/dim]")


def cmd_matrix(args):
    """导出标签配置矩阵"""
    scenario = get_scenario(args.scenario_id)
    if not scenario:
        console.print(f"[red]未找到场景: {args.scenario_id}[/red]")
        return

    _print_label_matrix(scenario)

    # 导出为文件
    if args.output:
        _export_matrix(scenario, args.output, args.format)


def cmd_guide(args):
    """生成控制台操作指南"""
    scenario = get_scenario(args.scenario_id)
    if not scenario:
        console.print(f"[red]未找到场景: {args.scenario_id}[/red]")
        return

    custom_service = f"{scenario.base_service}_{scenario.recommended_service_suffix}"

    guide_lines = [
        f"# {scenario.name} - 控制台配置指南",
        f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"\n## 一、创建自定义Service",
        f"\n1. 登录[内容安全控制台](https://yundun.console.aliyun.com/)",
        f"2. 左侧导航：**机器审核增强版 > 文本审核 > 规则配置**",
        f"3. 在规则管理页签，找到 `{scenario.base_service}` 服务",
        f"4. 点击操作列的 **复制** 按钮",
        f"5. 服务名称填写: `{custom_service}`",
        f"6. 备注填写: {scenario.name}场景专用",
        f"7. 点击确定",
        f"\n## 二、配置检测规则",
        f"\n1. 在新创建的 `{custom_service}` 服务行，点击 **设置规则**",
        f"2. 进入规则详情后，点击 **编辑** 进入编辑模式",
        f"3. 按以下矩阵配置各标签的开关状态:",
    ]

    # 按类别生成配置表
    categories_order = [
        LabelCategory.PORNOGRAPHIC, LabelCategory.POLITICAL,
        LabelCategory.VIOLENCE, LabelCategory.CONTRABAND,
        LabelCategory.INAPPROPRIATE, LabelCategory.PROMOTION,
        LabelCategory.RELIGION, LabelCategory.CUSTOM,
    ]

    for category in categories_order:
        category_labels = [l for l in ALL_LABELS if l.category == category]
        if not category_labels:
            continue

        guide_lines.append(f"\n### {category.value}类")
        guide_lines.append(f"\n| 标签 | 说明 | 建议状态 | 操作 |")
        guide_lines.append(f"|------|------|----------|------|")

        for label in category_labels:
            switch = scenario.label_config.get(label.key, LabelSwitch.OFF)
            status_icon = {
                LabelSwitch.CRITICAL: "🔴 必须开启",
                LabelSwitch.ON: "🟢 建议开启",
                LabelSwitch.OPTIONAL: "🟡 可选",
                LabelSwitch.OFF: "⚪ 建议关闭",
            }[switch]
            action = {
                LabelSwitch.CRITICAL: "✅ 开启",
                LabelSwitch.ON: "✅ 开启",
                LabelSwitch.OPTIONAL: "根据需要决定",
                LabelSwitch.OFF: "❌ 关闭",
            }[switch]
            guide_lines.append(
                f"| `{label.key}` | {label.description} | {status_icon} | {action} |"
            )

    guide_lines.extend([
        f"\n4. 确认所有标签配置后，点击 **保存**",
        f"5. 等待 2~5 分钟生效",
        f"\n## 三、配置说明",
    ])

    for i, note in enumerate(scenario.config_notes, 1):
        guide_lines.append(f"\n{i}. {note}")

    if scenario.special_requirements:
        guide_lines.append(f"\n## 四、场景特殊注意事项")
        for req in scenario.special_requirements:
            guide_lines.append(f"\n- {req}")

    guide_lines.extend([
        f"\n## 五、调用方式",
        f"\n配置完成后，使用以下service参数调用API：",
        f"\n```",
        f'service = "{custom_service}"',
        f"```",
        f"\n或使用测试框架：",
        f"\n```bash",
        f'python main.py run --samples your_samples.json --text-services {custom_service}',
        f"```",
    ])

    guide_text = "\n".join(guide_lines)

    # 控制台展示
    console.print(Markdown(guide_text))

    # 导出文件
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(
        OUTPUT_DIR,
        f"console_guide_{scenario.id}_{datetime.now().strftime('%Y%m%d')}.md"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(guide_text)

    console.print(f"\n[green]指南已导出: {output_path}[/green]")


def cmd_plan(args):
    """生成测试方案"""
    scenario = get_scenario(args.scenario_id)
    if not scenario:
        console.print(f"[red]未找到场景: {args.scenario_id}[/red]")
        return

    if not scenario.test_plan:
        console.print(f"[yellow]该场景暂无预定义测试方案[/yellow]")
        return

    plan = scenario.test_plan
    custom_service = f"{scenario.base_service}_{scenario.recommended_service_suffix}"

    console.print(Panel(
        f"[bold]{scenario.name} - 测试方案[/bold]",
        border_style="green",
    ))

    # 样本分类表
    sample_table = Table(title="需准备的测试样本", show_lines=True)
    sample_table.add_column("分类ID", style="bold")
    sample_table.add_column("说明")
    sample_table.add_column("预期结果", style="bold")

    for cat in plan.sample_categories:
        desc = plan.sample_descriptions.get(cat, "")
        expected = plan.expected_outcomes.get(cat, "")
        sample_table.add_row(cat, desc, expected)

    console.print(sample_table)

    # 重点标签
    console.print(f"\n[bold]重点关注标签:[/bold]")
    for label_key in plan.focus_labels:
        label = LABEL_MAP.get(label_key)
        if label:
            console.print(f"  - {label.key} ({label.name}): {label.description}")

    # 边界case
    if plan.edge_cases:
        console.print(f"\n[bold]边界测试Case:[/bold]")
        for i, case in enumerate(plan.edge_cases, 1):
            console.print(f"  {i}. {case}")

    # 生成样本文件模板
    console.print(f"\n[bold]生成样本文件模板...[/bold]")
    samples_data = {"samples": []}
    idx = 1
    for cat in plan.sample_categories:
        for j in range(3):  # 每分类3个占位样本
            samples_data["samples"].append({
                "sample_id": f"{scenario.id}_{idx:04d}",
                "modality": "text",
                "content": f"【待填写-{plan.sample_descriptions.get(cat, cat)}】示例{j+1}",
                "data_id": f"{scenario.id}_{cat}_{j+1:02d}",
                "category": cat,
                "expected_risk_level": plan.expected_outcomes.get(cat, "").split(" - ")[0].strip() if " - " in plan.expected_outcomes.get(cat, "") else "",
                "expected_labels": [],
            })
            idx += 1

    samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
    os.makedirs(samples_dir, exist_ok=True)
    template_path = os.path.join(samples_dir, f"template_{scenario.id}.json")
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(samples_data, f, ensure_ascii=False, indent=2)

    console.print(f"  样本模板: {template_path}")
    console.print(f"  共 {len(samples_data['samples'])} 个占位样本，请替换为真实测试数据")

    # 测试执行命令
    console.print(f"\n[bold]测试执行命令:[/bold]")
    console.print(f"  1. 替换样本模板中的占位内容为真实数据")
    console.print(f"  2. 确保已在控制台完成 {custom_service} 的规则配置")
    console.print(f"  3. 执行测试:")
    console.print(f"     python main.py run --samples {template_path} --text-services {custom_service}")
    console.print(f"  4. 标注结果:")
    console.print(f"     python main.py annotate --file results/results_batch_xxx.json")


def cmd_compare(args):
    """多场景对比"""
    scenarios_to_compare = []
    for sid in args.scenario_ids:
        s = get_scenario(sid)
        if not s:
            console.print(f"[yellow]跳过未找到的场景: {sid}[/yellow]")
            continue
        scenarios_to_compare.append(s)

    if len(scenarios_to_compare) < 2:
        console.print("[red]至少需要2个有效场景进行对比[/red]")
        return

    # 对比表
    compare_table = Table(title="场景标签配置对比", show_lines=True)
    compare_table.add_column("标签", style="bold")
    compare_table.add_column("类别")
    for s in scenarios_to_compare:
        compare_table.add_column(s.name, justify="center")

    switch_display = {
        LabelSwitch.CRITICAL: "[bold red]必须[/bold red]",
        LabelSwitch.ON: "[green]开启[/green]",
        LabelSwitch.OPTIONAL: "[yellow]可选[/yellow]",
        LabelSwitch.OFF: "[dim]关闭[/dim]",
    }

    for label in ALL_LABELS:
        row = [label.key, label.category.value]
        for s in scenarios_to_compare:
            switch = s.label_config.get(label.key, LabelSwitch.OFF)
            row.append(switch_display.get(switch, str(switch)))
        compare_table.add_row(*row)

    console.print(compare_table)

    # 差异分析
    console.print("\n[bold]差异分析:[/bold]")
    for label in ALL_LABELS:
        configs = set()
        for s in scenarios_to_compare:
            configs.add(s.label_config.get(label.key, LabelSwitch.OFF))
        if len(configs) > 1:
            details = ", ".join(
                f"{s.name}={s.label_config.get(label.key, LabelSwitch.OFF).value}"
                for s in scenarios_to_compare
            )
            console.print(f"  {label.key} ({label.name}): {details}")


def cmd_export_all(args):
    """导出所有场景配置"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_data = {}
    for scenario in list_scenarios():
        all_data[scenario.id] = {
            "name": scenario.name,
            "description": scenario.description,
            "industry": scenario.industry,
            "base_service": scenario.base_service,
            "custom_service": f"{scenario.base_service}_{scenario.recommended_service_suffix}",
            "risk_tolerance": scenario.risk_tolerance,
            "label_config": {k: v.value for k, v in scenario.label_config.items()},
            "config_notes": scenario.config_notes,
            "special_requirements": scenario.special_requirements,
        }

    output_path = os.path.join(OUTPUT_DIR, f"all_scenarios_{datetime.now().strftime('%Y%m%d')}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    console.print(f"[green]所有场景配置已导出: {output_path}[/green]")

    # 同时生成Excel对比矩阵
    try:
        import pandas as pd

        rows = []
        for label in ALL_LABELS:
            row = {"标签": label.key, "名称": label.name, "类别": label.category.value}
            for scenario in list_scenarios():
                switch = scenario.label_config.get(label.key, LabelSwitch.OFF)
                row[scenario.name] = switch.value
            rows.append(row)

        xlsx_path = os.path.join(OUTPUT_DIR, f"scenario_matrix_{datetime.now().strftime('%Y%m%d')}.xlsx")
        pd.DataFrame(rows).to_excel(xlsx_path, index=False)
        console.print(f"[green]对比矩阵已导出: {xlsx_path}[/green]")
    except ImportError:
        pass


# ============================================================
# 辅助函数
# ============================================================

def _print_label_matrix(scenario: BusinessScenario):
    """打印标签配置矩阵"""
    table = Table(title=f"{scenario.name} - 标签配置矩阵", show_lines=True)
    table.add_column("类别", style="bold")
    table.add_column("标签Key")
    table.add_column("名称")
    table.add_column("建议状态", justify="center")

    switch_style = {
        LabelSwitch.CRITICAL: "[bold red]🔴 必须开启[/bold red]",
        LabelSwitch.ON: "[green]🟢 建议开启[/green]",
        LabelSwitch.OPTIONAL: "[yellow]🟡 可选[/yellow]",
        LabelSwitch.OFF: "[dim]⚪ 建议关闭[/dim]",
    }

    current_category = None
    for label in ALL_LABELS:
        switch = scenario.label_config.get(label.key, LabelSwitch.OFF)
        cat_name = label.category.value if label.category != current_category else ""
        current_category = label.category
        table.add_row(
            cat_name,
            label.key,
            label.name,
            switch_style.get(switch, str(switch)),
        )

    console.print(table)


def _export_matrix(scenario: BusinessScenario, output_path: str, format: str):
    """导出标签配置矩阵"""
    import pandas as pd

    rows = []
    for label in ALL_LABELS:
        switch = scenario.label_config.get(label.key, LabelSwitch.OFF)
        rows.append({
            "类别": label.category.value,
            "标签Key": label.key,
            "名称": label.name,
            "说明": label.description,
            "建议状态": switch.value,
        })

    df = pd.DataFrame(rows)
    if format == "xlsx":
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

    console.print(f"[green]矩阵已导出: {output_path}[/green]")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="内容安全 - 业务场景管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="列出所有场景模板")

    # show
    show_p = subparsers.add_parser("show", help="查看场景详情")
    show_p.add_argument("scenario_id", help="场景ID")

    # matrix
    matrix_p = subparsers.add_parser("matrix", help="导出标签配置矩阵")
    matrix_p.add_argument("scenario_id", help="场景ID")
    matrix_p.add_argument("--output", "-o", help="输出文件路径")
    matrix_p.add_argument("--format", "-f", choices=["xlsx", "csv"], default="xlsx")

    # guide
    guide_p = subparsers.add_parser("guide", help="生成控制台操作指南")
    guide_p.add_argument("scenario_id", help="场景ID")

    # plan
    plan_p = subparsers.add_parser("plan", help="生成测试方案")
    plan_p.add_argument("scenario_id", help="场景ID")

    # compare
    compare_p = subparsers.add_parser("compare", help="多场景对比")
    compare_p.add_argument("scenario_ids", nargs="+", help="场景ID列表")

    # export-all
    subparsers.add_parser("export-all", help="导出所有场景配置")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cmd_map = {
        "list": cmd_list,
        "show": cmd_show,
        "matrix": cmd_matrix,
        "guide": cmd_guide,
        "plan": cmd_plan,
        "compare": cmd_compare,
        "export-all": cmd_export_all,
    }

    cmd_map[args.command](args)


if __name__ == "__main__":
    import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
