# RAM Policies

## Permission posture: none required

This skill is knowledge-driven and makes **zero cloud API calls**:

- No aliyun CLI invocation of any kind.
- No OpenAPI request to OSS, RAM, STS, BSS, or any other service.
- No network probing (no DNS lookups, no TCP connections).

All diagnosis is produced by the local entry script
`scripts/oss_backup_integration_diagnosis.py` from its embedded tool x
symptom integration catalog (`scripts/_integration_catalog.py`). Therefore
**no RAM policy, no role, and no credential of any kind are required to
run this skill**, and none should ever be requested from the user.

## Credential handling

Never ask the user for, read, print, or forward any AccessKey, secret, or
STS token. The diagnosis input is limited to: backup tool name/version,
error message text, symptom description, storage class, bucket name and
region — all non-sensitive strings.

## Advice-only boundary

Even where the diagnosis suggests a configuration change (endpoint form,
signature version, RAM actions for the backup tool, whitelist request),
this skill only produces the advice text. The user (or a support ticket)
executes the change. The Veeam compatibility whitelist in particular is a
manual Alibaba Cloud backend action that this skill can never perform.

## If cloud access is ever added in the future

Any future revision that introduces cloud calls must, before release:

1. Declare the minimal read-only RAM actions here, scoped to specific
   resources (never account-wide).
2. Keep the skill read-only; no write actions of any kind.
3. Re-run both static gates and update this file accordingly.
