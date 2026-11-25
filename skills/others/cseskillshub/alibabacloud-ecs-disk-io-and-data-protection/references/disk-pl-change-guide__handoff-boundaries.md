# Module M5 — Handoff boundaries (symptom areas this skill identifies but does not treat)

Used by `scripts/axes/disk_pl_change_guide/disk_pl_advisor.py` (all modes) and SKILL.md. This tier
covers exactly three symptom areas: **(1) change eligibility / operation
guidance / data safety** for disk type and performance level, **(2) IOPS /
throughput caliber and ceiling calculation**, **(3) bottleneck attribution
across disk side / instance side / workload side**. Anything else is
identified, declared out of scope, and handed off — with the doc links
below — never diagnosed halfway.

## Handoff table

| Customer symptom | Recognition cue | Handoff target | This skill NEVER |
|---|---|---|---|
| Quotation / price of a config / pricing failures | "how much", "quote", "price", "inquiry failed" on a buy page | official pricing calculator on the buy page; sales manager (commercial channel) | quote amounts, discounts, or refund figures (tickets T-8FCE8F40 / T-F7B7C8A6 / T-EB568736) |
| Instance CPU/memory spec change | the target of the change is the instance type | instance-spec change flow: <https://help.aliyun.com/zh/ecs/user-guide/change-the-instance-types-of-subscription-instances> | promise spec-change feasibility (ticket T-A89C6F2F) — but this skill DOES name the instance bandwidth as a bottleneck layer, that stays in scope |
| Disk capacity expansion / shrinking | the target is the SIZE, not type/PL | disk-resize flow; shrinking FAQ with the two replacement schemes: <https://help.aliyun.com/zh/ecs/disk-resizing-and-shrinking-faqs#title-n9f-bic-1n4> | execute resizing; here capacity only feeds the ceiling formulas (ticket T-E10A0001) |
| Unsubscribe / refund / stop billing a disk | "unsubscribe", "refund", "stop charging" verbs | billing channel; customer console docs: <https://help.aliyun.com/zh/ecs/switch-the-billing-method-of-a-disk> , <https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk> , <https://help.aliyun.com/zh/ecs/user-guide/release-a-disk> — warn: back up data before any release | touch billing (ticket T-BD63C308) |
| AutoPL burst post-paid charges / turning burst off | small unexpected io_burst line item | billing channel + burst config doc: <https://www.alibabacloud.com/help/zh/ecs/user-guide/modify-the-performance-configurations-of-an-essd-autopl-disk#title-o4i-xnc-cbf> ; caliber explained here (see performance-formulas.md §2) | compensate, disable, or promise any billing outcome (ticket T-9674C108) |
| Custom image content; lightweight-server → ECS migration | image contains which disks; cross-product move | image / migration flows: <https://help.aliyun.com/zh/ecs/user-guide/image-instant-access.md> (instant access is ESSD-only, relevant when choosing a disk type) | create/share images or migrate (tickets T-9C799442 / T-6A3314C0) |
| Per-process IO attribution inside the guest | "which process", atop/iostat/slow-log/OOM questions | the allowlisted listing commands can be dispatched after per-command confirmation; the attribution tools themselves are run by the customer, who pastes readings — [guest-diagnostics.md](disk-pl-change-guide__guest-diagnostics.md) §2/§4; unexplained cases → human support | dispatch anything outside the five-entry allowlist, or interpret a reading that was never collected (tickets T-EE75C111 / T-0F3C602D / T-CB4F17DF / T-CC0FA37F) |
| Platform-side history (background migration, replica rebuild claims) | "did you migrate my disk", unexplained IO windows | **human support ticket** — no cloud query API sees this (both cloud and guest evidence was exhausted in ticket T-CC0FA37F without a confirmed root cause) | assert or deny platform-side causes |
| Windows instance guest diagnosis | drive letters, PerfMon, Windows services | human support; this tier has no Windows ticket evidence | promise Windows in-guest flows |

## Handoff wording template

> "This part — <area> — is outside what my query-based disk-type /
> performance-level checks can settle. The right path is <target>. The
> references above are the official docs for it. What I CAN still do for
> you on the disk side is <remaining in-scope offer>."

Attach the specific doc URL from the table; where the customer was also
asking something in-scope (e.g. a pricing question wrapped around a real
upgrade question, ticket T-584A7DD3), split the request: treat the
in-scope half, hand off the rest.

## What counts as in-scope even when it looks like a handoff

- **Why the ceiling is what it is** (formula, capacity linearity, base vs
  burst caliber) — in scope (performance-formulas.md (in alibabacloud-ecs-high-frequency-issues)).
- **Which side the bottleneck is on** — in scope, including the conclusion
  "the fix is an instance-type change" (attribution only; executing it is
  the handoff) — ticket T-39B4EB79.
- **Whether a change is one-way / online / data-safe** — in scope
  ([change-matrix.md](disk-pl-change-guide__change-matrix.md)).
