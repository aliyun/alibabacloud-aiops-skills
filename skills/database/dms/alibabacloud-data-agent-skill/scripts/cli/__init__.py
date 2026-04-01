"""CLI package for Data Agent unified command-line tool.

Author: Tinker
Created: 2026-03-04
"""

from cli.formatters import (
    _fmt_jupyter_cell,
    _fmt_task_finish,
    _fmt_insights,
    _fmt_table_summaries,
    _extract_json_objects,
    _format_data_event,
    _format_parsed_json,
    _fmt_plan_progress,
    _fmt_status_change,
    _fmt_output_conclusion,
    _fmt_recommended_questions,
    _SKIP_DATA_CATEGORIES,
)
from cli.streaming import (
    StreamState,
    _print_event,
    _stream_response,
    _finalize_stream,
    _is_user_confirmation_event,
)
from cli.cmd_db import cmd_db, _build_data_source, _db_attach, _db_batch, _db_single
from cli.cmd_ls import cmd_ls, _extract_list
from cli.cmd_file import cmd_file, _print_generated_files
from cli.cmd_attach import cmd_attach
from cli.parser import build_parser, main

__all__ = [
    # Formatters
    "_fmt_jupyter_cell",
    "_fmt_task_finish",
    "_fmt_insights",
    "_fmt_table_summaries",
    "_extract_json_objects",
    "_format_data_event",
    "_format_parsed_json",
    "_fmt_plan_progress",
    "_fmt_status_change",
    "_fmt_output_conclusion",
    "_fmt_recommended_questions",
    "_SKIP_DATA_CATEGORIES",
    # Streaming
    "StreamState",
    "_print_event",
    "_stream_response",
    "_finalize_stream",
    "_is_user_confirmation_event",
    # Commands
    "cmd_db",
    "_build_data_source",
    "_db_attach",
    "_db_batch",
    "_db_single",
    "cmd_ls",
    "_extract_list",
    "cmd_file",
    "_print_generated_files",
    "cmd_attach",
    # Parser / entry
    "build_parser",
    "main",
]
