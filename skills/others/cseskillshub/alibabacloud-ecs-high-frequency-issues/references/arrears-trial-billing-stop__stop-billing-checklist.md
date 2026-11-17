# M4 — Stop-Billing Cleanup Checklist (Area C)

The customer's goal: **no ECS-related charges anymore**. Pay-as-you-go has no
"pause/turn-off service" switch — billing ends only when every metered
resource is gone (or fully covered by economical mode, which itself has
billing exceptions). The three misconceptions this checklist exists to kill,
all recorded in real tickets:

1. "Stopped = not billing." Stopping an instance is not stopping billing.
2. "Deleted the server = deleted everything." Attached resources (snapshots,
   auto snapshot policies, standalone disks, EIPs, images, network artifacts)
   live in their own console pages and often in OTHER regions.
3. "Unsubscribed/shut down the service." There is nothing to unsubscribe for
   pay-as-you-go; the equivalent is release + delete, item by item.

## Mandatory risk-disclosure gate (print all six items with this checklist)

1. Every release/delete below is **irreversible**; data is unrecoverable by
   anyone, including support.
2. **Back up first**: snapshot (for disks) or custom image (to move the whole
   system elsewhere).
3. **Backups bill too**: snapshots charge storage by their data volume, and
   deleting a snapshot is itself irreversible.
4. **Delete the generating policy too**: an auto snapshot policy recreates
   billable snapshots after every manual deletion — charges recur until the
   policy itself is deleted.
5. **Expect one more statement**: after cleanup, a delayed bill for the
   pre-cleanup usage window can still arrive; that is statement latency, not
   continued charging.
6. **Nobody clicks it for you**: this skill and support engineers do not
   execute releases or deletions on the customer's account; every step below
   is customer-performed in the console.

## Ordered checklist (per region — repeat in EVERY region ever used)

| # | Item | Where (console) | Stops billing for | Notes |
|---|---|---|---|---|
| 1 | Inventory first: where is money still going? | Expenses and Costs > bill details per cycle; or run this skill | — | The bill overview names the PRODUCT and its billing items (measured: no region field); the instance sweep and the console bill drill-down locate the REGION |
| 2 | Backups of anything still wanted | ECS console > Storage & Snapshots > Snapshots; Images > Custom Images | — | Snapshots/images bill themselves — a temporary cost, deleted at step 6 |
| 3 | Release ECS instances | ECS console > Instances (per region) | instance configuration, image usage, system disk, outbound traffic of the instance | Pay-as-you-go items billed while an instance EXISTS even unused; release doc: `https://help.aliyun.com/zh/ecs/user-guide/release-an-instance` |
| 4 | Release standalone / detached data disks | ECS console > Block Storage > Disks (per region) | disk capacity | **Detach is not release**: a detached disk keeps charging until released — support stated this verbatim in tickets; console may hide it unless you look at unattached disks |
| 5 | Release EIPs not kept by instances | VPC console > Elastic IP Addresses (per region) | EIP retention/hold fees while unused | An EIP retained for later use keeps a small periodic charge; if the customer wants the address forever, this is a keep-vs-cost decision, not a cleanup error |
| 6 | Delete snapshots | ECS console > Snapshots (per region) | snapshot storage | `https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1` — irreversible, keep the backup until the last moment |
| 7 | Delete auto snapshot policies | ECS console > Auto Snapshot Policy (per region) | future snapshot creation | THE recurrence root cause: tickets show customers who deleted snapshots only, then kept being billed days later |
| 8 | Remove network leftovers tied to deleted servers | VPC console (per region) | — | VPC/vSwitch objects themselves are free; what bills is what sits in them (EIP, gateways, etc.). Sweep per the bill's product rows, doc: `https://help.aliyun.com/zh/vpc/vpc-and-vswitch` |
| 9 | Verify next cycle | bill detail page or rerun this skill with the next BillingCycle | — | New rows appearing for a product you already cleaned mean a resource in ANOTHER region or an un-deleted policy; overdue + "instance released" states both explained? settle residual cents per M1 section 4 |

## Region sweep discipline

Charges routinely live in a region outside the customer's default console
view. Evidence from this tier's tickets: billable snapshot residue in regions
the customer "never used", while the deleted instance sat elsewhere.
Practical rule: sweep the region selector to every region appearing in ANY
bill cycle of the last months, and to the built-in common list; the script's
`--regions` accepts the explicit list, and the bill attribution step names
candidate regions.

## Stop vs release wording for the customer

- Stop (`stop-an-instance` path) saves compute charges under economical mode
  only, with exceptions and conditions — read
  `https://help.aliyun.com/zh/ecs/user-guide/economical-mode.md` with the
  customer rather than asserting "free while stopped".
- Only steps 3–7 above end the billing of the resources they cover.
- A machine that must be kept but idled: economical mode may reduce instance
  charges, but disks, snapshots, EIPs still bill; the bill query remains the
  arbiter.

## Documents and console entries (verified links only)

- Pay-as-you-go billing explanation:
  `https://help.aliyun.com/zh/ecs/pay-as-you-go-1`
- Start/stop instance docs:
  `https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md`,
  `https://help.aliyun.com/zh/ecs/user-guide/start-an-instance.md`
- Snapshot billing: `https://help.aliyun.com/zh/ecs/snapshots-1`,
  overview: `https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview`
- Create snapshot (backup): `https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot`
- ECS console home: `https://ecs.console.aliyun.com/home`
- Snapshot console: `https://ecs.console.aliyun.com/snapshot`
- Bill / expense detail:
  `https://usercenter2.aliyun.com/finance/expense-report/expense-detail`
- Orders list: `https://billing-cost.console.aliyun.com/order/list`
