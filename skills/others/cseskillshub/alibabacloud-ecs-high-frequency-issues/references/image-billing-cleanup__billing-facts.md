# Billing Facts

The fact card behind every charge question in this scenario. Each fact carries
its official source. Answer from this file, not from memory, and never extend a
fact beyond what is written here.

## Price policy (read this first)

Never quote a unit price - not for snapshot storage, not for outbound traffic,
not for a marketplace image. Numbers quoted in past support conversations go out
of date and differ by region and by contract. Give the billing formula, give the
official document, and send the customer to their own bill details for the exact
amount:

- Bill details, filterable by billing item:
  https://billing-cost.console.aliyun.com/finance/expense-report
- This skill reads no bill and no pricing API; it has no permission for either.

## Image and snapshot charges

1. A custom image is not billed as a separate object. Creating a custom image
   creates snapshots of the disks included in the image, and the storage charge
   you see comes from those associated snapshots.
2. Snapshot storage is billed by stored capacity multiplied by storage duration.
   Creating a snapshot is free; keeping it is not.
3. There is no free quota for the snapshot storage produced by a custom image.
4. Billing is not per image count. Several images cost according to the data
   volume they actually store, so a large number of small images is not
   automatically expensive and one large image is not automatically cheap.
5. Image and snapshot are not charged twice for the same data.
6. Free public images provided by Alibaba Cloud carry no image fee, and self-made
   custom images carry no image fee either - only the snapshot storage above.
7. A paid marketplace (third-party) image carries an image-product fee on top of
   the instance and storage charges. It follows the marketplace product's own
   pricing and billing cycle and appears as its own image-related bill entry.

Sources: https://help.aliyun.com/document_detail/56159.html and
https://help.aliyun.com/zh/ecs/images.md

## Stopping the charges

8. Deleting the image alone does not stop the charges: its associated snapshots
   stay in the account and keep accruing storage fees until they are deleted too.
9. Order matters. A snapshot that was created as part of a custom image cannot
   be deleted while that image still exists. Either delete the image and tick the
   option that also deletes its snapshots, or delete the image first and then the
   snapshots.
10. Deletion is irreversible. A deleted snapshot or image cannot be restored, and
    the data cannot be recovered by anyone afterwards.

Sources: https://help.aliyun.com/document_detail/25466.html#steps-ghh-wz7-w49 and
https://help.aliyun.com/document_detail/128131.html#b0bc4fe212sax

## What deletion does and does not affect

11. Deleting an image or a snapshot does not disturb running instances created
    from them. What is lost is a future ability: the system disk of those
    instances can no longer be re-initialized from that image, and a disk can no
    longer be rolled back to that snapshot.
12. Releasing an instance does not delete its custom images or snapshots; they
    stay in the account and keep accruing storage fees until manually deleted.
13. In a cross-account transfer or migration, custom images and snapshots do not
    move with the instance. They remain in the source account, and the source
    account keeps paying for them. The instance charges follow the instance to
    the target account.
14. After a release, a spot reclaim or a transfer, re-run the cleanup inventory
    in every region that was ever used - images and snapshots are region-scoped
    objects and are easy to forget.

Sources: https://help.aliyun.com/document_detail/2983150.html#0a5290309ey60 and
https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance

## Fee attribution - is this charge really an image charge?

| Bill entry | What it covers | Image or snapshot charge? |
| --- | --- | --- |
| Block storage | Cloud disks AND snapshot storage, including the snapshots behind a custom image | Snapshot part yes, disk part no |
| `NetworkOut` | Public outbound traffic; inbound traffic is not billed | No |
| Image product | A paid marketplace image's own product fee | Yes, marketplace only |
| Instance | Compute of the instance itself, by its billing method | No |

15. A bill that grew right after images or snapshots were deleted is frequently
    driven by a different item, most often public outbound traffic. Attribute by
    billing item before concluding anything, and let the customer filter their own
    bill details by item.
16. Traffic direction decides the charge: traffic leaving the instance to the
    internet is billed, traffic coming in is not. An instance that calls its own
    public address from inside produces billable outbound traffic.

Sources: https://help.aliyun.com/zh/ecs/billing-item-faqs#title-be2-euh-gea and
https://help.aliyun.com/zh/ecs/public-bandwidth

Investigating what a process inside the instance is doing - web server logs,
application configuration, self-calls over a public address - is outside this
skill's command whitelist. Report the attribution, then hand that part to human
support.

## Exporting and moving data out

17. Windows images cannot be exported because of licensing restrictions. To move
    data off a Windows instance, copy files over a remote-desktop session or use
    a server-migration tool.
18. Linux custom images can be exported. Exporting depends on OSS, so it incurs
    OSS storage and download-traffic fees on top of any image cost.
19. There is no free retrieval channel for a stopped or overdue-locked instance.
    Both realistic paths cost money: renew temporarily to restore access and copy
    the data off, or export a custom image through OSS. If the snapshots were
    already deleted, nobody can recover the data - say so plainly and hand the
    case to human support.

Source: https://help.aliyun.com/document_detail/58181.html#cea82809bfi7o

## Spot instances

20. A spot instance's data retention follows the spot rules: an image can only be
    created from a disk that has a snapshot, and a retained cloud disk can be
    attached to a new instance in the SAME zone but only as a data disk - a former
    system disk cannot become a system disk again. Create a fresh snapshot backup
    before any reuse operation.

Source: https://help.aliyun.com/document_detail/439255.html

## What this skill cannot see

- Snapshot object-level details: per-snapshot capacity, retention policy and the
  exact fee of one snapshot. The inventory prints the snapshot IDs attached to
  each image and nothing more; for the numbers use the console snapshots page.
- Bill amounts, invoices, orders, refunds and vouchers.
- The history of an instance that was already released, including when it was
  released and whether an image was made before the release.

State each of these as a limitation of the run instead of estimating a value.

## Sensitive data before keeping or sharing

Before an image or snapshot is kept, shared or handed to another account, check
that it does not carry credentials, keys or customer data that must not leave the
account:
https://help.aliyun.com/zh/ecs/user-guide/avoid-images-and-snapshots-from-accidentally-revealing-sensitive-information-1.md
