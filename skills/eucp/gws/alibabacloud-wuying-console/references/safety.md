# Safety Model

Supporting every command in the official plugin does not mean every command may run automatically. Classify the selected command using the generated catalog, then confirm against its live help and description.

## Read

Commands that only query or validate remote state may run without an additional confirmation after the user requests the task. Typical prefixes are `describe-`, `list-`, `get-`, and `query-`.

- Keep queries scoped to the requested account, region, and resource type.
- Paginate deliberately and avoid unbounded data exports.
- Treat downloaded files and export-task creation as non-read operations when they write locally or create remote jobs.

## Mutation

Commands that create, start, stop, reboot, renew, associate, attach, detach, modify, bind, unbind, assign, upload, tag, or otherwise change state require explicit confirmation immediately before execution.

Before asking, show:

- action and exact API command;
- account/profile and region;
- resolved resource names and IDs;
- important new values;
- whether service interruption, billing, or broad fan-out is possible.

Do not reuse confirmation from an earlier, materially different target set.

## Destructive

Commands beginning with `delete-`, `release-`, `reset-`, `rebuild-`, or `terminate-` are destructive by default. The same applies to any command whose live help says it removes data, releases resources, replaces disks/images, or resets state.

- Require an explicit confirmation that names the operation and target resources.
- Refuse wildcards, empty filters, or unresolved target lists.
- Re-query immediately before execution when the target list could have changed.
- Do not retry automatically after a timeout. Query state first to detect whether the operation was accepted.

## Dry run

`--cli-dry-run` validates local request construction and prints the request without sending it. Use it before risky operations when available, but do not describe it as completed work. Redact authorization headers, tokens, and credential material from any displayed dry-run output.
