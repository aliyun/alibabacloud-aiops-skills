# Aliyun CLI installation and configuration

Cloud operations require Aliyun CLI 3.3.22 or later and the SLS plugin.
Offline scripts need only the [Python dependencies](#python-dependencies).

## Environment check

Run with the Python interpreter that will execute the skill scripts:

```sh
python3 scripts/doctor.py
python3 scripts/doctor.py --offline
python3 scripts/doctor.py --aliyun /path/to/aliyun --with-sdk
```

The default check reports Python and `jsonschema` versions, the CLI path and
version, CLI profile configuration, the SLS plugin version, and available
dashboard/query commands.
`--offline` checks only Python dependencies. `--with-sdk` also checks
`alibabacloud-credentials` and `alibabacloud-sls20201230`. Exit code 0 means the
selected checks passed; exit code 1 means a prerequisite needs attention.
Suggested installation or update commands are printed to stdout for you to run.
CLI installation suggestions use a user-writable directory on Linux/macOS.
After installation, rerun doctor to check the plugin and command availability.
If `aliyun configure list` fails, doctor asks you to configure a CLI profile with
`aliyun configure` before cloud operations.

## Installation

### macOS or Linux

The installer writes the executable to `/usr/local/bin/aliyun` by default.
Installing or upgrading at this location requires elevated privileges, typically
through `sudo` or a root account. If you cannot use elevated privileges, follow the
[official installation instructions](https://help.aliyun.com/zh/cli/) to place the
binary in a user-writable directory and add that directory to PATH.

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

## Authentication and profiles

Use the CLI's configured authentication. Pass `--profile <name>` only when the
user specifies a profile; keep the default profile unchanged.

When diagnosing authentication, `aliyun configure list` shows configured
profiles. Use the failed request's error code and request ID for diagnosis.
Do not dump credential files or run `aliyun configure get`.

Authentication setup depends on the environment: a configured AccessKey or STS
profile, a RAM role, or another supported provider. Consult the
[official CLI configuration documentation](https://help.aliyun.com/zh/cli/configure-credentials/)
for the selected mode. Keep credentials out of chat and command output.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Installation or upgrade fails with permission denied for `/usr/local/bin/aliyun` | Use elevated privileges to write to the default location, or install in a user-writable directory and add it to PATH. |
| `aliyun` not found | Check the installation directory and PATH, then reopen the terminal. |
| SLS command or option missing | Check the SLS plugin version and command help; install or update the plugin as needed. |
| `InvalidAccessKeyId.NotFound` / `SignatureDoesNotMatch` | Check the configured authentication with the credential owner. |
| `InvalidSecurityToken.Expired` | Renew the expired session through the configured authentication provider. |
| SLS request denied by RAM permissions | Use the denied action and resource to check [SLS RAM permissions](ram-policies.md). |
| Project not found or wrong endpoint | Follow [connection options](datasources/api.md#connection-options), using the intended source region. |

Verify access with the SLS read required by the task.

## Network configuration

For a proxy, use the environment's HTTP(S) proxy settings:

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

Set `NO_PROXY` only for destinations that should bypass the proxy. For SLS
internal-network access or an endpoint override, use
[connection options](datasources/api.md#connection-options).

See the [official CLI documentation](https://help.aliyun.com/zh/cli/) for
platform-specific installation and additional configuration.

## Python dependencies

Use Python 3.10+ and install packages in the environment running the skill scripts.
Plan construction requires `jsonschema` (>=4.18, <5).
Metric StoreView queries and scheduled dashboard reports also require
`alibabacloud-credentials` (>=1.0.3, <2) and
`alibabacloud-sls20201230` (>=5.15.1, <6).
