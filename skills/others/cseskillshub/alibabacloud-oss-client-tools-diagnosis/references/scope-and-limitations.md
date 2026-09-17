# Scope and Limitations

## In scope

- Attributing ossbrowser/ossutil login failures: wrong/disabled AccessKey,
  missing stsToken, expired STS, endpoint/region mismatch, clock skew.
- Interpreting permission errors: AccessDenied with the EC decision table
  (0003-00000001 / 0003-00000101 / 0003-00000301) and least-privilege
  mapping, including ossbrowser 2.x bucket-level GetBucketInfo requirement.
- Connectivity troubleshooting guidance: proxy configuration, firewall,
  ossutil timeout/retry options.
- Tool selection and version guidance: ossbrowser 1.x vs 2.x, ossutil 1.x
  vs 2.x differences.
- Outputting the ossutil config template and the least-privilege RAM policy
  template for the user to apply locally.

## Out of scope (never handle here)

| Topic | Why | Handoff |
| --- | --- | --- |
| API/SDK-level transfer error codes (upload/download failures in code) | Different diagnosis track | alibabacloud-oss-transfer-error-code-diagnosis |
| Endpoint address selection strategy (internal vs public, traffic cost) | Different diagnosis track | alibabacloud-oss-endpoint-internal-diagnosis |
| Presigned URL generation / V4 URL signing deep dive | Different diagnosis track | alibabacloud-oss-presigned-url-v4-diagnosis |
| Billing disputes / cost spikes | Commercial process | alibabacloud-oss-billing-diagnosis or human support |
| Deleted-data recovery | Needs backend restore workflow | Human support ticket |
| Executing ossutil/ossbrowser commands for the user | This skill never runs client commands | Output the command; the user runs it locally |
| Live network probing (ping/TCP tests against OSS) | This skill is knowledge-driven with zero network calls | Guide the user to run local checks themselves |

## Human-escalation wording (verbatim template)

> This request is outside the scope of automated client-tool diagnosis
> (data recovery, billing disputes, or platform-side security policy
> handling). I recommend opening a human support ticket with the complete
> error message (including the EC code and RequestId if present) and your
> tool name/version attached, so the backend team can take over.

## Behavior when input is insufficient

- If only the tool name is available, present the common-issue candidate
  list for that tool and ask for the exact error message.
- If nothing recognizable is provided, ask for the tool (with version) and
  the complete error message including any EC code before diagnosing.
