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
待办列表（部署到阿里云 ECS）：
  [ ] 0. 解析 $SKILL_DIR（跨平台路径，必须最先执行 — 见下方 "Step 0" 章节）
  [ ] 1. 环境预检（⚠️ 必须运行 deploy_toolkit.py check，禁止手动执行命令替代）
  [ ] 2. 获取项目（如需克隆 git URL 则在此步执行；本地项目跳过）
  ── 🔀 检查 .appmanager/config.yaml 是否已存在（重复部署快捷路径）──
  │  存在 + 新建ECS（无 instanceId）→ 跳过 3~5，从 5.5 询价开始
  │  存在 + 已有ECS（有 instanceId）→ 跳过 3~5.5，从 6 部署开
  │  不存在 → 正常从 3 开始
  ─────────────────────────────────────────────────────────
  [ ] 3. 读取项目（README.md → 快速部署方案）+ 识别类型（agent / app）
  [ ] 4. 询问用户部署配置（地域 + 新建ECS/已有ECS）
  [ ] 5. 初始化 + 生成脚本（appmanager init → 生成 start/stop 脚本写入 config.yaml）
  [ ] 5.5. 部署前询价（⚠️ 必须运行 deploy_toolkit.py price，用户确认价格后再部署）
  [ ] 6. 部署（⚠️ 必须运行 deploy_toolkit.py deploy，禁止手动执行 deploy 命令替代）
  [ ] 7. 验证（⚠️ 必须运行 deploy_toolkit.py verify，禁止手动执行 status 命令替代）
  [ ] 8. 输出最终结果（控制台链接 + 费用提醒 + 管理命令）
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

> **⚠️ 环境前提不满足时的处置规则（MUST）**: When `check` exits 1 because the aliyun CLI is missing or older than 3.3.14 (or appmanager-cli is missing/outdated), the Agent **MUST NOT stop the workflow silently**. The required flow is:
> 1. **ASK the user first** — show the detected version + the required version + the install/upgrade command, and ask for explicit consent (e.g. "当前 aliyun CLI 版本 3.3.4 低于 appmanager 所需 ≥3.3.14，是否同意升级（覆盖安装到 /usr/local/bin，需要 sudo）？"). Never assume yes; never paste credentials.
> 2. **On approval** — execute the install/upgrade command (see snippet below or [references/init-and-credentials.md](references/init-and-credentials.md) for the right arch), then re-run `deploy_toolkit.py check` to confirm.
> 3. **On refusal** — stop with the refusal as the reason. Do NOT continue with the older version (deployment will fail anyway).
>
> The toolkit's `check` output already includes an `→ AGENT: DO NOT stop. ASK user ...` line for each fixable issue — follow it verbatim.

### AI-Mode Configuration (MANDATORY after CLI install)

> **⛔ MUST configure AI-Mode**: Agent MUST ensure AI-Mode is properly configured before running any `aliyun appmanager` commands. All subsequent `aliyun` CLI calls automatically carry the configured User-Agent header — no per-command `--user-agent` flag needed.

```bash
# 1. Enable AI-Mode (MUST — enables User-Agent tracking in all API calls)
aliyun configure ai-mode enable

# 2. Set User-Agent for skill traceability (MUST — identifies this skill in API logs)
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-code-deploy"

# 3. Update plugins to latest (ensures appmanager subcommand is available)
aliyun plugin update

# 4. Verify AI-Mode status
aliyun configure ai-mode show
# Expected: enabled=true, user-agent=AlibabaCloud-Agent-Skills/alibabacloud-ecs-code-deploy
```

**Disable AI-Mode** (when troubleshooting or if explicitly required):

```bash
# Disable AI-Mode (stops sending User-Agent header; re-enable with 'enable' above)
aliyun configure ai-mode disable
```

> `deploy_toolkit.py check` already handles AI-Mode enable + set-user-agent internally. The above is only needed for manual fallback scenarios.

---

## Task 2: Configure Credentials

`deploy_toolkit.py check` already validates credentials. Only if credentials are missing/invalid, see [references/init-and-credentials.md](references/init-and-credentials.md) for the default-credential-chain remediation flow.

> **⛔ SA-2.12 — DO NOT explicitly handle AK/SK**: This skill MUST rely on the aliyun CLI/SDK **default credential chain** (ECS RAM Role / env vars / pre-existing `~/.aliyun/config.json`). The Agent **NEVER** asks the user to paste AccessKey/Secret/STS-Token values into the chat, **NEVER** puts raw AK/SK in tool-call arguments or scripts, and **NEVER** echoes credential values. When credentials are missing, instruct the user to configure them out-of-band (their own terminal/shell profile/RAM role) and only re-verify via `aliyun sts get-caller-identity`. Full remediation flow → [references/init-and-credentials.md](references/init-and-credentials.md).
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

Use the **project directory name** (lowercased, hyphens). Inform user: "应用名称默认使用目录名 `<name>`"

### Determine `--region` and ECS target (MUST ask user)

**Agent MUST ask both questions together in ONE message:**

> **1. 请问您希望部署到哪个地域？**
> - 上海（cn-shanghai）/ 杭州（cn-hangzhou）/ 北京（cn-beijing）/ 深圳（cn-shenzhen）/ 广州（cn-guangzhou）/ 成都（cn-chengdu）/ 南京（cn-nanjing）/ 香港（cn-hongkong）
>
> **2. 使用新建 ECS 还是已有 ECS？**
> - 新建 ECS（自动创建实例，按量付费）
> - 已有 ECS（请提供实例 ID，如 `i-bp1xxxxxxxx`）

NEVER use "华东1区"/"华北2区". NEVER add descriptions. City names only.

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

## Task 4.5: Pre-deploy Price Check

> **MANDATORY**: Before deploying, run price check and ask user for confirmation.

```bash
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" price --config .appmanager/config.yaml
```

- Exit 0 + `=== AGENT_CONFIRM_REQUIRED ===`: Present COMPLETE cost breakdown to user (fixed hourly + traffic ¥/GB), ask confirmation
- Exit 1: Price query failed, do NOT proceed

Agent MUST present: "预估费用：¥X.XXX/小时（≈¥XXX.XX/月），公网流量按实际使用量另计 ¥0.80/GB。是否确认继续部署？"

---

## Task 5: Deploy

```
aliyun appmanager <agent|app> deploy --overwrite --output json
```

> **STOP after deploy success** — `status: success` only means orchestration completed. Agent MUST run Task 6 verification before outputting results.

### Handling deployment failure

> **⛔ `ReleaseCancelled` 语义**：意味着 start 脚本在 ECS 上执行失败或超时。**不是**"有人取消了部署"。唯一正确动作：运行 `deploy_toolkit.py verify` → 看日志 → 修脚本 → 重新部署。

**失败处理流程：**
1. 运行 `deploy_toolkit.py verify` 获取 `/root/app.log`（禁止跳过）
2. 分析日志定位根因
3. 修复脚本并重新部署（最多 3 次）
4. 3 次失败后停止 — 报告错误，仍输出 console link + cost reminder + delete command

---

## Task 6: Post-deploy Verification (BLOCKING)

> `status: Deployed` 不代表应用在运行。Agent MUST 运行 verify 并语义分析日志。

1. 运行 `deploy_toolkit.py verify`（自动读取 config.yaml 参数）
2. Agent 语义分析日志：判断应用是否真正启动成功
3. 未运行 → 定位原因 → 修复 → 重新部署+验证（最多 3 次）
4. 只有确认运行 / 需用户手动操作 / 3 次修复失败时才能输出最终结果

---

## Task 7 & 8: List, Delete, Validate & Final Output

See [references/deploy-output-and-management.md](references/deploy-output-and-management.md) for:
- List/Delete commands
- Config validation
- Config template reference
- Critical notes & pitfalls
- MANDATORY post-deploy output format (console link, cost reminder, usage guide)

### Pre-output Gate — Self-check (MANDATORY)

Before outputting results, Agent MUST print `✅ 部署自检报告` with all items confirmed. Only proceed when all pass.

---

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
#       Agent MUST first ASK the user for approval, then run the fix.
#       The script outputs an explicit `→ AGENT: DO NOT stop. ASK user ...`
#       hint for each issue — follow it verbatim.
#    - aliyun CLI missing or < 3.3.14: ASK user to approve install/upgrade
#      (covers to /usr/local/bin, needs sudo), then run the install command
#      printed by the script (see Task 1).
#    - appmanager-cli < 1.0.9 or BROKEN venv: ASK user to approve
#      `rm -rf ~/.aliyun/appmanager-venv` (auto-recreates on next aliyun
#      appmanager run).
#      ⚠️ 该路径固定为 ~/.aliyun/appmanager-venv（aliyun CLI 自管理的虚拟环境），
#         删除后 aliyun appmanager 首次运行会自动重建。Agent 必须**逐字使用**此路径，
#         禁止用变量替换或拼接路径，避免误删用户数据。
#    - credentials missing/invalid: present default-credential-chain remediation
#      to the user (RAM Role / env vars / `aliyun configure` interactive) — NEVER
#      collect AK/SK in chat. See Task 2 + references/init-and-credentials.md.
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
#      - instanceId ABSENT (新建 ECS): skip steps 3-5, jump to step 5.5 (price check)
#      - instanceId PRESENT (已有 ECS): skip steps 3-5.5, jump to step 6 (deploy)
#    In both cases, inform user: "检测到已有 .appmanager/config.yaml，将复用现有配置直接部署"
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
# → 问题1: "请问您希望部署到哪个地域？上海(cn-shanghai)/杭州(cn-hangzhou)/北京(cn-beijing)/深圳(cn-shenzhen)/广州(cn-guangzhou)..."
# → 问题2: "使用新建 ECS 还是已有 ECS？" — 已有需提供实例ID如 i-bp1xxxxxxxx
# → NEVER use "华东1区"/"华北2区" — always use city names
# → NEVER skip the ECS choice and default to creating new

# 5. Init + generate scripts (appmanager init → write start/stop to config.yaml)
# → If .appmanager/ already exists in the CURRENT project directory, ask user before removing.
#   ⚠️ DESTRUCTIVE: `rm -rf .appmanager` deletes the existing deployment config.
#      Required guard before deletion:
#        a. Confirm CWD matches the intended project directory (`pwd` shows expected path)
#        b. Confirm target is the relative path `.appmanager` (NEVER absolute, NEVER with variables)
#        c. Inform the user "即将删除 ./.appmanager 目录中的现有部署配置，此操作不可恢复" and obtain consent
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

# 5.5. Pre-deploy price check (MUST run deploy_toolkit.py price — Agent handles user confirmation)
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" price --config .appmanager/config.yaml
# → Script outputs pricing breakdown and exits 0 (success) or 1 (failure)
# → Script does NOT ask user for confirmation — that's the Agent's job
# → If exit 0: Agent MUST read the output, present COMPLETE cost breakdown to user:
#    - Fixed hourly cost: instance + disk (with monthly estimate)
#    - Traffic-based charges: ¥/GB rate — MUST mention explicitly, not omit
#    Example: "预估费用：计算资源 ¥X.XXX/小时（≈¥XXX.XX/月），公网流量按实际使用量另计 ¥0.80/GB。是否确认继续部署？"
# → If user confirms: proceed to step 6
# → If user declines: STOP deployment
# → If exit 1: price query failed, show error to user, do NOT proceed

# 6. Deploy (MUST use deploy_toolkit.py deploy — DO NOT run deploy manually)
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" deploy \
  --type <agent|app> --name <APP_NAME> --group <GROUP_NAME> --region <REGION_ID>
# ⛔ FORBIDDEN: running `aliyun appmanager deploy` directly without this script
# → Handles: group status check → conflict auto-resolve → deploy
# → Exit 0: deploy submitted, proceed to step 7
# → Exit 1: deploy failed, review error, fix, retry

# 7. Verify (MUST use deploy_toolkit.py verify — DO NOT check status manually)
python3 "$SKILL_DIR/scripts/deploy_toolkit.py" verify \
  --type <agent|app> --name <APP_NAME> --group <GROUP_NAME> --region <REGION_ID>
# ⛔ FORBIDDEN: running `aliyun appmanager status` + manual log analysis instead of this script
# → Optional: --wait <seconds> for slow-starting apps (default 3s, Java/heavy use 15-30)
# → Dual-path: Cloud Assistant cat /root/app.log (preferred) → deployCommandOutput (fallback)
# → Exit 0: app running, proceed to step 8
# → Exit 1: app failed — fix start script, re-deploy (back to step 6)
# → Exit 2: inconclusive — retry with longer --wait or suggest SSH check

# 7.5. Self-check summary (MANDATORY — show the user what was done)
# Before outputting final results, the Agent MUST print a summary like this to the user:
#
# ---
# ✅ 部署自检报告：
#   0. 路径解析 — SKILL_DIR=___ (script exists ✅)
#   1. 环境预检 — CLI v___ / appmanager-cli v___ / 凭证有效 ✅
#   2. 获取项目 — (本地/已克隆) ✅
#   3. 项目识别 — 类型: ___ / 部署方案来源: README.md ✅
#   4. 部署地域 — 用户选择: ___ ✅
#   5. 初始化 + 脚本 — config.yaml 已生成，start脚本: ___(关键命令摘要) ✅
#   5.5. 部署前询价 — 用户已确认价格 (¥___/小时, ≈¥___/月) ✅
#   6. 部署执行 — deploy_toolkit.py deploy exit 0 ✅
#   7. 运行验证 — deploy_toolkit.py verify exit 0 / 日志关键词: ___ ✅
# ---
#
# If any item is ❌, the Agent MUST fix it before proceeding to step 8.
# This summary is for the USER to see — it proves the Agent did the work properly.

# 8. Output results (MANDATORY: console link + cost reminder + management commands)
# → See references/deploy-output-and-management.md for full output format
