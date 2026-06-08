---
name: alibabacloud-ecs-code-deploy
description: Install Alibaba Cloud CLI (aliyun) and deploy projects to Alibaba Cloud ECS using aliyun appmanager commands. Use when the user wants to deploy applications or AI agents to ECS, set up aliyun CLI, or use appmanager init/deploy/status/delete commands.
---

# Deploy to Alibaba Cloud ECS via aliyun appmanager

## Overview

`aliyun appmanager` is an Agent-friendly CLI tool for one-click deployment of applications (App) and AI Agents to Alibaba Cloud ECS. It supports non-interactive mode (`--non-interactive`), structured JSON output (`--output json`), and streaming NDJSON responses.

**Default behavior**: When user invokes `/alibabacloud-ecs-code-deploy` without specifying a project path or URL, deploy the **current working directory** project to Alibaba Cloud ECS. If user provides a git URL, clone it to the current directory first, then `cd` into the cloned directory and proceed with deployment.

> **EXECUTION ORDER**: The Agent MUST follow the "Complete Deployment Workflow" section at the bottom of this document for the correct execution sequence. The Task sections below are organized by topic for reference — their numbering does NOT imply execution order.

---

## MANDATORY: Create Todo List Before Starting

**Before executing any step**, the Agent MUST create a todo list with ALL of the following items. Do NOT omit any item. Do NOT start deployment until the todo list is created.

```
Todo list (Deploy to Alibaba Cloud ECS):
  [ ] 0. Resolve $SKILL_DIR (cross-platform path — MUST run first; see "Step 0" below)
  [ ] 1. Environment pre-check (MUST run deploy_toolkit.py check; manual commands FORBIDDEN as replacement)
  [ ] 2. Obtain project (clone git URL here if needed; skip for local projects)
  ── Check whether .appmanager/config.yaml already exists (repeat-deploy shortcut) ──
  │  Exists + new ECS (no instanceId)      → skip 3-5, start from 5.5 (price check)
  │  Exists + existing ECS (has instanceId) → skip 3-5.5, jump to 6 (deploy)
  │  Does not exist                        → proceed normally from 3
  ───────────────────────────────────────────────────────────────────────────────
  [ ] 3. Read project (README.md -> quick-deploy method) + identify type (agent / app)
  [ ] 4. Ask user for deployment config (region + new ECS / existing ECS)
  [ ] 5. Init + generate scripts (appmanager init -> write start/stop scripts to config.yaml)
  [ ] 5.5. Pre-deploy price check + risk warning (MUST run deploy_toolkit.py price; confirm price / OSS billing / existing-ECS impact / group overwrite item by item)
  [ ] 6. Deploy (MUST run deploy_toolkit.py deploy; manual deploy command FORBIDDEN as replacement)
  [ ] 7. Verify (MUST run deploy_toolkit.py verify; manual status command FORBIDDEN as replacement)
  [ ] 8. Output final result (console link + cost reminder + management commands)
```

> **⛔ SCRIPT-FIRST RULE**: Steps 1, 5, 6, 7 have a dedicated toolkit script at `$SKILL_DIR/scripts/deploy_toolkit.py` (where `$SKILL_DIR` is resolved in **Step 0** below — works on Qoder, Claude Code, and any other platform). The Agent MUST run the corresponding subcommand DIRECTLY as the FIRST and ONLY action for that step — NEVER run manual CLI commands (like `aliyun version`, version checks, credential checks) BEFORE or INSTEAD of the script. The script already handles ALL checks internally. Manual commands are ONLY allowed as fallback if the script file itself does not exist.
>
> **❌ WRONG (Step 1)**: Run `aliyun version` → check version → run `~/.aliyun/appmanager-venv/bin/python ...` → check version → THEN run `deploy_toolkit.py check`
> **✅ CORRECT (Step 1)**: Run `python3 "$SKILL_DIR/scripts/deploy_toolkit.py" check` → if exit 1, fix the issue it reports → if script file missing, THEN fall back to manual checks

> Item 6 is **NON-NEGOTIABLE**. An Agent that skips log verification and directly outputs "deployment succeeded" has NOT completed this skill correctly. If `deploy_toolkit.py verify` exits 1 (failed), the Agent MUST fix the issue and re-deploy before proceeding to item 7.

---

## Step 0 (MANDATORY): Resolve `$SKILL_DIR` — Cross-Platform Path

> The toolkit script lives at `<skill-root>/scripts/deploy_toolkit.py`. Different platforms install skills to different locations (Qoder/Claude Code/Qwen/...). The Agent MUST resolve the absolute skill root **once** at session start and reuse it everywhere `$SKILL_DIR` appears below. **Hardcoding any platform-specific path is FORBIDDEN.**

**See [references/skill-dir-resolution.md](references/skill-dir-resolution.md) for the full 10-candidate detection algorithm, the `export + test -f` verify snippet, and Pattern A / Pattern B / ⛔ Anti-pattern usage rules.**

Quick recap (read the reference for details):

- ✅ **Pattern A** (persistent shell): `export SKILL_DIR="/abs/path"` then later `python3 "$SKILL_DIR/scripts/deploy_toolkit.py" <sub>`
- ✅ **Pattern B** (fresh shell per call): inline the absolute path — `python3 "/abs/path/scripts/deploy_toolkit.py" <sub>`
- ⛔ **Anti-pattern**: `SKILL_DIR=/path python3 "$SKILL_DIR/..."` — outer shell expands `$SKILL_DIR` BEFORE the prefix assignment, producing `/scripts/deploy_toolkit.py` and ENOENT. If you see `python3: can't open file '/scripts/deploy_toolkit.py'`, switch to Pattern A or B.

---

## Task 1: Install Alibaba Cloud CLI

**Primary action**: Run `python3 "$SKILL_DIR/scripts/deploy_toolkit.py" check` — it checks CLI version + appmanager-cli version + credentials in one run. Only if the script file is missing, use the fallback in [references/init-and-credentials.md](references/init-and-credentials.md).

> **MUST — Handling unmet environment prerequisites**: When `check` exits 1 because the aliyun CLI is missing or older than 3.3.19 (or appmanager-cli is missing/outdated), the Agent **MUST NOT stop the workflow silently**. The required flow is:
> 1. **CLI NOT installed** → **Auto-install directly without asking user** — execute the install command (see snippet below or [references/init-and-credentials.md](references/init-and-credentials.md) for the right arch), then re-run `deploy_toolkit.py check` to confirm.
> 2. **CLI already installed** → **ASK the user first** — show the detected version + the required version + the upgrade command, and ask for explicit consent (e.g. "aliyun CLI 3.3.4 is already installed but below the required >= 3.3.19 for appmanager; approve upgrade (overwrite-install into /usr/local/bin, requires sudo)?"). Never assume yes; never paste credentials.
>    - **On approval** — execute the install/upgrade command, then re-run `deploy_toolkit.py check` to confirm.
>    - **On refusal** — stop with the refusal as the reason. Do NOT continue with the older version (deployment will fail anyway).
>
> The toolkit's `check` output already includes an `→ AGENT: DO NOT stop. ASK user ...` line for each fixable issue — follow it verbatim (except for the "not installed" case, which is auto-handled).
>
> **MUST — Upgrade method priority** (avoid the "repeated upgrade" pitfall: `/usr/local/bin/` is often shadowed by earlier PATH entries like `/opt/homebrew/bin`):
> 1. brew-managed (`check` prints "managed by Homebrew") -> `brew upgrade aliyun-cli`; do NOT overwrite `/usr/local/bin/` again.
> 2. sudo available -> overwrite into `/usr/local/bin/`, then verify: `hash -r && which -a aliyun && aliyun version`.
> 3. No sudo -> install to `~/bin/`, ask user to approve appending `export PATH="$HOME/bin:$PATH"` to `~/.zshrc` / `~/.bashrc`.
>
> After install/upgrade, ALWAYS rerun `deploy_toolkit.py check` to confirm. If `which -a aliyun` still shows the old binary first, fix PATH order — DO NOT repeat the same overwrite.

### AI-Mode Configuration (MANDATORY after CLI install)

> **⛔ MUST configure AI-Mode**: Agent MUST ensure AI-Mode is properly configured before running any `aliyun appmanager` commands. `deploy_toolkit.py check` handles this internally; the commands below are for manual fallback only.

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-code-deploy"
aliyun plugin update
aliyun configure ai-mode show   # verify: enabled=true, user-agent set
aliyun configure ai-mode disable # only when troubleshooting
```

---

## Task 2: Configure Credentials

`deploy_toolkit.py check` already validates credentials. Only if credentials are missing/invalid, see [references/init-and-credentials.md](references/init-and-credentials.md) for the default-credential-chain remediation flow.

> **⛔ PREFER OAuth OVER AK**: This skill SHOULD guide users to use **OAuth authentication** as the PRIMARY method for providing Alibaba Cloud permissions. OAuth is more secure and convenient than AccessKey (no long-term secret storage needed). The Agent MUST present OAuth as the first option before mentioning AK-based methods.
>
> **OAuth Login Guide**: Instruct the user to run the following command in their terminal:
> ```bash
> aliyun configure --mode OAuth --profile oauth
> ```
> This is an interactive command that will:
> 1. Open a browser with an authorization link — user clicks to authorize
> 2. Prompt for region (e.g. `cn-hangzhou`, `cn-beijing`) — user enters their preferred region
> 3. Prompt for language (e.g. `zh`) — user enters their preferred language
>
> After OAuth setup completes, verify with: `aliyun sts get-caller-identity --profile oauth`
>
> **⛔ SA-2.12 — DO NOT explicitly handle AK/SK**: This skill MUST rely on the aliyun CLI/SDK **default credential chain** (OAuth / ECS RAM Role / env vars / pre-existing `~/.aliyun/config.json`). The Agent **NEVER** asks the user to paste AccessKey/Secret/STS-Token values into the chat, **NEVER** puts raw AK/SK in tool-call arguments or scripts, and **NEVER** echoes credential values. When credentials are missing, instruct the user to configure them out-of-band (their own terminal/shell profile/RAM role) and only re-verify via `aliyun sts get-caller-identity`. Full remediation flow → [references/init-and-credentials.md](references/init-and-credentials.md).
>
> **CRITICAL PROHIBITION**: NEVER run standalone `appmanager` or `aliyun appmanager login`.

---

## Task 3: Initialize Project

### Step 1 (MANDATORY): Read README.md FIRST

> **CRITICAL ORDERING RULE**: Before scanning any project files, the Agent MUST read `README.md` (or `README`) in the project root. This is ALWAYS the first action in Task 3.

**What to extract from README:**
- Quick-start / deploy commands (e.g. `pip install -r requirements.txt && python main.py`, `npm install && npm start`)
- Official build/run commands, Docker deploy methods, port number, required environment variables

#### MANDATORY: Present README Methods to User and Follow Decision Tree

**Step A**: List what README provides to the user.

**Step B**: Select method by priority:

| Priority | Method Type | Action |
|----------|------------|--------|
| 1 (HIGHEST) | **Native CLI / package manager install** (`npm install -g`, `pip install`, `go install`) | Use directly |
| 2 | **Native build + run** (`pip install && python main.py`, `npm install && npm start`) | Use, install runtime |
| 3 | **Script-based deploy** (`bash deploy.sh`) | Must confirm non-interactive |
| 4 (LOWEST) | **Docker / docker-compose** | Only when no higher priority exists; check China accessibility |

**Step C**: Execute based on scenario:
- **README has native method (priority 1/2)** → Use it directly as start script core. NEVER ignore README and build from scratch.
- **README only has Docker** → Check image accessibility (see [references/script-templates.md](references/script-templates.md) "Docker Image Accessibility Check"). Warn user about China mirror risks.
- **README has no deploy info / absent** → Agent scans project files independently (only allowed case).

> **Why README first?** Most projects document the exact build/run commands. Auto-detecting from files alone is error-prone.

---

### Step 2: Determine project type

| Condition | Type |
|-----------|------|
| Project depends on `agentscope` | `agent` |
| **Everything else** (langchain, mcp, autogen, web services, tools, etc.) | `app` |

### Determine `--name`

Use the **project directory name** (lowercased, hyphens). Inform user: `Default app name uses the directory name <name>`.

### Determine `--region` and ECS target (MUST ask user)

**Agent MUST ask both questions together in ONE message:**

> **1. Which region do you want to deploy to?**
> - Shanghai (cn-shanghai) / Hangzhou (cn-hangzhou) / Beijing (cn-beijing) / Shenzhen (cn-shenzhen) / Guangzhou (cn-guangzhou) / Chengdu (cn-chengdu) / Nanjing (cn-nanjing) / Hong Kong (cn-hongkong)
>
> **2. New ECS or existing ECS?**
> - New ECS (auto-create instance, pay-as-you-go)
> - Existing ECS (please provide the instance ID, e.g. `i-bp1xxxxxxxx`)

NEVER use zone-based labels like "East China 1" / "North China 2". NEVER add descriptions. City names only.

> ⚠️ **REGION PROPAGATION CHECK** (MANDATORY): The chosen region MUST be passed verbatim to `appmanager init --region`, written into `config.yaml` `common.deployment.regionId`, AND attached as `--region <REGION_ID>` to every subsequent `deploy_toolkit.py {price,deploy,verify}` invocation. Mismatch / omission triggers `InvalidParameter: DeployRegionId is invalid` from the OOS API.

### Determine `--port` (App type only, OPTIONAL)

Only specify when the project actually listens on HTTP. Skip for background services (bots, workers, CLI tools). If needed but unknown, default to `8080`. Agent type does NOT use `--port`.

### Non-interactive init

See [references/init-and-credentials.md](references/init-and-credentials.md) for all init flag combinations.

Creates `.appmanager/config.yaml`. Does NOT support `--overwrite` — delete `.appmanager/` first if exists.

---

## Task 4: Generate Deploy Scripts

For ALL project types, the Agent MUST generate deployment scripts and write them into `.appmanager/config.yaml`.

### Workflow

1. **Read README.md FIRST** — follow Task 3 decision tree
2. **If README has no deploy info** — scan project structure (Language Detection below)
3. **Docker accessibility check** — if Docker path selected (see [references/script-templates.md](references/script-templates.md))
4. **Generate start & stop scripts** — following rules below. Start script MUST ALWAYS include zip extraction sequence.
5. **Write to config.yaml** — under `common.scripts.start` and `common.scripts.stop` (NEVER top-level `scripts`)

### Language Detection Rules

| Indicator Files | Language |
|-----------------|----------|
| `package.json` / `*.js` / `*.ts` | Node.js |
| `requirements.txt` / `pyproject.toml` / `*.py` | Python |
| `pom.xml` / `build.gradle` / `*.java` | Java |
| `go.mod` / `*.go` | Go |
| `composer.json` / `*.php` | PHP |
| `docker-compose.yml` / `Dockerfile` | Docker |

### Files to Read (MUST read content, not just detect presence)

| Language | Must Read | Why |
|----------|-----------|-----|
| Python | `pyproject.toml`, `requirements.txt` | Entry point, deps |
| Node.js | `package.json` | `scripts.start`, `main` field |
| Java | `pom.xml` or `build.gradle` | JAR name |
| Go | `go.mod` | Module → binary name |
| PHP | `composer.json` | Framework detection |
| Docker | `docker-compose.yml` / `Dockerfile` | Services, ports |

### Entry Point Detection Order

- **Python**: `[project.scripts]` in pyproject.toml → `main.py` → `app.py` → `manage.py`
- **Node.js**: `scripts.start` → `main` field → `index.js` → `server.js`
- **Java**: `find ... -name "*.jar" | head -1` → `java -jar`
- **Go**: Pre-compiled binary: `find ... -type f -perm /111`
- **PHP**: `composer install --no-dev` → `php artisan serve` or `php -S`
- **Docker Compose**: `docker compose up -d` / `docker compose down`

### General Script Rules

| Rule | Requirement |
|------|-------------|
| **⛔ MANDATORY zip extract** | Start script MUST: find zip → `mkdir -p` → `unzip -o` → `cd`. Without this, project dir DOES NOT EXIST on ECS |
| **Runtime install** | MUST install language runtime FIRST (ECS is bare) |
| **Install unzip** | `command -v unzip &>/dev/null \|\| $PKG_MGR install -y unzip` |
| **Idempotent** | Safe to run multiple times |
| **⛔ Log file FIXED path** | MUST be `/root/app.log` and `/root/app.pid`. verify script hardcodes these paths |
| **Log append** | Always `>>` (never `>`) |
| **PID file** | `echo $! > /root/app.pid` after `nohup ... &` |
| **Background run** | `nohup ... >> /root/app.log 2>&1 &` |
| **Stop old process** | `[ -f /root/app.pid ] && kill "$(cat /root/app.pid)" 2>/dev/null \|\| true` |
| **App dir** | `/root/{app_name}` |
| **No heredoc** | NEVER use `<< 'EOF'` inside scripts — breaks YAML. Use `printf` or `python3 -c` |
| **MANDATORY tail log** | End with `sleep 3 && cat /root/app.log` for verification capture |
| **⛔ Stop script: NO exit** | MUST NOT contain `exit`. Deploy system concatenates stop+start — exit kills the entire process |

> ECS instances are bare Linux (typically Alibaba Cloud Linux, RHEL-based, uses `yum`/`dnf`).

For script templates, language install commands, and config.yaml writing method, see [references/script-templates.md](references/script-templates.md).

---

## Task 4.5: Pre-deploy Price Check + Risk Warning

> **MANDATORY**: Before deploying, run `deploy_toolkit.py price`. The script outputs the **price estimate (with OSS extra-billing reminder)** and, when applicable, a **risk warning** block. The Agent MUST present every flagged item to the user and obtain explicit confirmation BEFORE running `deploy`.

```bash
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" price --config .appmanager/config.yaml
```

- Exit 0 + `=== AGENT_CONFIRM_REQUIRED ===`: present the **complete** price + risk warning to the user, confirm item by item.
- Exit 1: price query failed; do NOT proceed to deploy.

The Agent MUST confirm up to 3 items (price + OSS fees / existing-ECS risk / group overwrite choice) — see [references/deploy-output-and-management.md](references/deploy-output-and-management.md) § "Pre-deploy Price Check: Confirmation Items" for detailed descriptions and example phrasing.

> Until ALL applicable confirmations are complete, the Agent MUST NOT invoke `deploy_toolkit.py deploy`.

---

## Task 5: Deploy

```
aliyun appmanager <agent|app> deploy --overwrite --output json
```

> **STOP after deploy success** — `status: success` only means orchestration completed. Agent MUST run Task 6 verification before outputting results.

### Handling deployment failure

> ⛔ **MANDATORY FAILURE GATE**: After ANY deploy failure (exit 1, timeout, or `ReleaseCancelled`), the Agent MUST run `deploy_toolkit.py verify` IMMEDIATELY — BEFORE any fix attempt, fallback to manual commands, or partial output. Skipping verify after a failure is **FORBIDDEN** and counts as skill failure.

> **Semantics of `ReleaseCancelled`**: it means the start script on ECS failed or timed out. It does **NOT** mean "someone cancelled the deploy". The only correct next action: run `deploy_toolkit.py verify` -> read the log -> fix the script -> redeploy.

> **Known failure patterns**: Before ad-hoc troubleshooting, check [references/lessons-learned.md](references/lessons-learned.md) for previously identified deployment failure patterns and proven fixes.

**Failure-handling flow:**
1. Run `deploy_toolkit.py verify` to fetch `/root/app.log` (DO NOT skip).
2. Analyze the log to locate root cause.
3. Fix scripts and redeploy (max 3 attempts).
4. After 3 failures, stop — report the error, but still output console link + cost reminder + delete command.

---

## Task 6: Post-deploy Verification (BLOCKING)

> `status: Deployed` does NOT mean the application is running. The Agent MUST run verify and semantically analyze the log.

1. Run `deploy_toolkit.py verify` (auto-reads parameters from config.yaml).
2. Agent semantically analyzes the log to decide whether the application actually started successfully.
3. Not running -> diagnose -> fix -> redeploy + verify (max 3 attempts).
4. Only when running is confirmed / user manual action required / 3 attempts failed should the Agent output the final result.

---

## Task 7 & 8: List, Delete, Validate & Final Output

See [references/deploy-output-and-management.md](references/deploy-output-and-management.md) for:
- List/Delete commands
- Config validation
- Config template reference
- Critical notes & pitfalls
- MANDATORY post-deploy output format (console link, cost reminder, usage guide)

### Pre-output Gate — Self-check (⛔ BLOCKING)

Before outputting results, Agent MUST print the exact `Deployment self-check report` template (see Workflow Step 7.5). **Skipping the report = skill failure** (not an optional summary). If any item is ❌, fix it BEFORE outputting Step 8.

> 📘 Hands-on walk-through with concrete inputs/outputs and edge cases (Python Flask example): see [references/tutorial-flask-app.md](references/tutorial-flask-app.md).

## Complete Deployment Workflow

> **⛔ MANDATORY EXECUTION RULE**: The Agent MUST follow this sequence exactly. For steps that specify a script (steps 1, 5, 6), the Agent MUST run the script — NEVER manually replicate the script's logic with individual commands. The Task sections above are REFERENCE ONLY (for understanding what the scripts do internally or as fallback if scripts are missing).

# 0. Resolve $SKILL_DIR (MANDATORY — see "Step 0" section above for full algorithm)
# → Detect the absolute directory containing THIS SKILL.md (most accurate)
# → Or fall back to platform-specific candidates: ~/.qoder/skills/..., ~/.claude/skills/..., ~/.qwen/skills/..., $SKILLS_HOME/..., etc.
# → Pattern A (persistent shell): export SKILL_DIR=<abs_path> ; verify $SKILL_DIR/scripts/deploy_toolkit.py exists ; reuse $SKILL_DIR everywhere
# → Pattern B (fresh shell per command): inline the absolute path — `python3 "/abs/path/scripts/deploy_toolkit.py" ...`
# → ⛔ NEVER use `SKILL_DIR=/path python3 "$SKILL_DIR/..."` — outer shell expands $SKILL_DIR
#    BEFORE the prefix assignment, producing `/scripts/deploy_toolkit.py` and ENOENT.

# 1. Environment check (MUST use deploy_toolkit.py check — DO NOT run manual commands)
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" check
# ⛔ FORBIDDEN: running `aliyun version`, `~/.aliyun/appmanager-venv/bin/python -c "..."`,
#    credential checks, or ANY manual version-check commands before or instead of this script.
#    The script checks ALL of: CLI version + appmanager-cli version + credentials in one run.
#    Just run the script. Period.
# → If exit 0: all checks passed, proceed to step 2
# → If exit 1, address the issue printed by the script:
#    ⚠️ DO NOT stop silently. For every fixable ❌ line the script prints,
#       Agent MUST follow the flow below:
#       - aliyun CLI NOT installed: AUTO-INSTALL directly (no need to ask user)
#       - aliyun CLI already installed but outdated: ASK user to approve upgrade
#         (covers to /usr/local/bin, needs sudo), then run the install command
#         printed by the script (see Task 1).
#       - appmanager-cli < 1.1.1 or BROKEN venv: ASK user to approve
#         `rm -rf ~/.aliyun/appmanager-venv` (auto-recreates on next aliyun
#         appmanager run).
#         ⚠️ This path is fixed at ~/.aliyun/appmanager-venv (the venv is self-managed
#            by the aliyun CLI). After deletion, the next `aliyun appmanager` run
#            auto-recreates it. The Agent MUST use this exact literal path —
#            NEVER replace it with a variable or build it via concatenation,
#            to avoid accidentally wiping user data.
#       - credentials missing/invalid: present OAuth-first remediation
#         to the user (OAuth / RAM Role / env vars / `aliyun configure` interactive) — NEVER
#         collect AK/SK in chat. See Task 2 + references/init-and-credentials.md.
# → If user refuses any fix: stop with that refusal as the reason — DO NOT
#   continue with a broken environment (deployment will fail anyway).
# → If script file not found: ONLY THEN fall back to manual checks (Task 1 + Task 2)

# 2. Obtain project source (if needed)
# → If git URL provided: clone to CURRENT WORKING DIRECTORY, cd into cloned dir
#    git clone <URL> && cd <cloned_dir>
# → If local path / current directory: skip this step, use directly

# 🔀 REPEAT DEPLOYMENT SHORTCUT — check BEFORE step 3
# → Check if .appmanager/config.yaml already exists in the project directory
# → If YES (config.yaml exists):
#    Read the file and check for common.deployment.instanceId:
#      - instanceId ABSENT (new ECS): skip steps 3-5, jump to step 5.5 (price check)
#      - instanceId PRESENT (existing ECS): skip steps 3-5.5, jump to step 6 (deploy)
#    In both cases, inform user: "Existing .appmanager/config.yaml detected; will reuse the existing config and deploy directly."
# → If NO (config.yaml does NOT exist): proceed normally from step 3

# 3. Read project + identify type (agent or app)
# → READ README.md FIRST — highest priority source for deployment method:
#    - Agent MUST list README's methods to user and select by priority:
#      Native CLI install > Native build+run > Script deploy > Docker
#    - ❌ NEVER ignore README methods and scan project files instead
#    - ❌ NEVER prefer Docker when native methods are available
#    - Docker: ONLY when no native method exists, MUST warn user about China mirror risks
#    - Only if README absent/empty/no deploy info → Agent scans project files independently
# → Only classify as "agent" if project depends on `agentscope`; everything else is "app"
# → Determine --name from directory name, --port from project config/README
# → For Docker: check image accessibility from China (see references/script-templates.md)

# 4. Ask user for deployment region + ECS target (MANDATORY — ask together in one question)
# → Question 1: "Which region do you want to deploy to? Shanghai(cn-shanghai)/Hangzhou(cn-hangzhou)/Beijing(cn-beijing)/Shenzhen(cn-shenzhen)/Guangzhou(cn-guangzhou)..."
# → Question 2: "New ECS or existing ECS?" — for existing, the user must provide the instance ID, e.g. i-bp1xxxxxxxx
# → NEVER use zone-based labels like "East China 1" / "North China 2" — always use city names
# → NEVER skip the ECS choice and default to creating new
# → ⚠️ Region MUST be propagated verbatim to: appmanager init --region, config.yaml common.deployment.regionId, AND every deploy_toolkit.py --region. Mismatch → InvalidParameter: DeployRegionId from OOS API.

# 5. Init + generate scripts (appmanager init → write start/stop to config.yaml)
# → If .appmanager/ already exists in the CURRENT project directory, ask user before removing.
#   ⚠️ DESTRUCTIVE: `rm -rf .appmanager` deletes the existing deployment config.
#      Required guard before deletion:
#        a. Confirm CWD matches the intended project directory (`pwd` shows expected path)
#        b. Confirm target is the relative path `.appmanager` (NEVER absolute, NEVER with variables)
#        c. Inform the user "About to delete the existing deployment config under ./.appmanager/. This is irreversible." and obtain consent
#      Recommended safer alternative: back up first
#        mv .appmanager .appmanager.bak.$(date +%Y%m%d%H%M%S)
#      Only after explicit user consent: rm -rf ./.appmanager
# → Run: aliyun appmanager init --non-interactive --name <DIR_NAME> --type <app|agent> --region <REGION> [--port <PORT>] [--ecs existing --instance-id <ID>] [--model qwen3.6-plus --api-key "$API_KEY"]
#   (See references/init-and-credentials.md for full flag combinations by type)
# → Then generate start/stop scripts and write to config.yaml:
#   - MUST write to common.scripts.start and common.scripts.stop (NEVER top-level scripts key)
#   - Use python3 yaml library: config['common']['scripts'] = {'start': ..., 'stop': ...}
#   - PRIORITY: README deployment commands → use directly; only auto-generate when README has none
#   - ⛔ MANDATORY: Start script MUST ALWAYS include zip extraction (mkdir + unzip + cd) BEFORE
#     any build/run commands. appmanager uploads zip but does NOT extract it.

# 5.5. Pre-deploy price check + risk warning (MUST run deploy_toolkit.py price — Agent handles user confirmation)
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" price --config .appmanager/config.yaml
# → Script output structure:
#    [Price table] estimate from `appmanager price` (order-billed resources: ECS/EIP/bandwidth) + the trailing 📦 OSS extra-billing reminder
#    [Risk warning] only when detected: [Existing-ECS deployment risk] / [Group overwrite risk] / [Failure-leftover group]
# → Script does NOT ask user for confirmation — that's the Agent's job
# → If exit 0: Agent MUST read the output, present the COMPLETE breakdown to user — including:
#    1) Price estimate + OSS extra-billing reminder (OSS storage ~CNY 0.12/GB/month, public outbound ~CNY 0.50/GB only when cross-region, requests billed per 10k)
#    2) If output contains [Existing-ECS deployment risk] -> ask whether to deploy onto that existing ECS (may impact other apps on it)
#    3) If output contains [Group overwrite risk] -> ask user to choose A (overwrite) or B (new group)
#    Example: "Estimated cost: compute resources CNY X.XXX/hour (~CNY XXX.XX/month); public traffic billed by usage at CNY 0.80/GB;
#             the deployment also incurs minor OSS storage and request fees (intra-region pull is free of public outbound charges).
#             Confirm to continue?"
# → After ALL items confirmed by user: run the matching deploy command per item 3's choice (default overwrite / --force-new-group for new group)
# → If ANY item refused: STOP deployment
# → If exit 1: price query failed, show error to user, do NOT proceed

# 6. Deploy (MUST use deploy_toolkit.py deploy — DO NOT run deploy manually)
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" deploy \
  --type <agent|app> --name <APP_NAME> --group <GROUP_NAME> --region <REGION_ID>
# ⛔ FORBIDDEN: running `aliyun appmanager deploy` directly without this script
# → Handles: group status check → conflict auto-resolve → deploy
# → Exit 0: deploy submitted, proceed to step 7
# → Exit 1: ⛔ MUST run step 7 (verify) IMMEDIATELY to fetch /root/app.log;
#           skipping to step 8, outputting partial results, or running manual
#           commands instead is FORBIDDEN. Then fix script per log and redeploy
#           (max 3 attempts).

# 7. Verify (MUST use deploy_toolkit.py verify — DO NOT check status manually)
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" verify \
  --type <agent|app> --name <APP_NAME> --group <GROUP_NAME> --region <REGION_ID>
# ⛔ FORBIDDEN: running `aliyun appmanager status` + manual log analysis instead of this script
# → Optional: --wait <seconds> for slow-starting apps (default 3s, Java/heavy use 15-30)
# → Dual-path: Cloud Assistant cat /root/app.log (preferred) → deployCommandOutput (fallback)
# → Exit 0: app running, proceed to step 8
# → Exit 1: app failed — fix start script, re-deploy (back to step 6)
# → Exit 2: inconclusive — retry with longer --wait or suggest SSH check

# 7.5. Self-check summary (⛔ BLOCKING — skill fails if omitted)
# MUST print the exact template below to the user — this is a completion criterion, NOT optional.
#
# ---
# ✅ Deployment self-check report:
#   0. Path resolution — SKILL_DIR=___ (script exists ✅)
#   1. Environment pre-check — CLI v___ / appmanager-cli v___ / credentials valid ✅
#   2. Project obtained — (local / cloned) ✅
#   3. Project identified — type: ___ / deploy method source: README.md ✅
#   4. Deployment region — user choice: ___ ✅
#   5. Init + scripts — config.yaml generated; start script: ___ (key command summary) ✅
#   5.5. Pre-deploy price check — user confirmed price (CNY ___/hour, ~CNY ___/month) ✅
#   6. Deploy executed — deploy_toolkit.py deploy exit 0 ✅
#   7. Run verification — deploy_toolkit.py verify exit 0 / log keywords: ___ ✅
# ---
#
# If any item is ❌, fix it BEFORE step 8 — this is for the USER to see, proving the work is properly done.

# 8. Output results (MANDATORY: console link + cost reminder + management commands)
# → See references/deploy-output-and-management.md for full output format
