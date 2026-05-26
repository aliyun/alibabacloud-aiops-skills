"""
统计报告生成器 - 生成测试结果的多维度统计分析报告
包含：按服务对比、按模态统计、按风险等级分布、标注对齐率分析
"""
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import OUTPUT_DIR
from models import AnnotationLabel, TestBatchResult

console = Console()


class Reporter:
    """统计报告生成器"""

    def __init__(self, batch_result: Optional[TestBatchResult] = None):
        self.batch_result = batch_result
        self.annotated_results: List[Dict] = []

    def load_annotated_results(self, file_path: str):
        """加载已标注的结果数据"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                self.annotated_results = json.load(f)
        elif ext in (".xlsx", ".xls"):
            import pandas as pd
            df = pd.read_excel(file_path)
            self.annotated_results = df.to_dict("records")
        elif ext == ".csv":
            import pandas as pd
            df = pd.read_csv(file_path)
            self.annotated_results = df.to_dict("records")

    def generate_summary_report(self) -> str:
        """生成汇总报告（控制台输出 + 返回文本）"""
        if not self.batch_result:
            console.print("[red]无测试结果数据[/red]")
            return ""

        br = self.batch_result
        report_lines = []

        # ===== 总体概览 =====
        console.print(Panel("[bold]测试批次汇总报告[/bold]", style="blue"))

        overview_table = Table(title="总体概览", show_lines=True)
        overview_table.add_column("指标", style="bold")
        overview_table.add_column("值", justify="right")

        overview_table.add_row("批次ID", br.batch_id)
        overview_table.add_row("开始时间", br.start_time)
        overview_table.add_row("结束时间", br.end_time)
        overview_table.add_row("总样本数", str(br.total_samples))
        overview_table.add_row("总请求数", str(br.total_requests))
        overview_table.add_row("成功率", f"{br.success_count}/{br.total_requests} ({br.success_count/max(br.total_requests,1)*100:.1f}%)")
        overview_table.add_row("失败数", str(br.failure_count))

        console.print(overview_table)
        report_lines.append(f"批次: {br.batch_id}")
        report_lines.append(f"总请求: {br.total_requests}, 成功: {br.success_count}, 失败: {br.failure_count}")

        # ===== 按服务统计 =====
        if br.service_stats:
            service_table = Table(title="按审核服务统计", show_lines=True)
            service_table.add_column("服务", style="bold")
            service_table.add_column("总数", justify="right")
            service_table.add_column("成功", justify="right")
            service_table.add_column("High", justify="right", style="red")
            service_table.add_column("Medium", justify="right", style="yellow")
            service_table.add_column("Low", justify="right", style="blue")
            service_table.add_column("None", justify="right", style="green")

            for service, stats in br.service_stats.items():
                service_table.add_row(
                    service,
                    str(stats.get("total", 0)),
                    str(stats.get("success", 0)),
                    str(stats.get("high", 0)),
                    str(stats.get("medium", 0)),
                    str(stats.get("low", 0)),
                    str(stats.get("none", 0)),
                )

            console.print(service_table)

        # ===== 按模态统计 =====
        if br.modality_stats:
            modality_table = Table(title="按内容模态统计", show_lines=True)
            modality_table.add_column("模态", style="bold")
            modality_table.add_column("总数", justify="right")
            modality_table.add_column("成功", justify="right")
            modality_table.add_column("High", justify="right", style="red")
            modality_table.add_column("Medium", justify="right", style="yellow")
            modality_table.add_column("Low", justify="right", style="blue")
            modality_table.add_column("None", justify="right", style="green")

            for mod, stats in br.modality_stats.items():
                modality_table.add_row(
                    mod,
                    str(stats.get("total", 0)),
                    str(stats.get("success", 0)),
                    str(stats.get("high", 0)),
                    str(stats.get("medium", 0)),
                    str(stats.get("low", 0)),
                    str(stats.get("none", 0)),
                )

            console.print(modality_table)

        # ===== 风险等级分布 =====
        if br.risk_level_stats:
            risk_table = Table(title="风险等级分布", show_lines=True)
            risk_table.add_column("等级", style="bold")
            risk_table.add_column("数量", justify="right")
            risk_table.add_column("占比", justify="right")

            total = sum(br.risk_level_stats.values())
            for level in ["high", "medium", "low", "none", "unknown"]:
                count = br.risk_level_stats.get(level, 0)
                if count > 0:
                    pct = count / max(total, 1) * 100
                    risk_table.add_row(level, str(count), f"{pct:.1f}%")

            console.print(risk_table)

        return "\n".join(report_lines)

    def generate_alignment_report(self) -> Dict:
        """
        生成标注对齐报告 - 分析人工标注与机器审核的一致性
        计算：准确率、误判率、漏判率
        """
        if not self.annotated_results:
            console.print("[yellow]无标注数据，请先加载标注结果[/yellow]")
            return {}

        # 按服务分组统计
        service_alignment: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"correct": 0, "false_positive": 0, "false_negative": 0, "uncertain": 0, "total": 0}
        )

        # 按模态分组统计
        modality_alignment: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"correct": 0, "false_positive": 0, "false_negative": 0, "uncertain": 0, "total": 0}
        )

        # 按类别分组统计
        category_alignment: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"correct": 0, "false_positive": 0, "false_negative": 0, "uncertain": 0, "total": 0}
        )

        for record in self.annotated_results:
            annotation = record.get("annotation", "pending")
            if annotation == "pending":
                continue

            service = record.get("service", "unknown")
            modality = record.get("modality", "unknown")
            category = record.get("category", "unknown")

            service_alignment[service]["total"] += 1
            service_alignment[service][annotation] += 1

            modality_alignment[modality]["total"] += 1
            modality_alignment[modality][annotation] += 1

            category_alignment[category]["total"] += 1
            category_alignment[category][annotation] += 1

        # 输出对齐报告
        console.print(Panel("[bold]标注对齐分析报告[/bold]", style="magenta"))

        # 按服务对齐率
        alignment_table = Table(title="按服务 - 标注对齐率", show_lines=True)
        alignment_table.add_column("服务", style="bold")
        alignment_table.add_column("已标注", justify="right")
        alignment_table.add_column("准确率", justify="right", style="green")
        alignment_table.add_column("误判率", justify="right", style="red")
        alignment_table.add_column("漏判率", justify="right", style="yellow")

        for service, stats in service_alignment.items():
            total = stats["total"]
            if total == 0:
                continue
            accuracy = stats["correct"] / total * 100
            fp_rate = stats["false_positive"] / total * 100
            fn_rate = stats["false_negative"] / total * 100

            alignment_table.add_row(
                service,
                str(total),
                f"{accuracy:.1f}%",
                f"{fp_rate:.1f}%",
                f"{fn_rate:.1f}%",
            )

        console.print(alignment_table)

        # 按模态对齐率
        if len(modality_alignment) > 1:
            mod_table = Table(title="按模态 - 标注对齐率", show_lines=True)
            mod_table.add_column("模态", style="bold")
            mod_table.add_column("已标注", justify="right")
            mod_table.add_column("准确率", justify="right", style="green")
            mod_table.add_column("误判率", justify="right", style="red")
            mod_table.add_column("漏判率", justify="right", style="yellow")

            for modality, stats in modality_alignment.items():
                total = stats["total"]
                if total == 0:
                    continue
                accuracy = stats["correct"] / total * 100
                fp_rate = stats["false_positive"] / total * 100
                fn_rate = stats["false_negative"] / total * 100

                mod_table.add_row(
                    modality, str(total),
                    f"{accuracy:.1f}%", f"{fp_rate:.1f}%", f"{fn_rate:.1f}%",
                )

            console.print(mod_table)

        return {
            "service_alignment": dict(service_alignment),
            "modality_alignment": dict(modality_alignment),
            "category_alignment": dict(category_alignment),
        }

    def export_report(self, output_path: str = "", format: str = "xlsx") -> str:
        """导出完整报告到文件"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not output_path:
            output_path = os.path.join(OUTPUT_DIR, f"report_{timestamp}.{format}")

        if format == "xlsx":
            self._export_xlsx(output_path)
        elif format == "json":
            self._export_json(output_path)
        else:
            self._export_csv(output_path)

        console.print(f"[green]报告已导出: {output_path}[/green]")
        return output_path

    def _export_xlsx(self, output_path: str):
        """导出为多Sheet的Excel报告"""
        import pandas as pd

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Sheet1: 详细结果（含requestId）
            if self.batch_result:
                detail_data = []
                for r in self.batch_result.results:
                    detail_data.append({
                        "样本ID": r.sample_id,
                        "RequestID": r.request_id,
                        "审核服务": r.service,
                        "模态": r.modality.value,
                        "风险等级": r.risk_level,
                        "风险标签": "|".join(r.labels),
                        "置信度": json.dumps(r.confidence, ensure_ascii=False),
                        "原因": r.reason,
                        "耗时(ms)": round(r.latency_ms, 2),
                        "成功": r.success,
                        "错误码": r.error_code,
                        "错误信息": r.error_message,
                        "请求时间": r.request_time,
                        "响应时间": r.response_time,
                        "标注结果": r.annotation,
                        "标注备注": r.annotation_note,
                        "标注人": r.annotated_by,
                        "标注时间": r.annotated_at,
                    })
                if detail_data:
                    pd.DataFrame(detail_data).to_excel(
                        writer, sheet_name="详细结果", index=False
                    )

            # Sheet2: 按服务统计
            if self.batch_result and self.batch_result.service_stats:
                service_data = []
                for service, stats in self.batch_result.service_stats.items():
                    service_data.append({"服务": service, **stats})
                if service_data:
                    pd.DataFrame(service_data).to_excel(
                        writer, sheet_name="服务统计", index=False
                    )

            # Sheet3: 标注对齐分析
            if self.annotated_results:
                annotated_df = pd.DataFrame(self.annotated_results)
                annotated_df.to_excel(
                    writer, sheet_name="标注明细", index=False
                )

    def _export_json(self, output_path: str):
        """导出为JSON报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "batch_id": self.batch_result.batch_id if self.batch_result else "",
            "summary": {
                "total_samples": self.batch_result.total_samples if self.batch_result else 0,
                "total_requests": self.batch_result.total_requests if self.batch_result else 0,
                "success_count": self.batch_result.success_count if self.batch_result else 0,
                "failure_count": self.batch_result.failure_count if self.batch_result else 0,
            },
            "service_stats": self.batch_result.service_stats if self.batch_result else {},
            "modality_stats": self.batch_result.modality_stats if self.batch_result else {},
            "risk_level_stats": self.batch_result.risk_level_stats if self.batch_result else {},
            "results": [],
        }

        if self.batch_result:
            for r in self.batch_result.results:
                report["results"].append({
                    "sample_id": r.sample_id,
                    "request_id": r.request_id,
                    "service": r.service,
                    "modality": r.modality.value,
                    "risk_level": r.risk_level,
                    "labels": r.labels,
                    "confidence": r.confidence,
                    "reason": r.reason,
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "annotation": r.annotation,
                    "annotation_note": r.annotation_note,
                })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def _export_csv(self, output_path: str):
        """导出为CSV"""
        import pandas as pd

        if self.batch_result:
            data = []
            for r in self.batch_result.results:
                data.append({
                    "sample_id": r.sample_id,
                    "request_id": r.request_id,
                    "service": r.service,
                    "modality": r.modality.value,
                    "risk_level": r.risk_level,
                    "labels": "|".join(r.labels),
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "annotation": r.annotation,
                })
            pd.DataFrame(data).to_csv(output_path, index=False, encoding="utf-8-sig")
