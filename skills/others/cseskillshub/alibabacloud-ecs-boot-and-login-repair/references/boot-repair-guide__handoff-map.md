# Handoff map

A large share of tickets in this tier are not boot failures. Routing them out on the first turn, with the
evidence that supports the routing, is this skill's highest-frequency contribution. Every handoff below names
the target and the read-only artifact that justifies it, and never asks the customer to repeat evidence the
skill already collected.

## Routing table

| Symptom as observed | Target | Artifact that justifies the route | What this skill still does |
|---|---|---|---|
| Patch or vulnerability installation failed; the OS boots | `alibabacloud-ecs-patch-management` | Instance reachable and services running; an installer error code rather than a boot message | Identifies, hands off, and states the boundary: "it broke after the update" returns here |
| Update or repair fails with a disk-space error; the system volume is nearly full | Capacity skill | `df -h` or `Get-Volume` output showing the free space | Names capacity as the root axis and refuses to delete anything on the customer's behalf |
| Inode exhaustion, a filled log directory, a large-volume cleanup decision | Capacity skill | `df -i` and the largest-paths output | Notes that every cleanup step is destructive-capable and stays manual |
| Partition not visible after an expansion, MBR to GUID conversion needed, LVM volumes missing after a partition-table rewrite | `alibabacloud-ecs-disk-expand-diagnosis` | The reported size versus the visible partition and physical volume | Warns that a partition-table rewrite on Windows deletes data and that on Linux it usually does not, and that LVM metadata must be handled before converting |
| Instance parked in `Starting` or `Stopping`, a change that never completed, or a hypervisor-level problem | `alibabacloud-ecs-instance-state-diagnosis` | `DescribeInstanceStatus` unchanged across the observation window | States that a rescue disk cannot diagnose a control-plane state problem, so the customer does not repeat that attempt |
| Every access attempt fails because the disk is saturated | `alibabacloud-ecs-disk-io-diagnosis` | Throughput or IOPS counters pinned at the ceiling | Explains that a saturated system looks identical to a dead one, which is why it was tagged as a boot failure |
| Memory below the OS minimum presenting as a frozen or blue screen | Capacity or performance skill | Configured memory versus the published minimum for the reported release | Says the machine is not failing to boot |
| SSH or RDP fails while VNC shows a working desktop | Connection path | `Running` status plus desktop visible on console | Explains that the VNC channel is independent of the remote-desktop service, so a VNC success is not a contradiction |
| Login rejected with a lockout code, or a lost credential | Credential and security path | The lockout code, or a password-reset flow that reports unsupported on this image type | Notes that offline credential reset requires a stop, and points at the credential-management article |
| Blackhole after an attack, security-group edits, an inbound drop affecting every service | Security handling | Address-level reachability across unrelated services, or a known attack window | Supplies only the data-rescue sequence if the customer wants the data out |
| Ransomware, encrypted boot files, an extortion note | Security handling | File names carrying an unexpected extension, encrypted boot manager | Orders the steps so the evidence and the data are preserved before anything is rebuilt |
| A web server, application, or middleware problem after a reboot | The relevant application flow | The OS is up and only the service is failing | States that the boot path is healthy, which closes the boot question |
| Billing, refunds, transfers, image-creation practice, a purchase that must be changed | Commercial or manual handling | The request itself | Warns that a background automatic update can consume outbound traffic and therefore bill |
| An unrelated product line (for example a simple application server, or a container service) | That product's own flow | The product identifier in the request | Explains that snapshot cost and retention semantics differ per product, so ECS-specific cost advice is not reused |

## Handoff wording

Three sentences, in this order. Do not lead with "not our problem".

1. What the evidence shows, naming the artifact.
2. Why that places the problem on another axis than the boot path.
3. What the customer should invoke or ask for next, and what to hand over with it.

Example, capacity:

```
Evidence: the system volume reports under 1 GB free, and the update failure carries a disk-space error
code. That places the failure on the capacity axis, not the boot axis; the machine is starting.
Next: run the capacity workflow (or the expansion workflow if the volume needs to grow), and hand over the
free-space figure plus the failing operation. Nothing will be deleted on your behalf; every cleanup or
growth step is yours to approve and run.
```

Example, boot failure confirmed and staying here:

```
Evidence: the instance reports Running, but the console screen you transcribed shows a loader prompt, and
the block-device listing you pasted shows the boot partition present with a filesystem the loader names.
That is the boot-loader layer, which this skill owns.
Next: confirm a snapshot at 100 percent and approve a stop window, then take the ordered manual steps in
references/boot-repair-guide__grub-efi-repair-guidance.md. This skill will not run them for you.
```

Example, evidence not available:

```
Evidence: no screen transcription and no in-guest output, and the cloud fields are normal. Boot failure is
neither confirmed nor excluded.
Next: open the console session and transcribe the full screen text; that single artifact decides between
this skill and the connection path.
STATUS: DEGRADED
NEXT_ACTION: Customer supplies the console screen text and the snapshot state.
```

The last line matters most in the noisy cases: naming what the customer must supply prevents a loop where
each side waits for the other to look first.
