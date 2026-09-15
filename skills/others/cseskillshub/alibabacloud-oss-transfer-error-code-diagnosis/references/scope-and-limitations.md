# Scope and Limitations

## In scope

- Mapping an OSS upload/download error code or HTTP status to a root-cause
  direction (permission / credential-signature / client network / tool usage /
  file limits / server side).
- Client-side vs server-side responsibility attribution.
- Troubleshooting steps distilled from 472 real support tickets.
- Network optimization and transfer acceleration advice for timeout-family
  errors.

## Out of scope (never handle here)

| Topic | Why | Handoff |
| --- | --- | --- |
| DDoS sandbox mitigation | Requires platform-side action | Human support ticket |
| Deleted-data recovery | Needs backend restore workflow | Human support ticket |
| Commercial refunds / billing disputes | Commercial process | alibabacloud-oss-billing-diagnosis or human support |
| Endpoint / internal-network choice deep dive | Different diagnosis track | alibabacloud-oss-endpoint-internal-diagnosis |
| Presigned URL generation or V4 signing deep dive | Different diagnosis track | alibabacloud-oss-presigned-url-v4-diagnosis |
| Live network probing (ping/TCP tests against OSS) | This skill is knowledge-driven with zero network calls | Guide the user to run local checks themselves |
| NON-OSS product errors (SSH / MySQL / Redis / MongoDB / PostgreSQL / RDS / CDN / k8s / docker connectivity, ECS host-level curl probes) | A timeout or 403 from another product is not an OSS transfer error, even when the wording matches a trigger phrase | Confirm the failing request actually targets Alibaba Cloud OSS; CDN back-to-origin cases route to alibabacloud-oss-cdn-origin-config-diagnosis, other products need their own support channel |

### Non-transfer EC codes: route onward, do not absorb

When the error body carries an EC numeric code owned by a sibling skill,
route there instead of diagnosing generically (the entry script attaches
the referral automatically):

| EC code | Owning skill |
| --- | --- |
| 0003-00000005 | alibabacloud-oss-direct-access-link-diagnosis (private-object direct-access link / platform ban) |
| 0003-00000201 | alibabacloud-oss-cross-account-auth-diagnosis (explicit RAM Deny) |
| 0003-00000602 | alibabacloud-oss-browser-upload-cors-diagnosis (CORS rule missing the request Origin/method) |
| 0024-00000008 | alibabacloud-oss-transfer-acceleration-diagnosis (transfer acceleration not enabled) |

> Note on 0024-00000008: first-hand measured behavior, NOT present in the
> official 0024 EC family (officially uncatalogued). The owning skill
> alibabacloud-oss-transfer-acceleration-diagnosis carries the RequestId-level
> probe evidence and the TAC-2 boundary statement; this skill only routes the
> code onward and does not claim it as an official error code.

## Human-escalation wording (verbatim template)

> This request is outside the scope of automated error-code diagnosis
> (DDoS sandbox handling, data recovery, or commercial refunds). I recommend
> opening a human support ticket with your OSS RequestId and the full error
> response body attached, so the backend team can take over.

## Non-error responses (do not diagnose)

- HTTP 304 Not Modified is a successful conditional-cache hit: the client sent
  If-None-Match / If-Modified-Since headers and its local cache is still
  fresh. It is NOT an OSS error and needs no troubleshooting; if the caller
  expected fresh bytes, instruct them to drop or adjust the conditional
  headers (official GetObject conditional-request semantics).

## Behavior when input is insufficient

- If only an HTTP status is available, present the candidate error codes and
  ask for the exact `<Code>` field from the error response body; never
  conclude on status alone.
- If only a RequestId is available, keep asking for the full error response
  body (Code, Message, RequestId) - never fabricate a root cause - and pass
  on the per-client-type recovery paths returned by the entry script in its
  `request_id_guidance` block.
- If the customer wording carries routable symptom phrasing (large-file
  upload breaks, mid-transfer breaks, bucket-domain unreachable), present
  the symptom candidate directions as a degraded list and ask for the error
  body; never conclude on symptom wording alone.
- If nothing recognizable is provided, ask for the full error response body
  (Code, Message, RequestId) before diagnosing.
