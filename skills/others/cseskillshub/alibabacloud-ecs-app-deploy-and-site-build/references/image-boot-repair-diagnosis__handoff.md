# Boundary handoffs and guided self-repair paths

This tier answers three things — detection-item interpretation, repair-task
failure diagnosis, boot-failure root-cause mapping with guided repair and
read-only re-verification. Anything beyond those axes gets a named exit,
not an answer. Relay the matching script when a route fires.

## Handoff table

| Customer wording that fires the route | Where it goes | Script to relay |
| --- | --- | --- |
| "storage fee / traffic fee for images", "can I delete the old image", "resource package deduction", "download cost" | `alibabacloud-ecs-image-billing-cleanup` (billing axis) | Image, snapshot and OSS billing, and whether an old image can be deleted, belong to the billing axis. Keep only the directly relevant fact here: repair orders postpaid resources, hence the balance threshold. |
| "the Cloud Assistant agent is offline / a command cannot run / agent needs upgrading" | `alibabacloud-ecs-cloud-assistant-diagnosis` | Detecting that an agent is *absent from the image* is this skill; installing, upgrading or debugging the *running agent* is the Cloud Assistant axis. |
| "instance stuck in Starting / Stopping / Pending", "cannot stop or force-reboot it" | `alibabacloud-ecs-instance-start-stop-anomaly` | Lifecycle state-machine faults come before any image-content verdict: once the state is healthy, boot-failure root-cause analysis continues here. |
| "the repair failed the same way for days, on a fresh snapshot too" (suspected platform-side) | Human support ticket | Platform-side image-service faults are invisible to every read in this skill; say exactly that and file the ticket with this report attached. |
| "convert the VMDK for me", "download the image to my laptop" | Official import doc + customer-local tooling | Conversion and export run on the customer's machine; give the format requirement mapping and the doc link, never improvised tool flags. |

Adjacent batch tiers referenced above are named by their skill names; if a
name changes before release, update this table and the `description`
"Do NOT use" line together.

## The repair this skill does NOT execute (class C, customer-run)

The verified ticket evidence for this tier was closed by support staff
performing console write operations (attach a repair disk, regenerate the
bootloader, reboot the instance). Those operations stay outside this skill
by design; what this skill provides is the two documented self-service
paths, the risk statements, and the read-only recheck afterwards.

### Path 1 — console diagnostic page with a live/PE repair disk

The instance's console diagnostic page offers mounting a PE/live repair
environment for the stopped instance, from which the bootloader can be
regenerated (wording from a verified support answer for a Debian GRUB
case; no official URL was verified in this batch, so describe the console
entry and do not fabricate a link).

### Path 2 — system disk on another instance, chroot

Detach the system disk from the broken instance, attach it as a data disk
to a healthy Linux instance, mount it, `chroot` into it, regenerate the
GRUB configuration, then unmount, detach and reattach to the source
instance. Every step is a customer console action with the risk
statements below. (Also from the verified support answer; this is the path
support staff used when the customer asked "can I do this myself?".)

### Risk statements to relay BEFORE the customer starts either path

- both paths require stopping the instance: business interruption, and
  in-memory data not yet flushed is lost — stop applications gracefully
  first;
- a snapshot backup before any repair is strongly recommended — and a
  snapshot is a billed feature: state that before they take one, citing
  <https://help.aliyun.com/zh/ecs/product-overview/snapshots-1>;
- on a Debian-style kernel-upgrade GRUB break, the newer kernel may boot
  fine once the configuration is regenerated (the verified case confirmed
  the 6.12 kernel worked after the fix): regenerating the bootloader
  configuration, not rolling back the OS, was the cure.

## Post-repair verification loop (this part IS this skill)

1. `verify-repair` read-backs: image record status, instance lifecycle
   status;
2. the customer confirms the OS reached its login/system stage;
3. the whitelisted guest checks that started the thread (mount targets,
   agent presence) re-run against the fixed system;
4. if the image was rebuilt: the customer re-triggers detection in the
   console and pastes the new report back for `analyze-report`.

## Requests with no owner above

Anything else (pricing negotiations, refunds, OS-level application
troubleshooting, security incidents) is outside every route in this table:
state the boundary, name the console entry or the right skill family, and
offer the human-ticket handoff.
