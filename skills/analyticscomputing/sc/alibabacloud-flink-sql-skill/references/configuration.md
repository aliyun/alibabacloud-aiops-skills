# Configuration and Authentication

Read when the next lifecycle step needs to query or modify cloud resources. Platform configuration is unnecessary for local-only SQL design, authoring, or explanation.

## Configuration Sources and Precedence

The unified entry point resolves `workspace`, `namespace`, and `region_id` in this order:

1. Command arguments: `-w`, `-n`, and `-r`
2. Environment variables: `FLINK_WORKSPACE`, `FLINK_NAMESPACE`, and `FLINK_REGION_ID`
3. Local file: `assets/flink-sql-manager.json`

Set `FLINK_SQL_MANAGER_CONFIG` to use another JSON file, including an existing configuration from an older installation. See [the configuration example](../assets/flink-sql-manager.example.json).

The configuration file stores the resource scope and optional Git repository URL, local path, and branch. It does not store an AccessKey ID, AccessKey secret, OAuth token, STS token, Git token, password, or private key. The real configuration file is excluded by `.gitignore`.

## First-Time Initialization

Install the [dependencies](#install-dependencies) with the same Python interpreter used by the CLI, then run `config_doctor` before the first Ververica OpenAPI call. If the result reports a missing workspace, namespace, or region:

1. Reuse real scope values already provided in the current request and ask only for a missing workspace, namespace, or region.
2. Ask whether to enable Git synchronization. If enabled, obtain the repository URL and optionally a local path and branch, whose defaults are `/tmp/vvr-sql-sync` and `main`. Do not ask for a Git password, token, or private key.
3. Run `config_init` once with the selected settings, then run `config_doctor` again. When enabling Git, append `--git-repo-url <repo-url>` to `config_init`; also append the applicable arguments when the local path or branch differs from its default.

```bash
python3 scripts/flink_sql_manager.py config_init \
  -w <workspace> -n <namespace> -r <region-id>
python3 scripts/flink_sql_manager.py config_doctor
```

When Git is disabled, omit all Git arguments. Repository access uses the local Git/SSH environment.

By default, `config_init` creates `assets/flink-sql-manager.json` with one resource scope and optional Git configuration:

```json
{
  "region_id": "cn-beijing",
  "workspace": "real Workspace ID",
  "namespace": "real Namespace",
  "git": {
    "repo_url": "git@example.com:team/flink-sql-deployments.git",
    "local_path": "/tmp/vvr-sql-sync",
    "branch": "main"
  }
}
```

The `git` object is optional. Without `--git-repo-url`, it is not written and synchronization remains disabled. The command neither reads nor stores cloud or Git credentials and does not call the Flink API. Later commands use the file's scope by default, so `-w/-n/-r` need not be repeated. If `FLINK_SQL_MANAGER_CONFIG` is set, the command creates the file referenced by that variable. See [git-sync.md](git-sync.md) for complete Git rules.

When a configuration exists, `config_init` returns `ConfigurationExists` by default and does not silently overwrite it. If replacement is required, explain that the entire configuration will be replaced and obtain agreement before appending `--overwrite` to `config_init`. To preserve, enable, or change Git synchronization, pass the complete Git settings at the same time; omitting the repository URL disables existing Git synchronization.

The current skill does not maintain multiple named configurations. Command arguments and environment variables are explicit temporary overrides and do not append to or modify the local file.

## Skill Identity and Session

Before cloud operations (including `config_doctor` and Cookie-based Metrics), read this skill's [manifest.json](manifest.json). It is the source of the skill name and version. If it is missing, unreadable, or invalid, stop and restore the manifest; never guess a version or fall back to an unversioned User-Agent.

Generate `SKILL_SESSION_ID` once per Agent session, unless that session already has a valid ID:

```bash
export SKILL_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
```

Pass this environment variable to every CLI invocation in the session, including subprocesses. It must contain exactly 32 lowercase hexadecimal characters; do not regenerate it for each command. Start a new ID for a new Agent session.

SDK and console requests use `AlibabaCloud-Agent-Skills/alibabacloud-flink-sql-skill/{session_id} skill-version/{version}`. The SDK may also append its runtime identifiers. Each request re-reads the local manifest; SDK clients are cached by region and complete skill identity. When switching skills, read the newly selected skill's own manifest and rebuild its User-Agent; never carry over another skill's name, version, client, or custom User-Agent. The session ID remains shared within the same Agent session.

`SkillIdentityError` stops the request before transmission. Repair the manifest or session environment according to the error, then retry. Local `--help`, `config_init`, and offline SQL authoring do not require this identity gate.

## Authentication

Ververica OpenAPI uses the Alibaba Cloud SDK default credential chain, including an aliyun CLI profile, RAM Role, STS credentials, and standard environment variables. Historical Metrics use separate Cookie authentication described in [job-observability.md](diagnosis/job-observability.md) and do not require SDK credentials or `config_doctor`. OAuth is recommended for personal development environments:

```bash
aliyun configure --mode OAuth --profile default
```

`region_id` is an API region. For example, the console host `flink-cn-beijing.data.aliyun.com` maps to `cn-beijing`. It is neither an availability zone nor a workspace ID.

Do not ask the user to paste an AccessKey ID or AccessKey secret into the conversation. Do not read or echo credential values, and never put real credentials in command examples.

## Preflight Check

```bash
python3 scripts/flink_sql_manager.py config_doctor
```

`config_doctor` checks the local scope configuration, optional Git settings, and the `git` executable, and resolves cloud credentials through the default credential chain. It does not call a Flink resource API, connect to the Git remote, or output credentials. When an OAuth token has expired, the OAuth provider may contact the identity service to refresh temporary credentials. Execute real platform commands only after the doctor check succeeds. When the scope is missing, save it through the first-time initialization flow; when authentication fails, let the user repair it locally and run the check again.

For a temporary scope switch, pass the scope directly. These arguments do not modify the configuration file:

```bash
python3 scripts/flink_sql_manager.py config_doctor \
  -w <workspace> -n <namespace> -r <region-id>
```

## Install Dependencies

```bash
python3 -m pip install -r assets/requirements.txt
python3 scripts/flink_sql_manager.py --help
```

## Common Errors

- `MissingCredentials`: no default credentials are available in the current shell; check the OAuth profile, RAM Role, or standard credential environment variables.
- `ConfigurationError`: a scope field is missing or the JSON is invalid; repair it according to the doctor output.
- `ConfigurationExists`: the configuration file already exists; verify the replacement target before using `config_init --overwrite`.
- `GitConfigurationError`: the Git repository URL, path, or branch is invalid; correct it according to [git-sync.md](git-sync.md).
- `GitSyncNotConfigured`: no Git repository URL has been provided, so Git synchronization is disabled.
- `Forbidden` / `AccessDenied`: authentication succeeded but RAM permissions are insufficient; add minimum permissions according to [ram-policies.md](ram-policies.md).
- Connection timeout: check the network, region, and endpoint; use `FLINK_SDK_CONNECT_TIMEOUT` and `FLINK_SDK_READ_TIMEOUT` to adjust timeouts in milliseconds.
