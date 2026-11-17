# Host Events, Maintenance Window and SLA Claim (Cluster A)

Rule-based answers for the host-driven system events that dominate this tier, plus
the maintenance-window self-service steps and the availability-compensation (SLA)
process. The event explanations are knowledge; the entry script additionally reads
the instance's own event record with the read-only
`DescribeInstanceHistoryEvents` API, so an explanation is anchored on the type and
lifecycle status the platform actually recorded.

Verification date for the rules below: 2026-08 (per the tier requirements
document). Event type names and their `InstanceEventType.N` enumeration were
re-verified against `aliyun ecs describe-instance-history-events --help` (CLI 3.4.5)
in 2026-10. Event types, instance-family classification and SLA terms are
version-sensitive; re-verify against the official Alibaba Cloud Help Center before
publishing.

## The reboot event types

ECS surfaces host-driven reboots as instance system events. The two that dominate
the reboot tickets are:

### SystemMaintenance.Reboot (planned)

- Meaning: Alibaba Cloud detected a POTENTIAL software/hardware risk on the
  underlying host of the instance and scheduled a planned maintenance reboot.
- Notification timing: the event notification is normally sent 24 to 48 hours
  before execution.
- The notified time is a WINDOW, not a hard deadline: within that window the
  customer may reboot the instance themselves at a low-traffic time. During the
  maintenance the instance is migrated to a healthy host.
- Common misconception: customers read this as an "unplanned forced reboot". It
  is a PLANNED event with a self-service window.

### SystemFailure.Reboot (unexpected)

- Meaning: the underlying host suffered an UNEXPECTED software/hardware failure,
  and the system force-rebooted the instance to recover it.
- Recovery: the reboot usually completes within 2 to 5 minutes.
- Typical notification wording quoted by customers: the instance was rebooted to
  recover from an unexpected host software/hardware failure; the reboot usually
  finishes in a few minutes.
- Common misconception: customers expect the platform to prevent all failures. An
  unexpected host failure cannot be fully prevented; impact is reduced with a
  maintenance window, event subscriptions, redundancy and backups.

## The redeploy and faulty-local-disk event types

A reboot is not the only host event. These variants carry a different customer
action and must not be answered with the reboot wording:

### SystemMaintenance.Redeploy / SystemFailure.Redeploy (host swap)

- Meaning: the host needs maintenance that a reboot cannot cover (planned), or the
  host failed in a way a reboot cannot recover from (unexpected), so the instance
  must be REDEPLOYED onto another physical host.
- Customer action: self-service. Redeploy from the ECS console event entry, or with
  the `RedeployInstance` operation. Prerequisites: the instance is Running or
  Stopped, it is NOT hosted on a Dedicated Host, it carries no security lock, and
  the account / instance is not in arrears past expiry.
- Risk: the redeploy restarts the instance - in-memory data is lost and local disks
  may be re-initialized. Back up first.
- If the event is still `Scheduled`, the customer can pick a low-traffic moment
  inside the notified window; waiting does not repair the failed host.

### SystemMaintenance.IsolateErrorDisk / SystemMaintenance.ReInitErrorDisk

- Meaning: the platform found a faulty LOCAL disk on the host, isolates it
  (planned maintenance), then re-initializes it so the host returns to a healthy
  state. Local-disk instances only; cloud disks are not affected.
- Customer action: treat the notification as a data-preservation deadline. Copy any
  data still needed off the affected local disk before the notified window - the
  re-initialization ERASES that disk.

## What this skill can and cannot confirm

- CAN (read-only): read the instance's own event record with
  `DescribeInstanceHistoryEvents` - event type, lifecycle status
  (Scheduled / Avoided / Executing / Executed / Canceled / Failed / Inquiring),
  publish time, planned `NotBefore` time and finish time - and explain the trigger
  mechanism, the recovery expectation, the notification timing and the
  self-service steps for that event type. `DescribeDedicatedHosts` additionally
  gives the usage status of a Dedicated Host the instance reports (Available /
  UnderAssessment / PermanentFailure).
- NOT AVAILABLE: whether a host is about to fail, and any engineering-internal
  record beyond the event itself. An empty event record does not prove the host was
  healthy - it only means no matching event is visible under this account and
  region. Never state "the host failure has been confirmed / ruled out" beyond what
  the event record and the host status actually show. When the event record is
  missing (no permission, or nothing recorded), the ECS console event / message
  page is the customer-side source of truth and screenshots can be interpreted
  against these rules.

## Maintenance-window self-service steps (customer performs)

1. Configure a planned maintenance window in the ECS console so reboots land in a
   low-traffic period.
2. Subscribe to instance event notifications so SystemMaintenance.Reboot /
   SystemFailure.Reboot messages arrive in advance.
3. Keep regular data backups (for example snapshots; note snapshots are a paid
   feature).
4. For critical workloads, use multi-instance / multi-zone redundancy.

These are guidance steps only. This skill lists them and never applies them.

## Availability compensation (SLA) process

- Compensation is APPLICATION-BASED, not automatic. The platform does not pay out
  proactively.
- Under the ECS service-level agreement in effect since 2018-02-01, a customer may
  apply for compensation for an instance that did not meet the committed
  availability AFTER the 5th business day of each month, for the previous month.
- Applying does NOT guarantee approval; the final decision is made by a human
  reviewer. "Can apply" is not "will be approved".
- Self-service claim entry (from the tier evidence; re-verify before publishing):
  https://usercenter2.aliyun.com/sla/availabilityhome
- This skill only explains the conditions and points to the entry; it never
  submits a claim, promises a payout, or performs any commercial / approval
  action. Compensation disputes are handed off to a human specialist.

## Reboot risk notice (when a reboot is part of the customer's own action)

When the guidance involves the customer rebooting an instance themselves (inside
the maintenance window, or a forced reboot to recover an unresponsive instance),
always give the three-point risk notice and let the customer execute it:

1. Do it in a low-traffic period.
2. Stop applications and let data flush to disk first.
3. Create a snapshot backup first (snapshots are a paid feature).

This skill never claims a reboot was performed on the customer's behalf.

## Sources

- ECS instance event / system-event notification documentation (Alibaba Cloud
  Help Center; exact URL re-verified before publishing).
- ECS service-level agreement and the SLA claim portal above.
- Real support tickets in this tier (planned-maintenance explanation, the
  24-48h notification window, the self-service reboot window, and the
  application-based SLA process).
