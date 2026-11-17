# Relocation paths

Every path below is manual work performed by the customer in the console. This
skill only establishes feasibility, prints the path, and names the resources
that will break. Nothing here is executed by the skill.

## Prefix that applies to all paths

**Snapshot first.** Before an operating-system replacement, a cross-zone change,
or any image and snapshot clean-up, take a manual snapshot of each affected disk
and wait until it is usable. A system disk that was wiped without a snapshot is
not recoverable. Custom images are free to build, but the snapshot they create is
billed, and copying a snapshot is billed on its own.

- Snapshot guide: [create a snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot)
- Backup guidance: [create a snapshot backup](https://help.aliyun.com/document_detail/25455.html)
- Pricing: [snapshot billing](https://help.aliyun.com/document_detail/56159.html)

## Path 1 - another region, same account

The region of an instance is fixed for its lifetime. There is no move button and
no move API; the destination is built from an image, and the old instance stays
where it is until you decide otherwise.

1. Snapshot the system disk and every data disk of the source instance.
2. Build a custom image from the system-disk snapshot:
   [create a custom image from an instance](https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance),
   or from a snapshot:
   [create a custom image from a snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-a-snapshot-1).
3. Copy the image to the destination region:
   [copy an image](https://help.aliyun.com/zh/ecs/user-guide/copy-an-image). Copy
   the data-disk snapshots too, because replication is per object and each copy
   is billed.
4. Build the destination: either a new instance from the copied image
   ([create an instance from a custom image](https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image))
   or a rebuild of an instance you already own there. Purchase options:
   [how to buy ECS](https://help.aliyun.com/zh/ecs/user-guide/a-picture-is-to-teach-you-how-to-buy-cloud-server-ecs.md).
5. Rebuild the data disks from their snapshots:
   [create a disk from a snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot).
6. Cut over: the public address changes, so update DNS, allowlists and any
   licence bound to the old address. Keep the source running until your own
   business checks pass.

If the customer objects that the chain is too long, say so plainly and offer the
alternative that historical cases accepted: back the data up, buy a fresh
instance in the destination region, restore, then unsubscribe from the old one.

## Path 2 - another account: resource ownership transfer first, rebuild second

Put the destination question first. Three routes exist and only one of them
keeps this exact instance.

### Path 2A - official ownership transfer, when the region, zone and specification stay

Official page: [ECS instance ownership transfer](https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance).

The operation changes which account owns one instance. Official facts:

- It supports subscription (pre-paid) and pay-as-you-go instances; it does
  **not** support preemptible (spot) instances.
- Only the owning account changes: region, zone,
  instance type, cloud disks (system disk plus data disks) and the fixed public
  IP configuration stay as they were.
- Snapshots and custom images are not
  carried over. Share them separately if the target account needs them.
- Stop the running instance before the operation; it takes about half an hour and Alibaba Cloud charges nothing
  for it. The target account pays the running cost afterwards.
- The instance joins
  the target account's VPC, so its network position and reachability change,
  and the private IP may change. Security group rules
  come from the target account; an elastic IP is not carried over, so unbind it
  first.

1. Prepare in the target account: a VPC, a vSwitch and a security group in the
   same region and zone as the instance.
2. Stop the instance, unbind the elastic IP, then submit the transfer from the
   console entry on the page above.
3. After it completes, re-create the deleted dependencies: DNS records,
   allowlists, security-group rules, monitoring and any alarm contacts.
4. Accept the trade: no reinstall, no data copy, same disks and same fixed
   public address - but a new VPC position, a possibly new private address and
   no snapshots or images travelling with the instance.

### Path 2B - another region, another zone or another specification: build it

Same chain as Path 1 plus a sharing hop, and two checks that are usually missed.
The transfer above cannot change region, zone or specification, so this is the
route for those destinations.

1. Share the custom image with the destination account:
   [share a custom image](https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image).
2. Share the data-disk snapshots as well:
   [share a snapshot](https://help.aliyun.com/zh/ecs/user-guide/share-a-snapshot).
3. In the destination account, apply the image through the operating-system
   replacement flow:
   [replace the operating system](https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance).
   **That clears the system disk of the target instance**, so snapshot the target
   too, not only the source.
4. Check the size floor before starting: the target system disk must be at least
   as large as the source image. An 80 GiB image cannot land on a 40 GiB disk;
   the disk has to be enlarged first.
5. Disk sizes and image size are not part of the read-only query this skill can
   run; read both in the console before quoting feasibility.
6. Server Migration Service is the alternative that produces a new instance
   directly; it is billed and still yields a new id and a new address.

### Path 2C - a preemptible instance: rebuild only

A preemptible (spot) instance cannot be transferred at all. Rebuild it in the
destination account from an image or from the deployment automation, and state
that the destination instance stays preemptible.

Cross-account trust, remote-session setup and application compatibility remain
human conversations. This skill does not model the other account.

## Path 3 - another zone in the same region

The route is a change of instance type across zones:
[change instance types across zones](https://help.aliyun.com/zh/ecs/user-guide/change-instance-types-across-zones.md).
Four things stop it, and each has its own check.

1. **Capacity.** The destination zone must have stock for the instance type at
   that minute. Use the read-only stock pre-flight for every candidate zone
   instead of trying zones one by one in the console.
2. **Payment.** The change executes only after its order is paid. "I started it
   and nothing happens" is normally an unpaid order sitting in the order list.
   Order state is not available to this skill; the customer checks the console.
3. **Private-address dependencies.** Custom route entries, remote-session
   records and data-sync tasks that still point at the private address block the
   change, and stopping the instance does not clear them. Each reference is
   removed in its own console.
4. **Resources bound to the zone.**
   - A data disk lives in one zone and cannot be attached in another. Rebuild it
     from a snapshot in the destination zone
     ([create a disk from a snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot)),
     consider a zone-redundant disk
     ([regional ESSD](https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md)),
     or fall back to transferring the files over the network.
   - An elastic network interface created by a managed cluster is owned by that
     cluster and cannot be deleted by hand; when its vSwitch is being retired,
     change the vSwitch of the interface instead
     ([elastic network interface overview](https://help.aliyun.com/zh/ecs/user-guide/eni-overview.md)).
   - An elastic address is unbound and re-bound in the console.

Address outcome, stated the same way every time: the **private address always
changes** (it can be edited afterwards), and the **fixed public address is kept
where allocation permits**, otherwise a new one is issued.

## Path 4 - a zone or region is being retired

The notice obliges the customer to move; the platform does not relocate the
instance. Guidance:
[instance migration due to upgrades at the underlying layer](https://help.aliyun.com/zh/ecs/user-guide/instance-migration-due-to-upgrades-at-the-underlying-layer.md).

1. Record the cut-over date from the notice the customer received. This skill
   keeps no retirement calendar and must not quote one from memory.
2. Run Path 1 or Path 3, whichever the target is.
3. Explain the retained window honestly: residual value may be refunded
   automatically while the instance is kept, but service levels no longer apply
   and release can happen at any moment. Urgency, not extra time.
4. Physical machine room address is a manual support lookup; there is no
   read-only query for it.

Commercial requests that come with a retirement - transferring remaining
subscription time, compensation, extensions - are outside this skill. Remaining
time cannot be moved between regions; unsubscription rules are reference only:
[refund rules](https://help.aliyun.com/document_detail/116043.html),
[fund destinations](https://help.aliyun.com/zh/user-center/user-guide/refund-destinations),
[self-service refund entry](https://usercenter2.aliyun.com/refund/refund). No
amount, voucher or extension is ever promised here.

## Path 5 - the target environment also needs an operating-system change

Only the constraint side is handled here; the replacement itself belongs to
another capability.

- Windows Server cannot move across more than one major version in place. Either
  step through the migration feature
  ([migrate the operating system](https://help.aliyun.com/zh/ecs/user-guide/migrate-the-operating-system-of-an-ecs-instance))
  or back up, replace the operating system
  ([replace the operating system](https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance)),
  and redeploy the software.
- Replacing the operating system clears the system disk. Snapshot first.
- Some historical cases report that Windows and Linux families cannot be swapped
  in certain overseas regions. No official rule page backs that statement in this
  package, so present it as "confirm in the console", never as a rule.

## What is not a relocation

- Changing the instance type inside the same zone is a specification change.
- Changing which deployment set an instance belongs to is placement, not
  relocation. It is configured on the instance page in the console and follows
  deployment-set rules, not relocation rules.
- Zone-redundant disks and asynchronous replication are disaster recovery, not
  relocation: [disk disaster recovery overview](https://help.aliyun.com/zh/ecs/user-guide/overview-8.md).
- Moving a whole website or an application stack from another cloud is a site
  migration, handled elsewhere.
