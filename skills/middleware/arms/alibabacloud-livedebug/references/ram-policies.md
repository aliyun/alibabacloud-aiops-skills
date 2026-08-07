# RAM Policy Reference

> Required RAM Actions for the **Live-Debug ServiceTask** skill.
> Derived solely from the OpenAPI calls this skill actually issues:
> `aliyun cms2 apm service-task create/list/get/delete` (CMS `2024-03-30`,
> `ServiceTaskController`), the discovery/resolution reads `aliyun cms2 workspace list`
> and `aliyun cms2 apm service list`, the optional temporary-service lifecycle
> `aliyun cms2 apm service create/delete`, and `aliyun sls get-logs-v2` (SLS log query).
> API granularity only - **no `*` wildcard in Action lists**.
>
> Replace `<accountId>`, `<region>`, `<project>`, and `<logstore>` with your values.

## Scope of This Skill

Live-Debug builds and manages ServiceTask diagnostics (probes and Java commands)
through the CMS OpenAPI, and reads capture results from SLS. To locate the target it
may also **read** workspaces (`workspace list`) and services (`apm service list`), and
when a workflow requires a temporary service entity (e.g. eval / sandbox rehearsals)
it may register and clean one up (`apm service create` / `delete`). It does **not**
onboard APM/agents, install cluster addons, or mutate service configurations - those
Actions are intentionally **not** requested here.

| Cloud service | APIs used | Purpose |
|---------------|-----------|---------|
| CMS (2024-03-30) | `apm service-task create` / `list` / `get` / `delete` | Create, list, get, and delete Live-Debug tasks (probes & commands) |
| CMS (2024-03-30) | `workspace list` | Discover an existing workspace when none is given |
| CMS (2024-03-30) | `apm service list` | Resolve `serviceId` by service name; verify cleanup |
| CMS (2024-03-30) | `apm service create` / `delete` (optional) | Register / clean up a temporary service entity when the workflow requires one |
| SLS | `get-logs-v2` | Query task installation status and capture results |

> The scripts under `scripts/live-debug/` call only the ServiceTask and SLS APIs; the
> workspace/service reads and the optional service lifecycle are issued directly via
> `aliyun cms2` per SKILL.md. No STS, Container Service, `apm configuration`,
> `integration addon`, or `entity query` Actions are used by this skill.

---

## 1. CMS Actions (CMS 2024-03-30)

| CLI subcommand | RAM Action | Kind |
|----------------|------------|------|
| `apm service-task create` | `cms:CreateServiceTask` | write |
| `apm service-task list` | `cms:ListServiceTask` | read |
| `apm service-task get` | `cms:GetServiceTask` | read |
| `apm service-task delete` | `cms:DeleteServiceTask` | write |
| `workspace list` | `cms:ListWorkspaces` | read (workspace discovery) |
| `apm service list` | `cms:ListServices` | read (serviceId resolution / cleanup verification) |
| `apm service create` | `cms:CreateService` | write (**optional** - temporary service lifecycle only) |
| `apm service delete` | `cms:DeleteService` | write (**optional** - temporary service lifecycle only) |

> Action names follow the controller operation IDs under the `cms` RAM product code.
> Confirm the exact strings in the RAM console's policy editor for CloudMonitor 2.0
> before applying in production. Grant `cms:CreateService` / `cms:DeleteService` only
> when the workflow registers its own temporary service (as the eval scenarios do);
> diagnosing an already-onboarded service does not need them.

## 2. SLS Query Action

| CLI subcommand | RAM Action |
|----------------|------------|
| `sls get-logs-v2` | `log:GetLogStoreLogs` |

> Bind the SLS Action to the specific project/logstore that stores Live-Debug
> results (see the resource ARN in the examples below) rather than `*`.

---

## Minimal Authorization Examples

### Read-only (inspect existing tasks + query results)

Sufficient when you only list/get already-dispatched tasks and read their capture
results, without creating or deleting probes. Includes the workspace/service reads
used to locate the target.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:ListWorkspaces",
        "cms:ListServices",
        "cms:ListServiceTask",
        "cms:GetServiceTask"
      ],
      "Resource": "acs:cms:<region>:<accountId>:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs"
      ],
      "Resource": "acs:log:<region>:<accountId>:project/<project>/logstore/<logstore>"
    }
  ]
}
```

### Full diagnostics (create / delete probes + query results)

The complete Live-Debug workflow additionally needs create and delete on ServiceTask.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:ListWorkspaces",
        "cms:ListServices",
        "cms:CreateServiceTask",
        "cms:ListServiceTask",
        "cms:GetServiceTask",
        "cms:DeleteServiceTask"
      ],
      "Resource": "acs:cms:<region>:<accountId>:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "log:GetLogStoreLogs"
      ],
      "Resource": "acs:log:<region>:<accountId>:project/<project>/logstore/<logstore>"
    }
  ]
}
```

> `cms:CreateServiceTask` and `cms:DeleteServiceTask` are write Actions - grant them
> only to identities that need to install or remove probes. For read/query-only
> operators, use the read-only policy above.

### Temporary service lifecycle (optional add-on)

Only needed when the workflow registers its **own temporary service entity** and
cleans it up afterwards (e.g. the eval scenarios' `apm service create` / `delete`
rehearsals). Diagnosing an already-onboarded service does not need this block -
omit it in that case.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:CreateService",
        "cms:DeleteService"
      ],
      "Resource": "acs:cms:<region>:<accountId>:*"
    }
  ]
}
```

> Attach this add-on **in addition to** the full-diagnostics policy, and detach it
> once temporary-service rehearsals are finished.
