"""
人工标注工具 - 提供命令行交互式标注界面和批量标注能力
支持：逐条标注、批量标注、标注进度保存/恢复、标注结果导出
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from config import ANNOTATION_LABELS, OUTPUT_DIR
from models import AnnotationLabel, ModerationResult, TestBatchResult

console = Console()


class Annotator:
    """人工标注工具"""

    def __init__(self, results_file: str = ""):
        self.results: List[Dict] = []
        self.results_file = results_file
        self.annotator_name = ""

    def load_results(self, file_path: str) -> int:
        """从结果文件加载待标注数据"""
        self.results_file = file_path
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.results = data if isinstance(data, list) else data.get("results", [])
        elif ext in (".xlsx", ".xls"):
            import pandas as pd
            df = pd.read_excel(file_path)
            self.results = df.to_dict("records")
        elif ext == ".csv":
            import pandas as pd
            df = pd.read_csv(file_path)
            self.results = df.to_dict("records")
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

        return len(self.results)

    def load_from_batch_result(self, batch_result: TestBatchResult):
        """从TestBatchResult对象加载"""
        self.results = []
        for r in batch_result.results:
            self.results.append({
                "sample_id": r.sample_id,
                "service": r.service,
                "request_id": r.request_id,
                "modality": r.modality.value,
                "content_preview": "",  # 内容预览需从样本数据获取
                "risk_level": r.risk_level,
                "labels": "|".join(r.labels),
                "reason": r.reason,
                "latency_ms": r.latency_ms,
                "success": r.success,
                "annotation": r.annotation,
                "annotation_note": r.annotation_note,
                "annotated_by": r.annotated_by,
                "annotated_at": r.annotated_at,
            })

    def start_interactive_annotation(self, annotator_name: str = ""):
        """启动交互式标注流程"""
        self.annotator_name = annotator_name or Prompt.ask("请输入标注人姓名")

        # 过滤出待标注的条目
        pending = [
            (i, r) for i, r in enumerate(self.results)
            if r.get("annotation", "pending") == "pending"
        ]

        if not pending:
            console.print("[green]所有条目已完成标注！[/green]")
            return

        console.print(
            f"\n[bold]待标注条目: {len(pending)} / {len(self.results)}[/bold]\n"
        )
        console.print(
            "标注选项: [green]c[/green]=正确  "
            "[red]fp[/red]=误判  [yellow]fn[/yellow]=漏判  "
            "[blue]u[/blue]=不确定  [dim]s[/dim]=跳过  "
            "[dim]q[/dim]=退出并保存\n"
        )

        annotated_count = 0
        for idx, (original_idx, record) in enumerate(pending):
            self._display_record(record, idx + 1, len(pending))

            choice = Prompt.ask(
                "标注",
                choices=["c", "fp", "fn", "u", "s", "q"],
                default="s",
            )

            if choice == "q":
                console.print("[yellow]退出标注，已保存进度。[/yellow]")
                break
            elif choice == "s":
                continue
            else:
                label_map = {
                    "c": AnnotationLabel.CORRECT.value,
                    "fp": AnnotationLabel.FALSE_POSITIVE.value,
                    "fn": AnnotationLabel.FALSE_NEGATIVE.value,
                    "u": AnnotationLabel.UNCERTAIN.value,
                }
                annotation = label_map[choice]

                # 可选备注
                note = ""
                if choice in ("fp", "fn", "u"):
                    note = Prompt.ask("备注（可选，回车跳过）", default="")

                self.results[original_idx]["annotation"] = annotation
                self.results[original_idx]["annotation_note"] = note
                self.results[original_idx]["annotated_by"] = self.annotator_name
                self.results[original_idx]["annotated_at"] = datetime.now().isoformat()
                annotated_count += 1

            # 每10条自动保存
            if annotated_count > 0 and annotated_count % 10 == 0:
                self._auto_save()
                console.print("[dim]（进度已自动保存）[/dim]")

        # 最终保存
        self._auto_save()
        console.print(
            f"\n[bold green]本次标注完成: {annotated_count} 条[/bold green]"
        )

    def batch_annotate(
        self,
        indices: List[int],
        annotation: str,
        annotator_name: str,
        note: str = "",
    ):
        """批量标注指定条目"""
        for idx in indices:
            if 0 <= idx < len(self.results):
                self.results[idx]["annotation"] = annotation
                self.results[idx]["annotation_note"] = note
                self.results[idx]["annotated_by"] = annotator_name
                self.results[idx]["annotated_at"] = datetime.now().isoformat()

    def get_annotation_progress(self) -> Dict[str, int]:
        """获取标注进度"""
        progress = {
            "total": len(self.results),
            "pending": 0,
            "correct": 0,
            "false_positive": 0,
            "false_negative": 0,
            "uncertain": 0,
        }
        for r in self.results:
            ann = r.get("annotation", "pending")
            if ann in progress:
                progress[ann] += 1
            else:
                progress["pending"] += 1
        return progress

    def export_annotated(self, output_path: str = "", format: str = "xlsx"):
        """导出标注结果"""
        if not output_path:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if format == "xlsx":
                output_path = os.path.join(
                    OUTPUT_DIR, f"annotated_{timestamp}.xlsx"
                )
            elif format == "csv":
                output_path = os.path.join(
                    OUTPUT_DIR, f"annotated_{timestamp}.csv"
                )
            else:
                output_path = os.path.join(
                    OUTPUT_DIR, f"annotated_{timestamp}.json"
                )

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
        else:
            import pandas as pd
            df = pd.DataFrame(self.results)
            if format == "xlsx":
                df.to_excel(output_path, index=False)
            else:
                df.to_csv(output_path, index=False, encoding="utf-8-sig")

        console.print(f"[green]标注结果已导出: {output_path}[/green]")
        return output_path

    def _display_record(self, record: Dict, current: int, total: int):
        """展示单条记录供标注"""
        content_preview = str(record.get("content_preview", record.get("content", "")))
        if len(content_preview) > 200:
            content_preview = content_preview[:200] + "..."

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("字段", style="bold")
        table.add_column("值")

        table.add_row("样本ID", str(record.get("sample_id", "")))
        table.add_row("RequestID", str(record.get("request_id", "")))
        table.add_row("服务", str(record.get("service", "")))
        table.add_row("模态", str(record.get("modality", "")))
        table.add_row("风险等级", self._colorize_risk(record.get("risk_level", "")))
        table.add_row("风险标签", str(record.get("labels", "")))
        table.add_row("审核原因", str(record.get("reason", "")))
        table.add_row("内容", content_preview)

        panel = Panel(
            table,
            title=f"[bold]标注 [{current}/{total}][/bold]",
            border_style="blue",
        )
        console.print(panel)

    @staticmethod
    def _colorize_risk(risk_level: str) -> str:
        """风险等级着色"""
        colors = {
            "high": "[bold red]high[/bold red]",
            "medium": "[yellow]medium[/yellow]",
            "low": "[blue]low[/blue]",
            "none": "[green]none[/green]",
        }
        return colors.get(risk_level, risk_level)

    def _auto_save(self):
        """自动保存当前标注进度"""
        save_path = self.results_file or os.path.join(
            OUTPUT_DIR, "annotation_progress.json"
        )
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

        # 保存为JSON（通用格式）
        progress_file = os.path.splitext(save_path)[0] + "_progress.json"
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
