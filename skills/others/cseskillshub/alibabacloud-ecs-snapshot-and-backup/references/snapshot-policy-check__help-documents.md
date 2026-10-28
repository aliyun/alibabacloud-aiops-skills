# Help documents used by this skill

Two provenance classes, kept apart deliberately:

- **Retrieved**: hit by the documentation search run while building this skill.
- **Quoted in tickets**: a link an agent pasted into a ticket thread. These are
  reproduced as seen; verify each one still resolves before sending it to a customer,
  because document slugs do move.

Do not invent a URL. If a question has no entry here, say the documentation is not
confirmed and describe the console path instead.

## Retrieved

| Topic | Document |
|---|---|
| snapshot overview: full and incremental, standard and archived | `https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview.md` |
| how snapshots work, and why a snapshot is not its disk's size | `https://help.aliyun.com/zh/ecs/user-guide/how-do-snapshots-work.md` |
| copy a snapshot cross-region | `https://help.aliyun.com/zh/ecs/user-guide/copy-a-snapshot.md` |
| replication time control for asynchronous disk replication (not snapshot copy) | `https://help.aliyun.com/zh/ecs/user-guide/replication-time-control-of-ebs-asynchronously-replication.md` |
| custom image from a snapshot | `https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-a-snapshot-1.md` |
| copy a custom image | `https://help.aliyun.com/zh/ecs/user-guide/copy-an-image.md` |
| custom image overview, snapshot versus image boundary | `https://help.aliyun.com/zh/ecs/user-guide/overview-36.md` |
| create a custom image with OOS | `https://help.aliyun.com/zh/ecs/user-guide/use-oos-to-create-a-custom-image.md` |
| create a disk from a snapshot (temp disk to read files) | `https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot.md` |
| re-initialize a data disk (restore-shaped requests, a different axis) | `https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-data-disk.md` |

There was **no** documentation hit for troubleshooting a policy that produces nothing.
That gap is covered by `references/policy-effectiveness.md`, which is built from
ticket dialogues rather than from product docs, and it is the reason that file cites
tickets on every claim.

## Quoted in ticket dialogues

| Topic | Document | Seen in |
|---|---|---|
| create a snapshot | `https://help.aliyun.com/document_detail/25455.html` | 0001ZS6NA6, 0008MRX2NY |
| snapshot billing | `https://help.aliyun.com/document_detail/56159.html`, `https://help.aliyun.com/zh/ecs/snapshots-1` | 0001ZS6NA6, 000ACRF8K2, 00069RU80Y |
| create an automatic snapshot policy | `https://help.aliyun.com/document_detail/127767.html`, `https://help.aliyun.com/zh/ecs/user-guide/automatic-snapshot-policy` | 0001FRZPLN, 00021RX22D |
| apply or unapply a policy (the binding step) | `https://help.aliyun.com/zh/ecs/user-guide/enable-or-disable-an-automatic-snapshot-policy` | 00021RX22D, 000F4RNG48 |
| delete an automatic snapshot policy | `https://help.aliyun.com/zh/ecs/user-guide/delete-an-automatic-snapshot-policy` | 000GJRTG60 |
| roll a disk back with a snapshot | `https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot-1`, `https://help.aliyun.com/document_detail/32317.html` | 000GJRTG60 |
| extend the retention of a snapshot | `https://help.aliyun.com/zh/ecs/user-guide/extend-the-snapshot-retention-period` | 00094RC1SX |
| view snapshot capacity and chains | `https://help.aliyun.com/document_detail/54789.html`, `https://help.aliyun.com/document_detail/25392.html` | 00094RC1SX |
| SQL Server application-consistent snapshots on Windows | `https://help.aliyun.com/document_detail/294429.html`, `https://help.aliyun.com/zh/ecs/user-guide/best-practice-for-creating-application-consistent-snapshots-for-a-windows-instance-on-which-sql-server-is-deployed` | 000BSRFJZW |
| export a custom image | `https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image` | 0005PR939W, 000CARSFMA |
| stop Cloud Backup billing, whole-instance backup comparison | `https://help.aliyun.com/zh/cloud-backup/product-overview/how-do-i-stop-being-billed-for-cloud-backup`, `https://help.aliyun.com/document_detail/89062.html` | 0008MRPHYY, 000GJRTG60 |

## Console entry points

These are safer than deep links because they are constructed from the region id and
are the pages agents actually sent:

```
https://ecs.console.aliyun.com/snapshot/region/<regionId>
https://ecs.console.aliyun.com/autoSnapshotPolicy/region/<regionId>
https://ecs.console.aliyun.com/disk/region/<regionId>
```

The block storage page is the one used to see, per region, which disks carry a policy
and to export that list for an audit (evidence: ticket 000ACRK142).
