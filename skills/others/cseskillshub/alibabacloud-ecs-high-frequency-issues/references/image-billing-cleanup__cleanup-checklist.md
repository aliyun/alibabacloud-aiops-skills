# Cleanup Checklist

How to turn an inventory into a decision the customer can act on. The inventory
lists and explains; the customer deletes. Nothing in this file is executed by the
skill.

## Step 1 - run the inventory per region

```
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py inventory --region <RegionId>
```

Images and snapshots are region-scoped. Run this once for every region the
customer ever used, including regions used only for a migration, a clone or a
temporary test - that is where forgotten leftovers usually are.

To keep the candidate list, add `--save-list <new-file>` together with
`--confirm`. That writes a brand-new file inside the system temporary directory;
it refuses to overwrite any existing file, it touches no cloud object, and it is
reversible by deleting the file. It is a gated action, so tell the customer what
will be written and where before adding `--confirm`.

## Step 2 - read the verdicts

| Verdict | What it means | What to tell the customer |
| --- | --- | --- |
| `IN_USE_BY_INSTANCE` | An existing instance still runs this image | Deleting it does not harm the running instance, but that instance's system disk can no longer be re-initialized from this image. Keep it, or accept the lost reset ability |
| `CLEANUP_CANDIDATE` | No instance in this region references it | Safe to consider. Deletion is manual, irreversible, and stops the storage charges only if the associated snapshots go too |
| `CREATE_FAILED_CANDIDATE` | Image creation failed | The failed object can usually be removed in the console; check whether a snapshot created for it survives and is still billed |
| `CREATING_WAIT` | Still being created | Wait until it is available; an image under creation cannot be deleted |
| `MARKETPLACE_REVIEW` | Marketplace image | Its image-product fee follows the marketplace product's pricing. Review the subscription and the bill entry first, and note that a running instance on a paid marketplace image blocks unsubscription and conversion |
| `SHARED_NOT_OWNED` | Shared into this account by another account | It cannot be deleted here and produces no image fee here; the owning account must withdraw the share or delete it |
| `PUBLIC_IMAGE_KEEP` | Public image from Alibaba Cloud | No image fee, cannot be deleted, no action |
| `ABNORMAL_STATE_REVIEW` | Non-standard status | Review manually in the console; never treat it as a safe candidate |

A shared image can also be the reason a deletion is refused in the console. The
share is managed by the owning account:
https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-modifyimagesharepermission.md

An image produced by an image build template is removed through the template
page, not through the ordinary custom-image list:
https://help.aliyun.com/zh/ecs/user-guide/view-and-execute-an-image-template.md

## Step 3 - the pre-deletion checklist

Work through every line with the customer before anything is deleted.

- [ ] The region is confirmed, and the inventory was run in every region used.
- [ ] The account is confirmed (`python3 scripts/areas/image_billing_cleanup/sts_token.py`): after a
      cross-account transfer the leftovers sit in the SOURCE account.
- [ ] No instance still needs the image, or the customer accepts losing the
      ability to re-initialize that system disk from it.
- [ ] A current backup exists for every disk whose content still matters. Create
      it first - through the gated `snapshot-backup` mode after approval, or in
      the console: https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot
- [ ] The customer knows the deletion is irreversible and that the data cannot be
      recovered afterwards.
- [ ] The image does not carry credentials, keys or customer data that must not
      leave the account:
      https://help.aliyun.com/zh/ecs/user-guide/avoid-images-and-snapshots-from-accidentally-revealing-sensitive-information-1.md
- [ ] If the guest-side question is "is there anything left in there I still
      need", answer it with a gated inspection command (`guest-check`) or ask the
      customer to run it in Workbench and paste the output. Do not guess.

## Step 4 - deletion order

Deletion happens in the console, by the customer. Print the order exactly:

1. Delete the custom image first. A snapshot that was created as part of a custom
   image cannot be deleted while that image still exists. In the deletion dialog,
   tick the option that also deletes the associated snapshots if the customer
   wants them gone in one step.
2. Then delete any remaining snapshot that is still billed.
3. Deleting the image alone does not stop the charges - the snapshots stay and
   keep accruing storage fees. This is the single most common reason a customer
   says "I deleted the image but I am still being charged".
4. Deleting an image or a snapshot does not disturb running instances; it only
   removes the ability to re-initialize a system disk from that image or to roll a
   disk back to that snapshot.

Console guides:
https://help.aliyun.com/document_detail/25466.html#steps-ghh-wz7-w49 (custom
image) and https://help.aliyun.com/document_detail/128131.html#b0bc4fe212sax
(snapshot). Also see
https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1.md

## Step 5 - the leftovers people forget

- Images and snapshots created for a migration, a clone or a temporary test
  region, long after the project ended.
- Images and snapshots left in the SOURCE account after a cross-account
  transfer: they do not move with the instance and keep billing there.
- Objects left after releasing an instance, including a spot reclaim.
- A snapshot created for an image whose creation failed.
- An elastic public IP or bandwidth plan that survived an instance
  unsubscription.
- A backup snapshot created during this very cleanup, once it is no longer
  needed. Deleting it later is irreversible, so let the customer decide when.

Retention rules after a release or a spot reclaim:
https://help.aliyun.com/document_detail/2983150.html#0a5290309ey60 and
https://help.aliyun.com/document_detail/439255.html

## Wording to use verbatim

- "Deleting this image or snapshot cannot be undone, and the data cannot be
  recovered afterwards. Deleting it does not affect your running instances; what
  you lose is the ability to reset a system disk back to this image or roll a
  disk back to this snapshot."
- "Deleting the image by itself does not stop the charge. The snapshots behind it
  stay in your account and keep billing until they are deleted too."
- "I can list what is safe to remove and in which order. I will not delete
  anything for you - deletion stays in your console, in your hands."

## Limits of this inventory

- Snapshot-level capacity, retention policy and per-snapshot fee are not
  queryable here; the inventory prints only the snapshot IDs attached to each
  image. For the numbers use the console snapshots page.
- Bill amounts are never read by this skill; use the bill details and filter by
  billing item (see [billing-facts.md](image-billing-cleanup__billing-facts.md)).
- An instance that was already released cannot be inspected. Its release time and
  the question "did I make an image before releasing it" are answered from the
  customer's own console history, not from this skill.
- An empty result is a legitimate result: it means the account has no custom,
  shared or marketplace image in that region. Report it as such instead of
  widening the query on your own.
