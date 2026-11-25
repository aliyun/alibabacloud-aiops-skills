# Customer-side console cards

Every step in this file is performed by the customer. This skill is read-only: it
holds no change permission, never acts on the customer's behalf, and must never be
worded as "done for you". Each card has the same five parts, and the order matters:
**entry**, **action**, **expected**, **risk gate**, **fallback**.

## The risk gate (applies to every card below)

Before a card that can destroy data or spend money, the customer confirms all of:

- A backup or snapshot of the affected disk exists. Snapshots are billed separately,
  as an independent item.
- They understand the action cannot be undone, and that a released system disk cannot
  be recovered.
- They personally read and accepted the amount shown on the page. This skill cannot
  see any amount.

Output the gate, wait for the confirmation, then give the steps. Skipping the gate is
a defect even when the steps are correct.

---

## Card 1: Stop the instance

- **Entry:** ECS console, Instances list, select the instance.
- **Action:** Stop. Choose the stop mode the workload can tolerate.
- **Expected:** the state reaches Stopped. Re-check with
  `python3 scripts/axes/marketplace_image_guide/ecs_marketplace_image_guide.py --region-id <region> --instance-id <id> --facts-only`,
  which prints the state from `DescribeInstanceStatus`.
- **Risk gate:** the workload is interrupted from this moment. A stopped instance can
  still be billed depending on the stop mode.
- **Fallback:** if it will not stop, stop here and raise a ticket with the instance
  identifier; a stuck instance is an instance-health problem, not an image problem.

## Card 2: Change the operating system

- **Entry:** Instances list, select the instance, image or operating-system change.
- **Action:** the instance must already be Stopped (Card 1). Select a public image, or
  the intended Marketplace image, and complete the order. When the target is a
  Marketplace image, the order payment is completed after the change is accepted.
- **Expected:** the instance reboots into the new system; re-run the entry script and
  confirm the printed `ImageId` is the new one.
- **Risk gate:** the original system disk is released. Every file, database and
  configuration on it is permanently deleted and cannot be recovered. Data disks are
  not deleted by this action but must be re-attached or re-mounted by the customer.
- **Fallback:** a payment failure on a stopped instance is not a status problem any
  more; collect the order details and use the billing route.

## Card 3: Read the image charge in the billing console

- **Entry:** Billing console, statements for the period in question.
- **Action:** filter for Marketplace and image line items.
- **Expected:** a line whose product name matches the image name printed by this skill.
  If it matches, the attribution is settled.
- **Risk gate:** none; read-only for the customer.
- **Fallback:** if the line does not match the attached image, or the customer disputes
  the attribution, raise a ticket with the instance identifier, the order numbers and a
  screenshot. This skill hands over its evidence block and submits nothing.

## Card 4: Self-service renewal-order cancellation

- **Entry:** the renewal and refund management page in the billing console
  (`https://usercenter2.aliyun.com/refund/renew-list`).
- **Action:** locate the instance and its pending renewal order.
- **Expected:** a cancellable entry with a visible refund amount.
- **Risk gate:** read the confirmation checklist out loud and get a yes on each item
  before the customer submits: refund reason; the exact instance identifiers; backup
  confirmed; the current expiry date understood; the on-page amount accepted. After
  cancellation the original expiry date reverts, refunds typically take about two
  business days, invoice quota is affected, and any promotional gift granted by the
  order is forfeited.
- **Fallback:** when a paid image is attached, a pending renewal order is not
  cancellable self-service at all. The manual route needs the customer to grant
  authorization in a ticket and a specialist to approve it. State that plainly; do not
  imply this skill cancelled anything.

## Card 5: Build a custom image and share it

- **Entry:** ECS console, Images, create a custom image from an instance; then share
  the image with the target account identifier.
- **Action:** create on the source, wait until the image reports available
  (`DescribeImages` prints `Status` and `Progress`), share with the destination
  account, and build a new instance there from the shared image.
- **Expected:** an equivalent instance in the destination account. Release the source
  only after the new instance is verified.
- **Risk gate:** the custom image is a point-in-time copy, so anything written after it
  was taken is missing. If the source is a paid image, the derived custom image can
  keep generating the licence fee.
- **Fallback:** if the image cannot be created or shared, raise a ticket; do not
  substitute a different migration path.

## Card 6: Move data out without exporting the image

- **Entry (Windows):** the Remote Desktop client, with local drive redirection enabled,
  then copy to the instance drive. See
  `https://help.aliyun.com/zh/ecs/user-guide/use-mstsc-exe-to-upload-a-file-to-a-windows-instance`.
- **Entry (Linux):** scp or sftp against the instance, or a file transfer tool.
- **Action:** copy the required paths out; the customer performs the transfer.
- **Expected:** files verified locally by size or checksum.
- **Risk gate:** needs the instance reachable and the correct credentials. Snapshots are
  the alternative and are billed separately.
- **Fallback:** if remote access itself is broken, that is an access problem, not an
  image-export problem; see `handoff.md`.

## Card 7: Adjust authorization for an image selection failure

- **Entry:** Resource Management console for the group contents; RAM console for
  policies. An administrator performs both.
- **Action:** confirm whether the selected Marketplace image appears inside the
  authorized resource group. It normally will not, because Marketplace images carry no
  group membership. Then either attach the Marketplace policy to the RAM user, or build
  a custom image from it and move that custom image into the authorized group.
- **Expected:** the operating-system change stops failing on the permission check.
- **Risk gate:** attaching a Marketplace policy widens a principal's reach; prefer the
  narrowest policy that works and review it afterwards. The paid-image fee follows a
  derived custom image.
- **Fallback:** if the failure persists, collect the request identifier from the error
  dialog and raise a ticket. This skill cannot read another identity's permission
  configuration.

## Documentation index

Titles and links below were carried in by the support evidence for this tier and were
not re-verified online at build time. If a link no longer resolves, search the title on
the help site rather than guessing a new URL.

| Topic | Link |
|---|---|
| ECS images, including image charge scope | `https://help.aliyun.com/zh/ecs/images` |
| Change the operating system of an instance | `https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance` |
| Cross-account instance transfer and its limits | `https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance` |
| Create a custom image from an instance | `https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance` |
| Export a custom image and its supported scope | `https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image` |
| Move a file to a Windows instance with mstsc | `https://help.aliyun.com/zh/ecs/user-guide/use-mstsc-exe-to-upload-a-file-to-a-windows-instance` |
| Change the preferred language of a Windows instance | `https://help.aliyun.com/zh/ecs/user-guide/change-the-preferred-language-of-a-windows-instance` |
| Create a snapshot | `https://help.aliyun.com/document_detail/25455.html` |
| Snapshot billing | `https://help.aliyun.com/document_detail/56159.html` |
| Refund rules | `https://help.aliyun.com/document_detail/116043.html` |
| Where a refund goes | `https://help.aliyun.com/zh/user-center/user-guide/refund-destinations` |
| ECS instance lifecycle states | `https://help.aliyun.com/zh/ecs/user-guide/overview-52.md` |
