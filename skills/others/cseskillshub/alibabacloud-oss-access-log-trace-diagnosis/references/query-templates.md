# Module 7: Console Query Templates

The statements this skill generates for the customer to run in the log console,
what each one answers, and how to run them. They are produced by
`trace_request.generate_query_statements` and appear in the report under
"Console statements".

**Generation is not execution.** When the log channel is unavailable, when the
caller lacks the log read permission, or when realtime logging is not enabled,
the skill hands these over instead of reporting nothing. When the log *is*
readable the same statements are still emitted, as a reusable artefact.

---

## 1. Running them

1. Open the log console and switch to the **bucket's region**.
2. Open project `oss-log-<uid>-<region>`, logstore `oss-log-store`, then the
   query and analysis page.
3. Set the time picker to the incident window (an absolute range is better than
   a relative one when the incident is older than a day).
4. Paste a statement. A statement containing `| SELECT ...` is an SQL analysis;
   a plain search phrase returns raw records.

Notation: `<bucket>` / `<IP>` / `<object>` / `<status>` / `<id>` are replaced
with concrete values. Literals are double-quoted; an IP wildcard prefix such as
`203.0.113.*` stays unquoted.

---

## 2. Generated statements

| ID | Answers | Requires |
|---|---|---|
| `T0` | The single logged row of one request ID | `--request-id` |
| `T1a` | What one client IP is doing (operation and status mix) | `--ip` |
| `T1b` | Which objects that IP is reading | `--ip` |
| `T2` | Every logged operation on one object key, chronological | `--object` |
| `T6b` | Batch-delete forensics for one object key | `--object` |
| `T4` | Who and what is producing one HTTP status | `--status` |
| `T5` | Writer attribution for one operation type | `--operation` |
| `T7` | Which IPs used one AccessKey | `--ak` |
| `T3` | Top client IPs (abnormal access screening) | always |
| `T4e` | Error distribution by EC code | always |
| `T8` | Anonymous versus signed access split | always |
| `T6a` | Deletion attribution for single-object deletes | always |

Each generated entry carries the **topic** it must be run against. Statements
for `T6b` run against the batch-delete topic; every other statement runs
against the access topic. Running a batch-delete statement against the access
topic returns nothing and looks like "no deletion happened".

### T0 — trace one request ID

```
__topic__: oss_access_log AND bucket: "<bucket>" AND request_id: <id>
```

The most precise entry point: one row, no ambiguity about which failure is
being discussed. The request ID appears in the SDK exception and in the error
response body, so ask for it first.

### T1a / T1b — trace one client IP

```
__topic__: oss_access_log AND bucket: "<bucket>" AND client_ip: <IP> |
  SELECT operation, http_status, error_code, ec, count(*) AS cnt,
         SUM(content_length_out) AS bytes_out
  FROM log GROUP BY operation, http_status, error_code, ec
  ORDER BY cnt DESC LIMIT 50
```

```
__topic__: oss_access_log AND bucket: "<bucket>" AND client_ip: <IP> |
  SELECT url_decode(object) AS object_name, count(*) AS cnt,
         SUM(content_length_out) AS bytes_out
  FROM log GROUP BY object_name ORDER BY cnt DESC LIMIT 20
```

An IPv4 wildcard prefix (`203.0.113.*`) and an IPv6 address are both accepted
by `client_ip`.

### T2 — who accessed this object

```
__topic__: oss_access_log AND bucket: "<bucket>" |
  SELECT time, request_id, operation, http_status, error_code, ec, client_ip,
         requester_id, access_id, sign_type
  FROM log WHERE url_decode(object) = '<object>'
  ORDER BY __time__ ASC LIMIT 100
```

For a prefix rather than one exact key, match with `LIKE '<prefix>%'` inside the
SQL part. The object field is URL encoded and usually not indexed, so it must be
matched after decoding and inside the SQL part — never in the filter part.

### T6a / T6b — deletion attribution

Single-object deletes, from the access topic:

```
__topic__: oss_access_log AND bucket: "<bucket>" |
  SELECT client_ip, requester_id, access_id, sign_type, count(*) AS cnt,
         min(time) AS first_seen, max(time) AS last_seen
  FROM log WHERE operation IN ('DeleteObject','DeleteObjects','ExpireObject')
  GROUP BY client_ip, requester_id, access_id, sign_type
  ORDER BY cnt DESC LIMIT 50
```

Batch deletes, from the batch-delete topic — by object key:

```
__topic__: oss_batch_delete_log AND bucket: "<bucket>" |
  SELECT from_unixtime(__time__) AS time, request_id,
         url_decode(object) AS objectname, user_agent, client_ip, requester_id
  FROM log WHERE url_decode(object) = '<object>'
  ORDER BY __time__ DESC LIMIT 100
```

or by a request ID already known from the access topic:

```
__topic__: oss_batch_delete_log AND bucket: "<bucket>" |
  SELECT from_unixtime(__time__) AS time, url_decode(object) AS objectname,
         user_agent, client_ip, requester_id, http_status
  FROM log WHERE request_id = '<id>' LIMIT 100
```

`user_agent` attributes the deletion source — a console user agent means the
removal came from the console rather than from application code.

### T4e — error distribution by EC code

```
__topic__: oss_access_log AND bucket: "<bucket>" |
  SELECT ec, error_code, http_status, operation, sign_type, count(*) AS cnt
  FROM log WHERE http_status >= 400
  GROUP BY ec, error_code, http_status, operation, sign_type
  ORDER BY cnt DESC LIMIT 50
```

Every grouped field is indexed, so no scan mode is needed and the aggregation
covers the whole window. Run this before tracing one instance of a failure, to
find which failure actually dominates.

### T8 — anonymous versus signed split

```
__topic__: oss_access_log AND bucket: "<bucket>" |
  SELECT sign_type, requester_id, count(*) AS cnt
  FROM log GROUP BY sign_type, requester_id ORDER BY cnt DESC LIMIT 20
```

`sign_type: NotSign` together with `requester_id: -` means anonymous access.

---

## 3. Additional statements not generated automatically

Useful when the customer asks a question the generated set does not cover.
Assemble them by hand only from the field catalog in
[module1_log_source.md](module1_log_source.md).

### AccessKey spread (credential-leak screening)

```
__topic__: oss_access_log AND bucket: "<bucket>" AND access_id: "<AccessKeyId>" |
  SELECT client_ip, operation, http_status, count(*) AS cnt
  FROM log GROUP BY client_ip, operation, http_status ORDER BY cnt DESC LIMIT 50
```

One AccessKey from many unrelated IPs suggests a leaked credential. That
investigation and any mitigation belong to a security workflow, not here.

### Public versus internal endpoint split

```
__topic__: oss_access_log AND bucket: "<bucket>" |
  SELECT CASE WHEN host LIKE '%-internal.aliyuncs.com' THEN 'internal'
              ELSE 'public' END AS link,
         count(*) AS cnt, SUM(content_length_out) AS bytes_out
  FROM log GROUP BY link
```

### Excluding CDN back-to-origin

Add `AND NOT sync_request: cdn` to the filter part of any statement. With
`sync_request: cdn` the recorded `client_ip` is a CDN node, and `referer` and
`user_agent` are whatever the CDN forwarded, so end-user analysis on those rows
is meaningless. `--exclude-cdn` adds this to every generated statement.

### Directory-level egress estimate

```
__topic__: oss_access_log AND bucket: "<bucket>"
  AND host: "<bucket>.oss-<region>.aliyuncs.com" AND NOT sync_request: cdn |
  SELECT SUM(response_body_length) AS total_traffic_out_byte
  FROM log WHERE url_decode(object) LIKE '<dir>/%'
```

The `host` header can be forged, so this is an **estimate**. Actual billed
egress must come from the bill, which is a different capability.

### Directory-level size delta

```
__topic__: oss_access_log AND bucket: "<bucket>" |
  SELECT SUM(delta_data_size) AS total_delta_data_size
  FROM log WHERE url_decode(object) LIKE '<dir>/%'
```

### Requests not going through a CDN

When acceleration is on but public OSS traffic remains, find what still links
OSS directly:

```
__topic__: oss_access_log AND bucket: "<bucket>"
  AND host: "<bucket>.oss-<region>.aliyuncs.com" AND NOT sync_request: cdn |
  SELECT referer, host, count(*) AS request_count
  FROM log GROUP BY referer, host ORDER BY request_count DESC
```

An empty `referer` usually means the URL was typed or pasted directly.

---

## 4. A syntax conflict worth knowing about

Two credible sources disagree on whether the filter part (before the `|`)
accepts a parenthesised `OR`:

- One reading is that `operation: (PutObject OR PostObject)` is not supported
  in the filter part, and a multi-value filter must be expressed as
  `WHERE operation IN ('PutObject','PostObject')` in the SQL part.
- Published template collections do use the parenthesised `OR` form in the
  filter part.

This has **not** been settled by measurement. Every statement this skill
generates therefore uses the `WHERE ... IN (...)` form, which is safe under both
readings. If a hand-written parenthesised `OR` filter returns zero rows or an
error, rewrite it as an `IN` list rather than concluding that no such request
exists.

---

## 5. Reading the results

| Pattern | Meaning | Where it belongs |
|---|---|---|
| High count from few IPs with `sign_type: NotSign` | A public-read bucket being scraped | Security / abuse workflow, not this skill |
| One AccessKey from many unknown IPs | Possible credential leak | Security workflow |
| The same object fetched hundreds of times | Systematic enumeration | Report the pattern; do not infer intent |
| `sign_type: AdminSign`, or a service-side `sync_request` value | OSS's own bookkeeping | Usually no customer action needed |
| `response_time` far above `server_cost_time` | Delay sits in the transfer path | Performance workflow |

Two hard limits on interpretation:

- **Do not infer file content from an object key**, and do not attribute intent
  beyond what the logged fields show.
- **An empty result is not a clean bill of health.** It means one of: logging
  off for that window, wrong region, window too narrow, key spelled or encoded
  differently, permission gap, or one of the four documented absence causes in
  [module1_log_source.md](module1_log_source.md).
