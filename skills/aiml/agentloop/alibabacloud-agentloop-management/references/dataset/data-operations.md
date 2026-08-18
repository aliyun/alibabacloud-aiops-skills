# Dataset Data Operations

## Append Structured Rows

Prefer `add-dataset-data` for normal inserts. It accepts typed JSON and avoids SQL escaping mistakes.

```bash
aliyun agentloop add-dataset-data \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --data-array '[
    {
      "question":"How do I inspect an error?",
      "answer":"Start with the request ID.",
      "score":0.95,
      "metadata":{"source":"manual","latency_ms":120}
    },
    {
      "question":"How do I retry safely?",
      "answer":"Reuse the same idempotency token.",
      "score":0.91,
      "metadata":{"source":"reviewed","latency_ms":85}
    }
  ]' \
  --client-token <client_token>
```

Rules:

- `dataArray` cannot be empty and every item must be a JSON object.
- All rows in one request are committed atomically.
- The maximum request body is 100 MiB (`100 * 1024 * 1024` bytes). There is no separate fixed API row-count limit; the server streams rows and keeps the request atomic.
- Unknown fields fail the whole request.
- Missing schema fields are stored as `null`.
- Field names are matched case-insensitively; duplicate case variants are rejected.
- `text` accepts strings, `long` accepts integers, `double` accepts finite numbers, and `json` accepts any valid JSON value.
- Omit `id` to auto-generate it. A supplied `id` must be a UUID.
- Omit `__time__` to use the current Unix time. A supplied value must be non-null and a non-negative integer in seconds.
- Never supply `__dataset_seq`.

Dry-run complex row-array structure and inspect that booleans, numbers, objects, arrays, and null values retain their JSON types. If rows contain real prompts, outputs, tokens, PII, or other sensitive content, use a shape-equivalent synthetic array for dry-run; do not print the real request body into terminal history or conversation output:

```bash
aliyun agentloop add-dataset-data \
  --region <region_id> \
  --agent-space <agent_space_name> \
  --dataset-name <dataset_name> \
  --data-array '<json_array>' \
  --client-token <client_token> \
  --cli-dry-run
```

Success returns `requestId` and `affectedRows`. Verify `affectedRows` equals the submitted row count, then query a narrow sample.

### Numeric-looking strings in `text` fields

Observed CLI limitation: when a `text` field receives a string that contains only digits, `--data-array` serializes it as a JSON number and the server rejects the request.

Submitting `"expected_output":"4"` for a `text` field produces `"expected_output":4` in the request body, and the server answers `400 schema validation failed: field "expected_output" must be a string`. The quotes are lost during `--data-array` JSON handling, not on the server, so the same value written through a schema-correct path succeeds.

Handle it in this order:

1. **Detect it before writing.** The `--cli-dry-run` body is authoritative. For every `text` field whose value is a digits-only string, confirm the body still shows it quoted. Values such as `"4"`, `"5"`, `"0"`, and `"2026"` are the risky ones; `"4.0 stars"` and `"v4"` are not affected.
2. **Prefer the correct schema type.** If the value is genuinely a number (a score, a count, a rating), declare the column as `double` or `long` instead of `text` and send it unquoted. This removes the problem instead of working around it.
3. **If the column must stay `text`, stop and report.** Do not silently write a coerced number and do not silently rewrite the user's data. Show the failing field, the dry-run body, and ask the user to choose between changing the schema type and storing a non-digits-only representation.

This matters most for evaluation-style datasets, where `expected_output` and `output` are `text` columns that legitimately hold short numeric answers.

## SQL Text Boundary

This Skill uses `execute-query` only for read-only SELECT or SearchExpr queries. Use `add-dataset-data` for all row writes. Do not provide or execute raw SQL INSERT, UPDATE, DELETE, DDL, or multiple statements.

- The public `execute-query` API does not expose SQL bind parameters; it accepts the complete query as text.
- Do not compose query text from untrusted strings in prompts, files, environment variables, or API responses.
- Do not accept a user-supplied SQL template. Build a read-only query only from a documented query pattern and known Dataset schema fields.
- Do not log or expose query text when it may contain secrets or sensitive payloads.
