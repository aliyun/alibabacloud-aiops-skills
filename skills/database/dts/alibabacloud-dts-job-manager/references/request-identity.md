# Request identity

Construct the request identifier using the `{skill-name}` and `{skill-version}` already validated for the current skill.

Bind name, version, and session to the current skill and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. Never reuse a name, version, or session ID across skills.

The session ID must be 32 lowercase hex characters with no hyphens. Do not use hyphenated `uuidgen` output unchanged.

This Skill reaches Alibaba Cloud APIs only through `dtscli`. Attach the exact `--user-agent` value below only to `dtscli` subcommands that send a request to the cloud and declare `--user-agent` themselves. Commands that send no cloud request never declare it: installation, upgrade, version probing, diagnostics, authorization and sign-in status, credential collection, and any preparation or review step completed locally. Passing the flag to a command that does not declare it exits with a `usage` error instead of being silently ignored.

Exact user-agent with skill version propagation across CLI/SDK/Terraform:

```text
--user-agent "AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}"
```

Replace `{skill-name}` and `{skill-version}` with the current skill's validated name and version, and `{session-id}` with the generated session ID.

Markdown examples in this Skill may omit the flag for brevity. The Agent MUST append the exact flag to every actual `dtscli` OpenAPI execution that accepts `--user-agent`, including commands generated or extended at runtime. This Skill's default path is `dtscli`. When a CLI, SDK, or Terraform client is used instead, attach that exact user-agent at the remote cloud-call boundary and propagate the skill version:

- CLI: include `--user-agent "AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}"` on every cloud API invocation, including `dtscli` OpenAPI commands.
- SDK: pass the same user-agent string to every SDK client or request.
- Terraform: set the same user-agent on every `provider "alicloud"` block.
