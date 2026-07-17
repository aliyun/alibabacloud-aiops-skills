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

Always dry-run complex row arrays and inspect that booleans, numbers, objects, arrays, and null values retain their JSON types:

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

## SQL Text Boundary

This Skill uses `execute-query` only for read-only SELECT or SearchExpr queries. Use `add-dataset-data` for all row writes. Do not provide or execute raw SQL INSERT, UPDATE, DELETE, DDL, or multiple statements.

- The public `execute-query` API does not expose SQL bind parameters; it accepts the complete query as text.
- Do not compose query text from untrusted strings in prompts, files, environment variables, or API responses.
- Do not accept a user-supplied SQL template. Build a read-only query only from a documented query pattern and known Dataset schema fields.
- Do not log or expose query text when it may contain secrets or sensitive payloads.
