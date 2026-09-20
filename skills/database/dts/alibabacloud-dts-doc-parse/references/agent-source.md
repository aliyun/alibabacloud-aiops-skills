# Calling agent source

Before running `dtscli web search`, `dtscli web fetch`, `dtscli doc parse`, or `dtscli doc resume`, identify the agent host actually executing this Skill and supply `--agent <agent>` on every invocation. The CLI sends it to DTS-AI as the `AgentName` query parameter. `--agent` on `skills ensure` and `skills install` only selects the Skills directory.

## Choosing a value

Use trusted platform identity in the current session or information explicitly supplied by the host. A model name, a workspace `CLAUDE.md` / `AGENTS.md`, a Skill installation path, or installed applications alone cannot establish the current host. For example, Cursor using a Claude model still sends `cursor`; OpenCode using a Qwen model still sends `opencode`. This Skill can run on multiple platforms; on every call, fill `--agent` with the current host.

When the current host can be identified, always supply `--agent`. The table lists common hosts:

| Current agent host | `<agent>` |
| --- | --- |
| Codex | `codex` |
| Claude / Claude Code | `claude` |
| Cursor | `cursor` |
| ZCode | `zcode` |
| Qoder | `qoder` |
| QoderWork | `qoderwork` |
| Qwen Code | `qwencode` |
| Qwen Work (China) / QwenWorkCN | `qwenworkcn` |
| OpenCode | `opencode` |
| Kimi | `kimi` |

An unlisted host still sends its own stable lowercase identifier, such as `foo` when Skills live in `~/.foo/skills`. Qwen Code sends `qwencode`; do not rewrite it as `qwen` or `qwenworkcn`. The value must match `^[a-z][a-z0-9_-]{0,31}$`: start with a lowercase letter, then lowercase letters, digits, hyphens, or underscores, at most 32 characters. Never guess or fabricate attribution, and never send `unknown`, a model name, or the literal placeholder.

Omit the parameter only when the host cannot be identified at all. The CLI defaults to an empty value (no `AgentName` parameter). Nonempty values that fail the pattern fail with `usage` before credential access or API calls.

## Calls and recovery

- Replace `<agent>` in all relevant command examples with the current host's value. This rule also applies to calls that omit the flag in reference documents.
- Within one CLI invocation, search, batch fetch, upload authorization, parser-job creation, status polling, result retrieval, and automatic retries all carry the same source. OSS file uploads and result downloads are not DTS-AI API requests and do not receive this parameter.
- When resuming a parse, select the host currently performing recovery, rather than the host that originally created the job. The CLI does not persist attribution in global configuration or recovery records, preventing shared installations from retaining another platform's identity.
- Local commands such as `ai check`, `ai setup`, and `doc history`, and the `job` management commands do not accept this parameter.
- If the CLI reports that `--agent` has an unsupported form, follow the Skill's CLI installation and upgrade workflow before proceeding. Never silently remove attribution for an identified host.

API basis: `Client.java` from the official Maven artifact `com.aliyun:dtsai20260401:1.1.2`; all six DTS-AI actions put `AgentName` in the query string.
