# ECS Spec-Change & Purchase-Feasibility Guide

Read-only knowledge for the four ticket scenarios this skill covers. The entry
script `scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py` gathers the evidence; this guide explains
how to interpret it and what manual guidance to give. This skill never changes a
spec, restarts an instance, or places an order.

## Scope (four scenarios, one tier)

| Scenario | Capability | Read-only evidence |
|---|---|---|
| Instance spec change (upgrade / downgrade) | A | current spec/status/charge type + the target types it can change to |
| Resource quota / quantity limit | C | account-level attributes + Quotas Center pointer |
| Spec change did not take effect / needs restart | A + D | authoritative control-plane InstanceType + restart rule |
| Purchase / create instance failed (out of stock) | B | availability of the target type in the zone |

Out of scope (state the boundary and hand off): actually performing the change,
renewal/pricing negotiation, refunds, cross-zone or cross-region migration, disk
expansion, and any write action.

## Spec-change feasibility (capability A)

Decision tree:

1. Confirm the instance exists in the given region (`DescribeInstances`). A wrong
   `--region` is the most common reason an instance is "not found"; the credential's
   account must own the instance.
2. Read the current `InstanceType`, `Status`, and `InstanceChargeType`.
3. Query the changeable targets (`DescribeResourcesModification`,
   `DestinationResource=InstanceType`, `OperationType=Upgrade` or `Downgrade`,
   `ResourceId=<instance-id>`).
4. Interpret:
   - **Feasible targets returned** -> the change is possible; list a few targets and
     note the charge-type rule below.
   - **No feasible target** -> the change is blocked for this instance/direction.
     Common causes: the instance family does not support the requested direction,
     the instance is in a state that forbids the change, or the target has no stock.
   - **A specific `--target-instance-type` was asked** -> report whether it is in the
     feasible list (`target_feasible`).

Charge-type rule:

- **Pay-as-you-go (PostPaid)**: most spec changes require the instance to be
  **Stopped** first, then started again; the new spec bills from the next start. A
  change attempted while `Running` returns `IncorrectInstanceStatus`.
- **Subscription (PrePaid)**: an upgrade follows the upgrade order flow and the
  instance is restarted during the change; a downgrade can be restricted by the
  discount window. Plan a maintenance window.

## Spec change did not take effect (capability D)

- The control-plane `InstanceType` from `DescribeInstances` is authoritative for what
  was actually changed. If the OS still shows the old vCPU/memory, the change has not
  been applied yet -- it takes effect only after the restart/order completion above.
- Confirm inside the OS with the system profiler after the restart; do not conclude
  "the change failed" from a pre-restart reading.
- If `InstanceType` already shows the new value but the OS does not, the instance has
  not been rebooted since the change.

## Stock / purchase feasibility (capability B)

- `DescribeAvailableResource` (`DestinationResource=InstanceType`, `RegionId`,
  `InstanceType`, optional `ZoneId`) reports whether the target type is available in
  the scope.
- **SoldOut / no stock** maps to the customer-visible error `OperationDenied.NoStock`:
  the purchase or the change to that target cannot be fulfilled right now. Guidance:
  try another zone in the same region, another type in the same family, or a different
  charge type; stock refills over time. This skill only reports availability.
- Purchase/create failures are dominated by stock and by account quota / real-name
  limits, not by the order UI. Check availability before concluding a purchase should
  work.

## Resource quota / limits (capability C)

- `DescribeAccountAttributes` (`RegionId`) returns account-level attributes and limits
  visible to the credential. Report what is returned; do not invent attribute values.
- The **per-instance-type purchase quota** lives in the Quotas Center / ECS instance
  quota console. When a create fails with a quota/limit message, point the user there
  to request a quota increase (a manual action outside this read-only skill).

## Error-code reference (customer-visible strings)

| Error code | Meaning | Read-only guidance |
|---|---|---|
| `OperationDenied.NoStock` | Target type/zone has no stock (sold out) | Try another zone/type/charge type; stock refills over time |
| `StoragePerformanceReachLimit` | A disk / performance-level ceiling was reached for the target config | Choose a target within the allowed performance level / family limits |
| `IncorrectInstanceStatus` | Instance state forbids the change (e.g. Running pay-as-you-go) | Stop the instance first per the charge-type rule, then retry (manual) |
| `InvalidInstanceId.NotFound` | Instance id not found in the region for this credential | Verify the instance id AND the region; the account must own it |
| `OperationDenied` | Generic denial for the current state/account | Read the returned Message; common causes: in-progress order, unpaid renewal, change-window restriction |

## Read-only boundary

Every conclusion is grounded in the API evidence above. Any spec change, restart,
stop/start, quota increase, or purchase is a **manual action the user performs in the
console**. On a permission failure, report the missing action using the literals
`NoPermission` / `ImplicitDeny` and point to `references/ram-policies.md`; never claim
a change was applied.
