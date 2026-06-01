---
name: alibabacloud-data-agent-skill
description: |
  Invoke Alibaba Cloud Apsara Data Agent for Analytics via CLI to perform natural language-driven data analysis on enterprise databases.
  Data Agent for Analytics is an intelligent data analysis agent developed by Alibaba Cloud Database team for enterprise users. It automatically completes requirement analysis, data understanding, analysis insights, and report generation based on natural language descriptions.
  This tool supports: discovering data resources (instances/databases/tables) managed in DMS, initiating query or deep analysis sessions, real-time progress tracking, and retrieving analysis conclusions and generated reports.
  Use this Skill when users need to query databases, analyze data trends, generate data reports, ask questions in natural language, or mention "Data Agent", "data analysis", "database query", "SQL analysis", "data insights".
compatibility: |
  Requires Python 3.10+ (macOS system Python is typically too old — use brew or pyenv to install);
  Requires valid Alibaba Cloud credentials (default credential chain or API_KEY);
  Requires dependencies in requirements.txt to be installed inside a venv;
  Data sources must be managed in Alibaba Cloud Apsara Database or DMS.
domain: AIOps
---
metadata:
  author: DataAgent Team
  version: "1.8.5"
---

# Changelog
- **v1.8.5** — Database listing migrated to `ListTagMetaAsset` (dms-enterprise 2018-11-01); workspace auto-resolution (CLI `--workspace-id` > env `DATA_AGENT_WORKSPACE_ID` > `InitDataAgentPersonalWorkspace`); `db` subcommand relaxed `--dms-instance-id` / `--instance-name` to optional.
- **v1.8.4**: Document project Python virtualenv (`venv/`) setup and activation; add end-to-end regression notes for ASK_DATA / ANALYSIS (async + attach)
- **v1.8.3**: `db` and `file` subcommands now accept `--session-mode CLAW`
- **v1.8.2**: `SendChatMessage` now supports per-message `Mode=CLAW` (injected via `SessionConfig.Mode`); dynamic DMSUnit resolution via `GetActiveRouteUnit`
- **v1.8.1**: Emphasize `attach`-based session reuse as the core interaction mechanism; add golden workflow, capability matrix, and usage rules
- **v1.8.0**: Add workspace (collaborative space) support, add custom agent support
- **v1.7.2**: Use Alibaba Cloud default credential chain instead of explicit AK/SK, add User-Agent header, fix RAM policy wildcard issues
- **v1.7.1**: Fix CLI `ls` command API response parsing (support case-insensitive field names), optimize SKILL documentation structure, separate ANALYSIS mode specification document
- **v1.7.0**: API_KEY authentication support, native async execution mode, session isolation, enhanced attach mode, optimized log output

---

---

# Installation

## Python Environment (venv) — MUST READ

> **🚨 Hard Requirement: Python ≥ 3.10**
>
> The macOS system `/usr/bin/python3` is typically 3.8 or 3.9 and **cannot run this project** (it relies on `match/case`, `TypeAlias`, `|` union syntax, and other 3.10+ features).
>
> Verify your version first: `python3 --version`. If below 3.10, install via Homebrew or pyenv:
> ```bash
> # Homebrew
> brew install python@3.12
> # Or pyenv
> pyenv install 3.12.4 && pyenv local 3.12.4
> ```

> **⚠️ You MUST use a venv virtual environment. Never install dependencies globally.** Running `pip install` against the system Python pollutes the environment and may fail due to permission issues.

### Use Existing venv (Recommended)

The project ships a pre-built `venv/` directory (all dependencies pre-installed). Use it whenever possible:

```bash
cd alibabacloud-data-agent-skill

# Option A (recommended): activate the venv
source venv/bin/activate
python3 scripts/data_agent_cli.py ls

# Option B: invoke the venv interpreter directly (no activation needed)
venv/bin/python3 scripts/data_agent_cli.py ls
```

### Rebuild venv

If `venv/` is missing or dependencies are corrupted, recreate with a **3.10+** Python:

```bash
python3.12 -m venv venv          # explicitly use a 3.10+ interpreter
source venv/bin/activate
pip install -r scripts/requirements.txt
```

> **Tip**: All examples in this document write `python3 scripts/data_agent_cli.py ...`. When venv is activated, `python3` resolves to the venv interpreter automatically; otherwise prefix with `venv/bin/python3`.

## Configure Credentials

This Skill uses Alibaba Cloud default credential chain (recommended) or API_KEY authentication.

### Option 1: Default Credential Chain (Recommended)

The Skill uses Alibaba Cloud SDK's default credential chain to automatically obtain credentials, supporting environment variables, configuration files, instance roles, etc.

See [Alibaba Cloud Credential Chain Documentation](https://help.aliyun.com/document_detail/378659.html)

### Option 2: API_KEY Authentication (File Analysis Only)

```bash
export DATA_AGENT_API_KEY=your-api-key
export DATA_AGENT_REGION=cn-hangzhou
```

Get API_KEY: [Data Agent Console](https://agent.dms.aliyun.com/cn-hangzhou/api-key)

### Permission Requirements

RAM users need `AliyunDMSFullAccess` or `AliyunDMSDataAgentFullAccess` permissions.
See [RAM-POLICIES.md](references/RAM-POLICIES.md) for detailed permission information.

## Debug Mode

```bash
DATA_AGENT_DEBUG_API=1 python3 scripts/data_agent_cli.py file example.csv -q "analyze"
```

## 💡 Getting Started Tips

- Use the built-in demo database `internal_data_employees` (DataAgent's built-in test database containing employee, department, and salary data) for first-time experience
- Or use local file `assets/example_game_data.csv` for file analysis experience


# Data Agent CLI — Unified Command-Line Data Analysis Tool

## Overview

`scripts/data_agent_cli.py` helps users complete the full workflow from **discover data → initiate analysis → track progress → get results**.

### Core Concepts

> **⚠️ Key Prerequisite**: Data Agent can only analyze databases that have been **imported into Data Agent Data Center**.
>
> - **Data Center**: Data Agent's data center, only databases here can be analyzed
> - **DMS**: Alibaba Cloud Data Management Service, stores metadata of all databases
> - **Relationship**: Databases registered in DMS ≠ Databases in Data Center
>
> **Usage Flow**:
> 1. First use `ls` to check if the target database exists in Data Center
> 2. If **not found**, use `dms` subcommand to search for database info, then use `import` subcommand to import it
> 3. After successful import, you can use `db` subcommand for analysis

---

## Analysis Modes

- **ASK_DATA** (default): Synchronous execution, sub-second response, suitable for quick Q&A
- **ANALYSIS**: Deep analysis, takes 5-40 minutes, requires spawning a sub-agent for async execution or using --async-run parameter
- **INSIGHT**: Insight-oriented exploration, follows the same plan-confirmation flow as ANALYSIS
- **CLAW**: Agentic CLAW mode. Two entry points:
  - CLI: `db --session-mode CLAW ...` / `file --session-mode CLAW ...` (session-level)
  - SDK: pass `mode="CLAW"` to `client.send_message(...)` / `AsyncDataAgentClient.send_message(...)` to override mode for a single message via `SessionConfig.Mode`

### End-to-End Regression Reference (v1.8.4 verified)

Both ASK_DATA and ANALYSIS modes are regression-tested against `chinook` database with the async + attach flow:

| Mode | Kickoff | Observed Chain | Typical Duration |
|------|---------|----------------|------------------|
| ASK_DATA | `db --session-mode ASK_DATA -q "..."` | async worker → live SSE → `result.json={"status":"completed"}` | ~15s |
| ANALYSIS | `db --session-mode ANALYSIS -q "..."` | async worker → **Plan** → `WAIT_INPUT` → `attach -q "confirm"` → step-by-step execution → Excel/Chart artifacts → text report → **2nd WAIT_INPUT** (webpage render) | 2-10 min (text); +10 min if rendering webpage |

Key checkpoints to look for in `sessions/<SESSION_ID>/progress.log`:

- `> User Query: ...` — request received
- `### Execution Plan (ID: ...)` — ANALYSIS plan generated, use `attach -q "confirm"` to proceed
- `> ⚠️  Plan confirmed, continuing analysis...` — plan approved, execution starts
- `## Step N/M: ...` — per-step progress with artifacts links
- `### Report Render` + `⚠️  Please review the report rendering request.` — optional HTML report render confirmation

> See [ANALYSIS_MODE.md](references/ANALYSIS_MODE.md) for details

---

## Workspace (Collaborative Space)

Workspaces are collaborative spaces that enable team-based data analysis with shared sessions, data sources, and access control.

- **List workspaces**: Use `workspace` subcommand to discover available workspaces (personal or shared)
- **Bind session to workspace**: Pass `--workspace-id <ID>` when using `db` or `file` to create a session within a specific workspace context
- **Workspace types**: `MY` (default, personal spaces), `ALL` (all accessible spaces including shared ones)

> **Note**: When a session is created within a workspace, all subsequent API calls (describe, send message, etc.) automatically carry the workspace context.

### Workspace Resolution

The workspace ID is resolved automatically in this order:
1. CLI flag `--workspace-id <id>`
2. Environment variable `DATA_AGENT_WORKSPACE_ID`
3. Auto-create personal workspace via `InitDataAgentPersonalWorkspace`

Both AK/SK and API_KEY authentication modes support this resolution chain.

---

## Custom Agent

Custom Agents are user-defined AI agents with specialized instructions, knowledge bases, and data scope configurations.

- **List custom agents**: Use `agent` subcommand to discover available custom agents (RELEASED status by default)
- **View agent details**: Use `agent describe --custom-agent-id <ID>` to see full agent configuration
- **Bind session to custom agent**: Pass `--custom-agent-id <ID>` when using `db` or `file` to create a session powered by a specific custom agent

> **Note**: Custom Agent sessions automatically use the `prod` stage. The custom agent's instructions, knowledge, and data scope will be applied to the analysis session.

---

## Session Reuse via `attach` (⭐ Core Mechanism)

> **Best Practice**: `attach` is the **recommended way** to interact with an ongoing or previously created session. Always prefer `attach` over creating a new session for any follow-up interaction on the same data scope.

### Why Use `attach`

After you call `db` / `file` to start a session, **all subsequent interactions on that session MUST go through `attach --session-id <ID>`**. A single session = a single conversation context on the server side, and `attach` is the only way to safely re-enter it.

| Capability | Command | Scenario |
|------------|---------|----------|
| **Follow-up questions** | `attach --session-id <ID> -q "..."` | Continue the conversation with full context, skip data-understanding overhead |
| **Plan confirmation** | `attach --session-id <ID> -q "confirm"` | Approve the execution plan generated by ANALYSIS/INSIGHT mode |
| **Plan modification** | `attach --session-id <ID> -q "simplify to 3 steps"` | Refine the plan before execution |
| **Progress monitoring** | `attach --session-id <ID>` (no `-q`) | Tail live SSE progress of a long-running session |
| **Resume after network drop** | `attach --session-id <ID> --checkpoint <N>` | Precise recovery from the Nth event after interruption |
| **Replay full history** | `attach --session-id <ID> --from-start` | Re-stream the entire session from event 0 |

### Golden Workflow (Async + attach)

The canonical pattern for long-running analyses is **async `db` kickoff → `attach` for everything else**:

```bash
# 1) Kick off async analysis, returns SESSION_ID immediately
python3 scripts/data_agent_cli.py db \
    --dms-db-id <dbId> \
    --db-name <schemaName> \
    --tables "employees,departments" \
    --workspace-id <workspace_id> \
    --session-mode ANALYSIS \
    -q "Analyze salary distribution"
# -> ✅ Async task started. Session ID: abc123xyz

# 2) Watch progress live (Ctrl-C is safe, server keeps running)
python3 scripts/data_agent_cli.py attach --session-id abc123xyz

# 3) Confirm or modify the plan when agent enters WAIT_INPUT
python3 scripts/data_agent_cli.py attach --session-id abc123xyz -q "confirm"

# 4) Ask follow-up questions (reuses context, no re-import, no re-profiling)
python3 scripts/data_agent_cli.py attach --session-id abc123xyz -q "Break down by job level"

# 5) Recover precisely if the stream was cut at event #219
python3 scripts/data_agent_cli.py attach --session-id abc123xyz --checkpoint 219

# 6) Fetch generated reports / charts
python3 scripts/data_agent_cli.py reports --session-id abc123xyz
```

### Benefits of Reusing a Session via `attach`

- **Context preservation** — previous SQL, table profiling, and user intent are kept, answers stay consistent.
- **Cost reduction** — skip re-discovering schema / re-profiling tables on every question.
- **Plan governance** — ANALYSIS / INSIGHT plans require explicit confirmation; only `attach -q "confirm"` can unblock them.
- **Resilience** — `--checkpoint` / `--from-start` make long-running tasks robust against network drops and client restarts.
- **Team collaboration** — share the Session ID, teammates can `attach` to the same session to review progress and results.

### Rules of Thumb

1. Create session **once** with `db` / `file`; drive everything else with `attach`.
2. Record the `Session ID` printed after kickoff — it is the only handle to the session.
3. For ANALYSIS / INSIGHT mode, always use `attach` (not a new `db`) to confirm plans; creating a new session loses the plan.
4. Session artifacts (progress log, checkpoint, result, images) are persisted under `sessions/<SESSION_ID>/`.

> See [COMMANDS.md](references/COMMANDS.md) for the full `attach` parameter list and [WORKFLOWS.md](references/WORKFLOWS.md) for end-to-end scenarios.

---

## Quick Start

```bash
# 1. List available databases
python3 scripts/data_agent_cli.py ls
# Example output:
#   chinook [mysql]  dbId=abc123  instanceResourceId=rm-xxx  catalogName=chinook
#   employees [mysql]  dbId=def456  instanceResourceId=rm-yyy  catalogName=employees

# 2. Create a session for initial analysis (record the returned Session ID!)
python3 scripts/data_agent_cli.py db \
    --dms-db-id <dbId> \
    --db-name <schemaName> \
    --tables <table1,table2> \
    --workspace-id <workspace_id> \
    -q "Which department has the highest average salary"
# -> ✅ Async task started. Session ID: abc123xyz

# 3. ⭐ Reuse the session — follow-up questions, confirm plans, monitor progress
python3 scripts/data_agent_cli.py attach --session-id abc123xyz -q "Break down by month"
python3 scripts/data_agent_cli.py attach --session-id abc123xyz -q "confirm"     # approve ANALYSIS plan
python3 scripts/data_agent_cli.py attach --session-id abc123xyz                  # tail live progress
python3 scripts/data_agent_cli.py attach --session-id abc123xyz --checkpoint 219 # resume after drop

# 4. List workspaces
python3 scripts/data_agent_cli.py workspace

# 5. Query in a specific workspace
python3 scripts/data_agent_cli.py db \
    --workspace-id <WORKSPACE_ID> \
    --dms-db-id <dbId> \
    --db-name <schemaName> \
    --tables <table1,table2> -q "Which department has the highest average salary"

# 6. List available custom agents
python3 scripts/data_agent_cli.py agent

# 7. Use a custom agent for analysis
python3 scripts/data_agent_cli.py db --custom-agent-id <AGENT_ID> --dms-instance-id ... -q "your question"
```

> **Remember**: `db` / `file` create the session **once**; all follow-ups go through `attach --session-id <ID>`.

> 📖 See [WORKFLOWS.md](references/WORKFLOWS.md) and [COMMANDS.md](references/COMMANDS.md) for complete workflows, command reference, and best practices

---

## Project Structure

```
                          # Skill root directory
├── SKILL.md              # This document
├── scripts/              # Source code
│   ├── data_agent/       # SDK module
│   ├── cli/              # CLI module
│   ├── data_agent_cli.py # CLI entry point
│   └── requirements.txt  # Dependencies
├── sessions/             # Session data
└── references/           # Reference documents
```
