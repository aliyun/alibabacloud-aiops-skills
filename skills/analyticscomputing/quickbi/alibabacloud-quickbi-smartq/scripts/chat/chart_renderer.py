# -*- coding: utf-8 -*-
"""
图表渲染器：基于 result 事件的结构化数据生成 matplotlib 图表。

支持图表类型（与 Quick BI 前端一致）：
  指标看板 | 线图 | 组合图
  柱图     | 堆积柱 | 百分比柱
  条形图   | 堆积条 | 百分比条
  排行榜   | 饼图   | 漏斗图
  散点图   | 气泡图
  分组柱状图（多指标默认）
"""

from __future__ import annotations

import glob
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import matplotlib.patches as mpatches
    import matplotlib.font_manager as fm
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ── 调色板 ──────────────────────────────────────────────────

PALETTE = [
    "#5B8FF9", "#5AD8A6", "#F6BD16", "#E86452",
    "#6DC8EC", "#945FB9", "#FF9845", "#1E9493",
    "#FF99C3", "#269A99",
]

# ── chartType 映射 ──────────────────────────────────────────

_CHART_TYPE_MAP: Dict[str, str] = {
    "indicator":     "indicator",
    "indicator-card": "indicator",
    "line":          "line",
    "combo":         "combo",
    "combination":   "combo",
    "bar":           "bar",
    "column":        "bar",
    "grouped_bar":   "grouped_bar",
    "stacked_bar":   "stacked_bar",
    "stackedBar":    "stacked_bar",
    "percent_bar":   "percent_bar",
    "percentBar":    "percent_bar",
    "horizontal_bar":        "horizontal_bar",
    "horizontalBar":         "horizontal_bar",
    "strip":                 "horizontal_bar",
    "stacked_horizontal_bar":  "stacked_horizontal_bar",
    "stackedHorizontalBar":    "stacked_horizontal_bar",
    "percent_horizontal_bar":  "percent_horizontal_bar",
    "percentHorizontalBar":    "percent_horizontal_bar",
    "ranking":       "ranking",
    "rank":          "ranking",
    "ranking-list":  "ranking",
    "pie":           "pie",
    "funnel":        "funnel",
    "scatter":       "scatter",
    "bubble":        "bubble",
    # table 类型不映射为 bar，保留原值让 render_chart 函数处理
    "table":         "table",
    "wordCloud":     "bar",
}


# ── 密集数据阈值 ────────────────────────────────────────────

MAX_DISPLAY_ITEMS = 20
MAX_DISPLAY_ITEMS_HORIZONTAL = 30

# ── 公共工具 ────────────────────────────────────────────────

def _format_value(v: float) -> str:
    abs_v = abs(v)
    if abs_v >= 1e8:
        return f"{v / 1e8:.2f}亿"
    if abs_v >= 1e4:
        return f"{v / 1e4:.2f}万"
    if abs_v == int(abs_v):
        return str(int(v))
    return f"{v:.2f}"


# ── 中文字体候选列表（按优先级排列） ────────────────────────

_CJK_FONT_CANDIDATES = [
    "Hiragino Sans GB", "STHeiti", "Heiti TC",
    "PingFang HK", "Songti SC", "Arial Unicode MS",
    "PingFang SC", "Microsoft YaHei", "SimHei",
    "Noto Sans CJK SC", "Noto Sans SC",
    "WenQuanYi Micro Hei", "WenQuanYi Zen Hei",
    "Droid Sans Fallback", "Source Han Sans SC",
    "Source Han Sans CN",
]

# 系统字体目录：用于扫描未被 matplotlib 自动发现的 .ttf/.otf 文件
_EXTRA_FONT_DIRS = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    os.path.expanduser("~/.local/share/fonts"),
    os.path.expanduser("~/.fonts"),
    "/System/Library/Fonts",
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    # Windows
    os.path.expandvars(r"%WINDIR%\Fonts"),
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
]

_font_setup_done = False


def _scan_and_register_fonts():
    """扫描系统字体目录，将未被 matplotlib 发现的字体强制注册。"""
    registered = 0
    for font_dir in _EXTRA_FONT_DIRS:
        if not os.path.isdir(font_dir):
            continue
        for ext in ("**/*.ttf", "**/*.otf", "**/*.ttc"):
            for font_path in glob.glob(os.path.join(font_dir, ext), recursive=True):
                try:
                    fm.fontManager.addfont(font_path)
                    registered += 1
                except Exception:
                    pass
    return registered


def _find_available_cjk_font() -> Optional[str]:
    """从候选列表中找到第一个 matplotlib 可用的中文字体名称。"""
    available = {f.name for f in fm.fontManager.ttflist}
    for name in _CJK_FONT_CANDIDATES:
        if name in available:
            return name
    return None


def _test_cjk_render(font_name: str) -> bool:
    """快速测试字体能否真正渲染中文字符（排除字体名存在但字形缺失的情况）。"""
    try:
        prop = fm.FontProperties(family=font_name)
        font_path = fm.findfont(prop, fallback_to_default=False)
        if font_path and os.path.exists(font_path):
            return True
    except Exception:
        pass
    return False


def _setup_style():
    global _font_setup_done

    # 第一步：尝试从候选列表直接匹配
    chosen_font = _find_available_cjk_font()

    # 第二步：若无可用字体，强制扫描系统字体目录并重新匹配
    if not chosen_font:
        count = _scan_and_register_fonts()
        if count > 0:
            chosen_font = _find_available_cjk_font()

    # 第三步：若仍无匹配，尝试从已注册字体中找任意含 CJK 关键词的字体
    if not chosen_font:
        cjk_keywords = [
            "CJK", "Noto", "Han", "Hei", "Song", "Ming", "Fang",
            "YaHei", "Gothic", "Droid", "WenQuan",
        ]
        for f in fm.fontManager.ttflist:
            if any(kw.lower() in f.name.lower() for kw in cjk_keywords):
                if _test_cjk_render(f.name):
                    chosen_font = f.name
                    break

    # 构建最终字体列表：已验证可用的字体放最前面
    if chosen_font:
        font_list = [chosen_font] + [
            f for f in _CJK_FONT_CANDIDATES if f != chosen_font
        ] + ["sans-serif"]
    else:
        font_list = _CJK_FONT_CANDIDATES + ["sans-serif"]

    if not _font_setup_done:
        if chosen_font:
            print(f"[chart_renderer] 使用中文字体: {chosen_font}", file=sys.stderr)
        else:
            _sys_name = platform.system()
            if _sys_name == "Windows":
                _install_hint = (
                    "建议安装: 在 Windows 设置 → 时间和语言 → 语言 → "
                    "中文（简体）→ 安装语言包，或手动安装 SimHei / Microsoft YaHei 字体"
                )
            elif _sys_name == "Darwin":
                _install_hint = "建议安装: macOS 通常自带 PingFang SC，若缺失请通过字体册安装中文字体"
            else:
                _install_hint = (
                    "建议安装: yum install -y google-noto-sans-cjk-sc-fonts && fc-cache -fv"
                )
            print(
                "[chart_renderer] 警告: 未找到可用中文字体，图表中文可能显示异常。"
                f"{_install_hint}",
                file=sys.stderr,
            )
        _font_setup_done = True

    plt.rcParams.update({
        "font.sans-serif": font_list,
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.3,
    })


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "-" or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _build_labels(rows: List[dict], dims: List[dict]) -> List[str]:
    dim_names = [d["fieldName"] for d in dims]
    labels = []
    for row in rows:
        parts = [str(row.get(dn, "")) for dn in dim_names]
        labels.append(" / ".join(parts) if len(parts) > 1 else parts[0])
    return labels


def _extract_metric_values(rows: List[dict], metric_name: str) -> List[Optional[float]]:
    return [_safe_float(r.get(metric_name)) for r in rows]


def _truncate_data(
    rows: List[dict],
    metrics: List[dict],
    limit: int,
) -> Tuple[List[dict], int]:
    """Truncate rows to *limit*, sorting by the first metric descending.

    Returns (truncated_rows, original_total).
    """
    total = len(rows)
    if total <= limit:
        return rows, total

    metric_name = metrics[0]["fieldName"]
    sorted_rows = sorted(rows, key=lambda r: _safe_float(r.get(metric_name)) or 0, reverse=True)
    return sorted_rows[:limit], total


def _apply_common_style(ax, title: str = "", ylabel: str = "", show_grid_y=True):
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12, color="#1e293b")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9, color="#64748b")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#e2e8f0")
    ax.spines["bottom"].set_color("#e2e8f0")
    ax.tick_params(colors="#94a3b8")
    ax.set_axisbelow(True)
    if show_grid_y:
        ax.grid(axis="y", color="#f1f5f9", linewidth=0.8)


def _add_truncation_note(ax, shown: int, total: int, position: str = "bottom"):
    if shown >= total:
        return
    note = f"显示前 {shown} 条（共 {total} 条）"
    if position == "bottom":
        ax.annotate(
            note, xy=(0.5, -0.02), xycoords="axes fraction",
            ha="center", va="top", fontsize=8, color="#94a3b8",
            fontstyle="italic",
        )
    else:
        ax.annotate(
            note, xy=(0.98, 0.98), xycoords="axes fraction",
            ha="right", va="top", fontsize=8, color="#94a3b8",
            fontstyle="italic",
        )


def _save_and_close(fig, path: Path):
    fig.patch.set_facecolor("white")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# ── 图表类型自动推断 ────────────────────────────────────────

# 仅支持单指标的图表类型，多指标时需回退到自动推断
_SINGLE_METRIC_TYPES = {"indicator", "bar", "horizontal_bar", "ranking", "pie", "funnel"}


def _infer_chart_type(
    dims: List[dict],
    metrics: List[dict],
    chart_type_hint: str,
) -> str:
    mapped = _CHART_TYPE_MAP.get(chart_type_hint, "")
    n_dims = len(dims)
    n_metrics = len(metrics)

    # 服务端推荐 table 类型时，直接返回 table（后续会渲染为 Markdown 表格）
    if mapped == "table":
        return "table"

    # 服务端推荐的类型仅支持单指标，但实际有多指标时，回退到自动推断
    if mapped and not (n_metrics > 1 and mapped in _SINGLE_METRIC_TYPES):
        return mapped

    if n_dims == 0 and n_metrics >= 1:
        return "indicator"
    if n_dims >= 1 and n_metrics == 1:
        return "bar"
    if n_dims >= 1 and n_metrics > 1:
        return "grouped_bar"
    return "bar"


# ── 主入口 ──────────────────────────────────────────────────

def render_result_charts(
    result_data: dict,
    output_dir: str | Path,
    *,
    prefix: str = "chart",
) -> List[str]:
    if not HAS_MPL:
        return []

    _setup_style()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data_list = result_data.get("dataList", [])
    if not data_list:
        return []

    ts = int(time.time())
    chart_paths: List[str] = []

    for idx, dataset in enumerate(data_list, 1):
        rows = dataset.get("data", [])
        field_info = dataset.get("fieldInfo", [])
        title = dataset.get("title") or ""
        chart_type_hint = dataset.get("chartType") or ""
        if not rows or not field_info:
            continue

        dims = [f for f in field_info if f.get("role") == "dimension"]
        metrics = [f for f in field_info if f.get("role") == "metric"]
        if not metrics:
            continue

        ctype = _infer_chart_type(dims, metrics, chart_type_hint)
        path = output_dir / f"{prefix}_{ts}_{idx}.png"

        # table 类型不渲染图片，直接跳过（由调用方使用 Markdown 表格 fallback）
        if ctype == "table":
            continue

        renderer = _RENDERERS.get(ctype, _render_bar_chart)
        try:
            renderer(rows, dims, metrics, title, path)
        except Exception:
            _render_bar_chart(rows, dims, metrics, title, path)

        if path.exists():
            chart_paths.append(str(path))

    return chart_paths


# =====================================================================
#  各图表类型渲染函数
#  统一签名: (rows, dims, metrics, title, path)
# =====================================================================

# ── 1. 指标看板 ─────────────────────────────────────────────

def _render_indicator(rows, dims, metrics, title, path):
    metric_name = metrics[0]["fieldName"]
    value = _safe_float(rows[0].get(metric_name))
    if value is None:
        return

    display_title = title or metric_name
    display_value = _format_value(value)

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.62, display_value, ha="center", va="center",
            fontsize=36, fontweight="bold", color="#1e293b")
    ax.text(0.5, 0.28, display_title, ha="center", va="center",
            fontsize=14, color="#64748b")

    _save_and_close(fig, path)


# ── 2. 柱图 ─────────────────────────────────────────────────

def _render_bar_chart(rows, dims, metrics, title, path):
    if not dims:
        _render_indicator(rows, dims, metrics, title, path)
        return

    total = len(rows)
    if total > MAX_DISPLAY_ITEMS:
        rows, total = _truncate_data(rows, metrics, MAX_DISPLAY_ITEMS_HORIZONTAL)
        return _render_bar_as_horizontal(rows, dims, metrics, title, path, total)

    metric = metrics[0]
    metric_name = metric["fieldName"]
    labels = _build_labels(rows, dims)
    values = _extract_metric_values(rows, metric_name)

    valid = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not valid:
        return
    labels, values = zip(*valid)

    fig_w = min(16, max(6, len(labels) * 0.8))
    fig, ax = plt.subplots(figsize=(fig_w, 5))

    bars = ax.bar(range(len(labels)), values, color=PALETTE[0], width=0.6, edgecolor="white")
    show_val_labels = len(labels) <= 15
    if show_val_labels:
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    _format_value(val), ha="center", va="bottom", fontsize=8, color="#475569")

    _set_x_labels(ax, labels)
    _apply_common_style(ax, title or metric_name, metric_name)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))

    _save_and_close(fig, path)


def _render_bar_as_horizontal(rows, dims, metrics, title, path, original_total):
    """Render a horizontal bar chart for dense data (auto-switched from vertical bar)."""
    metric = metrics[0]
    metric_name = metric["fieldName"]
    labels = _build_labels(rows, dims)
    values = _extract_metric_values(rows, metric_name)

    valid = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not valid:
        return
    labels, values = zip(*valid)
    labels = list(reversed(labels))
    values = list(reversed(values))

    n = len(labels)
    fig_h = max(5, n * 0.38)
    fig, ax = plt.subplots(figsize=(10, fig_h))

    max_val = max(values) if values else 1
    colors = [PALETTE[0] if i >= n - 3 else PALETTE[0] for i in range(n)]
    alphas = [1.0 if i >= n - 3 else 0.75 for i in range(n)]

    for i, (label, val) in enumerate(zip(labels, values)):
        ax.barh(i, val, height=0.6, color=colors[i], alpha=alphas[i], edgecolor="white")
        ax.text(val + max_val * 0.01, i, _format_value(val),
                ha="left", va="center", fontsize=8, color="#475569")

    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=8)
    _apply_common_style(ax, title or metric_name, show_grid_y=False)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    _add_truncation_note(ax, n, original_total, position="top")
    _save_and_close(fig, path)


# ── 3. 分组柱状图 ───────────────────────────────────────────

def _render_grouped_bar(rows, dims, metrics, title, path):
    if not dims:
        _render_indicator(rows, dims, metrics, title, path)
        return

    original_total = len(rows)
    if original_total > MAX_DISPLAY_ITEMS:
        rows, original_total = _truncate_data(rows, metrics, MAX_DISPLAY_ITEMS)

    labels = _build_labels(rows, dims)
    metric_names = [m["fieldName"] for m in metrics]
    data_matrix = [[_safe_float(r.get(mn)) for r in rows] for mn in metric_names]

    n_g = len(labels)
    n_m = len(metric_names)
    bw = 0.7 / n_m
    x = np.arange(n_g)

    fig_w = min(16, max(7, n_g * 1.2))
    fig, ax = plt.subplots(figsize=(fig_w, 5.5))

    show_val_labels = n_g <= 12

    for i, (mn, vals) in enumerate(zip(metric_names, data_matrix)):
        offset = (i - n_m / 2 + 0.5) * bw
        pv = [v if v is not None else 0 for v in vals]
        bars = ax.bar(x + offset, pv, bw, label=mn, color=PALETTE[i % len(PALETTE)], edgecolor="white")
        if show_val_labels:
            for bar, val in zip(bars, vals):
                if val is not None:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                            _format_value(val), ha="center", va="bottom", fontsize=7, color="#475569")

    _set_x_labels(ax, labels)
    _apply_common_style(ax, title or "数据对比")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
    _add_truncation_note(ax, n_g, original_total)
    _save_and_close(fig, path)


# ── 4. 堆积柱 ───────────────────────────────────────────────

def _render_stacked_bar(rows, dims, metrics, title, path):
    if not dims:
        return _render_indicator(rows, dims, metrics, title, path)

    original_total = len(rows)
    if original_total > MAX_DISPLAY_ITEMS:
        rows, original_total = _truncate_data(rows, metrics, MAX_DISPLAY_ITEMS)

    labels = _build_labels(rows, dims)
    metric_names = [m["fieldName"] for m in metrics]
    data_matrix = [[v if v is not None else 0 for v in _extract_metric_values(rows, mn)] for mn in metric_names]

    n = len(labels)
    x = np.arange(n)
    fig_w = min(16, max(6, n * 0.9))
    fig, ax = plt.subplots(figsize=(fig_w, 5.5))

    show_val_labels = n <= 15

    bottom = np.zeros(n)
    for i, (mn, vals) in enumerate(zip(metric_names, data_matrix)):
        arr = np.array(vals)
        ax.bar(x, arr, 0.6, bottom=bottom, label=mn, color=PALETTE[i % len(PALETTE)], edgecolor="white")
        if show_val_labels:
            for j, (xi, v) in enumerate(zip(x, arr)):
                if v != 0:
                    ax.text(xi, bottom[j] + v / 2, _format_value(v), ha="center", va="center", fontsize=7, color="white")
        bottom += arr

    _set_x_labels(ax, labels)
    _apply_common_style(ax, title or "堆积柱状图")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
    _add_truncation_note(ax, n, original_total)
    _save_and_close(fig, path)


# ── 5. 百分比柱 ─────────────────────────────────────────────

def _render_percent_bar(rows, dims, metrics, title, path):
    if not dims:
        return _render_indicator(rows, dims, metrics, title, path)

    original_total = len(rows)
    if original_total > MAX_DISPLAY_ITEMS:
        rows, original_total = _truncate_data(rows, metrics, MAX_DISPLAY_ITEMS)

    labels = _build_labels(rows, dims)
    metric_names = [m["fieldName"] for m in metrics]
    data_matrix = [np.array([v if v is not None else 0 for v in _extract_metric_values(rows, mn)]) for mn in metric_names]

    totals = sum(data_matrix)
    totals[totals == 0] = 1
    pct_matrix = [arr / totals * 100 for arr in data_matrix]

    n = len(labels)
    x = np.arange(n)
    fig_w = min(16, max(6, n * 0.9))
    fig, ax = plt.subplots(figsize=(fig_w, 5.5))

    show_val_labels = n <= 15

    bottom = np.zeros(n)
    for i, (mn, pcts) in enumerate(zip(metric_names, pct_matrix)):
        ax.bar(x, pcts, 0.6, bottom=bottom, label=mn, color=PALETTE[i % len(PALETTE)], edgecolor="white")
        if show_val_labels:
            for j, (xi, p) in enumerate(zip(x, pcts)):
                if p > 5:
                    ax.text(xi, bottom[j] + p / 2, f"{p:.0f}%", ha="center", va="center", fontsize=7, color="white")
        bottom += pcts

    ax.set_ylim(0, 100)
    _set_x_labels(ax, labels)
    _apply_common_style(ax, title or "百分比柱状图")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
    _add_truncation_note(ax, n, original_total)
    _save_and_close(fig, path)


# ── 6. 条形图（水平柱） ────────────────────────────────────

def _render_horizontal_bar(rows, dims, metrics, title, path):
    if not dims:
        return _render_indicator(rows, dims, metrics, title, path)

    original_total = len(rows)
    if original_total > MAX_DISPLAY_ITEMS_HORIZONTAL:
        rows, original_total = _truncate_data(rows, metrics, MAX_DISPLAY_ITEMS_HORIZONTAL)

    metric = metrics[0]
    metric_name = metric["fieldName"]
    labels = _build_labels(rows, dims)
    values = _extract_metric_values(rows, metric_name)

    valid = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not valid:
        return
    labels, values = zip(*valid)
    labels = list(reversed(labels))
    values = list(reversed(values))

    n = len(labels)
    fig_h = max(4, n * 0.38)
    fig, ax = plt.subplots(figsize=(10, fig_h))

    y = range(n)
    bars = ax.barh(y, values, color=PALETTE[0], height=0.6, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                " " + _format_value(val), ha="left", va="center", fontsize=8, color="#475569")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    _apply_common_style(ax, title or metric_name, show_grid_y=False)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    _add_truncation_note(ax, n, original_total, position="top")
    _save_and_close(fig, path)


# ── 7. 堆积条（水平堆积） ──────────────────────────────────

def _render_stacked_horizontal_bar(rows, dims, metrics, title, path):
    if not dims:
        return _render_indicator(rows, dims, metrics, title, path)

    labels = list(reversed(_build_labels(rows, dims)))
    metric_names = [m["fieldName"] for m in metrics]
    data_matrix = [np.array(list(reversed([v if v is not None else 0 for v in _extract_metric_values(rows, mn)]))) for mn in metric_names]

    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, max(4, len(labels) * 0.45)))

    left = np.zeros(len(labels))
    for i, (mn, vals) in enumerate(zip(metric_names, data_matrix)):
        ax.barh(y, vals, 0.6, left=left, label=mn, color=PALETTE[i % len(PALETTE)], edgecolor="white")
        for j, (yi, v) in enumerate(zip(y, vals)):
            if v != 0:
                ax.text(left[j] + v / 2, yi, _format_value(v), ha="center", va="center", fontsize=7, color="white")
        left += vals

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    _apply_common_style(ax, title or "堆积条形图", show_grid_y=False)
    ax.grid(axis="x", color="#f1f5f9", linewidth=0.8)
    ax.legend(fontsize=8, loc="lower right", framealpha=0.9)
    _save_and_close(fig, path)


# ── 8. 百分比条 ─────────────────────────────────────────────

def _render_percent_horizontal_bar(rows, dims, metrics, title, path):
    if not dims:
        return _render_indicator(rows, dims, metrics, title, path)

    labels = list(reversed(_build_labels(rows, dims)))
    metric_names = [m["fieldName"] for m in metrics]
    data_matrix = [np.array(list(reversed([v if v is not None else 0 for v in _extract_metric_values(rows, mn)]))) for mn in metric_names]

    totals = sum(data_matrix)
    totals[totals == 0] = 1
    pct_matrix = [arr / totals * 100 for arr in data_matrix]

    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, max(4, len(labels) * 0.45)))

    left = np.zeros(len(labels))
    for i, (mn, pcts) in enumerate(zip(metric_names, pct_matrix)):
        ax.barh(y, pcts, 0.6, left=left, label=mn, color=PALETTE[i % len(PALETTE)], edgecolor="white")
        for j, (yi, p) in enumerate(zip(y, pcts)):
            if p > 5:
                ax.text(left[j] + p / 2, yi, f"{p:.0f}%", ha="center", va="center", fontsize=7, color="white")
        left += pcts

    ax.set_xlim(0, 100)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    _apply_common_style(ax, title or "百分比条形图", show_grid_y=False)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.legend(fontsize=8, loc="lower right", framealpha=0.9)
    _save_and_close(fig, path)


# ── 9. 排行榜 ───────────────────────────────────────────────

def _render_ranking(rows, dims, metrics, title, path):
    if not dims:
        return _render_indicator(rows, dims, metrics, title, path)

    original_total = len(rows)
    if original_total > MAX_DISPLAY_ITEMS_HORIZONTAL:
        rows, original_total = _truncate_data(rows, metrics, MAX_DISPLAY_ITEMS_HORIZONTAL)

    metric = metrics[0]
    metric_name = metric["fieldName"]
    labels = _build_labels(rows, dims)
    values = _extract_metric_values(rows, metric_name)

    valid = [(l, v) for l, v in zip(labels, values) if v is not None]
    if not valid:
        return
    labels, values = zip(*valid)

    labels = list(reversed(labels))
    values = list(reversed(values))
    n = len(labels)
    max_val = max(values) if values else 1

    fig_h = max(4, n * 0.42)
    fig, ax = plt.subplots(figsize=(10, fig_h))

    y = range(n)
    for i, (label, val) in enumerate(zip(labels, values)):
        rank = n - i
        color = PALETTE[0] if rank <= 3 else "#cbd5e1"
        bar_alpha = 1.0 if rank <= 3 else 0.6

        ax.barh(i, val, height=0.55, color=color, alpha=bar_alpha, edgecolor="white")

        ax.text(-max_val * 0.02, i, f"{rank}", ha="right", va="center",
                fontsize=10, fontweight="bold", color=PALETTE[0] if rank <= 3 else "#94a3b8")
        ax.text(val + max_val * 0.01, i, _format_value(val), ha="left", va="center",
                fontsize=8, color="#475569")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(-max_val * 0.05, max_val * 1.18)

    _apply_common_style(ax, title or metric_name, show_grid_y=False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelbottom=False)
    ax.grid(False)
    _add_truncation_note(ax, n, original_total, position="top")
    _save_and_close(fig, path)


# ── 10. 线图 ────────────────────────────────────────────────

def _render_line(rows, dims, metrics, title, path):
    if not dims:
        return _render_indicator(rows, dims, metrics, title, path)

    original_total = len(rows)
    if original_total > MAX_DISPLAY_ITEMS * 2:
        rows = rows[:MAX_DISPLAY_ITEMS * 2]

    labels = _build_labels(rows, dims)
    n = len(labels)
    x = np.arange(n)

    fig_w = min(18, max(6, n * 0.6))
    fig, ax = plt.subplots(figsize=(fig_w, 5))

    show_val_labels = n <= 15
    marker_size = 5 if n <= 20 else (3 if n <= 30 else 0)

    for i, m in enumerate(metrics):
        mn = m["fieldName"]
        values = _extract_metric_values(rows, mn)
        plot_vals = [v if v is not None else float("nan") for v in values]
        color = PALETTE[i % len(PALETTE)]
        ax.plot(x, plot_vals, marker="o" if marker_size > 0 else None,
                markersize=marker_size, linewidth=2, color=color, label=mn)
        if show_val_labels:
            for xi, val in zip(x, values):
                if val is not None:
                    ax.text(xi, val, _format_value(val), ha="center", va="bottom", fontsize=7, color=color)

    _set_x_labels(ax, labels)
    _apply_common_style(ax, title or metrics[0]["fieldName"])
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    if len(metrics) > 1:
        ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
    _add_truncation_note(ax, n, original_total)
    _save_and_close(fig, path)


# ── 11. 组合图（第一个指标柱图，其余线图） ──────────────────

def _render_combo(rows, dims, metrics, title, path):
    if not dims or len(metrics) < 2:
        return _render_line(rows, dims, metrics, title, path)

    original_total = len(rows)
    if original_total > MAX_DISPLAY_ITEMS:
        rows, original_total = _truncate_data(rows, metrics, MAX_DISPLAY_ITEMS)

    labels = _build_labels(rows, dims)
    n = len(labels)
    x = np.arange(n)

    fig_w = min(16, max(7, n * 0.9))
    fig, ax1 = plt.subplots(figsize=(fig_w, 5.5))

    bar_metric = metrics[0]
    bar_vals = [v if v is not None else 0 for v in _extract_metric_values(rows, bar_metric["fieldName"])]
    ax1.bar(x, bar_vals, 0.5, color=PALETTE[0], alpha=0.7, label=bar_metric["fieldName"], edgecolor="white")
    ax1.set_ylabel(bar_metric["fieldName"], fontsize=9, color=PALETTE[0])
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))

    marker_size = 4 if n <= 20 else 0
    ax2 = ax1.twinx()
    for i, m in enumerate(metrics[1:], 1):
        mn = m["fieldName"]
        vals = [v if v is not None else float("nan") for v in _extract_metric_values(rows, mn)]
        color = PALETTE[i % len(PALETTE)]
        ax2.plot(x, vals, marker="o" if marker_size > 0 else None,
                 markersize=marker_size, linewidth=2, color=color, label=mn)
    ax2.set_ylabel(metrics[1]["fieldName"], fontsize=9, color=PALETTE[1])
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))

    _set_x_labels(ax1, labels)
    _apply_common_style(ax1, title or "组合图")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right", framealpha=0.9)
    ax2.spines["top"].set_visible(False)

    _add_truncation_note(ax1, n, original_total)
    _save_and_close(fig, path)


# ── 12. 饼图 ────────────────────────────────────────────────

_MAX_PIE_SLICES = 10

def _render_pie(rows, dims, metrics, title, path):
    metric = metrics[0]
    metric_name = metric["fieldName"]

    if dims:
        labels = _build_labels(rows, dims)
    else:
        labels = [metric_name]

    values = _extract_metric_values(rows, metric_name)
    valid = [(l, v) for l, v in zip(labels, values) if v is not None and v > 0]
    if not valid:
        return
    labels, values = zip(*valid)

    if len(labels) > _MAX_PIE_SLICES:
        pairs = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)
        top = pairs[:_MAX_PIE_SLICES - 1]
        others_sum = sum(v for _, v in pairs[_MAX_PIE_SLICES - 1:])
        labels = [l for l, _ in top] + ["其他"]
        values = [v for _, v in top] + [others_sum]

    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(7, 5.5))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 3 else "",
        colors=colors,
        startangle=90,
        pctdistance=0.75,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_color("white")
        t.set_fontweight("bold")

    legend_labels = [f"{l}  {_format_value(v)}" for l, v in zip(labels, values)]
    ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1.05, 0.5),
              fontsize=8, frameon=False)

    display_title = title or metric_name
    ax.set_title(display_title, fontsize=13, fontweight="bold", pad=12, color="#1e293b")

    _save_and_close(fig, path)


# ── 13. 漏斗图 ──────────────────────────────────────────────

def _render_funnel(rows, dims, metrics, title, path):
    metric = metrics[0]
    metric_name = metric["fieldName"]

    if dims:
        labels = _build_labels(rows, dims)
    else:
        labels = [str(i + 1) for i in range(len(rows))]

    values = _extract_metric_values(rows, metric_name)
    valid = [(l, v) for l, v in zip(labels, values) if v is not None and v > 0]
    if not valid:
        return
    labels, values = zip(*valid)

    max_val = max(values)
    n = len(labels)

    fig, ax = plt.subplots(figsize=(8, max(4, n * 0.7)))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n)
    ax.axis("off")

    for i, (label, val) in enumerate(zip(labels, values)):
        width = val / max_val * 0.8
        left = (1 - width) / 2
        y_bottom = n - i - 1
        color = PALETTE[i % len(PALETTE)]

        rect = mpatches.FancyBboxPatch(
            (left, y_bottom + 0.1), width, 0.75,
            boxstyle="round,pad=0.02", facecolor=color, edgecolor="white", linewidth=1.5,
        )
        ax.add_patch(rect)

        ax.text(0.5, y_bottom + 0.48, f"{label}    {_format_value(val)}",
                ha="center", va="center", fontsize=10, color="white", fontweight="bold")

    display_title = title or metric_name
    ax.set_title(display_title, fontsize=13, fontweight="bold", pad=8, color="#1e293b")
    _save_and_close(fig, path)


# ── 14. 散点图 ──────────────────────────────────────────────

def _render_scatter(rows, dims, metrics, title, path):
    if len(metrics) < 2:
        return _render_bar_chart(rows, dims, metrics, title, path)

    x_metric = metrics[0]["fieldName"]
    y_metric = metrics[1]["fieldName"]
    x_vals = _extract_metric_values(rows, x_metric)
    y_vals = _extract_metric_values(rows, y_metric)

    labels = _build_labels(rows, dims) if dims else [None] * len(rows)

    valid = [(xv, yv, l) for xv, yv, l in zip(x_vals, y_vals, labels) if xv is not None and yv is not None]
    if not valid:
        return
    xs, ys, ls = zip(*valid)

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.scatter(xs, ys, s=60, c=PALETTE[0], alpha=0.7, edgecolors="white", linewidths=0.5)

    for xv, yv, l in zip(xs, ys, ls):
        if l:
            ax.annotate(l, (xv, yv), textcoords="offset points", xytext=(5, 5), fontsize=7, color="#64748b")

    ax.set_xlabel(x_metric, fontsize=10, color="#475569")
    ax.set_ylabel(y_metric, fontsize=10, color="#475569")
    _apply_common_style(ax, title or "散点图")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    _save_and_close(fig, path)


# ── 15. 气泡图 ──────────────────────────────────────────────

def _render_bubble(rows, dims, metrics, title, path):
    if len(metrics) < 2:
        return _render_scatter(rows, dims, metrics, title, path)

    x_metric = metrics[0]["fieldName"]
    y_metric = metrics[1]["fieldName"]
    size_metric = metrics[2]["fieldName"] if len(metrics) >= 3 else None

    x_vals = _extract_metric_values(rows, x_metric)
    y_vals = _extract_metric_values(rows, y_metric)
    size_vals = _extract_metric_values(rows, size_metric) if size_metric else [None] * len(rows)

    labels = _build_labels(rows, dims) if dims else [None] * len(rows)

    valid = [(xv, yv, sv, l) for xv, yv, sv, l in zip(x_vals, y_vals, size_vals, labels)
             if xv is not None and yv is not None]
    if not valid:
        return
    xs, ys, ss, ls = zip(*valid)

    if any(s is not None for s in ss):
        s_arr = np.array([s if s is not None else 0 for s in ss])
        max_s = s_arr.max() if s_arr.max() > 0 else 1
        sizes = (s_arr / max_s) * 800 + 30
    else:
        sizes = [120] * len(xs)

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.scatter(xs, ys, s=sizes, c=PALETTE[0], alpha=0.5, edgecolors=PALETTE[0], linewidths=1)

    for xv, yv, l in zip(xs, ys, ls):
        if l:
            ax.annotate(l, (xv, yv), textcoords="offset points", xytext=(5, 5), fontsize=7, color="#64748b")

    ax.set_xlabel(x_metric, fontsize=10, color="#475569")
    ax.set_ylabel(y_metric, fontsize=10, color="#475569")
    _apply_common_style(ax, title or "气泡图")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_value(x)))
    _save_and_close(fig, path)


# ── X 轴标签辅助 ───────────────────────────────────────────

def _set_x_labels(ax, labels):
    n = len(labels)
    ax.set_xticks(range(n))

    if n <= 6:
        ax.set_xticklabels(labels, fontsize=9, rotation=0, ha="center")
    elif n <= 15:
        ax.set_xticklabels(labels, fontsize=8, rotation=30, ha="right")
    elif n <= MAX_DISPLAY_ITEMS:
        ax.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    else:
        step = max(1, n // 15)
        display = [labels[i] if i % step == 0 else "" for i in range(n)]
        ax.set_xticklabels(display, fontsize=7, rotation=45, ha="right")


# ── 渲染器注册表 ───────────────────────────────────────────

_RENDERERS = {
    "indicator":               _render_indicator,
    "bar":                     _render_bar_chart,
    "grouped_bar":             _render_grouped_bar,
    "stacked_bar":             _render_stacked_bar,
    "percent_bar":             _render_percent_bar,
    "horizontal_bar":          _render_horizontal_bar,
    "stacked_horizontal_bar":  _render_stacked_horizontal_bar,
    "percent_horizontal_bar":  _render_percent_horizontal_bar,
    "ranking":                 _render_ranking,
    "line":                    _render_line,
    "combo":                   _render_combo,
    "pie":                     _render_pie,
    "funnel":                  _render_funnel,
    "scatter":                 _render_scatter,
    "bubble":                  _render_bubble,
}


# =====================================================================
#  单图表入口（供数据集问数 / bichart 模式使用）
# =====================================================================

def render_chart(chart_data: dict, output_dir: str | Path = ".") -> Optional[str]:
    """渲染单个图表数据为 PNG，返回文件路径；失败时返回 None。

    ``chart_data`` 结构与 ``render_result_charts`` 的 ``dataList`` 中的
    单个元素一致：``{data, fieldInfo, chartType, title, id?}``。
    """
    if not HAS_MPL:
        return None

    output_dir = Path(output_dir)
    wrapper = {"dataList": [chart_data]}
    prefix = f"chart_{chart_data.get('id', 'out')[:8]}"
    paths = render_result_charts(wrapper, output_dir, prefix=prefix)
    return paths[0] if paths else None


# =====================================================================
#  Markdown 表格回退（matplotlib 不可用时使用）
# =====================================================================

def chart_data_to_markdown(chart_data: dict) -> str:
    """将图表数据转为 Markdown 表格文本。"""
    data = chart_data.get("data", [])
    field_info = chart_data.get("fieldInfo", [])
    title = chart_data.get("title", "")

    if not data or not field_info:
        return f"**{title}**\n\n（无数据）"

    headers = [f.get("fieldName", f"列{i}") for i, f in enumerate(field_info)]
    lines: List[str] = [f"**{title}**\n"] if title else []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join([" --- "] * len(headers)) + "|")

    for row in data[:50]:
        row_vals = [str(row.get(h, "")) for h in headers]
        lines.append("| " + " | ".join(row_vals) + " |")

    if len(data) > 50:
        lines.append(f"\n（共 {len(data)} 行，仅显示前 50 行）")

    return "\n".join(lines)
