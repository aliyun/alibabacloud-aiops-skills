# M1 — Arrears State and Settle-and-Restore Rules (Area A)

Scope: the customer received an overdue-payment notification, the instance
stopped, an address became unreachable, or they want to know what settling
the bill actually restores. Every rule below is what the entry script proves
with data plus what support tickets established; anything the authorized
read set cannot see is marked CONSOLE-CHECK.

## 1. Deciding the arrears state from data

| Question | Evidence | Source |
|---|---|---|
| Is the account overdue and by how much? | `AvailableAmount` (negative = arrears amount) | bssopenapi `QueryAccountBalance` |
| Which product still owes money in a cycle? | per-product `OutstandingAmount` > 0 | bssopenapi `QueryBillOverview` |
| Was an instance stopped for arrears? | `Status` = Stopped plus `OperationLocks` entry with lock reason `financial` | ecs `DescribeInstances` |
| Was the pay-as-you-go traffic address locked for arrears? | not exposed by the authorized read set | CONSOLE-CHECK: VPC console > Elastic IP Addresses, per region |

The last row is the documented limitation seen in real tickets: an EIP can be
system-locked for arrears while the instance itself still shows Running. The
skill may state the correlation ("account is overdue + instance runs + IP
unreachable" makes an arrears-driven lock the most likely explanation) but
must label it an inference and hand the customer the console path above.

## 2. What arrears affects — and what it does not

- Arrears restrict **pay-as-you-go** usage: instances get stopped,
  pay-as-you-go EIPs can be locked, and further metering can tip more
  resources into restricted state.
- A **subscription** (prepaid, package) instance that is not itself expired
  keeps running despite a zero/negative account balance — the ticket-side
  statement used by support: arrears affect pay-as-you-go product usage.
  (Console-check its exceptions.)
- Account arrears have **no documented link to an ICP filing application
  status**: support engineers explicitly denied such a link in tickets. Filing
  rules themselves are OUT OF SCOPE here — hand off per
  [handoff-map.md](arrears-trial-billing-stop__handoff-map.md) if asked.
- Being overdue starts the retention clock on pay-as-you-go data
  (snapshots included). See [resource-retention-after-arrears.md](arrears-trial-billing-stop__resource-retention-after-arrears.md)
  before quoting ANY time figure.

## 3. Settle and restore — the branch the customer wants

Manual steps only; this skill never tops up or starts anything itself.

1. Top up until `AvailableAmount` turns positive, and leave a buffer: the
   moment metered items (instance in normal mode, EIP retention, snapshot
   storage) resume, a thin balance re-triggers the stop within the next
   deduction cycle.
2. Start the stopped instance in the ECS console once the balance recovers
   (official start path: see the start-an-instance document listed below).
3. Re-run `QueryAccountBalance` and `DescribeInstances` (this script) to
   confirm: positive amount + lock reasons cleared + status back to Running.
4. If the service is still unreachable AFTER the account-side evidence is
   clean, the remaining fault is connectivity/security-group/OS-side — stop
   here and hand off (that handoff paragraph is exactly what saved rounds of
   repeated verification in real tickets).
5. If the instance no longer appears in any swept region, check the retention
   document next: past the retention window, automatic release means the data
   is gone and only a kept backup can rebuild the service.

## 4. "I released everything but still owe a few cents"

Recurring ticket pattern: after a release, a small final statement arrives.
Cause: usage accrued up to the release time is billed/settled after the fact
(statement latency), not continued charging. Evidence handling:

- `QueryBillOverview` shows the owed product and cycle; the instance sweep
  shows it is gone; together they support "the charge belongs to the pre-release
  usage window" — stated with both citations, never as a guess.
- The exact last-statement timestamp is NOT retrievable from the authorized
  read set (support engineers read it from internal back-office views): point
  the customer to the bill statement detail page instead
  (`https://usercenter2.aliyun.com/finance/expense-report/expense-detail`).
- Settle the residual amount, then verify with the NEXT cycle's query that no
  new rows are being produced.

## 5. Documents and console entries (verified links only)

- Overdue-payment rules: `https://help.aliyun.com/zh/ecs/overdue-payments`
- Pay-as-you-go starter guide:
  `https://help.aliyun.com/zh/ecs/user-guide/ecs-pay-as-you-go-starter-guide.md`
- Instance lifecycle states:
  `https://help.aliyun.com/zh/ecs/user-guide/overview-52.md`
- Start an instance:
  `https://help.aliyun.com/zh/ecs/user-guide/start-an-instance.md`
- Stop an instance:
  `https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md`
- Bill statement detail:
  `https://usercenter2.aliyun.com/finance/expense-report/expense-detail`
- Orders list (ID-type triage aid):
  `https://billing-cost.console.aliyun.com/order/list`
