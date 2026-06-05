# SMS Send-Status Error Codes

> Reference for the per-message `ErrorCode` field returned by
> `aliyun dysmsapi query-send-details`. Two layers of codes are combined:
>
> 1. **Alibaba platform codes** (`isv.*` / `isp.*`) — surfaced by Alibaba pre-checks
>    or the SMS gateway before the message is handed off to the carrier.
> 2. **Carrier receipts** (`DELIVERED`, `MOBILE_NOT_ON_SERVICE`, …) — async
>    delivery receipts pushed back by domestic carriers (China Mobile / Unicom /
>    Telecom). Receipt arrival typically takes 10–30 s; absence is common when
>    `SendStatus = 1` (sent) but not yet `SendStatus = 3` (delivered).
>
> Upstream source:
> [Domestic SMS delivery-receipt error codes (101347)](https://help.aliyun.com/document_detail/101347.html).

---

## How to read `query-send-details` output

`query-send-details` returns `SmsSendDetailDTOs[]`, where each entry carries:

| Field           | Meaning                                                           |
| --------------- | ----------------------------------------------------------------- |
| `PhoneNum`      | Recipient mobile number                                           |
| `SendStatus`    | `1` = sent (in flight), `2` = failed, `3` = delivered (success)   |
| `ErrCode`       | The error code documented in this file (only meaningful when `SendStatus != 3`) |
| `Content`       | Rendered SMS body                                                 |
| `SendDate`      | Submission time (`yyyy-MM-dd HH:mm:ss`)                           |
| `ReceiveDate`   | Receipt time from carrier (empty when no receipt yet)             |
| `OutId`         | External tracking ID, if you supplied `--out-id` on send          |

**Important — empty `ErrCode` semantics**:

- `SendStatus = 1` + empty `ErrCode` → in flight, retry the query later (carrier receipt not arrived yet).
- `SendStatus = 2` + non-empty `ErrCode` → failure, look up the code below.
- `SendStatus = 3` + `ErrCode = DELIVERED` (or empty) → success.

---

## Section 1 — Alibaba platform codes (`isv.*` / `isp.*`)

Returned synchronously at send time **and** echoed in the receipt. Most can also
appear as the response `Code` of `SendSms` / `SendBatchSms` (see SKILL.md
`Error Handling`).

### 1.1 Account & service-level

| Code                          | Message                              | Cause / Resolution                                                                 |
| ----------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------- |
| `isv.ACCOUNT_NOT_EXISTS`      | Account not found                    | Wrong account or AccessKey. Confirm credentials.                                   |
| `isv.ACCOUNT_ABNORMAL`        | Account abnormal                     | Billing query exception. Open a ticket via the SMS DingTalk group.                 |
| `isv.OUT_OF_SERVICE`          | Business stopped (insufficient balance) | Top up the SMS quota.                                                           |
| `isv.PRODUCT_UN_SUBSCRIPT`    | Cloud-communication product not enabled | Activate the SMS service for the AccessKey owner account.                       |
| `isv.PRODUCT_UNSUBSCRIBE`     | Specific product not subscribed      | The AccessKey has not enabled the API's product (e.g. voice). Subscribe first.     |
| `isp.RAM_PERMISSION_DENY`     | Insufficient RAM permission          | Grant `AliyunDysmsFullAccess` (or scoped) to the RAM user.                         |
| `isp.SYSTEM_ERROR`            | System error                         | Transient — retry; if persistent, open a support ticket.                           |

### 1.2 Signature / template / content

| Code                                   | Message                                              | Cause / Resolution                                                              |
| -------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------- |
| `isv.SMS_SIGN_NAME_ILLEGAL`            | Signature missing or unapproved                      | Verify the signature is approved (`SignStatus=1`).                              |
| `isv.SMS_SIGNATURE_ILLEGAL`            | No matching signature under this account             | Check that AK and signature belong to the same account; remove garbled chars.   |
| `isv.SMS_SIGN_ILLEGAL`                 | Signature forbidden                                  | Apply a compliant signature in the console.                                     |
| `isv.SIGN_STATE_ILLEGAL`               | Signature state is "unavailable"                     | Inspect signature detail, fix the unavailability reason and re-submit.          |
| `isv.SMS_SIGNATURE_SCENE_ILLEGAL`      | Signature/template scene mismatch                    | Verification-code signatures can only send verification-code templates.         |
| `isv.SMS_TEMPLATE_ILLEGAL`             | Template missing, unapproved, or vars don't match    | Check the template is approved and `--template-param` keys match the placeholders. |
| `isv.TEMPLATE_MISSING_PARAMETERS`      | Template variables not all assigned                  | Fill every `${...}` placeholder in `--template-param`.                          |
| `isv.SMS_CONTENT_ILLEGAL`              | SMS content contains forbidden words                 | Revise per the template content guidelines.                                     |
| `isv.INVALID_PARAMETERS`               | Parameter format invalid                             | E.g. `SendDate` must be `yyyyMMdd` (`20260326`, not `2026-03-26`).              |
| `isv.INVALID_JSON_PARAM`               | Parameter is not valid JSON                          | Use proper JSON: `{"code":"123"}`.                                              |
| `isv.EXTEND_CODE_ERROR`                | Extension code reuse across signatures               | Use distinct extension codes per signature.                                     |

### 1.3 Recipient / quota / control

| Code                                    | Message                                            | Cause / Resolution                                                              |
| --------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------- |
| `isv.MOBILE_NUMBER_ILLEGAL`             | Phone number format error                          | Use `+86` / `0086` / `86` / bare 11-digit for domestic; international = country-code + number. |
| `isv.MOBILE_COUNT_OVER_LIMIT`           | Too many recipients in one call                    | `SendSms` ≤ 1000; `SendBatchSms` ≤ 100.                                         |
| `isv.BUSINESS_LIMIT_CONTROL`            | Cloud-communication flow-control hit               | Per-recipient frequency cap. Lower send rate or adjust threshold in the console. |
| `isv.DAY_LIMIT_CONTROL`                 | Daily quota reached                                | Raise daily threshold in console **General Settings → Domestic SMS → Security**. |
| `isv.MONTH_LIMIT_CONTROL`               | Monthly quota reached                              | Same as above (monthly).                                                        |
| `isv.BLACK_KEY_CONTROL_LIMIT`           | Number is on the blacklist                         | User opted out / complained via 12321; remove from your audience.               |
| `isv.DENY_IP_RANGE`                     | Source IP region blocked                           | Calls from non-mainland IPs cannot send domestic SMS.                           |
| `isv.DOMESTIC_NUMBER_NOT_SUPPORTED`     | Intl/HK-MO-TW template can't send to mainland     | Use a domestic-message template for mainland numbers.                           |

---

## Section 2 — Carrier delivery error codes

Pushed asynchronously by the carrier after the message reaches the destination
(or fails to). They populate `ErrCode` only after `SendStatus` transitions to
`2` (failed) or `3` (delivered).

### 2.1 Success

| Code        | Meaning                                                                    |
| ----------- | -------------------------------------------------------------------------- |
| `DELIVERED` | Carrier confirmed handset reception. Equivalent to `SendStatus = 3`.       |

### 2.2 Recipient-side failures

| Code                          | Meaning                                                          | Suggested handling                                          |
| ----------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------- |
| `MOBILE_NOT_ON_SERVICE`       | Number is suspended / out of service / shut down                 | Stop sending; flag the number invalid in CRM.               |
| `MOBILE_SEND_LIMIT`           | Recipient hit the per-day per-number receive limit               | Defer; do not retry within 24h.                             |
| `MOBILE_ACCOUNT_ABNORMAL`     | Carrier account abnormal (arrears, deregistered, …)              | Mark inactive; manual confirmation needed.                  |
| `MOBILE_IN_BLACK`             | Number is on the carrier blacklist                               | Remove from audience permanently.                            |
| `MOBILE_TERMINAL_ERROR`       | Handset off / out of coverage / not yet activated                | Retry once after several hours.                             |
| `USER_REJECT`                 | User explicitly refused / has opted-out                          | Do not retry; honor the opt-out.                            |
| `INVALID_NUMBER`              | Number does not exist on carrier registry                        | Same as `MOBILE_NOT_ON_SERVICE`.                            |

### 2.3 Content / route-side failures

| Code                          | Meaning                                                          | Suggested handling                                          |
| ----------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------- |
| `CONTENT_KEYWORD`             | Carrier content audit hit a forbidden keyword                    | Revise the template; resubmit for approval.                 |
| `CONTENT_ERROR`               | Marketing SMS missing opt-out instruction                        | Append a regulation-compliant unsubscribe tail (e.g. `STOP` / reply-T-to-opt-out). |
| `EXPIRED`                     | Submission expired in carrier queue                              | Resend with fresh content.                                  |
| `NO_ROUTE`                    | No usable route to recipient (rare)                              | Open a ticket with cloud-communication support.             |
| `SP_NOT_BY_INTER_SMS`         | International sending not supported on this signature/template   | Switch to an int'l-enabled signature/template.              |
| `SP_UNKNOWN_ERROR`            | Carrier returned an opaque error                                 | Retry once; persist failures → ticket.                      |
| `REQUEST_SUCCESS`             | Carrier accepted but final receipt not yet received              | Treat as in-flight; query again later.                      |

> The carrier code list above is non-exhaustive — carriers may add or rename
> codes without notice. Treat unknown values as transient unless they repeat
> across many recipients within a short window (then open a ticket).

---

## Section 3 — Triage workflow

Use this decision tree when investigating a failed message:

1. **Read `SendStatus` first**:
   - `1` (in flight) → wait 30 s and re-query; do **not** retry sending yet.
   - `3` (delivered) → success path; ignore `ErrCode`.
   - `2` (failed) → continue below.

2. **Inspect `ErrCode` prefix**:
   - `isv.*` / `isp.*` → look up Section 1.
     - Account / signature / template issues → fix in console; do **not**
       retry the same payload until the root cause clears.
     - Throttling (`BUSINESS_LIMIT_CONTROL` / `*_LIMIT_CONTROL`) → exponential
       back-off retry, or raise the threshold in console.
   - Otherwise carrier code → look up Section 2.
     - Recipient-side failures → mark recipient invalid; do not retry blindly.
     - Content / route-side failures → fix content; resend after re-approval.

3. **No `ErrCode` but `SendStatus = 2`** is rare and indicates an internal
   gateway issue — open a ticket with the `BizId` and `RequestId`.

4. **Aggregate analysis**: if a single date's `RespondedFailCount` is unusually
   high, run `query-send-statistics` (per signature) to confirm it is not
   isolated to one signature/template, then sample 20 failed `BizId`s via
   `query-send-details` to identify the dominant `ErrCode`.

---

## Section 4 — Example: enrich a failed delivery report

```bash
# 1) For a known phone + date, list per-message details
aliyun dysmsapi query-send-details \
  --api-version 2017-05-25 \
  --phone-number "13800138000" --send-date "20260326" \
  --page-size 50 --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

Parse `SmsSendDetailDTOs[]` and group by `ErrCode`:

```python
from collections import Counter
import json, sys
data = json.load(sys.stdin)["SmsSendDetailDTOs"]["SmsSendDetailDTO"]
codes = Counter((d["SendStatus"], d.get("ErrCode") or "") for d in data)
for k, v in sorted(codes.items(), key=lambda x: -x[1]):
    print(f"status={k[0]} code={k[1]:<35s} count={v}")
```

Cross-reference each `ErrCode` against Section 1/2 above to choose the right
remediation (fix template, revise audience, raise quota, …).

---

## References

- [Domestic SMS delivery-receipt error codes (101347)](https://help.aliyun.com/document_detail/101347.html)
- [SMS service error codes (101346)](https://help.aliyun.com/document_detail/101346.html)
- [QuerySendDetails API](https://help.aliyun.com/document_detail/419277.html)
- Local: [`SKILL.md`](../SKILL.md) — `## Error Handling` section; RAM action list is referenced from there.
