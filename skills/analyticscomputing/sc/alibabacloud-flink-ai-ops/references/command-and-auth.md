# Command and Auth

## Standalone Installation and Runtime

Follow the [installation steps](../SKILL.md#2-installation) to create `.venv` and install the dependencies in the skill root. Use the local interpreter with `--help` to inspect the command syntax.

```bash
.venv/bin/python scripts/flink_ai_ops_cli.py --help
```

The SDK resolves existing credentials through its default chain. Run `scripts/flink_ai_ops_cli.py` as the entry point. The implementation lives in `scripts/flink_ai_ops/`. Resolve relative paths from the skill root.

`chat.py` and `patrol.py` each register commands and validate business input. `cli.py` uniformly parses common parameters, completes validation before creating the client, then dispatches execution and prints JSON. `client.py` centrally maintains SDK client creation, credentials, regional endpoints, User-Agent, default timeouts, and SDK retry configuration. `sdk.py` reuses that configuration for the signed requests and read retries of the six APIs. `common.py` shares validation and body parameters, and `redaction.py` redacts at the output boundary. When extending commands, maintain the workflow they belong to. Copying the whole directory makes it self-contained.

## Environment Routing

Business commands always route to the production endpoint `ververica.{region}.aliyuncs.com` derived from the `-r` region; no pre-release or test environment entry point exists. Pre-release console links (`pre-flink-*.data.aliyun.com`) are out of scope; if the user provides one, state that this skill supports production only.

## Credentials and Authorization

Run the business command when its parameters and authorization are ready. Set `SKILL_SESSION_ID` and `SKILL_VERSION` as described in [SDK Request Tracing](../SKILL.md#7-sdk-request-tracing). The script checks both values before initializing credentials and uses the manifest version to construct the SDK User-Agent.

The default credential chain can use an existing local credential file, a RAM role, or temporary credentials; do not conclude credentials are missing merely because environment variables are unset. Only when credential resolution ultimately fails, guide configuration per `MissingCredentials`. Insufficient permissions, expired credentials, and similar cases keep their real error codes; do not relabel them as missing credentials.

When credentials are missing, the user sets their own credentials in the terminal where the execution process is started. The values below are redacted placeholders — they must not be executed as-is, and the user must not be asked to send real values into the chat.

When delivering a `MissingCredentials` outcome to the user, include the environment-variable code example below in the reply, mark the token line as STS-only, and attach the official link plus the process environment-inheritance note.

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID='***REDACTED***'
export ALIBABA_CLOUD_ACCESS_KEY_SECRET='***REDACTED***'
export ALIBABA_CLOUD_SECURITY_TOKEN='***REDACTED***'
```

The last item is required only for STS temporary credentials. The executing process must inherit the new environment; exporting in another terminal does not update an already-started process. When offering this quick example, also provide the [official Python SDK credential configuration docs](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials) so local credential files, roles, or OIDC can be used. Never solicit, print, write into the repository, or auto-configure credentials.

## Common Parameters and Output

```text
SKILL_SESSION_ID=<trace-id> SKILL_VERSION=<skill-version> \
python3 scripts/flink_ai_ops_cli.py <command>
  -w <actual-workspace> -n <actual-namespace> -r <actual-region>
  [--connect_timeout SECONDS] [--read_timeout SECONDS]
```

The angle-bracket values above are placeholders only and must not be used for cloud calls. `workspace`, `namespace`, and `region_id` are required for every business command; collect the real values first when they are missing.

Timeout parameters are in seconds. `--connect_timeout` defaults to 10 seconds. `--read_timeout` controls how long to wait for data and defaults to 300 seconds for the AI assistant and 60 seconds for patrol; it can be overridden explicitly. The command-level `--timeout` limits an entire Chat collection round or patrol wait, defaulting to 300 seconds. `--poll_interval` defaults to 5 seconds.

The SDK client disables automatic retries; the wrapper retries at most once for retryable transient read errors. Chat, Trigger, and PATCH are never replayed. A failed write may leave the result uncertain: keep the received events, verify read-only against the actual resource, report, or configuration, and never retry blindly. This version has no session-state query command.

Default output JSON envelope:

```json
{
  "success": true,
  "operation": "get_patrol_config",
  "data": {},
  "error": null,
  "request_id": ""
}
```

This is a structural sketch, not a real response. On failure, keep `error.code`, the redacted `error.message`, `request_id`, and any partial results available; a non-zero exit code means the command did not finish successfully. `request_id` may be empty when the API did not return one and must never be fabricated.

## Command Parameters and API Mapping

For business parameters, enums, defaults, and official API mappings, select Related Commands from the main skill's [Reference Links](../SKILL.md#13-reference-links).
