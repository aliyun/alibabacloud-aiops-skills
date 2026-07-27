---
name: alibabacloud-workbench-cli
description: |
  Agent-native CLI for managing ECS instances without public IPs, primarily for single-instance operations. It supports millisecond-level remote command execution, large file transfers up to 1GB, and TCP port forwarding. It offers four authentication modes: AK, RamRoleArn, CredentialsCmd, and CredentialsURI. Use it to run commands, deploy code, view logs, check processes, transfer files, set up port forwarding, or query and filter ECS instance lists.
license: Apache-2.0
metadata:
  domain: cloud-infrastructure
compatibility: Requires workbench CLI binary installed. Cross-platform Linux/macOS (amd64/arm64), Windows (amd64). Network access to *.aliyuncs.com and Workbench backend WebSocket endpoints required.
allowed-tools: Bash
---

# Workbench CLI Expert

Help users operate Alibaba Cloud ECS instances — especially those **without public IP addresses** — using the `workbench` command-line tool. Core capabilities for Agent workflows: millisecond-level remote command execution (`exec`), file transfer up to 1GB (`upload`/`download`), and port forwarding. This skill covers: install → configure credentials → exec/transfer/forward → manage sessions → troubleshoot errors.

## Instructions

### 1. Install the Workbench CLI

**Pre-check:**

```bash
workbench version     # Should print version, commit, build date
```

**Linux / macOS:**

```bash
curl -fsSL https://workbench-cli.oss-cn-hangzhou.aliyuncs.com/install.sh | bash
```

**Windows (PowerShell):**

```powershell
irm https://workbench-cli.oss-cn-hangzhou.aliyuncs.com/install.ps1 | iex
```

**Upgrade:**

```bash
workbench upgrade                        # Upgrade to latest
workbench upgrade --version 0.2.0        # Upgrade to specific version
```

### 2. Configure credentials

Credentials are stored in `~/.workbench/config.json` with `0600` permissions. As an Agent, write this file directly instead of using the interactive `workbench config` command.

```bash
# Create config directory
mkdir -p ~/.workbench

# Write config file (example: AK mode)
cat > ~/.workbench/config.json << 'EOF'
{
  "current": "default",
  "profiles": {
    "default": {
      "mode": "AK",
      "access_key_id": "<AccessKeyID>",
      "access_key_secret": "<AccessKeySecret>"
    }
  }
}
EOF

# Set secure permissions
chmod 600 ~/.workbench/config.json
```

**Config file schema by mode:**

AK mode:
```json
{
  "current": "default",
  "profiles": {
    "default": {
      "mode": "AK",
      "access_key_id": "LTAI...",
      "access_key_secret": "..."
    }
  }
}
```

RamRoleArn mode (auto-refreshes STS tokens):
```json
{
  "current": "default",
  "profiles": {
    "default": {
      "mode": "RamRoleArn",
      "access_key_id": "LTAI...",
      "access_key_secret": "...",
      "ram_role_arn": "acs:ram::123456789:role/WorkbenchRole",
      "role_session_name": "workbench-session"
    }
  }
}
```

CredentialsURI mode (HTTP endpoint returns credentials):
```json
{
  "current": "default",
  "profiles": {
    "default": {
      "mode": "CredentialsURI",
      "credentials_uri": "http://localhost:8080/credentials"
    }
  }
}
```

| Mode | When to use |
| --- | --- |
| **AK** (default) | Development, long-lived credentials |
| **StsToken** | Temporary security credentials (AccessKey + STS Token) |
| **RamRoleArn** | Production, cross-account, least-privilege via STS role assumption (auto-refreshes tokens) |
| **CredentialsCmd** | Zero-trust / Vault integration — external command outputs credential JSON |
| **CredentialsURI** | Metadata service / sidecar — HTTP endpoint returns credential JSON |

**Profile management (non-interactive):**

```bash
workbench config list                     # List all profiles (* marks active)
workbench config switch --profile prod    # Switch active profile
workbench config get                      # Show current profile details (JSON)
workbench config get --profile prod       # Show specific profile details
workbench config delete --profile old     # Delete a profile (cannot delete active)
```

### 3. Command reference

```
workbench
├── exec             # Execute remote command (non-interactive, millisecond-level)
├── upload           # Upload local file to instance (up to 1GB, via OSS relay)
├── download         # Download file from instance (up to 1GB, via OSS relay)
├── list             # List ECS instances
├── session          # Session management (list / close)
├── daemon           # Daemon lifecycle (start / status / stop)
├── config           # Credential configuration & profile management
│   ├── set          # Set a single config field
│   ├── list         # List all profiles
│   ├── switch       # Switch active profile
│   ├── get          # Show profile details
│   └── delete       # Delete a profile
├── upgrade          # Self-update
└── version          # Print version info
```

**Global flags:**

| Flag | Purpose | Default |
| --- | --- | --- |
| `--output` / `-o` | Output format: `text|json` | `text` |
| `--region` / `-r` | Alibaba Cloud region (e.g., `cn-hangzhou`) | auto-inferred from instance ID prefix |
| `--profile` / `-P` | Use a specific profile (overrides active profile) | current active profile |

### 4. List instances

```bash
workbench list ecs --region cn-hangzhou
workbench list ecs --region cn-hangzhou --status Running
workbench list ecs --region cn-hangzhou --tag env=prod --tag team=infra
workbench list ecs --region cn-hangzhou --instance-type ecs.g7.large
workbench list ecs --region cn-hangzhou --instance-name my-instance
workbench list ecs --region cn-hangzhou --image-id ubuntu_22_04_x64_20G_alibase_20230907.vhd
workbench list ecs --region cn-hangzhou --output json
```

`--region` is **required** for `list ecs`. Filters: `--status` (Running|Stopped|Starting|Stopping), `--tag` (key=value or key, repeatable, AND logic), `--instance-type` (e.g. ecs.g7.large), `--instance-name` (supports wildcards `*`), `--image-id`, `--vpc-id`, `--zone-id`, `--vswitch-id`, `--private-ip` (comma-separated), `--limit` (1-100, default 50), `--next-token` (pagination).

JSON output schema:

```json
[{
  "instance_id": "i-bp1xxxxx",
  "instance_name": "web-prod-01",
  "instance_type": "ecs.g7.large",
  "region_id": "cn-hangzhou",
  "status": "Running",
  "private_ip": "172.16.0.10",
  "public_ip": "",
  "os_type": "linux",
  "image_id": "ubuntu_22_04_x64_20G_alibase_20230907.vhd",
  "tags": {"env": "prod"}
}]
```

### 5. Remote command execution

**Built-in safety**: The CLI is a non-interactive executor — it does NOT provide a persistent shell. Each invocation is isolated and stateless, which prevents accidental cascading damage from lingering shell sessions.

**Agent pre-check requirement**: Before executing destructive commands (e.g., `rm -rf`, `shutdown`, `reboot`, `mkfs`, `dd`, service stop/restart, or any command that deletes data or halts the system), the Agent MUST confirm with the user by describing the intended action, the target instance, and the potential impact. Do NOT execute destructive commands without explicit user approval.

```bash
workbench exec --instance-id i-bp1xxxxx --command "df -h"
workbench exec --instance-id i-bp1xxxxx --command "sleep 30" --timeout 10
workbench exec --instance-id i-bp1xxxxx --command "df -h" --output json
```

| Flag | Required | Description | Default |
| --- | --- | --- | --- |
| `--instance-id` / `-i` | Yes | ECS instance ID | — |
| `--command` / `-c` | Yes | Command to execute | — |
| `--timeout` | No | Timeout in seconds | `30` |

**Important**: Each `exec` invocation runs in an independent shell context. State (cd, export) is NOT preserved between calls. Use `&&` or `;` to chain commands that need shared context in a single invocation.

JSON output schema:

```json
{
  "output": "Filesystem ...\n",
  "stderr": "",
  "exit_code": 0
}
```

### 6. File transfer

**Built-in safety**: The `upload` command has a built-in overwrite protection. When the remote destination file already exists, the CLI prompts for confirmation before overwriting:

```
Remote file "/root/id.txt" already exists (728 B, modified Jul 27 10:42). Overwrite? [y/N]
```

The default answer is **No** — if the user does not explicitly confirm, the upload is aborted. This prevents accidental overwriting of existing remote files.

**Agent pre-check requirement**: When using `upload` in automated/Agent workflows where interactive confirmation is not possible, the Agent MUST first check whether the target file exists on the remote instance (e.g., via `workbench exec --command "ls -la <path>"`) and inform the user if a file will be overwritten.

```bash
workbench upload ./app.jar /opt/app/app.jar --instance-id i-bp1xxxxx
workbench download /var/log/app.log ./ --instance-id i-bp1xxxxx
workbench download /var/log/app.log /tmp/local-copy.log --instance-id i-bp1xxxxx
```

Transfer goes through OSS as intermediary — transparent to the user, no OSS configuration needed. `download` second arg (local-path) is optional, defaults to current directory.

### 7. Session management

```bash
workbench session list
workbench session list --output json
workbench session close <session-id>
workbench session close --all
```

**Session lifecycle**: OPEN → RECONNECTING → BROKEN → CLOSED. Idle timeout 30min → auto CLOSED. Multiple operations on same instance share one session (transparent multiplexing).

### 8. Daemon management

```bash
workbench daemon start      # Manual start (usually not needed)
workbench daemon status
workbench daemon stop       # Closes all sessions
```

- **Auto-start**: Spawned on first CLI invocation.
- **Auto-exit**: 60 seconds after last session closes.
- **Singleton**: One per OS user (PID file lock).
- **IPC**: JSON-RPC over Unix socket (`~/.workbench/run/daemon.sock`).

### 9. Region inference

The CLI auto-infers region from the instance ID 3-character prefix (covers 290+ regions). If inference fails, `--region` is required. For `list` command, `--region` is always required.

## Exit Codes

| Code | Constant | Trigger |
| --- | --- | --- |
| **0** | `ExitSuccess` | Successful execution |
| **1** | `ExitGeneral` | Unclassified runtime error (includes instance not found, API errors, etc.) |
| **2** | `ExitArgument` | Missing, malformed, or invalid flag value |
| **3** | `ExitSessionNotFound` | Session ID invalid or expired |
| **4** | `ExitAuth` | Authentication or authorization failed |
| **5** | `ExitNetwork` | Network timeout, WebSocket exception |
| **6** | `ExitDaemonUnreach` | Local daemon not running or socket invalid |
| **7** | `ExitSessionBusy` | Session attached by another TTY |
| **N** | *(exec only)* | `exec` transparently passes through the remote command's exit code |

Error JSON output (on failure with `--output json`):

```json
{
  "code": 1,
  "message": "InvalidParameter.InstanceId: the specified instance does not exist"
}
```

## RAM Permissions

Minimum RAM policy required:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs-workbench:LoginECSInstance",
        "ecs-workbench:ChatMessages"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:StartTerminalSession"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ram:CreateServiceLinkedRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ram:ServiceName": "workbench.ecs.aliyuncs.com"
        }
      }
    }
  ]
}
```

Restrict to specific instances: replace `"Resource": "*"` in each statement with the corresponding format:
- ecs-workbench:LoginECSInstance : `acs:ecs:<region>:<account-id>:ecs/<instance-id>`
- ecs actions: `acs:ecs:<region>:<account-id>:instance/<instance-id>`

## Troubleshooting

| Error message pattern | Exit Code | First Action |
| --- | --- | --- |
| `InvalidAccessKeyId` / authentication errors | 4 | Verify AK/SK in `~/.workbench/config.json`. Re-run `workbench config`. |
| `profile not found` | 1 | Check profile name with `workbench config list`. |
| `not found in <region>` / instance not found | 1 | Verify instance ID and region. Use `workbench list --region <region>` to confirm. |
| Network timeout / WebSocket errors | 5 | Check network connectivity to `*.aliyuncs.com`. Verify security group rules. |
| Session busy / attach errors | 7 | Another terminal is attached. Close it first, or use `workbench session close <id>`. |
| `cannot start daemon` / socket errors | 6 | Run `workbench daemon status`. If stopped, any command will auto-restart it. |
| Permission denied (RAM) | 4 | Attach the RAM policy from `## RAM Permissions` to the user or role. |
| `insecure permissions` | 2 | Run `chmod 600 ~/.workbench/config.json`. |
| STS token expired | 4 | If using `RamRoleArn` mode, the CLI auto-refreshes. If using static STS, update the token. |
