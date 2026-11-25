# Migration checklist: region / data-center decommission and forced migration

Scope: the customer's instance is affected by a region or availability-zone retirement,
or a platform-initiated migration. The customer performs every step themselves; this
skill only reads instance facts and lays out the path. See the boundary notes at the end.

Related playbooks: [incident and SLA](incident-sla-guide.md),
[fees and refunds](billing-dispute-guide.md), [hand-off boundaries](handoff-boundaries.md).

## What the platform does and does not do

- A decommission notice does NOT move your workload for you, and taking the old region
  offline does NOT automatically bring your website back online.
- The cross-region move is a self-service sequence built on custom images.
- Residual-value or equal-amount vouchers are NOT issued automatically; a business or
  billing specialist reviews and issues them. This skill only prepares the request.

## The five self-service steps

1. Create a custom image from the source instance (source region).
   Entry: ECS console > Instances > select instance > More > Disk and Image > Create Custom Image.
   Doc: https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance
   Expect: a new `m-xxxx` image in Available state in the source region.
2. Copy that custom image to the target region.
   Entry: ECS console > Images > select the custom image > Copy Image > pick target region.
   Doc: https://help.aliyun.com/zh/ecs/user-guide/copy-an-image
   Expect: after the copy task succeeds, the same image id appears in the target region.
   If it does not appear yet, the copy is still running or the wrong destination was chosen;
   re-check the copy task status and the region before continuing.
3. Create a new instance in the target region from the copied image.
   Doc: https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-imag
   Re-create security groups in the target region, then restore application data and config.
4. Verify the new instance actually serves the workload BEFORE touching the old one.
   Test the service on the new public IP, then repoint DNS / EIP / any allow-lists.
5. Only after step 4 passes, retire the old instance. Releasing it is irreversible and
   deletes its data. Confirm remaining paid value with a specialist first.

Read-only fact the skill provides: instance existence, Status, RegionId/ZoneId, and charge
type for the source instances in the region you pass, to ground steps 1 and 5. It cannot
see the decommission timeline or the host-release schedule; treat those as things the
customer reads from the official notice.

## Completion-evidence checklist (to prove the loop closed)

- [ ] source custom image id (`m-xxxx`)
- [ ] copy destination region and the copied image id
- [ ] new instance id and the image id it is running
- [ ] public reachability test on the new instance (customer-run `curl` / browser screenshot)
- [ ] old instance retirement confirmation, dated only after the items above are green

## Costing caveats raised in real tickets

- The system disk has a minimum size, and splitting orders can change the price, so an
  identical re-build is not always a 1:1 cost. Do not assert a number; hand the specifics
  to a specialist.
- Keep the old instance until the new one is proven. Releasing early loses the fallback.

## Boundaries (do not overclaim)

- This skill does not build images, copy images, order instances, verify reachability by
  itself, or retire the old instance. Those are the customer's console actions.
- Compensation is a manual business/billing decision; this skill only assembles evidence
  and points to the human channel.
