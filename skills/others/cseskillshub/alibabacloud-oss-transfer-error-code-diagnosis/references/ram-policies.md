# RAM Policies

## Permission posture: none required

This skill is knowledge-driven and makes **zero cloud API calls**:

- No aliyun CLI invocation of any kind.
- No OpenAPI request to OSS, RAM, STS, BSS, or any other service.
- No network probing (no DNS lookups, no TCP connections).

All diagnosis is produced by the local entry script
`scripts/oss_transfer_error_diagnosis.py` from its embedded error-code
catalog. Therefore **no RAM policy, no role, and no credential of any kind
are required to run this skill**, and none should ever be requested from the
user.

## Credential handling

Never ask the user for, read, print, or forward any AccessKey, secret, or
STS token. The diagnosis input is limited to: error code, HTTP status,
RequestId, bucket name, and operation type - all non-sensitive strings.

## If cloud access is ever added in the future

Any future revision that introduces cloud calls must, before release:

1. Declare the minimal read-only RAM actions here, scoped to specific
   resources (never account-wide).
2. Keep the skill read-only; no write actions of any kind.
3. Re-run both static gates and update this file accordingly.
