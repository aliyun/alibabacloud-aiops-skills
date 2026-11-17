# Spot inventory, purchase failures and suitability

Scope: "I cannot buy a spot instance", "when will stock come back", "it keeps being
reclaimed", and "is my workload fit for spot". Answered with one read-only query
(`DescribeAvailableResource`) plus the documented supply rules. Architecture design is
not done here.

Sources:
`https://help.aliyun.com/zh/ecs/user-guide/spot-instance-advisor.md` and
`https://help.aliyun.com/zh/ecs/user-guide/what-is-a-spot-instance.md`.
Console entries below came from real ticket dialogs in this tier and are recorded, not
re-fetched: `https://ecs.console.aliyun.com/spotAdvisor/realTimeData` and
`https://ecs.console.aliyun.com/spotAdvisor/historyData`. Verify the paths before
quoting them.

## 1. The supply rule

- Spot capacity **is idle inventory**. It is not a reserved pool, and it is not sized by
  demand forecasts.
- When a zone and instance type are sold out, purchases fail — and **there is no
  committed restock time**. Nobody can answer "when will it be back", because the honest
  answer is that supply reappears when the pool of idle capacity changes. Say this
  plainly; do not hedge it into an estimate.
- The same mechanism explains both customer complaints in this tier:
  - "I cannot buy it at all" → no idle inventory for that zone and type right now;
  - "I bought it and it keeps being reclaimed" → inventory is thin and moving.
- A spot instance can be reclaimed while the account balance is ample and while the
  customer bids at the market price; no bidding mode removes the inventory trigger.

## 2. What the read-only query settles

`DescribeAvailableResource` answers **right now, for this account's view of the region**:
which zones and instance types are sellable, and with what stock category.

| Field echoed | Reading used here |
|---|---|
| `Status` | `Available` / `SoldOut` / other raw value |
| `StatusCategory` | `WithStock` = purchasable, `ClosedWithStock` = restricted or low stock, `WithoutStock` = sold out |

Verdict rules applied by `scripts/areas/preemptible_instance_guide/spot_instance_check.py`:

- any row `WithStock` or `Available` → **sellable at query time**;
- otherwise any `ClosedWithStock` → **unreliable**;
- otherwise any `WithoutStock` or `SoldOut` → **sold out at query time**;
- no rows carrying a status → **no conclusion** (the limitation is reported, never
  replaced with a guess).

Notes the report must carry:

- The stock categories are the documented ones; unexpected values are echoed raw and
  flagged as outside the bundled mapping.
- Spot supply can be narrower than general supply. When the query is run without a
  bidding mode, the rows describe capacity in general and the script says so.
- `InstanceChargeType=PostPaid` is auto-filled for this question (spot is sold on the
  pay-as-you-go charging type) and is declared under `ASSUMPTIONS`.
- A result is a snapshot. Tell the customer to re-check immediately before ordering.
- The query shows **purchasability**, not interruption rate. Those are different numbers,
  and only the advisor pages below speak to interruption rate.

## 3. Selection guidance for a customer who must use spot

The customer does this in their own console; this skill does not read advisor data — the
advisor interfaces were **not** part of the verified API surface bundled here, so the
script makes no call for it and no field of it is ever quoted.

1. Open the spot advisor pages above: real-time and historical price and interruption
   rate per region and instance type.
2. Prefer **low interruption rate** types over cheapest-price types when the workload has
   any cost of failure; the cheapest option is the one most likely to be taken.
3. Widen the candidate set: several instance types and several zones, so supply moves
   around without taking the whole job down. Cross-zone spread also matters if data is
   retained — a retained disk can only join an instance **in its own zone**
   (`ref-data-retention.md` §2).
4. Keep state off the instance, so that losing it costs a restart instead of a rebuild.
5. If a reclamation actually happened, use the self-check path in
   `ref-spot-mechanism.md` §5 rather than asking this skill to attribute it.

## 4. Is the workload fit for spot at all

Judgement, from the documented criteria: **stateless, fault-tolerant, interruptible**.

| Workload | Fit | Why |
|---|---|---|
| Elastic web front end, behind a load balancer | Good | Any node can be taken without losing service |
| Batch, render, CI, scale-out compute, test environments | Good | A retry is cheap; interruption is absorbable |
| Databases, or any stateful service on local disks | Not suitable | The persistent state is exactly what reclamation deletes |
| Message queues / caches with local persistence | Not suitable without external durability | Same reason |
| Long single-run jobs without checkpoints | Poor unless checkpointed | Progress dies with the instance |
| Anything with a compliance or availability commitment | Not suitable for the committed part | Spot carries no availability guarantee |

The recurring ticket shape is a customer who chose spot **for a database** because of the
discount. The correct answer is the suitability rule plus "move the state off the
instance", not a reclamation explanation — and the "why did it stop" part is answered in
`ref-spot-mechanism.md`.

## 5. Out of scope here, hand off

| Ask | Goes to |
|---|---|
| Designing an Auto Scaling group, capacity-rescue strategies, multi-zone architecture | Solution / architecture tier |
| A purchase failure on a **non-spot** instance, or a pure order-placement error | Instance purchase / creation tier; this tier only covers "spot depends on idle inventory" |
| Quotas, limits, real-name or account-level blocks | The account and quota tier |
| Any statement about price history as a promise about future price | Do not state it; the advisor pages are the customer's own reading |
| Specific amounts billed | `ref-billing-scope.md`, then the billing tier |
