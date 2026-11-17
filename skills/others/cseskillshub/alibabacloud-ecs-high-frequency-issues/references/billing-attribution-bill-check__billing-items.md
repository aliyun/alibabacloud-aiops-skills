# M1 — ECS-Related Billing Items Dictionary

Attribution order for every charge: **amount -> product -> billing item ->
region -> instance/resource ID -> usage -> unit price -> payable / deducted
/ paid**. The bill row is the single source of truth; the unit prices below
are reference examples observed in real support tickets and MUST NOT
override the row's own `ListPrice` / `Usage` fields.

## Item dictionary

### Public outbound traffic (NetworkOut / pay-by-traffic)

- Billed by usage in the **outbound direction only**; inbound traffic is
  not billed. Applies when the instance's internet bandwidth billing mode
  is "pay-by-traffic" (`InternetChargeType=PayByTraffic`).
- Ticket reference price: 0.8 CNY/GB (Chinese mainland, pay-by-traffic
  IPv4). The row's `ListPrice x Usage` is authoritative; the script
  recomputes both and flags any row that cannot be explained.
- A **Subscription (monthly) instance can and does carry this post-paid
  item** — the single most frequent surprise ("I pay monthly, why is there
  a traffic bill"). The fee appears in the post-paid bill list even for
  monthly instances.
- Per-day traffic detail is only queryable for instances with a **fixed
  public IP billed by traffic**; fixed-bandwidth instances produce no
  traffic line items at all.
- Historical traffic DESTINATIONS (which address, which peer) are never
  retained cloud-side for privacy reasons — see `handoff-map.md`.

### Snapshot chain capacity

- Billed hourly by snapshot size x duration. The first snapshot of a disk
  is full; later snapshots are incremental, so billed size is the total of
  the chain, not of each backup moment.
- Manual snapshots bill normally. The limited-time-free quota applies ONLY
  to snapshots produced by the free auto-snapshot policy AND disks actually
  bound to it — see `deduction-matrix.md`.
- Snapshots copied to another region bill in the DESTINATION region; this
  explains fees in regions where the customer created no instance.
- Snapshot management operations (create / delete / policy bind) belong to
  the snapshot-management skill; this skill only attributes the fee.

### Disk (block storage) capacity

- A cloud disk bills **from the moment it exists**, attached or not, even
  while its instance is stopped. Unattached disks are the classic "paying
  for something I do not use" finding: the bill row's resource ID maps to
  no running instance.
- Deleting a disk is irreversible — guidance only, never execution.

### Instance specification (compute) fee

- Pay-as-you-go instances bill hourly by spec **including while merely
  stopped**. Only release ends the fee (manual, destructive).
- Economical (savings) stop suspends exactly: instance spec fee, fixed
  public bandwidth fee, image license fee. Everything else keeps billing.

### System disk / data disk fees

- Follow the disk-capacity caliber; they keep accruing under savings stop.

### Burstable-instance excess CPU credits (SurplusCredit)

- t5/t6 burstable instances have a baseline CPU performance and accrue
  credits; in unlimited mode, exceeding the baseline consumes credits that
  are billed as the SurplusCredit item.
- The bill may display the PRODUCT as "ECS subscription" while the actual
  BILLING ITEM is SurplusCredit — always read the item column, not the
  product label (the classic multi-round dispute starter).

### Image license fee

- Commercial / marketplace images add a license fee; suspended under
  savings stop together with the spec fee.

### Elastic IP address (EIP) fee

- EIP holding / traffic fees continue under savings stop and while the
  EIP is unbound.

## Amount fields on every bill row

| Field | Meaning (caliber) |
|---|---|
| `PretaxGrossAmount` | gross amount = usage x list price before discounts |
| `InvoiceDiscount` | commercial discount on the row |
| `DeductedByResourcePackage` | **CNY equivalent** deducted by a resource package (NOT usage volume) |
| `DeductedByCoupons` | coupon amount deducted on this row |
| `AfterDiscountAmount` | amount after discounts |
| `PretaxAmount` | payable — what the balance is charged |
| `CashAmount` | paid from cash balance |
| `OutstandingAmount` | unsettled remainder |

A row with `PretaxAmount > 0` while `DeductedByResourcePackage = 0` and
`DeductedByCoupons = 0` is the deterministic evidence of "in fee with zero
deduction" used by the deduction report (see `deduction-matrix.md`).

## Non-ECS items inside an ECS bill question

Object Storage (OSS), Security Center, Cloud Backup, CDN/ESA and Cloud Data
Transfer (CDT) rows surface whenever a customer asks "where did my money
go". This skill attributes them to product x item x amount, then hands the
rules questions to the owning channel — see `handoff-map.md`.
