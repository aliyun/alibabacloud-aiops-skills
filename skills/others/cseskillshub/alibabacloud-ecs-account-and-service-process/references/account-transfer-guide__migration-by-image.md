# M2 — Cross-account migration by shared custom image (the fallback path)

When `--assess` returns `TRANSFER_NOT_ELIGIBLE` (different verified entities,
campaign instance, blocked direction), the data still has a route: create a
custom image, share it, and rebuild on the target account. This module is the
canonical step list; `scripts/axes/account_transfer_guide/transfer_guide.py --guide image-migration`
emits the same content from `scripts/axes/account_transfer_guide/_constants.py`.

## Steps

1. **Create a custom image from the source instance** (source account, ECS
   console > Images > Create Custom Image). The instance keeps running;
   nothing on it changes.
2. **Cross-region? Copy the image FIRST.** Cross-account + cross-region
   sharing requires copying the custom image into the destination region
   before sharing. The copy creates new snapshots in the destination region
   — they **incur snapshot storage fees** and are **independently retained**
   there regardless of what later happens to the source image.
   Doc: `https://help.aliyun.com/zh/ecs/user-guide/copy-an-image`
3. **Share the image with the destination account UID.** The UID is the
   16-digit account number; the OWNER of each account reads their own via
   `python3 scripts/axes/account_transfer_guide/sts_token.py` (a UID cannot be looked up across
   accounts).
4. **On the destination account, use the shared image:**
   * **New instance** — purchase flow, select Shared Image. Doc:
     `https://help.aliyun.com/zh/ecs/user-guide/use-shared-images`
   * **Existing instance** — use the console entry named
     **"Replace Operating System (re-select image)"**. Use this standard
     wording: a real ticket showed that telling a customer to look for a
     "reset image" button caused a wasted round-trip, because that entry
     name does not exist in the console.

## Snapshot-first rule (mandatory, dialogue-verified)

Replacing the OS from an image **permanently destroys the existing
system-disk data**. Before guiding or performing step 4 on any existing
instance, back the current system disk up first:

* Doc basis: `https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot`
* Fee basis: snapshot storage bills as an independent item
  (`https://help.aliyun.com/zh/ecs/snapshots-1`).
* In this skill the backup is executable through the gated mode:
  `python3 scripts/axes/account_transfer_guide/transfer_guide.py --create-snapshot --region-id cn-hangzhou --disk-id d-xxxx`
  — it refuses to run until the agent has told the user *what runs / impact
  / reversibility* and the user approved this exact call (`--confirm yes`,
  valid for one call only).
* After the run: remind the user that snapshots keep billing until THEY
  delete them (this skill never deletes anything).

## What this path does and does not carry

| Carried by the image | NOT carried |
| --- | --- |
| System disk content (data + software) | The fixed public IP — the new instance gets a NEW IP |
| Data disks included in the image | EIPs, key pairs, snapshots and images themselves (they stay in the source account) |
| OS configuration | Discount / campaign eligibility (a discounted instance cannot re-join discount campaigns after moving) |

## SMC (mentioned, not scripted)

Some tickets also referenced the Server Migration Center (SMC) as an
alternative mover. This skill holds **no verified SMC procedure link**, so
v1 may only mention "SMC exists as another option" and must direct the
customer to confirm via the official documentation or a support ticket —
never fabricate URLs or parameters for it.

## Fee / risk statements to deliver with the plan

* Cross-region image copy → new snapshots → snapshot storage fees in the
  destination region from the moment the copy is created.
* OS replacement → original system-disk data unrecoverable without a
  snapshot — hence snapshot-first.
* The new instance bills under the TARGET account from creation; the source
  instance and its snapshots stay billable in the SOURCE account until the
  customer releases/deletes them manually (human steps only — this skill
  never releases or deletes).
