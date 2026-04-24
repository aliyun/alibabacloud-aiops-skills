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
    python scripts/file_stream_query.py <fileId> "各部门人数分布"
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
)
from chat.chart_renderer import render_result_charts, HAS_MPL

from common.config_loader import get_skill_output_dir, get_image_output_dir

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

    def __init__(self, question: str):
        self.question = question
        self.ts = int(time.time())

        # 核心输出
        self.code_parts: List[str] = []
        self.result_data: Optional[dict] = None
        self.chart_images: List[str] = []
        self.reporter_parts: List[str] = []

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
        """流结束后的收尾：保存代码、渲染图表。"""
        if self.code_parts:
            full_code = "".join(self.code_parts).strip()
            if full_code:
                path = _save_code_file(full_code, self.ts)
                print(f"\n[代码] 分析代码已生成", flush=True)

        if self.result_data and HAS_MPL:
            charts = render_result_charts(
                self.result_data,
                get_image_output_dir(),
                prefix="chart",
            )
            if charts:
                self.chart_images.extend(charts)
                for img in charts:
                    print(f"\n[图表] 已生成 → {img}", flush=True)
                    print(f"![图表]({img})", flush=True)

    def get_result_summary(self) -> str:
        """返回简要结果摘要（仅输出元信息，避免与流式输出重复）。"""
        parts = []

        if self.result_data:
            data_list = self.result_data.get("dataList", [])
            parts.append(f"取数结果：共 {len(data_list)} 组数据")
            for i, ds in enumerate(data_list, 1):
                rows = ds.get("data", [])
                fields = [f.get("fieldName", "") for f in ds.get("fieldInfo", [])]
                parts.append(f"  数据集{i}: {len(rows)} 行, 字段={fields}")

        if self.chart_images:
            parts.append(f"生成图表 {len(self.chart_images)} 张：")
            for img in self.chart_images:
                parts.append(f"  - {img}")

        if self.error_msg:
            parts.append(f"错误：{self.error_msg}")

        return "\n".join(parts) if parts else "未获取到有效结果"

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
            print(f"\n\n[取数结果] 共 {len(data_list)} 组数据", flush=True)
            for i, ds in enumerate(data_list, 1):
                rows = ds.get("data", [])
                fields = [f.get("fieldName", "") for f in ds.get("fieldInfo", [])]
                print(f"  数据集{i}: {len(rows)} 行, 字段={fields}", flush=True)
        else:
            self.text_parts.append(str(data))
            print(f"\n[执行结果] {str(data)[:500]}", flush=True)

    # ----- reporter 事件：分析报告 -----

    def _on_reporter(self, data):
        if data:
            self.reporter_parts.append(str(data))
            print(str(data), end="", flush=True)

    # ----- plan / question / relatedInfo -----

    def _on_plan(self, data):
        self.plan_text = str(data)
        print(f"\n[分析规划]\n{data}", flush=True)

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
            print(f"\n[子问题] {data}", flush=True)

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
            print(f"\n[HTML 图表] 已保存 → {path}（仅供参考，图表由 result 数据生成）", flush=True)

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
            print(f"\n[图表数据] 共 {len(data_list)} 组数据", flush=True)
        else:
            print(f"\n[图表数据] {str(data)[:300]}", flush=True)

    def _on_unStructuredChart(self, data):
        if data:
            self.html_chart_index += 1
            path = _save_html_raw(str(data), self.question, self.html_chart_index)
            self.html_files.append(path)
            print(f"\n[非结构化图表] 已保存 → {path}", flush=True)

    # ----- SQL / 结论 -----

    def _on_sql(self, data):
        self.sql = str(data)
        print(f"\n[SQL]\n{data}", flush=True)

    def _on_python(self, data):
        if isinstance(data, dict):
            code = data.get("code", "")
            result = data.get("result", "")
            if code:
                self.code_parts.append(code)
            if result:
                print(f"\n[执行结果]\n{result}", flush=True)
        else:
            print(f"\n[Python] {data}", flush=True)

    def _on_conclusion(self, data):
        self.conclusion = str(data)
        print(f"\n[结论] {data}", flush=True)

    def _on_summary(self, data):
        self.summary = str(data)
        print(f"\n[数据解读] {data}", flush=True)

    # ----- 终止事件 -----

    def _on_trace(self, data):
        self.trace_id = str(data)
        print(f"[Trace] {self.trace_id}", flush=True)

    def _on_finish(self, data):
        self.finish_msg = str(data) if data else ""
        if self.finish_msg:
            print(f"\n[完成] {self.finish_msg}", flush=True)
        else:
            print("\n[完成]", flush=True)
        if self.trace_id:
            print(f"[Trace ID] {self.trace_id}（问题反馈时请提供此 ID）", flush=True)

    def _on_error(self, data):
        self.error_msg = str(data)
        print(f"\n[错误] {data}", flush=True)
        check_trial_expired(data if isinstance(data, dict) else str(data))

        if self.react_event_start_count >= 2:
            print(
                "\n============================================================\n"
                "⚠️ 数据文件解析失败\n"
                "当前问数的数据文件可能存在格式或内容问题，服务端多次重试执行均未成功。\n\n"
                "💡 建议排查\n"
                "请检查文件是否为标准的 Excel/CSV 格式，确认数据内容完整无损后重新上传。\n\n"
                "💬 如仍无法解决，点击下方链接，进入交流群联系 Quick BI 产品服务同学获取支持：\n"
                "https://at.umtrack.com/r4Tnme\n"
                "============================================================",
                flush=True,
            )

    def _on_check(self, data):
        print(f"\n[校验] {data}", flush=True)

    def _on_reject(self, data):
        print(f"\n[拒识] {data}", flush=True)

    # ----- 辅助事件 -----

    def _on_step(self, data):
        print(f"\n[步骤] {data}", flush=True)

    def _on_subStep(self, data):
        print(f"\n[子步骤] {data}", flush=True)

    def _on_rewrite(self, data):
        print(f"\n[问题改写] {data}", flush=True)

    def _on_python_error(self, data):
        print(f"\n[Python 错误] {data}", flush=True)

    def _on_olapResult(self, data):
        if isinstance(data, dict):
            print(f"\n[OLAP 结果] 行数={len(data.get('data', []))}", flush=True)

    def _on_onlineSearchResult(self, data):
        print(f"\n[联网搜索] {str(data)[:200]}", flush=True)

    def _on_actionThinking(self, data):
        print(f"\n[思考] {data}", flush=True)

    def _on_schedule(self, data):
        print(f"\n[调度] {data}", flush=True)

    def _on_selector(self, data):
        print(f"\n[选表] {data}", flush=True)

    def _on_systemSelector(self, data):
        print(f"\n[系统选表] {data}", flush=True)

    def _on_react(self, data):
        if data:
            print(f"\n[重试代码] {data}", flush=True)

    def _on_table_retrieve(self, data):
        print(f"\n[表召回] {data}", flush=True)

    def _on_schema_retrieve(self, data):
        print(f"\n[Schema 召回] {data}", flush=True)

    def _on_adaptation(self, data):
        print(f"\n[问题改写] {data}", flush=True)

    def _on_resource_info(self, data):
        print(f"\n[资源信息] {data}", flush=True)

    def _on_unknown(self, event_type: str, data):
        if data:
            print(f"\n[{event_type}] {str(data)[:200]}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="文件问数：基于 fileId 发起流式问数")
    parser.add_argument("file_id", help="步骤 1（upload_file.py）返回的 fileId")
    parser.add_argument("question", help="要问的问题")
    parser.add_argument("--verbose", action="store_true", help="启用详细调试输出")
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    args = parser.parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    try:
        config = read_config()
        user_id = require_user_id(config)

        print(f"[文件问数] fileId={args.file_id}", flush=True)
        print(f"[文件问数] userId={user_id}", flush=True)
        print(f"[文件问数] 问题: {args.question}", flush=True)
        print("=" * 60, flush=True)

        body = {
            "fileId": args.file_id,
            "userId": user_id,
            "userQuestion": args.question,
            "runningBySkill": True,
        }

        session = StreamSession(args.question)

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
        print(f"\n[错误] {e}", flush=True)
        check_trial_expired(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
