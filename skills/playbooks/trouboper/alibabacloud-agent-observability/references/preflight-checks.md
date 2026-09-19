# Preflight Seven Checks: Details and Remediation

`scripts/preflight.py` validates the environment in one pass before any queries. **Configuration checks only, no data checks**: there are no time window parameters
and no data existence probes — whether a window has data is surfaced by the analysis scripts' `totals` / `genai_index_coverage`. Preflight depends only on read-only interfaces of the SLS and CMS products (the skill has no auto-discovery mechanism).

```bash
SKILL_SESSION_ID={session-id} python3 scripts/preflight.py --region <region> \
  [--project <SLS Project>] [--workspace <CMS workspace>] [--logstore <name>] \
  [--strict] [--format json|yaml]
```

## Check Items

| # | id | Command | Determination | Remediation on Failure/Warning |
|---|---|---|---|---|
| 1 | `cli_version` | `aliyun version` (local) | Parse version number, tuple comparison >= `3.3.3`; if parsing fails then `warn` | `aliyun upgrade` (CLI >= 3.3.5) or initial install via official script |
| 2 | `plugins` | `aliyun plugin list` (local) | Must contain `aliyun-cli-sls` / `aliyun-cli-cms`; report each as `{name, version, installed}` | `aliyun configure set --auto-plugin-install true` then `aliyun plugin install --names <missing items>` |
| 3 | `credentials` | `aliyun configure list` (local) | Parse profile table -> `{profile, credential_type, valid, region}`; no profile or no `valid` profile = `fail`; STS/RamRoleArn/unrecognized types = `warn` with explanation | See "Credentials & STS" below |
| 4 | `bindings` | -- (parameter validation only) | `--region` present; `--project` / `--workspace` **at least one**. Both missing = `fail`; only one missing = `warn` | Ask the user for the names; if they cannot provide them, explain the console navigation path in text — **do not guess or compose resource names** |
| 5 | `sls_project` | `aliyun sls list-log-stores` (with UA) | Project is reachable; `ProjectNotExist`/permission failure = `fail` | Verify project name and `--region`; on permission failure, grant `log:ListLogStores` |
| 6 | `ebpf_logstore` | (reuses response from 5) | `ebpf-event` (or `--logstore` specified name) is in the logstore list | Verify project; confirm eBPF collector is installed; or use `--logstore` to override |
| 7 | `cms_workspace` | `aliyun cms list-workspaces --api-version 2024-03-30` (with UA) | The workspace **exists in that region** (real existence check), and `status=Normal`; non-existent = `fail`; abnormal status = `warn` | Verify workspace name (console label: Cloud Monitor 2.0 Workspace); on permission failure, grant `cms:ListWorkspaces`; **no auto-discovery mechanism; do not guess or compose names** |

## Semantics of `skipped`

Checks for the unbound side are set to **`skipped`**, with `detail.reason` explaining why (no `--project` -> skip 5/6;
no `--workspace` -> skip 7). **Skipped is not failure** — binding only one side is a valid configuration; analysis runs will automatically narrow to the bound source and report the other side as a gap.

## Credentials & STS

`credentials` only outputs the credential **type prefix**, never the credential value (output always has `credential_masked: true`;
json/yaml detail lines note "credential values masked"). Recognized types:

| Type | Meaning and Notes |
|---|---|
| `AK` | Long-lived AccessKey. Permissions must be granted to the RAM user/root account itself |
| `STS` | Temporary credentials, **they expire** (expiration manifests as `InvalidSecurityToken.Expired`); must be reconfigured outside the session; do not ask for or paste credentials within the session |
| `RamRoleArn` / `ChainableRamRoleArn` | Cross-account AssumeRole. **The role that needs permissions is the assumed role, not the caller**; the role's trust policy must allow the current caller to assume it |
| `EcsRamRole` / `CredentialsURI` | Automatically obtained from the instance or external credential source; no manual configuration needed |
| Others | Reported as-is with `credential_recognised: false` — **no guessing, no fabrication** |

Any "no valid profile" situation must **STOP**: ask the user to configure credentials outside the session, then come back and re-run. Never ask for AK/SK.

## Output and Exit Codes

```json
{
  "skill": "alibabacloud-agent-observability",
  "checked_at": 1789296252,
  "region": "cn-hangzhou",
  "status": "ok",
  "binding": {"region": "...", "project": "...", "workspace": "...",
              "sources_available": ["ebpf", "loongsuit"], "sources_missing": []},
  "checks": [{"id": "cli_version", "title": "Aliyun CLI Version", "status": "ok",
              "detail": {...},
              "evidence": {"command": "aliyun version", "cloud_api": false,
                           "user_agent": false},
              "fix": null}],
  "summary": {"ok": 7, "warn": 0, "fail": 0, "skipped": 0},
  "notes": [...],
  "cache": {...}
}
```

- `status` in `ok` / `warn` / `fail` / `skipped`; overall status takes the most severe across all check items.
- **Exit codes**: `ok` / `warn` -> 0; `--strict` with `fail` present -> 2; hard errors (missing `--region`, `aliyun` not in
  PATH) -> `ObsError` -> 2.
- `evidence.cloud_api` / `user_agent` indicate whether this item actually made a cloud API call — useful for auditing "which checks produced cloud calls".
  Only items 5/6/7 are cloud calls; the rest are local commands.

## When to Run

- After Step 0 clarification of bindings, before Step 1 any queries (see SKILL.md section 8 Step 0.5).
- After changing bindings, changing region, or any command reporting permission/resource-not-found errors, re-run preflight first to identify which item broke, then fix parameters.
- During iterative analysis, **no need to re-run repeatedly**: it does not check data; re-running just repeats the same configuration validation (the cloud call portion uses cache).
