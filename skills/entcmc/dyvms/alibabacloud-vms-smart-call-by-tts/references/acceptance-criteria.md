# Acceptance Criteria: alibabacloud-vms-smart-call-by-tts

**Scenario**: Smart voice notification call (SubmitIntent)
**Purpose**: Skill test acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — Verify the product subcommand exists

> **Note**: `aliyun ... --help` is a help-mode command and DOES NOT accept `--user-agent`. Only business calls (e.g. `aliyun dyvmsapi submit-intent --user-message ...`) carry `--user-agent`.

#### ✅ CORRECT
```bash
aliyun dyvmsapi submit-intent --help
```

#### ❌ INCORRECT
```bash
# Wrong: PascalCase (the plugin uses kebab-case)
aliyun dyvmsapi SubmitIntent --help

# Wrong: misspelled product name
aliyun dyvms submit-intent --help
```

---

## 2. Command — Verify the Action subcommand exists

#### ✅ CORRECT
```bash
aliyun dyvmsapi submit-intent --user-message "Remind Mom I won't be home for dinner tonight" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

#### ❌ INCORRECT
```bash
# Wrong: nonexistent subcommand name
aliyun dyvmsapi intent-submit --user-message "..."
aliyun dyvmsapi smart-call --user-message "..."
```

---

## 3. Parameters — Verify parameter names

#### ✅ CORRECT
```bash
# The only business parameter is --user-message
aliyun dyvmsapi submit-intent --user-message "Call Manager Zhang and let him know the meeting is at 10 AM tomorrow" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

#### ❌ INCORRECT
```bash
# Wrong: parameter-name typos
aliyun dyvmsapi submit-intent --usermessage "..."
aliyun dyvmsapi submit-intent --message "..."
aliyun dyvmsapi submit-intent --user_message "..."

# Wrong: passing parameters that don't apply (CalledNumber belongs to SingleCallByTts, not SubmitIntent)
aliyun dyvmsapi submit-intent --user-message "..." --called-number 13800000001
```

---

## 4. Plugin — Verify the intranet-online plugin install

> **Note**: `aliyun plugin install` is a CLI tooling command and DOES NOT accept `--user-agent`.

#### ✅ CORRECT
```bash
# Install the intranet-online build (the flag is --names, not --name)
aliyun plugin install --names dyvmsapi \
  --version 0.1.0 \
  --source-base https://cli.aliyun-inc.com/registry_id/2/env/online/plugins
```

#### ❌ INCORRECT
```bash
# Wrong: --name instead of --names
aliyun plugin install --name dyvmsapi --version 0.1.0 --source-base ...

# Wrong: installing the public-release build (does not contain submit-intent)
aliyun plugin install --names aliyun-cli-dyvmsapi

# Wrong: missing --source-base (would download the public-release build, no SubmitIntent)
aliyun plugin install --names dyvmsapi --version 0.1.0
```

---

## 5. AI-Mode — Verify enable / disable operations

> **Note**: `aliyun configure ai-mode enable|disable` are CLI system commands and DO NOT accept `--user-agent`. Only BUSINESS calls (e.g. `aliyun dyvmsapi submit-intent --user-message ...`) carry `--user-agent`.

#### ✅ CORRECT
```bash
# Enable (before Skill execution) — system command; no --user-agent
aliyun configure ai-mode enable

# Disable (after Skill execution; required at every exit path) — system command; no --user-agent
aliyun configure ai-mode disable
```

#### ❌ INCORRECT
```bash
# Wrong: ai-mode not disabled at the end of the Skill
aliyun configure ai-mode enable
aliyun dyvmsapi submit-intent --user-message "..." \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
# ← missing disable

# Wrong: --user-agent on a system command (raises `unknown flag: --user-agent`)
aliyun configure ai-mode enable \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

---

## 6. Response — Verify response parsing

#### ✅ CORRECT — successful response
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

Validation points:
- `Code == "OK"` and `Success == true`
- `Model.CallId` non-empty
- `Model.Tag` is semantically consistent with the contact referenced in UserMessage
- **The response does not return the dialed number (no `PhoneNumber` field)**

#### ❌ INCORRECT — false-positive success
```json
{
  "Code": "AiCalleeNotFound",
  "Message": "未能从描述中识别出要通知的对象..."
}
```
This is a business error and must not be treated as success. Prompt the user to check the address-book tag.

---

## 7. Distinguishing from SingleCallByTts

#### ✅ CORRECT — SubmitIntent invocation
```bash
# Only natural-language intent is needed; no number, template ID, or template variables
aliyun dyvmsapi submit-intent --user-message "Tell Lao Wu to bring the contract this afternoon" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

#### ❌ INCORRECT — confusing the two APIs
```bash
# Wrong: passing SingleCallByTts parameters to SubmitIntent
aliyun dyvmsapi submit-intent \
  --called-number 13800000001 \
  --tts-code TTS_331070002 \
  --tts-param '{"code":"8888"}'
```

---

## 8. QueryCallDetailByCallId — CDR Query Acceptance

### 8.1 CLI subcommand name

> **Note**: `aliyun ... --help` is a help-mode command and DOES NOT accept `--user-agent`.

#### ✅ CORRECT
```bash
aliyun dyvmsapi query-call-detail-by-call-id --help
```

#### ❌ INCORRECT
```bash
# Wrong: PascalCase (the plugin uses kebab-case)
aliyun dyvmsapi QueryCallDetailByCallId --help

# Wrong: misspelled hyphenation
aliyun dyvmsapi query-call-detail-by-callid --help
aliyun dyvmsapi querycall-detail-by-call-id --help
```

### 8.2 Required parameter combination

#### ✅ CORRECT
```bash
CALL_ID="1779786101083^9876543210"
QUERY_DATE="${CALL_ID%%^*}"   # Take the front-segment millisecond timestamp from CallId

aliyun dyvmsapi query-call-detail-by-call-id \
  --call-id "$CALL_ID" \
  --prod-id 11000000300006 \
  --query-date "$QUERY_DATE" \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"
```

#### ❌ INCORRECT
```bash
# Wrong: incorrect prod-id; returns Code:OK but no Data
aliyun dyvmsapi query-call-detail-by-call-id \
  --call-id "$CALL_ID" --prod-id 11030000180001 --query-date "$QUERY_DATE"

# Wrong: query-date not on the same day as CallId
aliyun dyvmsapi query-call-detail-by-call-id \
  --call-id "1779786101083^1779786101083" \
  --prod-id 11000000300006 \
  --query-date 1700000000000   # different day from the CallId front segment

# Wrong: missing required parameters
aliyun dyvmsapi query-call-detail-by-call-id --call-id "$CALL_ID"
```

### 8.3 Response parsing

#### ✅ CORRECT — answered successfully
```json
{
  "Code": "OK",
  "Message": "OK",
  "RequestId": "5A17BFE8-D155-5771-BF27-D29099EB997A",
  "Data": "{\"callId\":\"1779786101083^1779786101083\",\"state\":\"200000\",\"stateDesc\":\"用户接听\",\"duration\":4,\"callee\":\"185****8980\",...}"
}
```

Validation points:
- `Data` is a JSON **string**; a second `JSON.parse` is required before reading fields
- `Data.state == "200000"` and `Data.stateDesc == "用户接听"` = answered
- `Data.duration > 0` = a non-zero talk duration occurred

#### ❌ INCORRECT — misjudging scheduling delay as failure
```json
{
  "Code": "OK",
  "Message": "OK",
  "RequestId": "..."
  // Note: no Data field
}
```
Right after the call is initiated, scheduling may not yet have committed (before the call ends, or within ~40s after it ends), so `Data` may be missing. **Do not** mark this as a failure; tell the user to retry shortly (typically queryable ~40s after the call ends; if still empty, retry after another 30–60s).

### 8.4 Number masking

#### ✅ CORRECT — mask the number when presenting to the user
```
👤 Callee        185****8980      # first 3 + **** + last 4
```

#### ❌ INCORRECT — emitting the full number
```
👤 Callee        18546048980      # the full number must not enter the chat context
```

Note: the API itself returns the full number (the account owner viewing their own CDR is expected); however, when the Skill presents it to the user, masking is required.

### 8.5 Readable presentation

#### ✅ CORRECT — three Markdown tables after parsing

**Call Result**

| | |
|---|---|
| ✅ Status | `用户接听` (state=`200000`) |
| 👤 Callee | `185****8980` |
| ⏰ Duration | `4` seconds |

**Timeline**

| | |
|---|---|
| 🔔 Ringing | `2026-05-26 17:01:42` (+`1`s) |
| 📞 Answered | `2026-05-26 17:01:47` (+`5`s after ring) |

#### ❌ INCORRECT — dumping raw JSON
```
Response: {"Code":"OK","Data":"{\"callId\":\"...\",\"state\":\"200000\",...}"}
```
Users cannot read the nested-escaped JSON string — render the readable layout defined in SKILL.md step 4 instead.

#### ❌ INCORRECT — ASCII art with `─────` separators
```
─────────────────────────────────────
✅ Status        用户接听 (state=200000)
👤 Callee        185****8980
─────────────────────────────────────
```
Long horizontal-rule characters get absorbed as `<hr>` by Markdown renderers across chat UIs and IDEs, **reflowing all rows into a single line**. Render real Markdown tables instead.

