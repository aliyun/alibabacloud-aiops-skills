# Acceptance Criteria

This document contains CORRECT and INCORRECT examples for the `alibabacloud-rds-postgresql-inspection` skill.

---

## CORRECT Examples

### 1. CLI Command with User-Agent

```bash
# CORRECT: Include --user-agent with complete format
aliyun rds describe-db-instances \
  --region cn-hangzhou \
  --engine PostgreSQL \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection/{session-id}
```

### 2. Script Execution with Session-ID

```bash
# CORRECT: Pass session-id via environment variable
SKILL_SESSION_ID=abc123def456... python3 scripts/inspect.py --all
```

### 3. Local Commands (No User-Agent)

```bash
# CORRECT: Local commands do NOT need --user-agent
aliyun version
aliyun configure list
aliyun plugin update
```

### 4. Read-Only Operations

```bash
# CORRECT: Only use read-only API actions
aliyun rds describe-db-instances
aliyun rds describe-db-instance-attribute
aliyun cms describe-metric-list
```

### 5. Plugin Installation Syntax

```bash
# CORRECT: Use --name flag (CLI 3.3.16+)
aliyun plugin install --name aliyun-cli-rds
aliyun plugin install --name aliyun-cli-cms
```

---

## INCORRECT Examples

### 1. Missing Session-ID in User-Agent

```bash
# INCORRECT: Missing /{session-id} segment
aliyun rds describe-db-instances \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rds-postgresql-inspection
```

### 2. Using Deprecated AI-Mode

```bash
# INCORRECT: AI-Mode is deprecated, do NOT use
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "..."
export ALIBABA_CLOUD_USER_AGENT="..."
```

### 3. Adding User-Agent to Local Commands

```bash
# INCORRECT: Local commands don't support --user-agent
aliyun version --user-agent AlibabaCloud-Agent-Skills/...
aliyun configure list --user-agent AlibabaCloud-Agent-Skills/...
```

### 4. Using --header for User-Agent

```bash
# INCORRECT: --header does NOT work for User-Agent in aliyun CLI
aliyun rds describe-db-instances --header "User-Agent=AlibabaCloud-Agent-Skills/..."
```

### 5. Incomplete User-Agent Format

```bash
# INCORRECT: Missing /alibabacloud-rds-postgresql-inspection/{session-id}
aliyun rds describe-db-instances --user-agent AlibabaCloud-Agent-Skills
```

### 6. Plugin Installation with Positional Argument

```bash
# INCORRECT: CLI 3.3.16+ requires --name flag
aliyun plugin install aliyun-cli-rds
```

### 7. Mutating Operations

```bash
# INCORRECT: This is a read-only inspection skill
aliyun rds modify-db-instance-spec  # FORBIDDEN
aliyun rds delete-database          # FORBIDDEN
```

---

## Verification Checklist

Before considering the skill complete, verify:

- [ ] All `aliyun` CLI commands include `--user-agent` with complete format
- [ ] Session-ID is generated (32-char lowercase hex) at skill load
- [ ] Local commands (configure, version, plugin) do NOT include `--user-agent`
- [ ] No deprecated AI-Mode commands are used
- [ ] Script reads `SKILL_SESSION_ID` from environment variable
- [ ] Plugin pre-installation uses `--name` flag
- [ ] Only read-only API actions are in the whitelist
