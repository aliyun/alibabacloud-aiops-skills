# Verification Methods — Smart Voice Notification

## 1. Verify CLI Plugin Installation

> **Note**: `aliyun ... --help` is a help-mode command and DOES NOT accept `--user-agent`; `aliyun plugin install` is a CLI tooling command and likewise DOES NOT accept `--user-agent`. Only business calls (e.g. `aliyun dyvmsapi submit-intent --user-message ...`) carry `--user-agent`.

```bash
aliyun dyvmsapi submit-intent --help
```

**Expected**: the output contains the command description and the `--user-message` parameter description.

**Failure note**: if the output reports `unknown command: "submit-intent"`, the intranet-online plugin is not installed. Run:

```bash
aliyun plugin install --names dyvmsapi \
  --version 0.1.0 \
  --source-base https://cli.aliyun-inc.com/registry_id/2/env/online/plugins
```

---

## 2. Verify AK Credentials Are Effective

```bash
aliyun configure list
```

**Expected**: the output contains an AK profile in `Valid` status.

---

## 3. Verify the Calling Capability

```bash
aliyun dyvmsapi submit-intent \
  --user-message "<user-provided natural-language intent>" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

**Success criteria**:

```json
{
  "Code": "OK",
  "Success": true,
  "Model": {
    "CallContent": "爸，早点回家啊。",
    "CallId": "1779785134472^9876543210",
    "Tag": "爸爸"
  },
  "RequestId": "56A1AFDB-6945-505A-938A-9B311D64B5C0"
}
```

> For phone-number safety, the response does not return the dialed number.

**Item-by-item check**:

| Check | Condition | Description |
|---|---|---|
| `Code` | equals `"OK"` | request was accepted |
| `Success` | equals `true` | business execution succeeded |
| `Model.CallId` | non-empty | call was initiated; usable for tracking |
| `Model.Tag` | non-empty | a contact in the address book matched successfully |
| `Model.CallContent` | non-empty | the LLM produced playback content |

---

## 4. Common Failure Scenarios

| Code | Reason | Investigation |
|---|---|---|
| `AiCalleeNotFound` | No matching contact in the address book | Verify the tag referenced in UserMessage matches one the user has registered; relay the error to the user |
| `ContactBookEmpty` | Address book is empty | Add contacts in the console |
| `ContentRefused` | Content-safety blocked | Modify UserMessage and remove disallowed content |
| `Throttling` | Rate limit hit | Wait, then retry (1/min, 5/hour, 20/24h per number) |
| `InvalidParameter` | Parameter validation failed | Check whether UserMessage is empty or too long |

---

## 5. (Optional) Verify the Callee Actually Answered

`Code: OK` from `SubmitIntent` only signifies the call was **accepted**. To strictly verify that the callee **answered**, query the CDR API:

```bash
CALL_ID="<the Model.CallId from SubmitIntent's response>"
QUERY_DATE="${CALL_ID%%^*}"

aliyun dyvmsapi query-call-detail-by-call-id \
  --call-id "$CALL_ID" \
  --prod-id 11000000300006 \
  --query-date "$QUERY_DATE" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

**Answered determination** (after a second JSON parse on the `Data` field):

| Check | Condition for a successful answer |
|---|---|
| `Code` | equals `"OK"` |
| `Data` field | present and non-empty (typically queryable ~40s after the call ends; if still empty, retry after another 30–60s) |
| `Data.state` | equals `"200000"` |
| `Data.stateDesc` | equals `"用户接听"` |
| `Data.duration` | greater than `0` |

**Note**: `--prod-id` MUST be `11000000300006` (the Voice Notification product ID); other values return `OK` but yield no `Data`.

**Presentation requirement**: once verified, do not dump the raw `Data` JSON string to the user — render in the readable presentation format defined in SKILL.md step 4 (masked number + status text alongside the code + relative time offsets). The reference document [related-commands.md](./related-commands.md) §2 contains the same recommended format.
