---
name: alibabacloud-chatapp-message-send
description: >
  Send WhatsApp messages via Alibaba Cloud Chat App Message Service (CAMS).
  Supports both template messages and custom (free-form) messages.
  Use this skill when the user wants to send WhatsApp messages, broadcast notifications,
  marketing campaigns, verification codes, reply to customer messages,
  view available message templates, or query template structure and variables.
license: Apache-2.0
compatibility: >
  aliyun-cli >= 3.3.3
  cams plugin (auto-install)
  Alibaba Cloud AccessKey required
metadata:
  domain: cloud-communication
  owner: chatapp-team
  contact: chatapp-team@alibaba-inc.com
  implementation: aliyun-cli
  ram_policies: references/ram-policies.md
---
## Overview

This skill wraps the Alibaba Cloud Chat App Message Service (CAMS) via **aliyun CLI**, providing the following core capabilities:

- **Send Template Messages**: Send WhatsApp template-based messages with variable substitution
- **Send Custom Messages**: Send free-form messages (text, image, video, audio, document, interactive, location) within the 24-hour session window
- **List Templates**: Query all message templates with filtering by audit status, type, and language
- **Get Template Detail**: View template structure and variables to correctly fill in send parameters

## Prerequisites

### 1. CLI Version Verification

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.
>
> **Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send`

**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send"
```

**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

### 2. Install cams Plugin

```bash
aliyun plugin install --names aliyun-cli-cams
```

### 3. Credential Verification

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
>
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
>
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
>
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

### 4. Enable Chat App Message Service

Complete the following in the [Alibaba Cloud Console](https://cams.console.aliyun.com/):

1. Enable Chat App Message Service
2. Bind a WhatsApp Business Account (WABA)
3. Register and get the sender phone number approved (From)
4. Create and get message templates approved (required for template messages)

## Usage

### Direct aliyun CLI

**Send a template message:**

```bash
aliyun cams send-chatapp-message \
  --channel-type whatsapp \
  --type template \
  --from "86138xxxx" \
  --to "86139xxxx" \
  --template-code "hello_world" \
  --biz-language "en" \
  --template-params 1=Alice 2=Bob \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send
```

**Send a custom text message:**

```bash
aliyun cams send-chatapp-message \
  --channel-type whatsapp \
  --type message \
  --from "86138xxxx" \
  --to "86139xxxx" \
  --message-type text \
  --content '{"text":"Hello, this is a test message"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send
```

**List approved templates:**

```bash
aliyun cams list-chatapp-template \
  --audit-status pass \
  --template-type WHATSAPP \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send
```

**Get template detail:**

```bash
aliyun cams get-chatapp-template-detail \
  --template-code "hello_world" \
  --biz-language "en" \
  --template-type WHATSAPP \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send
```

### Using Wrapper Scripts

This skill provides Python wrapper scripts for simplified invocation with pre-send confirmation.

**List approved templates:**

```bash
python scripts/list_templates.py --audit-status pass --template-type WHATSAPP
```

**Get template detail (view variable structure):**

```bash
python scripts/get_template_detail.py --template-code hello_world --language en
```

**Send a template message (with confirmation):**

```bash
python scripts/send_chatapp_message.py send-template \
  --from "86138xxxx" --to "86139xxxx" \
  --template-code hello_world --language en \
  --template-params 1=Alice 2=Bob
```

**Send a custom message (with confirmation):**

```bash
python scripts/send_chatapp_message.py send-message \
  --from "86138xxxx" --to "86139xxxx" \
  --message-type text \
  --content '{"text":"Hello"}'
```

**Skip confirmation and send directly:**

```bash
python scripts/send_chatapp_message.py send-template ... --yes
```

**Preview command only (dry-run):**

```bash
python scripts/send_chatapp_message.py send-template ... --dry-run
```

## Parameter Reference

### aliyun cams send-chatapp-message Parameters

| Parameter         | Required              | Description                                                                                                  |
| ----------------- | --------------------- | ------------------------------------------------------------------------------------------------------------ |
| --channel-type    | Yes                   | Channel type:`whatsapp` / `viber`                                                                        |
| --type            | Yes                   | Message type:`template` (template message) / `message` (custom message)                                  |
| --from            | Yes                   | Sender phone number, numeric digits only, must be registered and approved in console (e.g.`8613867404376`) |
| --to              | Yes                   | Recipient phone number, numeric digits with country code**without `+`** (e.g. `8619521605234`)     |
| --template-code   | Required for template | Template code                                                                                                |
| --biz-language    | Required for template | Template language, e.g.`en`, `zh_CN`                                                                     |
| --template-params | No                    | Template variables in format `key=value`, multiple separated by spaces                                     |
| --message-type    | Required for custom   | Content type:`text`/`image`/`video`/`audio`/`document`/`interactive`/`location` etc.           |
| --content         | Required for custom   | Message content as a JSON string                                                                             |
| --cust-space-id   | No                    | ISV account space ID                                                                                         |
| --user-agent      | Yes                   | Fixed value `AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send`                                  |

### Custom Message Content JSON Formats

The `--content` parameter is a JSON string; format varies by message-type:

- **text**: `{"text":"Message content"}`
- **image**: `{"link":"https://example.com/img.jpg","caption":"Description"}`
- **video**: `{"link":"https://example.com/vid.mp4","caption":"Description"}`
- **audio**: `{"link":"https://example.com/aud.mp3"}`
- **document**: `{"link":"https://example.com/doc.pdf","fileName":"doc.pdf"}`
- **location**: `{"latitude":"39.9042","longitude":"116.4074","name":"Tiananmen","address":"Beijing"}`
- **interactive**: `{"type":"button","action":{"buttons":[{"type":"reply","reply":{"id":"btn1","title":"Confirm"}}]}}`

## Core Workflow and Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., From, To, template code, language, template params, content JSON, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

### Template Message Flow

**Step 1: Confirm sender and recipient numbers**

- Sender (From): WhatsApp number registered in the console, **numeric digits only without `+`** (e.g. `8613867404376`)
- Recipient (To): Target user's WhatsApp number, **numeric digits with country code without `+`** (e.g. `8619521605234`)

**Step 2: Select template code**

- Run `python scripts/list_templates.py --audit-status pass` to query approved templates
- Let the user select a template code from the list

**Step 3: Confirm template language**

- Ask the user for the template language, e.g. `en`, `zh_CN`, `zh_HK`

**Step 4: View template variables and guide user to fill them in**

- Run `python scripts/get_template_detail.py --template-code <CODE> --language <LANG>`
- Based on the variable list in the output, guide the user to fill in each variable value one by one
- Variable format: `--template-params 1=value1 2=value2 3=value3`

**Step 5: Confirm before sending**

- The script automatically summarizes all parameters and displays them for user confirmation
- Sending is only executed after the user inputs `yes`

### Custom Message Flow

**Step 1: Confirm sender and recipient numbers** (same as above)

**Step 2: Confirm message type**

- Ask the user for the message type: `text` / `image` / `video` / `audio` / `document` / `interactive` / `location`

**Step 3: Construct Content JSON based on message type**

- Based on the selected type, guide the user to provide necessary fields (e.g. text requires `text`, image requires `link`, etc.)
- Construct the JSON string as the `--content` parameter

**Step 4: Confirm before sending**

- The script automatically summarizes and displays; sending occurs after user inputs `yes`

> **Note**: Custom WhatsApp messages can only be sent within the 24-hour session window (within 24 hours after the user's last message). Outside the window, template messages must be used.

## Output Reference

### Successful Send Response

```json
{
  "Code": "OK",
  "Message": "OK",
  "RequestId": "4C3D8B1B-B3D8-5673-B724-1F251799CE9A",
  "Data": {
    "MessageId": "wamid.xxx"
  }
}
```

### Template List Example

```
Found 3 templates:

  - hello_world | Welcome Template | Language: en | Status: pass | Category: MARKETING | WHATSAPP
  - otp_verification | OTP | Language: zh_CN | Status: pass | Category: AUTHENTICATION | WHATSAPP
```

## Error Handling

### Common Error Codes

| Error Code                       | Description                 | Resolution                                                                                 |
| -------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------ |
| InvalidParameter.FromOnlyNumeric | Phone number contains `+` | API requires pure numeric format, remove `+`, e.g. `8613867404376`                     |
| TemplateNotFound                 | Template does not exist     | Confirm template code and language are correct                                             |
| TemplateParamInvalid             | Template variable error     | Check variable count and format match the template                                         |
| SessionWindowExpired             | Session window expired      | Custom messages must be sent within 24h of user's last reply; use template message instead |
| PhoneNumberNotRegistered         | Sender not registered       | Complete phone number registration and approval in console                                 |
| Forbidden.RAM                    | Insufficient permissions    | Check if RAM user has CAMS permissions                                                     |

### CLI Configuration Errors

| Error Message               | Cause                    | Solution                   |
| --------------------------- | ------------------------ | -------------------------- |
| InvalidAccessKeyId.NotFound | Wrong AccessKey ID       | Check AccessKey ID         |
| SignatureDoesNotMatch       | Wrong Secret             | Check AccessKey Secret     |
| Forbidden.RAM               | Insufficient permissions | Check RAM user permissions |

## RAM Permissions

This skill requires RAM permissions for CAMS APIs. See [`references/ram-policies.md`](references/ram-policies.md) for the complete permission list and minimum policy JSON.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
>
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Notes

1. **Phone Number Format**: All numbers must be **pure numeric digits** with country code but **without `+`**. For example: China `8613867404376`, US `14155551234`. Passing `+8613867404376` will raise `InvalidParameter.FromOnlyNumeric`
2. **Session Window**: Custom WhatsApp messages can only be sent within 24 hours after the user's last message. Outside the window, template messages must be used
3. **Template Approval**: Template messages must use approved templates (`audit-status = pass`)
4. **User-Agent**: All CLI commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-chatapp-message-send`
5. **Credential Security**: Never hardcode AK/SK in code or commands
6. **Viber Limitations**: Viber messages do not require templates, but have `promotion`/`transaction` type restrictions
7. **Content JSON**: The `--content` parameter for custom messages must be a valid JSON string
8. **ISV Scenarios**: If using an ISV account, additionally provide `--cust-space-id`

## Related Resources

- [Alibaba Cloud CLI Documentation](https://help.aliyun.com/zh/cli/)
- [Chat App Message Service Console](https://cams.console.aliyun.com/)
- [SendChatappMessage API Docs](https://www.alibabacloud.com/help/zh/chatapp/developer-reference/api-cams-2020-06-06-sendchatappmessage)
- [ListChatappTemplate API Docs](https://www.alibabacloud.com/help/zh/chatapp/developer-reference/api-cams-2020-06-06-listchatapptemplate)
- [GetChatappTemplateDetail API Docs](https://www.alibabacloud.com/help/zh/chatapp/developer-reference/api-cams-2020-06-06-getchatapptemplatedetail)
