#!/usr/bin/env python3
"""
内容安全自动化测试框架 - 主入口
支持命令：run（运行测试）、annotate（人工标注）、report（生成报告）
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler

from config import OUTPUT_DIR, SAMPLES_DIR, TestConfig
from runner import SampleLoader, TestRunner
from annotator import Annotator
from reporter import Reporter

console = Console()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)


def cmd_run(args):
    """执行测试命令"""
    # 加载样本
    sample_file = args.samples
    if not os.path.exists(sample_file):
        console.print(f"[red]样本文件不存在: {sample_file}[/red]")
        sys.exit(1)

    console.print(f"[bold]加载样本文件: {sample_file}[/bold]")
    samples = SampleLoader.load(sample_file)
    console.print(f"[green]成功加载 {len(samples)} 个样本[/green]")

    # 配置测试
    config = TestConfig()
    if args.text_services:
        config.text_services = args.text_services.split(",")
    if args.image_services:
        config.image_services = args.image_services.split(",")
    if args.audio_services:
        config.audio_services = args.audio_services.split(",")
    if args.video_services:
        config.video_services = args.video_services.split(",")
    if args.concurrent:
        config.max_concurrent = args.concurrent

    # 运行测试
    runner = TestRunner(config)
    batch_result = runner.run(samples)

    # 输出结果
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成报告
    reporter = Reporter(batch_result)
    reporter.generate_summary_report()

    # 导出结果
    output_format = args.format or config.output_format
    report_path = reporter.export_report(format=output_format)

    # 同时保存JSON详细结果（方便后续标注加载）
    json_path = os.path.join(
        OUTPUT_DIR,
        f"results_{batch_result.batch_id}.json",
    )
    results_data = []
    for r in batch_result.results:
        # 获取样本内容预览
        matching_samples = [s for s in samples if s.sample_id == r.sample_id]
        content_preview = ""
        if matching_samples:
            content = matching_samples[0].content
            content_preview = content[:200] if len(content) > 200 else content

        results_data.append({
            "sample_id": r.sample_id,
            "request_id": r.request_id,
            "service": r.service,
            "modality": r.modality.value,
            "content_preview": content_preview,
            "risk_level": r.risk_level,
            "labels": "|".join(r.labels),
            "confidence": r.confidence,
            "reason": r.reason,
            "latency_ms": round(r.latency_ms, 2),
            "success": r.success,
            "error_code": r.error_code,
            "error_message": r.error_message,
            "request_time": r.request_time,
            "response_time": r.response_time,
            "annotation": r.annotation,
            "annotation_note": "",
            "annotated_by": "",
            "annotated_at": "",
        })

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)

    console.print(f"\n[bold green]测试完成！[/bold green]")
    console.print(f"  报告文件: {report_path}")
    console.print(f"  结果文件: {json_path}")
    console.print(f"\n[dim]使用以下命令进行标注:[/dim]")
    console.print(f"  python main.py annotate --file {json_path}")


def cmd_annotate(args):
    """人工标注命令"""
    results_file = args.file
    if not os.path.exists(results_file):
        console.print(f"[red]结果文件不存在: {results_file}[/red]")
        sys.exit(1)

    annotator = Annotator()
    count = annotator.load_results(results_file)
    console.print(f"[green]加载 {count} 条待标注记录[/green]")

    # 显示标注进度
    progress = annotator.get_annotation_progress()
    console.print(
        f"  已标注: {progress['total'] - progress['pending']} / {progress['total']}"
    )

    if args.export_only:
        # 仅导出已有标注
        output_path = annotator.export_annotated(format=args.format or "xlsx")
        return

    # 启动交互式标注
    annotator.start_interactive_annotation(annotator_name=args.annotator or "")

    # 标注完成后导出
    output_path = annotator.export_annotated(format=args.format or "xlsx")

    # 显示最终进度
    progress = annotator.get_annotation_progress()
    console.print(f"\n[bold]标注统计:[/bold]")
    console.print(f"  正确: {progress['correct']}")
    console.print(f"  误判: {progress['false_positive']}")
    console.print(f"  漏判: {progress['false_negative']}")
    console.print(f"  不确定: {progress['uncertain']}")
    console.print(f"  待标注: {progress['pending']}")


def cmd_report(args):
    """生成/查看报告命令"""
    results_file = args.file
    if not os.path.exists(results_file):
        console.print(f"[red]文件不存在: {results_file}[/red]")
        sys.exit(1)

    reporter = Reporter()
    reporter.load_annotated_results(results_file)

    # 生成对齐分析报告
    reporter.generate_alignment_report()

    # 导出报告
    if args.output:
        reporter.export_report(output_path=args.output, format=args.format or "xlsx")


def main():
    parser = argparse.ArgumentParser(
        description="内容安全自动化测试框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 运行测试
  python main.py run --samples assets/text_samples.json

  # 指定服务对比
  python main.py run --samples assets/text_samples.json \\
    --text-services ugc_moderation_byllm,aigc_moderation_byllm

  # 人工标注
  python main.py annotate --file results/results_batch_xxx.json

  # 生成对齐报告
  python main.py report --file results/annotated_xxx.xlsx
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run 子命令
    run_parser = subparsers.add_parser("run", help="运行审核测试")
    run_parser.add_argument(
        "--samples", "-s", required=True, help="样本数据文件路径 (json/csv/xlsx)"
    )
    run_parser.add_argument(
        "--text-services", help="文本审核服务列表，逗号分隔"
    )
    run_parser.add_argument(
        "--image-services", help="图片审核服务列表，逗号分隔"
    )
    run_parser.add_argument(
        "--audio-services", help="音频审核服务列表，逗号分隔"
    )
    run_parser.add_argument(
        "--video-services", help="视频审核服务列表，逗号分隔"
    )
    run_parser.add_argument(
        "--concurrent", "-c", type=int, default=10, help="并发数 (默认10)"
    )
    run_parser.add_argument(
        "--format", "-f", choices=["xlsx", "csv", "json"], default="xlsx",
        help="输出格式 (默认xlsx)"
    )
    run_parser.set_defaults(func=cmd_run)

    # annotate 子命令
    annotate_parser = subparsers.add_parser("annotate", help="人工标注")
    annotate_parser.add_argument(
        "--file", "-f", required=True, help="待标注的结果文件"
    )
    annotate_parser.add_argument(
        "--annotator", "-a", help="标注人姓名"
    )
    annotate_parser.add_argument(
        "--export-only", action="store_true", help="仅导出已有标注"
    )
    annotate_parser.add_argument(
        "--format", choices=["xlsx", "csv", "json"], default="xlsx",
        help="导出格式"
    )
    annotate_parser.set_defaults(func=cmd_annotate)

    # report 子命令
    report_parser = subparsers.add_parser("report", help="生成统计报告")
    report_parser.add_argument(
        "--file", "-f", required=True, help="已标注的结果文件"
    )
    report_parser.add_argument(
        "--output", "-o", help="报告输出路径"
    )
    report_parser.add_argument(
        "--format", choices=["xlsx", "csv", "json"], default="xlsx",
        help="报告格式"
    )
    report_parser.set_defaults(func=cmd_report)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
