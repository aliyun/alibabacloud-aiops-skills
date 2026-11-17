# Stop modes and what keeps charging

Read this before answering any "am I still charged?" question. Quote the rule, name
the source, and put today's date next to it: every statement below is rule knowledge,
and the vendor edits these pages without notice.

## 1. The three states customers mix up

| State | What the platform keeps | What you pay for afterwards | Restart behaviour |
|---|---|---|---|
| Normal stop (charge kept) | Compute allocation, private and public addresses | Everything, exactly as while running | Immediate; stock is not involved |
| Economical stop mode | The disks, the instance identity, the configuration | Disks and snapshots only; compute charging is suspended | Compute has to be re-acquired, so stock can block it and the system-assigned public IP can change |
| Release | Nothing | Nothing for the instance itself | Not applicable; the data is gone and cannot be recovered |

The single sentence that settles most of these conversations:

> Stopping is not releasing. Economical stop mode suspends compute billing, it does
> not end billing. Only release ends instance charging, and release destroys the data.

## 2. Why the bill does not go to zero

A pay-as-you-go bill for a stopped instance is normally made of continuing items,
not of a mistake:

- System disk: still charged while it exists.
- Data disks: still charged while they exist.
- Snapshots: charged by stored capacity, independent of the instance state.
- Compute (vCPU, memory, GPU): charging suspended in economical stop mode only.
- Public bandwidth: see the unresolved note below; do not assert a value.

If the customer reports a concrete amount, do not estimate it. This skill has no
billing action, so give the self-check entry and ask for what the page shows:

- Bill detail by instance:
  `https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance`

Reference unit prices the customer may see on that page, and what each means:

| Bill line item | Unit | Meaning |
|---|---|---|
| Instance configuration | CNY per hour | The compute part; suspended in economical stop mode |
| Disk capacity | CNY per GiB per hour | The storage part; continues while the disk exists |
| Outbound traffic | CNY per GB | Network egress; only accrues when traffic actually leaves |

Never state a customer's amount yourself. Read the number off the page the customer
is looking at.

## 3. Unresolved point that must not be guessed

Whether public bandwidth keeps charging during economical stop mode is **not settled**
in the material this package was built from, and the two readings found in customer
reports contradict each other:

- One reading: the public address and its bandwidth are released with the compute, so
  nothing accrues.
- Other reading: bandwidth still appears among the charged items.

Rule for the agent: do not pick a side. Say that the released public address is a
fact, that the bandwidth line has to be confirmed against the cited document today,
and that the authoritative number for this customer is what the bill detail page
shows. Ask for a screenshot if the customer needs a definite answer.

## 4. Standing clarifications

Reuse these sentences verbatim; they are the recurring misreadings:

1. Being able to see a value is not the same as being able to change it.
2. Economical stop mode is available on pay-as-you-go instances only.
3. Subscription instances have no stop-mode choice; converting the billing method
   first is a change the customer makes, not this skill.
4. Disk data survives economical stop mode. The system-assigned public IP may not.
5. The mode has no scheduler: it never starts or stops anything by itself on a timer.
6. Performance mode on a burstable instance is a different concept; it is not a
   stop mode.

## 5. Facts this skill cannot read

| Question | Why it stays open | What to do instead |
|---|---|---|
| Is this instance currently in economical stop mode? | No verified read-only field is claimed by this package for the stop-mode marker | The customer reads it on the instance details page or sends a screenshot; never report it as confirmed |
| What exactly was billed this hour? | No billing action in the policy | Customer opens the bill detail page above |
| Was the released public IP reused by someone else? | Address reassignment is not queryable from here | Hand off to the EIP and address topics |
| Will the arrears, refund or coupon request succeed? | Commercial and human review process | Hand off to human support |

## 6. Sources

Verify each link online at answer time, then record the date in the report.

- Economical mode usage:
  `https://help.aliyun.com/zh/ecs/user-guide/use-of-economical-mode.md`
- Stopping an instance, including the mode choice:
  `https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance`
- Releasing an instance:
  `https://help.aliyun.com/zh/ecs/user-guide/release-an-instance`
- Impacts and risks of economical stop mode:
  `https://help.aliyun.com/document_detail/63353.html`
- ECS overview and billing methods:
  `https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md`
- Bill detail by instance (console entry, not a document):
  `https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance`

The stop-mode marker limitation in section 5 is an explicit open item of the tier
specification this package implements: the read contract available at build time
covered the instance and its attached groups only, and did not establish a stop-mode
field. Treat it as a blind spot, not as a value to infer from the power state.
