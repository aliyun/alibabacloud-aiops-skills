#!/usr/bin/env python3
# requires: wuying-agentbay-sdk>=1.0.0
import argparse
import asyncio
import base64
import json
import os
import sys
import time

from agentbay import AsyncAgentBay, CreateSessionParams


def _api_key_config_path() -> str:
    """Return the API key config file path for the current platform."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        # Windows: %USERPROFILE%\.config\agentbay\api_key
        base = os.environ.get("USERPROFILE", home)
        return os.path.join(base, ".config", "agentbay", "api_key")
    # Unix-like: $XDG_CONFIG_HOME/agentbay/api_key or ~/.config/agentbay/api_key
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(xdg, "agentbay", "api_key")


def _read_api_key_from_config() -> str:
    """Read API key from config file if present. Returns empty string if not found or on error."""
    path = _api_key_config_path()
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return (f.read() or "").strip()
    except OSError:
        pass
    return ""


def _load_code(args: argparse.Namespace) -> str:
    if args.code and args.code_file:
        raise ValueError("Use only one of --code or --code-file.")
    if args.code:
        return args.code
    if args.code_file:
        # Security: Validate code-file path is within current working directory
        cwd = os.getcwd()
        abs_code_file = os.path.abspath(args.code_file)
        # Resolve symlinks to prevent directory traversal attacks
        abs_code_file = os.path.realpath(abs_code_file)
        if not abs_code_file.startswith(cwd + os.sep) and abs_code_file != cwd:
            raise ValueError(
                f"Security error: --code-file must be within current working directory. "
                f"Current directory: {cwd}, Requested file: {abs_code_file}"
            )
        with open(abs_code_file, "r", encoding="utf-8") as f:
            return f.read()
    raise ValueError("Either --code or --code-file is required.")


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run code in AgentBay code_latest sandbox via run_code."
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("AGENTBAY_API_KEY", ""),
        help="AgentBay API key (or set AGENTBAY_API_KEY).",
    )
    parser.add_argument(
        "--language",
        default="python",
        choices=["python", "javascript", "r", "java"],
        help="Language for run_code (python/javascript/r/java).",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=60,
        help="Execution timeout in seconds (<= 60).",
    )
    parser.add_argument("--code", help="Inline code to execute.")
    parser.add_argument(
        "--code-file",
        help="Path to a file containing code to execute (must be within current working directory).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON output.",
    )

    args = parser.parse_args()

    # Validate timeout-s parameter (must be <= 60)
    if args.timeout_s > 60:
        print("Error: --timeout-s must be <= 60 seconds.", file=sys.stderr)
        return 2
    if args.timeout_s <= 0:
        print("Error: --timeout-s must be > 0 seconds.", file=sys.stderr)
        return 2

    if not args.api_key:
        args.api_key = _read_api_key_from_config()
    if not args.api_key:
        path = _api_key_config_path()
        print(
            f"Missing API key. Apply for an API key at the AgentBay console:\n"
            f"  https://agentbay.console.aliyun.com/service-management\n"
            f"Then save it to the local config file: {path}\n"
            f"(Alternatively, set the AGENTBAY_API_KEY environment variable.)",
            file=sys.stderr,
        )
        return 2

    try:
        code = _load_code(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # For Python matplotlib code, add preamble to ensure proper backend configuration
    if args.language.lower() == "python" and ("matplotlib" in code or "plt." in code):
        # Always inject CJK font configuration, regardless of user code content.
        # Split into two parts: backend setup and CJK font config.
        # This ensures CJK fonts are configured even if user code already sets Agg backend.
        backend_preamble = """
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
"""
        # Detect if user code contains CJK characters (Chinese/Japanese/Korean)
        import re as _re_cjk
        _has_cjk_chars = bool(_re_cjk.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', code))

        # If CJK characters detected, add font installation as a safety net
        cjk_install_preamble = ""
        if _has_cjk_chars:
            cjk_install_preamble = """
import subprocess as _sp
import os as _os

# Proactively install CJK fonts if not already available
_font_paths = ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
               '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
if not any(_os.path.exists(p) for p in _font_paths):
    _sp.run(['apt-get', 'update', '-qq'], capture_output=True, timeout=30)
    _sp.run(['apt-get', 'install', '-y', '-qq', 'fonts-wqy-microhei'], capture_output=True, timeout=60)
"""

        cjk_font_preamble = """
import matplotlib
import matplotlib.font_manager as fm
import os as _os
import glob as _glob

# Auto-configure CJK font for Chinese/Japanese/Korean character rendering
_cjk_font_names = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC',
                    'Noto Sans CJK', 'Noto Sans CJK JP', 'Noto Sans CJK KR',
                    'SimHei', 'Microsoft YaHei', 'PingFang SC',
                    'Source Han Sans SC', 'AR PL UMing CN', 'Droid Sans Fallback']

# Try to add font files directly if they exist
_font_dirs = ['/usr/share/fonts/truetype/wqy', '/usr/share/fonts/opentype/noto',
              '/usr/share/fonts/truetype', '/usr/local/share/fonts']
for _fd in _font_dirs:
    if _os.path.isdir(_fd):
        for _ff in _glob.glob(_os.path.join(_fd, '**', '*.tt[cf]'), recursive=True):
            try:
                fm.fontManager.addfont(_ff)
            except Exception:
                pass
        for _ff in _glob.glob(_os.path.join(_fd, '**', '*.otf'), recursive=True):
            try:
                fm.fontManager.addfont(_ff)
            except Exception:
                pass

# Clear matplotlib font cache and rebuild from scratch for reliability
_cache_dir = matplotlib.get_cachedir()
if _cache_dir and _os.path.isdir(_cache_dir):
    for _cf in _glob.glob(_os.path.join(_cache_dir, 'fontlist-*')):
        try:
            _os.remove(_cf)
        except Exception:
            pass
try:
    fm.fontManager = fm.FontManager()
except Exception:
    pass

_available_cjk = [f.name for f in fm.fontManager.ttflist
                  if any(c in f.name for c in _cjk_font_names) or 'CJK' in f.name]
if _available_cjk:
    matplotlib.rcParams['font.sans-serif'] = list(dict.fromkeys(_available_cjk)) + ['DejaVu Sans']
else:
    matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
"""
        imports_preamble = """
import matplotlib.pyplot as plt
import base64
from io import BytesIO
"""
        # Strip any existing matplotlib font/backend config from user code to avoid conflicts
        import re as _re
        # Remove user's own matplotlib.use(...) calls to avoid double-setting
        code = _re.sub(r"""matplotlib\.use\(['"][^'"]*['"]\)""", '# (backend set by runner)', code)
        # Remove user's own rcParams font settings to avoid overriding our CJK config
        code = _re.sub(r"""matplotlib\.rcParams\[['"]font\.sans-serif['"]\]\s*=.*""", '# (font set by runner)', code)
        code = _re.sub(r"""matplotlib\.rcParams\[['"]axes\.unicode_minus['"]\]\s*=.*""", '# (unicode_minus set by runner)', code)
        code = _re.sub(r"""plt\.rcParams\[['"]font\.sans-serif['"]\]\s*=.*""", '# (font set by runner)', code)
        code = _re.sub(r"""plt\.rcParams\[['"]axes\.unicode_minus['"]\]\s*=.*""", '# (unicode_minus set by runner)', code)
        code = cjk_install_preamble + backend_preamble + cjk_font_preamble + imports_preamble + code

        # If the code doesn't have savefig, automatically save the plot
        if "plt.savefig" not in code and "savefig" not in code:
            # Add code to save the last plot automatically
            auto_save_code = """
# Automatically save the last plot if no savefig was called
if plt.get_fignums():
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    print(f"[AGENTBAY_CHART_BASE64:{img_base64}]")
    plt.close()
"""
            code = code + auto_save_code

    try:
        agent_bay = AsyncAgentBay(api_key=args.api_key, user_agent='AlibabaCloud-Agent-Skills/alibabacloud-agentbay-aio-skills')
    except TypeError:
        agent_bay = AsyncAgentBay(api_key=args.api_key)
    session_result = await agent_bay.create(CreateSessionParams(image_id="code_latest"))

    try:
        code_result = await session_result.session.code.run_code(
            code, args.language, timeout_s=args.timeout_s
        )
        if args.json:
            payload = {
                "success": code_result.success,
                "result": code_result.result,
                "logs": {
                    "stdout": code_result.logs.stdout,
                    "stderr": code_result.logs.stderr,
                },
                "error_message": code_result.error_message,
            }
            print(json.dumps(payload, ensure_ascii=True))
        else:
            if code_result.success:
                # First, check for AGENTBAY_CHART_BASE64 marker in stdout or result
                stdout_content = "".join(code_result.logs.stdout) if code_result.logs.stdout else ""
                result_content = code_result.result or ""
                combined_output = stdout_content + result_content

                # Check for our custom marker [AGENTBAY_CHART_BASE64:...]
                import re
                chart_match = re.search(r'\[AGENTBAY_CHART_BASE64:([A-Za-z0-9+/=]+)\]', combined_output)
                if chart_match:
                    try:
                        img_base64 = chart_match.group(1)
                        img_bytes = base64.b64decode(img_base64)
                        timestamp = int(time.time())
                        filename = f"chart_{timestamp}.png"
                        with open(filename, "wb") as f:
                            f.write(img_bytes)
                        print(f"Successfully saved {filename} ({len(img_bytes)} bytes)")
                        # Remove the marker from output
                        combined_output = combined_output.replace(chart_match.group(0), "")
                    except Exception as e:
                        print(f"Error saving auto-captured chart: {e}", file=sys.stderr)

                # Check for rich output in results
                if hasattr(code_result, 'results') and code_result.results:
                    for res in code_result.results:
                        # Handle Images (PNG, JPEG, SVG)
                        img_data = None
                        ext = ""
                        if hasattr(res, 'png') and res.png:
                            img_data = res.png
                            ext = "png"
                        elif hasattr(res, 'jpeg') and res.jpeg:
                            img_data = res.jpeg
                            ext = "jpg"
                        elif hasattr(res, 'svg') and res.svg:
                            img_data = res.svg
                            ext = "svg"

                        if img_data:
                            try:
                                timestamp = int(time.time())
                                filename = f"chart_{timestamp}.{ext}"
                                if ext == "svg":
                                    with open(filename, "w", encoding="utf-8") as f:
                                        f.write(img_data)
                                    print(f"Successfully saved {filename}")
                                else:
                                    if isinstance(img_data, str):
                                        img_bytes = base64.b64decode(img_data)
                                    else:
                                        img_bytes = img_data
                                    with open(filename, "wb") as f:
                                        f.write(img_bytes)
                                    print(f"Successfully saved {filename} ({len(img_bytes)} bytes)")
                            except Exception as e:
                                print(f"Error saving image: {e}", file=sys.stderr)

                # For matplotlib charts, also check if the code contains plt.savefig or savefig
                # and verify if the file was created in the sandbox
                if args.language.lower() == "python" and ("plt.savefig" in code or "savefig" in code):
                    # Try to extract saved file info from stdout or result
                    stdout_content = "".join(code_result.logs.stdout) if code_result.logs.stdout else ""
                    result_content = code_result.result or ""

                    # Check if there's any indication of file saving
                    if "saved" in stdout_content.lower() or "saved" in result_content.lower():
                        print("\nChart saved successfully.")
                    else:
                        # If matplotlib was used but no explicit savefig, try to save the plot
                        # This is a fallback for cases where the user didn't call savefig
                        if "plt.show()" in code or ("plt.plot" in code and "plt.savefig" not in code):
                            print("\nNote: The matplotlib chart was generated but not explicitly saved.")
                            print("To save the chart, please use plt.savefig('filename.png') in your code.")

                # Continue with other rich output handling
                if hasattr(code_result, 'results') and code_result.results:
                    for res in code_result.results:
                        # Handle HTML
                        if hasattr(res, 'html') and res.html:
                            print(f"\n[HTML Output]:\n{res.html}")

                        # Handle Markdown
                        if hasattr(res, 'markdown') and res.markdown:
                            print(f"\n[Markdown Output]:\n{res.markdown}")

                        # Handle LaTeX
                        if hasattr(res, 'latex') and res.latex:
                            print(f"\n[LaTeX Output]:\n{res.latex}")

                        # Handle JSON
                        if hasattr(res, 'json') and res.json:
                            print(f"\n[JSON Output]:\n{json.dumps(res.json, indent=2)}")

                        # Handle Chart Data
                        if hasattr(res, 'chart') and res.chart:
                            print(f"\n[Chart Data]:\n{json.dumps(res.chart, indent=2)}")

                        # Handle Text (if not main result, to avoid duplication)
                        if hasattr(res, 'text') and res.text and not getattr(res, 'is_main_result', False):
                             print(f"\n[Text Output]:\n{res.text}")

                if code_result.result:
                    print(code_result.result)
                if code_result.logs.stdout:
                    print("".join(code_result.logs.stdout), end="")
                if code_result.logs.stderr:
                    print("".join(code_result.logs.stderr), end="", file=sys.stderr)
            else:
                print(code_result.error_message or "run_code failed", file=sys.stderr)
                return 1
    finally:
        await session_result.session.delete()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
