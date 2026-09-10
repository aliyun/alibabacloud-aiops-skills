# Aliyun CLI installation and configuration

This skill requires Aliyun CLI 3.3.22 or later and the SLS plugin.

## Installation

### macOS or Linux

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
aliyun version
```

### Windows

Download the [Windows binary](https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip),
extract it, and add its directory to PATH. Open a new terminal and run
`aliyun version`.

## SLS plugin

Check `aliyun sls version` and the requested command's help. Install a missing
plugin or update it when the required command or option is unavailable:

```bash
aliyun plugin install --names sls
aliyun plugin update --name sls
```

Choose the command appropriate to the installed state.

## Authentication and profiles

Use the CLI's configured authentication. Pass `--profile <name>` only when the
user specifies a profile; keep the default profile unchanged.

When diagnosing authentication, `aliyun configure list` shows configured
profiles. Diagnose the failed request using its error code and request ID.
Do not dump credential files or run `aliyun configure get`.

Authentication setup depends on the environment: a configured AccessKey or STS
profile, a RAM role, or another supported provider. Consult the
[official CLI configuration documentation](https://help.aliyun.com/zh/cli/configure-credentials/)
for the selected mode. Keep credentials out of chat and command output.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `aliyun` not found | Check the installation directory and PATH, then reopen the terminal. |
| SLS command or option missing | Check the SLS plugin version and command help; install or update the plugin as needed. |
| `InvalidAccessKeyId.NotFound` / `SignatureDoesNotMatch` | Check the configured authentication with the credential owner. |
| `InvalidSecurityToken.Expired` | Renew the expired session through the configured authentication provider. |
| Permission denied | Use the denied action and resource to check [SLS RAM permissions](ram-policies.md). |
| Project not found or wrong endpoint | Follow [region and endpoint configuration](regions.md), including cross-region discovery when needed. |

Verify access with the SLS read required by the task. An unrelated ECS request
can fail because the caller has no ECS permission.

## Network configuration

For a proxy, use the environment's HTTP(S) proxy settings:

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

Set `NO_PROXY` only for destinations that should bypass the proxy. For SLS
internal-network access or an endpoint override, use
[region and endpoint configuration](regions.md).

See the [official CLI documentation](https://help.aliyun.com/zh/cli/) for
platform-specific installation and additional configuration.
