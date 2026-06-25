# -*- coding: utf-8 -*-
"""
文件问数流式查询脚本（步骤 2）。

接收步骤 1（upload_file.py）返回的 fileId，发起流式问数，
实时解析 SSE 事件流并输出结果。

核心策略：
  - code  事件 → 拼接为完整 Python 代码并保存
  - result 事件 → 解析结构化数据，用 matplotlib 渲染图表 PNG
  - reporter 事件 → 拼接为分析报告文本
  - html 事件 → 仅保存原始 HTML（不截图）

用法：
    python3 scripts/file_stream_query.py <fileId> "各部门人数分布"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import (
    read_config,
    require_user_id,
    request_openapi_stream,
    parse_sse_event,
    check_trial_expired,
    check_known_error_code,
)
from chat.chart_renderer import render_result_charts, HAS_MPL, _infer_chart_type as infer_chart_type_from_renderer
from common.config_loader import get_skill_output_dir, get_image_output_dir
from common.messages import msg, set_locale

OUTPUT_DIR = None  # 已废弃，下方函数直接调用 get_skill_output_dir()
STREAM_URI = "/openapi/v2/smartq/queryByQuestionStreamByFile"

TERMINAL_EVENTS = {"finish", "error", "check"}
SKIP_EVENTS = {"heartbeat", "timestamp", "locale", "feedback", "message", "token"}


def _save_code_file(code: str, ts: int) -> str:
    """将拼接完成的 Python 代码保存到 output/ 目录。"""
    output_dir = get_skill_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"analysis_code_{ts}.py"
    path.write_text(code, encoding="utf-8")
    return str(path)


def _save_html_raw(html_content: str, question: str, index: int) -> str:
    """将原始 HTML 保存到 output/（不做截图）。"""
    output_dir = get_skill_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    filepath = output_dir / f"chart_html_{ts}_{index}.html"
    if not (html_content.strip().lower().startswith("<!doctype")
            or html_content.strip().lower().startswith("<html")):
        html_content = (
            '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/></head>'
            f"<body>{html_content}</body></html>"
        )
    filepath.write_text(html_content, encoding="utf-8")
    return str(filepath)


# ---------------------------------------------------------------------------
# 事件流处理
# ---------------------------------------------------------------------------

class StreamSession:
    """管理一次文件问数的流式会话状态。"""

    def __init__(self, question: str, file_id: str = ""):
        self.question = question
        self.file_id = file_id
        self.ts = int(time.time())

        # 核心输出
        self.code_parts: List[str] = []
        self.result_data: Optional[dict] = None
        self.chart_images: List[str] = []
        self.reporter_parts: List[str] = []
        self.inferred_chart_types: List[str] = []  # 存储推断的图表类型

        # 辅助
        self.text_parts: List[str] = []
        self.reasoning_parts: List[str] = []
        self.answer_parts: List[str] = []
        self.plan_text = ""
        self.related_info_parts: List[str] = []
        self.html_files: List[str] = []
        self.html_chart_index = 0
        self.sql = ""
        self.conclusion = ""
        self.summary = ""
        self.finish_msg = ""
        self.error_msg = ""
        self.react_event_start_count = 0
        self.trace_id = ""

    # ----- 公共方法 -----

    def handle_event(self, event: Dict[str, Any]):
        """处理单个 SSE 事件。"""
        event_type = event.get("type", "")
        data = event.get("data", "")
        sub_type = event.get("subType", "")

        if event_type in SKIP_EVENTS:
            return

        if event_type == "react" and sub_type == "EVENT_START":
            self.react_event_start_count += 1

        handler = getattr(self, f"_on_{event_type}", None)
        if handler:
            handler(data)
        else:
            self._on_unknown(event_type, data)

    def finalize(self):
        """流结束后的收尾：保存代码、渲染图表、保存JSON结果。"""
        if self.code_parts:
            full_code = "".join(self.code_parts).strip()
            if full_code:
                path = _save_code_file(full_code, self.ts)
                print(msg("file_query_code_generated"), flush=True)

        # 统一推断图表类型（复用 chart_renderer 的逻辑）
        if self.result_data:
            self._infer_all_chart_types()

        if self.result_data and HAS_MPL:
            charts = render_result_charts(
                self.result_data,
                get_image_output_dir(),
                prefix="chart",
            )
            if charts:
                self.chart_images.extend(charts)
                for img in charts:
                    print(msg("file_query_chart_generated", path=img), flush=True)
                    print(msg("file_query_chart_link", title=msg("smartq_chart_default_title"), path=img), flush=True)

        # 保存问数结果为 JSON
        self._save_json_result()

    def get_result_summary(self) -> str:
        """返回简要结果摘要（仅输出元信息，避免与流式输出重复）。"""
        parts = []

        if self.result_data:
            data_list = self.result_data.get("dataList", [])
            parts.append(msg("file_query_result_summary_data", count=len(data_list)))
            for i, ds in enumerate(data_list, 1):
                rows = ds.get("data", [])
                fields = [f.get("fieldName", "") for f in ds.get("fieldInfo", [])]
                parts.append(msg("file_query_dataset_row", idx=i, rows=len(rows), fields=fields))

        if self.chart_images:
            parts.append(msg("file_query_result_summary_chart", count=len(self.chart_images)))
            for img in self.chart_images:
                parts.append(f"  - {img}")

        if self.error_msg:
            parts.append(msg("file_query_result_summary_error", error=self.error_msg))

        return "\n".join(parts) if parts else msg("file_query_no_valid_result")

    def _infer_all_chart_types(self):
        """统一推断所有图表类型（复用 chart_renderer 的逻辑）。"""
        if not self.result_data:
            return

        data_list = self.result_data.get("dataList", [])
        self.inferred_chart_types = []

        for dataset in data_list:
            field_info = dataset.get("fieldInfo", [])
            chart_type_hint = dataset.get("chartType", "")

            # 提取 dimensions 和 metrics
            dims = [f for f in field_info if f.get("role") == "dimension"]
            metrics = [f for f in field_info if f.get("role") == "metric"]

            # 复用 chart_renderer 的推断逻辑
            if not metrics:
                chart_type = "table"
            else:
                chart_type = infer_chart_type_from_renderer(
                    dims, metrics, chart_type_hint)

            self.inferred_chart_types.append(chart_type)

    def _save_json_result(self):
        """处理问数结果并保存为 JSON 文件。"""
        if not self.result_data:
            return

        data_list = self.result_data.get("dataList", [])
        if not data_list:
            return

        # 构建 charts 数组
        charts = []
        for idx, ds in enumerate(data_list):
            rows = ds.get("data", [])
            field_info = ds.get("fieldInfo", [])
            title = ds.get("title", "")

            # 转换数据格式：从数组格式转为字典格式
            data_rows = []
            for row in rows:
                if isinstance(row, list):
                    # 数组格式：按 fieldInfo 顺序映射
                    row_dict = {}
                    for i, field in enumerate(field_info):
                        field_name = field.get("fieldName", f"field_{i}")
                        row_dict[field_name] = row[i] if i < len(row) else ""
                    data_rows.append(row_dict)
                elif isinstance(row, dict):
                    # 已经是字典格式
                    data_rows.append(row)

            # 使用已推断的图表类型
            chart_type = self.inferred_chart_types[idx] if idx < len(
                self.inferred_chart_types) else "table"

            chart_entry = {
                "title": title if title else self.question,
                "chartType": chart_type,
                "data": data_rows,
                "fieldInfo": field_info,
                "logicBlock": {
                    "pythonCode": "".join(self.code_parts).strip() if self.code_parts else ""
                }
            }
            charts.append(chart_entry)

        # 构建最终结果
        result_data = {
            "question": self.question,
            "cube_id": self.file_id,  # 文件问数使用 fileId
            "charts": charts
        }

        # 保存查询结果
        output_dir = get_skill_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"query_result_{int(time.time())}.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            print(msg("smartq_query_saved", path=output_file), flush=True)
        except Exception as e:
            print(msg("smartq_query_save_failed", exc=e), flush=True)

    # ----- code 事件：拼接 Python 代码 -----

    def _on_code(self, data):
        if data:
            self.code_parts.append(str(data))

    # ----- result 事件：结构化取数结果 + 图表渲染 -----

    def _on_result(self, data):
        parsed = data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                parsed = None

        if isinstance(parsed, dict) and "dataList" in parsed:
            self.result_data = parsed
            data_list = parsed.get("dataList", [])
            print(msg("file_query_result_groups", count=len(data_list)), flush=True)
            for i, ds in enumerate(data_list, 1):
                rows = ds.get("data", [])
                fields = [f.get("fieldName", "") for f in ds.get("fieldInfo", [])]
                print(msg("file_query_dataset_row", idx=i, rows=len(rows), fields=fields), flush=True)
        else:
            self.text_parts.append(str(data))
            print(msg("file_query_exec_result", data=str(data)[:500]), flush=True)

    # ----- reporter 事件：分析报告 -----

    def _on_reporter(self, data):
        if data:
            self.reporter_parts.append(str(data))
            print(str(data), end="", flush=True)

    # ----- plan / question / relatedInfo -----

    def _on_plan(self, data):
        self.plan_text = str(data)
        print(msg("file_query_plan", data=data), flush=True)

    def _on_question(self, data):
        parsed = data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                parsed = data
        if isinstance(parsed, dict):
            title = parsed.get("title", "")
            desc = parsed.get("desc", "")
            print(f"\n[{title}]\n{desc}", flush=True)
        else:
            print(msg("file_query_sub_question", data=data), flush=True)

    def _on_relatedInfo(self, data):
        if data:
            self.related_info_parts.append(str(data))

    # ----- text / reasoning / answer -----

    def _on_text(self, data):
        if data:
            self.text_parts.append(str(data))
            print(str(data), end="", flush=True)

    def _on_reasoning(self, data):
        if data:
            self.reasoning_parts.append(str(data))
            print(str(data), end="", flush=True)

    def _on_answer(self, data):
        if data:
            self.answer_parts.append(str(data))
            print(str(data), end="", flush=True)

    # ----- html 事件（仅保存，不截图） -----

    def _on_html(self, data):
        if data:
            self.html_chart_index += 1
            path = _save_html_raw(str(data), self.question, self.html_chart_index)
            self.html_files.append(path)
            print(msg("file_query_html_chart", path=path), flush=True)

    def _on_html_result(self, data):
        parsed = data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                parsed = data
        if isinstance(parsed, dict) and "dataList" in parsed:
            self.result_data = parsed
            data_list = parsed.get("dataList", [])
            print(msg("file_query_chart_data", count=len(data_list)), flush=True)
        else:
            print(msg("file_query_chart_data_raw", data=str(data)[:300]), flush=True)

    def _on_unStructuredChart(self, data):
        if data:
            self.html_chart_index += 1
            path = _save_html_raw(str(data), self.question, self.html_chart_index)
            self.html_files.append(path)
            print(msg("file_query_unstructured_chart", path=path), flush=True)

    # ----- SQL / 结论 -----

    def _on_sql(self, data):
        self.sql = str(data)
        print(msg("file_query_sql_block", data=data), flush=True)

    def _on_python(self, data):
        if isinstance(data, dict):
            code = data.get("code", "")
            result = data.get("result", "")
            if code:
                self.code_parts.append(code)
            if result:
                print(msg("file_query_exec_result_block", data=result), flush=True)
        else:
            print(msg("file_query_python", data=data), flush=True)

    def _on_conclusion(self, data):
        self.conclusion = str(data)
        print(msg("file_query_conclusion", data=data), flush=True)

    def _on_summary(self, data):
        self.summary = str(data)
        print(msg("file_query_summary", data=data), flush=True)

    # ----- 终止事件 -----

    def _on_trace(self, data):
        self.trace_id = str(data)
        print(f"[Trace] {self.trace_id}", flush=True)

    def _on_finish(self, data):
        self.finish_msg = str(data) if data else ""
        if self.finish_msg:
            print(msg("file_query_finish", data=self.finish_msg), flush=True)
        else:
            print(msg("file_query_finish_empty"), flush=True)
        if self.trace_id:
            print(msg("smartq_trace_id", trace_id=self.trace_id), flush=True)

    def _on_error(self, data):
        self.error_msg = str(data)
        print(msg("file_query_error", data=data), flush=True)
        check_known_error_code(data if isinstance(data, dict) else str(data))

        if self.react_event_start_count >= 2:
            print(msg("file_query_file_parse_error"), flush=True)

    def _on_check(self, data):
        print(msg("file_query_check", data=data), flush=True)

    def _on_reject(self, data):
        print(msg("file_query_reject", data=data), flush=True)

    # ----- 辅助事件 -----

    def _on_step(self, data):
        print(msg("file_query_step", data=data), flush=True)

    def _on_subStep(self, data):
        print(msg("file_query_sub_step", data=data), flush=True)

    def _on_rewrite(self, data):
        print(msg("file_query_rewrite", data=data), flush=True)

    def _on_python_error(self, data):
        print(msg("file_query_python_error", data=data), flush=True)

    def _on_olapResult(self, data):
        if isinstance(data, dict):
            print(msg("file_query_olap_result", rows=len(data.get('data', []))), flush=True)

    def _on_onlineSearchResult(self, data):
        print(msg("file_query_online_search", data=str(data)[:200]), flush=True)

    def _on_actionThinking(self, data):
        print(msg("file_query_thinking", data=data), flush=True)

    def _on_schedule(self, data):
        print(msg("file_query_schedule", data=data), flush=True)

    def _on_selector(self, data):
        print(msg("file_query_selector", data=data), flush=True)

    def _on_systemSelector(self, data):
        print(msg("file_query_system_selector", data=data), flush=True)

    def _on_react(self, data):
        if data:
            print(msg("file_query_react", data=data), flush=True)

    def _on_table_retrieve(self, data):
        print(msg("file_query_table_retrieve", data=data), flush=True)

    def _on_schema_retrieve(self, data):
        print(msg("file_query_schema_retrieve", data=data), flush=True)

    def _on_adaptation(self, data):
        print(msg("file_query_rewrite", data=data), flush=True)

    def _on_resource_info(self, data):
        print(msg("file_query_resource_info", data=data), flush=True)

    def _on_unknown(self, event_type: str, data):
        if data:
            print(f"\n[{event_type}] {str(data)[:200]}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="文件问数：基于 fileId 发起流式问数")
    parser.add_argument("file_id", help="步骤 1（upload_file.py）返回的 fileId")
    parser.add_argument("question", help="要问的问题")
    parser.add_argument("--locale", required=True, choices=["zh_CN", "en_US"], help="语言环境: zh_CN(简体中文) 或 en_US(英文)")
    parser.add_argument("--verbose", action="store_true", help="启用详细调试输出")
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    args = parser.parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    set_locale(args.locale)

    try:
        config = read_config()
        user_id = require_user_id(config)

        print(msg("file_query_header", file_id=args.file_id), flush=True)
        print(msg("file_query_userid", user_id=user_id), flush=True)
        print(msg("file_query_question", question=args.question), flush=True)
        print(msg("file_query_locale", locale=args.locale), flush=True)
        print("=" * 60, flush=True)

        body = {
            "fileId": args.file_id,
            "userId": user_id,
            "userQuestion": args.question,
            "runningBySkill": True,
            "locale": args.locale,
        }

        session = StreamSession(args.question, args.file_id)

        for raw_event in request_openapi_stream(STREAM_URI, json_body=body, config=config):
            if args.verbose:
                print(f"\n--- RAW SSE ---\n{raw_event}\n--- END SSE ---", flush=True)
            event = parse_sse_event(raw_event)
            if not event:
                continue
            if args.verbose:
                print(f"[PARSED] type={event.get('type', '')}, data={json.dumps(event, ensure_ascii=False, default=str)[:500]}", flush=True)
            session.handle_event(event)
            event_type = event.get("type", "")
            if event_type in TERMINAL_EVENTS:
                break

        session.finalize()

        print("\n" + "=" * 60, flush=True)
        print(session.get_result_summary(), flush=True)

    except Exception as e:
        print(msg("file_query_error", data=e), flush=True)
        check_known_error_code(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
