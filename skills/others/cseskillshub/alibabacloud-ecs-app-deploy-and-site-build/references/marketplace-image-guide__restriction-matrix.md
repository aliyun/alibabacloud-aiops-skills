# Restriction matrix: what a Marketplace or paid image blocks

Read this after `DescribeInstances` and `DescribeImages` have established two facts:
which image is attached, and whether it is a Marketplace or licence-charging image.
The verdict column is the same one the entry script prints.

Legend: **Blocked** = the console refuses the operation while that image is attached.
**Conditional** = allowed, but a precondition must be met first. **Not blocked** = the
image is not the cause, look elsewhere.

| Operation | Public free image | Paid public image (Windows, Red Hat, SUSE, Alibaba Cloud Linux 3 Pro) | Marketplace / third-party image | Custom image derived from a paid image |
|---|---|---|---|---|
| Switch subscription to pay-as-you-go, or the reverse | Allowed | Allowed | **Blocked**: the console reports that the instance image is a Marketplace image and conversion is not supported | **Blocked** while the licence link remains |
| Change bandwidth billing method | Allowed | Allowed | **Not blocked** | **Not blocked** |
| Change the public IP address | Allowed | Allowed | **Not blocked** (but see the mis-entry trap below) | **Not blocked** |
| Cross-account instance transfer | Allowed if the standard preconditions hold | Same | **Blocked**: refuse the self-service flow | Allowed, subject to the licence note below |
| Export an image to a local file | Not applicable to public images | **Blocked** for Windows Server system images | **Blocked**, including for a custom image built from it | **Blocked** |
| Unsubscribe / cancel an instance | Allowed self-service | Image licence has to be settled | **Conditional**: change to a free image first; a paid image fee itself is not refundable once associated with an instance | Same licence caveat applies |
| Cancel a renewal order that has not taken effect | Self-service | Needs the manual route | **Blocked** self-service: a cancellation specialist handles the instance order, then the image order follows automatically | Same |
| Change the operating system (system disk change) | Allowed when Stopped | Allowed when Stopped | **Conditional**: the instance must be Stopped, and the Marketplace order payment is completed after the change | Allowed when Stopped |
| Select the image as a RAM user scoped to a resource group | Allowed | Allowed | **Blocked** by the group-scope check: Marketplace images carry no resource group membership | Allowed once the custom image is moved into the authorized group |
| Boot on the purchased instance type | Allowed | Allowed | **Conditional**: some Marketplace products are limited to specific instance families; a mismatch can leave the instance stuck loading | Inherited from the source image |

## The mis-entry trap

The same Marketplace-image conversion message appears in two different console
entries. Establishing which one the customer was on is the first decision point, and
it changes the answer completely:

| Customer's actual goal | Entry they were on | Correct action |
|---|---|---|
| Convert the instance between subscription and pay-as-you-go | Instance billing-method conversion | Blocked by the image: change to an eligible public image first |
| Change the public IP address, or the bandwidth billing method | Instance billing-method conversion, by mistake | Leave the instance charge mode alone; convert only the bandwidth billing method |
| Temporarily raise the instance specification for a day or two | Instance billing-method conversion, because they think it is required | A temporary upgrade does not need a billing-method conversion at all |

## Choosing the intermediate image when conversion is the goal

The image that unblocks a conversion has to be a free public image. Red Hat
Enterprise Linux and SUSE Linux Enterprise Server are themselves licence-charging
images and do not serve as an intermediate step; an Alibaba Cloud public image is the
usual target. The change itself releases the old system disk, so the backup gate in
`console-guides.md` comes first.

## Two restrictions that survive the workaround

- **Licence follows the derived image.** A custom image built from a paid Marketplace
  image can keep generating the image fee, so the custom-image route is not a way to
  escape the charge, only a way to move the workload.
- **Export covers neither.** A custom image derived from a Marketplace image is
  outside the export scope, exactly like the Marketplace image it came from.

## What this matrix cannot settle on its own

Amounts, order counts, refund eligibility and refund arrival are order-side facts and
are not visible to any action in `ram-policies.md`. The matrix says whether the image
is the blocker; the billing console says what it costs. See `billing-rules.md` and the
handoff channels in `handoff.md`.
