# Image-repair task failures: log anatomy, error codes, exits

## Ground rule: the log is the evidence

The console image-repair pipeline runs **inside the customer's account**:
it provisions a transition VPC, VSwitch and security group, then orders one
pay-as-you-go transition instance, runs a repair script there, and releases
the resources. There is **no verified read-only API to pull repair-task
details or logs** for this scenario, so the pipeline log the customer
pastes (or screenshots of the task page) is the primary evidence. The
entry script's `analyze-log` mode parses it; nothing is ever fetched.

A pasted log line that settles most threads of this axis looks like:

```text
Create transition vpc/vSwitch/securityGroup successfully.
requestId:"019FD9C4-...", api:"CreateInstance",
code:"InvalidAccountStatus.NotEnoughBalance",
info:"Your account does not have enough balance to order postpaid product.".
Failed to prepare transition resources. Start releasing resources...
```

Read three fields out of it, always: the **requestId** (for follow-up),
the **api** at which it failed (localizes the stage), and the **code**
(names the root cause). The `api` value decides the conclusion: a failure
at `CreateInstance` means the flow died while ordering the transition
instance — the repair never touched the image content at all.

## InvalidAccountStatus.NotEnoughBalance

- **Stage**: transition-resource preparation — network lines
  succeeded, the instance order failed, rollback released what existed.
- **Root cause**: ordering postpaid products requires an account balance
  of at least 100 CNY (the repair itself consumes far less). This is an
  account-commercial condition, not an image defect.
- **Conclusion to give**: the backup/image is NOT invalid; the repair
  simply never started against the guest.
- **Exit (manual)**: the customer tops up the balance, then re-triggers
  detection/repair from the console image page. This skill never triggers
  the repair. Top-up itself belongs to the billing axis
  ([handoff.md](handoff.md)).
- **Cost note to state before, not after**: a successful repair runs a
  real (billed) pay-as-you-go instance for its duration; the transition
  resources are released afterwards.

## Task page says one thing, the log says another

Real ticket shape: two repair attempts failed at the balance threshold
while the task-management page displayed a success-looking status. No
verified document explains the task-page status semantics, so the
discipline is fixed:

1. report **both sources verbatim** — the page status and the failing
   log lines with requestId + api + code;
2. state that the error log is the concrete evidence and the page status
   is unexplained for this batch;
3. recommend console/human verification for which one is authoritative.

Never declare "the repair succeeded" from the page alone, and never
invent a mechanism ("the page only records submission") as fact.

## Other codes

`InvalidAccountStatus.NotEnoughBalance` is the only error code whose
semantics were confirmed by ticket evidence in this batch. Any other
literal code from a pasted log is echoed **as-is** with the stage
localization, plus the detect-and-repair doc pointer; the script does not
guess meanings for codes it does not carry:

- <https://help.aliyun.com/zh/ecs/user-guide/detect-custom-images-and-repair.md>

A log whose stages all pass but whose guest script failed moves the axis
to image content — continue with `detection-codes.md` (fstab / agents /
NVMe) and the read-only guest checks.

## "Is my backup invalid?" (the fear behind most of these threads)

A failed detection/repair task does not invalidate an existing custom
image or snapshot: creation status of the image record is read-only
verifiable (`DescribeImages` `Status` / `Progress`, `Available` = the
image itself is fine), and the repair failing at the ordering stage means
the image was never modified. For the *content* defects question (will an
instance booted from it work), route to the detection items and guest
checks. If detection criticals remain after the customer fixed the image,
the loop is: fix manually → rebuild image → re-detect → re-run this skill
on the new report — never an in-place repair by this skill.
