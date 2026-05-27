# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

> **Aliyun CLI 3.3.8+**: This Skill requires `plugin install --source-base` flag, which was introduced in v3.3.7 (2026-04-16, [PR #1299](https://github.com/aliyun/aliyun-cli/pull/1299)). The minimum is set to **3.3.8** as a conservative floor. Versions < 3.3.8 will fail step §1.3 with `ERROR: invalid flag source-base`.

> **User-Agent declaration scope**: the commands shown in this guide are **CLI bootstrapping commands** (install / `aliyun configure` / authentication smoke-tests). They run **before** the Skill workflow begins. Once the Skill workflow starts, every **business** `aliyun ...` invocation (e.g. `aliyun dyvmsapi submit-intent`, `aliyun dyvmsapi query-call-detail-by-call-id`) in SKILL.md and the other reference documents declares the User-Agent **per-command** by passing `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"` on the command line. **System / tooling commands** (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`, any `aliyun ... --help`) DO NOT accept this flag and MUST NOT carry it — passing it raises `unknown flag: --user-agent` and aborts the command (see SKILL.md §1.1.1).


## Installation

> **How to pick a strategy** — use this matrix; pick the **first row that matches** your runtime. The strategies are ordered by manageability (easier to upgrade / uninstall later).
>
> | Runtime | Architecture | Recommended Strategy | Why |
> |---|---|---|---|
> | macOS with Homebrew | Apple Silicon (`arm64`) or Intel (`x86_64`) | **macOS · Homebrew** | Managed by `brew`; `brew upgrade` keeps it current; works for both architectures |
> | macOS without Homebrew, **with** sudo | Intel | macOS · Binary (Intel, system-wide) | Standard `/usr/local/bin` install |
> | macOS without Homebrew, **with** sudo | Apple Silicon | macOS · Binary (Apple Silicon, system-wide) | Native arm64 binary; **do not use the `amd64` build on arm64 hardware** |
> | macOS, **no** sudo (agent sandbox, restricted user) | any | macOS · Binary (user-level, no sudo) | Drops into `$HOME/.local/bin` and updates PATH |
> | Linux with sudo (Debian/Ubuntu/CentOS/RHEL) | `amd64` or `arm64` | Linux · Binary (system-wide) | Standard `/usr/local/bin` install |
> | Linux, **no** sudo (CI runner, container, agent sandbox) | `amd64` or `arm64` | Linux · Binary (user-level, no sudo) | Drops into `$HOME/.local/bin` and updates PATH |
> | Windows | `amd64` | Windows · Binary or PowerShell | See Windows section below |
>
> **Note for non-interactive shells (agent sandboxes / CI / containers)**: anything that calls `sudo` interactively will deadlock waiting for a password it cannot read. Pick a sudo-less strategy in those environments. SKILL.md §1.1 already automates this selection — the manual recipes here exist for diagnostics and edge cases.

### macOS

**macOS · Homebrew (Recommended)**
```bash
brew install aliyun-cli
# Upgrade an existing install
brew upgrade aliyun-cli

# Verify version (>= 3.3.8)
aliyun version
```

**macOS · Binary (Intel, system-wide)** — only for Intel Macs (`x86_64`).
```bash
# Detect architecture first; this recipe is only for Intel Macs.
[ "$(uname -m)" = "x86_64" ] || { echo "This recipe is for Intel Macs only; use the arm64 recipe below." >&2; exit 1; }

curl -fsSL https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz \
  | tar -xz -C /tmp
sudo mv /tmp/aliyun /usr/local/bin/
aliyun version
```

**macOS · Binary (Apple Silicon, system-wide)** — only for Apple Silicon Macs (`arm64`).
```bash
[ "$(uname -m)" = "arm64" ] || { echo "This recipe is for Apple Silicon Macs only; use the amd64 recipe above." >&2; exit 1; }

curl -fsSL https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-arm64.tgz \
  | tar -xz -C /tmp
sudo mv /tmp/aliyun /usr/local/bin/
aliyun version
```

**macOS · Binary (user-level, no sudo)** — use when no `brew` is available and `/usr/local/bin` is not writable (agent sandbox, restricted user).
```bash
DEST="$HOME/.local/bin"
mkdir -p "$DEST"

# Auto-detect arch so the same recipe works on Intel and Apple Silicon.
case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  arm64)  ARCH=arm64 ;;
  *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac

curl -fsSL "https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-${ARCH}.tgz" \
  | tar -xz -C "$DEST"
chmod +x "$DEST/aliyun"

# Add to PATH for the current shell and persist for future shells.
export PATH="$DEST:$PATH"
grep -qsF "$DEST" ~/.zshrc || echo "export PATH=\"$DEST:\$PATH\"" >> ~/.zshrc

hash -r
aliyun version
```

### Linux

**Linux · Binary (system-wide)** — covers Debian/Ubuntu/CentOS/RHEL on `amd64` or `arm64`. Requires sudo.
```bash
case "$(uname -m)" in
  x86_64|amd64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac

curl -fsSL "https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-${ARCH}.tgz" \
  | tar -xz -C /tmp
sudo mv /tmp/aliyun /usr/local/bin/
aliyun version
```

**Linux · Binary (user-level, no sudo)** — for CI runners, containers, and agent sandboxes where `/usr/local/bin` is not writable.
```bash
DEST="$HOME/.local/bin"
mkdir -p "$DEST"

case "$(uname -m)" in
  x86_64|amd64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "Unsupported arch: $(uname -m)" >&2; exit 1 ;;
esac

curl -fsSL "https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-${ARCH}.tgz" \
  | tar -xz -C "$DEST"
chmod +x "$DEST/aliyun"

export PATH="$DEST:$PATH"
grep -qsF "$DEST" ~/.bashrc || echo "export PATH=\"$DEST:\$PATH\"" >> ~/.bashrc

hash -r
aliyun version
```

### Windows

**Using Binary**
1. Download from: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract the ZIP file
3. Add the directory to your PATH environment variable
4. Open new Command Prompt or PowerShell
5. Verify: `aliyun version`

**Using PowerShell**
```powershell
# Download
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"

# Extract
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli

# Add to PATH at the **User** scope (no admin privileges required; persists across new shells for the current user).
# Use `Machine` scope only if you explicitly need a system-wide install AND have admin rights.
$env:Path += ";C:\aliyun-cli"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::User)

# Verify
aliyun version
```

## Configuration

### Quick Start

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

All `aliyun configure` commands support non-interactive flags, which is the recommended approach —
it works in scripts, CI/CD pipelines, and agent-driven automation without hanging on stdin prompts.

**Where to Get Access Keys**

1. Log in to Aliyun Console: https://ram.console.aliyun.com/
2. Navigate to: AccessKey Management
3. Create a new AccessKey pair
4. Save the secret immediately — it's only shown once

### Default Region Id — Common Choices

`aliyun configure` (interactive mode) prompts for **Default Region Id**. The CLI does not show the candidate list, which often blocks users. Use the table below to pick one.

For this Skill, `dyvmsapi` is a **centralized service** and is not region-sensitive — any valid public-cloud region works. The recommended default is **`cn-hangzhou`**. If the user's other Alibaba Cloud resources already live in another region (e.g. `cn-shanghai`), pick that one so a single profile serves multiple workloads.

> The list below mirrors the authoritative Alibaba Cloud regions/zones reference at <https://help.aliyun.com/document_detail/40654.html>. When in doubt, **always** consult the authoritative page — region inventory evolves (new regions are added, local regions are decommissioned).

**Public cloud — China**

| Region Id | Location |
|---|---|
| `cn-hangzhou` (recommended) | East China 1 (Hangzhou) |
| `cn-shanghai` | East China 2 (Shanghai) |
| `cn-beijing` | North China 2 (Beijing) |
| `cn-shenzhen` | South China 1 (Shenzhen) |
| `cn-qingdao` | North China 1 (Qingdao) |
| `cn-zhangjiakou` | North China 3 (Zhangjiakou) |
| `cn-huhehaote` | North China 5 (Hohhot) |
| `cn-wulanchabu` | North China 6 (Ulanqab) |
| `cn-heyuan` | South China 2 (Heyuan) |
| `cn-guangzhou` | South China 3 (Guangzhou) |
| `cn-chengdu` | Southwest China 1 (Chengdu) |
| `cn-zhongwei` | Northwest China 2 (Zhongwei) |
| `cn-wuhan-lr` | Central China 1 (Wuhan, local region) |
| `cn-hongkong` | China (Hong Kong) |

**Public cloud — Overseas**

| Region Id | Location |
|---|---|
| `ap-southeast-1` | Singapore |
| `ap-southeast-3` | Malaysia (Kuala Lumpur) |
| `ap-southeast-5` | Indonesia (Jakarta) |
| `ap-southeast-6` | Philippines (Manila) |
| `ap-southeast-7` | Thailand (Bangkok) |
| `ap-southeast-8` | Malaysia (Johor) |
| `ap-northeast-1` | Japan (Tokyo) |
| `ap-northeast-2` | South Korea (Seoul) |
| `us-east-1` | USA (Virginia) |
| `us-west-1` | USA (Silicon Valley) |
| `na-south-1` | Mexico |
| `eu-central-1` | Germany (Frankfurt) |
| `eu-west-1` | UK (London) |
| `eu-west-2` | France (Paris) |
| `me-east-1` | UAE (Dubai) |
| `me-central-1` | Saudi Arabia (Riyadh, partner-operated) |

**Finance Cloud (isolated)**

Finance Cloud regions (e.g. `cn-hangzhou-finance`, `cn-shanghai-finance-1`, `cn-shenzhen-finance-1`) are **isolated** from the public cloud and require a finance-cloud account. **Do not** select them unless the user is explicitly on the finance cloud.

### Configuration Modes

Aliyun CLI supports 6 authentication modes. All examples below use non-interactive flags.

#### 1. AK Mode (Access Key)

Most common mode for personal accounts and scripts.

```bash
aliyun configure set \
  --mode AK \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --region cn-hangzhou
```

Configuration is stored in `~/.aliyun/config.json`:

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "AK",
      "access_key_id": "LTAI5tXXXXXXXX",
      "access_key_secret": "8dXXXXXXXXXXXXXXXXXXXXXXXX",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "en"
    }
  ]
}
```

#### 2. StsToken Mode (Temporary Credentials)

For short-lived access (tokens expire in 1-12 hours).

```bash
aliyun configure set \
  --mode StsToken \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --sts-token v1.0:XXXXXXXXXXXXXXXX \
  --region cn-hangzhou
```

Use cases: CI/CD pipelines, temporary access for external contractors, cross-account access.

#### 3. RamRoleArn Mode (Assume RAM Role)

Assume a RAM role for elevated or cross-account access.

```bash
aliyun configure set \
  --mode RamRoleArn \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --ram-role-arn acs:ram::123456789012:role/AdminRole \
  --role-session-name my-session \
  --region cn-hangzhou
```

Use cases: cross-account resource access, temporary elevated privileges, role-based access control.

#### 4. EcsRamRole Mode (ECS Instance RAM Role)

Use the RAM role attached to an ECS instance — no credentials needed.

```bash
aliyun configure set \
  --mode EcsRamRole \
  --ram-role-name MyEcsRole \
  --region cn-hangzhou
```

Requirements: must be running on an ECS instance with a RAM role attached.

Use cases: scripts and automation running on ECS instances.

#### 5. RsaKeyPair Mode (RSA Key Pair)

Use RSA key pair for authentication (generate key pair in Aliyun Console first).

```bash
aliyun configure set \
  --mode RsaKeyPair \
  --private-key /path/to/private-key.pem \
  --key-pair-name my-key-pair \
  --region cn-hangzhou
```

#### 6. RamRoleArnWithEcs Mode (ECS + RAM Role)

Combine ECS instance role with RAM role assumption for cross-account access from ECS.

```bash
aliyun configure set \
  --mode RamRoleArnWithEcs \
  --ram-role-name MyEcsRole \
  --ram-role-arn acs:ram::123456789012:role/TargetRole \
  --role-session-name my-session \
  --region cn-hangzhou
```

### Environment Variables

**Highest priority** - overrides config file

**Access Key Mode**
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

**STS Token Mode**
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret
export ALIBABA_CLOUD_SECURITY_TOKEN=your_sts_token
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

**ECS RAM Role Mode**
```bash
export ALIBABA_CLOUD_ECS_METADATA=role_name
```

**Use Case**:
- CI/CD pipelines
- Docker containers
- Temporary credential override

### Managing Multiple Profiles

**Create Named Profiles**

```bash
aliyun configure set --profile projectA \
  --mode AK \
  --access-key-id LTAI5tAAAAAAAA \
  --access-key-secret 8dAAAAAAAAAAAAAAAAAAAAAAAA \
  --region cn-hangzhou

aliyun configure set --profile projectB \
  --mode AK \
  --access-key-id LTAI5tBBBBBBBB \
  --access-key-secret 8dBBBBBBBBBBBBBBBBBBBBBBBB \
  --region cn-shanghai
```

**Use Specific Profile**

```bash
aliyun ecs describe-instances --profile projectA

export ALIBABA_CLOUD_PROFILE=projectA
aliyun ecs describe-instances   # Uses projectA
```

**List and Switch Profiles**

```bash
aliyun configure list                      # List all profiles
aliyun configure set --current projectA    # Switch default profile
```

### Credential Priority

Credentials are loaded in this order (first found wins):

1. **Command-line flag**: `--profile <name>`
2. **Environment variable**: `ALIBABA_CLOUD_PROFILE`
3. **Environment credentials**: `ALIBABA_CLOUD_ACCESS_KEY_ID`, etc.
4. **Configuration file**: `~/.aliyun/config.json` (current profile)
5. **ECS Instance RAM Role**: If running on ECS with attached role

## Verification

### Test Authentication

```bash
# Basic test - list regions
aliyun ecs describe-regions

# Expected output: JSON array of regions
```

**If successful**, you'll see:
```json
{
  "Regions": {
    "Region": [
      {
        "RegionId": "cn-hangzhou",
        "RegionEndpoint": "ecs.cn-hangzhou.aliyuncs.com",
        "LocalName": "华东 1（杭州）"
      },
      ...
    ]
  },
  "RequestId": "..."
}
```

**If failed**, you'll see error messages:
- `InvalidAccessKeyId.NotFound` - Wrong Access Key ID
- `SignatureDoesNotMatch` - Wrong Access Key Secret
- `InvalidSecurityToken.Expired` - STS token expired (for StsToken mode)
- `Forbidden.RAM` - Insufficient permissions

### Debug Configuration

```bash
# Show current configuration
aliyun configure get

# Test with debug logging
aliyun ecs describe-regions --log-level=debug

# Check credential provider
aliyun configure get mode
```

## Security Best Practices

### 1. Use RAM Users (Not Root Account)

❌ **Don't**: Use Aliyun root account credentials
✅ **Do**: Create RAM users with specific permissions

```bash
# Create RAM user in console
# Attach only necessary policies
# Use RAM user's access keys
```

### 2. Principle of Least Privilege

Grant only the minimum permissions needed:

```bash
# Example: Read-only ECS access
# Attach policy: AliyunECSReadOnlyAccess
```

### 3. Rotate Access Keys Regularly

```bash
# Create new access key in RAM Console, then update configuration
aliyun configure set --access-key-id NEW_KEY --access-key-secret NEW_SECRET
# Delete old access key from console
```

### 4. Use STS Tokens for Temporary Access

```bash
aliyun configure set --mode StsToken \
  --access-key-id XXXX --access-key-secret XXXX \
  --sts-token XXXX --region cn-hangzhou
```

### 5. Use ECS RAM Roles When Possible

```bash
aliyun configure set --mode EcsRamRole --ram-role-name MyRole --region cn-hangzhou
```

### 6. Never Commit Credentials

```bash
# Add to .gitignore
echo "~/.aliyun/config.json" >> .gitignore

# Use environment variables in CI/CD instead
```

### 7. Secure Config File

```bash
# Restrict permissions
chmod 600 ~/.aliyun/config.json
```

## Troubleshooting

### Issue: Command Not Found

```bash
# Check installation
which aliyun

# Check PATH
echo $PATH

# Reinstall or add to PATH
```

### Issue: Authentication Failed

```bash
# Verify configuration
aliyun configure get

# Test with debug
aliyun ecs describe-regions --log-level=debug

# Check credentials in console
# Verify access key is active
```

### Issue: Permission Denied

```bash
# Error: Forbidden.RAM

# Check RAM user permissions
# Attach necessary policies in RAM console
# Example: AliyunECSFullAccess for ECS operations
```

### Issue: STS Token Expired

```bash
# Error: InvalidSecurityToken.Expired

# Reconfigure with new token
aliyun configure set --mode StsToken \
  --access-key-id XXXX --access-key-secret XXXX \
  --sts-token NEW_TOKEN --region cn-hangzhou
```

### Issue: Wrong Region

```bash
# Some resources may not exist in the specified region

# Check available regions
aliyun ecs describe-regions

# Update default region
aliyun configure set region cn-shanghai
```

## Advanced Configuration

### Custom Endpoint

```bash
# Use custom or private endpoint
export ALIBABA_CLOUD_ECS_ENDPOINT=ecs-vpc.cn-hangzhou.aliyuncs.com
```

### Proxy Settings

```bash
# HTTP proxy
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# No proxy for specific domains
export NO_PROXY=localhost,127.0.0.1,.aliyuncs.com
```

### Timeout Settings

```bash
# Connection timeout (default: 10s)
export ALIBABA_CLOUD_CONNECT_TIMEOUT=30

# Read timeout (default: 10s)
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

## Next Steps

After installation and configuration:

1. **Install plugins** for services you need (v3.3.8+ required for `--source-base` flag used by this Skill):
   ```bash
   aliyun plugin install --names ecs vpc rds

   # List all available plugins
   aliyun plugin list-remote
   ```

2. **Explore commands**:
   ```bash
   aliyun ecs --help
   aliyun fc --help
   ```

3. **Read documentation**:
   - Official Documentation: https://help.aliyun.com/zh/cli/

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- Access Key Management: https://ram.console.aliyun.com/manage/ak
- Plugin Repository: https://github.com/aliyun/aliyun-cli
