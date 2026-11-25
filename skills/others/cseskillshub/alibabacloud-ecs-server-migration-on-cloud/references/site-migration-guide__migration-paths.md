# Migration paths, gates, and known pitfalls

Source of truth for the decision tree the `plan` subcommand encodes. Every step in this file is
executed by the customer in the console; this skill only plans, pre-checks, and verifies.

## Routing

```
What is the source?
|
+-- Alibaba Cloud ECS, reachable
|   +-- same account, same region      -> Path 1  image clone within one region
|   +-- same account, other region     -> Path 2  image plus region copy
|   +-- other account                  -> Path 3  transfer, or image plus share
|
+-- Alibaba Cloud ECS, expired or stopped -> Path 4  rescue window first
|
+-- Virtual host, other cloud, or IDC
    +-- file level, planned downtime   -> Path 5  package, transfer, deploy, reconfigure
    +-- agent based import             -> Path 6  import tool, then its limitations
```

Always finish in the same place for every path: the cutover checks in
[precheck-and-cutover-checklists.md](precheck-and-cutover-checklists.md), then the leftover-billing
review.

## Path 1 and 2: image clone (the main line)

1. Create a custom image from the source instance. The source keeps running and is not affected by
   this step: [create a custom image from an instance](https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance).
2. Cross region only: copy the image into the destination region:
   [copy an image](https://help.aliyun.com/zh/ecs/user-guide/copy-an-image).
3. Apply it:
   - no destination yet: buy the new instance from that image:
     [create an ECS instance by using a custom image](https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image);
   - destination already purchased: apply the image by replacing its operating system. The
     lightweight-server form of this operation is documented at
     [reset a simple application server](https://help.aliyun.com/zh/simple-application-server/user-guide/reset-a-simple-application-server);
     the equivalent ECS entry point still needs manual confirmation.
4. Data disks: confirm whether the image includes the data disks the site needs. A system-image-only
   move leaves the database and uploads behind; a data disk that must land on a smaller target disk
   fails the same way the system disk does.
5. After it boots: the content is identical, the addresses are not. Re-point every DNS record to the
   new public address, and expect the private address to change too.

### Compatibility gate (state it every time)

Compatibility between an image and a newer instance family cannot be predicted in advance. Some
newer instance types need an extra driver installed on the source before the image will boot there.
The safe sequence, taken from the reported cases:

1. create the image;
2. create one pay-as-you-go test instance of the target specification from that image;
3. boot it, log in, and start the services;
4. only then buy the production instance, or convert the validated pay-as-you-go instance to
   subscription.

If the test instance cannot boot, that is the moment to change the plan (redeploy the application
instead of cloning the disk), before any production server is touched.

## Path 3: cross account

Decide first what must survive, because the two options differ:

- Instance transfer (change of ownership): keeps the instance, its configuration and its billing.
  The entry point needs manual confirmation; eligibility and the conditions are decided by the
  account policy, so confirm with a human agent rather than assuming.
- Image route: create the image in the source account, share it with the destination account (entry
  point needs manual confirmation), then create the destination instance from the shared image.

What does not move across accounts, in both options:

- Account-bound promotions and discounted renewal prices stay with the purchasing account. A cheap
  yearly activity price does not follow the instance to another account.
- Network configuration objects of the access-control-list family, for example prefix lists and port
  range lists, cannot be migrated across accounts at all. Within one account they can be cloned
  across regions; across accounts they must be recreated by hand in the destination account.
- Security groups are per account and per region, so the rules have to be rebuilt in the destination
  account; only the instance listing tells you which group ids were bound.

## Path 4: expired or stopped instance

1. Distinguish the cause first. A subscription instance that reached its end date stops by policy;
   that is not the same as an overdue payment, and the fix differs. The billing type and status come
   from the `precheck` evidence.
2. Data is still on the disk while the instance is retained. Renew briefly, or ask a human agent
   whether a short extension can be applied: an extension is a manual decision and must never be
   promised. An instance left unrenewed past the retention window is released and its data cannot be
   recovered; read the exact deadline from the console or the expiry notice, not from any figure
   quoted in a support case.
3. Once reachable again: snapshot the system disk and each data disk, then use the image route or
   attach the disk to a new instance to copy the site out.
   [Create a snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot) and
   [snapshot billing](https://help.aliyun.com/document_detail/56159.html).
4. Never start a repair by re-initializing or replacing the system disk of the instance that still
   holds the only copy of the data.

## Path 5: virtual host, other cloud, IDC

The order that survives contact with reality:

1. Inventory what has to move: web files, database content, upload directory, certificates, cron or
   scheduled tasks, and any control-panel configuration.
2. Package on the source. On Windows, built-in compression can stall for hours on a deep tree with
   many small files; that is a throughput characteristic of the tool, not a permissions bug, and a
   reboot does not help. Archive per directory in batches, or use a faster archiver, and check the
   archive size before transferring.
3. Prepare the destination environment before the transfer window:
   [deploy an LNMP environment](https://help.aliyun.com/zh/ecs/user-guide/deploy-lnmp.md) and
   [build a website on ECS](https://help.aliyun.com/zh/ecs/user-guide/build-a-website.md).
4. Restore files and database, then update the application configuration so it points at the new
   database host, account, password, and name. Editing configuration inside the instance is a change
   the customer performs.
5. Re-point DNS last, after the site answers on the new server by address.

Pitfalls observed in this scenario:

- Changing DNS is not migrating. A domain that resolves to the new server serves nothing until the
  program and the data exist there.
- Two sites cannot be "merged" simply because both listen on port 80; name-based virtual hosts let
  several sites share one port on one server. The real cost is deploying and configuring the site.
- A partial file copy is the usual cause of a site that loads but shows a blank page or a missing
  theme: verify the theme or template directory and the upload directory specifically.
- A database connection error after the move means the configuration file still describes the old
  database, not that the database copy failed.

## Path 6: agent-based import from another cloud

When the import tool classifies the source as an unrecognised distribution, the resulting image type
is OthersLinux, and the console cannot reset the root password for that image type. Then:

- take a snapshot of the affected disk first
  ([create a snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot),
  [reference](https://help.aliyun.com/document_detail/25455.html));
- change the password from inside the instance over the console connection, or attach an SSH key
  pair: [instance logon credentials](https://help.aliyun.com/document_detail/2936588.html);
- check whether automatic snapshots created by the tool were attached to the system disk or only to a
  data disk before relying on them for anything.

To change the operating system of an imported instance while keeping the system-disk data, use the
operating-system migration route and read its pre-migration assessment first:
[migrate the operating system of an ECS instance](https://help.aliyun.com/zh/ecs/user-guide/migrate-the-operating-system-of-an-ecs-instance-1).
Replacing the system disk instead wipes that environment. A system-disk snapshot cannot be rolled
back onto a replaced or newly purchased system disk; its uses are to create a disk from the snapshot
and mount it to extract files, or to build a custom image from the snapshot and reset from that.

A new data disk that must receive the recovered files has to be partitioned, formatted, mounted, and
added to the mount table. That sequence is a change inside the instance and is performed by the
customer, snapshot first:
[initialise a Linux data disk up to 2 TiB](https://help.aliyun.com/zh/ecs/user-guide/initialize-a-data-disk-whose-size-does-not-exceed-2-tib-on-a-linux-instance).

## Capacity and layout gates

- The destination system disk must be at least as large as the source system disk. An activity or
  promotion instance with a 40 GiB or 80 GiB system disk cannot receive an image or snapshot built
  from a 100 GiB source; the move then needs either a larger disk class or an image plus an extra
  data disk. This is the single most common reason a plan that looked correct failed at the last
  step.
- The console listing is the authority for purchased disk size; the guest view of the same disk is a
  second, different fact. If the guest sees less than what was purchased, that is an expansion
  question, not a migration failure: see
  [handoff-boundaries.md](handoff-boundaries.md).
- After an image-based move of a Linux instance, check that the network interface did not keep a
  static private address copied from the source; a stale address on a new subnet breaks logins and
  looks like a security-group problem.

## Billing and commercial rules (state the rule, never the amount)

- Remaining subscription term and remaining subscription value cannot be moved to another instance or
  another region. A forced move caused by a region shutdown ends in an unsubscription for a partial
  refund, or in a compensation decision made by a human or the commercial owner. The skill states the
  rule and the entry points only.
  [Unsubscription rules](https://help.aliyun.com/zh/user-center/user-guide/unsubscription-rules),
  [refund rules](https://help.aliyun.com/document_detail/116043.html),
  [refund destinations](https://help.aliyun.com/zh/user-center/user-guide/refund-destinations),
  [self-service refund entry](https://usercenter2.aliyun.com/refund/refund).
- A downgrade refund is the difference between the new configuration price and the effective
  remaining price of the old configuration; where a discount was applied, the refundable amount can
  be zero. The amount shown on the page is authoritative. Instance resources cannot be split and
  part of them moved to a new instance.
- Unsubscription notes to repeat: back up first because data is cleared after a refund; the refund
  path and its working days are shown on the page; invoiced amount is reduced accordingly; gifted
  items can be voided; the figure on the refund page is the one to trust.
- Leftover billing after a move: post-paid data disks still attached to a stopped instance,
  unattached post-paid disks, outbound traffic, and side services such as file storage in regions
  that are no longer used. Bill item detail:
  [expense detail by instance](https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance),
  file storage pricing: [NAS pricing](https://www.aliyun.com/price/product#/nas/detail/nas_bag).
  Releasing or deleting anything is a customer action in the console.

## Documentation entry points still pending

These topics have no confirmed link in this build, so the reports and answers must say "needs manual
confirmation" instead of inventing a URL: instance transfer between accounts, sharing a custom image
with another account, replacing the operating system of an ECS instance, the agent-based server
migration centre procedure, editing a DNS record, adding an inbound security-group rule, prefix lists
and port range lists, and the driver referenced for newer instance families.
