---
name: alibabacloud-sms-send-short-message
description: >
  Send short messages (SMS) to specified phone numbers via Alibaba Cloud Short Message Service.
  Supports verification codes, notification messages, and marketing messages.
  Use this Skill whenever the user wants to send SMS verification codes, system notifications,
  order reminders, or marketing campaigns. Supports single send (SendSms, up to 1000 phone
  numbers sharing the same signature and template parameters) and batch send (SendBatchSms,
  up to 100 phone numbers, each with its own signature and template parameters). Supports
  domestic SMS as well as international/HK-Macao-Taiwan SMS. The signature and template
  approval status can be verified before sending to maximize delivery success rate.
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
> Run `aliyun version` to verify the version is >= 3.3.3. If not installed or the version
> is too low, run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install or
> update.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin
> installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local
> machine are always up-to-date.

**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution. Run the
following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message"
```

**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response
for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow
success, workflow failure, error/exception, user cancellation, session end, or any other
scenario where no further CLI commands will be executed. AI-mode is only used for Agent
Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation in this Skill must
include the flag:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message`

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

## Interactive Parameter Confirmation (Must Read)

Before executing any send-class operation (`send-sms` / `send-batch-sms`), this Skill
**must** collect these critical parameters first:

- `--sign-name` (signature name)
- `--template-code` (template code)
- `--template-param` (template variables, when the template contains placeholders)
- `--phone-numbers` / `--phone-number-json` (phone numbers)

### Handling Rules

When the user does not explicitly provide the **signature** or **template**, the AI
agent **must not guess or fabricate them**. Instead it should:

1. **Ask the user proactively**: "Which signature/template should I use? If unsure, I can
   list approved ones from your account for you to pick from."
2. **After the user agrees, call list APIs**:
   - `aliyun dysmsapi query-sms-sign-list ...`
   - `aliyun dysmsapi query-sms-template-list ...`
   - Filter by `SignStatus = 1` / `TemplateStatus = 1` (approved) and present a table
     (index / code / name / content / status) for the user to choose.
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

## Prerequisites

### 1. Install aliyun CLI (>= 3.3.3)

```bash
# macOS
brew install aliyun-cli

# Linux
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz && sudo mv aliyun /usr/local/bin/

aliyun version  # must be >= 3.3.3
```

### 2. Install the dysmsapi plugin

```bash
aliyun plugin install --names dysmsapi
```

### 3. Configure Credentials

The aliyun CLI **default credential chain** is recommended; it picks credentials in this
priority order: env vars → `~/.aliyun/config.json` → ECS RAM role → OIDC Token.

```bash
# Recommended for CI/CD: env vars
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou

# Verify
aliyun configure get
```

> **Important**: Never hard-code AK/SK in code or commands. Always rely on the default
> credential chain. On ECS use a RAM role; in K8s use OIDC.

### 4. Activate the SMS Service

In the [Alibaba Cloud SMS Console](https://dysms.console.aliyun.com/): activate the
service, create an **approved** signature, and create an **approved** template.

## Usage

### Calling aliyun CLI directly

**Send SMS**:
```bash
aliyun dysmsapi send-sms \
  --api-version 2017-05-25 \
  --phone-numbers "13800138000" \
  --sign-name "AliyunDemo" \
  --template-code "SMS_123456" \
  --template-param '{"code":"123456"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message \
  --read-timeout 3
```

**Batch send (different signatures / template params)**:
```bash
aliyun dysmsapi send-batch-sms \
  --api-version 2017-05-25 \
  --phone-number-json '["13800138000","13900139000"]' \
  --sign-name-json '["SignA","SignB"]' \
  --template-code "SMS_123456" \
  --template-param-json '[{"code":"111111"},{"code":"222222"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message \
  --read-timeout 3
```

**Query lists / status / details**:
```bash
# Approved signatures / templates (use to populate user choices)
aliyun dysmsapi query-sms-sign-list      --api-version 2017-05-25 --page-index 1 --page-size 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
aliyun dysmsapi query-sms-template-list  --api-version 2017-05-25 --page-index 1 --page-size 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# Single signature / template lookup
aliyun dysmsapi get-sms-sign     --api-version 2017-05-25 --sign-name "AliyunDemo"     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
aliyun dysmsapi get-sms-template --api-version 2017-05-25 --template-code "SMS_123456" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# Per-message delivery details (use BizId for precise lookup)
aliyun dysmsapi query-send-details \
  --api-version 2017-05-25 \
  --phone-number "13800138000" --send-date "20260326" \
  --page-size 10 --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# Aggregated statistics (--is-globe: 1=domestic, 2=intl/HK-Macao-Taiwan)
aliyun dysmsapi query-send-statistics \
  --api-version 2017-05-25 --is-globe 1 \
  --start-date "20260301" --end-date "20260326" \
  --page-index 1 --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# Filter by signature name + template type (optional)
aliyun dysmsapi query-send-statistics \
  --api-version 2017-05-25 --is-globe 1 \
  --start-date "20260301" --end-date "20260326" \
  --page-index 1 --page-size 10 \
  --sign-name "AliyunDemo" --template-type 0 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# SMS qualification — list records (full detail in references/sms-qualification.md)
aliyun dysmsapi query-sms-qualification-record \
  --api-version 2017-05-25 --page-no 1 --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# SMS qualification — single detail by GroupId
aliyun dysmsapi query-single-sms-qualification \
  --api-version 2017-05-25 --qualification-group-id 10000123 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

> Full filter parameters, response schemas, and state enum mapping for the
> qualification APIs are documented in
> [`references/sms-qualification.md`](references/sms-qualification.md).

### Using the wrapper script

`scripts/send_sms.sh` automatically applies `--api-version`, the compliant `--user-agent`,
and `--read-timeout`:

```bash
# Send (single or comma-separated phones)
./scripts/send_sms.sh send -p "13800138000" -s "AliyunDemo" -t "SMS_123456" -tp '{"code":"123456"}'

# Send with signature/template pre-verification (recommended)
./scripts/send_sms.sh send -p "13800138000" -s "AliyunDemo" -t "SMS_123456" -tp '{"code":"123456"}' --verify

# List & inspect
./scripts/send_sms.sh list-signs
./scripts/send_sms.sh list-templates
./scripts/send_sms.sh query-sign     --sign-name "AliyunDemo"
./scripts/send_sms.sh query-template --template-code "SMS_123456"

# Status & statistics
./scripts/send_sms.sh query-status     -p "13800138000" --send-date "20260326" --biz-id "xxx^0"
./scripts/send_sms.sh query-statistics --start-date "20260301" --end-date "20260326"
./scripts/send_sms.sh query-statistics --start-date "20260301" --end-date "20260326" --is-globe 2

# Filter by signature name and/or template type
./scripts/send_sms.sh query-statistics --start-date "20260301" --end-date "20260326" --sign-name "AliyunDemo" --template-type 0
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
| --user-agent      | Yes      | Fixed to `AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message` |
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
| --user-agent               | Yes      | Fixed to `AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message`     |
| --read-timeout             | Yes      | Read timeout in seconds, recommended value `3`                               |

> **SendSms vs SendBatchSms**: `send-sms` shares one signature/template across up to 1000
> numbers; `send-batch-sms` lets each phone use a different signature/template params (up
> to 100 numbers).

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
| --user-agent      | Yes      | Fixed to `AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message`             |
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

### CLI configuration errors

| Error message                | Cause                | Resolution                                     |
| ---------------------------- | -------------------- | ---------------------------------------------- |
| InvalidAccessKeyId.NotFound  | Wrong AccessKey ID   | Check the AccessKey ID                         |
| SignatureDoesNotMatch        | Wrong Secret         | Check the AccessKey Secret                     |
| Forbidden.RAM                | Insufficient permission | Verify the RAM user has SMS permissions     |

## Execution Flow

1. **Pre-check**: aliyun CLI installed (>= 3.3.3) and dysmsapi plugin available;
   AI-Mode enabled; credentials configured.
2. **Validate required parameters** (`phone-numbers`, `sign-name`, `template-code`).
   If signature or template is missing, ask the user; after consent call
   `query-sms-sign-list` / `query-sms-template-list` and present approved candidates.
3. **[Optional, --verify]** Verify signature status via `get-sms-sign` (`SignStatus=1`).
4. **[Optional, --verify]** Verify template status via `get-sms-template` (`TemplateStatus=1`).
5. **Send** via `aliyun dysmsapi send-sms` (or `send-batch-sms` for per-recipient
   personalization).
6. **Return result**: `Code=OK` → success, return `BizId`; otherwise return error info.
7. **[MUST]** Disable AI-Mode at every exit (success / failure / cancellation).

## Examples

### Scenario 1: Send a verification code

```bash
# 1) Pull approved signatures & templates first (so the user can pick)
aliyun dysmsapi query-sms-sign-list     --api-version 2017-05-25 --page-index 1 --page-size 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
aliyun dysmsapi query-sms-template-list --api-version 2017-05-25 --page-index 1 --page-size 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# 2) Send (after user confirmation)
aliyun dysmsapi send-sms \
  --api-version 2017-05-25 \
  --phone-numbers "13800138000" \
  --sign-name "YourSign" --template-code "SMS_xxx" \
  --template-param '{"code":"123456"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

### Scenario 2: Bulk-send with same signature & params

```bash
aliyun dysmsapi send-sms \
  --api-version 2017-05-25 \
  --phone-numbers "13800138000,13900139000,13700137000" \
  --sign-name "YourSign" --template-code "SMS_xxx" \
  --template-param '{"activity":"Double 11 Sale","discount":"50% OFF"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

### Scenario 3: Batch send with per-recipient personalization

```bash
aliyun dysmsapi send-batch-sms \
  --api-version 2017-05-25 \
  --phone-number-json '["13800138000","13900139000","13700137000"]' \
  --sign-name-json    '["BrandA","BrandB","BrandC"]' \
  --template-code "SMS_xxx" \
  --template-param-json '[{"name":"Alice","code":"111111"},{"name":"Bob","code":"222222"},{"name":"Charlie","code":"333333"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

> Lengths of `--phone-number-json`, `--sign-name-json`, and `--template-param-json` must
> match and correspond one-to-one.

### Scenario 4: Verify delivery & aggregate statistics

```bash
# Per-message delivery (uses BizId returned by send-sms)
aliyun dysmsapi query-send-details \
  --api-version 2017-05-25 \
  --phone-number "13800138000" --send-date "20260326" --biz-id "xxx^0" \
  --page-size 10 --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3

# Range-based aggregated statistics (1 row per send-day)
aliyun dysmsapi query-send-statistics \
  --api-version 2017-05-25 --is-globe 1 \
  --start-date "20260301" --end-date "20260326" \
  --page-index 1 --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

> **QuerySendDetails vs QuerySendStatistics**: `query-send-details` returns per-message
> records (delivery time, error code) — useful for troubleshooting. `query-send-statistics`
> returns aggregated daily counts — useful for trend reporting.

## Multi-Environment / Multi-Account

aliyun CLI supports multiple profiles. Prefer env vars or RAM roles:

```bash
# Option 1: env vars (recommended)
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>

# Option 2: profiles (region only; credentials still come from env vars or RAM role)
aliyun configure set --profile prod --region cn-hangzhou
aliyun configure set --profile test --region cn-shanghai

aliyun dysmsapi send-sms --profile prod \
  --api-version 2017-05-25 \
  --phone-numbers "13800138000" --sign-name "Sign" --template-code "SMS_xxx" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message --read-timeout 3
```

## Notes

1. **Plugin install**: First-time use requires `aliyun plugin install --names dysmsapi`.
2. **API version**: When calling the CLI directly, `--api-version 2017-05-25` is mandatory.
3. **Parameter format**: kebab-case (e.g. `--phone-numbers`, not `--PhoneNumbers`).
4. **Timeout**: `--read-timeout 3` is required. After a timeout, query the delivery
   receipt before deciding whether to retry.
5. **User-Agent**: `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sms-send-short-message`
   is required so the server can identify the caller.
6. **Idempotency**: SendSms/SendBatchSms are NOT idempotent — prevent duplicate sends at
   the business layer.
7. **Single vs batch**: Prefer `send-sms` for verification codes; `send-batch-sms` is only
   needed when each recipient requires different signature or template params (≤ 100).
8. **Billing**: Billing depends on carrier delivery; API success but carrier failure is
   not billed. QPS limit is 5000/s per user.
9. **Credential safety**: Never hard-code AK/SK; always rely on the default credential
   chain (env vars / `~/.aliyun/config.json` / ECS RAM role / OIDC).
10. **Parameter confirmation**: Never guess signature/template — always ask the user, and
    after consent fetch `query-sms-sign-list` / `query-sms-template-list` (see
    "Interactive Parameter Confirmation").

## References

- [Alibaba Cloud CLI documentation](https://help.aliyun.com/zh/cli/)
- [SMS Service console](https://dysms.console.aliyun.com/)
- [SendSms API documentation](https://help.aliyun.com/document_detail/419273.html)
- [Error code reference](https://help.aliyun.com/document_detail/101346.html)
- [SMS qualification query (local)](references/sms-qualification.md) — `QuerySmsQualificationRecord` / `QuerySingleSmsQualification`
