# Module 1: The Realtime Access-Log Source

Everything this skill proves about a single request comes from the customer's own
realtime access log. This module covers how to address it, what it contains, and
the two mistakes that silently produce wrong numbers.

---

## 1. Two different logging features — do not confuse them

| Feature | Where the data goes | How it is read | Latency | Used by this skill |
|---|---|---|---|---|
| **Realtime log query** | A Log Service project created per account per region | Log query API | about 3 seconds for realtime data | **Primary source** |
| **Periodic log shipping** | Log objects written into a bucket the customer designates | Download the log objects and parse them | hours | Fallback only |

The distinction matters because the two have different field layouts, different
latency and different setup paths. A customer who says "I have logging on" may
mean either one. `log_source_check.py` reports which is present.

Realtime log query is enabled per bucket in the console, under the monitoring
section of the bucket. Periodic log shipping is a bucket configuration that can
be read back and is reported by the probe when realtime logging is absent.

---

## 2. Addressing the log source

The project name is derived, never guessed:

```
project   : oss-log-<uid>-<region>
logstore  : oss-log-store
endpoint  : <region>.log.aliyuncs.com
```

`<uid>` is the account number, which `sts_token.py` derives from the caller
identity — the customer should never be asked for it. `<region>` is the region of
the **bucket**, and the project is per region: a bucket in another region writes
to another project. Getting the region wrong yields an empty result that looks
exactly like "no such request", which is why the probe reports the project name
it used.

### The topic filter is mandatory

One logstore carries **three** kinds of rows:

| `__topic__` | Content |
|---|---|
| `oss_access_log` | One row per request — what this skill needs |
| `oss_batch_delete_log` | One row per key removed by a **batch** delete call |
| `oss_metering_log` | One row per bucket per hour — usage counters |

Every query this skill issues pins the topic:

```
__topic__: oss_access_log AND bucket: <bucket>
```

Without it, a `count(*)` over the logstore mixes per-request rows with hourly
metering rows and every rate, ratio and top-N result becomes meaningless. This
is the easiest mistake to make and the hardest to notice, because the query
still returns data.

**The batch-delete split is the second trap.** A batch delete call logs only
**one** request row in the access topic; the individual removed keys are
recorded under `oss_batch_delete_log` and join back through `request_id`. So a
"who deleted my files" question answered from the access topic alone reports a
single delete request and no keys, which reads like "nothing was deleted".
`user_agent` in the batch-delete rows attributes the source — a console user
agent means the removal came from the console rather than from application code.

---

## 3. Field catalog

Field names below are the realtime access-log schema. Support tooling uses a
different schema for server-side logs with different names for the same concepts;
the two must never be mixed, and only the names below are valid here.

### Identity

| Field | Meaning |
|---|---|
| `bucket` | Bucket name |
| `owner_id` | Account ID that owns the bucket |
| `requester_id` | Requester ID; `-` for anonymous access |
| `access_id` | AccessKey ID used; `-` when unsigned |
| `sign_type` | `NotSign`, `NormalSign` (V1 header), `UriSign` (V1 presigned URL), `AdminSign` (service-side), `NORMAL_SIGN4` (V4 header), `URI_SIGN4` (V4 presigned URL) |
| `extend_information` | For RAM-role requests: `requesterParentId,roleName,roleSessionName,roleOwnerId`, comma separated; further fields may be appended |
| `user_defined_log_fields` | Base64 of a JSON object holding configured custom headers and parameters |

`extend_information` is the authoritative field for identity questions. Note the
casing of `sign_type` values: the first four are camel case while the two V4
values are upper case with underscores, so comparisons must not assume one style.

### Network

| Field | Meaning |
|---|---|
| `client_ip` | Client IP — the caller itself, or its firewall or proxy |
| `host` | Request host, e.g. `bucketname.oss-cn-beijing.aliyuncs.com` |
| `http_type` | HTTP or HTTPS |
| `vpc_id` | ID of the VPC through which OSS was reached; empty or `-` for public access |
| `vpc_addr` | Integer form of the VPC address; see the conversion note below |
| `referer` | Referer header |
| `user_agent` | User-Agent header |

`vpc_id` being empty is how a public request is recognised, which is what a
source-VPC policy condition is evaluated against.

To turn `vpc_addr` back into an address:

```sql
select int_to_ip(cast(vpc_addr as bigint))
```

The octets of the result come back **reversed** and must be reversed again
before use. Reporting the raw conversion as an address is a wrong finding.

### Request

| Field | Meaning |
|---|---|
| `http_method` | HTTP method |
| `operation` | OSS operation name — see the traps below |
| `request_uri` | URI including the query string, **URL encoded** |
| `object` | Object key, **URL encoded** |
| `object_size` | Object size in bytes |
| `request_length` | Request size including headers, in bytes |
| `content_length_in` | Request `Content-Length` in bytes |
| `sync_request` | `-` normal request, `cdn` CDN back-to-origin, `lifecycle` lifecycle execution |
| `logging_flag` | `true` when periodic log shipping is enabled |

### Response and timing

| Field | Meaning |
|---|---|
| `http_status` | HTTP status returned |
| `error_code` | Classic OSS error code; `-` on success |
| `ec` | **Detailed EC error code — the primary diagnosis key** |
| `response_time` | Total response time in milliseconds, including transfer |
| `server_cost_time` | Server-side processing time in milliseconds |
| `response_body_length` | Response body size in bytes, excluding headers |
| `content_length_out` | Response `Content-Length` in bytes |

`response_time` versus `server_cost_time` separates transfer time from service
time; a large gap points at the network path rather than at OSS.

### Storage and acceleration

| Field | Meaning |
|---|---|
| `bucket_storage_type` | `standard`, `archive`, `IA`, and the other storage classes |
| `bucket_location` | Data center of the bucket, usually `oss-<regionId>` |
| `delta_data_size` | Object size change; `0` if unchanged, `-` if not an upload |
| `restore_priority` | Restore priority for archive retrieval |
| `archive_direct_read_size` | Bytes billed as archive direct read |
| `acc_access_region` | Access-point region for a transfer-acceleration request, else `-` |
| `time` | Request end time, e.g. `27/Feb/2018:13:58:45`. Use `__time__` for a timestamp |

---

## 4. Operation-name traps

| Logged operation | What it actually is |
|---|---|
| `GetBucket` | **Listing objects**, not reading bucket attributes |
| `CompleteUploadPart` | Completing a multipart upload. `CompleteMultipart` does not appear in the log — querying it returns zero rows and looks like "the upload never finished" |
| `InitiateMultipartUpload` | Initialisation only; carries almost no payload |
| `UploadPart` | The actual data transfer of a multipart upload |
| `PostObject` | Form-based upload, where the policy and signature travel in the form body |
| `ProcessImage` | An image-processing request |

When measuring upload throughput, the payload-bearing operations are `PutObject`,
`PostObject`, `UploadPart` and `AppendObject`.

---

## 5. Indexing: what may appear before the pipe

A log query has two parts: a filter before `|` and an SQL statement after it.
Only indexed fields may appear in the filter part.

Usually indexed: `bucket`, `owner_id`, `access_id`, `client_ip`, `host`,
`http_method`, `operation`, `http_status`, `error_code`, `ec`, `sign_type`,
`sync_request`, `request_id`, `bucket_storage_type`, `vpc_id`.

Usually **not** indexed: `object`, `request_uri`, `referer`, `user_agent`,
`object_size`, `response_time`, `server_cost_time`, `response_body_length`,
`content_length_in`, `content_length_out`, `requester_id`,
`extend_information`.

Index configuration is **not** customer-editable for this dedicated logstore:
it accepts no other data and its index cannot be modified, although query,
statistics and alerting are unrestricted. So the two lists above are stable
rather than per-account, and the fix for a filter that returns nothing is never
"add an index" — it is to move the predicate into the SQL part.

```
__topic__: oss_access_log AND bucket: my-bucket |
  SELECT time, operation, http_status FROM log
  WHERE url_decode(object) = 'images/a.png'
  ORDER BY __time__ DESC LIMIT 20
```

---

## 6. When the probe says the log is unusable

`log_source_check.py` distinguishes four outcomes, because each needs a
different customer action:

| Probe status | Meaning | Customer action |
|---|---|---|
| `available` | Readable and returning rows | Proceed to tracing |
| `no_data_in_window` | Logstore reachable, no row for this bucket in the window | Widen the window; verify the bucket name and its region |
| `not_enabled` | The project does not exist | Enable realtime log query in the console |
| `not_permitted` | Reachable but the credential may not read it | Grant the log read action from [ram-policies.md](ram-policies.md) |

Two statements must accompany a `not_enabled` result, because omitting either
one misleads the customer:

1. Realtime logging captures only requests made **after** it was enabled.
   Historical requests cannot be recovered this way.
2. Realtime data becomes queryable in roughly three seconds, so a request made
   moments ago should already be visible; anything older than that is a genuine
   gap rather than lag.

An empty result is never reported as "no problem occurred". It is reported as
"no evidence available", with the reason.

---

## 7. Why an expected request row may be ABSENT

Log absence never proves the request did not happen. Four causes are documented,
and one of them must be quoted instead of concluding "no such request occurred":

| # | Cause | What it means | How to check |
|---|---|---|---|
| 1 | **CDN cache hit** | The request was served by a CDN edge and never reached OSS | Look at CDN offline logs for cache-served requests |
| 2 | **Client-side interruption** | The request died before reaching OSS (client network or configuration) | Inspect the client SDK error logs around the same timestamp |
| 3 | **Log push failure** | OSS does not guarantee 100% log delivery; a small loss rate is documented expected behaviour | Treat a single missing row as inconclusive, not as proof |
| 4 | **Cross-region endpoint usage** | The request hit another region's endpoint for this bucket, so it landed in that region's project | Query the project of the region whose endpoint was used |

Cause 3 is the one that most often gets missed: a customer who is told "no
record exists, so the request never happened" has been given a conclusion the
platform explicitly does not support.

---

## 8. Custom log fields (`user_defined_log_fields`)

The standard schema is fixed, but a bucket may additionally record up to **6**
chosen request headers and/or query parameters.

| Property | Value |
|---|---|
| Where it lands | The single field `user_defined_log_fields`, Base64-encoded JSON with the keys `headers`, `querys` and `truncated` |
| Size cap | Key and value combined, 1024 bytes; keys are lowercased |
| Prerequisite | Realtime log query must be enabled |
| Takes effect | Within roughly 15 minutes |
| Typical use | Recording `x-forwarded-for` to recover the real client IP behind a CDN or proxy chain. Header names must use hyphens, not underscores |

The consequence for tracing: when the real behind-proxy client IP is needed and
this field was **not** configured for the window in question, it cannot be
recovered — it can only be enabled going forward. Say that plainly instead of
substituting the proxy's IP for the end user's.

---

## 9. Retention, cleanup and cost

| Fact | Detail |
|---|---|
| Logstore retention | 7 days by default; adjustable in the log service, and beyond the free tier its billing applies |
| Shipped log files | **Never** auto-deleted. A lifecycle rule on the destination bucket is required to clean them up |
| Free tier (feature-based billing) | Retention of 7 days or less **and** daily write (compressed) plus index traffic of 900 GB or less (about 900 million records at 1 KB each) incurs no log-service charge |
| Free shard quota | 16 x 31 shard*days per month; excess is billed |
| Charged at standard rates | Read traffic, internet traffic, data transformation and delivery of the dedicated logstore |
| Do not delete | The OSS-related log project or logstore — log push breaks |
| Cannot enable | A bucket without a region attribute cannot enable realtime log query |

Quote these figures only from this table; never invent numbers.

---

## 10. Data plane only

Realtime access logs cover the **data plane**. Management-plane events — who
changed a RAM policy, a bucket ACL, a policy or any bucket configuration — are
recorded in **ActionTrail**, not in this log.

So "who deleted my file" is answerable here, while "who made my bucket public"
is not: that is an ActionTrail question. Stating the boundary is part of the
answer; silently returning an empty result is not.

---

## 11. Sources

Field catalog, naming rules, absence causes, custom fields, retention and
billing figures in this module come from the public Alibaba Cloud
documentation. Runtime verification against the help-center index is performed
by `scripts/_doc_lookup.py` when the entry script is given `--question`; cite
only URLs that lookup actually returns, and never recall a documentation URL
from memory.
