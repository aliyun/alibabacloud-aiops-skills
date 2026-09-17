# Dial-test / site-monitoring guidance (endpoint reachability from a region/ISP)

When a customer reports "OSS is unreachable from a certain region", "some
regions return 6xx", or "downloads are slow only in one province/ISP", the
root cause is often the network path between a specific region + ISP and the
OSS endpoint -- not the endpoint string itself. This reference tells the Agent
how to **guide the customer / frontline to run a dial-test themselves and how
to interpret the result**. It complements `endpoint-rules.md` (which decides
whether the endpoint string is correct) and `diagnosis-tree.md`.

## 0. Scope boundary (read first -- what this skill does and does NOT do)

- This skill is **read-only** and issues only GetBucketInfo / ListBuckets /
  ListCname / GetCallerIdentity plus an OS-level DNS probe. It **never runs a
  dial-test itself** and never creates a monitoring task.
- The Agent's job here is to (a) hand the customer the exact dial-test target
  URL, (b) tell them where to run it (self-service), and (c) interpret the
  result they bring back into a region/ISP attribution.
- **Not ported (out of scope):** any internal dial-test backend / internal
  CLI (e.g. an internal `site-monitor-run` style command that creates a real
  monitoring task on an internal system). Such tooling is an internal-channel
  dependency and is deliberately excluded; the equivalent capability is
  delivered below through **customer-facing self-service channels only**
  (CloudMonitor console site monitoring + `ossutil probe`). Source of the
  ported methodology: the internal OSS-assistant dial-test knowledge base, cap13-dial-test-detail.md
  (142 lines); the internal command invocations at cap13:13-67,94-107,118-121
  are NOT ported, only the target forms / interpretation / SOP / anti-patterns.

## 1. OSS-native self-service probe: `ossutil probe` (official)

`ossutil probe` measures network connectivity and upload/download bandwidth
between the client host and OSS, and suggests a concurrency value. It runs
entirely on the customer side (no internal channel), so it is the first
self-service tool to recommend when the question is "is the path from THIS
client to OSS healthy / how fast".

- Docs: help.aliyun.com/zh/oss/developer-reference/probe and
  help.aliyun.com/zh/oss/developer-reference/probe-probe-state
- Modes: `--upload` / `--download`; reports connectivity, bandwidth, and a
  best-concurrency suggestion.
- Use it to separate "this client's path is bad" from "OSS-side / endpoint
  misconfiguration". It is client-local, so it does NOT tell you whether a
  *different* region/ISP is affected -- for that use CMS site monitoring (sec.2).

## 2. CloudMonitor (CMS) site monitoring -- multi-node region/ISP dial-test

CMS site monitoring fires HTTP(S) requests to a target URL from many
ISP + city probe nodes across the country and returns each node's response
code and timing. It is the right tool to answer "which region / which ISP
cannot reach OSS". The customer runs it in the **CloudMonitor console**
(Site Monitoring) as a self-service task; the Agent supplies the
target URL and interprets the returned per-node results.
(ported from cap13:7-9,30-36; delivery channel changed from an internal CLI to
the customer-facing CMS console.)

### 2.1 Dial-test target forms (ported cap13:30-36)

| Scenario | Target URL |
|---|---|
| Public HTTP(S) access | `https://<bucket>.oss-<region>.aliyuncs.com` (append `/<object>` to test a real object) |
| Transfer acceleration | `https://<bucket>.oss-accelerate.aliyuncs.com` |
| Custom domain (CNAME) | `https://<custom-domain>` (see `endpoint-rules.md` sec.3.3) |

Always pass a **full URL including the scheme** (`https://...`); a bare domain
may default to HTTP and produce a misleading result (anti-pattern sec.4).

### 2.2 Result interpretation (ported cap13:69-88)

Read each probe node's HTTP status:

| Node result | Meaning | Attribution |
|---|---|---|
| 2xx / 3xx | Normal response | That node can reach the target |
| 4xx | Client error (e.g. 404 / 403) | Usually the request itself, NOT a network problem |
| 5xx | Server error | OSS-side; investigate further |
| **6xx** | **ISP hijack / interception** | Carrier/middlebox problem, NOT an OSS-side problem |
| No response / timeout | Path down | That node's route to the target is broken |

**About 6xx (ported cap13:81-88):** 6xx codes are not standard HTTP; they are
abnormal responses injected by an ISP or an intermediate network device.

- **610** -- timeout (`context deadline exceeded`): ISP path down or a link
  black-hole.
- **612** -- connection reset (`connection reset by peer`): ISP firewall / RST
  blocking.
- **601-609** -- DNS hijack, WAF/firewall interception, ISP cache anomaly, etc.
- **610 and 612 can BOTH mean ISP blocking** -- do not rule out carrier
  blocking just because 610 looks like a "timeout" or 612 like a "reset";
  RST blocking typically shows as 612 and a link black-hole as 610.
- If **one ISP's nodes in a region broadly return 6xx while other ISPs are fine**
  -> that ISP's problem: advise switching ISP or using **transfer acceleration**
  to bypass it (transfer-acceleration skill).

### 2.3 Narrowing to a specific region + ISP (ported cap13:90-109)

Full-node dial-tests cover ~150+ nodes and poll slowly. When only one
region/ISP matters, restrict the probe set to that region's city + ISP codes in
the CMS console to cut the wait. (The internal `--isp-cities` JSON flag at
cap13:98-109 is an internal-CLI detail and is NOT ported; the console exposes
the same node selection.)

## 3. Dial-test troubleshooting SOP (ported cap13:113-133)

### Scenario A -- "OSS unreachable from a region / partial 6xx"

1. Confirm the target URL: the bucket public domain
   `https://<bucket>.oss-<region>.aliyuncs.com` (verify the endpoint string
   first via `endpoint-rules.md`; a wrong endpoint is not a network problem).
2. Have the customer run a CMS site-monitoring dial-test against that URL
   (self-service, sec.2).
3. Interpret:
   - One region + one ISP broadly 6xx -> **ISP problem**: advise transfer
     acceleration or a different ISP.
   - All ISPs in one region abnormal -> possible region-to-OSS path problem:
     escalate to the network team.
   - All nodes normal -> the problem is client-side (local DNS, local network,
     firewall); go back to `ossutil probe` on the affected client (sec.1).
4. State the conclusion with scope (region + ISP), the status codes observed,
   and the recommended action.

### Scenario B -- "downloads slow in one region"

1. First rule out OSS-side causes (client-tools / transfer-error-code skills).
2. If the OSS side is clean, use a CMS dial-test to look at the response-time
   distribution per ISP in that region.
3. Conclude whether it is a regional ISP network-quality problem (and whether
   transfer acceleration would help).

## 4. Anti-patterns (ported cap13:136-143)

- **Dial-test target without a scheme** -- pass a full URL (`https://...`);
  a bare domain may go over HTTP and skew the result.
- **Full-node dial-test when only one region matters** -- ~150+ nodes poll
  slowly; restrict to the target region/ISP nodes.
- **Treating a 4xx as a network problem** -- 4xx (404 / 403) is a normal
  client error, not an ISP problem; only 6xx means ISP hijack/interception.
- **Judging the path down from a single timing-out node** -- a few nodes not
  responding is normal (node-side issue); conclude only when **multiple nodes
  of the same region + ISP** are broadly abnormal.
- **Running the dial-test on the customer's behalf through an internal
  channel** -- out of scope (sec.0); always hand the customer the self-service
  CMS console / `ossutil probe` path and interpret what they return.

## 5. Traceability

Every claim above maps to either the internal OSS-assistant dial-test knowledge base (cap13-dial-test-detail.md)
(line ranges cited inline) or an official OSS/CMS doc:
`ossutil probe` (help.aliyun.com/zh/oss/developer-reference/probe,
probe-probe-state), transfer acceleration and endpoint forms
(help.aliyun.com/zh/oss/user-guide/access-and-network-overview,
regions-and-endpoints), custom domain (access-buckets-via-custom-domain-names).
The internal dial-test backend commands are explicitly excluded (sec.0).
