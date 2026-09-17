# Scope and Limitations

## In scope

- Parsing a pasted OSS presigned (signed/share) URL locally: V1/V2/V4 form
  detection, expiry extraction, credential-scope validation.
- Routing presigned-URL failures to root-cause directions: expired, clock
  skew beyond +/-15 minutes, V1 signature forbidden, parameter tampering,
  credential rotation/STS expiry, permission change, HTTP method mismatch,
  malformed signature parameters.
- V1→V4 upgrade compatibility checklist and the official V1 retirement policy.
- Share-link recovery guidance (regeneration with correct TTL/method/credential).

## Out of scope (never handle here)

| Topic | Why | Handoff |
| --- | --- | --- |
| Generating a new presigned URL | Requires the owner's credential and is a write of knowledge, not diagnosis | The bucket owner generates it via SDK/console; human support if blocked |
| Signature-algorithm implementation teaching | Out of diagnosis scope; official docs cover it | Point to the official V4 signing documentation |
| Generic upload/download error codes unrelated to presigned URLs | Different diagnosis track | alibabacloud-oss-transfer-error-code-diagnosis |
| Billing questions / commercial refunds | Commercial process | alibabacloud-oss-billing-diagnosis or human support |
| Endpoint / internal-network choice | Different diagnosis track | alibabacloud-oss-endpoint-internal-diagnosis |
| Browser direct-upload form signing (PostObject policy forms) | Not covered by this skill's catalog | Human support ticket |
| Live network probing (fetching/curling the presigned URL) | This skill is knowledge-driven with zero network calls, and probing may expose the link | Guide the user to test the link themselves |
| Server-side log / CanonicalRequest forensics (querying internal request logs, reconstructing the server-side StringToSign) | Server-side evidence is not reachable without cloud APIs, and the server-side canonical string CANNOT be used to infer how the client built the request; the correct method is to compare the client's intermediate signing variables layer by layer | Ask the user to dump the SDK's signing input (endpoint, signed headers, SignedHeaders list, region) and compare locally; human support with the RequestId if backend evidence is required |
| Deleted-data recovery / DDoS sandbox mitigation | Requires platform-side action | Human support ticket |

## Human-escalation wording (verbatim template)

> This request is outside the scope of automated presigned-URL diagnosis. I
> recommend opening a human support ticket with your OSS RequestId and the
> full error response body attached (never include AccessKeys or secrets),
> so the backend team can take over.

## Behavior when input is insufficient

- If only an error code or HTTP status is available, present the candidate
  failure modes in order and ask for the presigned URL itself or the full
  error response body; never conclude on candidates alone.
- If nothing recognizable is provided, ask for the presigned URL and/or the
  full error response body (Code, Message, RequestId) before diagnosing.
