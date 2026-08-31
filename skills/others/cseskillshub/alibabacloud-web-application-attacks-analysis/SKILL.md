---
name: alibabacloud-web-application-attacks-analysis
description: |
  Analyze origin web access logs (Nginx/Apache/IIS) to detect CC attacks,
  proxy-pool distributed bots, scanning probes, login brute force, abnormal
  crawlers, QPS/bandwidth/status-code surges, and slow resource consumption,
  then produce an actionable security report with mitigation advice.
  Read-only; no credentials required.
  Triggers: "CC attack", "HTTP flood", "proxy pool bot", "login brute force",
  "web access log analysis", "access log security analysis",
  "abnormal crawler", "QPS surge", "bandwidth surge", "4xx/5xx surge",
  "site being attacked", "scanning probe", "API abuse",
  "slow request analysis".
---

# Web Application Attacks Analysis

Analyze origin web access logs and identify security threats with actionable mitigation recommendations. The analyzer supports Nginx, Apache, and IIS W3C log formats (auto-detected), extracts the real client IP from X-Forwarded-For chains, aggregates traffic across eleven analysis dimensions, detects eleven attack patterns with evidence-backed confidence levels, and renders a pure-ASCII report in text or Markdown format.

Requires Python 3 (standard library only, no third-party packages):

```bash
python3 --version
```

## Module Index

| Module | Purpose | File |
|--------|---------|------|
| Log Parsing | Format auto-detection, Nginx/Apache/IIS patterns, real client IP extraction, standardized fields | [references/log_parsing.md](references/log_parsing.md) |
| Attack Detection | Detection thresholds, behavioral signatures, and aggregate functions behind each attack type | [references/attack-detection.md](references/attack-detection.md) |
| Report Generation | Dual-audience layout: Executive Summary up front, the 11 detail sections, and Structured Findings (JSON) at the end | [references/report-generation.md](references/report-generation.md) |

> Load references on demand. Do not read all reference files unless the task requires them.

## User Confirmation

- Before running any analysis, confirm the access log file path with the user.
- If the user has not provided a log file, ask for the file path first. Never guess, derive, or scan for log files on your own.
- ABSOLUTE PROHIBITION: never run `find`, `ls`, `glob`, or any filesystem scan to look for log files. If no log file is provided, ask the user for the file path; never probe the disk instead.

## Execution Principle

MANDATORY:

- **Read-only**: this skill only reads and analyzes. It MUST NOT modify, move, or delete any user file, and it requires no credentials of any kind.
- **Single entry point**: all analysis MUST be executed through the entry script `scripts/log_analyzer.py`. Do not hand-assemble parsing or detection command chains. ABSOLUTE PROHIBITION: never write or run your own analysis scripts (no self-authored Python/shell analyzers, no ad-hoc awk/grep detection pipelines); the only permitted analysis command is the entry script.
- **User-provided files only**: only analyze log files the user explicitly specifies. Never open or analyze files the user did not point to.
- **No scanning**: never search for or open log files beyond the one the user provided.
- **Report file path**: the final answer MUST state the analyzed log file path exactly as provided by the user. Never omit it from the final report or summary.
- **Run immediately**: run the entry script immediately with the user-provided file path. ABSOLUTE PROHIBITION: before the first run, do NOT read the analyzer source code, do NOT grep or browse the codebase, and do NOT install any dependency; the script requires only the Python 3 standard library and needs no setup.
- **Missing file handling**: when the user explicitly requests analysis but the specified log file does not exist, still run the entry script ONCE against the given path to capture the real error as evidence, then report the error faithfully and tell the user a real log file is needed. This only permits running against the path the user gave; never scan the disk for alternative files.

## Final Answer Contract

MANDATORY: after every successful analysis, the final answer MUST contain ALL THREE of the following parts, copied from the report without paraphrase:

1. **Analyzed log file path** (MANDATORY): restate the analyzed log file path exactly as the user provided it (e.g. `/tmp/cc_single_ip.log`).
2. **Conclusion line and attack types** (MANDATORY): quote the report's conclusion line containing "ATTACK DETECTED" (or "No attack detected") together with "Overall risk level", and list every detected attack type by its exact original name as printed in the report (e.g. "Proxy-pool distributed bot CC", "Single-IP high-frequency CC", "API Abuse", "Scanning/probing", "Slow resource consumption"). ABSOLUTE PROHIBITION: never rephrase, translate, or paraphrase these attack-type names or the conclusion line.
3. **Dual-audience sections and report path** (MANDATORY): explicitly reference the report's "Executive Summary" and "Structured Findings" sections by these exact names, and state the report file path where the full report was saved.

ABSOLUTE PROHIBITION: never deliver a final answer that omits any of the three parts above.

## Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| C1 | Single-IP High-Frequency CC | One IP generating massive requests in a short time window |
| C2 | Proxy-Pool / Distributed Bot CC | Many IPs sharing similar behavior (same UA, same URL, low frequency per IP) |
| C3 | API Abuse | Direct abnormal access patterns against API endpoints |
| C4 | Scanning / Probing | Systematic path/method enumeration with high 404 ratio |
| C5 | Login Brute Force / Credential Stuffing | Repeated POST requests against login endpoints |
| C6 | Abnormal Crawler | Non-standard UAs, aggressive crawling, spoofed browser UAs reused across many IPs |
| C7 | QPS Surge Mutation | Abrupt traffic surge or drop between adjacent minute windows |
| C8 | Slow Resource Consumption | Abnormally high upstream_time or request_time across time windows |
| C9 | Origin Direct-Access Risk | remote_ip == client_ip (no proxy layer in front of the origin) |
| C10 | Bandwidth Surge Mutation | Abrupt bandwidth surge or drop between adjacent minute windows |
| C11 | Status Code Surge (4xx/5xx) | Abrupt increase of 4xx or 5xx errors between adjacent minute windows |

Detection thresholds and behavioral signatures behind each capability are documented in [references/attack-detection.md](references/attack-detection.md).

## Commands

Set the skill directory once, then run the entry script:

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-web-application-attacks-analysis
```

### Analyze an access log (text report)

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py access.log
```

### Generate a Markdown report

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py access.log --output-format markdown
```

### Analyze only the last N minutes

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py access.log --time-window 30
```

### Force log format and custom output path

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py access.log --format nginx --output /tmp/report.txt
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `log_file` | Path to the access log file (required; `.gz` supported) | - |
| `--format <FORMAT>` | Force log format: `nginx`, `apache`, or `iis` | auto-detect |
| `--top-n <N>` | Number of Top N entries to display in report tables | 20 |
| `--time-window <N>` | Only analyze the last N minutes of log data | full range |
| `--output <FILE>` | Output report file path | `<skill>/output/<logname>_report.<ext>` (falls back to the current working directory if the skill directory is not writable) |
| `--output-format <FORMAT>` | Report format: `text` or `markdown` (Markdown suits documentation tools) | text |

Exit code contract: `0` = analysis succeeded; `1` = input error (file not found, undetectable format, or no parseable log records); `2` = invalid command-line arguments.

## Examples

**Example 1**: User: "My site is being attacked, here is the Nginx access log: /tmp/access.log"

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py /tmp/access.log
```

**Example 2**: User: "I suspect a CC attack in the last hour, analyze this compressed log."

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py access.log.gz --time-window 60
```

**Example 3**: User: "Analyze this Apache log and give me a Markdown report I can paste into my documentation."

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py apache_access --format apache --output-format markdown
```

**Example 4**: User: "Login failures spiked, check this IIS log for brute force."

```bash
cd $SKILL_DIR && python3 scripts/log_analyzer.py u_ex260531.log --format iis
```

## Important Notes

- All attack conclusions MUST be evidence-driven; never speculate beyond what the log data shows.
- When log data is insufficient, the report explicitly lists missing fields (xff / ua / referer / request_time) and their impact on analysis accuracy. Surface these caveats to the user.
- Real client IP extraction: when xff exists, the first valid public IP from left to right becomes client_ip; otherwise client_ip = remote_ip. remote_ip is always preserved.
- Attack-source analysis uses client_ip by default; remote_ip is only used for proxy-chain and direct-access risk assessment.
- Reports are pure ASCII English (no emoji, no box-drawing characters). Do not re-render them with non-ASCII decorations.
- ABSOLUTE PROHIBITION (final answer): it is forbidden to omit the analyzed log file path, the report conclusion line ("ATTACK DETECTED"/"No attack detected" + "Overall risk level"), the exact attack-type names, or the "Executive Summary" / "Structured Findings" section references from the final answer. See the Final Answer Contract above; every final answer MUST satisfy all three parts.
- Reports are dual-audience by design: they open with an Executive Summary (one-line conclusion + overall risk level, plain-language explanation, prioritized actions) for non-technical users, keep the 11 detailed sections for technical deep-dive, and close with a Structured Findings JSON block (machine-readable: overall_risk, attack_types, top_attack_sources, time_window, total_requests, format, data_quality_notes) intended as the next agent stage's input. When relaying results, quote the Executive Summary for non-technical readers and the Structured Findings for downstream automation.
- For large log files (hundreds of MB or more), narrow the scope first with `--time-window` to keep analysis time reasonable.
- Gzip-compressed logs (`*.gz`) are supported directly; no manual decompression needed.
- The report renders the Executive Summary first, then 11 fixed-order detail sections (Attack Conclusion, Core Evidence, Top client_ip, Top URL, IP x URL Cross Analysis, UA, Referer, Status Codes, Traffic, Latency, Mitigation Recommendations), and finally the Structured Findings JSON section; the cross-analysis and latency sections appear only when relevant data exists.
- When `--output` is omitted, the report is written to `<skill>/output/` and the actual saved path is printed to stderr; if the skill directory is read-only, the script falls back to the current working directory and says so on stderr.
- See [references/report-generation.md](references/report-generation.md) for the full report layout and [references/log_parsing.md](references/log_parsing.md) for supported log formats.
