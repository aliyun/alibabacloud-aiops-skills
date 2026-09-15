# M1: Adoption Decision Tree - Transfer Acceleration "Not Taking Effect" Detection

This module is the knowledge base behind the entry script's
`verdict.adoption` field. It answers one question: the user says "I
enabled transfer acceleration but it does not work / is still slow" -
what is actually wrong?

## Accelerate domain forms

| Domain | Applies to | Notes |
|---|---|---|
| `oss-accelerate.aliyuncs.com` | Global acceleration (mainland China <-> overseas and all cross-region paths) | The default choice |
| `oss-accelerate-overseas.aliyuncs.com` | Non-mainland-China-only acceleration (overseas <-> overseas) | Cheaper path when traffic never touches mainland China |

Rules on the endpoint value (source: help.aliyun.com transfer
acceleration FAQ, verified 2026-08):

- The SDK / ossutil **Endpoint string must not contain the bucket
  name**: exactly `oss-accelerate.aliyuncs.com`. Configuring
  `<BucketName>.oss-accelerate.aliyuncs.com` as the Endpoint fails DNS
  resolution (the bucket-prefixed form is the resulting request host,
  not the configured Endpoint).
- Accelerate domains serve **object data access only** (bucket-prefixed
  third-level requests). Management/control-plane operations such as
  ListBuckets are not served by them; this skill therefore always
  queries bucket metadata through a regioned endpoint.
- After enabling, requests must be sent to the accelerate domain for
  acceleration to happen. Enabling the switch alone changes nothing in
  the client's traffic path; the bucket's original domains keep working
  normally in parallel, so clients can migrate gradually.
- **Custom-domain CNAME acceleration**: a custom domain can CNAME to an
  accelerate domain, but an ICP-unregistered domain cannot resolve to a
  mainland-China IP - the official guidance is to CNAME it to
  `oss-accelerate-overseas.aliyuncs.com` instead of the global one.

## Official limits and operational patterns

- Protocol: accelerate domains serve only HTTP/HTTPS API traffic; RTMP and
  other non-HTTP protocols are not supported on them.
- Third-level bucket-prefixed access only (no management operations - as
  above).
- Backend transport may use HTTPS even when the client uses HTTP, so access
  logs can show HTTPS protocol for such requests - not an anomaly.
- **Domain fallback design**: the accelerate domain and the public domain
  are independent; an outage of one does not affect the other. Official
  best practice: applications should auto-degrade to the public domain
  when the accelerate domain misbehaves.
- **CDN double-acceleration**: pointing the CDN origin-pull to the
  accelerate domain builds "CDN edge cache + transfer acceleration" for
  globally distributed static content.
- **Big files**: combine transfer acceleration with multipart upload /
  resumable download to cut timeout risk on long-distance links.

## Measured enablement-status semantics

Status is read with the oss2 SDK call
`bucket.get_bucket_transfer_acceleration()` (measured on oss2 2.19.1):

| OSS response | Meaning for diagnosis |
|---|---|
| 200 with `Enabled=true` | Feature is switched on |
| 404 `NoSuchTransferAccelerationConfiguration` | Feature was **never enabled** - this is the diagnostic finding `enabled=false`, not an API failure |
| 403 / other errors | Unknown; degrade, never guess the state |

## The decision tree

Inputs: feature status (`enabled` / `disabled` / `unknown`) and the
classified client endpoint (accelerate / accelerate-overseas / public /
internal / custom domain / invalid).

| Feature status | Client endpoint | Verdict | Root cause / advice |
|---|---|---|---|
| enabled | accelerate or accelerate-overseas | `effective` | Adoption is correct. If still slow: check the ~30-minute propagation window, ISP link quality, and VPN exit location (below) |
| enabled | public / internal / custom domain | `not_effective_endpoint_not_replaced` | The classic root cause: the switch is on but clients still use the plain endpoint, so traffic never enters the acceleration path. Replace the client Endpoint with `oss-accelerate.aliyuncs.com` and re-test after the propagation window |
| disabled | accelerate or accelerate-overseas | `accelerate_endpoint_without_feature` | Requests to the accelerate domain **fail** while the feature is off. Enable the feature in the OSS console (Bucket -> Bucket Configuration -> Transfer Acceleration), then wait out the propagation window |
| disabled | public / internal / custom domain | `feature_not_enabled` | Nothing is switched on. Decide from the access pattern whether enabling is worthwhile (cross-border / cross-region: yes; same-region same-network: no - plain endpoint is correct) |
| unknown | any | `unknown` (DEGRADED) | Status query failed (permission / network). Fall back to user-provided evidence: console screenshot or status description of the bucket's Transfer Acceleration page, then run this table on that evidence and declare the evidence source |

## Known-effect modifiers (ticket-proven)

1. **Propagation window**: enabling or disabling takes about **30
   minutes** to propagate globally. Testing immediately after switching
   produces false "no effect" reports.
2. **502/504 on the accelerate domain** can be normal automatic path
   switching inside the acceleration network; clients should retry with
   exponential backoff instead of treating isolated 502/504 as an
   outage.
3. **VPN testing caveat**: a client testing through a VPN exits from
   the VPN gateway's location, not its real location; the measured
   effect then reflects the VPN path and distorts the conclusion.
4. **ISP-link bound**: cross-border acceleration optimizes the route but
   cannot fully eliminate international link fluctuation; results are
   bounded by the underlying carrier links.
5. **Disabling breaks the domain**: after the feature is switched off,
   requests to `oss-accelerate.aliyuncs.com` return errors (e.g. 400
   class) until clients are switched back to plain endpoints - plan the
   client rollback together with the console switch.
6. **Downstream-service domain restrictions**: some third-party or
   Alibaba Cloud downstream services (e.g. AI services validating the
   image URL's region) accept only the bucket's regional default domain
   and treat the accelerate domain as an unexpected region. Keep the
   default domain for those specific calls while using the accelerate
   domain for the accelerated upload/download path.

## Enablement is a manual console action

This skill never enables, disables, or reconfigures transfer
acceleration. Guidance is worded as: OSS console -> target bucket ->
Bucket Configuration -> Transfer Acceleration -> switch on/off (per the
official FAQ this is free to enable; traffic fees follow
[fee-facts.md](fee-facts.md)).
