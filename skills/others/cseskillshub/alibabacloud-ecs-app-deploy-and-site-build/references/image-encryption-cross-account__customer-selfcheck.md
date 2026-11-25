# What only the customer can confirm

This skill reads one account and one region per run, using the identity behind
the default credential chain. Everything below is therefore **outside** its
evidence and must be requested from the customer as text or a screenshot. Ask for
one item at a time, quote the answer back in the report, and label it
`customer-reported, not verified by this skill`.

## A. Peer-account items (always unreachable from here)

| Ask the customer for | Why the skill cannot get it | What it settles |
| --- | --- | --- |
| Screenshot of the **Shared Images** tab, with the region selector visible, in the recipient account | The queries only return resources the calling account can see | Whether the share landed at all, and whether the recipient is looking in the right region |
| The recipient account's **main account ID**, read from the avatar menu | An account ID typed wrong is the single most common cause of an invisible share | Whether the owner shared to the ID the recipient actually owns |
| Recipient's own `DescribeImages` output or the image row for the shared ID | Cross-account reads need the recipient's credentials | Whether the recipient sees the image as `Available` |
| Screenshot of the disk encryption option on the purchase page | Launch-time parameters are not stored on the image | Whether the failure was the missing encryption flag rather than permissions |
| Whether the recipient account has account-level default encryption configured with a key | It is an account setting outside ECS image reads | Which key the launched disks actually use |

## B. Owner-account items the API does not return here

The queried actions give the encryption flag per snapshot mapping, but not the
key or the recipient list. Ask for:

1. The **KMS key id and its region** shown next to each snapshot of the image in
   the console - needed to check the trust policy of
   `AliyunECSShareEncryptImageDefaultRole` and to confirm the key exists in the
   destination region before a copy.
2. The **share target list and share time**, from hovering the share icon on the
   image row in the Custom Images tab.
3. The **trust policy JSON** of `AliyunECSShareEncryptImageDefaultRole` in the
   owner account, if a share was accepted but the recipient still cannot use it:
   a missing `<recipient-account-id>@ecs.aliyuncs.com` principal, or a
   role created in the wrong account, is the usual cause.
4. Which policy is attached to that role: `AliyunKMSFullAccess` for the service
   key, or the custom `kms:` policy for a customer master key. A mismatch here
   produces a recipient-side failure that looks like "image not found".

## C. In-guest items (this skill never enters an instance)

If the symptom is about the operating system inside the instance, ask the
customer to run a **read-only** command themselves and paste the output, or hand
the case to the Cloud Assistant / remote-connection skill. This skill never runs
anything inside an instance and never claims to.

Typical read-only requests in this symptom axis, phrased as "please run and paste
back":

* the disk layout and mount points, to see whether a launched instance actually
  got the expected data disks;
* the OS edition, to confirm a Windows image (which is also the export
  exclusion in `image-encryption-basis.md` section I).

## D. How to phrase the hand-back

Ask in a way that produces evidence, not narrative:

> "Please open the Images page in the receiving account, switch the region
> selector to `<region>`, open the **Shared Images** tab, and send a screenshot
> that includes the region selector and the account ID in the top-right corner.
> I will compare it against the owner-side evidence I already collected."

Then in the report, keep the two sides separate: `verified by read-only query`
versus `customer-reported`. Never merge them into one conclusion, and never let a
customer-reported item upgrade the report status above what the queries support.
