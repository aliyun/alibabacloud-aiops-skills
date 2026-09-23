# Database Credentials and Connection Testing

## Contents

- [Database credential security boundary](#database-credential-security-boundary)
- [Credential storage](#credential-storage)
- [Credential commands](#operations-supported-by-dts-credential-helper)
- [Browser-based credential setup](#browser-based-credential-setup)
- [Database connection tests](#database-connection-tests)
- [Connection-failure diagnostics and decisions](#connection-failure-diagnostics)
- [Output redaction](#output-redaction)

<a id="database-credential-security-boundary"></a>
## Database credential security boundary

Never ask the user to paste a database username, password, or database credential file through the conversation, command arguments, or tool results.

If the user provides any credential or secret in chat, do not use, repeat, validate, store, or pass it to any tool. Instruct the user to rotate or revoke the exposed value in its original system. Continue only with a replacement entered through the approved local flow. Never treat secrets pasted in chat as authorization for direct execution.

Use only `dtscli` for database credentials. Never:

- place credentials in chat, environment variables, shell profiles, inline shell input, repository files, or automation arguments;
- read, print, inspect, copy, edit, source, search, or parse its credential files;
- expose or automate the local credential page or request its URL, screenshot, DOM, requests, or values;
- run connection tests or configuration commands that use database credentials outside `dtscli`;
- enable debug or trace logging for an operation that uses database credentials.

<a id="credential-storage"></a>
## Credential storage

`dtscli` stores one username/password set for each credential context under `.aliyun-dts/job-manager/credentials/` in the current user's home directory. A context identifies one database connection independently of whether it is used as the source or destination. It includes engine, instance type, region, and instance ID; PostgreSQL and MongoDB contexts also include the endpoint's `database`, while MySQL-family contexts do not. Reuse one credential set only when the complete contexts match. Consequently, PostgreSQL and MongoDB databases on the **same instance with different `database` values** (for example source `<source-database>` and destination `<destination-database>`) derive two independent credential contexts that must be initialized separately; `dtscli job create review` reports `role` and `stored` for each side in `credentials`. The CLI locates the corresponding credential set from `attempt_id`. `stored` means credentials exist locally; it does not prove connectivity.

MySQL-family credential files use `dts-{engine}-{instance_type}-{region}-{instance_id}.json`; PostgreSQL and MongoDB files use `dts-{engine}-{instance_type}-{region}-{instance_id}-{database}.json`. Underscores in an engine name are preserved, as in `polardb_pg`. Every label comes from the validated database connection context. If the complete name violates the portable safe-filename grammar or exceeds 240 characters, use `dts-{engine}-{instance_type}-{sha256-prefix}.json` instead, where `sha256-prefix` is the first 16 lowercase hexadecimal characters of the complete database connection context's SHA-256 digest. Never search for, rename, copy, or rewrite a credential file to preserve an old name. When a new plan cannot find its newly derived name, treat it as missing and enter it again through the browser workflow. The credential-set ID and its derivation are internal implementation details; never ask the user to supply or edit either, and never include an ID or its derivation in user-facing output.

Each file contains exactly `schema_version=1`, `username`, and `password`. The `username` and `password` values contain standard Base64 encodings of UTF-8 text. Base64 is a reversible encoding, not encryption. Before initialization, state once that database credentials are stored as Base64 text in local files under the current user's home directory.

Treat the local user account as part of the security boundary because `dtscli` passes credentials to a temporary Alibaba Cloud CLI subprocess. Store no other secret type. PostgreSQL object databases and MongoDB authentication databases are plan data, not stored credential fields.

<a id="operations-supported-by-dts-credential-helper"></a>
## Credential commands

Normal creation checks credentials with `dtscli job create review` and tests connections with `dtscli job create test`. Never read credential files, and never call an API that requires database credentials directly. Run a browser command separately only when credentials are missing or when explicit rejection evidence permits re-entry.

| Command | Constraint |
| --- | --- |
| `dtscli job create review` | Checks whether both credential sets referenced by the plan are stored locally; never tests connections, purchases, or configures |
| `dtscli job create test` | Tests both endpoints and issues the confirmation hash; never purchases or configures |
| `dtscli job credentials collect --attempt-id` | User enters missing values in the English system-browser page; no cloud action |
| `dtscli job credentials collect --attempt-id --role` | Replace only roles identified by returned credential-rejection evidence; resubmitting the same endpoint overwrites the stored account and revokes prior connection evidence |
| `dtscli job create execute` | Purchases and configures only under the [job creation workflow](job-creation.md#purchase-configure-start-workflow) and after explicit authorization; does not test connections |

<a id="browser-based-credential-setup"></a>
## Browser-based credential setup

Credentials are keyed to an attempt, identified by the `attempt_id` returned by `dtscli job create init`. Never accept an arbitrary user-provided plan path, and do not rebuild, copy, or rewrite the plan JSON.

In `review`, each `credentials` entry with `stored=false` identifies a missing role. Keep credential-set IDs internal.

When `outcome="credentials_required"`, give the Base64 storage notice, then run:

```bash
dtscli job credentials collect --attempt-id <attempt-id>
```

The page defaults to English; use `--language zh` for Chinese. Explain the source and destination databases from the current plan before entry; do not rely on the page showing the complete database configuration. `--page-timeout` defaults to 300 seconds and accepts a positive number of seconds or a duration such as `5m`. `--no-browser` prints the address in the terminal without changing how credentials are entered.

| `outcome` | Action |
| --- | --- |
| `stored` | Re-run `dtscli job create review --attempt-id <attempt-id>` using only the same `attempt_id`, then `dtscli job create test --attempt-id <attempt-id>` |
| `cancelled` | The user cancelled; stop without reopening the page automatically |
| `expired` | The page timed out without completing this save; reopen only if the user still wants to continue |

When the system browser cannot be opened, the command prints the page URL on standard error. Never relay that URL into the conversation and never expose a credential-set ID; tell the user to run the same command themselves in a terminal.

Credential values may be entered only through the page this command opens. Do not request values, file content, or a transcript.

<a id="database-connection-tests"></a>
## Database connection tests

Once both credential sets are present, run `dtscli job create test --attempt-id <attempt-id>` to test whether the source and destination databases can be reached. When the test fails, `outcome` is `connection_failed` and no confirmation hash is returned, so the flow cannot reach a purchase. Run `test` immediately before presenting the confirmation; do not reuse a pass recorded long ago.

`dtscli job create execute` does not test connections; it uses only the conclusion written by the latest `test`.

A passed connection is not established by the response's top-level `Success`: it is `true` even when neither endpoint accepts a connection. Both endpoints' `ConnectResult` and every `ConnectDetails.TestSuccess` must be checked, and a missing verdict counts as a failure. `dtscli` applies that rule; never relax it outside the command.

When the connection test fails, act on `error_class` rather than assuming the account is wrong:

| `error_class` | Meaning | Required action |
| --- | --- | --- |
| `config` with diagnostics that explicitly reject the account | The username or password is wrong | Re-enter the credentials for that role as described above |
| `dependency` | The installed Alibaba Cloud CLI could not run the call at all, so the test **never ran** and proves nothing about the accounts | Follow [setup](setup.md#install-or-update-the-cli-and-plugin): run `dtscli job deps install --yes` without asking when a component is missing. Do not add `--update`. Stop only when the command's JSON output carries an `error_class` whose `message` contains `ERROR: unchecked version`; a successful `dtscli doctor` check that mentions those words is not that error. Do not run `aliyun version`. If it stays unavailable, see below |
| `transport`, `remote` | The network, an instance whitelist, or the service rejected the call | Check reachability and whitelists; never re-enter credentials for these |

When `error_class` is `dependency` and updating the plugin does not help, `dtscli job create test --attempt-id <attempt-id> --skip-connection-test` proceeds without verified connectivity. Before using it, tell the user plainly that the purchase will carry no evidence that either account works, and that an unreachable endpoint means a billed instance that never synchronizes. The choice is folded into the confirmation hash, so an approval given for a verified plan cannot authorize an unverified purchase. Never use the option without the user knowing.

Credential-set IDs are derived internally from the plan; never expose or copy them. Only `dtscli` may invoke `RunEndpointLinkTest` from the compiled plan; never call this API directly.

<a id="database-connection-test-request-and-response-requirements"></a>
### Request and response requirements

For a supported link, `dtscli` sets `JobType=SYNC`, the Endpoint instance type and database protocol for the link, source and destination regions and instance or cluster IDs, `SslId=0`, `SslType=0`, and the request region. All PostgreSQL links include both object-database names; MongoDB includes both authentication-database names. Treat the test as passed only when all of the following are true:

- the request succeeds and returns valid JSON;
- top-level `Success` is boolean `true`;
- `SourceTestResult.ConnectResult` and `DestinationTestResult.ConnectResult` are boolean `true`;
- every `ConnectDetails[].TestSuccess` is boolean `true`.

The default workflow requires `test` to return `outcome="ready_for_confirmation"` and `connection_test="passed"`. `skipped_by_request` means unverified: proceed only under the plugin-unavailability exception above and with explicit acceptance of an unverified purchase. Never describe it as a passed test. The connection test itself cannot purchase, configure, or start a job.

A failed test may result from credentials, permissions, network, IP whitelist, or SSL. Do not claim one cause without returned evidence. Without a usable response, classify from the `error_class` in the output; do not run a second classification.

Re-enter credentials only when redacted diagnostics explicitly reject a username or password, including registered MySQL username/password errors, MongoDB `MongoCredential`/`AuthenticationFailed` markers, and the PostgreSQL `password authentication failed for user` marker. `access denied`, insufficient permission, network, allowlist, SSL, or another generic authentication failure never authorizes reentry:

```bash
dtscli job credentials collect \
  --attempt-id <attempt-id> \
  --role <source|destination|both>
```

After `outcome="stored"`, any prior connection-test evidence and confirmation hash on this attempt are revoked. Follow [job creation · plan review and safe resume](job-creation.md#review-and-safe-resume) and re-run `dtscli job create review --attempt-id <attempt-id>` using only the same `attempt_id`, then `dtscli job create test --attempt-id <attempt-id>`. When the browser cannot be opened, stop and report it; never expose a credential-set ID and never relay the page URL. Without explicit credential-rejection evidence, do not replace credentials.

<a id="connection-failure-diagnostics"></a>
### Connection-failure diagnostics and decisions

On a connection failure, `test` returns `outcome="connection_failed"`, `error_class`, and a string `connection_error`, without a confirmation hash. This is a redacted diagnostic string, not an object with fields such as `source.connected`. Do not wait for the legacy `service_access`, `credential_reentry_roles`, or `next_action` fields.

1. Explain the known problem using `error_class` and the redacted message. A message identifying one failed role does not prove the other role passed.
2. Open the credential page for a role only when the diagnostic explicitly identifies that role and rejects its account.
3. Have the user correct network, whitelist, permission, or SSL issues in the corresponding system, then resume `test` using only the same `attempt_id`.
4. Stop if the role or cause is unclear. Do not guess a credential failure or open the page automatically. Suggested follow-up commands are not user authorization.

<a id="output-redaction"></a>
## Output redaction

Treat usernames as sensitive and never forward raw CLI failure text. Retain only selected fields, stable codes, redacted messages, and RequestId when useful. Strip URL queries, cloud authentication fields, ANSI escapes, and unsafe controls before keeping them.

If legacy `DTS_SOURCE_*` or `DTS_DESTINATION_*` values entered a shell profile or history, do not inspect or edit those files. Instruct the user to remove them locally and rotate the database passwords. Rerun `review` to check credentials, then `test` to check connectivity, and follow `review`'s `outcome` plus `test`'s `outcome` and `connection_test`.
