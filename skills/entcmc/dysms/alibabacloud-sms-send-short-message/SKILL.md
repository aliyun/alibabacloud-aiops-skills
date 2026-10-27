---
name: alibabacloud-sms-send-short-message
description: >
  Send short messages (SMS) to specified phone numbers via Alibaba Cloud Short Message Service.
  Supports verification codes, notification messages, and marketing messages.
  Use this Skill whenever the user wants to send SMS verification codes, system notifications,
  order reminders, or marketing campaigns. Supports single send (SendSms, up to 1000 phone
  numbers sharing the same signature and template parameters) and batch send (SendBatchSms,
  up to 100 phone numbers, each with its own signature and template parameters). The
  signature and template approval status can be verified before sending to maximize
  delivery success rate. For brand-new accounts that do not yet have any approved
  signature or template, a built-in test verification SMS (SendTestVerification) can be
  sent to a single phone number to validate that the service works — no signature or
  template required.
license: Apache-2.0
compatibility: >
  aliyun-cli >= 3.3.3
  dysmsapi plugin (auto-installed)
  Requires Alibaba Cloud AccessKey configured via `aliyun configure`
metadata:
  domain: cloud-communication
  owner: sms-team
  contact: sms-team@alibaba-inc.com
  implementation: aliyun-cli
  ram_policies: references/ram-policies.md
---

## Critical CLI Compliance (Must Read First)

The following declarations apply to **every** `aliyun` CLI invocation in this Skill —
they must be honored before any send / query operation, workflow step, or functional
scenario described later in this document.

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See `references/cli-installation-guide.md` for full installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If the file is missing, invalid, or the field is absent/empty/not a string, STOP and report the error. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. When switching skills or returning to this skill, reread this skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag below to every actual execution, including commands generated or extended at runtime; do not repeat UA boilerplate in every example block.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message/{session-id} skill-version/{skill-version}"
```

The entire UA value MUST be double-quoted because it contains a space. Do not skip, alter, or omit it on any `aliyun` API command.

**Script / Terraform execution:** Inject both scoped values inline:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/deploy.py

# Terraform
TF_VAR_session_id={session-id} TF_VAR_skill_version={skill-version} terraform apply
# provider: configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message/${var.session_id} skill-version/${var.skill_version}"
```

Scripts and Terraform configs MUST require both values and construct the same UA product.
Generated Terraform providers MUST set `configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message/${var.session_id} skill-version/${var.skill_version}"`.

The wrapper script `scripts/send_sms.sh` requires both values in its environment:

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} ./scripts/send_sms.sh send -p "..." -s "..." -t "..."
```

---

## Overview

This Skill wraps the Alibaba Cloud Short Message Service (SMS) end-to-end on top of the
**aliyun CLI**, exposing the following capabilities:

- **Send SMS**: verification codes, notifications, or marketing messages (SendSms).
- **Batch send**: different signatures / template params per phone number (SendBatchSms).
- **Signature management**: query approval status and signature lists.
- **Template management**: query approval status and template lists.
- **Send status query**: query SMS send details and delivery receipts.
- **Send statistics query**: aggregated send / success / fail counts in a date range
  (QuerySendStatistics).
- **SMS qualification query**: list records (QuerySmsQualificationRecord) and
  single-record detail (QuerySingleSmsQualification) — see
  [`references/sms-qualification.md`](references/sms-qualification.md).
- **Send test SMS**: for accounts that have no approved signature or template yet, send a
  built-in test verification code SMS to a single phone number (SendTestVerification). No
  signature or template is required — useful for validating the service before submitting
  a signature/template for approval.

## Interactive Parameter Confirmation (Must Read)

Before executing any send-class operation (`send-sms` / `send-batch-sms`), this Skill
**must** collect these critical parameters first: `--sign-name`, `--template-code`,
`--template-param` (when the template contains placeholders), and
`--phone-numbers` / `--phone-number-json`.

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, signature/template names, phone
> numbers, template variables, etc.) MUST be confirmed with the user. Do NOT assume or
> use default values without explicit user approval.

### Handling Rules

When the user does not explicitly provide the **signature** or **template**, the AI
agent **must not guess or fabricate them**. Instead it should:

1. **Ask the user proactively**: "Which signature/template should I use? If unsure, I can
   list approved ones from your account for you to pick from."
2. **After the user agrees, call list APIs**:
   - `aliyun dysmsapi query-sms-sign-list ...` then `aliyun dysmsapi get-sms-sign --sign-name <name>` per candidate.
   - `aliyun dysmsapi query-sms-template-list ...`
   - **Hard filter**: keep only signs with `SignStatus = 1` (approved) and templates with `TemplateStatus = 1`. **Do NOT drop signs based on carrier registration alone** — unregistered carriers may still deliver. Instead, surface `SignIspRegisterDetailList[*].RegisterResult` (per-carrier registration status) as an extra column in the candidate table and let the user decide. Columns: index / code / name / content / `SignStatus` / per-carrier registration.
3. **Resolve template variables**: If the picked template contains `${xxx}` placeholders,
   ask for each variable's value one by one and assemble them into `--template-param` JSON.
4. **Phone numbers**: Always require explicit phone numbers from the user; never reuse
   placeholder numbers like `13800138000` from this document as the actual recipient.
5. **Final confirmation**: Once all critical parameters are collected, **restate the
   complete send plan and only call `send-sms` / `send-batch-sms` after the user gives an
   explicit confirmation (e.g. "confirm" / "send")**.

### Quick Recovery When Signature / Template Is Invalid

If `send-sms` returns `isv.SMS_SIGN_NAME_ILLEGAL` / `isv.SMS_TEMPLATE_ILLEGAL`, the agent
should proactively offer to "list existing signatures and templates" and, after the user
agrees, call the list APIs instead of retrying blindly.

### When the Account Has No Signature or Template (Test Verification)

When the user asks to send an SMS but the account has **no approved signature AND no
approved template** (e.g. a brand-new account, or `query-sms-sign-list` /
`query-sms-template-list` return no approved entries), the agent **must not** attempt
`send-sms` / `send-batch-sms` (they would fail with `isv.SMS_SIGN_NAME_ILLEGAL` /
`isv.SMS_TEMPLATE_ILLEGAL`). Instead:

1. **Explain the situation**: sending a normal SMS requires an approved signature and
   template, which they don't have yet.
2. **Offer the built-in test SMS**: propose `send-test-verification`, which uses Alibaba
   Cloud's built-in test signature/template and needs only a phone number.
3. **Ask for the phone number**: prompt the user to input the recipient `--phone` (a single
   number). Never reuse the placeholder `13800138000` from this document as the real
   recipient.
4. **Confirm and send**: after the user provides the number and confirms, call
   `aliyun dysmsapi send-test-verification --phone <number> --api-version 2017-05-25`.
5. **Guide next steps**: remind the user to create and get approved a signature and template
   in the console so they can send production SMS afterwards.

## Prerequisites

1. **Install aliyun CLI (>= 3.3.3)** — see `references/cli-installation-guide.md`.
2. **Install the dysmsapi plugin**: `aliyun plugin install --names dysmsapi`.
3. **Configure credentials** — use the CLI **default credential chain** (priority: env vars
   → `~/.aliyun/config.json` → ECS RAM role → OIDC Token). Verify with `aliyun configure get`.

   ```bash
   export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
   export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
   export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
   ```

   > **Important**: Never hard-code AK/SK in code or commands. On ECS use a RAM role; in K8s use OIDC.
4. **Activate the SMS service** in the [SMS Console](https://dysms.console.aliyun.com/) and
   create an **approved** signature and template. Without them, only
   `send-test-verification` (test SMS) can be used.

## Usage

### Calling aliyun CLI directly

**Send SMS** (see Examples for bulk / per-recipient variants):
```bash
aliyun dysmsapi send-sms --api-version 2017-05-25 \
  --phone-numbers "13800138000" --sign-name "AliyunDemo" --template-code "SMS_123456" \
  --template-param '{"code":"123456"}' --read-timeout 3

# Batch send: per-phone signature / template params (<= 100 numbers)
aliyun dysmsapi send-batch-sms --api-version 2017-05-25 \
  --phone-number-json '["13800138000","13900139000"]' --sign-name-json '["SignA","SignB"]' \
  --template-code "SMS_123456" \
  --template-param-json '[{"code":"111111"},{"code":"222222"}]' --read-timeout 3

# Test SMS: no signature/template needed, single phone only
aliyun dysmsapi send-test-verification --api-version 2017-05-25 --phone "13800138000" --read-timeout 3
```

**Query lists / status / details**:
```bash
# Approved signatures / templates (use to populate user choices)
aliyun dysmsapi query-sms-sign-list      --api-version 2017-05-25 --page-index 1 --page-size 50 --read-timeout 3
aliyun dysmsapi query-sms-template-list  --api-version 2017-05-25 --page-index 1 --page-size 50 --read-timeout 3

# Single signature / template lookup
aliyun dysmsapi get-sms-sign     --api-version 2017-05-25 --sign-name "AliyunDemo"     --read-timeout 3
aliyun dysmsapi get-sms-template --api-version 2017-05-25 --template-code "SMS_123456" --read-timeout 3

# Per-message delivery details (use BizId for precise lookup)
aliyun dysmsapi query-send-details --api-version 2017-05-25 \
  --phone-number "13800138000" --send-date "20260326" \
  --page-size 10 --current-page 1 --read-timeout 3

# Aggregated statistics (--is-globe: 1=domestic, 2=intl/HK-Macao-Taiwan).
# Optional filters: --sign-name "AliyunDemo" --template-type 0
aliyun dysmsapi query-send-statistics --api-version 2017-05-25 --is-globe 1 \
  --start-date "20260301" --end-date "20260326" --page-index 1 --page-size 10 --read-timeout 3

# SMS qualification — list records / single detail by GroupId
aliyun dysmsapi query-sms-qualification-record --api-version 2017-05-25 --page-no 1 --page-size 20 --read-timeout 3
aliyun dysmsapi query-single-sms-qualification --api-version 2017-05-25 --qualification-group-id 10000123 --read-timeout 3
```

> Full filter parameters, response schemas, and state enum mapping for the
> qualification APIs are documented in
> [`references/sms-qualification.md`](references/sms-qualification.md).

### Using the wrapper script

`scripts/send_sms.sh` automatically applies `--api-version`, `--read-timeout`, and the
versioned `--user-agent`. It requires `SKILL_SESSION_ID` and `SKILL_VERSION` in the
environment (see Observability); export them once per session:

```bash
export SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version}

# Send (single or comma-separated phones); add --verify to pre-check sign/template
./scripts/send_sms.sh send -p "13800138000" -s "AliyunDemo" -t "SMS_123456" -tp '{"code":"123456"}'

# Send a test verification SMS (no signature/template needed)
./scripts/send_sms.sh send-test -p "13800138000"

# List & inspect
./scripts/send_sms.sh list-signs
./scripts/send_sms.sh list-templates
./scripts/send_sms.sh query-sign     --sign-name "AliyunDemo"
./scripts/send_sms.sh query-template --template-code "SMS_123456"

# Status & statistics (--is-globe / --sign-name / --template-type are optional filters)
./scripts/send_sms.sh query-status     -p "13800138000" --send-date "20260326" --biz-id "xxx^0"
./scripts/send_sms.sh query-statistics --start-date "20260301" --end-date "20260326"
```

## Parameters

### aliyun dysmsapi send-sms

| Parameter         | Required | Description                                              |
| ----------------- | -------- | -------------------------------------------------------- |
| --api-version     | Yes      | API version, fixed to `2017-05-25`                       |
| --phone-numbers   | Yes      | Phone numbers, comma-separated, up to 1000               |
| --sign-name       | Yes      | SMS signature name                                       |
| --template-code   | Yes      | SMS template code                                        |
| --template-param  | No       | Template variables JSON, e.g. `'{"code":"123456"}'`      |
| --out-id          | No       | External tracking ID                                     |
| --read-timeout    | Yes      | Read timeout in seconds, recommended value `3`           |

### aliyun dysmsapi send-batch-sms (batch send)

| Parameter                  | Required | Description                                                                  |
| -------------------------- | -------- | ---------------------------------------------------------------------------- |
| --api-version              | Yes      | API version, fixed to `2017-05-25`                                           |
| --phone-number-json        | Yes      | Phone numbers JSON array, up to 100, e.g. `'["138xxx","139xxx"]'`            |
| --sign-name-json           | Yes      | Signature names JSON array, must match the phone count                       |
| --template-code            | Yes      | Template code (all phones share the same template)                           |
| --template-param-json      | No       | Template variables JSON array, must match the phone count                    |
| --sms-up-extend-code-json  | No       | Upstream SMS extension codes JSON array                                      |
| --out-id                   | No       | External tracking ID, less than 256 characters                               |
| --read-timeout             | Yes      | Read timeout in seconds, recommended value `3`                               |

> **SendSms vs SendBatchSms**: `send-sms` shares one signature/template across up to 1000
> numbers; `send-batch-sms` lets each phone use a different signature/template params (up
> to 100 numbers).

### aliyun dysmsapi send-test-verification (test SMS, no signature/template)

| Parameter         | Required | Description                                                              |
| ----------------- | -------- | ------------------------------------------------------------------------ |
| --api-version     | Yes      | API version, fixed to `2017-05-25`                                       |
| --phone           | Yes      | A single recipient phone number, e.g. `13800138000`                      |
| --read-timeout    | Yes      | Read timeout in seconds, recommended value `3`                           |

> **When to use**: only for accounts that have no approved signature/template yet. It uses
> Alibaba Cloud's built-in test signature and template, is free of charge, and sends a fixed
> test verification code to a single number. It is NOT a substitute for `send-sms` in
> production — create and get an approved signature/template for real business SMS.

### aliyun dysmsapi query-send-statistics

| Parameter         | Required | Description                                                                          |
| ----------------- | -------- | ------------------------------------------------------------------------------------ |
| --api-version     | Yes      | API version, fixed to `2017-05-25`                                                   |
| --is-globe        | Yes      | Scope: `1` = domestic; `2` = international / HK-Macao-Taiwan                         |
| --start-date      | Yes      | Start date in `yyyyMMdd`                                                             |
| --end-date        | Yes      | End date in `yyyyMMdd`                                                               |
| --page-index      | Yes      | Current page, starts from 1                                                          |
| --page-size       | Yes      | Page size, 1~50                                                                      |
| --template-type   | No       | `0`=verify code, `1`=notification, `2`=marketing(corp), `3`=intl/HK-Macao-Taiwan(corp), `7`=digital |
| --sign-name       | No       | Filter by signature name                                                             |
| --read-timeout    | Yes      | Read timeout in seconds, recommended value `3`                                       |

> **Response**: returns `Data.TargetList[]` (each entry has `SendDate`, `TotalCount`,
> `RespondedSuccessCount`, `RespondedFailCount`, `NoRespondedCount`) and `Data.TotalSize`.

### Wrapper script options

| Option            | Short | Description                                |
| ----------------- | ----- | ------------------------------------------ |
| --phone-numbers   | -p    | Phone numbers                              |
| --sign-name       | -s    | Signature name                             |
| --template-code   | -t    | Template code                              |
| --template-param  | -tp   | Template variables (JSON)                  |
| --out-id          | -o    | External tracking ID                       |
| --verify          | —     | Verify signature/template before sending   |
| --region          | -r    | Region ID, defaults to `cn-hangzhou`       |
| --profile         | —     | Use the given aliyun CLI profile           |

## Output

### Successful send response

```json
{
  "BizId": "114814474505895421^0",
  "Code": "OK",
  "Message": "OK",
  "RequestId": "4C3D8B1B-B3D8-5673-B724-1F251799CE9A"
}
```

### Approval status reference

| Value | SignStatus / TemplateStatus | Description                          |
| ----- | --------------------------- | ------------------------------------ |
| 0     | Reviewing                   | SMS cannot be sent for now           |
| 1     | Approved                    | Available for sending                |
| 2     | Rejected                    | Needs revision and resubmission      |
| 10    | Cancelled                   | Sign/template has been cancelled     |

## Error Handling

### Common business error codes

| Error code                       | Description                          | Suggested action                              |
| -------------------------------- | ------------------------------------ | --------------------------------------------- |
| isv.SMS_SIGNATURE_SCENE_ILLEGAL  | Signature/template scene mismatch    | Make sure signature and template scenes align |
| isv.SMS_TEMPLATE_ILLEGAL         | Template missing or unapproved       | Verify the template has been approved         |
| isv.SMS_SIGN_NAME_ILLEGAL        | Signature missing or unapproved      | Verify the signature has been approved        |
| isv.MOBILE_NUMBER_ILLEGAL        | Bad phone number format              | Check the number format                       |
| isv.AMOUNT_NOT_ENOUGH            | Insufficient account balance         | Top up the SMS quota                          |
| isv.BUSINESS_LIMIT_CONTROL       | Throttling triggered                 | Reduce the send rate                          |
| SignatureNotFound                | Signature not found                  | Create the signature in the console           |
| TemplateNotFound                 | Template not found                   | Create the template in the console            |

> `query-send-details` `ErrCode` = Alibaba `isv.*`/`isp.*` (above) + carrier receipts (`DELIVERED`, `MOBILE_NOT_ON_SERVICE`, `MOBILE_SEND_LIMIT`, …). Full table + triage: [`references/sms-error-codes.md`](references/sms-error-codes.md).

### CLI configuration errors

| Error message                | Cause                | Resolution                                     |
| ---------------------------- | -------------------- | ---------------------------------------------- |
| InvalidAccessKeyId.NotFound  | Wrong AccessKey ID   | Check the AccessKey ID                         |
| SignatureDoesNotMatch        | Wrong Secret         | Check the AccessKey Secret                     |
| Forbidden.RAM                | Insufficient permission | Verify the RAM user has SMS permissions     |

## Execution Flow

1. **Pre-check**: aliyun CLI installed (>= 3.3.3) and dysmsapi plugin available;
   credentials configured; `{skill-version}` read from `references/manifest.json` and a
   fresh `{session-id}` generated (see Observability).
2. **Validate required parameters** (`phone-numbers`, `sign-name`, `template-code`).
   If signature or template is missing, ask the user; after consent call
   `query-sms-sign-list` / `query-sms-template-list` and present approved candidates.
   If the account has **no approved signature AND no approved template** at all, do not
   call `send-sms`; instead offer the test verification SMS (step 5a).
3. **[Optional, --verify]** Verify sign via `get-sms-sign`: require `SignStatus=1`; also surface `SignIspRegisterDetailList[*].RegisterResult` to the user as info (unregistered carriers may still deliver — do not block).
4. **[Optional, --verify]** Verify template status via `get-sms-template` (`TemplateStatus=1`).
5. **Send** via `aliyun dysmsapi send-sms` (or `send-batch-sms` for per-recipient
   personalization).
5a. **[No signature/template] Send test SMS**: when the account has no approved
   signature/template, ask the user for a single `--phone` and (after confirmation) call
   `aliyun dysmsapi send-test-verification --phone <number>`. Then guide the user to create
   and get approved a signature/template for production sending.
6. **Return result**: `Code=OK` only confirms gateway acceptance — return `BizId`. To report final delivery to the user, always call `query-send-details` (Scenario 3); never use the send response as proof of delivery.

## Examples

### Scenario 1: Send a verification code (or bulk-send with the same signature/params)

```bash
# 1) Pull approved signatures & templates first (so the user can pick)
aliyun dysmsapi query-sms-sign-list     --api-version 2017-05-25 --page-index 1 --page-size 50 --read-timeout 3
aliyun dysmsapi query-sms-template-list --api-version 2017-05-25 --page-index 1 --page-size 50 --read-timeout 3

# 2) Send (after user confirmation). For bulk, comma-separate up to 1000 numbers in
#    --phone-numbers; all of them share this signature and these template params.
aliyun dysmsapi send-sms --api-version 2017-05-25 \
  --phone-numbers "13800138000" --sign-name "YourSign" --template-code "SMS_xxx" \
  --template-param '{"code":"123456"}' --read-timeout 3
```

### Scenario 2: Batch send with per-recipient personalization

```bash
aliyun dysmsapi send-batch-sms --api-version 2017-05-25 \
  --phone-number-json '["13800138000","13900139000"]' \
  --sign-name-json    '["BrandA","BrandB"]' \
  --template-code "SMS_xxx" \
  --template-param-json '[{"code":"111111"},{"code":"222222"}]' --read-timeout 3
```

> Lengths of `--phone-number-json`, `--sign-name-json`, and `--template-param-json` must
> match and correspond one-to-one.

### Scenario 3: Verify delivery & aggregate statistics

```bash
# Per-message delivery (uses BizId returned by send-sms)
aliyun dysmsapi query-send-details --api-version 2017-05-25 \
  --phone-number "13800138000" --send-date "20260326" --biz-id "xxx^0" \
  --page-size 10 --current-page 1 --read-timeout 3

# Range-based aggregated statistics (1 row per send-day)
aliyun dysmsapi query-send-statistics --api-version 2017-05-25 --is-globe 1 \
  --start-date "20260301" --end-date "20260326" --page-index 1 --page-size 10 --read-timeout 3
```

> `send-sms` / `send-batch-sms` responses only confirm gateway acceptance (`Code=OK` + `BizId`); they are NOT proof of delivery. Whenever the user asks "did it arrive?" / "was it delivered?", always call `query-send-details` (use `BizId` for precise lookup) and surface `SendStatus` (1=in-flight, 2=failed, 3=delivered) and `ErrCode` — never reply based on the send-API response alone.

### Scenario 4: Send a test SMS when there is no signature/template

For a brand-new account with no approved signature/template, ask the user for a single
phone number, then send the built-in test verification SMS:

```bash
aliyun dysmsapi send-test-verification --api-version 2017-05-25 --phone "13800138000" --read-timeout 3
```

> A successful response returns `Code=OK` / `Success=true`. Afterwards, guide the user to
> create and get approved a signature and template in the console so they can use
> `send-sms` for real business SMS.

## Multi-Environment / Multi-Account

aliyun CLI supports multiple profiles. Prefer env vars or RAM roles for credentials; use
profiles for region selection only:

```bash
aliyun configure set --profile prod --region cn-hangzhou
aliyun dysmsapi send-sms --profile prod --api-version 2017-05-25 \
  --phone-numbers "13800138000" --sign-name "Sign" --template-code "SMS_xxx" --read-timeout 3
```

## Notes

1. **Plugin install**: First-time use requires `aliyun plugin install --names dysmsapi`.
2. **API version**: When calling the CLI directly, `--api-version 2017-05-25` is mandatory.
3. **Parameter format**: kebab-case (e.g. `--phone-numbers`, not `--PhoneNumbers`).
4. **Timeout**: `--read-timeout 3` is required. After a timeout, query the delivery
   receipt before deciding whether to retry.
5. **User-Agent**: every API command must carry the versioned `--user-agent` described in
   the Observability section — never a hardcoded or session-less value.
6. **Idempotency**: SendSms/SendBatchSms are NOT idempotent — prevent duplicate sends at
   the business layer.
7. **Single vs batch**: Prefer `send-sms` for verification codes; `send-batch-sms` is only
   needed when each recipient requires different signature or template params (≤ 100).
8. **Billing**: Billing depends on carrier delivery; API success but carrier failure is
   not billed. QPS limit is 5000/s per user. `send-test-verification` is free.
9. **Credential safety**: Never hard-code AK/SK; always rely on the default credential
   chain (env vars / `~/.aliyun/config.json` / ECS RAM role / OIDC).
10. **Parameter confirmation**: Never guess signature/template — always ask the user, and
    after consent fetch `query-sms-sign-list` / `query-sms-template-list` (see
    "Interactive Parameter Confirmation").
11. **Send-result reporting**: a send response is gateway acceptance only, never proof of
    delivery — confirm with `query-send-details` (Scenario 3).

## References

- [Alibaba Cloud CLI documentation](https://help.aliyun.com/zh/cli/)
- [SMS Service console](https://dysms.console.aliyun.com/)
- [SendSms API documentation](https://help.aliyun.com/document_detail/419273.html)
- [SendTestVerification API (test SMS, no signature/template)](https://api.aliyun.com/api/Dysmsapi/2017-05-25/SendTestVerification)
- [Send-status error codes (local)](references/sms-error-codes.md) — `query-send-details` `ErrCode` (Alibaba `isv.*`/`isp.*` + carrier receipts); upstream: [101347](https://help.aliyun.com/document_detail/101347.html) / [101346](https://help.aliyun.com/document_detail/101346.html)
- [SMS qualification query (local)](references/sms-qualification.md) — `QuerySmsQualificationRecord` / `QuerySingleSmsQualification`
