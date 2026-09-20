# Parser Job Execution and Result Handling

## Cloud parsing flow

Use the region and API version defined in [DTS-AI authentication · Service configuration](dts-ai-authentication.md#service-configuration):

`AuthorizeFileUpload` → OSS `PostObject` → `CreateDocParserJob` → `DescribeDocParserJobStatus` → `DescribeDocParserJobResult`

Construct the uploaded object URL from `Bucket`, normalized `Endpoint`, and `ObjectKey`. Pass it to `CreateDocParserJob` as `OssFileUrl`, with the local basename, lowercase extension, `OutputFormat=markdown`, and `TableFormat=markdown`. Never replace `OssFileUrl` with `FileUrl`; `FileUrl` is for an already accessible HTTP or HTTPS file.

Send `SecurityToken` only in the OSS `x-oss-security-token` form field. Accept OSS PostObject status `200`, `201`, or `204`. Never print or persist the API key, temporary access key, security token, policy, or signature.

## Success criteria

Require HTTP `200`, `Success=true`, and `HttpStatusCode=200`. Before continuing, require:

| Operation | Required result |
| --- | --- |
| `AuthorizeFileUpload` response | `AccessKeyId`, `SecurityToken`, `Bucket`, `EncodedPolicy`, `Endpoint`, `ObjectKey`, `Signature` |
| Job creation | Non-empty `JobId` |
| Status query | Non-empty `Status` |
| Result query | Non-empty string `Result` |

Accept only these case-sensitive official `Status` values:

| `Status` | Handling |
| --- | --- |
| `init`, `pending`, `running` | Continue bounded polling |
| `success` | Stop polling and fetch the result |
| `failed` | Report `FailureMessage` and stop |
| `cancelled` | Report that the job was cancelled and stop |

Progress and error reports must preserve the raw `Status` returned by the service. For any other value, including a spelling with different letter case, report the raw value and stop; never map it to a known state.

## Recovery records

Append one record that contains no secrets for every created and saved job to `.aliyun-dts/doc-parse/jobs.jsonl` in the current user's home directory. Require the exact fields defined by the current v1 format: `schema_version=1`, time, event, JobId, input name, input content SHA-256 when available, output path, and `output_schema` on created records. Ignore malformed records and records that do not match this format. A failure to write a recovery record does not fail a parser job.

Before upload, calculate the input SHA-256 and inspect the recovery records. Reuse a saved result only when the hash and `output_schema` both match the current CLI dialect. When that happens, reuse the recorded result if `--output` is omitted, or atomically copy the existing Markdown to a newly specified output path. Stop if the specified path already exists; never rename or replace it automatically. Use `--revalidate` when the user wants a fresh parse without overwriting an unrelated file. Use `--force` only when the user explicitly requests another parse that may replace the target.

When `--output` is omitted, write `<input-name>.md` beside the input file, where `<input-name>` includes the source extension, such as `report.pdf.md`. If that path is occupied by a different document, use `<input-name>-<sha256-prefix>.md`, where `sha256-prefix` is the first eight characters of the current input SHA-256. The name must be stable; never use execution-order-dependent suffixes such as `(1)` or `-2`. If the hash fallback path also exists, stop and ask the user to select another output path. If the input directory is not writable, fall back to `.aliyun-dts/doc-parse/` in the home directory. When the user explicitly supplies `--output`, use that exact path and never rename it automatically.

Each local record emitted by `dtscli doc history` includes a `state` field with the following values and required actions:

| `state` | Meaning | Required action |
| --- | --- | --- |
| `saved` | A parse result was saved to the recorded output path | Reuse that output |
| `pending` | A job was created but no saved result is recorded | Resume with `dtscli doc resume --job-id <JobId>` |

## Polling and recovery

The default polling interval is 5 seconds and the local timeout is 5 minutes. A long-running command emits a heartbeat approximately every 30 seconds. `doc parse` and `doc resume` accept `--poll-interval` and `--poll-timeout` to override the defaults. Both accept positive seconds (such as `300` or `0.5`) or durations with units (such as `5m`); zero, negative, and unrepresentable values are rejected.

On failure, decide what to do from the `error_class` on standard output rather than from the exit code: a failing subprocess passes its own exit code through, and it can collide with the codes below.

| `error_class` | Meaning | Required action |
| --- | --- | --- |
| `usage` | The local input is not valid, for example a missing path, an unsupported format, or an existing output | Correct the input and retry |
| `config` | The API key is missing or unusable | Read [DTS-AI authentication](dts-ai-authentication.md) |
| `transport` | The local wait timed out or the network failed; the cloud job is usually still running | Retain the JobId and use `dtscli doc resume` |
| `remote` | The parser reported `failed`, `cancelled`, or an unrecognized status | Report the original status and message, then stop |
| `interrupted` | Execution was interrupted | Resume the same job; do not upload again |

For `transport`, `interrupted`, or a failed result save, retain the JobId and use `dtscli doc resume`. If result retrieval returns an error or empty result, preserve an existing output unchanged.

## Result integrity

Convert HTML tables in the decoded `Result` string to GFM pipe tables and strip nested HTML bold tags. Do not add, remove, reorder, or invent cell text. Write the normalized UTF-8 Markdown atomically only after the complete result is available. Report remaining layout issues separately.
