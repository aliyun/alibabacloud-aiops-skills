# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
from typing import List, Optional


def get_kernel_log_lines(source: str, path: Optional[str]) -> List[str]:
    if path:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    if source == "journal":
        try:
            r = subprocess.run(
                ["journalctl", "-k", "-b", "-o", "short-precise", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout.splitlines()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    for cmd in (["dmesg", "-T"], ["dmesg"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if r.returncode == 0 and r.stdout:
                return r.stdout.splitlines()
        except FileNotFoundError:
            pass
    return []
