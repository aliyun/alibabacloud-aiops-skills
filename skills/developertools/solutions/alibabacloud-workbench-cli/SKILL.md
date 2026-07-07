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

Credentials are stored in `~/.workbench/config.json` with `0600` permissions. The CLI rejects config files with lax permissions (group/other readable).

```bash
workbench config                          # Interactive setup (auto-detects mode)
workbench config --mode AK                # Specify mode directly
```

| Mode | When to use |
| --- | --- |
| **AK** (default) | Development, long-lived credentials |
| **RamRoleArn** | Production, cross-account, least-privilege via STS role assumption (auto-refreshes tokens) |
| **CredentialsCmd** | Zero-trust / Vault integration — external command outputs credential JSON |
| **CredentialsURI** | Metadata service / sidecar — HTTP endpoint returns credential JSON |

**CredentialsCmd** output format (to stdout):
```json
{"mode":"AK","access_key_id":"...","access_key_secret":"..."}
```
or with STS:
```json
{"mode":"StsToken","access_key_id":"...","access_key_secret":"...","sts_token":"..."}
```

### 3. Command reference

```
workbench
├── exec             # Execute remote command (non-interactive, millisecond-level)
├── upload           # Upload local file to instance (up to 1GB, via OSS relay)
├── download         # Download file from instance (up to 1GB, via OSS relay)
├── forward          # Port forwarding (start / list / stop)
├── list             # List ECS instances
├── session          # Session management (list / close)
├── daemon           # Daemon lifecycle (start / status / stop)
├── config           # Credential configuration
├── upgrade          # Self-update
└── version          # Print version info
```

**Global flags:**

| Flag | Purpose | Default |
| --- | --- | --- |
| `--output` / `-o` | Output format: `text|json` | `text` |
| `--region` / `-r` | Alibaba Cloud region (e.g., `cn-hangzhou`) | auto-inferred from instance ID prefix |

### 4. List instances

```bash
workbench list --region cn-hangzhou
workbench list --region cn-hangzhou --status Running
workbench list --region cn-hangzhou --tag env=prod --tag team=infra
workbench list --region cn-hangzhou --output json
```

`--region` is **required** for `list`. Flags: `--status` (Running|Stopped|Starting|Stopping), `--tag` (key=value or key, repeatable, AND logic).

JSON output schema:

```json
[{
  "instance_id": "i-bp1xxxxx",
  "instance_name": "web-prod-01",
  "region_id": "cn-hangzhou",
  "status": "Running",
  "private_ip": "172.16.0.10",
  "public_ip": "",
  "os_type": "linux",
  "tags": {"env": "prod"}
}]
```

### 5. Remote command execution

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

```bash
workbench upload ./app.jar /opt/app/app.jar --instance-id i-bp1xxxxx
workbench download /var/log/app.log ./ --instance-id i-bp1xxxxx
workbench download /var/log/app.log /tmp/local-copy.log --instance-id i-bp1xxxxx
```

Transfer goes through OSS as intermediary — transparent to the user, no OSS configuration needed. `download` second arg (local-path) is optional, defaults to current directory.

### 7. Port forwarding

```bash
workbench forward start --instance-id i-bp1xxxxx --remote-port 3306 --local-port 13306
workbench forward list
workbench forward stop <forward-id>
```

| Flag (start) | Required | Description | Default |
| --- | --- | --- | --- |
| `--instance-id` / `-i` | Yes | ECS instance ID | — |
| `--remote-port` | Yes | Remote port on instance (1-65535) | — |
| `--local-port` | No | Local listening port | `0` (auto-assign) |

Port forwards are maintained by the daemon — they **survive CLI exit**. Alive until explicitly stopped or daemon exits.

### 8. Session management

```bash
workbench session list
workbench session list --output json
workbench session close <session-id>
workbench session close --all
```

**Session lifecycle**: OPEN → RECONNECTING → BROKEN → CLOSED. Idle timeout 30min → auto CLOSED. Multiple operations on same instance share one session (transparent multiplexing).

### 9. Daemon management

```bash
workbench daemon start      # Manual start (usually not needed)
workbench daemon status
workbench daemon stop       # Closes all sessions and forwards
```

- **Auto-start**: Spawned on first CLI invocation.
- **Auto-exit**: 60 seconds after last session closes.
- **Singleton**: One per OS user (PID file lock).
- **IPC**: JSON-RPC over Unix socket (`~/.workbench/run/daemon.sock`).

### 10. Region inference

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
        "ecs:DescribeInstances",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:StartTerminalSession",
        "ecs-workbench:LoginECSInstance",
        "ecs-workbench:ChatMessages",
        "ims:GetUser"
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

Restrict to specific instances: replace `"Resource": "*"` with `acs:ecs:<region>:<account-id>:instance/<instance-id>`.

## Troubleshooting

| Error message pattern | Exit Code | First Action |
| --- | --- | --- |
| `InvalidAccessKeyId` / authentication errors | 4 | Verify AK/SK in `~/.workbench/config.json`. Re-run `workbench config`. |
| `not found in <region>` / instance not found | 1 | Verify instance ID and region. Use `workbench list --region <region>` to confirm. |
| Network timeout / WebSocket errors | 5 | Check network connectivity to `*.aliyuncs.com`. Verify security group rules. |
| Session busy / attach errors | 7 | Another terminal is attached. Close it first, or use `workbench session close <id>`. |
| `cannot start daemon` / socket errors | 6 | Run `workbench daemon status`. If stopped, any command will auto-restart it. |
| Permission denied (RAM) | 4 | Attach the RAM policy from `## RAM Permissions` to the user or role. |
| `insecure permissions` | 2 | Run `chmod 600 ~/.workbench/config.json`. |
| STS token expired | 4 | If using `RamRoleArn` mode, the CLI auto-refreshes. If using static STS, update the token. |
