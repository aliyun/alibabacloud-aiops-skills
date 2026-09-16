# Traffic-Abuse Forensics Playbook

Mandatory investigation sequence for OSS traffic abuse / suspected
security incidents. The decisive evidence lives in the OSS real-time log
(SLS); the control-plane exposure audit only ranks the candidates. Run the
steps in order — each step's output decides how to read the next.

## Step 0 — CDN origin-pull check (always first)

```
__topic__: oss_access_log and bucket: <BUCKET> | SELECT sync_request, count(*) AS req_count GROUP BY sync_request ORDER BY req_count DESC LIMIT 10
```

- `sync_request: cdn` marks CDN origin-pull requests; `-` marks direct
  client requests (official field semantics, help.aliyun.com OSS log
  documentation).
- If most requests are `cdn`, the OSS-side Top IPs are CDN edge nodes, not
  end users — the investigation moves to the CDN side (origin-pull
  configuration, CDN traffic bill). Do not run Top-IP attribution against
  edge-node IPs.

## Mandatory 6-step traffic-source sequence

Every query uses the same base filter (successful direct downloads, CDN
origin-pull excluded) and is run in the SLS console against the dedicated
project `oss-log-<uid>-<regionId>` / logstore `oss-log-store`:

```
__topic__: oss_access_log and bucket: <BUCKET> and operation: GetObject and http_status: 200 not sync_request: cdn
```

| Step | Dimension | Query focus | How to read it |
|---|---|---|---|
| 1 | Auth mode | `sign_type`, `access_id` distribution | **Most decisive.** `NotSign` with `access_id` `-` = anonymous reads (public-read scraping); `NormalSign` with a real AccessKey ID the owner does not recognize = AK-leak branch |
| 2 | Top client IPs | `client_ip` grouped with `sign_type` | Few dominant IPs = scripted scraping from fixed hosts; wide dispersion + third-party referers = hotlinking |
| 3 | User agents | `user_agent` with request count + bytes | Bare HTTP-client UAs (java/python/go clients) = bulk programmatic downloads |
| 4 | Referers | `referer` ordered by downloaded bytes | Empty referer `-` = direct programmatic calls; third-party domains = hotlinking (bandwidth theft) |
| 5 | Top objects | `url_decode(object)` ordered by bytes | Same object fetched dozens/hundreds of times = systematic bulk scraping; never infer file content from key names |
| 6 | Top request URIs | `request_uri` ordered by count | URIs carrying signature parameters (`OSSAccessKeyId` / `Signature`) from many IPs = presigned URL leak or abuse |

Daily-trend shape (the script runs it as step 1d and classifies
automatically, `log_evidence.daily_trend`; thresholds below are this
skill's own heuristic classifier parameters, not official platform facts):

| Shape | Signature | Typical meaning |
|---|---|---|
| burst | one day ≥ 3x the median of the other days | a trigger event — the link got shared, a scraper found the bucket |
| sustained | every day high and stable | long-running business consumption or a long-lived scrape — read the endpoint split (mostly-internal ⇒ likely legitimate) before calling it abuse |
| spiky | large fluctuations, max/min ≥ 3x with sharp peaks | batch-pull scraping — the classic theft signature |

The shape narrows the root cause BEFORE the per-request steps are read;
it never replaces them.

The scripts EXECUTE these statements read-only (`oss_traffic_forensics.py`
→ `realtime_log.queries` → `log_evidence`): `aliyun sls get-histograms`
does the volume pre-count, `aliyun sls get-logs` runs each statement, and
the interpreter classifies the rows. With `--no-log-execution`, or when
the log leg degrades (real-time log not enabled / no permission /
over-cap window), the same statements are emitted ready-to-paste for the
SLS console and the exposure audit still completes.

Query-capacity discipline: a single GetLogs scan covers at most ~300k
entries [measured, not officially documented; official SLS query-limit
pages do not state a numeric row cap for GetLogs — this value is derived
from script auto-detection of over-cap windows]. ~150k rows is a safe
per-slice budget (same source: measured heuristic). When analyzing
manually, split a high-volume day into hourly
sub-ranges (keep each slice comfortably below the cap), then merge the
per-slice GROUP BY results by key
(`client_ip` / `object` / `referer`) across the day; do not trust a
partial scan silently.

## Four-way root-cause classification

| Root cause | Log signature | Exposure precondition | First containment |
|---|---|---|---|
| `public-read-scraping` | `sign_type=NotSign`, `access_id='-'` dominate; IPs concentrated on few hosts | public-read ACL or anonymous policy grant | Switch bucket ACL to private; enable Block Public Access |
| `ak-leak` | `sign_type=NormalSign` with an unrecognized AccessKey ID; source IPs outside the owner's known servers | any — the bucket can be fully private | Disable/rotate the leaked AccessKey in the RAM console; move to STS temporary credentials |
| `hotlinking` | `sign_type=NotSign`, many distinct IPs, referer points at third-party domains | public-readable objects | Anti-hotlink (Referer) whitelist + deny empty Referer; serve static assets via CDN with URL authentication |
| `signed-url-leak` | signature-bearing `request_uri` hit from many distinct IPs with irregular user agents | presigned URLs shared externally | Shorten URL expiration, stop public sharing, rotate the signing AccessKey |

Routing rule used by the script: an open exposure surface (public ACL or
anonymous policy) ranks scraping/hotlinking first; a closed surface
(private ACL + no anonymous policy) ranks `ak-leak` first. The SLS step-1
auth-mode result confirms or refutes the candidate — never conclude a
root cause from the exposure audit alone.

Cross-account attribution trick (field semantics, for the `ak-leak`
branch): a plain signed request logs `extend_information` as
`<requesterParentId>,,,,` (first value = requester's primary account UID);
an STS-assumed request logs
`<requesterParentId>,<roleName>,<roleSessionName>,<roleOwnerId>,`
(fourth value = role owner's primary UID). Official field name:
`extend_information` (source: help.aliyun.com/zh/sls/log-fields-17,
log-fields-13, sls/oss — all three consistent). Splicing rule:
`requesterParentId,roleName,roleSessionName,roleOwnerId` separated by
half-width commas; official notes "may continue to append new fields".
Compare the requester's PRIMARY account UID against the bucket
owner UID to flag genuinely cross-account usage. Never conclude
"cross-account" from `access_id != owner's AK` alone: a RAM sub-user of
the SAME primary account also carries a different AccessKey ID but is
same-account by definition.

## Containment + hardening checklist (manual guidance only)

### V7 trade-off: private-ACL vs anti-hotlink — decide by dependency, never one-sided

Real-ticket lesson (V7): a customer whose site depended on anonymous
public reads switched the bucket to private on a one-sided
recommendation, the site images broke, and they switched BACK to
public-read — the exposure returned. Always present both options with
their premises:

| Option | Security gain | Cost / business impact | Applicable when |
|---|---|---|---|
| A. Switch to private ACL (+ presigned URLs / STS for readers) | Cuts ALL anonymous access; scraping and hotlinking drop to zero immediately | Every anonymous-link consumer breaks with 403 at once; clients must be refactored to fetch signed URLs or STS credentials; one-off migration effort | No legitimate anonymous reader exists, or all clients are under the owner's control and can be refactored |
| B. Keep public-read + layered controls (anti-hotlink Referer whitelist + deny empty Referer + Requester Pays; optionally CDN with URL authentication) | Blocks non-whitelisted referers and bare scripted calls; Requester Pays rejects anonymous requests outright (they fail with EC 0003-00000701 because they carry no `x-oss-request-payer` header); does NOT stop referer-spoofing scrapers | Zero client-side change for browser consumers (Referer is sent automatically); whitelist needs maintenance; native apps / server-side callers with empty Referer need an allowance or a CDN hop; compliant third parties outside the whitelist get rejected too | The site/app serves public static assets via direct OSS links and cannot be refactored immediately (V7's case) |

Decision rule: FIRST ask whether any legitimate anonymous public-read
consumer exists. If yes, start with option B (Requester Pays buys
immediate relief without touching the ACL) and plan an option-A migration
window; if no, go straight to option A. Never emit a one-sided "switch to
private" without stating the breakage it causes.

Public-surface causes (scraping / hotlinking):

1. Switch the bucket ACL to Private (OSS console → bucket → Permission
   Control → Read/Write Permission) and remove any bucket-policy statement
   allowing Principal `*`.
2. Enable Block Public Access for the bucket to override residual grants.
3. Migrate legitimate readers to presigned URLs or STS temporary
   credentials instead of anonymous reads.
4. For hotlinking: configure the anti-hotlink (Referer) whitelist with the
   owner's own domains and deny empty Referer; serve public static assets
   through CDN with URL authentication instead of direct OSS links.

Credential causes (AK leak / signed-URL leak):

5. Disable or rotate the leaked AccessKey in the RAM console immediately;
   audit where the old key was stored (public code repositories, client
   bundles).
6. Replace long-lived AK/SK with STS temporary credentials and
   least-privilege RAM policies scoped to the bucket.
7. For signed-URL leak: shorten presigned-URL expiration and rotate the
   signing key if the URL was posted externally.

Attack-surface reduction (official malicious-traffic best practices):

8. **PrivateLink private access**: for VPC-internal consumers, replace
   public-endpoint access with a PrivateLink endpoint connection — traffic
   never touches the public internet, which removes the attack surface for
   public scraping/DDoS and enables security-group-level source control.
9. **CORS tightening**: restrict cross-origin rules to the real business
   origins/methods instead of `*`, so browser-based abuse from third-party
   sites is rejected.
10. **Anti-enumeration naming**: if objects are named with guessable
    sequential prefixes (timestamps, incrementing IDs), attackers can
    enumerate and scrape the whole namespace; the official guidance is a
    hexadecimal-hash prefix or reversed file names.

DDoS-attack branch (bucket enters the sandbox):

11. When a bucket is under volumetric attack (or holds violating content),
    OSS may move it into the SANDBOX — service degrades (access only via
    the sandbox domain) but stays reachable; the console/billing shows the
    state. The official prevention options are: enable **OSS DDoS
    Protection** (traffic scrubbed in the Anti-DDoS cluster then forwarded
    to OSS; one instance per region binding at most 10 buckets; protects
    ONLY the default public domain — NOT transfer-acceleration or access
    point domains), or front the origin with an ECS reverse proxy bound to
    an Anti-DDoS IP. Recommend these as manual actions when the symptom is
    an attack-driven outage rather than traffic theft.

Universal (always):

12. Set an outbound-traffic alarm (OSS console → Operations & Monitoring →
   Monitoring → Internet Outbound Traffic → alarm rule at 3–5× normal
   volume); the official example alarms on public inbound/outbound traffic
   ≥ 100 Mbytes per 1-minute period via CloudMonitor.
13. Block abusive source IPs by IP/CIDR with a Bucket Policy Deny
   statement (OSS console → bucket → Permission Control → Bucket Policy →
   add a Deny statement with condition `acs:SourceIp` set to the abuser's
   IP/CIDR range; Deny takes priority over any Allow). This is the
   high-frequency containment action in real tickets (observed in multiple
   traffic-abuse tickets); keep legitimate source IPs out of the blocked
   ranges. Caveat when mixing VPC and public clients: an `acs:SourceIp`
   condition only matches public-network requests, so a policy meant to
   ALLOW specific VPCs AND public IPs needs the `acs:SourceVpc` condition
   key as well (public Bucket Policy condition-key semantics).
14. Keep the real-time log (SLS) feature enabled so the next anomaly is
    traceable with this sequence.

## Billing-side reading of the traffic mix

When the complaint is "my outbound bill exploded" rather than "someone is
scraping me", first split the traffic: `sync_request=cdn` origin-pull
egress is metered as CDN origin-pull outbound (`CdnOut`), which is listed
as a separate billing item from internet outbound (`NetworkOut`); the unit
price of each is published on the official pricing page (do not assume a
fixed ratio). If nearly all
traffic is `cdn`, the bill driver is CDN origin-pull volume and belongs to
the CDN bill analysis, not direct OSS abuse — say so instead of forcing a
security conclusion (OSS traffic-fee doc: internet outbound `NetworkOut`
and CDN origin-pull outbound `CdnOut` are billed as separate items,
with cross-region replication traffic `ReplicationDatasize` as a third;
https://help.aliyun.com/zh/oss/traffic-fees ).

Metering-vs-access-log caveat: the bill is computed from the metering
log, which can differ slightly from the access log the queries above read
(sampling boundary, timing, field granularity). Treat access-log sums as
evidence for WHO consumed the traffic, and the metering/billing console
as the authority for HOW MUCH was billed; do not promise the two numbers
match to the byte.

## Customer-communication templates (support-engineering wording)

- **Abuse confirmed**: "Log analysis of `<window>` shows `<N>` source IPs
  (top: `<ip>`) accounting for `<X>`% of outbound traffic with
  `<signature: NotSign anonymous reads / unrecognized AK / third-party
  referer>`. This matches `<root cause>`. Immediate containment:
  `<checklist items, with the V7 trade-off stated when the fix touches the
  read path>`."
- **Normal business traffic**: "The analyzed window is dominated by
  same-region internal-endpoint traffic (`<x>`%, `-internal.aliyuncs.com`
  hosts) and authorized CDN origin-pull; no anomalous external source was
  found. This looks like normal business traffic, not abuse — check the
  billing-side split (internet outbound vs CDN origin-pull) before
  escalating."
- **Insufficient evidence**: "The real-time log is not enabled for this
  bucket (or the window has already rolled out of the rolling 7-day
  retention); per-request attribution is not possible retroactively.
  Enable the real-time log now so the next anomaly is traceable."
- Never characterize file CONTENT from object key names — report transfer
  behavior only; whether the traffic was "theft" is a business/legal
  conclusion the customer makes, not the forensics.
- Before declaring abuse, distinguish it from a legitimate surge: read the
  daily-trend shape AND the endpoint split first (a sustained, mostly-
  internal curve is business traffic even when it is large).

## Evidence channels (customer-side observability only)

- **OSS real-time log (SLS)** — primary channel; enable it via OSS console
  → bucket → Log Management → Real-time Query → Enable now.
  Asset naming:
  project `oss-log-<uid>-<regionId>`, logstore `oss-log-store`.
- **OSS log storage (delivery)** — alternative when real-time query is not
  enabled; logs delivered to a customer-owned bucket, analyzed offline.
- **OSS console monitoring** — coarse traffic curves for anomaly timing.
- **ActionTrail** — for API-level audit questions (who changed the bucket
  configuration): OSS data events must be delivered to SLS to be queried;
  guide the user there. This skill does not call ActionTrail APIs.
