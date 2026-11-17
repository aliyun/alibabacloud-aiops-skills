# M3: Switching the Performance Mode — Customer Console Steps + Warnings

The performance mode (standard / constrained vs. unlimited / "no
performance constraint") is a **console switch the customer operates**. This
skill is strictly read-only: it never toggles the mode itself; it supplies
the path, the official document, and — mandatorily — the two-sided
consequence warning **before** any step.

## Official document (primary guidance source)

- Switch the performance mode of a burstable instance:
  https://help.aliyun.com/zh/ecs/user-guide/switch-the-performance-mode-of-a-burstable-instance
- Mode FAQ: https://help.aliyun.com/document_detail/90634.html#related-links-atz-8da-bw4
- Mode concepts: https://help.aliyun.com/zh/ecs/user-guide/burst-performance-instance-overview.md

## Console path (as stated in ticket evidence T-E42721B9 / T-AECC16D7)

1. Log on to the **ECS console** and open the **Instances** list for the
   instance's region.
2. Select the target instance -> **More** -> **Instance Attributes** ->
   turn **on** or **off** the no-performance-constraint (unlimited) mode.
3. Confirm the dialog. No reboot is required for the switch itself; the
   effect is immediate per the official document.

> Console menus are versioned: if the customer cannot find the entry, give
> the official document above as the current path authority instead of
> improvising a location.

## WARNING — before turning the mode OFF (mandatory, emit first)

- With no credit balance in hand, the instance is **pinned to its baseline
  CPU performance immediately**. Anything that had been running above the
  baseline slows down at once.
- Real-ticket lesson: a customer switched the mode off to stop the excess
  charges and the website became unreachable right after (T-2F07C4BD);
  another could not even open a browser on a 4-vCPU 25%-baseline box at
  baseline (T-BEE1DF3D — baseline capacity is about 1 core).
- If the workload genuinely needs sustained CPU above baseline, switching
  off is only safe after confirming the baseline covers normal load — that
  comparison is the customer's, using the baseline math in
  [credit-rules.md](burstable-instance-guide__credit-rules.md).

## WARNING — before turning the mode ON (mandatory, emit first)

- Unlimited mode keeps bursting past every credit pool; past accrued and
  advanced credits it consumes **excess credits, billed pay-as-you-go**
  continuously while load stays above baseline (rate: see
  [billing-unlimited.md](burstable-instance-guide__billing-unlimited.md)).
- There is no default per-charge realtime alert: configure the CloudMonitor
  credit-threshold alarm (and the account cost alert) together with the mode
  switch, or the bill arrives first — exactly the complaint pattern of
  tickets T-6F237607 / T-0495147E.

## Hand-off note

- Spec change / reboot / snapshot around a mode decision are separate
  customer operations with their own prerequisites (restart ~3-5 min, stop
  applications first, snapshot recommended — ticket T-408C886A guidance);
  this skill explains prerequisites and re-verifies facts read-only
  afterwards, it never executes them.
