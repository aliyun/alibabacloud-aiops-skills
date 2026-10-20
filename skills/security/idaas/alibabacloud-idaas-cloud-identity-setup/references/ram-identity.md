# Runtime RAM identity

This management/configuration skill uses a customer's authorized RAM user or
RAM role for EIAM administration. Publisher permissions do not grant access to
customer instances. Never bundle a publisher profile or credentials.

Verify EIAM identity with STS GetCallerIdentity and instance-scoped reads.
STS AccountId identifies the credential's account; in delegated cross-account
contexts it alone does not prove instance ownership. Use explicit instance
ownership metadata or server-side authorization evidence. Read access does not
prove write permission.

For the Alibaba Cloud target profile, STS AccountId must exactly equal the
requested cloud account. Compare current-account and other-account context
using verified identities and instance ownership, not the instance ID string.
AWS and Tencent Cloud require their own separate verified identities.

Use temporary credentials and official profile providers. Never print profile
credential files, environment credential values, callback URLs, or tokens.
Use only the mode-specific actions loaded through the main skill entrypoint.
Do not grant administrator wildcard Actions to overcome an authorization failure.

## Chaining an existing profile

Use the official `ChainableRamRoleArn` mode with `--source-profile` when an
existing OAuth/STS/profile identity assumes an approved target role.
`RamRoleArn` is for an AccessKey-based source and is not a substitute for profile
chaining. Check `aliyun configure set --help`, configure the named chain, then
verify STS AccountId before any target call. If configuration fails, stop with
the sanitized error. Never inspect or copy fields from credential files to make
the chain work. Do not pipe failed CLI calls to tee/head without preserving the
CLI exit code; parse JSON and treat non-JSON CLI errors as failures.

The non-interactive profile command uses `--ram-role-arn` and requires a
`--role-session-name`; `--role-arn` is not the configuration flag. For example:

```sh
aliyun configure set --profile TARGET_PROFILE --mode ChainableRamRoleArn --source-profile SOURCE_PROFILE --ram-role-arn APPROVED_ROLE_ARN --role-session-name idaas-onboarding --region CONFIRMED_REGION
```

For plugin-based CLI versions, prepare each named profile separately before
API calls: after checking flag support, set `--auto-plugin-install true` for
SOURCE_PROFILE and TARGET_PROFILE. Run local command help for STS/EIAM with
the source profile and IMS/RAM with the target profile so any authorized official
plugin installation finishes outside JSON API response parsing. A source-profile
setting is not inherited by a chainable target profile. Do not leave an install
prompt running inside discovery or resource inspection.

This stores profile references, not manually copied credential values. Validate
flag support against the installed CLI before invoking the command.

On permission denial, stop the affected workflow. Do not probe another cloud
profile, enumerate RAM roles/policies, broaden access, or treat denial as absence.

Source: https://help.aliyun.com/en/cli/ram-role-credentials
