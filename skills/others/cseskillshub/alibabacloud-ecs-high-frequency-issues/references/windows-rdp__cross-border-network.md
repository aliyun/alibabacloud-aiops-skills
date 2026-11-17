# Cross-border public path (mainland <-> overseas)

When a Windows instance sits in an overseas region (or cn-hongkong) and the
customer connects from mainland China — or the reverse — the failures are often
**not** fixable on the instance at all. The public internet path across the
border is subject to international-link congestion and carrier egress routing
limits; its quality is not something the ECS control plane can guarantee. This
is one of two hard "cloud-side uncontrollable" edges of this tier (the other is
the customer's own device / local network).

## How the branch shows up

* The server-side facts are clean: instance `Running`, a public IP, the security
   group allows the port, the guest listener is up — yet `mstsc` from mainland
   China times out or drops intermittently.
* Other instances in the same overseas region "sometimes work" and the customer
   reasonably asks "why do my other HK machines work then?" — variable public
   path, not a per-instance defect.
* A customer on a *second* mainland network or on the same-region link connects
   fine, which localizes the failure to the mainland-to-overseas segment.

## What this skill does

It states the boundary and the evidence, and offers mitigations to *route
around* the public path. It does **not** claim to fix the link, because on the
cloud side there is nothing to fix. The engineer wording the tickets used was:
"the server-side resources are normal and show no anomaly; the public path
across the border is uncontrollable".

## Mitigations to give the customer (in order of practicality)

1. **Use a channel that does not ride the flaky RDP session for critical work**
   — console Workbench / Session Manager for a command task, or the VNC rescue
   console, so a dropped path does not kill the session. See
   [vnc-rescue-and-channel-choice.md](windows-rdp__vnc-rescue-and-channel-choice.md).
2. **Jump from a same-side host**: connect with `mstsc` from another machine
   that is itself in the same overseas region, so the last hop is local to the
   instance.
3. **Move the workload closer to the users** — migrate / re-buy the instance in
   a mainland region (or the user's side). This is a change-and-billing decision
   the customer and their business owner make; the skill only names it as the
   root-level option and does not perform any migration.

## Say it plainly to avoid false hope

Do not tell the customer the account, the security group or the instance will
"fix" cross-border latency once this branch is recognized. Report it as a known
path limitation with the mitigations above, and record that server-side checks
passed — so nobody restarts the instance chasing a network-segment problem.
