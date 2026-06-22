---
name: alibabacloud-history-lock-diagnose
description: |
  Alibaba Cloud PolarDB/RDS MySQL historical lock wait root cause analysis skill.
  Diagnoses and analyzes historical lock wait issues, identifies the complete lock chain and lock holder.
  Triggers: lock diagnosis, lock wait troubleshooting, deadlock analysis, PolarDB lock issue, RDS lock issue,
  lock wait timeout, transaction blocking, metadata lock wait, InnoDB lock analysis, database lock troubleshooting,
  MySQL lock wait, database performance troubleshooting, lock conflict analysis.
  Use when the user mentions database lock, deadlock, lock wait, transaction blocking, or slow queries related to locks.
---

# Alibaba Cloud Historical Lock Wait Diagnosis

Diagnose historical lock wait issues on PolarDB MySQL and RDS MySQL instances. Identifies the root cause, complete lock chain, and lock holder.

**Architecture:** PolarDB/RDS MySQL + DAS (Database Autonomy Service) + Aliyun CLI

**Supported lock types:** InnoDB row locks (Record/Gap/Next-Key), MDL (Metadata Lock), Table Lock, Deadlock, FLUSH cascading, AUTO-INC Lock

---

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command that calls a cloud API must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}`
(See Observability section below for session-id generation)

**Runtime Requirements:**
- Python >= 3.7 (standard library only)
- Aliyun CLI >= 3.3.3

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**

---

## RAM Policy

Required permissions: hdm:GetDasSQLLogHotData, hdm:GetDeadLockHistory, hdm:GetDeadLockDetail, hdm:CreateLatestDeadLockAnalysis, hdm:DescribeSqlLogConfig, hdm:GetMySQLAllSessionAsync

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors:
> 1. Read `references/ram-policies.md` for the full permission list
> 2. Use `ram-permission-diagnose` skill to guide the user
> 3. Pause and wait until permissions are granted

---

## Parameter Confirmation

> **IMPORTANT:** ALL parameters MUST be confirmed with the user before execution.

| Parameter | Required | Description |
|-----------|----------|-------------|
| InstanceId | Yes | RDS (rm-xxx) or PolarDB (pc-xxx) |
| ProblemTime | Yes | Lock wait time (e.g. `2026-06-08 17:02:35.894`) |
| ThreadID | Yes | Blocked thread ID |
| BlockedSQL | Yes | Blocked SQL statement |

---

## Core Workflow

### Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include `--user-agent`.**
Local commands (`configure`, `plugin`, `version`) do not support this flag.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-history-lock-diagnose/{session-id}
```

### Step 1: Environment Check

```bash
aliyun version
aliyun configure list
```

### Step 2: Run Diagnosis Script

> **[MUST] Execute the script directly with the command below.**
> **Do NOT read `scripts/smart-lock-diagnosis.py` — it is 3700+ lines and reading it will waste context and slow down execution.**
> The script handles everything internally: SQL audit query, lock type detection, blocking chain analysis, deadlock diagnosis, and report generation.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/smart-lock-diagnosis.py \
  --instance-id {InstanceId} \
  --time "{ProblemTime}" \
  --thread-id {ThreadID} \
  --sql "{BlockedSQL}"
```

The script automatically:
1. Checks SQL Insight config (hot data availability)
2. Queries SQL audit records with smart time ranges
3. Detects lock type (InnoDB row lock / MDL / Deadlock / FLUSH / Gap Lock etc.)
4. Identifies lock holder thread via time overlap analysis
5. Outputs structured diagnosis report with blocking chain

### Step 3: Present Diagnosis Report

Extract the key findings from the script output and present to the user:

1. **Lock holder thread** — who holds the lock and what SQL was executed
2. **Blocking chain** — the wait relationship (A blocks B blocks C...)
3. **Lock type** — Record Lock / Gap Lock / MDL Lock / Deadlock / Flush Lock etc.
4. **Transaction timeline** — lock holder's BEGIN → DML → (uncommitted)
5. **Recommendations** — based on actual SQL content (shorten transactions, add indexes, etc.)

**Key requirements:**
- Do NOT paste the full raw script output — extract and summarize key information only
- Timestamps must include milliseconds (e.g., `10:39:28.390`)
- Recommendations must be based strictly on actual SQL content observed

---

## Notes

- The instance must have **SQL Insight (SQL Audit)** enabled
- **Hot data**: `GetDasSQLLogHotData` retention depends on instance config (check `HotRetention` field). Data outside retention window may be unavailable
- Deadlock analysis (`GetDeadLockHistory`) can query historical records beyond hot data window
- This skill does not modify any user data or instance configurations. `CreateLatestDeadLockAnalysis` triggers DAS server-side deadlock parsing (classified as Write) but does not alter the database

---

## Cleanup

This is a diagnostic skill. No user resources are created or modified; no cleanup required.

---

## Reference Links

| Reference File | Description |
|---------------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policy list |
| [references/related-commands.md](references/related-commands.md) | CLI command reference |
| [references/best-practices.md](references/best-practices.md) | Diagnosis best practices and known limitations |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria and anti-patterns |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/transaction-lifecycle.md](references/transaction-lifecycle.md) | Transaction lifecycle rules |
| [references/verification-method.md](references/verification-method.md) | Verification methods and checklist |
