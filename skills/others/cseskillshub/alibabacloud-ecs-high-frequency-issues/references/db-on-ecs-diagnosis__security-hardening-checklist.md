# Database exposure hardening checklist

The standard set support engineers handed out on this tier's tickets after an
intrusion or an exposed-port finding. It is guidance: every step is performed
by the customer in their own console or inside their instance. This skill
reports which items already hold, from collected evidence, and never applies
any of them.

| # | Item | Where the customer does it | Notes |
| --- | --- | --- | --- |
| 1 | Restrict management ports (SSH 22, RDP 3389) to specific source IPs | ECS console - security group ingress | Never leave 22/3389 open to `0.0.0.0/0` on an internet-facing instance |
| 2 | Do not publish database ports (1433, 3306, 6379, 5432, 27017) to the whole internet | ECS console - security group ingress | Allow only the application/office egress IPs; if the app runs on the same instance, bind the database to loopback instead |
| 3 | Strong unique passwords for every database account; disable unused accounts (including `sa` if unused) | Inside the database | Weak-password guessing is the entry route on every ransom ticket in this set |
| 4 | Change default ports where the client can follow, or keep them and tighten item 2 | Database config | A port move alone is not security; pair it with source restriction |
| 5 | Rotate credentials after any successful attack or leaked connection string | Database + application config | Old strings inside published apps keep reconnecting as "ghost" clients |
| 6 | Regular disk snapshots, plus an automatic snapshot policy for the data disks | ECS console - snapshots | Paid feature billed by stored capacity and retention (see https://help.aliyun.com/document_detail/56159.html); verify old snapshot cleanup so bills do not creep (delete guide https://help.aliyun.com/document_detail/128131.html) |
| 7 | OS and database security patches; remove panels, web services and middleware that the workload does not actually run | Inside the instance | Each unnecessary listener is another exposed port; third-party panels bring their own attack surface |
| 8 | Cloud Security Center agent (the free tier at minimum) for login and anomaly alerts | https://yundun.console.aliyun.com/ | Alerting, not prevention; keeps evidence warm for the forensics tier |

## After a suspected intrusion (ransom pattern)

The fixed action order, identical to the ticket practice:

1. **Preserve the scene before touching anything.** Take a disk snapshot now
   (this skill offers the gated write for exactly this). Do not delete,
   clean, reboot or reinstall before the snapshot exists - that destroys the
   only recovery and forensic baseline.
2. **Do not pay the ransom note**; there is no platform-side guarantee of
   decryption.
3. **Recovery path**: if no pre-existing snapshot exists, cloud-side data
   recovery is not possible; the practical route is a third-party data
   recovery specialist from the cloud marketplace
   (https://market.aliyun.com/products/?keywords=%E5%8B%92%E7%B4%A2%E7%97%85%E6%AF%92)
   or a rebuild via re-initialize system disk (a destructive manual step the
   skill documents but never performs).
4. **Then the checklist above, all of it**, before the workload goes back
   online - every reinfection on this tier came from re-exposing the same
   open port.

## Snapshot cost statement (use this wording, then point to the official page)

"Snapshots are billed by stored capacity and retention time. The ticket-side
reference caliber for standard snapshots was about 0.016 yuan for 100 GB held
for one hour (about 0.4 yuan for one day); the official snapshot pricing page
https://help.aliyun.com/document_detail/56159.html is the authoritative
source. The snapshot lives in cloud storage, consumes no space on the disk
being diagnosed, and does not need the instance stopped."
