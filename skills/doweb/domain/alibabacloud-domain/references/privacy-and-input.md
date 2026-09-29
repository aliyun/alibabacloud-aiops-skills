# Private data and secure inputs

Use this reference for contacts, registrant templates, real-name review, email verification, ICP data, and execution artifacts. DomainCLI preserves some OpenAPI fields without client-side masking; this Skill is responsible for minimizing what it repeats or saves. Do not claim that a missing or masked field necessarily comes from the API, or that WHOIS proves account ownership.

## Data boundary

User-selected private inputs go from a permission-restricted local file through the supported DomainCLI leaf to the corresponding Alibaba Cloud service. Authentication stays inside DomainCLI and its trusted parent CLI. Do not add another credential provider, raw API call, upload destination, or diagnostic data collection step.

- Never open credential configuration or caches, extract temporary credentials with a parent command, dump environment values, or inspect process arguments to diagnose authentication. Use `aliyun domain auth`, `whoami`, and the intended read-only cloud command instead.
- Never run `aliyun configure set` with credential flags or use shell variable defaults, copied configuration, or hardcoded STS credentials to construct an OAuth profile. Redacting a final answer cannot undo credentials disclosed in a tool call or its output.
- Do not request secrets, SMS codes, transfer codes, email tokens, identity images, or full identity/contact records in chat. When the leaf supports secure file input, ask only for the user's existing file path and let the CLI inspect it. When it offers only secret-bearing command-line input, hand that step to the user's private terminal; do not embed the secret in a tool command or report.
- Do not read, print, copy, or create a private input file from guessed personal data. A nonexistent or inaccessible file is an input problem, not permission to create fictitious data or search unrelated user directories.

## Input completeness and independent decisions

| Request | Minimum next step | Stop condition |
|---|---|---|
| Create a template named after a company | Inspect `template create --help`, ask for the supported secure input-file path and missing non-secret choices. | A display label alone cannot supply the required registrant, contact, address, and identity fields. Return `awaiting_input`; no create/apply submission. |
| Apply a newly created template | Verify successful create/readback and the returned template ID; use account-side `detail` for the exact target domain. Preview applying that exact template separately. | Creation pending/failed, template ID missing, domain inaccessible, or no fresh application confirmation. |
| Verify a template or email | Follow the installed leaf's secure-input and confirmation contract. | Missing protected input or required human verification. Do not invent verification data. |
| Query personal records | Run only the requested read, then select task-relevant non-secret fields. | Data access denied or a request for credentials. Do not fetch another account's records. |

Template creation, default-template changes, verification, and contact application are separate mutations. Confirmation of one does not authorize the others. A discovered template must not replace the template the user asked to create.

## Safe outputs and artifacts

Keep a diagnostic record to command path, non-secret target IDs, CLI status/error code, request/task ID, confirmation state, and safe next command. Do not save verbatim stdout/stderr, credential configuration, raw SDK errors, encoded authorization diagnostics, or private API payloads to reports, repository fixtures, or action logs. A transcript cannot be made safe by redacting only the final answer after credentials were already printed.

For contact, registrant-template, and verification reads, use a strict output allowlist: task-relevant resource IDs, status, `default`, `entityType`, `realNameStatus`, counts, and safe request/task IDs. Omit names, email addresses, phone numbers, postal addresses, identity fields, and submitted materials from chat and artifacts even when the raw CLI response contains them. Masking is not a reason to include a field that the task does not require. Do not create `outputs/`, `ran_scripts/`, raw logs, or reports for a read unless the user explicitly requested a file; an explicitly requested artifact must still use this allowlist.

For authentication or `whoami` reads, report only whether the explicitly requested identity check succeeded and its safe status. Omit account/principal IDs, ARNs, identity types, and raw response fields from chat and artifacts. Do not call `whoami` merely to diagnose another command or to compensate for a failed/empty product read.

- Keep session attribution in memory; do not create a session-ID file or include attribution IDs in generated reports or command logs. Use the required attribution for CLI transport, not as a separate artifact.
- Treat signed resource URLs as secret-bearing when they include security tokens, signatures or authorization query parameters. Do not follow, print or save them as diagnostic evidence; retain a sanitized resource identifier or result summary instead. Tool-level sanitization belongs in DomainCLI/its adapter before the output reaches the model, and a Skill cannot claim to provide that missing protection retroactively.

- Credentials, verification tokens/codes, passwords, payment secrets, and private keys are never output fields.
- Summarize contact and ICP records using status, resource IDs, entity type, and counts. Omit names, addresses, phone numbers, email addresses, identity fields, and materials. If exact personal values are necessary, direct the user to the secure official workflow rather than duplicating them in chat or artifacts.
- Preserve price source/currency, domain names, and resource identifiers needed to resume. These are not substitutes for exposing a holder's identity, phone, or document number.
- If raw output contains a secret, do not repeat or save it. Report the sanitized error class and safe recovery. Do not attempt to repair authentication by using the leaked credential.
