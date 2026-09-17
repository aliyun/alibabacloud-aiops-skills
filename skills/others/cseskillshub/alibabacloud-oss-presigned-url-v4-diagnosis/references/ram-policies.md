# RAM Policies

## Permission posture: none required

This skill is knowledge-driven and makes **zero cloud API calls**:

- No aliyun CLI invocation of any kind.
- No OpenAPI request to OSS, RAM, STS, BSS, or any other service.
- No network probing (no DNS lookups, no TCP connections, and never
  fetching the presigned URL itself).

All diagnosis is produced by the local entry script
`scripts/oss_presigned_url_diagnosis.py` from its embedded failure-mode
catalog. Therefore **no RAM policy, no role, and no credential of any kind
are required to run this skill**, and none should ever be requested from the
user.

## Credential handling

Never ask the user for, read, print, or forward any AccessKey, secret, or
STS token. The diagnosis input is limited to: the presigned URL (with keys
and signatures masked by the script), the error code, the HTTP status, and
free-text symptom description.

## If cloud access is ever added in the future

Any future revision that introduces cloud calls must, before release:

1. Declare the minimal read-only RAM actions here, scoped to specific
   resources (never account-wide).
2. Keep the skill read-only; no write actions of any kind.
3. Re-run both static gates and update this file accordingly.
