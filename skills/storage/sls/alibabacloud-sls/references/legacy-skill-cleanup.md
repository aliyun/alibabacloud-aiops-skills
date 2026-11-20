# Legacy SLS skill cleanup

Use this workflow only when asked about legacy **skill installations**. It does not require the Aliyun CLI, change cloud resources, or run automatically after installation.

## Exact allowlist

The unified `alibabacloud-sls` skill replaces these eight skills. Match names exactly; never infer candidates from a prefix or wildcard.

- `alibabacloud-sls-query`
- `alibabacloud-sls-index-config-management`
- `alibabacloud-sls-alerting`
- `alibabacloud-sls-dashboard`
- `alibabacloud-loongcollector-ops`
- `alibabacloud-sls-agent-workflow`
- `alibabacloud-sls-cli-guidance`
- `alibabacloud-sls-sdk-guidance`

## Find and remove

1. Look for allowlisted skills directly under `~/.agents/skills` (global) or `.agents/skills` relative to the current project root (project), and nowhere else. The directory name and `SKILL.md` frontmatter `name` must both match the same allowlist entry.
2. For a lookup, report matching names and absolute installation paths, or report no matches. Do not delete anything.
3. Delete only if the user explicitly requests cleanup and `alibabacloud-sls` is installed.
4. Recheck each requested match immediately before removal. For a symlink, unlink the installation entry itself without a trailing slash; never recursively delete its resolved target. For a real directory, remove only that exact skill installation. Skip source checkouts, ambiguous paths, and any removal that would break the verified unified skill. Never remove a parent directory or an unlisted skill.
5. Check each attempted installation path is gone (including the link itself), then report removed, skipped, or failed paths. An absent legacy skill needs no action; the other seven need not be installed.
