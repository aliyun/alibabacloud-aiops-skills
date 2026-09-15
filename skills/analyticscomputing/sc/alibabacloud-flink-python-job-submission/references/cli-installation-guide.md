# Aliyun CLI Installation

Use `aliyun version` to check the installed version. This skill requires 3.3.3+
for product plugins.

For a first installation or major upgrade on macOS or Linux:

```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
aliyun version
```

For a routine update when CLI 3.3.5+ is already installed:

```bash
aliyun upgrade
aliyun version
```

Configure credentials outside the agent conversation using `aliyun configure`
or the supported credential environment variables. Check profile availability
with `aliyun configure list`; keep credential values out of commands and output.

The Python SDK uses `CredentialClient` and its credential provider chain.
If CLI commands succeed but SDK authentication fails, configure a supported SDK
provider outside the conversation, such as environment credentials, the
`~/.alibabacloud/credentials` file, or an ECS RAM role.

Follow the conversation-scoped initialization and user-agent instructions in
`SKILL.md` before the first cloud command.
