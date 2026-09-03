# alibabacloud-migration-cas-cutover-review Installation and Usage Guide

> This document was consolidated from the original `INSTALLATION.md`, `QUICKSTART.md`, `README.md`, and usage-notes text file.
> All paths are relative paths or path placeholders, avoiding binding to a specific user directory.

## Path Placeholder Conventions

| Placeholder | Description |
|--------|------|
| `${SKILL_ROOT}` | The root directory of the current skill package (auto-injected by Qoder; for manual installation usually `~/.qoder/skills/alibabacloud-migration-cas-cutover-review/`) |
| `<work-dir>` | The current directory when the user runs the command |

## System Requirements

- Python 3.8+ (macOS / Linux / Windows all supported)
- Dependency: `openpyxl==3.1.5`
- No network needed; runs entirely locally

## Installation Steps

### Auto-load via Qoder (recommended)
Place the skill directory into `~/.qoder/skills/`, and Qoder will recognize it automatically on startup.

### Manual Deployment
```bash
# 1. Copy the skill to the target location
cp -r <this skill directory> ~/.qoder/skills/alibabacloud-migration-cas-cutover-review/

# 2. Install the dependency
pip install openpyxl==3.1.5
# If there are permission issues: pip install --user openpyxl==3.1.5

# 3. Verify the installation
python3 scripts/cutover_reviewer.py assets/example-cutover-manual.xlsx --scenario other
```

## 5-Minute Quick Start

```bash
# Step 1: Prepare an .xlsx cutover manual (see assets/example-cutover-manual.xlsx)

# Step 2: Run the review (choose batch / full / other by scenario)
python ${SKILL_ROOT}/scripts/cutover_reviewer.py your-cutover-manual.xlsx \
    --scenario batch -o ./output

# Step 3: Open the report
# macOS:   open output/*_Review*.md
# Linux:   xdg-open output/*_Review*.md
# Windows: start output/*_Review*.md
```

Report focus points:
1. **Overall score**: ≥ 70 is recommended before execution
2. **Issue-list summary**: sorted by CRITICAL / HIGH / MEDIUM / LOW
3. **P0 immediate-action list**: items that must be resolved first

## Command Parameter Cheat Sheet

Invocation convention (mandatory): run the command from the skill root and keep the script argument as the relative path `scripts/cutover_reviewer.py` — never an absolute path, never a shell variable such as `$SKILL_DIR`, never wrapped in a generated `.sh` file. The manual path comes immediately after the script path, and `--scenario` / `--list-sheets` immediately after the manual path; all other flags follow.

```bash
# List the Sheet names only (no review)
python3 scripts/cutover_reviewer.py manual.xlsx --list-sheets

# Basic (other scenario, default)
python3 scripts/cutover_reviewer.py manual.xlsx

# Application-database batch cutover
python3 scripts/cutover_reviewer.py manual.xlsx --scenario batch

# Application-database full cutover
python3 scripts/cutover_reviewer.py manual.xlsx --scenario full

# Output to a specified directory
python3 scripts/cutover_reviewer.py manual.xlsx --scenario batch -o ./output

# JSON format
python3 scripts/cutover_reviewer.py manual.xlsx --format json

# Markdown + JSON output simultaneously
python3 scripts/cutover_reviewer.py manual.xlsx --format both

# Check only specific Sheet types
python3 scripts/cutover_reviewer.py manual.xlsx --sheets checklist,process

# Help
python3 scripts/cutover_reviewer.py --help
```

Supported `--sheets` types: `checklist`, `process`, `rollback`, `domains`, `data_migration`

## Environment Variables (optional)

```bash
export CUTOVER_REVIEWER_OUTPUT_DIR=./output    # default output directory
export CUTOVER_REVIEWER_FORMAT=markdown        # markdown / json / both
```

## Timeout Configuration

The script applies a built-in **60-second timeout** (`LOAD_WORKBOOK_TIMEOUT`) when loading the Excel workbook via `openpyxl.load_workbook()`. This guards against unpredictable execution time caused by very large files or network-mounted paths.

If a timeout occurs:
1. Move the file from a network path (NFS / SMB / cloud drive) to local disk and retry.
2. If the file itself is too large (> 30 MB), consider splitting it into smaller workbooks (one Sheet per file) and reviewing them separately.
3. For environments with slow I/O, set the environment variable `CUTOVER_REVIEWER_LOAD_TIMEOUT` to override the default (in seconds):
   ```bash
   export CUTOVER_REVIEWER_LOAD_TIMEOUT=120
   ```

The overall script execution is expected to complete within 120 seconds for typical cutover manuals (< 50 MB, < 500 rows per Sheet). If total execution exceeds this, interrupt and inspect the file.

## Scoring Bands and Handling Recommendations

| Score | Level | Meaning | Recommended action |
|------|------|------|----------|
| 90-100 | 🟢 Excellent | Plan is complete | Execute after rehearsal |
| 70-89  | 🟡 Good | Basically complete | Execute after adding minor items |
| 50-69  | 🟠 Medium | Significant defects | Must remediate and re-review |
| 0-49   | 🔴 Poor | Severely incomplete | Suspend cutover, remediate comprehensively |

Issue severity labels:
- 🔴 CRITICAL fatal defect (must be resolved, e.g., missing reverse-sync link)
- 🟠 HIGH serious issue (strongly recommended to resolve)
- 🟡 MEDIUM important issue (recommended to resolve to improve quality)
- 🔵 LOW improvement suggestion

## Typical Scenarios

### First review scores very low (30 points)
1. Prioritize resolving all 🔴 CRITICAL items (reverse sync, database read-only, etc.)
2. Fill in the missing check-item categories
3. Assign owners and times
4. Target ≥ 50 on re-review, then iterate to ≥ 70

### Score stuck at 60-70
1. Check whether rollback trigger conditions are quantified (error rate / latency threshold, etc.)
2. Check whether time control is specific (30 minutes, 1 hour)
3. Verify that verification steps and contingency plans are complete

### Can it be executed after 70 points?
- 70 is only the minimum admission bar; ≥ 75-80 is recommended
- You **must** conduct a test-environment rehearsal and organize an expert review meeting
- Prepare a complete contingency plan and a 24h contact list

## Troubleshooting

| Issue | Solution |
|------|----------|
| `command not found: python` | Use `python3`; on Windows install from python.org |
| `ModuleNotFoundError: openpyxl` | `pip install openpyxl==3.1.5`, or `python3 -m pip install openpyxl` |
| Report garbled / Excel read failure | Confirm `.xlsx` format (not `.xls`), file not corrupted; re-save as xlsx in Excel |
| Sheet page not recognized | Rename the Sheet to contain a keyword (checklist, process, rollback, domain, migration), or specify it explicitly with `--sheets` |

## Customizing Review Rules

To extend keywords or add custom rules, edit the constants in `scripts/cutover_reviewer.py`:

```python
ATA_STANDARD_CATEGORIES = [...]      # 6 major check-item categories
CRITICAL_CHECKLIST_ITEMS = [...]     # key check items
CRITICAL_PROCESS_NODES = [...]       # key process nodes
CRITICAL_ROLLBACK_ELEMENTS = [...]   # key rollback elements
REASONABLE_STEP_ORDER = [...]        # reasonable step order
SYNONYM_MAP = {...}                  # Chinese-English synonym extension
```

## Output File Naming Convention

- Markdown: `{original filename}_Review Report_{YYYYMMDD_HHMMSS}.md`
- JSON: `{original filename}_Review Report_{YYYYMMDD_HHMMSS}.json`

The JSON report contains the structured `issues` and `issues_summary` fields, facilitating integration by upstream systems.
