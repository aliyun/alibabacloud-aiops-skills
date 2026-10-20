# OpenAgent Skill connection setup

Use this guide when no valid connection exists or the user explicitly wants to change one. Existing valid settings apply across host conversations; do not ask each session to configure again.

## Select and save

1. Run `setup status`. If needed, run `bootstrap` with the same absolute entry and check status again. If `local_state_read` is false, the saved connection is still unknown; do not treat it as absent or overwrite it. Reuse its credential-presence summary; `credentials inspect` can check presence even before dependencies are prepared, without reading credential contents or contacting the cloud. Inspect again only after the user prepares a source or when that summary is unavailable.
2. Ask for the OpenAgent service region and credential source unless the user has already explicitly selected them. Explain that the service region is separate from resource locations. The supported service regions are Hangzhou (`cn-hangzhou`) and Singapore (`ap-southeast-1`).
3. If the chosen source is not ready, have the user prepare it privately, then recheck presence. Use `describe credentials` for supported sources and exact field names. Environment credentials use `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET`; never request their values in chat. Profiles need the actual profile name. Do not inspect other profiles or fall back to a different source.
4. Save the explicit choices using `setup configure --text <connection-json>` or `--input-file <path>` (`-` reads standard input). This is **OpenAgent Skill connection configuration**, a local save with no cloud control or model-key calls. The choices themselves authorize that local save; do not introduce a second plan-confirmation step.

Example after the user has chosen Hangzhou and environment credentials:

```json
{
  "connection": {
    "region": "cn-hangzhou",
    "credentials": {"kind": "environment"}
  }
}
```

The endpoint is derived as `openagent.${regionId}.aliyuncs.com`. Users do not provide an endpoint or a model ID. Ask only for missing choices; do not infer Hangzhou from a request to list Hangzhou resources.

If either choice is declined, skipped, or unanswered, stop setup and the account task. A later request to continue may reuse the user's explicit choices, but never invent a missing one. On success, continue the original business task; an online diagnostic is not a routine prerequisite. For connection failures, follow [connection and result troubleshooting](tasks.md#connection-and-result-troubleshooting).

## Credentials in desktop apps

The selected official SDK provider handles supported refresh and federation. A desktop app's command environment must actually contain the selected credentials. Exporting values in another terminal does not update an already running app. Guide the user to their host's private credential preparation, then verify presence from the app's real command environment without printing secrets. Do not change machine-wide environment settings or read credential files to compensate.

## Local files and migration

User-readable `config/connection.json` stores connection choices only. The client stores local conversation bindings, submission references, and recovery journals separately in state. It does not persist cloud account controls, model settings, or an approved cloud baseline. `setup status` shows the platform's resolved config, state, data, cache, and runtime paths. Linux follows XDG overrides; macOS and Windows use platform directories. Locked Python environments belong outside the installed skill.

Recognized older connection settings are migrated without creating a cloud conversation; existing supported region and source choices are reused. Old cloud-control snapshots, setup plans, and update preferences do not govern the connection. Migration does not authorize a new cloud action. Existing saved task bindings retain their original connection scope: after an explicit region or source change, restore the original connection before recovering an old task rather than silently attaching it to the new account or region.

## Invocation identity (optional host integration)

By default, each client invocation creates a fresh 32-hex User-Agent identifier; users do not configure it. Hosts that need to correlate command subprocesses within one conversation may generate a distinct `SKILL_SESSION_ID` for each host conversation and inject it only into that conversation's subprocesses, never machine-wide environment or user configuration. Requests and retries within one Transport keep the same identifier; it does not select a business Session or Run.
