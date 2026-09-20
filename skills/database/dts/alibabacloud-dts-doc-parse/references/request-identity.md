# Request identity

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `name` as `{skill-name}` and only its top-level non-empty string `version` as `{skill-version}`. The `name` must match this Skill's `SKILL.md` frontmatter `name` and the skill directory name. If missing or invalid, STOP. NEVER invent, guess, or reuse a name or version from another skill.

Bind name, version, and session to the current skill and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. On a skill switch or return, reread that skill's manifest; never cross-skill reuse name, version, or session ID.

The session ID must be 32 lowercase hex characters with no hyphens. Do not use hyphenated `uuidgen` output unchanged.

This Skill reaches Alibaba Cloud APIs only through `dtscli`. Attach `--user-agent` with the exact value below only to `dtscli` commands that call an OpenAPI and accept `--user-agent`. Commands that do not declare `--user-agent` must not receive it, for example `dtscli version`, `dtscli skills ensure`, and `dtscli ai check`.

Exact user-agent with skill version propagation across CLI/SDK/Terraform:

```text
--user-agent "AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}"
```

Replace `{skill-name}` with the manifest `name`, `{skill-version}` with the manifest `version`, and `{session-id}` with the generated session ID.

Markdown examples in this Skill may omit the flag for brevity. The Agent MUST append the exact flag to every actual `dtscli` OpenAPI execution that accepts `--user-agent`, including commands generated or extended at runtime. This Skill's default path is `dtscli`. When a CLI, SDK, or Terraform client is used instead, attach that exact user-agent at the remote cloud-call boundary and propagate the skill version:

- CLI: include `--user-agent "AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}"` on every cloud API invocation, including `dtscli` OpenAPI commands.
- SDK: pass the same user-agent string to every SDK client or request.
- Terraform: set the same user-agent on every `provider "alicloud"` block.
