---
name: alibabacloud-migration-dbm-redis-shake-migration
description: 端到端管理 RedisShake 数据迁移任务：从用户提供的 Excel 表格、文本描述或逐项问答中提取迁移信息，生成 shake.toml 配置文件，并在本地或通过 SSH 远程部署、启动、停止、监控迁移任务。当用户需要配置 Redis 迁移/同步、提供了含 Redis 地址密码等信息的文本/表格、需要启动或管理 RedisShake 任务、或通过 SSH 远程操作服务器时触发。本 skill 不适用于：MongoDB/MySQL/ES 等非 Redis 数据迁移、Redis 内存 dump 备份、集群拓扑改造、未提供 SSH 凭证的远程操作；本 skill 不验证迁移后的数据一致性（推荐使用redis-full-check进行校验），仅在已部署 redis-shake 二进制的 Linux 服务器上运行。
---

# RedisShake Migration Task Management

> This skill works well on Agent platforms that support Bash/Shell tools (Qoder, Claude Code, Cursor, etc.); it does not support browser-only Agents.

End-to-end workflow: collect info -> generate config -> deploy to server -> start running -> monitor progress

> **User-facing language**: Communicate with the user in their language (Chinese by default for this skill). All user-facing templates in this document (e.g., confirmation prompts, clarification lists, authorization recitations) are written in English for reference - when presenting them to the user, render them in the user's language.

## Prerequisites

### Local machine (the machine running the Agent)
- bash 4+
- OpenSSH client (ssh / scp / ssh-copy-id)
- tar, sha256sum

### Target server
- Linux x86_64 (glibc >= 2.17)
- bash 4+
- Optional: systemd (production mode)

### Troubleshooting and verification tools (as needed)
- redis-cli (data sampling before/after migration)
- python3 >= 3.11 (tomllib module, for validating toml syntax)

### Optional hardening
- envsubst (from the gettext package, used by the credential-hardening approach)

---

## ReAct Execution Rules

- **Max tool calls**: 10 (migration tasks involve multiple steps; when exceeded, report to the user and ask whether to continue)
- **SSH connection failure retries**: at most 2; if it still fails, stop and output the error log for the user to troubleshoot
- **Config validation failure**: do not retry; return the specific offending field and correction advice directly
- **Repeated commands**: stop after the same command fails twice in a row; do not auto-retry further

---

## Entry Routing: jump by user intent

Determine which stage is needed based on the user input. **Every stage is optional and can run independently:**

| User intent | Jump to stage |
|---------|----------|
| Provided migration info (address/password/mode, etc.), needs config generation | -> Stages 1-3 |
| Already has shake.toml, needs deploy/start | -> Stages 4-5 |
| Task already running, needs status/logs/progress | -> Stages 5-6 |
| Needs to stop/restart the task | -> Stage 5 |
| Encountered a problem, needs troubleshooting | -> Troubleshooting |
| Full end-to-end flow (from scratch) | -> Stages 1-6 in order |

> Important: Do not assume the user must start from Stage 1. If the user says "start redis-shake", go straight to Stage 5; if the user says "check migration progress", go straight to Stage 6.

---

## Network Access Scope

| Type | Scope | Notes |
|------|------|------|
| SSH remote access | User-specified server IP:Port | Requires user-provided credentials |
| HTTP local access | `localhost:{status_port}/metrics` | RedisShake built-in monitoring port |
| SSH port forwarding | Local port -> remote localhost:8080 | Optional, used for remote monitoring |
| Redis connection | User-provided source/target Redis address | Only for redis-cli sampling verification |

### Basis for Network Access Authorization

This skill's network access does **not** include any proactive access to preset fixed domains/IPs. All outbound connections satisfy the following three conditions, which constitute the user's explicit authorization:

1. **User-initiated input**: Target addresses (SSH server IP, Redis host:port) are 100% provided by the user proactively in the conversation. The skill itself carries no built-in address or default server.
2. **Confirm before operating**: Before performing an SSH connection, Redis connection, or sudo operation, the Agent must recite the target address to the user and obtain confirmation (backstopped by the `scripts/confirm-write.sh` Hook).
3. **Single access purpose**: Used only for RedisShake migration task deployment, start/stop, status queries, and sampling verification - no data exfiltration, no port scanning, and no network activity beyond DNS resolution.

### Network access NOT involved

- This skill **does not access** any public domain (excluding cloud OpenAPI, GitHub, package registries).
- This skill **does not upload** any credentials, configs, or logs to external systems.
- Binary downloads are done manually by the user from the RedisShake official page; the skill does not proxy downloads.

> Compliance basis: This skill follows the least-privilege principle of "user explicitly provided = authorized" and does not extend access scope to targets the user did not specify. This constraint is cross-verified in three places: SKILL.md, the Hook script, and the Stage 5 runtime recitation.

## Required Permissions (grouped by operation type)

### Read operations (least privilege, no confirmation needed)
- SSH user's read access to `/opt/redis-shake/`
- Commands: `tail`, `ps`, `grep`, `cat` (read-only), `curl`, `redis-cli ping/get`

### Write operations (require explicit user confirmation)
- SSH user's write access to `/opt/redis-shake/`
- Create/overwrite `shake.toml`, `data/shake.pid`, `data/shake.log`
- Kill the **own** redis-shake process (via the PID file)
- Use of the SSH private key (`~/.ssh/id_rsa` or a user-specified path, key-auth mode only)

### sudo permissions (only needed for systemd production mode)
- Write `/etc/systemd/system/redis-shake.service`
- Run `systemctl daemon-reload / enable / start / stop`

> Before performing any SSH connection, sudo operation, file write, or process kill, the Agent must clearly explain the operation about to be performed and obtain confirmation. This Skill has a PreToolUse Hook (`scripts/confirm-write.sh`) configured to automatically intercept write-type commands.

---

## Stage 1: Collect Migration Info

### Prerequisite permission check

| Reader mode | Required source-side permission |
|-------------|-------------|
| `sync_reader` | PSYNC / REPLCONF (usually unsupported on managed cloud) |
| `scan_reader` | SCAN, DUMP, TTL, TYPE |
| `scan_reader` + `ksn=true` | The above + keyspace notifications enabled |
| `rdb_reader` / `aof_reader` | None (local files) |

### Input methods

**Method 1: Excel table** - field recognition rules:
- `host:port` -> address
- account:password or a plain string -> password
- sync / scan / rdb / aof -> mode
- cluster / TLS / db / prefix -> corresponding option

**Method 2: Natural-language description** - mapping rules:
- Real-time sync / zero downtime -> sync_reader
- One-time migration / full -> scan_reader
- Alibaba Cloud / cloud Redis -> scan_reader (does not support PSYNC)
- Incremental / listen for new writes -> ksn = true
- Do not overwrite / skip -> rdb_restore_command_behavior = "skip"
- Overwrite / newest wins -> rdb_restore_command_behavior = "rewrite"
- Rate limit / protect target -> lower target_redis_max_qps
- Read from replica -> prefer_replica = true

### Validation rules

| Field | Validation | Error message |
|------|------|----------|
| Address | `host:port`, port in 1-65535 | "Please provide host:port format" |
| Address (boundary) | Reject `localhost:0` / `0.0.0.0:0` / port <= 0 | "Invalid address" |
| Password | Any non-empty string; `无`/`none`/`-`/`空` -> treated as no password | - |
| Password (boundary) | Length <= 1024 chars, ASCII printable characters only | "Password too long or contains illegal characters" |
| Mode | sync / scan / rdb / aof | "Invalid mode, please choose a valid value" |
| File path | Absolute path (starts with `/`) | "Please provide an absolute path" |

### Clarification format

List recognized info ([OK]) and items needing confirmation/correction ([!]) all at once - do not ask in multiple separate rounds.

Required fields: source address, source password, target address, target password, Reader mode
Optional fields: cluster, TLS, key filtering, DB range, conflict policy, rate limit, empty target

> **Warning**: **High-risk option**: If the user mentions "empty the target" (`empty_db_before_sync = true`), you must explicitly confirm twice:
> "Are you sure you want to empty all data on the target before syncing? This operation is irreversible and all existing data on the target will be lost. Please type YES to confirm."

---

## Stage 2: Choose Reader Mode

Quick reference:
- Self-hosted Redis, zero downtime -> `sync_reader`, sync_rdb=true, sync_aof=true
- Self-hosted Redis, full only -> `sync_reader`, sync_aof=false
- Managed cloud, one-time full -> `scan_reader`, ksn=false
- Managed cloud, continuous incremental -> `scan_reader`, ksn=true
- Alibaba Cloud Tair / ElastiCache -> must use `scan_reader`
- RDB file restore -> `rdb_reader`
- AOF file replay -> `aof_reader`

See [reader-modes.md](references/reader-modes.md) for the detailed decision tree and parameter descriptions.

---

## Stage 3: Generate the Config File

After confirming the info, output the complete `shake.toml`:
1. Output the full code block, with a comment for each item
2. Provide the save command: `cat > /opt/redis-shake/shake.toml << 'EOF'`
3. Security notice (see below)

### Output security requirements

```
Warning: Passwords are stored in cleartext in shake.toml. After saving, run:
chmod 600 /opt/redis-shake/shake.toml
Make sure not to commit to Git (add shake.toml to .gitignore)
```

**Masking rule** (mandatory): Before displaying shake.toml content in the conversation, you **must** first apply a regex replacement to password fields:

```bash
# For display only (first 2 chars + ***); the actual on-disk file still uses the full password
sed -E 's/(password[[:space:]]*=[[:space:]]*")([^"]{0,2})[^"]*"/\1\2***"/g' shake.toml
```

- Conversation display: `password = "ab***"` (shows only the first 2 chars + `***`)
- The save command (`cat > ... << EOF`) uses the full password
- Must include the notice: "The config contains a cleartext password. Please copy the command directly into your terminal to run it - do not screenshot or share the conversation content."

**Parameter security requirements** (prevent command injection):
- The password is written only into the shake.toml file; it **must not** appear in Shell command arguments
- All user-provided variables (HOST/USER/paths) in Shell commands must be wrapped in single quotes
- If the password contains a `"` character, escape it as `\"` in TOML; if it contains `\`, escape as `\\`
- Do not concatenate user input into Shell commands using double quotes or backticks

**Credential-hardening approach** (optional, recommended):
```bash
# Approach: use envsubst to avoid hard-coding the password in the file
export REDIS_SRC_PASS='actual password'
export REDIS_DST_PASS='actual password'
envsubst < shake.toml.tpl > shake.toml && chmod 600 shake.toml
# In shake.toml.tpl write: password = "${REDIS_SRC_PASS}"
```
> Note: This approach requires installing envsubst (the gettext package) and suits environments with higher security requirements.
> The default approach (chmod 600) is suitable for closed intranet environments.

See [templates.md](references/templates.md) for config templates.

### Alibaba Cloud Redis special handling
- Address contains `aliyuncs.com` -> force scan_reader
- Password format `account:password` -> fill the whole thing into password
- Incremental -> enable keyspace notifications in the console first

---

## Stage 4: Deploy to Server

### Obtain the redis-shake binary

If redis-shake is not yet installed on the server:

> Please download the file for your platform from the RedisShake official page.
>
> After downloading, verify file integrity (compare against the SHA256 value on the Release page):
> ```bash
> sha256sum redis-shake-linux-amd64.tar.gz
> ```
>
> Extract and deploy to the target path:
> ```bash
> tar -xzf redis-shake-linux-amd64.tar.gz
> mv redis-shake /opt/redis-shake/redis-shake
> chmod +x /opt/redis-shake/redis-shake
> mkdir -p /opt/redis-shake/data
> ```

### Confirm the execution environment

- **Local execution**: already logged into the server, run commands directly
- **Remote execution**: operate via SSH -> must confirm: username, server IP, SSH port, authentication method

Default deployment paths:
- Binary: `/opt/redis-shake/redis-shake`
- Config: `/opt/redis-shake/shake.toml`
- Logs: `/opt/redis-shake/data/`

### Upload the config (remote mode)

```bash
scp -o ConnectTimeout=10 shake.toml USER@HOST:/opt/redis-shake/shake.toml
ssh -o ConnectTimeout=10 -o ServerAliveInterval=30 USER@HOST 'chmod 600 /opt/redis-shake/shake.toml'
```

See [remote-ssh.md](references/remote-ssh.md) for detailed remote-mode commands.

---

## Stage 5: Start and Manage

> Using the bundled scripts is recommended (they have idempotency checks and error handling built in). The scripts are located at `${SKILL_ROOT}/scripts/`; you can first copy them to the target server, then call them with the commands below.

### Network Connection Authorization Recitation (mandatory)

Before running any SSH remote command (start/stop/restart/kill/systemctl) or sudo operation, the Agent **must** first output the following authorization recitation and wait for the user's explicit confirmation (type YES):

```
[Network Access Authorization Confirmation]
Target address: <HOST:PORT>
Access method: SSH remote execution / local Bash
Access purpose: <specific operation, e.g., "start redis-shake", "stop the process and clean up PID">
Data direction: local <- target server only (no data uploaded to any third party)
Privilege level: user-mode / sudo (systemd scenario)

Proceed? (YES/NO)
```

> Applicable scope: SSH connections, scp uploads, sudo commands, kill process, systemctl start/stop. Purely local read-only queries (e.g., viewing local logs) do not require recitation.

### Start

```bash
bash ${SKILL_ROOT}/scripts/start.sh /opt/redis-shake
```

Equivalent inline command (for scenarios where the scripts cannot be pre-placed):

```bash
cd /opt/redis-shake && mkdir -p data
if [ -f data/shake.pid ] && kill -0 $(cat data/shake.pid) 2>/dev/null; then
    echo "Already running, PID: $(cat data/shake.pid)"; exit 1
fi
nohup ./redis-shake shake.toml > data/shake.log 2>&1 &
echo $! > data/shake.pid && echo "Started, PID: $(cat data/shake.pid)"
```

### Stop

```bash
bash ${SKILL_ROOT}/scripts/stop.sh /opt/redis-shake
```

### Check status

```bash
bash ${SKILL_ROOT}/scripts/status.sh /opt/redis-shake
```

### View logs

```bash
# Follow in real time (auto-exit after 60s timeout, adjust as needed)
timeout 60 tail -f /opt/redis-shake/data/shake.log

# View the latest key metrics
grep -E "entries|qps|rdb|aof|error|ERR" /opt/redis-shake/data/shake.log | tail -30
```

### Restart

```bash
bash ${SKILL_ROOT}/scripts/stop.sh /opt/redis-shake && sleep 2 && bash ${SKILL_ROOT}/scripts/start.sh /opt/redis-shake
```

### systemd (recommended for production)

> **Warning**: Requires sudo permissions

```bash
sudo bash -c 'cat > /etc/systemd/system/redis-shake.service << "EOF"
[Unit]
Description=RedisShake Data Migration
After=network.target
[Service]
Type=simple
WorkingDirectory=/opt/redis-shake
ExecStart=/opt/redis-shake/redis-shake shake.toml
Restart=on-failure
RestartSec=5s
StandardOutput=append:/opt/redis-shake/data/shake.log
StandardError=append:/opt/redis-shake/data/shake.log
[Install]
WantedBy=multi-user.target
EOF'
sudo systemctl daemon-reload && sudo systemctl enable redis-shake && sudo systemctl start redis-shake
```

---

## Stage 6: Migration Progress Monitoring

### Completion signals

| Stage | Completion signal |
|------|---------|
| RDB full | Log shows `rdb done` / `finished` |
| AOF incremental | QPS continuously approaches 0 |
| scan full | `scan finish`; with ksn=false it exits automatically |

```bash
watch -n 5 "grep -E 'entries|qps|rdb|aof' /opt/redis-shake/data/shake.log | tail -5"
```

### HTTP monitoring

```bash
# shake.toml: [advanced] status_port = 8080
curl http://localhost:8080/metrics
```

### Completion checklist

```
[ ] No ERROR / PANIC in the log
[ ] Source and target dbsize match
[ ] Sampling verification: redis-cli -h TARGET get SOME_KEY
[ ] sync mode: aof_qps < 10 indicates the incremental has caught up
[ ] scan mode: exited (ksn=false) or continuously listening (ksn=true)
```

---

## Error Feedback Format

On failure, output uniformly in the following three-part structure so the user can locate issues quickly:

```
[Failure reason] The specific error log snippet or field
[Suggested action] Optional fix command or config adjustment
[Retryable] Yes / No + condition (e.g., "retry after modifying the config")
```

## Troubleshooting

| Symptom | Investigation |
|------|------|
| Exits after start | `tail -50 data/shake.log` |
| Config file syntax error | Log reports a `toml: ...` error -> validate with `cat shake.toml \| python3 -c "import tomllib,sys;tomllib.loads(sys.stdin.read())"`, or check quotes/indentation |
| Connection failure | `redis-cli -h HOST -p PORT -a PASS ping` |
| Target busy | Change `rdb_restore_command_behavior` to rewrite/skip |
| Slow speed | Increase `pipeline_count_limit`, check `target_redis_max_qps` |
| Process exits | Switch to systemd for auto-restart |
| Insufficient systemd permissions | Add sudo |
| SSH remote issues | See [remote-ssh.md](references/remote-ssh.md) |

---

## Multi-task Management

Each task has an independent config; set `[advanced] dir` to a different path:

```bash
nohup ./redis-shake task1.toml > data/task1/shake.log 2>&1 &
nohup ./redis-shake task2.toml > data/task2/shake.log 2>&1 &
```

---

## Disclaimer

- The migration configs and commands output by this skill are for reference only; have a DBA review them before running in production.
- All credentials are used only in the local conversation and config files and are not uploaded to external systems.
- Migration results require manual verification (use redis-cli to sample-check dbsize and key content); this skill takes no responsibility for data consistency/integrity.
- Using systemd or sudo commands modifies system configuration; confirm permissions and validate in a test environment first.
