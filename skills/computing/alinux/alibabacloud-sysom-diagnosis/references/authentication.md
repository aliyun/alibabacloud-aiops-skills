# Alibaba Cloud Authentication Setup Guide

This guide explains how to configure authentication for remote SysOM diagnosis.

## Prerequisites

- Alibaba Cloud CLI installed (if needed: `yum install aliyun-cli -y`)
- Alibaba Cloud account or RAM-user permissions

## Supported Authentication Modes

| Auth mode | Typical scenario | Recommendation |
|---------|---------|---------|
| **ECS RAM Role** | Running inside ECS instance | ⭐⭐⭐⭐⭐ strongly recommended |
| **AccessKey (AK)** | Local development/testing | ⭐⭐⭐ for controlled use only |
| **STS Token** | Temporary sessions / cross-account temporary auth | ⭐⭐⭐⭐ preferred over long-lived AK |

---

## Mode 1: ECS RAM Role (Recommended)

### Why RAM Role

- No manual AccessKey lifecycle management
- Temporary credential auto-rotation
- SDK can auto-fetch credentials from metadata service

### Setup Steps

#### Step 1: Create RAM Role (if missing)

1. Open [RAM Console](https://ram.console.aliyun.com/roles)
2. Create role -> trusted service: **ECS**
3. Name role (for example `SysomRole`) and complete creation

Reference: [Create RAM role](https://help.aliyun.com/zh/ram/user-guide/create-a-ram-role-for-a-trusted-alibaba-cloud-service)

#### Step 2: Grant `AliyunSysomFullAccess` (Required)

Attach `AliyunSysomFullAccess` to the RAM role; otherwise SysOM APIs will fail.

Reference: [Policy details](https://ram.console.aliyun.com/policies/AliyunSysomFullAccess/System/content)

#### Step 3: Attach RAM Role to ECS Instance

1. Open [ECS Console](https://ecs.console.aliyun.com/server)
2. Select instance -> More -> Instance Settings -> Bind/Unbind RAM Role
3. Select created role and confirm

Verify:

```bash
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/
```

Reference: [Attach instance RAM role](https://help.aliyun.com/zh/ecs/user-guide/attach-an-instance-ram-role-to-an-ecs-instance)

#### Step 4: Configure CLI as EcsRamRole

```bash
aliyun configure --mode EcsRamRole --ram-role-name <ROLE_NAME>
```

Example:

```bash
aliyun configure --mode EcsRamRole --ram-role-name SysomRole
```

Example `~/.aliyun/config.json`:

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "EcsRamRole",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "en"
    }
  ],
  "meta_path": ""
}
```

Notes:

- `ram_role_name` field is not required in `config.json`.
- SDK resolves role name and temporary credentials from metadata (`100.100.100.200`).

#### Step 5: Validate with Precheck

```bash
cd /path/to/sysom-diagnosis
./scripts/osops.sh precheck
```

`precheck` validates:

1. ECS metadata role visibility
2. env credentials (AK/SK and optional STS token)
3. `~/.aliyun/config.json` auth profile
4. SysOM API accessibility via `InitialSysom`

Use `osops precheck` as the only recommended validation method.

### Troubleshooting (RAM Role)

- Role attached but precheck fails:
  - `AliyunSysomFullAccess` not granted to role
  - policy change not propagated yet (wait 2-5 minutes)
- Role not found:
  - verify role exists in RAM console
  - verify role is attached in ECS console

---

## Mode 2: AccessKey (AK)

### Security Notes

- Long-lived secrets carry higher leakage risk; use for controlled dev/test scenarios.
- Do not pass AK/SK via command-line options.

### Agent/Multi-shell Safety (Preferred)

In COSH or agent workflows, do not paste secrets into chat.

Preferred flow:

```bash
./scripts/osops.sh configure
./scripts/osops.sh precheck
```

If interactive shell is unavailable (no PTY), enable interactive shell (`/settings`) or use `/bash`.

### Setup Steps

#### Step 1: Obtain AccessKey

1. Open [RAM Console](https://ram.console.aliyun.com/)
2. Create/select RAM user
3. Create AccessKey and store ID/Secret securely

#### Step 2: Configure (choose one method)

Method A (recommended): edit `~/.aliyun/config.json`

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "AK",
      "access_key_id": "LTAI...",
      "access_key_secret": "...",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "en"
    }
  ],
  "meta_path": ""
}
```

Method B: interactive helper

```bash
./scripts/osops.sh configure
```

#### Step 3: Validate

```bash
./scripts/osops.sh precheck
```

---

## Mode 3: STS Token

Use STS for temporary sessions or cross-account delegated access.

Supported env variables:

- `ALIBABA_CLOUD_ACCESS_KEY_ID`
- `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
- `ALIBABA_CLOUD_SECURITY_TOKEN`

`~/.aliyun/config.json` also supports `mode: StsToken` with `sts_token` / `security_token`.

Validate with:

```bash
./scripts/osops.sh precheck
```

---

## Recommended Validation and Runtime Sequence

1. Configure one auth path (RAM Role / AK / STS)
2. Run `./scripts/osops.sh precheck`
3. After `ok: true`, run deep diagnosis commands

---

## Common Failure Patterns

| Symptom | Likely cause | Recommended action |
|------|------|------|
| `service_not_activated` | SysOM not activated | Activate SysOM in Alinux console, wait 1-3 minutes, rerun precheck |
| credential parse error | malformed `~/.aliyun/config.json` | fix JSON or recreate via `./scripts/osops.sh configure` |
| ECS role visible but auth fails | role policy missing | attach `AliyunSysomFullAccess` to role and retry |
| remote diagnosis auth failure | missing prerequisites on target | rerun precheck and follow [invoke-diagnosis.md](./invoke-diagnosis.md) |

---

## Related Documents

- [openapi-permission-guide.md](./openapi-permission-guide.md)
- [permission-guide.md](./permission-guide.md)
- [invoke-diagnosis.md](./invoke-diagnosis.md)
- [metadata-api.md](./metadata-api.md)
