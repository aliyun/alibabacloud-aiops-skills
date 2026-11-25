# Encrypted ECS images and cross-account limits: the fact base

Every statement below is an English summary of a specific Alibaba Cloud
help page, read on the date given. The linked page is the authority; its
wording is Chinese and governs over this summary. Anything the cited pages do
not state is listed in section J as **not established** and must be answered by
customer self-check, never by assumption.

Verification date for all links in this file: **2026-09-18**.

## A. What "encrypted image" means

* An encrypted image is a custom image that has one or more **encrypted
  snapshots** attached; the image itself carries no separate encryption, it
  inherits the snapshot state.
  <https://help.aliyun.com/zh/ecs/user-guide/encrypt-custom-images-1.md>
* A custom image built from an encrypted snapshot is encrypted by default, and
  the key used is the key of that snapshot.

## B. Encryption is irreversible

* Only two transitions exist: unencrypted to encrypted, and encrypted to
  encrypted with a different key. **Encrypted to unencrypted does not exist.**
* Consequence for customers: there is no "decrypt and then export" or "decrypt
  and then share as plain". The only supported route to a plain image is to
  launch an instance from the encrypted image, move the needed data, and derive
  a **new unencrypted custom image** from that instance.
* Sources: the encryption page above, and the export FAQ
  <https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image.md>

## C. Two ways an image becomes encrypted

1. At launch time: an unencrypted image plus per-disk encryption (parameter
   `Encrypted=true`, optional `KMSKeyId`) produces encrypted disks; a custom
   image later taken from those disks is encrypted.
2. By copying: an **encrypted copy** applies encryption to every snapshot the
   image owns. Without an explicit key the service key is used for snapshots
   that were plain, and already-encrypted snapshots keep their original key.

The ECS service key alias shown in the console is `alias/acs/ecs`, and the
console key picker labels the default as `Default Service CMK`.

## D. Launching from an encrypted or shared encrypted image

* Disks backed by the image's encrypted snapshots are encrypted, the option
  **cannot be cleared**, and through the API the encryption parameter must be
  sent as `true`.
* For a **shared** encrypted image the same rule applies to the recipient, and
  the recipient may choose its own key. If the recipient has account-level
  default encryption enabled with a configured key, that key wins; otherwise
  the service key is used.
* Omitting the encryption flag when launching from a shared encrypted image is
  the documented cause of a failed launch request. This is the most common
  "the shared image is broken" report and it is a parameter problem, not a
  permissions problem.
* Source: <https://help.aliyun.com/zh/ecs/user-guide/encrypt-custom-images-1.md>

## E. Copying an encrypted image

Summarised on 2026-09-18 from the copy page
(<https://help.aliyun.com/document_detail/25462.html>) plus the encryption page;
confirm the wording on the page before quoting it to a customer.

* An encrypted image can only be copied as an encrypted copy; a plain copy is
  not offered for it. A plain copy only changes region.
* An encrypted copy may target the same region or a different one, and the key
  selected must exist **in the destination region**.
* Re-encrypting copies take longer than plain copies.
* A copy produces its own snapshots in the destination region. Those snapshots
  are billed and are kept independently of the source image.
* Copy progress is visible in the destination region image list; an in-flight
  copy whose image is still in progress can be cancelled from the console.

## F. Cross-account sharing rules

From <https://help.aliyun.com/document_detail/25463.html> and
<https://help.aliyun.com/document_detail/2838993.html>:

* Sharing works **within one region only**. To reach another region, copy the
  image to that region first, then share from there.
* An account can share only its own custom images. An image that was shared to
  this account cannot be shared on again.
* A custom image derived from a Marketplace image cannot be shared between a
  China-site account and an international-site account.
* Sharing is free, but if the ultimate source image is a paid image, the
  recipient is charged for the image when launching from it.
* Sharing does not consume the recipient's custom-image allowance; the sender
  owns the count, bounded by the quota in section G below.
* Only the owner can inspect or withdraw a grant. The recipient cannot change
  who else receives the image.
* A shared image stays in place until the share to that account is withdrawn;
  withdrawing the share is the documented prerequisite for cleaning the image
  up afterwards.
* Encrypted images may be shared, and a shared encrypted image can be used
  cross-account **in the same region**, provided the authorisation described at
  the end of this section exists.

### Authorisation required before an encrypted image can be shared

The owner account must grant the recipient account's ECS service access to its
KMS keys. Steps as documented:

1. In the **owner** account, a RAM role whose trusted entity is an Alibaba Cloud
   account, named `AliyunECSShareEncryptImageDefaultRole` for images
   (`AliyunECSShareEncryptSnapshotDefaultRole` for snapshots).
2. Edit the role's **trust policy** to admit the recipient's ECS service
   principal, of the form `<recipient-account-id>@ecs.aliyuncs.com`; for
   resource-directory sharing, use the `*@ecs.aliyuncs.com` principal with a
   condition on `sts:ServiceOwnerRDId` (whole directory) or
   `sts:ServiceOwnerRDPath` (one folder).
3. Grant KMS access to that role:
   * Image encrypted with a **customer master key**: a custom policy allowing
     `kms:List*` on `acs:kms:<key-region>:<key-owner-uid>:key`, and
     `kms:DescribeKey`, `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey`,
     `kms:TagResource`, `kms:UntagResource` on
     `acs:kms:<key-region>:<key-owner-uid>:key/<key-id>`.
   * Image encrypted with the **service key**: attach the managed policy
     `AliyunKMSFullAccess`.
4. Only then perform the share itself.

Separately, using a customer master key for ECS encryption at all requires the
default role `AliyunECSDiskEncryptDefaultRole`, offered by the console the first
time a customer-managed key is selected.

## G. Quotas and platform limits

From <https://help.aliyun.com/zh/ecs/user-guide/limitations.md>:

* `q_user-image-count` - custom images an account may keep in a region.
* `q_user-per-image-shared-user-count` - how many recipient accounts a single
  custom image may be shared with. This is the ceiling that produces "the share
  was refused" reports; it is raised from Quota Center, not from the image page.

Quota lookup and adjustment: <https://help.aliyun.com/document_detail/184116.html>
and <https://quotas.console.aliyun.com/products/ecs/quotas>.

## H. What the read-only API can and cannot prove here

Provable with `DescribeImages` (response shape verified on 2026-09-18 from
<https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-describeimages.md>):

* `DiskDeviceMappings.DiskDeviceMapping[].Encrypted` - per-snapshot encryption
  flag, which is how this skill decides "is this image encrypted".
* `IsSelfShared` - whether this own image has ever been shared out.
* `ImageOwnerAlias` - `self` (own custom), `others` (shared to you, or a
  community image), `system` (published), `marketplace`.
* `ImageOwnerId` - owning account, honoured only for shared and community
  queries; elsewhere the API answers
  `InvalidOperation.ImageOwnerIdUnsupported`.
* `Status` and `Progress` - `Creating`, `Waiting`, `Available`, `UnAvailable`,
  `CreateFailed`, `Deprecated`; the request default is `Available`, so an
  in-flight image is invisible unless `ALL` is queried. `Waiting` means the task
  is queued, not failed.
* `DiskDeviceMapping[].Progress` and `RemainTime` - per-snapshot copy progress.
* `Usage`, `IsCopied`, `IsPublic`, `Size`, `OSType`, `Architecture`, `Platform`.

**Not** returned by the actions this skill calls, so never claimed from them:

* the KMS key id behind an encrypted mapping;
* the list of accounts an image was shared to;
* anything in the peer account, in any region, under any credential this skill
  does not hold.

Quotable error literals for this symptom axis, each read from the official error
table of the operation that returns it: `InvalidOperation.ImageOwnerIdUnsupported`,
`InvalidImageOwnerAlias.PublicImageUnsupported`, `InvalidFilterKey.NotFound` and
`MissingParameter.Status` from the `DescribeImages` error table;
`IMAGE_ALREADY_EXIST` from the export FAQ, meaning an object of the same name
already exists in the target OSS bucket; and `NoPermission` / `ImplicitDeny` for
authorization failures. Quote one only when a report or the customer's own
message actually contains it.

## I. Export restriction (adjacent symptom, used for identification)

From <https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image.md>:

* Encrypted custom images **cannot be exported**. Neither can custom images
  derived from Marketplace images, nor Windows Server images.
* Export needs an OSS bucket in the same region as the image, standard or
  infrequent-access storage class.
* A failed export task carries an error code readable in Task Management; a
  name collision on the object returns `IMAGE_ALREADY_EXIST`, fixed by changing
  the bucket or the file-name prefix.

## J. Not established by the cited documents

Do not assert these; hand them to the customer as self-check items or back to a
human queue.

* Whether a **recipient** of a shared encrypted image may copy it into another
  region: the share page and the copy page do not state the combination.
* Whether KMS request fees created through the share role are billed to the key
  owner or the recipient.
* How long an accepted share takes to appear in the recipient's console.
* Whether the trust policy can name a RAM role of the recipient instead of the
  recipient's ECS service principal.
* Any per-region availability of encrypted-image sharing features, and any
  behaviour of accounts created after the documents were last revised.
