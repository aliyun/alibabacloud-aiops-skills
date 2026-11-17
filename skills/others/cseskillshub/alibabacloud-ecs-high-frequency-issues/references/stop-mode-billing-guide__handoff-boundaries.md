# Boundaries, handoffs, and what to say when data is missing

The rule for this skill: answer the stop-mode and stopped-billing question, name the
rule, show the evidence, and hand over everything else. An honest handoff is a better
answer than a confident guess.

## 1. Hard boundaries

This skill never:

- runs or drafts a lifecycle action for a resource: no stopping, starting, restarting,
  converting a billing method, reassigning an address, or removing an instance, and no
  command for the customer to paste that performs one of those;
- executes anything inside an instance, not even a read-only command such as a disk
  usage query;
- performs commercial or approval work: refunds, coupons, arrears handling, invoices,
  filing changes, address recovery;
- reports a value it did not read. In particular the stop-mode marker is not read back
  here, so no answer may claim the mode was confirmed.

Every action-shaped request ends as: steps for the customer, consequences disclosed,
then a read-only re-check by this skill.

## 2. Recognise and hand off

| Customer symptom | Belongs to | Say this |
|---|---|---|
| Fixed public address, address conversion, a released address that must come back, filing record affected | EIP and address topics | "The address was released with the compute, which is the rule of this mode. Keeping a fixed address is a separate topic, and this skill cannot restore an address. Here is the rule; the operation belongs to the address and filing topics." |
| Snapshot, image creation, restore, or a slow image build | Snapshot and image topics | "Your stop is not the reason the image job is slow; that belongs to the snapshot and image topic. The rule that stays here is that disk data survives economical stop." |
| Port unreachable, connection timeout, security group, routing | Network and public-access diagnosis, for example `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` | "Reachability after the restart is a network diagnosis, not a billing question. This skill confirms the power state and the address change only." |
| Spot or pre-emptible instance reclaimed, interruption notices | Spot instance topic | "Interruption rules belong to the spot topic. The part that overlaps with stopping is data retention, and that answer is: disks survive economical stop, restart can be blocked by stock." |
| Scheduled or automatic start and stop | Operation Orchestration Service or CloudMonitor | "Economical stop has no scheduler; it never fires on a timer. Building a scheduled start and stop belongs to those services." |
| Refund, coupon, arrears, invoice, disputed charge | Billing account topics and human support | "Charges already consumed are settled by the billing process, not by this assistant. I can give you the rule and the bill page; the dispute goes to a human." |
| Guest-level questions: which process used memory, which file grew | In-guest diagnostics | "I do not run commands inside your instance. You can check it yourself, and I can keep answering what the stop mode does to billing." |

## 3. When the read comes back empty or refused

Use the shape, not a paraphrase of the tool output:

- Nothing returned: *"The instance is not visible to this credential in this region, so
  I cannot state anything about it. Confirm the region and the account, or send the
  instance id from the console page. An empty answer here is not evidence that the
  instance is gone."*
- Permission refused (`NoPermission` or `ImplicitDeny`): *"I am missing the read
  permission named in the output. The minimal policy is in
  `references/ram-policies.md`; attach that read action and I will re-run the same
  query."*
- Value not modelled by any read here (mode marker, billed amount, address history):
  *"That value is not obtainable from the read-only queries this skill uses. Open
  <the page named in the rule reference> or send a screenshot, and I will continue
  from what the page shows."*

Never fill a gap from general knowledge while implying it was read.

## 4. Disclosure duty on every guided step

Because this skill does not act, its obligation moves to the moment it hands over
steps: each guided action carries its own consequence in the same answer.

| Guided action | Consequence that must appear in the same message |
|---|---|
| Stop in economical mode | Disks keep charging; the system-assigned address is released; the next start needs stock |
| Convert the billing method | A change the customer performs; pricing and address behaviour change with it |
| Remove the instance | Ends all instance charging and destroys the data; back up first, recovery is not possible afterwards |
| Change type or zone to escape a sold-out failure | Addresses and latencies can change; the customer performs it and this skill re-reads the state |

## 5. Report tail

Close every answer with the script's own tail, unedited:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <manual guidance only>
```

`DEGRADED` means at least one needed fact is missing; the answer must then carry the
matching limitation from section 3 instead of a conclusion.
