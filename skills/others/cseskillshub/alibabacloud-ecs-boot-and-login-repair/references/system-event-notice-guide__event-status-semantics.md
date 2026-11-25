# Event families, states, and the rules behind each answer

Confidence labels used below:

- `official-doc` - the rule is stated by one of the linked help pages. **The
  pages have not been re-fetched by this build**, so open the link before quoting
  the rule to a customer.
- `support-wording` - the rule is the wording used when these cases were handled
  by Alibaba Cloud support. Reliable in practice, not confirmed against the
  official page.
- `unverified` - a boundary that has to be checked before it is repeated.

Primary pages:

- ECS system event overview:
  `https://help.aliyun.com/zh/ecs/user-guide/overview-of-ecs-system-events.md` (`official-doc`, not re-fetched)
- ECS event explanation page quoted in handled cases:
  `https://help.aliyun.com/document_detail/57052.html` (`official-doc`, not re-fetched)
- Finding and troubleshooting instance issues:
  `https://help.aliyun.com/zh/ecs/user-guide/identify-and-troubleshoot-instance-issues.md` (`official-doc`, not re-fetched)
- Resource reservation events (adjacent family, deliberately separate):
  `https://help.aliyun.com/zh/ecs/user-guide/resource-reservation-event.md` (`official-doc`, not re-fetched)

## 1. The three families this tier covers

| Family | What the customer sees | Root pattern | Who acts |
|---|---|---|---|
| Planned maintenance reboot | A notice that the instance must be rebooted because of system maintenance, with an automatic execution time | The platform found a potential hardware or software fault risk on the underlying host and wants the instance moved to a healthy host at a chosen moment | The customer reboots or schedules; the system executes at the deadline if nobody acts |
| Unplanned downtime migration | The instance restarted on its own, sometimes after a service interruption | An actual host fault already occurred, so the platform migrated the instance and rebooted it | Nothing to approve; the customer verifies the workload and enables auto-start |
| Performance or capacity alert carrying an event code | An alert such as `Instance:StoragePerformanceReachLimit` | The named subsystem reached its configured limit; the code describes the subsystem, not the network | The customer reads the matching metric |

Region or zone closure notices are recognised here but only as far as interpreting the
notice; executing the migration and any commercial follow-up belong elsewhere
(see [boundary-handoff.md](boundary-handoff.md)).

## 2. State semantics

`support-wording`. These are the states seen in the handled cases; the complete
official enumeration and its exact console labels are **not verified in this
build**. Treat an unlisted label as unknown and say so.

| Console state | What it means | Does the customer still act |
|---|---|---|
| Scheduled / pending | The event exists and waits - either for the customer, or for the automatic execution time | Yes, or accept the automatic execution |
| Avoided | The customer rebooted or migrated before the deadline, so the exposure was removed by the customer | No |
| Canceled | The platform withdrew the event: the risk was repaired or mitigated first, or the maintenance task finished or changed | No |
| Executed | The platform carried out the action itself at the automatic time | No, but verify the workload |

The two confusions worth untangling every time:

- **Canceled is not a contradiction.** A notice followed by a canceled event means
  the reason for the notice went away before execution. It does not mean the
  notice was wrong, and it does not mean the instance is now unprotected.
- **Avoided is not a failure.** A customer who reboots by hand sees `Avoided`,
  never `Executed`, because `Executed` describes an action the platform ran.

State display can lag the reboot by some minutes, so a stale row after a manual
reboot is a refresh question, not evidence that the risk returned.

## 3. Deadline rules

`support-wording` for the mechanism, `official-doc` for the exact times:

- The notice carries an automatic execution time. If the customer does nothing,
  that is when the instance is rebooted.
- There is **no self-service entry to push the automatic time out**; where a
  customer asked for a different day, the request was handled by a ticket rather
  than by the console. Say this plainly instead of promising a reschedule.
- A customer-initiated reboot inside the window is always allowed; recommend a
  low-traffic moment, a graceful stop of the application, and a snapshot first
  when the workload matters.
- A maintenance event is a one-off. A repeating weekly or daily restart pattern
  points at the customer's own auto start/stop configuration, which is a separate
  feature and should not be described as maintenance.

## 4. Data, IP, and the difference between reboot and redeploy

| Question | Answer | Confidence |
|---|---|---|
| Does a maintenance reboot erase my disk data? | No. A reboot does not re-deploy the instance and does not clear cloud disks. Running processes do stop, so flush unwritten data and stop the application gracefully. | `support-wording` + `official-doc` |
| Does data survive a redeployment class event? | Locally attached disks are re-initialised by a redeployment, so data on local disks really is lost; back it up before the deadline. Cloud disks of the instance are not cleared by a plain reboot. Confirm the wording on the event overview page before answering. | `unverified` in this build |
| Does my IP change? | A maintenance reboot keeps the private IP and the public IP of the instance. | `support-wording` |
| Does a migration to another region keep the address? | No. A new instance in another region has new addresses, so DNS and allow-lists must be updated. | `official-doc` for the migration steps, `support-wording` for the address consequence |
| Will my service come back by itself? | Only if the application starts on boot. That is the practical follow-up after any unplanned reboot. | `support-wording` |

## 5. What the event feed does not tell you

Say these are absent rather than inventing them:

- **Which disk** is saturated, and at what percentage. An event that reports a
  storage performance limit names the instance and the subsystem only; per-disk
  and per-process detail has to come from block storage metrics or from inside
  the instance.
- **Host health, the physical machine in use, and the migration destination.** The
  platform does not expose these to customers through any supported read, and the
  console cannot show them either. If a customer wants them verified, that is a
  ticket item handled by a human.
- **Operation history inside the guest.** If the platform side has no event for
  the moment the customer describes, that is reported as a negative result on the
  platform side only; the cause may be inside the operating system, and reading it
  is the customer's own action.
- **Progress of anything handled off-platform**: a reschedule request, a
  compensation claim, a commercial approval.

## 6. Auto-fill and disclosure

Any region, page size, or batch size the script picked on its own is echoed in
the report under `Declared parameters and assumptions`. Repeat those in the
answer, because a wrong region is the most common way a query returns nothing.
