# Console guidance the customer performs

This skill performs none of these steps. Each block is the fixed five-element
shape the report prints: **entry point**, **object**, **action**, **expected
result**, **rollback** - plus the risk notice that must accompany it. Fill the
placeholders from the evidence section of the report; never fill one from memory.

Rule of construction: quote the linked help page for any detail this file leaves
as `<...>`; an unfilled placeholder is reported as "not covered by the cited
documentation", which is a valid answer, whereas a guessed one is not.

---

## 1. Share an encrypted custom image with another account

**Precondition gate.** If the report shows `encryption=encrypted`, this step must
be done **before** the share, or the recipient will not be able to use the image.

*Entry point (owner account).* RAM console <https://ram.console.aliyun.com/roles>,
then ECS console Images page
<https://ecs.console.aliyun.com/image>.

*Object.* The owner account's role `AliyunECSShareEncryptImageDefaultRole`, the
image `<ImageId>` and its snapshots `<SnapshotId...>`, and the recipient main
account ID `<peer-account-id>`.

*Action.*
1. In the owner account, ensure the role `AliyunECSShareEncryptImageDefaultRole`
   exists with an Alibaba Cloud account as trusted entity.
2. In its trust policy, add the principal `<peer-account-id>@ecs.aliyuncs.com`;
   for an organization, use `*@ecs.aliyuncs.com` with the condition
   `sts:ServiceOwnerRDId` (directory) or `sts:ServiceOwnerRDPath` (folder).
3. Attach the KMS grant matching how the image is encrypted: a custom policy for
   a customer master key (see `image-encryption-basis.md` section F), or
   `AliyunKMSFullAccess` for the service key `alias/acs/ecs`.
4. On the Images page, with the correct resource group and region selected, open
   the **Custom Images** tab, find `<ImageId>`, and use **Share Image** in the
   Actions column; enter `<peer-account-id>`, accept the security confirmation.

*Expected result.* The image appears in the recipient account's **Shared Images**
tab **in the same region**, and hovering the share icon on the owner side lists
`<peer-account-id>` with a share time.

*Rollback.* Withdraw the share from the same Custom Images row. Do not withdraw
the role or the KMS grant until every image that depends on it is unshared, or
already-running instances launched from those images lose their key access path.

*Risk notice to state before guiding.* Sharing makes the image's disk contents
readable to another account through any instance it launches from: clean SSH
keys, shell history, credentials and temporary files from the image first. The
grant is KMS-level, so an over-broad key policy exposes every encrypted snapshot
the owner account holds, not just this image. If the source image is a paid
image, the recipient is billed for the image on launch.

---

## 2. Copy an encrypted image to another region (or re-key it)

*Entry point.* ECS console Images page
<https://ecs.console.aliyun.com/image>, **Custom Images** tab, Actions column >
**Copy Image**.

*Object.* Image `<ImageId>`, destination region `<destination-region>`, and a key
that already exists in that destination region (or the service key).

*Action.* Choose the encrypted copy type, select `<destination-region>`, select
the key, give the new image a name, confirm.

*Expected result.* A new custom image in `<destination-region>` whose status is
`Creating` with a rising progress percentage, later `Available`. Per-snapshot
progress and remaining time are readable by re-running this script against the
destination region.

*Rollback.* While the copy is still in progress, cancel it from the image row.
After completion, the new image and its own snapshots remain until the customer
removes them, and they keep being billed; the source is untouched.

*Risk notice.* Re-encrypting is slower than a plain copy. The copy creates real
snapshots in the destination region, so expect additional snapshot storage cost,
independent of the source. Encryption cannot be reversed, so a copy can never
produce an unencrypted image.

---

## 3. Launch an instance from a shared encrypted image (recipient side)

*Entry point.* Recipient account, ECS console Images page to confirm visibility,
then the instance purchase page.

*Object.* The shared image `<ImageId>` as seen in the recipient account, in the
same region the owner shared it in.

*Action.* Select the image, keep disk encryption enabled (it is not
deselectable for the encrypted snapshots of that image), optionally choose the
recipient's own key, and complete the order. Through the API, the disk
encryption parameter must be sent as `true`.

*Expected result.* The instance launches and its disks are encrypted; if the
recipient has account-level default encryption with a configured key, that key is
used, otherwise the service key.

*Rollback.* None needed: a launch that fails on the encryption parameter creates
no resource. An instance that did launch stays an ordinary instance the customer
manages under their own account.

*Risk notice.* A missing encryption parameter is the documented reason such a
launch request fails; it is not a permission failure, so do not widen policies
for it. The image content is only as trustworthy as its owner: it is another
account's disk image.

---

## 4. Explain why an image cannot be exported or de-encrypted

*Entry point.* ECS console Images page, **Custom Images** tab, Actions column >
**Export Image**; and Task Management
<https://ecs.console.aliyun.com/task/region> for failed tasks.

*Object.* Image `<ImageId>` whose report line reads `encryption=encrypted`.

*Action.* None. Tell the customer the exclusion is a platform limitation:
encrypted custom images, Marketplace-derived custom images and Windows Server
images are not exportable, and encryption is irreversible so there is no
decrypt-then-export path.

*Expected result.* No export task is offered for an encrypted image.

*Rollback.* Not applicable; nothing was changed.

*Risk notice.* The supported alternative is a round trip: launch an instance from
the encrypted image, copy the needed data onto unencrypted storage, then take a
new unencrypted custom image from that instance and export that. That route moves
plaintext data onto new disks, so it must be done in a controlled window with the
customer's own key material handling.

---

## 5. Check the sharing quota before a share is refused

*Entry point.* Quota Center for ECS
<https://quotas.console.aliyun.com/products/ecs/quotas>.

*Object.* `q_user-per-image-shared-user-count` (recipients per image) and
`q_user-image-count` (custom images kept per region).

*Action.* Read the current value and usage, and raise the limit from the same
page if the customer is at the ceiling.

*Expected result.* The share attempt succeeds once the ceiling is raised, or the
customer reduces the number of recipients.

*Rollback.* Not applicable; a quota increase has no destructive effect, but the
raised ceiling persists and is billed only for what is used.

*Risk notice.* Quota increases are subject to approval and to account-level
limits; do not promise a specific new ceiling.
