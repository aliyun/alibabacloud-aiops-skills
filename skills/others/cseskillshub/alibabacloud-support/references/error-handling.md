# Error Handling Contract

The client classifies every failure into exactly one of three outcomes, and the outcome
decides whether a retry is allowed at all.

## Outcome model

| Outcome | Detected by | Client behaviour | Retry allowed |
|---|---|---|---|
| Deterministic rejection | process exit `0` with `Success: false`, or a non-zero exit whose body is a valid `Success: false` envelope | `ClientError` with the redacted `Code`, `Message` and `RequestId` | yes, only after the input is actually corrected |
| Indeterminate result | process timeout, user interrupt, abnormal exit without a verifiable envelope, non-JSON stdout, non-object JSON, missing or invalid `Success`, `Success: true` with an error `Code`, or a successful envelope with no resolvable ticket id | `WorkorderIndeterminateError` | never automatic |
| Success | exit `0` and `Success: true` with `Code` in {`0`, `200`} | normalized JSON | — |

`CreateTicket`, `ReplyTicket`, `CloseTicket` and `EvaluateTicket` are the non-idempotent set.
For them, an indeterminate outcome is terminal for the run: the client states that the result
is unknown and forbids a repeat call. `CreateTicket` is the only one with an automatic
reconciliation pass.

## Create reconciliation

Triggered when `CreateTicket` did not produce a verifiable ticket id. One pass, no repeat
write:

1. `list-tickets` over the window that starts before the call (with a 60 second clock-skew
   allowance) and ends now, `--page-size 100`, `--page-number 1`.
2. The page is accepted only when `TotalCount` equals the number of returned records;
   otherwise the reconciliation stops.
3. Candidates with an exactly equal title are each fetched with `get-ticket` and compared on
   creation time inside the window, title, the complete body including this run's
   `[client request id]` marker, category id and severity.
4. Exactly one complete match returns `creationState` `reconciled_after_timeout` (timeout) or
   `reconciled_after_indeterminate_result` (other unclear outcome). Zero matches, several
   matches, an interrupted reconciliation or any unverifiable field stops and demands manual
   checking with `ticket list` or the console.

An older ticket with the same title and body cannot match, because it lacks this run's marker.

## Confirmation token failures

| Message | Meaning | Correct next step |
|---|---|---|
| a write operation is missing its confirmation token | the write was attempted without a preview | run the matching `preview-*` and show it |
| the confirmation token does not exist or was already used | single-use violation | preview again; never reuse a token |
| the confirmation token has expired | older than 30 minutes | preview again |
| the confirmation token does not match the current content or ticket state | bytes or status drifted | preview again with the identical bytes |
| the ticket status changed after confirmation | the ticket moved on, possibly to a terminal state | re-read the status, stop if terminal |

## Readiness states

`doctor.readiness.state` is one of `ready`, `cli_missing`, `cli_unusable`,
`oauth_unsupported` or `workorder_access_unavailable`. Only `ready` allows ticket operations.
`workorderAccess.reason` distinguishes `list_products_succeeded`, `api_probe_failed`,
`cli_missing` and `skill_version_unavailable`. `api_probe_failed` must be narrowed down to an
expired login, a network problem or a RAM permission gap from the redacted detail, and the client
never switches credentials on its own. `skill_version_unavailable` means the User-Agent version
cannot be read from the installed skill package: the installation is incomplete, ticket and catalog
operations are blocked with `nextAction` `request_skill_reinstallation_consent`, no CLI call is
made, and the installed version source must be restored by reinstalling the skill — never
substituted with a guessed version.
`rules_update`, `match` and `draft` stay available in every state.

## Capability probe outcomes

`workorderCapabilities.probe.mode` is `plugin_help_listing`. One offline
`aliyun workorder --help` call is parsed for the nine lowercase-hyphenated command names, so
no request leaves the machine and no credential is needed:

- a listed command → `supported`;
- a help page produced by the plugin that omits one of the nine → `unsupported`, and
  `probe.complete` stays `true`;
- a non-zero exit, a timeout, or a help page that lists no workorder command at all (typically
  the product plugin is not installed) → every operation stays `unknown`,
  `probe.complete` is `false`, and the reason is `workorder_help_failed` or
  `workorder_help_lists_no_commands`;
- an unreadable installed version source → the probe never starts, the reason is
  `skill_version_unavailable` and no CLI process is spawned.

`unknown` never becomes a "not supported" claim, and the capability matrix marks the affected
capability `unknown` instead of `available`. `--cli-dry-run` is not used for the probe: it is
intercepted by CLI mock records, which would make `doctor` consume injected faults.

## Encoding and platform failures

CLI output and standard input are read as bytes. Standard input prefers UTF-8; on Windows the
CLI output prefers the system preferred code page, elsewhere UTF-8, and only an explicit
`ALIBABACLOUD_SUPPORT_CLI_ENCODING` of `utf-8` or `gb18030` overrides that. Undecodable bytes
are reported as such instead of being replaced by placeholder characters, and machine-readable
JSON output is always UTF-8. Garbled output is never attributed to the terminal font, and it
is never fixed by editing the installed files.
