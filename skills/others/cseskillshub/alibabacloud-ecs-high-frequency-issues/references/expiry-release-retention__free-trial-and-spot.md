# Free Trial and Spot (Preemptible) Instances: lifecycle specifics

Two lifecycle forms generate a large share of "why is my instance gone /
still charging" confusion. Evidence tags follow `lifecycle-rules.md`.

## 1. ECS free trial

Mechanism (customer misunderstanding corrector):

- The free trial is NOT a separate "free server" product. It is a normal
  pay-as-you-go instance whose charges are offset by a granted
  savings-plan-style resource package [ticket:T-C3E9D9B3].
- Trial-end notification SMS ("your ECS free trial ... will end at
  <time>") refers to the resource package end time, not necessarily to the
  instance being deleted at that moment [ticket:T-EDCE8535].
- At trial end there is NO auto-renewal. If the account holds no remaining
  instance, nothing further is charged and there is nothing to "manually
  release" [ticket:T-EDCE8535].
- If the pay-as-you-go instance still exists after the package ends, it
  keeps billing against the account balance until it is released or
  converted to subscription [ticket:T-C3E9D9B3].
- Resource-identifier caution: verify WHICH instance belongs to the account
  before quoting an id -- a real dialog first quoted the wrong instance id
  and had to correct it [ticket:T-C3E9D9B3]. The script always echoes the
  resolved instance id + region + IPs for the customer to confirm.

Docs (manual actions):

- [doc:https://help.aliyun.com/zh/ecs/user-guide/what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md]
- [doc:https://help.aliyun.com/zh/ecs/user-guide/common-operations-for-the-ecs-free-trial.md]
- [doc:https://help.aliyun.com/zh/ecs/user-guide/ecs-pay-as-you-go-starter-guide.md]

Out of scope: free trials of NON-ECS products (e.g. security products) that
start charging after the trial -- identify and hand off to the matching
product channel [ticket:T-56201A2E]. Plan/pricing recommendations
("cheap yearly plan") are commercial topics -- hand off.

## 2. Spot (preemptible) instances

Reclamation facts:

- A spot instance can be reclaimed AUTOMATICALLY by the platform when
  inventory or price conditions change. Customers experience this as "my
  instance disappeared, I did not release it" [ticket:T-7D84AD37].
- The release/reclamation FACT and TIME are evidenced from the query side
  (full-status events / billing records when available); the specific
  reclamation REASON (price vs inventory vs protection period) is NEVER
  asserted -- no verified API field carries it in this tier [design rule].
- Spot instances are not a long-term storage vehicle: they can be released
  at any time and are only suitable for short-term, interruptible workloads
  [ticket:T-B12C03B4].

Data retention after reclamation:

- Without snapshots/images, reclaimed-instance data is unrecoverable -- same
  verdict as a normal release [ticket:T-7D84AD37].
- Retained block storage rules after reclamation
  [ticket:T-78D54558]:
  - a custom image requires a SYSTEM-disk snapshot;
  - a retained system disk can only be re-attached as a DATA disk;
  - the disk and the new instance must be in the SAME zone.
- Prevention at creation time: set the spot "interruption mode" to the
  economical (savings) stop mode, so a reclamation stops the instance
  instead of releasing it immediately, preserving the data environment
  [ticket:T-7D84AD37].

Docs:

- [doc:https://help.aliyun.com/zh/ecs/user-guide/preemptible-instance-data-retention-and-data-recovery-after-interrupt-reclamation.md]
- [doc:https://help.aliyun.com/zh/ecs/user-guide/create-a-spot-instance]
- [doc:https://help.aliyun.com/zh/ecs/user-guide/economical-mode]

## 3. How the script reports these forms

- The instance report echoes `SpotStrategy` verbatim and adds the
  reclamation-risk note when the instance is spot.
- Free-trial instances appear as normal pay-as-you-go instances; the
  billing-stop matrix and the "still charging?" answer follow
  `billing-stop-matrix.md`.
- Neither form changes the core verdicts: no snapshot/image -> no recovery;
  payment cannot unlock data the platform never stored
  [ticket:T-F829BAC4].
