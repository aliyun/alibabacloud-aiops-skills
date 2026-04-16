# -*- coding: utf-8 -*-
"""
用户可见「远程专项能进一步得到什么」——措辞与 skill 内 references/diagnoses 对齐；
不包含仓库外路径，供 classify / 各 memory 子命令复用。
"""
from __future__ import annotations

from typing import Dict


def remote_analysis_value_map() -> Dict[str, str]:
    """service_name -> 简短说明（中文）。"""
    return {
        "memgraph": (
            "SysOM memgraph：在目标 ECS 上做内存全景采集与汇总，含整机/应用维度的内存组成，"
            "强于仅看本机 /proc 粗值。"
        ),
        "oomcheck": (
            "SysOM oomcheck：在目标机结合 memgraph 等路径上的输出与日志侧信息，"
            "定位 OOM / oom-killer 事件与根因链。"
        ),
        "javamem": (
            "SysOM javamem：JVM 堆、GC、Java 进程内存等语言侧专项分析。"
        ),
    }
