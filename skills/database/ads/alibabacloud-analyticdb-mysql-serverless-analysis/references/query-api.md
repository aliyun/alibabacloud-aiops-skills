# ADB Serverless Query API

## Request Format

```http
POST {endpoint}/workspace/{workspaceId}/v1/query
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

{"sql":"<presto-sql>"}
```

- Use an endpoint supplied by the user, or derive it from regionCode as `https://serverless.{regionCode}.ads.aliyuncs.com`.
- Require the user to confirm `workspaceId`; never infer it from another field.
- Prefer a non-empty `accessToken` explicitly supplied by the user for the current request. Fall back to `ADB_ACCESS_TOKEN` only when no explicit token was supplied.
- Pass an explicit token through an in-process runtime parameter or a child-only environment override. Never put it in command arguments, files, output, or logs.
- Use Presto SQL syntax.

## Safe Invocation

Prefer `scripts/adb_query.py` because it:

- rejects non-HTTPS endpoints and endpoints containing credentials, query strings, fragments, or API paths;
- rejects malformed workspace IDs;
- rejects empty SQL, multiple statements, and statements without a read-only leading keyword;
- does not read the token or access the network in dry-run mode;
- redacts the token from errors;
- limits the response body to 10 MiB to prevent unbounded memory use.

Treat dry-run output as a parameter-fidelity gate. Compare the returned endpoint, `workspaceId`, and SQL with the current user-confirmed literals character-for-character. A mismatch means the local command was constructed incorrectly: do not send it live, rebuild it from the confirmed values, and repeat dry-run. Do not infer success from narration or task state; a completed query step requires its actual `adb_query.py` invocation and returned output in the current turn.

The Python entry point accepts `main(argv, access_token=...)` for trusted in-process callers. When `access_token` is non-empty it overrides `ADB_ACCESS_TOKEN` for that request. The CLI intentionally has no raw-token option because process arguments can be observed or logged.

### regionCode mode

```bash
SKILL_SESSION_ID={session-id} python3 scripts/adb_query.py \
  --region-code <confirmed-region-code> \
  --workspace-id <confirmed-workspace-id> <<'SQL'
SHOW SCHEMAS FROM hive
SQL
```

### endpoint mode

```bash
SKILL_SESSION_ID={session-id} python3 scripts/adb_query.py \
  --endpoint <confirmed-https-endpoint> \
  --workspace-id <confirmed-workspace-id> \
  --sql-file <validated-presto-sql-file>
```

## Success Criteria

Evaluate each layer independently. Never present a lower-layer success as completion of the business task:

1. Local input and SQL validation succeeded.
2. The HTTP request succeeded.
3. The server executed the SQL successfully.
4. The response contains interpretable data.
5. The data is sufficient to answer the confirmed analysis goal.

For a required ordered workflow, each layer must have matching current-turn tool evidence before the next dependent query runs. Progress narration, todo completion, or a result remembered from another turn cannot substitute for a script invocation and response.

If the response contains a requestId or queryId, preserve it in the final report. Never output the Authorization header or token.

## Result Interpretation

- The client adds an `evidence` object beside the unmodified response body. It contains stable assertion facts: `querySucceeded`, `serviceCode`, and, when returned by the service, `columnCount`, `rowCount`, and `hasMore`.
- Treat `evidence.querySucceeded: true` as server-execution evidence, not as proof that the returned data answers the user's analysis goal. Assertions should also match the expected schema, bounded row count, or aggregate value.
- Treat `columns` as the positional header for every returned row: `rows[n][i]` belongs to `columns[i]`.
- Preserve that mapping even when a value looks semantically unexpected for its column name. Value plausibility is not evidence that the service reordered columns.
- Do not relabel values or report a schema/data mismatch unless the response contains structural evidence, such as `len(rows[n]) != len(columns)`, or the service explicitly reports a schema error.
- A structurally valid but surprising row is still the successful result for the requested scope. Report it without adding diagnostic queries unless the user explicitly authorizes a new troubleshooting goal.

## Error Handling

| Error | Response |
|---|---|
| 400 with `Cannot detect OSS file format`, `no supported files`, `No files found`, `NoSuchBucket`, or `NoSuchKey` | Stop for the current OSS scope. Do not alter the path, try globs or subdirectories, or switch readers. |
| 401/403, `InvalidAccessToken`, or `AccessDenied` | Stop. Ask the user to verify the token, workspace authorization, and OSS read permissions outside the conversation. Do not retry or switch sources. |
| 404, workspace not found, bucket not found, or prefix not found | Stop for the confirmed endpoint, workspace, and OSS scope. Do not guess another region or path. |
| 429 | Preserve requestId and wait or reduce concurrency. Do not retry indefinitely. |
| 5xx | Preserve the redacted error and requestId, then stop. Only the specific `DESCRIBE files(...)` unsupported-shape messages documented in the Skill permit one same-prefix bounded fallback. |
| SQL syntax error | Correct the statement as Presto SQL, then run dry-run again. |
| Timeout or oversized result | Narrow the OSS path, partitions, time range, projection, and LIMIT. |

Terminal means no retry, timeout increase, endpoint/workspace replacement, parent or sibling prefix probe, registered/direct-source switch, or alternative table function. Report the redacted failure and the exact scope that could not be accessed.

## Raw curl Form

Use this only when the Python client cannot run. Select an explicit user-supplied token before the environment fallback, then expose the selected value to `curl` only through a child-process environment variable:

```bash
curl --fail-with-body --silent --show-error \
  -X POST "https://serverless.<confirmed-region>.ads.aliyuncs.com/workspace/<confirmed-workspace-id>/v1/query" \
  -H "Authorization: Bearer ${ADB_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"sql":"SHOW SCHEMAS FROM hive"}'
```

Do not enable verbose or trace options that print request headers.
