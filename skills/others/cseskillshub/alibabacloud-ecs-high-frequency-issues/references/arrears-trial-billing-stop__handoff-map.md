# M6 — Handoff Map (what this read-only skill does NOT resolve)

This skill covers account/billing/instance state for arrears, trial expiry
and stopping billing, plus manual guidance for the cleanup order. A large
share of tickets that touch "overdue" or "still being charged" are really
about something else. When the entry script's `--question` routing (or your
own reading) detects one of these, finish the billing-side evidence you can,
then hand off with a structured summary — do NOT try to solve it here, and do
NOT run mutating actions.

## Handoff table

| Symptom (customer wording) | Why not here | Route to |
|---|---|---|
| "Refund / unsubscribe / waive this fee / give a voucher" | commercial process, no authorized API | human commercial support (Billing Management > ticket) |
| "Close / cancel my whole account" | account lifecycle is out of scope | account/human support |
| "Transfer the server to another (real-name) subject / between accounts" | real-name + resource transfer policy; ECS stays within one verified subject | account/business support |
| "Payment keeps failing / my payment is restricted" (e.g. company entity deregistered) | account/finance restriction | account/human support |
| "Company was deregistered, business moved, who owns the server now" | subject-change policy | business/account support |
| Website defaced / attacked / DDoS / traffic blackhole | security incident, not billing | security incident response (Anti-DDoS / Security Center) |
| "Server won't start / stuck stopping / boot failure" | instance-state diagnosis, not billing | instance-state skill (`area:instance-state-diagnosis`) |
| "Can't SSH / security group / port / route / forgot password" after the bill was settled | network + OS side; the billing part is proven done | connectivity/security-group skill (e.g. `alibabacloud-ecs-vpc-publicnetwork-troubleshoot`) + password reset guidance |
| "Disk full / inode exhausted / can't create files" | guest-side capacity, needs read-only in-guest checks | disk-capacity skill |
| "Resized the disk but the OS still shows the old size / partition not extended" | guest-side partition + grow steps | disk-expand-diagnosis skill |
| "Disk IO slow / performance below spec" | performance diagnosis | `area:resource-bottleneck` |
| "Is it worth converting to subscription? Save me money / reserved instance? / savings plan recommendation?" | cost-optimization area | `alibabacloud-finops-inspect` |
| "ICP filing needs a 3-month subscription — does my arrears affect filing?" | filing process/eligibility (arrears is NOT a filing criterion, but the filing flow is elsewhere) | filing/beian support; here only confirm the balance fact |
| "Security Center free trial expiring" SMS, not an ECS instance | different product | Security Center console (`https://yundun.console.aliyun.com/?p=sas`), with the ECS-side exclusion from this skill attached |
| Trial-page has no Windows/region/plan option | campaign eligibility rules | activity page / human |
| "Detach my data disk failed (process holding it)" | OS-side process occupancy | instance/storage ops (needs guest read-only commands) |

## How to hand off (mandatory summary template)

Emit a short structured block so the receiving channel does not repeat
discovery:

> Handoff to: <channel/skill from the table>
> Billing-side already proven by this skill:
>   - Account arrears: <yes no figure / from QueryAccountBalance>
>   - Instances: <found/absent, states, charge types / from DescribeInstances>
>   - Bill attribution: <which products still bill, which cycle / from QueryBillOverview>
>   - Attached-resource residue: <console-checked / DEGRADED>
> Customer's actual out-of-scope issue: <their words>
> Why routed: <reason from the table above>
> Read-only note: this skill performed no changes; the customer executed <none / described console steps>.

## Cross-product handoff: Security Center trial notices

When an expiring-soon notice is actually about a Security Center pay-as-you-go
resource package (a documented confusion source in this tier), close it from
the Security Center console (`https://yundun.console.aliyun.com/?p=sas`), not
the ECS console. Support confirmed: closing such a package does not affect the
ECS instance's operation. This skill only helps prove that the ECS instance
itself is not the subject of the notice (by reading its `ExpiredTime` and
absence).
