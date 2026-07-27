# Required RAM Permissions

This document declares all RAM permissions required by the Workbench CLI, in `{Product}:{Action}` format.

## Core Permissions

| Permission | Description |
| --- | --- |
| `ecs-workbench:LoginECSInstance` | Establish a session to an ECS instance via Workbench (required for exec, upload, download) |
| `ecs-workbench:ChatMessages` | Send and receive messages over the Workbench session channel (command I/O, file transfer data) |

## ECS Permissions

| Permission | Description |
| --- | --- |
| `ecs:DescribeInstances` | List and query ECS instance metadata (required for `workbench list ecs`) |
| `ecs:DescribeCloudAssistantStatus` | Check Cloud Assistant agent status on target instance (connectivity pre-check) |
| `ecs:StartTerminalSession` | Initiate a terminal session to the instance (underlying transport for exec/transfer) |

## Service-Linked Role

| Permission | Description | Condition |
| --- | --- | --- |
| `ram:CreateServiceLinkedRole` | Create the Workbench service-linked role on first use (one-time setup) | `ram:ServiceName` equals `workbench.ecs.aliyuncs.com` |

## Notes

- All permissions above are **required** for full CLI functionality.
- To restrict access to specific instances, replace wildcard `Resource: "*"` with instance ARNs:
  - `ecs-workbench:LoginECSInstance`: `acs:ecs:{region}:{account-id}:ecs/{instance-id}`
  - `ecs:*` actions: `acs:ecs:{region}:{account-id}:instance/{instance-id}`
- See `SKILL.md § RAM Permissions` for the complete JSON policy document ready for attachment.
