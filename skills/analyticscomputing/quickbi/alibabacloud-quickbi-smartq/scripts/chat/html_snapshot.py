# -*- coding: utf-8 -*-
"""
HTML → PNG 截图工具（零额外依赖）。

利用系统已安装的 Chrome / Chromium / Edge 的 headless 模式将 HTML 文件截图为 PNG。
无需安装 Playwright、Selenium 或任何 pip/npm 包。

用法：
    from html_snapshot import html_to_png

    png_path = html_to_png("/path/to/chart.html")
    # 返回 PNG 路径，失败返回 None
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

_BROWSER_PATHS: dict[str, list[str]] = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ],
    "Linux": [
        "google-chrome",
        "google-chrome-stable",
        "chromium-browser",
        "chromium",
        "microsoft-edge",
    ],
    "Windows": [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    ],
}


def _find_browser() -> Optional[str]:
    """在系统中查找可用的 Chrome/Chromium/Edge 浏览器路径。"""
    sys_name = platform.system()
    candidates = _BROWSER_PATHS.get(sys_name, [])

    for path in candidates:
        if sys_name in ("Darwin", "Windows"):
            if Path(path).exists():
                return path
        else:
            # 使用 shutil.which() 替代 subprocess 调用 which 命令，跨平台兼容
            found = shutil.which(path)
            if found:
                return found
    return None


def html_to_png(
    html_path: str,
    *,
    output_path: Optional[str] = None,
    width: int = 800,
    height: int = 600,
) -> Optional[str]:
    """将 HTML 文件截图为 PNG。

    Args:
        html_path: HTML 文件的绝对路径
        output_path: PNG 输出路径，默认为同目录同名 .png
        width: 视口宽度
        height: 视口高度

    Returns:
        PNG 文件路径，浏览器不可用或截图失败时返回 None
    """
    browser = _find_browser()
    if not browser:
        return None

    html_path = str(Path(html_path).resolve())
    if output_path is None:
        output_path = str(Path(html_path).with_suffix(".png"))

    # 使用 Path.as_uri() 生成跨平台兼容的 file:// URL
    file_url = Path(html_path).as_uri()

    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-software-rasterizer",
        f"--window-size={width},{height}",
        f"--screenshot={output_path}",
        "--hide-scrollbars",
        file_url,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
        )
        if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
            return output_path
    except Exception:
        pass

    return None
