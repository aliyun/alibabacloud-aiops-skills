# Module 2: Tracing a Request

Query patterns used by `trace_request.py`, the constraints that make them work,
and how to read what comes back.

---

## 1. Choose the tracing mode

| Situation | Mode | Entry point |
|---|---|---|
| The customer has a request ID | `--request-id` | Most precise; always prefer it |
| The customer names a file, not a request | `--object` | Object history, chronological |
| A batch delete removed several keys | `--object --batch-delete` | Batch-delete topic, joined by `request_id` |
| The customer only reports an error code | `--ec` | One representative row carrying that EC |
| The customer reports "lots of failures" | (default) | EC and error-code distribution over the window |
| The log cannot be read here | `--generate-only` | Console statements, nothing executed |

A request ID beats everything else: it identifies one row with no ambiguity
about which failure is being discussed. Ask for it first when the customer can
obtain it — the SDK exception and the error response body both carry it.

The full catalog of generated statements, what each one answers, and the
console steps for running them are in
[module7 query templates](query-templates.md).

---

## 2. Query patterns

Every pattern pins the topic and the bucket in the filter part.

### By request ID

```
__topic__: oss_access_log AND bucket: my-bucket AND request_id: 65A1B2C3D4E5F6G7H8I9J0K1
```

`request_id` is indexed, so this belongs in the filter part and costs one lookup.

### Object history

```
__topic__: oss_access_log AND bucket: my-bucket |
  SELECT time, request_id, operation, http_method, http_status, error_code, ec,
         sign_type, access_id, requester_id, client_ip
  FROM log
  WHERE url_decode(object) = 'images/a.png'
  ORDER BY __time__ ASC
  LIMIT 100
```

Two details decide whether this returns anything:

- `object` is **URL encoded** in the log, so matching the readable key requires
  `url_decode(object)`. Matching the raw field needs the encoded form
  (`images%2Fa.png`).
- `object` is usually **not indexed**, so it cannot go into the filter part.
  Putting it there returns an error or zero rows rather than a wrong answer,
  which is why the mistake is easy to miss.

This pattern answers "was this file deleted, and by whom": filter the result for
removal operations and read `requester_id`, `client_ip` and `sign_type` from the
matching row.

### Error distribution

```
__topic__: oss_access_log AND bucket: my-bucket |
  SELECT ec, error_code, http_status, operation, sign_type, count(*) AS cnt
  FROM log
  WHERE http_status >= 400
  GROUP BY ec, error_code, http_status, operation, sign_type
  ORDER BY cnt DESC
  LIMIT 50
```

All grouped fields are indexed, so no scan mode is needed and the aggregation
covers the whole window. Use this to find which failure dominates before tracing
a single instance of it.

### By EC code

```
__topic__: oss_access_log AND bucket: my-bucket AND ec: 0003-00000101 |
  SELECT time, request_id, operation, object, client_ip, vpc_id, access_id,
         requester_id, sign_type, host, referer, user_agent, extend_information
  FROM log
  ORDER BY __time__ DESC
  LIMIT 1
```

`ec` is indexed. Taking the most recent row gives a representative request to
feed into the policy hit analysis.

### Concurrent writes to one object

```
__topic__: oss_access_log AND bucket: my-bucket |
  SELECT time, request_id, operation, http_status, ec, sign_type,
         sync_request, client_ip, access_id
  FROM log
  WHERE url_decode(object) = 'images/a.png'
    AND operation IN ('PutObject','PostObject','UploadPart','AppendObject')
  ORDER BY __time__ ASC
  LIMIT 100
```

Used for a version-conflict failure, to show which operations competed for the
same object.

---

## 3. Syntax constraints that change the answer

| Constraint | Wrong | Right |
|---|---|---|
| No parenthesised OR in the filter part | `operation: (PutObject OR PostObject)` | `WHERE operation IN ('PutObject','PostObject')` in the SQL part |
| Non-indexed fields cannot filter | `object: images/a.png` before the pipe | `WHERE url_decode(object) = '...'` after the pipe |
| Object keys are URL encoded | `WHERE object = 'images/a.png'` | `WHERE url_decode(object) = 'images/a.png'` |
| Topic must be pinned | `bucket: my-bucket \| SELECT count(*)` | `__topic__: oss_access_log AND bucket: my-bucket \| SELECT count(*)` |
| Timestamps are Unix **seconds** | milliseconds from a JavaScript client | divide by 1000 |
| Scan mode has a ceiling | one query over a day of heavy traffic | narrow the window first, then aggregate |

Scan mode (`set session mode=scan;` placed after the pipe and before `SELECT`)
is only needed when the SQL part references a non-indexed field. It scans a
bounded number of raw rows, so on a busy bucket the window must be narrowed
until the row count fits; otherwise the result is silently partial. Aggregating
over indexed fields alone needs no scan mode and covers the whole window — which
is why the error-distribution pattern above is preferred for finding the
dominant failure.

---

## 4. Time windows

| Window | Use |
|---|---|
| 1 hour | A failure happening now; fastest and cheapest |
| 24 hours (default) | A failure reported today |
| 72 hours | Intermittent failures, or a customer in another time zone |
| 7 days (maximum) | Establishing whether an object ever existed |

Two rules:

1. Convert the customer's local time before building the window. The logged
   `time` field is a formatted timestamp, while `__time__` is the numeric one;
   queries filter on the numeric range, so an unconverted window silently misses
   every row.
2. Widen the window before concluding that no evidence exists. An empty result
   from a one-hour window proves nothing about a failure that happened yesterday.

---

## 5. Reading a traced row

The report renders a row in this order, because it follows the causal chain:

```
identity   time, request_id, bucket, owner_id, requester_id, access_id,
           sign_type, extend_information
request    object, operation, http_method, host, request_uri, referer,
           user_agent, vpc_id, client_ip, sync_request
response   http_status, error_code, ec, object_size, content_length_in,
           response_body_length
timing     response_time, server_cost_time
```

Interpretation notes that come up constantly:

- `sign_type: NotSign` with `access_id: -` means an **anonymous** request. Any
  authorization conclusion must be drawn against anonymous access, not against a
  credential.
- `access_id` starting with a temporary-credential prefix means the caller used
  temporary credentials. For an assumed role, the decisive identity is
  `roleOwnerId` — the fourth field of `extend_information` — not the caller's own
  parent id. See [module4_policy_analysis.md](module4_policy_analysis.md).
- `vpc_id` empty or `-` means the request came over the public network, which is
  what a source-VPC condition is evaluated against.
- `sync_request: cdn` means the request came from a CDN node back to the origin.
  The logged `client_ip` is then the CDN node, not the end user, and the logged
  `referer` and `user_agent` are what the CDN forwarded. Analysing end-user
  behaviour from those rows produces wrong conclusions; exclude them, and if all
  rows are CDN back-to-origin, the question belongs to the CDN side.
- `response_time` much larger than `server_cost_time` places the delay in the
  transfer path rather than in the service.
- Any field present in the row but absent from the catalog is rendered with an
  "undocumented field" marker, so a schema addition never hides evidence.

---

## 6. When tracing returns nothing

Report which of these applies; never report "no problem found".

| Cause | How to tell | Action |
|---|---|---|
| The log channel is unavailable on this host | Probe status is `channel_unavailable` | Say plainly that **no query was executed**, then hand over the generated statements with the project, logstore, region and time-window guidance |
| Realtime logging was not enabled at the time | Probe status is `not_enabled` | Say plainly that historical requests cannot be recovered |
| The caller may not read the logstore | Probe status is `not_permitted` | Grant the log read action, then re-run |
| Wrong region | The probe names a project that does not exist while the bucket is elsewhere | Re-run with the bucket's real region (the entry script resolves it automatically) |
| Window too narrow | Zero rows in 1 hour, rows appear in 72 hours | Widen and re-run |
| Key spelled differently | Object history empty while the error distribution shows failures | Compare the encoded key form |

When the log source is fine and the query ran but a specific expected request is
still missing, that is a different question with four documented causes — CDN
cache hit, client-side interruption, log push loss, and cross-region endpoint
usage. They are listed in
[module1_log_source.md](module1_log_source.md) section 7, and one of them must be
quoted instead of concluding that the request never happened.
