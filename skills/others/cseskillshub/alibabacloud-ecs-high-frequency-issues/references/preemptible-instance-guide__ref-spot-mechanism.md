# Spot reclamation mechanism, notice and attribution

Scope: what this skill may state about **why** a preemptible (spot) instance stops, what
the notice means, and what may not be concluded. Every statement below is tied to an
official document; the script echoes these as rule statements so an answer never drifts
between runs.

> Evidence caveat, restated in every report: the document links in this bundle were
> recorded from the tier evidence snapshot (`aliyun-help-search`) and were **not
> re-fetched while packaging**. Confirm version-sensitive values against the live
> official document before quoting them as current, and note the check date in the
> answer.

## 1. What a preemptible instance is

- Sold from **idle inventory** at a market price that carries a large discount against
  the pay-as-you-go price of the same instance type.
- The platform **automatically interrupts** the instance when the market price rises
  above the customer's bid ceiling, or when idle inventory changes.
- Suited to **stateless, fault-tolerant, interruptible** workloads. Not suited to
  persistent stateful services such as databases.

Source: `https://help.aliyun.com/zh/ecs/user-guide/what-is-a-spot-instance.md`
(overview; also `https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md` for where spot
sits among the instance types).

## 2. The notice and the 5-minute window

- The customer is notified **about 5 minutes before** an interruption, and the instance is
  **released 5 minutes after** the guaranteed usage duration is exceeded. That is ONE single
  5-minute window, not two consecutive ones — the advance notice *is* the reaction time.
  "We were told 5 minutes ahead" therefore does **not** mean there was time to react if the
  notice arrived late, to a phone nobody holds, or not at all.
- Notice wording seen in real tickets reads, in effect: *your preemptible instance will
  enter the stopped state due to inventory changes*. The localized wording is the
  customer-visible string to match on, not an API error code.
- **Delivery time is not release time.** Notice delivery can lag the actual release, so a
  customer who compares the SMS timestamp with the release timestamp may conclude the
  wrong thing. This distinction settles several tickets in this tier.
- Notices go to the notification channels **bound to the account** — commonly the mobile
  number bound to the primary account, which in company accounts is not the operator's
  number. Recipients are managed by the customer in the Message Center. **This skill
  cannot query notification delivery records**; that is a support-ticket matter, and the
  agent must not claim the notice "was" or "was not" delivered.

Source: spot overview document above (notice and protection-period wording).

## 2b. Guaranteed usage duration (fixed at creation, never modifiable)

| Setting | Meaning | Consequence |
|---|---|---|
| **1 hour** | The instance is **not interrupted during the first hour** after creation | The only protection against interruption, and it expires |
| **No guaranteed duration** | The instance can be **interrupted at any time** | Nothing protects the first minutes; suitable only for work that can restart |

- The duration is chosen **when the instance is created and cannot be changed afterwards**,
  so "can we add the 1-hour guarantee now" is answered "no, not on this instance".
- The guarantee only covers the **first hour**. It is not a renewal, not a reservation and
  not a promise about any later hour.

## 3. What an interruption actually does: the two interruption modes

The interruption mode is chosen **at creation and cannot be modified** after the instance
exists. It decides whether anything survives, and whether anything keeps being billed. Ask
for the mode before answering "is my data gone", because the two modes give opposite
answers. Console label to API term: "direct release" is the release-everything mode, and
"stop-charging" is the mode the API/CLI calls `StopCharging`.

| | **Direct release** | **Stop-charging** (`StopCharging`) |
|---|---|---|
| Compute resources (vCPU/GPU, memory) | Released | Reclaimed |
| Fixed public IP | Released | Reclaimed |
| Fixed bandwidth | Released | Reclaimed |
| Cloud disks (system + data) | **Released with the instance** — data is deleted | **Retained** |
| Elastic IP address (EIP) | Released | **Retained** |
| Snapshots | Released unless separately protected | **Retained** |
| What keeps being billed afterwards | Nothing on this instance (snapshots the customer keeps are billed by the snapshot tier) | **The retained disks, EIP and snapshots keep being billed while they exist** |
| Can it come back | No: a released instance cannot be restored | The instance stays in the stopped state, **but a restart can fail** — see below |

- **Stop-charging restart can fail.** After a stop-charging interruption the instance may
  refuse to start again because the zone/instance-type **inventory** is insufficient, or
  because the **floating market price has risen above the customer's bid**. A stop-charging
  interruption is therefore *not* a guaranteed "I can start it again later"; treat a failed
  restart as consistent with the spot rules, not automatically as a platform fault.
- In **direct-release** mode the instance and its disks are gone; **data on the disks that
  were released together with it cannot be recovered**, and there is no exception path in
  the product. Say it plainly.
- Once released, the instance **stops appearing in read-only query results**. "Not found"
  from this skill is therefore consistent with a reclamation — but also with a wrong
  region, a wrong id, or another account. Never convert "not found" into "proof it was
  reclaimed".
- Retained-but-still-billed is the misconception antidote for stop-charging: a customer who
  believes "the instance is stopped, so it is free" is still paying for the disks, the EIP
  and the snapshots. Amounts stay out of scope (`ref-billing-scope.md`); the *rule* is
  stated here.

## 4. Bidding modes, and the balance misconception

| `SpotStrategy` value | Meaning | What it can and cannot prevent |
|---|---|---|
| `SpotWithPriceLimit` | Preemptible with a customer-set maximum hourly price | Addresses the price trigger only |
| `SpotAsPriceGo` | Preemptible billed at the prevailing market price | Addresses the price trigger only |
| `NoSpot` | Not a preemptible instance (pay-as-you-go or subscription) | Out of this tier: the stop has another cause |

- **A sufficient account balance does not keep a spot instance alive.** Interruption
  depends on price and inventory, not on balance. This is the single most common
  misconception in the tier's tickets.
- Automatic bidding at the market price does **not** immunise the instance either: with no
  ceiling, the price trigger is met by definition, and inventory-driven reclamation is
  unaffected by any bidding mode. Customers reporting "frequent release despite automatic
  bidding and plenty of balance" are hitting the inventory trigger.

## 5. Attribution: what may not be concluded

The decisive question for a complaining customer is usually *which* trigger applied.

- **Not readable** from the whitelisted queries. `DescribeInstances` /
  `DescribeInstanceStatus` give existence, status, zone, charging type, bidding mode and
  any operation-lock reason — not the reason a past release happened.
- `OperationLocks` carrying a **recycling** lock reason is the strongest in-API signal
  that reclamation is in progress; the script echoes the raw value and reports the match
  separately, because the raw value is the evidence and the match is the reading of it.
- When attribution is asked:
  1. state both triggers and that no bidding mode removes the inventory one;
  2. point the customer to the official interruption-event self-check path below, which
     they read in their own console;
  3. ask for the bidding mode and the notice they received, and explain those against
     the rules above;
  4. route any demand for platform-side evidence (delivery records, release attribution,
     timestamps of a released instance) to a support ticket.
- The API contract for querying spot **interruption events** was not part of the verified
  surface bundled with this skill, so the script does **not** call it. Treat the
  self-check document as the customer's path, and do not name an action for it.

Source:
`https://help.aliyun.com/zh/ecs/user-guide/query-the-interruption-events-of-preemptible-instances.md`

## 6. Distinguishing a spot reclamation from other stops

Do this first; it decides whether the question belongs here at all.

| Signal | Reading |
|---|---|
| `SpotStrategy` is a bidding mode and status is `Stopped`/`Stopping` | In scope: spot interruption is consistent with this |
| `SpotStrategy` is `NoSpot`, or the field is absent | Not this tier: route to the stop-cause / expiry / billing tier instead of explaining spot |
| Subscription instance near its expiry | Expiry and release lifecycle tier |
| Stop with no spot billing type but a security or content-related lock | Forced-stop / compliance tier |
| Stopped pay-as-you-go instance with a stop-mode question | Saving-stop-mode tier; only the disk-fee point below overlaps this tier |
| Customer cannot buy a spot instance at all | Not a reclamation: inventory, see `ref-inventory-advisor.md` |

## 7. Windows and guest-OS confidence

Every rule above depends on the **billing type and cloud-side behaviour**, not on the
guest operating system, so they carry over unchanged to Windows spot instances
(confidence: high).

**Windows-specific interruption behaviour — for example whether the in-guest notice or
shutdown behaviour differs — has no evidence in this bundle (confidence: low,
unverified). Do not assert it**; say that this skill has no verified information on that
point.

## 8. Statements this skill may never make

- "Your balance was insufficient" / "your overdue payment caused the release."
- "The market price exceeded your bid" as a fact about one specific past release.
- "We sent the notice at HH:MM" (delivery records are not readable here).
- "We restored / re-attached / snapshotted / changed ..." — nothing is ever done.
- "This instance can be recovered from the release."
- Any claim about a specific billed amount.
