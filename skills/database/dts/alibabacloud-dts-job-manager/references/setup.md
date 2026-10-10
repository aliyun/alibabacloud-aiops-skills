# CLI Installation, Authentication, and Service Access

## Contents

- [Runtime requirements](#runtime-requirements)
- [Install or update the CLI and plugin](#install-or-update-the-cli-and-plugin)
- [Check the current CLI profile](#check-the-current-cli-profile)
- [Configure or recover CLI OAuth](#configure-or-recover-cli-oauth)
- [Validate the profile and service access](#validate-the-profile-and-service-access)
- [CLI execution rules](#cli-execution-rules)

<a id="runtime-requirements"></a>
## Runtime requirements

| Component | Required value |
| --- | --- |
| Runtime host | macOS, Linux, or Windows (amd64/arm64) |
| `dtscli` | Installed and on `PATH` |
| Alibaba Cloud CLI and DTS plugin | Both installed, with the plugin callable through the CLI; no minimum plugin version |

`dtscli` writes its result as JSON on standard output and progress on standard error. On failure, the exit code is non-zero. Standard output may contain a generic error with `error_class`, or retain the command-specific status or execution summary. Interpret the JSON under the relevant workflow; do not determine success from the exit code or one field alone.

If the CLI is missing, follow [platform installation and command execution](runtime-platforms.md) for the host installer, paths, and shell syntax.

Then run `dtscli version --json` to verify the version on PATH. This installation uses version directories and a pointer; check for updates with `dtscli upgrade --check` and run `dtscli upgrade` when the user requests an upgrade. Skill documentation and the CLI are installed separately.


<a id="install-or-update-the-cli-and-plugin"></a>
## Install or update the CLI and plugin

When either component is missing, run this once without asking the user, then continue the interrupted command. Do not add `--update`:

```bash
dtscli job deps install --yes
```

The command checks for the Alibaba Cloud CLI and the DTS plugin and installs whichever is missing. It leaves an already installed CLI alone, including an older CLI. Do not add `--update`, and do not replace the `aliyun` binary. The top-level `action` is `installed`, `updated`, `already_usable`, or `manual_steps_required`. Each `components` entry carries `name` (`aliyun-cli` or `dts-plugin`) and `state` (`installed`, `updated`, `present`, `outdated`, or `missing`); a discovered CLI can also include `path` and `version`. `already_usable` requires both components to be present; the CLI may still be marked `outdated`, meaning generic RPC calls may be unavailable, not that it has been upgraded.

Stop the current task only when a command's JSON output carries an `error_class` whose `message` contains `ERROR: unchecked version`. Preserve and report that error; afterward, do not run another `dtscli job` command or any `aliyun` command. The trigger is the `error_class` in the JSON, not the shell exit code: piping `dtscli` into `tail` or the like collapses the exit code to 0, while `error_class` is unaffected. A successful `dtscli doctor` check that mentions the same words is not that error; continue. Quote the CLI version from the `version` field of `dtscli job deps install`. Do not run `aliyun version`. Do not upgrade the Alibaba Cloud CLI or read the same data through another interface.

On macOS the command can install Alibaba Cloud CLI using Homebrew. On Linux/Windows, first install `aliyun` using the official instructions and add it to PATH, then run the command above to install the DTS plugin. When a component cannot be installed automatically, the output lists the manual steps. See the [official Alibaba Cloud CLI installation instructions](https://help.aliyun.com/en/cli/install-update-alibaba-cloud-cli).

<a id="check-the-current-cli-profile"></a>
## Check the current CLI profile

```bash
dtscli job auth status
```

Continue only when the result contains `status="OK"`, one non-empty `current_profile`, a non-empty `region`, `language` set to `zh` or `en`, and `auth_mode` set to `OAuth`, `StsToken`, or `AK`. These fields contain no secrets and do not prove that a DTS service request can authenticate.

How to read the remaining fields depends on `auth_mode`:

- `OAuth`: `site_type` must also be `CN` or `INTL`.
- `StsToken`: an empty `site_type` is expected. Do not stop for that reason, and do not replace the profile with OAuth.
- `AK`: an empty `site_type` is expected. Do not stop for that reason, and do not replace the profile with OAuth.

When `status` is not `OK`, how to read the other fields depends on the status. Under `INVALID` and `UNSUPPORTED_AUTH`, `current_profile`, `region`, `language`, `site_type`, and `auth_mode` hold the current profile's real values; the profile simply cannot be used. Under `EMPTY`, `NO_CURRENT`, `UNAVAILABLE`, and `UNPARSEABLE` those fields are empty because no usable configuration could be read. Never read an empty value as "the user configured an empty region".

`EMPTY` means no profile is configured. `UNSUPPORTED_AUTH` means the current profile is not OAuth, StsToken, or AK (for example EcsRamRole) and cannot be used by this Skill. `INVALID`, `NO_CURRENT`, `AMBIGUOUS_CURRENT`, `UNAVAILABLE`, or `UNPARSEABLE` means the current profile is unusable. Stop on any of these results. When authentication must be created or replaced, guide the user through OAuth in the next section only. Never guide, demonstrate, or configure StsToken or AK, and never request an AccessKey, STS token, or any other secret. Correct other issues and check again.

Each OpenAPI read times out after 10 seconds; there is no `--timeout` flag. The command never retries on its own, and never add an Agent retry loop. On failure it returns a fixed status above without raw output.

<a id="configure-or-recover-cli-oauth"></a>
## Configure or recover CLI OAuth

This Skill accepts an already-configured Alibaba Cloud CLI OAuth, StsToken, or AK profile. OAuth is the recommended setup path and corresponds to OAuth in [Configure credentials for Alibaba Cloud CLI](https://help.aliyun.com/en/cli/configure-credentials/). When no usable profile is configured, or the current profile is none of these methods, guide the user to configure OAuth only; never guide the user to configure StsToken or AK. Never read, copy, or migrate credential files. Never request, accept, or write an AccessKey, AccessKey Secret, or STS token. Launch OAuth only in these cases:

- Initial setup: `dtscli job auth status` returns `status="EMPTY"`. Complete the RAM OAuth prerequisites below first.
- Authentication-method replacement: the profile check returns `status="UNSUPPORTED_AUTH"`. Do not continue with the current profile; create or update an OAuth profile.
- OAuth recovery: the current `auth_mode="OAuth"` and the service check returns `category="AUTH_UNAVAILABLE"` or `service_failure_category="AUTH_UNAVAILABLE"`. Do not treat `PERMISSION_DENIED`, `NETWORK_ERROR`, `SERVICE_ERROR`, or an unclassified failure as unavailable OAuth authentication. When `auth_mode` is `StsToken` or `AK` and service authentication fails, the existing credential may be invalid; stop and tell the user to refresh the existing profile, or switch to OAuth if they explicitly choose that. Never configure StsToken or AK on their behalf.

The profile name is a local label, not the RAM identity.

### Complete RAM OAuth prerequisites

When configuring CLI OAuth for the current Alibaba Cloud account for the first time, or when browser authorization reports that the call is not authorized, guide the user to contact a RAM administrator and complete these steps in order:

1. Open the [RAM console Third-party Application page](https://ram.console.aliyun.com/applications?activeTab=ThirdParty) and sign in as a RAM administrator.
2. In the left navigation pane, choose **Integrations > OAuth (Preview)**, then open the **Third-party Application** tab.
3. Find `official-cli`. If it is absent, click **Provision Official Application**, select **Official CLI**, and complete installation; otherwise, skip installation.
4. Open the `official-cli` application details, select the **Assignments** tab, and click **Create Assignment**.
5. Add the RAM user or role that will complete OAuth authorization in the browser, then finish the assignment.
6. Ask the user to confirm that `official-cli` is installed and the target identity is assigned. Continue to profile settings and OAuth launch only after confirmation.

When giving this guidance, include both the RAM console link above and the [official Alibaba Cloud CLI OAuth credentials documentation](https://help.aliyun.com/en/cli/oauth-credentials) as clickable links. A RAM administrator normally installs `official-cli` only once per Alibaba Cloud account; each additional RAM user or role still requires an assignment. Never operate the RAM console for the user or request screenshots, page content, or authorization configuration details.

### Confirm profile settings

Before creating or updating a named profile:

1. Confirm the user's profile name.
2. Confirm the default region; never infer it from the current job or local environment.
3. Confirm the CLI language as `zh` or `en`.
4. Explain that the profile will be created or updated with these non-secret settings, then obtain explicit authorization. The sign-in site is derived from the language: `zh` is China site `CN`, `en` is international site `INTL`. Do not ask the user for a site type or pass one.

Preserve values the user already supplied and ask only for a missing or ambiguous choice. The user must state each value or explicitly confirm one complete set; “yes,” “okay,” and similar replies cannot select an unresolved option.

### Launch OAuth

After authorization, run:

```bash
dtscli job auth login \
  --profile <profile-name> \
  --region <region-id> \
  --language <zh|en>
```

The command executes `aliyun configure --mode OAuth --profile <profile-name>`. The OAuth subprocess receives only the `CN` or `INTL` value derived from the language; all later prompts use CLI defaults. The user must personally complete or cancel login and authorization in the system browser, and the agent never inspects or operates the authorization page. After the OAuth command succeeds, it runs the following constrained command to set only the confirmed non-secret values:

```bash
aliyun configure set \
  --profile <profile-name> \
  --region <region-id> \
  --language <zh|en>
```

The OAuth subprocess receives no input except the sign-in site, and the region-and-language subprocess disables stdin. Both subprocesses discard all raw stdout and stderr, and the command returns only documented status JSON. Never execute either command directly. Never request, expose, or inspect a browser URL, authorization code, token, AccessKey, CLI output, transcript, credential store, profile file, or token cache. Because the sign-in URL is never displayed, stop and report a timeout if the system browser does not open; never ask the user to provide or copy the URL.

`OAUTH_COMMAND_STARTED` means only that the local OAuth command started. `COMPLETED` means the OAuth command and the region-and-language configuration command both exited successfully; it does not prove DTS service access. On `FAILED`, `UNAVAILABLE`, `TIMEOUT`, `CONFIGURATION_FAILED`, `CONFIGURATION_UNAVAILABLE`, `CONFIGURATION_TIMEOUT`, or `UNSUPPORTED_PLATFORM`, stop without guessing another CLI command or asking for raw output.

After `COMPLETED`, validate the same profile as described below. Retry a failed read at most once after authentication recovery. Before retrying a management operation, query current state and repeat its review.

<a id="validate-the-profile-and-service-access"></a>
## Validate the profile and service access

### Validate profile settings

An already-configured StsToken or AK profile with `status="OK"` does not need `job auth login`. After confirming `auth_mode` is `StsToken` or `AK`, continue with business commands.

After an OAuth sign-in, read the current profile back and compare each value against what was chosen at login:

```bash
dtscli job auth status
```

The command takes no expected values; it reports the profile's real values and this Skill compares them.

| Output field | Success condition |
| --- | --- |
| `current_profile` | Matches the name passed to `job auth login --profile` |
| `region` | Matches the region passed to `job auth login --region` |
| `language` | Matches the `zh` or `en` passed to `job auth login --language` |
| `auth_mode` | `OAuth` |
| `site_type` | `CN` for `zh`, `INTL` for `en` |

Continue only when every field matches and the result contains `status="OK"`. Stop and name the differing field when any of them does not match. Later business commands (`job price`, `job list`, `job get`, `job create test`) expose whether the DTS service is reachable; do not run a separate probe.

<a id="cli-execution-rules"></a>
## CLI execution rules

API version, command format, and allowed scope are defined in the [API allowlist](api-allowlist.md). During configuration checks also observe:

- Use the valid active profile. Apart from `job auth login`, cloud `job` commands do not accept `--profile`. If the current identity is wrong, sign in or switch the Alibaba Cloud CLI's current profile first. Pass the region flags documented by the applicable workflow.
- Do not bypass `dtscli` to invoke a generic RPC that it wraps.
- Do not change profile, region, API version, or authentication source to make a request pass.

Stop the current workflow when the CLI returns `unknown flag`. This error indicates only an incompatible parameter format; it is not evidence of an authentication or permission problem.
