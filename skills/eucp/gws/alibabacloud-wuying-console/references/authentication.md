# Authentication

Use Aliyun CLI's standard credential mechanisms. Do not copy credentials into this skill, command history, generated files, or chat output.

## Recommended setup

For a human operating a local agent, prefer OAuth login:

```bash
aliyun configure --mode OAuth --profile default
```

This opens the official Aliyun authorization flow. Ask the user before starting it because authentication changes local CLI state.

For an existing named profile, pass it consistently:

```bash
aliyun ecd <command> --profile <profile> --api-version <version> --cli-ai-mode
```

## Rules

- Reuse an existing valid profile when the user identifies one.
- Never print, store, or ask the user to paste an AccessKey secret into chat.
- Do not create a second credential store for this skill.
- Do not silently switch accounts or profiles. State which profile/account context will be used before a mutation.
- For unattended environments, use the credential method approved by the customer's security policy; do not convert a personal login into a long-lived shared credential.
- If authentication expires, stop and request reauthentication. Do not fall back to a different profile without approval.
