# Shared CLI/OpenAPI procedure

EIAM API version is 2021-12-01. Supported vendor values are alibaba_cloud, aws,
and tencent_cloud; site values are china_mainland and global. Follow the
selected provider reference directly linked from SKILL.md.

## Profile resolution

For a live request with confirmed targets, prepare a plugin-based Alibaba Cloud
CLI before the first STS or other API call:

1. Inspect the local version and configure-set help for supported flags.
2. Enable auto-plugin-install on the selected EIAM Alibaba Cloud CLI profile.
   For an Alibaba Cloud target, configure its already authorized role chain if
   needed, then enable the same setting on that target Alibaba Cloud profile.
   AWS and Tencent Cloud targets use their own CLI profiles; do not create or
   configure Alibaba Cloud profiles for them. Do not copy credentials.
3. Complete local STS/EIAM command help on the EIAM profile and the required
   target-provider command help on its own profile. Use documented public API
   commands for capability checks, not auxiliary actions omitted from public
   CLI metadata. Complete authorized official plugin installation separately;
   do not pipe installation/help through head or parse it as an API response.
4. Only after preparation succeeds, call the identity APIs and continue
   discovery. Bound each preparation command to 120 seconds and each identity
   request to 60 seconds. An installer prompt, unsupported flag, or timeout is
   environment_required; stop with the actual blocker instead of repeating a
   hanging API request.

Inspect only sanitized profile summaries. Verify each candidate with the
provider's identity API and require exact target-account ownership. Verify the
EIAM profile can access the requested instance independently. Multiple valid
matching profiles require user selection; do not choose the first arbitrarily.
If CLI or authorization is missing, explain one actionable step and resume
with the same inputs afterward. Install official software only with authorization.

## Login isolation

Use a CLI-supported no-browser/device/remote login option when opening a
specific browser is necessary. Open each one-time URL in one browser only;
an unrelated default-browser session can otherwise complete the callback for
the wrong account. Keep the original CLI process running to receive its own
callback or polling result. Enter a required one-time code in the local
terminal, not chat. Verify full identity immediately after login.

Do not override system browser settings or substitute system executables.
Windows uses supported official CLI login and Start-Process where necessary;
no macOS open command or Linux xdg-open is assumed.

## Discovery and dynamic configuration

Read all ListInstances and ListCloudAccounts pages. Match both vendor and
external account ID. Stop on failed reads instead of treating them as absence.
After CreateCloudAccount, locate the automatic system/system_init role.
Missing automatic roles indicate a server creation failure: do not call
CreateCloudAccountRole, which creates a user role.

GetCloudAccountRoleConfig returns a vendor-specific configuration object.
Read RoleName, TrustConfig, and PolicyConfigs without fabricating missing fields.
CloudAccountProviderName is the preferred provider name. Normalize audience
strings/arrays to sets and compare policy documents semantically.

Inspect provider, role trust/duration, policy default versions and attachments.
Read existing objects before creating, and distinguish not-found from denied.
Use stable ClientToken where supported. After a write timeout, read state before
retrying. Never rename or delete a conflicting resource to bypass the conflict.

## Verification

Run CheckCloudAccountRoleConfig and read CloudAccountHealth,
CloudAccountHealthCheckResult, CloudAccountRoleHealth, and
CloudAccountRoleHealthCheckResult. Preserve ErrorCode and RequestId but sanitize
errors before user-visible output. A stale healthy result is not proof that the
latest configuration passed. Use bounded waits and report partial completion.
