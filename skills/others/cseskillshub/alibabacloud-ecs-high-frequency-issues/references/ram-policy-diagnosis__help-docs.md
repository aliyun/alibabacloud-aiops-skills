# Official Documents & Console Entries (verified inventory for this tier)

Every URL below comes from the injected evidence for this tier (help-search
hits or links that support staff actually pasted in the reviewed
conversations). Do NOT cite URLs outside this list; where a topic has no
verified URL, the answer must say so (gap list at the bottom) instead of
pointing at an invented document.

## Identity, authorization and access control (main chain)

| Topic | URL | Used by |
|---|---|---|
| RAM users for ECS access control (standard grant path) | https://help.aliyun.com/zh/ecs/user-guide/control-access-to-resources-by-using-ram-users.md | clusters A/C guidance |
| RAM roles to control access to ECS instances | https://help.aliyun.com/zh/ecs/user-guide/use-a-ram-role-to-control-access-to-ecs-instances.md | cluster D role flow |
| RAM user executing Cloud Assistant commands | https://help.aliyun.com/zh/ecs/user-guide/run-cloud-assistant-commands-as-a-regular-user.md | guest-check channel prerequisites |
| Workbench CLI install & credential configuration | https://help.aliyun.com/zh/ecs/user-guide/install-and-configure-workbench-cli-credentials.md | cluster B (Workbench chain), channel setup |
| How to limit a RAM user to specific ECS instances | https://help.aliyun.com/document_detail/2669110.html | resource-group / instance-scoped grants — pasted by staff in ticket T-EE03C367 |
| RAM user FAQ | https://help.aliyun.com/document_detail/39743.html | cluster A FAQ — pasted by staff in ticket T-EE03C367 |
| RAM console: users page (grant entry) | https://ram.console.aliyun.com/users | manual grant steps (tickets T-169ADF41 / T-2B09C359) |

## Connection & client-identity boundary (handoff targets)

| Topic | URL | Used by |
|---|---|---|
| Security-group quick guide (secure, precise network access) | https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md | security-group area handoff (tickets T-D5229C33 / T-E55C752C patterns) |
| Connect to a Linux instance with a password | https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-1 | OS-user-vs-RAM-user handoff (staff link in ticket T-2B09C359) |
| More remote-connection methods | https://help.aliyun.com/document_detail/71529.html | connection-method handoff (staff link in ticket T-2B09C359) |
| Install a graphical desktop on CentOS (MATE) | https://help.aliyun.com/document_detail/41227.html | graphical-needs handoff (staff link in ticket T-2B09C359) |
| OOS use case: alert-triggered restart of high-CPU ECS | https://help.aliyun.com/zh/oos/use-cases/trigger-restarts-of-ecs-instances-with-high-cpu-utilization-based-on-alerts | after finishing the role grant of ticket T-0217BF77 |
| Images overview | https://help.aliyun.com/zh/ecs/product-overview/images | boot/image area handoff (staff link in ticket T-28ED5673) |

## Standing risk-practice pointers (staff scripts, referenced not executed)

| Topic | URL | Notes |
|---|---|---|
| Create a snapshot | https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot | "snapshot before risky cleanup" — the standing staff script (pasted in ticket T-2B09C359); this skill never performs the action, only relays the pointer |
| Snapshot billing | https://help.aliyun.com/document_detail/56159.html | cost notice accompanying the snapshot advice (ticket T-2B09C359) |
| Alibaba Cloud CLI install | https://help.aliyun.com/document_detail/121541.html | prerequisite of this skill's credential chain |

## Known document gaps for this tier (no injected URL — do not substitute
invented links)

- RAM policy grammar / version reference underpinning the wildcard-Action
  pairing rule (currently backed by ticket T-8FE09114 summary only).
- The managed-policy page of `AliyunECSWorkbenchFullAccess`.
- The official self-service page for deleting a service-linked role
  (mentioned by staff in ticket T-8FA544FE, URL not in the injection).
- BSS / cost-center permission reference for the instance-inventory planning
  case (ticket T-2D30AEF6).
- Resource-group grant scope + mobile-console resource-group switch (only
  indirectly covered by document_detail/2669110 above).

When an answer needs one of these, state the gap and hand to human support
with the concrete decoded evidence (denial text, action token, visibility
result) attached.
