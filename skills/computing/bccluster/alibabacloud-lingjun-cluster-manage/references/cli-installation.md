# Aliyun CLI Installation & Authentication

The Lingjun skill needs exactly 1 CLI plugin: `eflo-controller`.

## Version Requirement

**Minimum version**: `aliyun-cli 3.3.3+` (versions below 3.3.3 have no plugin subsystem and cannot load `eflo-controller`).

```bash
aliyun version  # check version
```

## Install the CLI

| Platform | Command |
|---|---|
| macOS (Homebrew) | `brew install aliyun-cli && brew upgrade aliyun-cli` |
| macOS / Linux x86_64 | `curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh \| bash` |
| Linux ARM64 | `wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz && tar -xzf aliyun-cli-linux-latest-arm64.tgz && sudo mv aliyun /usr/local/bin/` |
| Windows | Download `https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip`, unzip, and add to PATH |

## Install the Plugin

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install --names eflo-controller
aliyun plugin update
aliyun plugin list  # verify eflo-controller is present
```

## 6 Authentication Modes

| Mode | When to use |
|---|---|
| **AK** | Personal account / scripts (most common) |
| **StsToken** | Short-term credentials (valid for 1-12 hours) |
| **RamRoleArn** | Assume a RAM role / cross-account |
| **EcsRamRole** | Running on an ECS instance, credential-free |
| **RsaKeyPair** | RSA key pair (rarely used) |
| **RamRoleArnWithEcs** | Assume a target role from an ECS-attached role |

### AK Mode Quick Setup (recommended)

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-key-id> \
  --access-key-secret <your-key-secret> \
  --region cn-hangzhou
```

Credentials are stored in `~/.aliyun/config.json`.

### Other Mode Examples

```bash
# StsToken
aliyun configure set --mode StsToken \
  --access-key-id <id> --access-key-secret <secret> \
  --sts-token <token> --region cn-hangzhou

# RamRoleArn
aliyun configure set --mode RamRoleArn \
  --access-key-id <id> --access-key-secret <secret> \
  --ram-role-arn acs:ram::123456789012:role/AdminRole \
  --role-session-name <session-name> \
  --region cn-hangzhou

# EcsRamRole
aliyun configure set --mode EcsRamRole \
  --ram-role-name <role-name> --region cn-hangzhou
```

## Credential Precedence

Loaded in the following order (first match wins):

1. CLI flag `--profile <name>`
2. Environment variable `ALIBABA_CLOUD_PROFILE`
3. Environment credentials `ALIBABA_CLOUD_ACCESS_KEY_ID` / `_SECRET` / `_SECURITY_TOKEN`
4. Current profile in `~/.aliyun/config.json`
5. RAM Role attached to the ECS instance

## Multi-Profile Management

```bash
aliyun configure set --profile projectA --mode AK \
  --access-key-id <...> --access-key-secret <...> --region cn-hangzhou

aliyun configure list                       # list all profiles
aliyun configure set --current projectA     # switch default profile
aliyun eflo-controller list-clusters --profile projectA --region cn-hangzhou
```

## Verification

```bash
aliyun configure list                       # check profile + region
aliyun eflo-controller list-clusters \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
  --region cn-hangzhou                      # smoke test
```

## Common Authentication Error Codes

| ErrorCode | Meaning | Handling |
|---|---|---|
| `InvalidAccessKeyId.NotFound` | AccessKey ID wrong or disabled | Check AK status in the RAM console |
| `SignatureDoesNotMatch` | AccessKey Secret wrong | Reconfigure |
| `InvalidSecurityToken.Expired` | STS token expired | Reissue and reconfigure |
| `Forbidden.RAM` | Insufficient permissions | See [ram-policies.md](ram-policies.md) |

## Advanced Configuration (optional)

```bash
# Custom endpoint
export ALIBABA_CLOUD_ECS_ENDPOINT=ecs-vpc.cn-hangzhou.aliyuncs.com

# Timeouts (seconds)
export ALIBABA_CLOUD_CONNECT_TIMEOUT=30
export ALIBABA_CLOUD_READ_TIMEOUT=30

# HTTP proxy
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1,.aliyuncs.com
```

## 📖 References

- [Aliyun CLI official docs](https://help.aliyun.com/zh/cli/)
- [Eflo-Controller OpenAPI](https://api.aliyun.com/api/eflo-controller/2022-12-15)
- [RAM console](https://ram.console.aliyun.com/) · [AccessKey management](https://ram.console.aliyun.com/manage/ak)
