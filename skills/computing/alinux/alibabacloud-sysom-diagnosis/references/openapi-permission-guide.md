# SysOM OpenAPI: Agent Permission Playbook

Use this guide to walk users through identity, policy, and service-activation setup.  
It is designed to work with **`precheck` JSON** and diagnosis commands.

## 1) Session Rules (Strict)

1. If a session needs **remote SysOM capability** (`memory ... --deep-diagnosis`), the **first step** must be:
   ```bash
   ./scripts/osops.sh precheck
   ```
   (or `cd scripts && ./osops.sh precheck`; run `./scripts/init.sh` once before first use).
2. **Before precheck passes**, do not repeatedly run remote OpenAPI diagnosis commands.
3. If precheck fails, guide users by `error.code`, `data.guidance`, and `agent.findings` from JSON.  
   Do not blindly retry the same remote API call. Re-run precheck after configuration changes.

## 2) Three Requirements for Remote OpenAPI (All Required)

| Requirement | Meaning | Typical setup path |
|------|------|----------------|
| **Identity** | Valid credentials for OpenAPI | **AK/SK**: RAM user + AccessKey; **ECS RAM Role** (recommended on ECS): ECS-trusted role + attached to instance + `aliyun configure --mode EcsRamRole` |
| **Policy** | `AliyunSysomFullAccess` | Grant to **user** (AK path) or **role** (ECS RAM Role path) |
| **Activation + SLR** | SysOM is activated, and service-linked role `AliyunServiceRoleForSysom` exists | Usually activated in [Alinux Console](https://alinux.console.aliyun.com/?source=cosh), where SLR is auto-created. For subaccount SLR permission issues, see [service-linked-role-subaccount.md](./service-linked-role-subaccount.md) |

Detailed auth steps: [authentication.md](./authentication.md).  
InvokeDiagnosis prerequisites (Cloud Assistant, console authorization, etc.): [invoke-diagnosis.md](./invoke-diagnosis.md).

### 2.1 First-time CLI Environment Setup

1. Add full `sysom-diagnosis` directory to workspace (`scripts/`, `references/`, `SKILL.md`).
2. Run once in skill root: `./scripts/init.sh` (install/sync dependencies).
3. Verify entrypoint: `./scripts/osops.sh --help` or `./scripts/osops.sh precheck`.

### 2.2 Agent / Multi-shell Credential Safety (Important)

**Security policy**: never ask users to paste AccessKey/Secret into chat.

Recommended agent flow:

```bash
./scripts/osops.sh configure
./scripts/osops.sh precheck
```

`configure` writes `~/.aliyun/config.json`, so credentials survive isolated shell processes.

In COSH, Bash tool calls are often isolated processes; `export` from one call may not carry to the next.

| Method | Guidance |
|------|------|
| **Recommended for Agent** | Run `./scripts/osops.sh configure` in skill root, then `./scripts/osops.sh precheck` |
| Advanced script-only | In a **single shell process**: `export ... && export ... && ./scripts/osops.sh precheck` |

If interactive input is unavailable (no PTY), enable interactive shell in COSH (`/settings`) or enter `/bash`, then run `configure`.

### 2.3 End-to-end Checklist (Precheck to Deep Diagnosis)

| Step | Action | Notes |
|------|------|------|
| 1 | `./scripts/osops.sh precheck` | Mandatory before first remote capability in a session |
| 2 | If `ok: false` | Follow branches below; do not skip setup |
| 3 | If `ok: true` | Run deep diagnosis (`memory ... --deep-diagnosis`) |
| 4 | Diagnosis still fails | Re-run precheck; read `remediation`; verify target ECS prerequisites in [invoke-diagnosis.md](./invoke-diagnosis.md) |

### 2.4 Precheck Failure Branches (Agent)

- No valid credentials (env + `~/.aliyun/config.json` unavailable): follow **A-K1** or **E-R1**.
- AK exists but no SysOM policy: **A-K2** -> attach `AliyunSysomFullAccess` -> wait for effect -> precheck.
- `error.code == service_not_activated`: **A-K3 / E-R4** -> activate SysOM -> wait 1-3 minutes -> precheck.
- On ECS, `instance-id` reachable but `ram/security-credentials/` is 404: likely role not attached -> attach role + grant policy + configure EcsRamRole -> precheck.
- `ecs_role_name` exists but still fails: likely **E-R3** or policy not effective yet.
- `~/.aliyun/config.json` parse failure: fix JSON (or recreate via `./scripts/osops.sh configure`) -> precheck.

## 3) AK/SK Path: Scenarios and Actions

| Scenario ID | Condition | Agent guidance |
|---------|----------|----------------|
| **A-K1** | No AK / not configured | Create RAM user -> create AK/SK -> attach `AliyunSysomFullAccess` -> configure -> **precheck** |
| **A-K2** | AK exists, policy missing | Attach `AliyunSysomFullAccess` to RAM user -> **precheck** |
| **A-K3** | AK and policy exist, SysOM not activated | Activate SysOM in console -> **precheck** |
| **A-K4** | All ready | `precheck` should pass -> run deep diagnosis |

## 4) ECS RAM Role Path: Scenarios and Actions

| Scenario ID | Condition | Agent guidance |
|---------|----------|----------------|
| **E-R1** | No role / role not attached | Create ECS-trusted role -> attach `AliyunSysomFullAccess` -> attach to instance -> configure EcsRamRole -> **precheck** |
| **E-R2** | Role exists, instance not attached | Attach role in ECS console -> **precheck** |
| **E-R3** | Role attached, policy missing | Grant `AliyunSysomFullAccess` to role -> **precheck** |
| **E-R4** | Identity and policy ready, SysOM not activated | Activate SysOM -> **precheck** |

## 5) How to Read Precheck Output

- `ok: true`: deep diagnosis can proceed (`memory ... --deep-diagnosis`), while still requiring target-side prerequisites in [invoke-diagnosis.md](./invoke-diagnosis.md).
- `ok: false`:
  - `error.code == service_not_activated`: follow **A-K3 / E-R4**.
  - Auth/API failure: follow **A-K1 / A-K2 / E-R1-E-R3**, check `agent.findings` and `data.suggestion`, then [authentication.md](./authentication.md).
  - `data.ecs_role_name` present but failure continues: verify role policy and CLI mode (`EcsRamRole`).

## 6) When Remote Deep Diagnosis Fails

1. Re-run `./scripts/osops.sh precheck`.
2. If still OpenAPI/permission related, follow this guide + [authentication.md](./authentication.md).
3. If instance authorization/distribution fails, complete SysOM diagnosis authorization in SysOM/ECS console. Do not rely on deprecated authorization APIs.

## 7) Common Failure Fields in CLI JSON

- `error.code` (machine-readable)
- `data.guidance` / `data.remediation` (ordered steps, doc pointers)
- `data.precheck_command` (recommended precheck retry command)

## 8) `error.code` Quick Mapping

| `error.code` (examples) | Typical meaning | Suggested order |
|---------------------|----------|--------------|
| `auth_failed` | Invalid credentials or InitialSysom validation failed | fix A-K* / E-R* and [authentication.md](./authentication.md), then precheck |
| `service_not_activated` | SysOM not activated / account not ready | activate in Alinux console -> wait -> precheck |
| permission-related diagnosis errors | one or more of three requirements missing, or target instance not authorized | precheck -> this guide -> invoke-diagnosis |

Always trust current JSON `agent.findings` and `data.remediation` as the highest-priority guidance.

## 9) Activation and Service-Linked Role (Summary)

1. Use primary account or authorized RAM user to activate SysOM in [Alinux Console](https://alinux.console.aliyun.com/?source=cosh). SLR `AliyunServiceRoleForSysom` is usually auto-created.
2. If subaccounts fail due to `ram:CreateServiceLinkedRole`, see [service-linked-role-subaccount.md](./service-linked-role-subaccount.md).
3. Wait 1-3 minutes after activation, then run `./scripts/osops.sh precheck`.
4. If still unactivated, verify the credential account matches the console account used for activation.

## 10) Additional Steps for Repeated Deep-Diagnosis Failures

1. Re-run `./scripts/osops.sh precheck`.
2. Read full stdout JSON (`error`, `data`, `agent.summary`).
3. Cross-check [invoke-diagnosis.md](./invoke-diagnosis.md): region, instance ID, `service_name`, `channel`, Cloud Assistant, and console authorization prerequisites.
4. Complete missing target authorization in console if API explicitly reports authorization issues.
5. Avoid repeating the exact same call with unchanged params under the same error.
