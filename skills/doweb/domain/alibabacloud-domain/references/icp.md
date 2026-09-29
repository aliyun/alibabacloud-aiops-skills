# ICP filing

All filing capability is under `aliyun domain icp`. Use the leaf help as the source of truth and add `--cli-ai-mode` to operational calls.

## Command map

| User intent | Command | Authentication | Completion meaning |
|---|---|---|---|
| Ask filing-policy or process questions | `aliyun domain icp ask --question "个人网站如何备案？"` | China-site OAuth | A knowledge answer was returned; no filing was created. |
| Open the filing assistant | `aliyun domain icp fill` | None | A filing page URL was returned or opened; no filing was created or submitted by the CLI. |
| Query filing order progress | `aliyun domain icp status` | China-site OAuth | Current matching order data was returned; it may still be non-terminal. |
| Query successful filing data | `aliyun domain icp info` | China-site OAuth | Successful filing records visible to the account were returned. |

## Selection rules

- Use `ask` for policy, eligibility, required materials, province-specific guidance, entity type, and order-type questions.
- Use `fill` only when the user wants to start or continue entering filing information in the official browser workflow.
- Use `status` for an in-progress filing. Supply at least one identifier supported by leaf help: filing order ID, organizer name, domain name, or ICP number.
- Use `info` for filing-success records. Do not represent it as risk scoring unless the installed leaf explicitly exposes such output.

## Safe examples

```bash
aliyun domain icp ask --question "网站新增备案需要准备哪些材料？" --cli-ai-mode
aliyun domain icp fill --cli-ai-mode
aliyun domain icp status --domain-name example.com --cli-ai-mode
aliyun domain icp info --cli-ai-mode
```

## Privacy and lifecycle rules

- Organizer names, identity attributes, filing numbers, order IDs, phone numbers, and contact data are private. Return only fields needed for the user's task.
- Never ask for identity documents, SMS codes, passwords, or OAuth tokens in chat.
- Browser opening is a handoff, not filing completion. Tell the user which page was opened and what they must do there.
- A non-terminal filing response must include the current state, the next required party or action when available, and the identifier needed for a later status query.
- Do not bypass DomainCLI with direct Beian or Company Registration OpenAPI calls.

