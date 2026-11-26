# Action Authority Matrix

This file is the customer- and agent-facing contract for what this skill may do on a
customer's behalf. **It is governed by `references/action-classes.json`; on any conflict
the JSON wins.** The build gate `check_action_policy.py` (suite tooling archive) re-reads both
and fails if they drift, if a guide-only action has any dispatch call site in `scripts/`,
or if a dispatched consent-write action lacks its cost disclosure.

The rule comes from the customer instruction (2026-11-12): a high-risk action - a restart,
and anything that interrupts service, cannot be undone, or changes a paid spec that needs
a restart - is **never executed for the customer; guidance only**. A configuration-changing
action may be executed **after the customer agrees to that one operation**, and must state
its side effects (for example, a snapshot bills).

## The three classes

- **auto-read** - the action changes nothing (Describe / Get / List / Query / Check). It
  runs without asking. Exception: a read delivered *inside* the customer's instance
  (`RunCommand`) still needs per-operation consent, because it executes in their machine
  and leaves a task record there.
- **consent-write** - the action changes configuration or creates a billable object, and
  the effect is reversible or additive-and-billed. It runs only after the customer agrees
  to that one operation in this turn, with the class obligations printed.
- **guide-only** - the action interrupts a running service, destroys or replaces data or a
  system disk, changes a spec/billing class that needs a restart, or cannot be undone. The
  skill never dispatches it; it explains the effect, the prerequisites, and where the
  customer performs it themselves.

## Obligations (what each class owes the customer)

| obligation | meaning |
|---|---|
| per-operation-consent | one agreement authorises exactly one operation; a prior agreement is not carried forward |
| state-effect | say what changes and what the customer will observe while it happens |
| state-cost | say what the operation bills for, and on what basis |
| state-revert | say how it is undone, or state plainly that it is not undoable |
| rollback-point | before a filesystem- or data-touching change, name the snapshot already taken |
| no-result-claim | never state the effect was achieved unless this run read it back |

## Customer wording templates

- **auto-read (cloud-side)**: no preface needed; the answer cites the read it ran.
- **auto-read (in-guest)**: "This reads the inside of the instance through Cloud Assistant:
  one command, from a frozen list of non-mutating readings, recorded as an execution task in
  your console. Nothing is changed inside. May I run it?"
- **consent-write**: name the operation, its effect, its cost, and how it is undone, then
  ask for that one operation. Example (snapshot): "Creating the snapshot is billable:
  snapshot storage is charged by capacity used, not by the number of snapshots, and it keeps
  accruing until the snapshot is deleted. A running disk may be snapshotted without a
  restart. Shall I create it?"
- **guide-only refusal**: "Guide only, not executed for you: <effect>. You perform this in
  the console (or the OS) when the window suits you; the steps are in the guide, and
  afterwards this check can re-read the result for you." Never name an internal switch.

## Actions by class

### auto-read (1)
| action | api | capability | areas |
|---|---|---|---|
| guest-read-command | RunCommand | dispatched | access-block-layered, console-channel-diagnosis, disk-expand-diagnosis, host-intrusion-cleanup, instance-start-stop-anomaly, instance-state-diagnosis, resource-bottleneck, ssh-connection, web-inaccessible-slow |

### consent-write (3)
| action | api | capability | areas |
|---|---|---|---|
| create-snapshot | CreateSnapshot | dispatched | disk-expand-diagnosis, host-intrusion-cleanup, instance-start-stop-anomaly |
| guest-config-change | RunCommand | not-built | - |
| security-group-write | AuthorizeSecurityGroup | not-built | - |

### guide-only (12)
| action | api | capability | areas |
|---|---|---|---|
| reboot-instance | RebootInstance | never-dispatched | - |
| stop-instance | StopInstance | never-dispatched | - |
| reinit-disk | ReInitDisk | never-dispatched | - |
| replace-system-disk | ReplaceSystemDisk | never-dispatched | - |
| delete-instance | DeleteInstance | never-dispatched | - |
| delete-snapshot | DeleteSnapshot | never-dispatched | - |
| spec-or-billing-change | ModifyInstanceSpec | never-dispatched | - |
| network-spec-change | ModifyInstanceNetworkSpec | never-dispatched | - |
| eip-lifecycle | ReleaseEipAddress | never-dispatched | - |
| redeploy-instance | RedeployInstance | never-dispatched | - |
| install-cloud-assistant | InstallCloudAssistant | never-dispatched | - |
| refund-or-unsubscribe | CancelInstanceForRefund | never-dispatched | - |

## Not built (capability proposals, not shipped legs)

`guest-config-change` (in-guest swap/sysctl/systemctl changes) and `security-group-write`
are recorded as `not-built`: implementing either is a capability project that needs product
sign-off, a snapshot prerequisite, a rollback design, and a new gate. They name no areas and
are never dispatched. `InstallCloudAssistant` exists as an API but needs a restart to
complete, so it is guide-only and is **not** added to the authorization surface.
