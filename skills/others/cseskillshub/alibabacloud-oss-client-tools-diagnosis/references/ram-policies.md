# RAM Policies

## Permission posture: none required

This skill is knowledge-driven and makes **zero cloud API calls**:

- No aliyun CLI invocation of any kind.
- No OpenAPI request to OSS, RAM, STS, BSS, or any other service.
- No network probing (no DNS lookups, no TCP connections).
- No execution of any ossutil/ossbrowser command — commands and templates
  are only OUTPUT for the user to run locally.

All diagnosis is produced by the local entry script
`scripts/oss_client_tools_diagnosis.py` from its embedded client-tool
catalog. Therefore **no RAM policy, no role, and no credential of any kind
are required to run this skill**, and none should ever be requested from the
user.

## Credential handling

Never ask the user for, read, print, or forward any AccessKey, secret, or
STS token. The diagnosis input is limited to: tool name, error text, EC
code, symptom, endpoint, and version — all non-sensitive strings. The
embedded config template contains placeholders only.

## If cloud access is ever added in the future

Any future revision that introduces cloud calls must, before release:

1. Declare the minimal read-only RAM actions here, scoped to specific
   resources (never account-wide).
2. Keep the skill read-only; no write actions of any kind.
3. Re-run both static gates and update this file accordingly.
