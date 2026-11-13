# SysAgent CLI Setup

Use this guide on the first SysAgent use in a local Agent conversation. Reuse successful checks for later requests in that conversation while the executable, plugin environment, and identity are unchanged. If one changes or fails, repeat only the affected checks.

| Requirement | What to verify |
| --- | --- |
| Aliyun CLI | Version 3.4.0 or later; use the same executable for all steps |
| SysOM plugin | A stable version strictly greater than 0.10.0; the SysAgent subcommands must load |
| Credentials | An authorized CLI identity that can reach SysAgent |

## 1. Install or update Aliyun CLI

Check the executable and its version:

```bash
command -v aliyun
aliyun version
```

If the CLI is missing, too old, or the installed plugin requires a newer host, use the [Aliyun CLI Installation Guide](cli-installation-guide.md). If PATH contains several copies, choose a compatible absolute path and use that executable for the rest of the conversation.

## 2. Install or update the SysOM plugin

Use `aliyun plugin show --name sysom` to check whether it is installed. Run **one** of the following commands at the first readiness check, or after the CLI or plugin environment changes:

**First installation**

```bash
ALIBABA_CLOUD_CLI_PLUGIN_NO_CACHE=true aliyun plugin install --names sysom --source-base https://aliyuncli.alicdn.com/plugins-v2
```

**Already installed**

```bash
ALIBABA_CLOUD_CLI_PLUGIN_NO_CACHE=true aliyun plugin update --name sysom --source-base https://aliyuncli.alicdn.com/plugins-v2
```

The install selects the latest stable release without pinning a version. The update checks the index and upgrades SysOM when a newer stable release is available. Cache bypass is scoped to that command. Keep the user's global plugin settings and other plugins unchanged.

Verify the actual loaded plugin and command help:

```bash
aliyun plugin show --name sysom
aliyun sysom version
aliyun sysom sysagent --help
aliyun sysom sysagent ask --help
aliyun sysom sysagent run watch --help
```

The loaded version must be **strictly greater than 0.10.0**. The leaf commands must expose `--request-id` and `--stream-events`, respectively. If the update source is unavailable and the local version and commands pass, state that the latest version could not be confirmed and continue. If readiness still fails after one appropriate install or update and recheck, report which check failed and stop before submitting work.

## 3. Check and configure credentials

### Check the existing configuration

```bash
aliyun configure list
```

Use this command to inspect Profile names, modes, and status. Keep an authorized working identity: use the user's named Profile when supplied, otherwise use the identity resolved by the CLI. An empty list does not verify or rule out a configured environment or workload credential provider. Probe such a provider only if it is already configured for this environment and is the intended identity. Do not inspect credential files or print environment variable values.

### Configure only if no usable identity is available

Pause cloud calls and direct the user to [Configure CLI Credentials](https://help.aliyun.com/zh/cli/configure-credentials). The user configures their approved mode in their own terminal or through their environment's credential provider. The Skill does not select a default authentication mode.

| Environment | Options to consider if authorized |
| --- | --- |
| Local workstation | Existing named Profile, browser-based authentication such as OAuth or CloudSSO, or an approved RAM credential |
| ECS or managed workload | Existing instance RAM role or the workload's approved identity provider |
| CI or temporary access | An approved temporary credential or credential provider |

For modes that support interactive configuration, the user can run the following outside the Agent conversation. Replace the placeholders using the CLI's help and the official guide.

```bash
aliyun configure --mode MODE --profile PROFILE_NAME
```

Do not ask for passwords, access keys, or tokens in chat, pass their values as arguments, run credential-writing commands on the user's behalf, or log the configuration contents. Repeat the relevant checks after the user finishes.

## 4. Verify SysAgent access

Resolve `USER_AGENT` per [Observability](../SKILL.md#observability), then run the read-only probe:

```bash
aliyun sysom sysagent session list --limit 1 --user-agent USER_AGENT
```

An empty session list is a successful probe. If using a named Profile, append the Host's `--profile PROFILE_NAME` to this probe and subsequent cloud calls. No diagnostic task is needed to verify setup.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| Command not found or version differs from the expected installation | Verify the executable path and version, then use the installation guide. |
| `sysagent` or a leaf command is missing | Check the Host and plugin versions and retry the matching help command after an appropriate update. |
| No credentials, invalid identity, or expired credential | Recheck the selected credential source. If it cannot renew, the user should reconfigure or refresh it through the same approved method. Re-run the probe. |
| Identity is valid but SysAgent returns AccessDenied | Keep the operation and request ID. Follow [RAM guidance](ram-policies.md); do not change identity or start a new login as a workaround. |
| Network, index, or service error | Report the failing endpoint class or operation without secrets. A service error alone does not require a new credential. |

If identity and service access need to be distinguished, the Agent may optionally run `aliyun sts get-caller-identity --region cn-hangzhou --user-agent USER_AGENT` with the same identity. That command verifies the caller, not SysAgent access.
