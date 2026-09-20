---
name: alibabacloud-dts-doc-parse
description: Use Alibaba Cloud DTS-AI for end-to-end parsing of local PDF, DOCX, PPTX, and image files such as JPEG, JPG, and PNG into Markdown files. Use when the user mentions DTS-AI document parsing or wants to parse, convert, or extract local PDF, Word, PowerPoint, JPEG, JPG, or PNG files into Markdown.
---

# Document Parsing

## Capabilities and supported formats

Use `dtscli doc parse` to parse supported local files into Markdown and deliver the final files to the user. Cloud jobs and their recovery mechanism are internal implementation details; in the normal workflow, never ask the user to inspect, select, or resume a job.

Parse readable, non-empty local files with these extensions: `pdf`, `docx`, `pptx`, `png`, `jpg`, and `jpeg`.

## Cloud processing and safety boundaries

- Start parsing only when the user explicitly requests that DTS-AI or this Skill parse specified local files, or explicitly confirms after being informed that the workflow requires cloud processing. Authorization covers the upload and cloud processing required for the current request. Never upload a file by itself or process a file the user did not specify.
- Never print, log, or expose the API key or temporary OSS credentials.
- Read credentials only through `dtscli`. Read [DTS-AI authentication](references/dts-ai-authentication.md) when the API key is missing, setup is required, or authentication fails.
- Save the Markdown written by `dtscli`. The CLI already converts HTML tables to GFM and strips nested HTML bold; do not rewrite the file again. After a timeout, interruption, save failure, or indeterminate result state, read [parser job execution and result handling](references/parser-job-execution.md).

## Runtime and authentication setup

Require `dtscli` on PATH. macOS, Linux, and Windows are supported. When the shell reports `dtscli: command not found`, read [platform installation and command execution](references/runtime-platforms.md) to select the installer, paths, and shell syntax for the actual host.

In the current user session, run `dtscli version --json` only the first time this Skill is used. Confirm that capabilities contains `skills.ensure`, then run:

```bash
dtscli skills ensure --agent <agent>
```

Then run `dtscli ai check`. Later steps and sub-agents in the same session run business commands directly. Continue when `ready=true`, including `action=busy`. Stop and reload Skill files when `reload_required=true`. When `ready=false` without reload, read [automatic Skills updates](references/skills-updates.md).

`--agent` names the current host. `skills ensure` uses it to select the install directory; `doc parse` / `doc resume` send it as the DTS-AI call source. The values are the same.

| Current host | `--agent` |
| --- | --- |
| Codex | `codex` |
| Claude / Claude Code | `claude` |
| Cursor | `cursor` |
| ZCode | `zcode` |
| Qoder | `qoder` |
| QoderWork | `qoderwork` |
| Qwen Code | `qwencode` |
| QwenWorkCN | `qwenworkcn` |
| OpenCode | `opencode` |
| Kimi | `kimi` |

When the current host can be identified, always supply `--agent`. The value must match `[a-z][a-z0-9_-]{0,31}`. An unlisted host uses its own stable lowercase identifier. If the host cannot be identified at all or the CLI rejects the value, read [calling agent source](references/agent-source.md). Replace `<agent>` in the examples below with the current host identifier.

Standard output carries only the final JSON result object and step-by-step progress goes to standard error, so standard output can be piped straight into a JSON parser. On failure, standard output holds an object containing `error_class` and the exit code is non-zero.

If the CLI is missing, obtain installation authorization and follow [platform installation and command execution](references/runtime-platforms.md).

Then run `dtscli version --json` to verify the version and continue the local authentication check. Never fall back to another way of calling DTS-AI or ask for an API key in chat.

If the key is absent, read [DTS-AI authentication](references/dts-ai-authentication.md) before offering:

```bash
dtscli ai setup --language <en|zh>
```

## Request identity

Before any cloud API invocation, read [request identity](references/request-identity.md) and `references/manifest.json`. Use only its top-level non-empty string `name` as `{skill-name}` and only its top-level non-empty string `version` as `{skill-version}`. The `name` must match this Skill's frontmatter `name` and the skill directory name. If missing or invalid, STOP. NEVER invent, guess, or reuse a name or version from another skill.

Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder.

Attach `--user-agent` only to `dtscli` commands that call an OpenAPI and accept `--user-agent`. Exact user-agent with skill version propagation across CLI/SDK/Terraform:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dts-doc-parse/{session-id} skill-version/{skill-version}"
```

## Output files and internal recovery

When `--output` is omitted, write `<input-name>.md` beside the input file, such as `report.pdf.md` next to `report.pdf`. If that name is occupied by a different document, the command appends the first eight characters of the input SHA-256, such as `report.pdf-a1b2c3d4.md`. Recovery records stay in `.aliyun-dts/doc-parse/` under the current user's home directory. If the input directory is not writable, the command falls back to that home directory. Another output directory must already exist and must be explicitly selected by the user.

Never replace an unrelated existing output without an explicit `--force` request. The command first uses the input SHA-256 plus the current `output_schema` to detect a reusable result; when found, it reuses that file without uploading again and reports `reused` as `true`. A saved result from an older dialect is not reused. If the user asks to parse again but not to overwrite an unrelated file, use `--revalidate`. If the user specifies a new `--output`, the command atomically copies a reusable result to that path; it still stops if the target exists and never renames or replaces it automatically. Never use `--force` unless the user explicitly requests another parse that may overwrite the target. Read [parser job execution and result handling](references/parser-job-execution.md) when handling overwrite, reuse, or an output conflict.

In a sandbox that cannot write beside the input or to the home-directory fallback, ask the user for a writable destination or rerun in an environment with write access.

## Document parsing workflow

### Parse a single file

`--input` is required and specifies one local file; `doc resume` requires `--job-id`. Omit `--output` unless the user selected a destination:

```bash
dtscli doc parse --input "/absolute/path/to/<input-file>" --agent <agent>
```

For a user-selected existing directory:

```bash
dtscli doc parse --input "/absolute/path/to/<input-file>" --agent <agent> \
  --output "/absolute/existing-dir/<output-file>.md"
```

The command waits end to end for parsing to finish and saves the result. It waits up to five minutes by default; adjust that with `--poll-timeout`.

After a successful `doc parse` or `doc resume`, tell the user only the Markdown output path and any necessary result notes; never expose the JobId, job state, resume command, or recovery records. Repeat the successful JSON `output` field exactly, including the original extension and any short hash the CLI appended; do not rewrite the filename, report only the input path, or replace the path with a content summary. On success, the object on standard output carries `job_id`, `output`, and `reused`. On failure the process exits with a non-zero code and emits no such object.

### Internal recovery after an exception

Only after a timeout, interruption, save failure, or indeterminate result state, retain the JobId from the command output and resume within the same request without another upload:

```bash
dtscli doc resume --job-id "<JobId>" --agent <agent>
```

A successful resume returns `job_id` and `output`. When `--output` is omitted, the command uses the recorded path and stops if no matching valid record exists. When locating a resumable parse, list local recovery records, which contain no secrets, without a network request:

```bash
dtscli doc history
```

The output is an array of records, each with `job_id`, `state`, `input`, `output`, and `time`. Read [parser job execution and result handling](references/parser-job-execution.md) when checking an API response or recovery record, handling an abnormal state, or responding to a timeout, interruption, or save failure, and prefer to complete recovery autonomously. Only when the final file cannot be delivered in the current request, tell the user that parsing did not complete and what they can do next. Never require the user to understand or operate a JobId, `doc history`, or `doc resume` unless troubleshooting requires it.

### Process multiple files and multipage documents

Treat a multi-page document as one file, one job, and one output. Never split it automatically. The parser separates PDF pages with `---`; it does not rejoin sentences across page boundaries.

`dtscli doc parse` accepts one file per call. Parse multiple independent files sequentially, one job and output per file. A failure does not invalidate earlier outputs. When `--output` is omitted, let the command generate stable, non-overwriting names under the rule above. Stop when a user-selected output path conflicts; never bypass that conflict with `--force`. Merge outputs only when the user explicitly requests it. After each file, report that command's `output` path exactly.

## Official API documentation

- [Use the DTS-AI API to parse documents](https://help.aliyun.com/en/dts/use-cases/use-dtsai-api-to-parse-documents)
- [CreateDocParserJob](https://help.aliyun.com/en/dts/developer-reference/api-dtsai-2026-04-01-createdocparserjob)
- [DescribeDocParserJobStatus](https://help.aliyun.com/en/dts/developer-reference/api-dtsai-2026-04-01-describedocparserjobstatus)
- [DescribeDocParserJobResult](https://help.aliyun.com/en/dts/developer-reference/api-dtsai-2026-04-01-describedocparserjobresult)
