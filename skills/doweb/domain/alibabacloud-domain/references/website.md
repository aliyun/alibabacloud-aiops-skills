# Wan Xiao Zhi website building

All AI website capability is under `aliyun domain wxz`. Supported DomainCLI versions use thematic commands: `wxz <theme> --operation <operation>`. Use `project --operation list` first when a site ID is not already known. Its returned `bizId` is the stable project identifier used by most other commands.

If the user supplies a `bizId`, conversation ID, chat ID, domain, or channel, freeze it for the operation. `project --operation list` may resolve an identifier only when the user did not provide one and gave an unambiguous selector; otherwise ask the user to choose. A different visible project is never a substitute for a missing, unauthorized, or inaccessible requested project.

## Core workflow

1. Inspect available inspiration with `aliyun domain wxz account` when quota matters.
2. Start a requirement conversation with `aliyun domain wxz chat-start --message "为一家咖啡店创建官网"`. The first run is a preview; creating the conversation and site requires `--confirm=true` after user approval.
3. Capture `conversationId`, `chatId`, event state, and any new `bizId` from output.
4. If the stream requests user input, use `chat-resume`. After requirements are approved, use `chat-generate`. If the stream disconnects before the turn ends, use `chat-reconnect`.
5. Use `preview` to obtain a preview URL. Do not describe preview as production publication.
6. Read `project --operation show` for the requested `bizId`, then use `aliyun domain wxz deploy --operation publish` to preview publication for that same project. Require structured preview success, obtain user confirmation, then rerun that same leaf with `--confirm=true`.
7. Follow deployment with `deploy --operation status`; use `deploy --operation history` for prior versions and `deploy --operation rollback` only after a separate rollback confirmation. Observe the bounded wait contract; manual input, review, or a pending deployment is a handoff, not an indefinite polling loop.

No stage automatically performs the next one. Inspect each leaf's `--help` for the exact IDs and flags.

## Command families

| Intent | Commands |
|---|---|
| Quota | `account` |
| Projects | `project --operation list`, `show`, `delete` |
| Conversation and generation | `chat-start`, `chat-send`, `chat-history`, `chat-resume`, `chat-generate`, `chat-reconnect` |
| Conversation administration | `conversation --operation list`, `show`, `lock-status` |
| Preview | `preview` |
| Publish and rollback | `deploy --operation publish`, `status`, `history`, `rollback` |
| Site availability | `site --operation online`, `offline` |
| Bound domains | `site --operation domain-list`, `domain-show`, `domain-bind`, `domain-unbind`, `domain-dns`, `domain-cert`, `domain-redirect-list`, `domain-redirect-delete`, `domain-icp` |
| Generated code | `code --operation tree`, `cat`, `rollback` |
| Material directories | `material-directory --operation tree`, `create`, `rename`, `move`, `delete` |
| Material files | `material-file --operation list`, `show`, `summary`, `archive`, `status`, `rename`, `move`, `export` |
| Draft content | `content --operation article-save`, `image-save`, `video-save` |
| Website plugins | `skill --operation list`, `show`, `cat`, `versions`, `install`, `uninstall`, `create`, `upload`, `update`, `rollback`, `delete` |
| Analytics | `analytics-daily` |

In each thematic row, every listed operation repeats the preceding theme and `--operation`; for example `wxz project --operation show`, not `wxz show` or `wxz project show`. Inspect `wxz <theme> --help` for operation-specific flags. Some help parameter descriptions still mention legacy names such as `project-list`; select the current theme/operation shown in root help instead of executing those legacy references.

Plugin scope is part of the frozen target. A request for `scope=mine` must not fall back to `public`, and a public-marketplace read must not substitute a private plugin. If the requested list/read returns a non-retryable failure or does not yield the required `pluginId` and version, stop that path without `whoami`, alternate-scope discovery, repeated flag combinations, evaluator-file inspection, or a fabricated preview. Plugin install, uninstall, create, upload, update, rollback, and delete remain separate writes; preview each exact target and obtain a fresh confirmation without executing or downloading plugin contents.

## Domain and filing distinctions

- `wxz site --operation domain-bind` associates a hostname with a Wan Xiao Zhi project; it does not register the domain. Binding steps (`--operate-type`) are separate actions; do not silently overwrite DNS with `--overwrite`.
- `wxz site --operation domain-dns` reports DNS records needed for binding or verification; use the DomainCLI DNS command group to modify Alidns records when modification is required.
- `wxz site --operation domain-cert` manages website certificate binding, not domain ownership verification. User certificate/key files must remain protected; do not read or print private-key contents.
- `wxz site --operation domain-icp` updates the site's displayed filing number; it does not create, submit, or approve an ICP filing. Use `aliyun domain icp` for filing workflows.
- Domain registration, filing, DNS verification, certificate issuance, domain binding, and site publication are separate states. Verify each separately.

## High-risk operations

The following need a preview, an explicit confirmation of the exact target, and a readback/status check:

- Creating a paid or quota-consuming conversation.
- Publishing, rolling back, taking a site online or offline.
- Binding or unbinding a domain, setting a certificate, deleting redirects.
- Deleting projects, directories, plugins, or other persistent resources.
- Replacing generated code or material state.

Never auto-confirm `--confirm=true`. Preserve exact `bizId`, domain, conversation ID, chat ID, channel, and requested operation between preview and execution. If state changes, re-preview.

If authentication fails, the requested project is not found, the preview fails, or the friendly `aliyun domain wxz` leaf is unavailable, stop that stage. Do not choose another project, call generated WebsiteBuild actions, or publish through raw OpenAPI, SDK, HTTP, or console automation.

## Safe examples

```bash
aliyun domain wxz project --operation list --page 1 --limit 20 --cli-ai-mode
aliyun domain wxz project --operation show --biz-id WS20260000000000000001 --cli-ai-mode
aliyun domain wxz chat-start --message "为域名服务团队创建一个官网" --cli-ai-mode
aliyun domain wxz preview --conversation-id CONVERSATION_ID --cli-ai-mode
aliyun domain wxz deploy --operation publish --biz-id WS20260000000000000001 --cli-ai-mode
aliyun domain wxz deploy --operation status --biz-id WS20260000000000000001 --cli-ai-mode
```

The IDs above are examples only. Never execute writes using fabricated identifiers.
