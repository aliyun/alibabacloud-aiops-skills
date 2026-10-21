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

### Official flow and permission boundaries

- OAuth login is interactive. `aliyun configure set --mode OAuth ...` writes
  configuration parameters only; it does not start browser authorization or
  establish a valid OAuth session. Do not offer it as a noninteractive login
  alternative or treat a saved profile as successful authentication.
- OAuth scopes and RAM Action permissions are different contracts. Do not
  construct OAuth scopes from product names or present `ecd:*`,
  `appstream-center:*`, or other product wildcards as consent-page scopes.
  Consult the [official OAuth setup guide](https://help.aliyun.com/zh/ram/configure-oauth-for-alibaba-cloud-cli)
  and the actual official consent screen. That guide documents `openid` and
  `/internal/ram/usersts` for `official-cli`; business API access still depends
  on the signed-in identity's RAM authorization. OAuth's internal acquisition
  of temporary STS credentials is not permission to select a StsToken profile
  as this Skill's authentication fallback.
- RAM users/roles may need an administrator to install the `official-cli`
  application and assign their identity before login. Administrator application
  consent and the user's browser consent are separate. Report a missing
  prerequisite; do not install the RAM application, assign identities, or grant
  broader permissions as part of routine CLI/plugin setup. A local browser on
  the CLI device is required; a headless sandbox is not proof the user's own
  device cannot authenticate. Never fall back to AK/STS to work around this.
- For a configuration-plan/preparation-only request, give the unexecuted command,
  actual checks and future consent/recheck steps, then finish. Explain unresolved
  account/site/overwrite decisions as prerequisites for a later authorized
  login; do not hold the completed plan waiting for execution authorization.

See [official CLI OAuth credentials](https://help.aliyun.com/zh/cli/oauth-credentials)
for login prerequisites and the distinction between configuration and login.

Avoid duplicate chat confirmations:

- Reuse a valid active OAuth profile without asking the user to log in again.
- Finish allowed dependency preparation first. For metadata-only/check-only
  tasks, no login is needed; do not ask for it.
- An explicit no-login/no-profile-change restriction is a decision, not missing
  authorization to request again. In that task, report the authentication
  blocker and finish; do not hold it for consent to a prohibited action.
  Future prerequisites may be described as unexecuted conditions, not as a
  question that must be answered to complete the current blocked task.
- Retain authorization already given for the exact profile/login operation in
  this workflow. An explicit request to configure OAuth for a named profile is
  authorization for that scoped login, not a reason to ask the same question again.
  A generic cloud query or permission to install software is not login authority.
- If login/profile changes are not prohibited but the exact change is not yet
  authorized, ask one combined question describing
  the proposed profile and any account/overwrite decision that actually remains
  unresolved. Do not ask separately whether to configure, open the browser,
  then continue. Account choice and overwriting an existing profile must never
  be inferred merely to avoid a question.
- Use the selected effective CLI path for login as well as rechecking/execution.
  Have the user complete official browser login and consent; do not answer consent
  for them, collect secrets in chat, or repeatedly restart the login flow. On
  completion, rerun the check and automatically resume the original permitted
  task. A cloud mutation still needs its separate exact-target confirmation.
- A failed/timed-out profile inspection is not an expired profile. Retry that
  local inspection once before reporting the blocker; do not start login or
  change credentials based on missing evidence.

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
- If the available profile is not OAuth, stop business calls and follow the single scoped login decision above. Do not continue with another credential mode.
- Client-session API contracts are unsupported. If a command requires client-session credentials, do not ask for them; select an OAuth-compatible catalog entry or report the operation as unsupported.
- If authentication expires, stop business calls and follow the same scoped reauthentication decision. Never fall back to AK/STS or another profile to continue this OAuth-only workflow.

## Real execution is not an authentication override

Instructions such as "execute real calls", "never simulate/mock", "verify now",
or "do not stop" describe the requested execution quality, not new credential
authority. When OAuth is unavailable, run the real environment check (or the
entry point, which records `request_sent: false`) and report the real rejection.
That is not a simulated cloud result. Do not issue a direct CLI/SDK/HTTP request
to satisfy the task after preflight denies it, even if a valid STS/AK profile is
available. Software-installation authorization also does not authorize this.
