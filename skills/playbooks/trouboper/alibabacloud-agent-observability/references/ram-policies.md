# RAM Permission List (Read-Only)

This skill only reads Agent trace data (LoongSuit side via CMS 2.0 UModel `GetEntityStoreData`, eBPF side via SLS
`GetLogs`), no write permissions are needed. Data source bindings (`--project` / `--workspace`) **can only be provided by the user**, the skill has
no auto-discovery mechanism, therefore no AgentLoop permissions are needed.

## Required Permissions

### LoongSuit Source (CMS 2.0 Workspace Traces)

| Action | Resource | Purpose |
|---|---|---|
| `cms:GetEntityStoreData` | `*` | Query `.trace_set(domain=apm, name=apm.trace.common)` in SPL umodel mode to get GenAI span details |
| `cms:ListWorkspaces` | `*` | Verify that the workspace bound by `--workspace` actually exists in this region (`preflight.py`'s `cms_workspace` check item) |

> Call pattern: `aliyun cms get-entity-store-data --api-version 2024-03-30 --workspace <name> --from <ts>
> --to <ts> --query <SPL> --region <region>`, requires the `aliyun-cli-cms` plugin (multi-version API support).
> `--workspace` is a real query parameter, not a label. See the CMS UModel query reference for details.

### eBPF Source (SLS ebpf-event)

| Action | Resource | Purpose |
|---|---|---|
| `log:GetLogStoreLogs` | `acs:log:*:*:project/<SLS_PROJECT>/logstore/<LOGSTORE>` | GetLogs raw search for runtime facts |
| `log:GetIndex` | `acs:log:*:*:project/<SLS_PROJECT>/logstore/<LOGSTORE>` | Confirm logstore index is available |
| `log:ListLogStores` | `acs:log:*:*:project/<SLS_PROJECT>` | List logstores: verify binding exists + probe for `ebpf-event` |
| `log:GetProject` | `acs:log:*:*:project/<SLS_PROJECT>` | Verify the bound project exists |

> eBPF side only does **raw search**, no server-side SQL aggregation — runtime fields are not indexed, `group by` will be rejected. See
> the eBPF field dictionary.

## Reference Policy (Minimal Read-Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["cms:GetEntityStoreData", "cms:ListWorkspaces"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["log:GetLogStoreLogs", "log:GetIndex"],
      "Resource": "acs:log:*:*:project/<SLS_PROJECT>/logstore/*"
    },
    {
      "Effect": "Allow",
      "Action": ["log:ListLogStores", "log:GetProject"],
      "Resource": "acs:log:*:*:project/<SLS_PROJECT>"
    }
  ]
}
```

- Replace `<SLS_PROJECT>` with the binding value for `--project` (the project storing `ebpf-event`).
- When using only the LoongSuit source, the two SLS Statements can be removed; when using only the eBPF source, the CMS Statement can be removed.
  But **binding at least one of the two datasets** is a runtime prerequisite, so normally both groups are needed.

## Permissions Explicitly Not Requested

- **`CreateThread` / `CreateChat`**: CMS's `cms_natural_language_query` (natural language query) requires them,
  which are write permissions. This skill **does not use** that API, only uses structured SPL queries, therefore does not request them.
- **Any CMS / SLS write permissions**: This skill is read-only throughout. SPL pipe commands that initiate external or model calls
  (`http-call` / `llm-call` / `agentic-call` / `embedding` / `entity-call` / `prom-call` /
  `graph-call`) are intercepted client-side by `cms_trace.SPL_DENY`, does not rely on server-side permission enforcement.
- **ARMS permissions**: ARMS dependency has been completely removed (`arms:SearchTracesByPage` / `arms:GetMultipleTrace` are no longer needed).

## Cross-Account AssumeRole Notes

When credential type is `RamRoleArn` / `ChainableRamRoleArn`: **the above permissions must be granted to the assumed role, not the caller**;
and the role's trust policy must allow the current caller to assume it. `preflight.py`'s `credentials` check item identifies this type and
provides a hint.

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read the RAM policies reference to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
