# Instance-Family Isolation, DDH and Capacity Reservation (Cluster B)

Rule-based answers for "is my instance shared or dedicated", "why is one instance
slower than another of the same type", "which families avoid CPU contention", and
"how do Dedicated Host / capacity reservation / elasticity assurance help". The
entry script classifies the family from real `DescribeInstances` data (or from a
supplied instance type) using the embedded table; this module explains the rules
and the selection paths.

Verification date: 2026-08 (per the tier requirements document). Family
classification is version-sensitive; re-verify against the official instance-family
documentation before publishing.

## CPU isolation model (shared vs burstable vs dedicated)

- SHARED families: the physical CPU is shared with other instances on the same
  host. A noisy neighbor running a heavy load can slow your instance down even
  though your own usage looks normal. Shared / economy families in this tier
  include: `e`, `s6`, `xn4`, `n4`, `mn4`, `e4`.
- BURSTABLE families (`t` series, e.g. `t5`, `t6`): CPU-credit based - a baseline
  performance plus temporary bursts. The physical CPU is also shared, and sustained
  load above the baseline is limited when credits run out.
- DEDICATED families: the vCPU is exclusively scheduled and not shared with other
  tenants on the host. Common dedicated families include `g` (general), `c`
  (compute), `r` (memory), `u` (universal), and similar. Elastic Bare Metal (`ebm`)
  and Super Computing Cluster (`scc`) give a whole dedicated physical host.

The embedded classifier in `scripts/areas/ddh_capacity_guide/_constants.py` implements exactly this rule
(bare-metal first, then burstable `t`, then shared, then dedicated), so the
verdict is deterministic and reproducible rather than recalled from memory.

## Why two instances of the "same type" can perform differently

- Same type does NOT guarantee same performance. On shared / burstable families,
  contention from other tenants on the host explains most differences.
- On dedicated families, contention from other tenants is ruled out, but a real
  difference may still come from: the guest workload itself (a process saturating
  CPU / memory / disk), the storage performance ceiling (see
  performance-limits.md), or an underlying host issue.
- The host's real-time load, CPU steal and contention evidence are NOT visible to
  read-only APIs. When a dedicated-family difference cannot be explained from the
  visible facts, this skill says so and hands off to a ticket - it never asserts a
  host root cause it cannot see.

## Three isolation paths to completely avoid CPU contention

1. DEDICATED instance family (g / c / r / u and similar): vCPU exclusively
   scheduled. The simplest path; usually reached by reconfiguration (changing the
   instance type) or by launching new dedicated instances.
2. Dedicated Host (DDH): a physical server dedicated to a single account. You
   control instance placement, so no other tenant shares the physical CPU. Suits
   strict isolation, compliance and bring-your-own-license (BYOL) scenarios.
3. Capacity reservation / elasticity assurance: reserves capacity in a zone for a
   period so resources are guaranteed available when you launch or scale. This is
   a capacity-assurance product, not a per-instance isolation switch.

Changing an instance type, purchasing a Dedicated Host, or creating a reservation
are WRITE / purchase actions the customer performs in the console. This read-only
skill only compares the options and lists the steps; it never submits a change.

## Host migration (a common customer request)

Moving an instance to a different host has TWO customer self-service paths, so a
support ticket is not the normal route:

1. **System event driven redeploy.** After a `SystemMaintenance.Redeploy` or
   `SystemFailure.Redeploy` event, the customer redeploys the instance from the ECS
   console event entry, or with the `RedeployInstance` operation. Prerequisites:
   the instance is Running or Stopped, it is NOT hosted on a Dedicated Host, it has
   no security lock, and the account / instance is not in arrears past expiry.
2. **Dedicated Host / deployment-set placement.** To move an instance onto or
   between Dedicated Hosts (or onto a deployment set), optionally changing the
   instance type in the same operation, the customer calls
   `ModifyInstanceDeployment` with `InstanceId` and the target `DedicatedHostId`.

Both paths restart the instance: in-memory data is lost, local disks may be
re-initialized, the underlying hardware fingerprint changes, and third-party
license-bound software may need re-activation. Back up first.

Raise a human support ticket only when the platform itself has to investigate the
host hardware fault (for example the host is UnderAssessment / PermanentFailure and
the customer cannot move off it), or when the instance is in a locked state that
blocks self-service redeployment. Reading facts and executing a change remain
different things: this read-only skill explains both paths and never executes
`RedeployInstance` or `ModifyInstanceDeployment`.

## What this skill can and cannot confirm

- CAN (read-only): list the instances under the account+region, classify each
  family as shared / burstable / dedicated, read the instance's platform event
  record (`DescribeInstanceHistoryEvents`) and the Dedicated Host usage status of
  the host the instance reports (`DescribeDedicatedHosts`), and compare the three
  isolation paths with the official rules.
- CANNOT: see host load / steal / live per-neighbour contention (no read-only API
  exposes another tenant's usage), execute a reconfiguration, or perform a host
  migration. Availability of a target instance type for reconfiguration / purchase
  is a live check the customer does in the console (the `DescribeAvailableResource`
  action is reserved for a future version - see ram-policies.md).

## Sources

- Official ECS instance-family documentation and the Dedicated Host (DDH) user
  guide (Alibaba Cloud Help Center; from the tier help-search evidence
  https://help.aliyun.com/zh/ecs/user-guide/dedicated-hosts.md - re-verify the
  exact URL before publishing).
- Real support tickets in this tier (the shared-vs-dedicated family answer, the
  same-type performance-difference investigation, and the host-migration
  prerequisites and permission boundary).
