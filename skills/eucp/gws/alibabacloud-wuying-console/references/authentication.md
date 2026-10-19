# Authentication

This Skill supports only Aliyun CLI OAuth profiles. Do not use AccessKey, STS, client-session tokens, or another credential mode as a fallback. Do not copy credentials into this skill, command history, generated files, or chat output.

## Recommended setup

Only after the user authorizes the exact profile change, configure OAuth login:

```bash
aliyun configure --mode OAuth --profile <authorized-profile>
```

This opens the official Aliyun authorization flow and changes local CLI state.
Do not overwrite an existing profile or silently select a different account.
Have the authorized OAuth profile active, then rerun `check_environment.py`.

Every business request uses the checked active OAuth profile through the same
entry point (replace product, command and parameters only after live-help
verification):

```bash
python3 scripts/run_wuying.py -- aliyun <product> <command> --api-version <version> <parameters> --cli-ai-mode --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-wuying-console/${SKILL_SESSION_ID} skill-version/${SKILL_VERSION}"
```

## Rules

- Only `checks.valid_oauth_profile is true` authorizes business execution; a valid AK/STS profile is not OAuth evidence. Do not pass `--profile` or credential overrides around the entry point.
- Never print, store, or ask the user to paste an AccessKey secret, `client-id`, `login-token`, or `session-id` into chat.
- Do not create a second credential store for this skill.
- Do not silently switch accounts or profiles. State which profile/account context will be used before a mutation.
- If the available profile is not OAuth, stop and request authorization to configure OAuth. Do not continue with another credential mode.
- Client-session API contracts are unsupported. If a command requires client-session credentials, do not ask for them; select an OAuth-compatible catalog entry or report the operation as unsupported.
- If authentication expires, stop and request reauthentication. Never fall back to AK/STS or another profile to continue this OAuth-only workflow.

## Real execution is not an authentication override

Instructions such as "execute real calls", "never simulate/mock", "verify now",
or "do not stop" describe the requested execution quality, not new credential
authority. When OAuth is unavailable, run the real environment check (or the
entry point, which records `request_sent: false`) and report the real rejection.
That is not a simulated cloud result. Do not issue a direct CLI/SDK/HTTP request
to satisfy the task after preflight denies it, even if a valid STS/AK profile is
available. Software-installation authorization also does not authorize this.
