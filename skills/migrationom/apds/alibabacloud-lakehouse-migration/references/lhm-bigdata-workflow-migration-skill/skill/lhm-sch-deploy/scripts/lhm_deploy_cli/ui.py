"""终端展示辅助：颜色、状态映射、日志输出。"""

from __future__ import annotations

import sys

# ANSI 颜色（仅 TTY 时启用）
_IS_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _IS_TTY else text


def GREEN(t: str) -> str:
    return _c("32", t)


def YELLOW(t: str) -> str:
    return _c("33", t)


def RED(t: str) -> str:
    return _c("31", t)


def CYAN(t: str) -> str:
    return _c("36", t)


def DIM(t: str) -> str:
    return _c("2", t)


# 状态 → 中文映射
STATUS_CN = {
    "ALL_SUCCESS": ("✅", "全部成功"),
    "SUCCESS": ("✅", "成功"),
    "RUNNING": ("🔄", "进行中"),
    "SUBMITTING": ("📤", "提交中"),
    "WAITING": ("⏳", "等待中"),
    "INIT": ("⏳", "初始化"),
    "PARTIAL_SUCCESS": ("⚠️", "部分成功"),
    "FAILED": ("❌", "失败"),
    "CANCELLED": ("🚫", "已取消"),
    "TERMINATED": ("🚫", "已终止"),
}

# 终止状态集合
TERMINAL_STATES = {
    "ALL_SUCCESS", "SUCCESS", "FAILED", "CANCELLED",
    "PARTIAL_SUCCESS", "TERMINATED",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def banner(msg: str) -> None:
    line = "━" * 40
    log(f"\n{CYAN(line)}")
    log(f"{CYAN('  ' + msg)}")
    log(f"{CYAN(line)}")


def fmt_status(status: str) -> str:
    icon, text = STATUS_CN.get(status, ("❓", status))
    return f"{icon} {text}"


def fmt_elapsed(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def is_success_status(status: str) -> bool:
    """判断状态是否表示成功（兼容英文与中文返回值）。"""
    return status in {"ALL_SUCCESS", "SUCCESS", "成功", "全部成功"}
