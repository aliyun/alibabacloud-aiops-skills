# Module 5: Boundaries, Escalation and Customer Wording

What this skill cannot prove, how it says so, and how the result is handed to a
human being.

---

## 1. Scope

**In scope:** explaining why an OSS request failed or behaved unexpectedly, using
the customer's own realtime access log and the customer's own bucket, object and
RAM configuration. Read-only throughout.

**Out of scope — defer to the matching capability, and name it:**

| Request | Where it belongs |
|---|---|
| Bill amounts, cost attribution, resource packages | The OSS billing-diagnosis capability, or the billing console |
| Traffic-abuse or theft emergency mitigation (blocking IPs, changing an ACL, disabling keys) | The OSS security-incident forensics capability |
| Endpoint resolution errors (wrong region, internal endpoint used off-network, custom domain resolution) | The OSS endpoint-diagnosis capability |
| Transfer-acceleration error codes | The OSS transfer error-code capability |
| Event notification or upload callback faults | The OSS event-notification capability |
| Multipart upload tuning (part size, concurrency) | The OSS multipart-upload capability |
| Transfer throughput analysis (slow uploads or downloads) | A performance-diagnosis flow; this skill only reports the timing fields it happens to see |
| Applying any fix | The customer, or support. This skill never changes a configuration |
| Reading object data | Not requested by default; the relevant command is handed to the customer instead |
| Who changed a configuration (ACL, policy, RAM) | **ActionTrail** — management-plane history is not in the access log |

When a request falls outside the scope, say so and point at the right place. Do
not stretch the evidence to cover it. Naming the boundary is itself a useful
answer; a confident answer built on the wrong evidence is not.

---

## 1b. The two-mode design and the STATUS contract

This skill has two modes, and which one runs is decided by evidence, not by
preference:

| Mode | Precondition | Output |
|---|---|---|
| **Direct read** | The log channel is available, the caller may read the logstore, and realtime logging is on | The traced row plus the configuration evidence, correlated into an A/B/C verdict |
| **Degraded** | Any of those is missing | The derived log target, the console verification path, and ready-to-run statements — with a plain statement that **no query was executed** |

Every report carries two contract lines:

| Line | Values | Meaning |
|---|---|---|
| `STATUS:` | `OK` / `DEGRADED` | `DEGRADED` whenever anything failed, was unavailable, or could not be verified |
| `NEXT_ACTION:` | one sentence | The single next step the customer should take |

Relay both in the final answer. `STATUS: DEGRADED` is not a failure of the skill
— it is the honest result of an environment that could not supply evidence, and
it is far better than an invented conclusion.

**The one wording rule that matters most here:** an unexecuted query must never
be reported as an empty log. "No query was executed; run this statement
yourself" and "the log contains no such request" are different statements, and
only the first one is true in degraded mode.

---

## 2. What cannot be verified from the customer side

These four evidence sources decide many OSS failures and none of them is
reachable through a customer-facing API. A conclusion that depends on them is
**class C** and must be escalated rather than inferred.

| Unreachable evidence | What it would have settled | Consequence |
|---|---|---|
| The server-side request log | The exact denial message, the string-to-sign and the canonical request | A signature mismatch can only be narrowed to ranked candidates, never pinpointed |
| Sandbox or isolation state of a bucket | Whether the bucket is under a governance hold, where configuration changes cannot restore access | A denial may persist after every configuration fix; this cannot be ruled out from the customer side |
| Throttling records | Whether a rate limit was hit in a given window | Sporadic 503 responses cannot be attributed |
| Compliance or risk-control records | Whether an account, bucket or object is blocked | `0003-00000801` and part of `0003-00000005` stay unresolved |

The report states these gaps in a dedicated section. Omitting the section while
still giving a confident conclusion is the exact failure mode this module exists
to prevent.

---

## 3. The ticket package

For a class C verdict the script emits a package. Paste it into the ticket as-is;
it contains no credential material and no configuration change.

```
skill            : alibabacloud-oss-access-log-trace-diagnosis
session id       : <32-character hex>
bucket           : example-bucket
region           : cn-hangzhou
owner uid        : 1234567890123456
request id       : 65A1B2C3D4E5F6G7H8I9J0K1
logged time      : 12/Jun/2026:09:41:07
operation        : GetObject
http status      : 403
error code       : AccessDenied
ec               : 0003-00000001
object           : images/a.png
client ip        : 198.51.100.7
host             : example-bucket.oss-cn-hangzhou.aliyuncs.com
sign type        : NormalSign
verified here    : <what the skill did prove>
could not verify : <what needs support-side evidence>
conclusion so far: <the honest partial conclusion>
```

The request ID is the single most valuable field in this package: it is the key
support uses to locate the server-side record. If the customer has it, get it
into the ticket even when everything else is missing.

---

## 4. Customer-facing wording

The report file is an engineering artefact. What is pasted to the customer is a
short message built from it. Rules:

1. Plain text, no tables in the customer message.
2. State the abnormal facts and the customer's action items. Leave out the
   reasoning chain, the field names and the query syntax.
3. **No low-level inference**: never guess a cause that the evidence did not
   establish. If the verdict is class B, say which candidates remain and what to
   check — do not pick one to sound decisive.
4. Anything undetermined becomes a numbered self-check list the customer can
   follow.
5. Quote configuration verbatim when the finding is a configuration match: the
   matched statement, and the condition values that were compared.
6. Never characterise the customer's data. An object key is the customer's own
   naming; drawing conclusions about file contents from a path is both unreliable
   and a privacy violation.

### Banned in the customer message

| Banned | Why | Use instead |
|---|---|---|
| "diagnosis completed", "check completed" as an opener | Filler that delays the point | State the finding directly |
| Log field names (`sign_type`, `vpc_id`, `extend_information`) | The customer cannot act on a schema | Describe the fact: "the request was unsigned", "the request came over the public network" |
| Query syntax, SQL, topic filters | Implementation detail | Omit entirely |
| Verdict class letters (A / B / C) | Shorthand from this module | Say what it means: "confirmed from your configuration", "two possibilities remain", "this needs a support ticket" |
| "probably", "most likely", "should be" for a class C verdict | A guess presented as a finding | "This cannot be determined from your side; support has to check it" |
| Any region alias or account number not supplied by the customer | Noise, and a possible leak | Reference only what the customer gave |

### Opening templates

Confirmed cause (class A):

> Your request failed because {cause in one sentence}. The evidence is
> {the configuration or log fact}. To fix it: {numbered actions}.

Narrowed but unconfirmed (class B):

> Your request failed with {error}. Your own logs and configuration rule out
> {what was excluded}, which leaves {N} possibilities: {ranked list}. To tell
> them apart: {one verification step per possibility}.

Needs support (class C):

> Your request failed with {error}. The cause is recorded on the service side,
> which is not visible to you or to this check, so it cannot be confirmed here.
> Please open a ticket and attach the block below. Retrying the request, or
> re-issuing credentials, will not change this outcome.

### Closing

State what was **not** changed:

> This check was read-only. No bucket setting, policy or object was modified.

Do not add boilerplate such as "please check first and contact us if needed" —
the action items above already say what to do.

---

## 5. Report delivery

1. Write the full report to a file with `--output output/<bucket>-diagnosis.md`.
2. In the conversation, reply with the file link, the verdict class in words,
   and one key conclusion. Do not paste the full tables into the chat.
3. Present results as tables inside the report; never paste a raw API response.
4. A field obtained from more than one source appears once.
5. The customer-facing message is emitted in the conversation body, **not**
   written into the report file, so it can be copied directly.

---

## 6. Failure circuit-breaker

| Situation | Behaviour |
|---|---|
| One configuration read fails | Record `[WARN]`, mark the field unavailable, continue with the remaining evidence |
| The log probe fails | Record the probe status, continue on configuration evidence alone, and list the log-dependent conclusions as unavailable |
| A rule raises an unexpected error | Record it, fall back to the "not covered by the knowledge base" answer, still emit a report |
| The CLI is missing | Exit with installation and configuration guidance; never ask for an access key |
| Every source fails | Emit the report skeleton with all gaps stated. Never emit a conclusion without evidence |

A report that says "three of five evidence sources were unavailable, so no cause
is asserted" is a correct outcome. A confident cause built on one successful read
out of five is not.
