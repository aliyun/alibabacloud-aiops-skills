# Inventory fallback (sold out / NoStock handling)

## What the readings mean

- `DescribeResourcesModification` answers: for THIS instance, which target
  specs are selectable at all, and each target's state
  (`Available` / `SoldOut` / other) - the change-set view.
- `DescribeAvailableResource` answers: what is sellable in a region / zone
  right now - the buy-page view, also used for new purchase.
- A type can be sellable on the buy page yet absent from a specific
  instance's change set (family path rules), and vice versa; always say
  which view a statement comes from. The reviewed case `T-9FD79CD0` ended
  with exactly this question unanswered by the human - the skill must
  answer it with both readings side by side.
- Stock is an INSTANTANEOUS value: it can flip within minutes
  (`T-7EF1DFC9`: `ecs.g7.6xlarge` shown sold out, then self-recovered) and
  release times cannot be predicted (`T-F3FCB834`: even the human's test
  showed sold out). Never promise WHEN something becomes buyable.

## Fallback ladder (in order, each step evidence-first)

1. **Re-check now** with `--check-inventory` for the target type across the
   region; report per-zone `Available` / `SoldOut` verbatim from the data.
2. **Same-tier substitutes**: use the substitute scan (`--cores` /
   `--memory`) so every suggested type is PROVEN in stock in this region
   (lesson from `T-26C336BF`, where a human suggested an alternative region
   without checking its stock).
3. **Other zones / regions**: run `--check-inventory` with another
   `--region-id` before recommending it; say what was verified, with which
   reading.
4. **Wait and retry**: legitimate, but frame it with the caveat above
   (`T-F3FCB834`: "refresh the change page over the next days"; never
   attach a time when stock returns).
5. **Start-blocked special case** (`T-EB859CCC`): if an instance refuses to
   START with `OperationDenied.NoStock`, the way out is a spec change to an
   in-stock type (the entry script's change-set reading shows which), then
   start again; if it stays stuck between states, that part leaves this
   tier - hand off (see `references/spec-change-purchase__handoff-map.md`).

## What always stays human

- Resource reservation / coordination, escalation to a business manager
  (`T-54655754`: repeated reservation attempts never succeeded;
  `T-B6B7ECDB`: only 2 units left in the zone, business manager took over).
- Any guarantee of future stock, or of keeping an order through a
  promotion window - if a deadline competes with waiting for stock
  (`T-F3FCB834`: expiry on Sep 6 vs sold-out target), lay out the
  conflict honestly and offer the evidence-backed alternatives above.

## Wording discipline

- Present stock as "at check time X, region/zone Y state Z", never as a
  standing fact.
- The console's sold-out / insufficient-inventory wording (localized) maps
  to the `OperationDenied.NoStock` handling line; do not treat it as a
  separate code (`references/spec-change-purchase__error-codes.md`).
- If the customer's purchase page simply cannot SHOW a low spec during a
  downgrade (`T-9FD79CD0`), the change-set reading is the authority: not
  listed = not selectable for this instance; explain, then offer ladder
  steps 2-4.
