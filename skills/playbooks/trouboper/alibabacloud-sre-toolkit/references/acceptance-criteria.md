# Acceptance Criteria

This document provides acceptance criteria for the usage and implementation of this Skill in a "CORRECT / INCORRECT" pattern. When performing diagnostics/inspection or configuration management, the correct patterns must be followed and the corresponding incorrect patterns avoided.

## 1. CLI Parameter Format (plugin mode)

Alibaba Cloud OpenAPI commands must use **plugin mode** (lowercase-hyphenated names), not PascalCase API names.

CORRECT
```bash
aliyun ecs describe-instances --region-id cn-beijing
aliyun rds describe-db-instances --region-id cn-hangzhou
aliyun sts get-caller-identity
```

INCORRECT
```bash
# Using PascalCase API name as subcommand
aliyun ecs DescribeInstances --RegionId cn-beijing
```

> Plugin mode depends on `aliyun configure set --auto-plugin-install true` and `aliyun plugin update`. See [cli-installation-guide.md](cli-installation-guide.md).

## 2. Configuration Format (accounts array vs hardcoded credentials)

`.starops/config.json` uses an `accounts[]` array to store `uid -> profile -> digital employee` mappings. **Never store credentials**.

CORRECT
```json
{
  "accounts": [
    {"uid": "123456", "profile": "acct-a", "employeeId": "emp-1", "workspace": "ws-1"}
  ]
}
```

INCORRECT
```json
{
  "accessKeyId": "EXAMPLE_AK_ID_DO_NOT_USE",
  "accessKeySecret": "EXAMPLE_AK_SECRET_DO_NOT_USE",
  "employeeId": "emp-1"
}
```

## 3. Authentication Mode (CredentialClient + profile read-only resolution vs modifying current)

Resolve credentials from `~/.aliyun/config.json` **read-only** by the session-selected profile. **Do not modify** `current`.

CORRECT
```
Use CredentialClient to read-only resolve ~/.aliyun/config.json by --profile to obtain AK/STS.
Each session is strictly bound to its UID's corresponding profile credentials. Does not modify aliyun CLI current.
```

INCORRECT
```bash
# Switching global current to obtain credentials, polluting other sessions/tools
aliyun configure set --profile acct-a   # modifies current
```

## 4. Idempotency Key (structured JSON sha256 vs raw | concatenation)

`idempotencyKey` is based on the `uid`/`employeeId`/`workspace`/`title` tuple, using **structured JSON (sort_keys + compact separators) followed by sha256**.

CORRECT
```python
idempotencyKey = sha256_hex(
    json.dumps(
        {"uid": uid, "employeeId": employeeId, "workspace": workspace, "title": title},
        separators=(",", ":"), sort_keys=True,
    ).encode()
)
```

INCORRECT
```python
# Raw string | concatenation, ambiguity / injection when field contains delimiter
idempotencyKey = f"{uid}|{employeeId}|{workspace}|{title}"
```

> The single source of truth for idempotency keys is defined in [starops-api.md](starops-api.md).

## 5. Security (credentials never persisted to .starops/config.json)

The sole storage location for credentials is aliyun CLI (`~/.aliyun/config.json`). Project configuration only stores mappings.

CORRECT
```
The skill never accepts or handles AK/SK credentials. Users configure credentials externally via `aliyun configure`.
.starops/config.json only writes uid/profile/employeeId/workspace mappings.
```

INCORRECT
```json
// Writing AK/SK into project config file (may leak via repository)
{"accounts": [{"uid": "123456", "accessKeySecret": "abcd1234********"}]}
```

> For configuration and credential constraints, see [starops-config.md](starops-config.md).
