---
name: alibabacloud-agentbay-aio-skills
description: >
  Execute code in a secure cloud sandbox via AgentBay SDK. Use this skill whenever users
  request to run, execute, or evaluate code (Python, JavaScript, R, Java), including
  plotting charts, running scripts, or viewing code output. Covers requests like
  "run this code", "execute script", "plot with Python", "run data analysis".
---

# AgentBay AIO Skill

## How It Works

This skill runs user code in a remote sandbox (not locally) via AgentBay SDK. The entry script `scripts/run_code.py` handles sandbox creation, code execution, and result parsing automatically.

```bash
# Basic execution
python scripts/run_code.py --code "<user_code>" --language python

# Execute from file
python scripts/run_code.py --code-file /path/to/file.py --language python

# Structured JSON output (use this when writing results to files)
python scripts/run_code.py --code "<user_code>" --language python --json
```

Supported languages: `python`, `javascript`, `r`, `java` (case-insensitive). Timeout: 60 seconds max (`--timeout-s`).

## Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | >= 3.8 | Runtime |
| wuying-agentbay-sdk | >= 1.0.0 | AgentBay SDK for sandbox code execution |

## Setup

The script requires `wuying-agentbay-sdk` installed locally. Install it before first use:

```bash
pip install wuying-agentbay-sdk
```

This is the skill's own required dependency — installing it is not a security concern. If `run_code.py` fails with `ModuleNotFoundError: No module named 'agentbay'`, install the SDK and retry.

Network domains used: `agentbay.aliyuncs.com` (API endpoint), `agentbay.console.aliyun.com` (console), `mirrors.aliyun.com` (PyPI mirror).

## API Key Configuration

Run scripts directly without prompting for API Key configuration. Only guide users when the script explicitly reports "Missing API key":

1. Apply at [AgentBay Console](https://agentbay.console.aliyun.com/service-management)
2. Save to config file: `~/.config/agentbay/api_key` (macOS/Linux) or `%USERPROFILE%\.config\agentbay\api_key` (Windows)

## Execution Rules

**CRITICAL**: All user code MUST run through `scripts/run_code.py` — NEVER execute code directly in the local terminal (e.g., `python -c`, `node -e`, `timeout ... python`). This applies even if `run_code.py` fails on the first attempt.

- If `run_code.py` fails with a transient error, **retry once** before reporting failure.
- If `run_code.py` fails with "Missing API key" or `ModuleNotFoundError`, guide the user to fix the issue (see Setup / API Key Configuration) and retry — do NOT fall back to local execution.
- NEVER run user code locally as a fallback. Report the error instead.

Do not install packages other than `wuying-agentbay-sdk`, and do not create virtual environments. The sandbox has its own package environment — the Agent should not attempt to modify it from outside.

## Output Handling

**Standard output**: Exit code 0 = success, results in stdout. Non-zero = failure, error in stderr.

**Structured output** (`--json`): Returns `{ success, result, logs: { stdout, stderr }, error_message }`.

**Writing results to files**: Use `--json` mode and extract only the `result` field to write to the target file. This ensures SDK metadata (such as session identifiers or internal request IDs) is not accidentally included in output files, because the raw non-JSON output may contain SDK log lines mixed with actual results.

**Reporting results**: Quote the script's original output directly. Do not infer, abbreviate, or recalculate values — if output is long, clearly indicate omitted portions but keep quoted values verbatim.

## File Download Validation

When saving files generated in the sandbox (e.g., chart images) to the local environment:

1. Use `--json` mode and extract the base64 content with Python (`json` module) — do NOT use shell tools (grep/sed/awk) to extract base64 strings, as they truncate long strings.
2. Decode with: `python -c "import base64,json,sys; d=json.load(sys.stdin); open('out.png','wb').write(base64.b64decode(d['result']))" < output.json`
3. Verify the saved file: size > 0 bytes; for images (PNG/JPEG), check magic bytes (`89 50 4E 47` / `FF D8 FF`).
4. For chart images, file size should be > 5 KB. A file under 5 KB almost certainly indicates truncated data — re-extract and re-decode.

If verification fails, retry the download. Do not report success with a corrupted file.

## Chinese/CJK Character Rendering

The script (`run_code.py`) automatically handles CJK font configuration for matplotlib code — it detects Chinese/Japanese/Korean characters in user code and injects font installation and configuration before execution. No manual font setup is needed.

When the user's code contains Chinese characters AND uses matplotlib/plt, the Agent should proactively prepend the following font installation block in the `--code` argument on the **first execution** (not as a retry), because the sandbox may lack CJK fonts and the script's auto-detection provides a safety net but explicit installation is more reliable:

```python
import subprocess
subprocess.run(['apt-get', 'update', '-qq'], capture_output=True)
subprocess.run(['apt-get', 'install', '-y', '-qq', 'fonts-wqy-microhei'], capture_output=True)
import matplotlib
import matplotlib.font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc')
fm.fontManager = fm.FontManager()
matplotlib.rcParams['font.family'] = 'WenQuanYi Micro Hei'
matplotlib.rcParams['axes.unicode_minus'] = False
```

This proactive approach avoids the undetectable failure where Chinese characters render as blank boxes (tofu) in the generated image — since tofu appears only visually in the image and produces no text-based warning in stdout, a retry-based approach cannot reliably detect the problem.

## Information Security

Do not output internal environment variable names, API Key values, or SDK debug details in conversation replies. When executing scripts, use `--json` mode and display only the `result` and `error_message` fields to users. The raw SDK output may contain internal fields (session identifiers, request IDs, access credentials) that should not be exposed to users or written to output files.
