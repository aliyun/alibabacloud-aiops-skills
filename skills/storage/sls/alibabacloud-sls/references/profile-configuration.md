# Profile configuration

Use this page for profile selection, authentication setup, and credential precedence.
Follow the [credential safety rules](../SKILL.md#safety-rules).

## Select a profile

Use the configured profile unless the user specifies another one for the task.
List available profiles with:

```bash
aliyun configure list
```

Change the saved default profile only when the user requests it.

For CLI commands, profile selection uses the first applicable source:

1. `--profile` / `-p` on the command line.
2. The first nonempty variable among `ALIBABACLOUD_PROFILE`,
   `ALIBABA_CLOUD_PROFILE`, and `ALICLOUD_PROFILE`, in that order.
3. The configuration file's `current` profile.

An explicitly selected profile must exist. Environment credentials do not bypass
an unknown-profile error.

Profiles are stored in `~/.aliyun/config.json` by default.

## Authentication modes

Configure authentication in the local terminal or browser. Follow the
[credential safety rules](../SKILL.md#safety-rules).

For setup instructions, see the
[official credential documentation](https://help.aliyun.com/zh/cli/configure-credentials/).

| Mode | Use |
| --- | --- |
| AK | Static AccessKey credentials. |
| StsToken | Temporary AccessKey credentials and a security token; refresh them when expired. |
| RamRoleArn | Assume a RAM role using an identity authorized to assume that role. |
| OAuth | Browser login and authorization. |
| EcsRamRole | An ECS instance with an attached RAM role. |
| RsaKeyPair | A configured RSA key pair and private-key file. |
| RamRoleArnWithEcs | An ECS role used to assume another RAM role. |

For user-run AK setup:

```bash
aliyun configure --mode AK --profile sls-work
```

For modes that require additional options, follow the mode-specific CLI help and
configuration instructions.

For browser login, run `aliyun configure --mode OAuth --profile sls-work`
and follow the authorization prompts.

## Credential precedence

For AK and StsToken authentication, each credential field resolves independently:
explicit CLI value → nonempty value in the selected profile → fallback environment value.

Environment values fill missing fields; they do not replace saved values.
Select the profile containing the intended credential set instead of mixing sources.

The standard fallback variables are `ALIBABA_CLOUD_ACCESS_KEY_ID`,
`ALIBABA_CLOUD_ACCESS_KEY_SECRET`, and `ALIBABA_CLOUD_SECURITY_TOKEN` (StsToken).
In managed environments, inject these values through the environment's secret manager.

Within each environment-variable row below, the first nonempty value wins:

| Field | Environment variables, highest priority first |
| --- | --- |
| AccessKey ID | `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABACLOUD_ACCESS_KEY_ID`, `ALICLOUD_ACCESS_KEY_ID`, `ACCESS_KEY_ID` |
| AccessKey secret | `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, `ALIBABACLOUD_ACCESS_KEY_SECRET`, `ALICLOUD_ACCESS_KEY_SECRET`, `ACCESS_KEY_SECRET` |
| Security token | `ALIBABA_CLOUD_SECURITY_TOKEN`, `ALIBABACLOUD_SECURITY_TOKEN`, `ALICLOUD_SECURITY_TOKEN`, `SECURITY_TOKEN` |

For authentication failures, see [troubleshooting](troubleshooting.md).

## Connection settings

Use command-line region and endpoint overrides for the task; see
[region and endpoint configuration](regions.md).
Save connection settings in a profile only when the user requests it.

For environments requiring a proxy, configure the relevant proxy variables:

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

Set `NO_PROXY` only for hosts that should bypass the proxy.
Proxy settings do not select the SLS service endpoint.
