# Constraints, error wording, and how confident each statement is

Every statement here is tagged. Read the tag before repeating the statement to a
customer.

| Tag | Meaning | How to present it |
| --- | --- | --- |
| `official` | Quoted from the official Alibaba Cloud help page named in the same row | State it as a fact, with the page |
| `dialogue` | Confirmed in a first-hand support conversation of a past case | State it as a fact |
| `summary` | Reaches us only through the closing summary of a past case | State it as "usually" and ask for console confirmation |
| `design` | This skill's own routing logic, not a quoted product rule | State it as the check being performed |

## Hard constraints

| Id | Constraint | Applies to | Tag |
| --- | --- | --- | --- |
| `pick-the-route-first` | Another account splits into three routes: ownership transfer (same region and zone), image/snapshot or SMC rebuild (different region, zone or spec), rebuild only (preemptible) | cross-account | `design` |
| `ownership-transfer` | Official ECS ownership transfer changes only the owner of one instance: region, zone, instance type, cloud disks and the fixed public IP configuration stay as they were; it supports subscription and pay-as-you-go and does NOT support preemptible instances; snapshots and custom images are NOT transferred; about half an hour, free of charge, target account pays afterwards | cross-account | `official` |
| `ownership-transfer-prerequisites` | The running instance must be stopped first; the target account needs a VPC, vSwitch and security group in the same region and zone; the transfer switches the instance into the target VPC, so network position and reachability change and the private IP may change; an EIP is not carried over | cross-account | `official` |
| `region-immutable` | The region of an instance cannot be changed after it exists; a "move" is always a rebuild elsewhere | cross-region | `dialogue` |
| `custom-image-system-disk-only` | A custom image taken from an instance covers the system disk by default; data disks need their own snapshots | cross-region, cross-account | `dialogue` |
| `target-disk-not-smaller` | The target system disk must be at least as large as the source image size | cross-account | `dialogue` |
| `same-zone-attach-limit` | A data disk can only be attached inside the zone that holds it | cross-zone | `dialogue` |
| `private-ip-changes` | A zone change always replaces the private address; the fixed public address is kept where allocation permits, otherwise a new one is issued | cross-zone | `dialogue` |
| `source-untouched` | Image and snapshot work does not disturb the running source instance | cross-region, cross-account | `dialogue` |
| `smc-vs-image` | A host-migration service produces a new instance, so it belongs to the rebuild route; loading data into an instance that already exists is better served by the image and snapshot chain, and keeping the same instance is served by the ownership transfer | cross-account | `dialogue` |
| `windows-major-upgrade` | Windows Server cannot be upgraded across more than one major version in place | os-change | `dialogue` |
| `no-automatic-move` | The platform does not relocate an instance for you after a retirement notice | platform-retirement | `dialogue` |
| `retained-window-not-guaranteed` | Inside a retirement window a kept instance loses its service-level guarantee and can be released at any time | platform-retirement | `dialogue` |
| `entitlement-is-manual` | Remaining subscription time cannot be transferred between regions or instances; refunds and compensation are manual commercial decisions | platform-retirement | `dialogue` |
| `order-must-be-paid` | A zone change executes only after its order is paid | cross-zone | `summary` |
| `dependent-private-resources` | Private-address references block a zone change even while the instance is stopped | cross-zone | `summary` |
| `eip-rebind` | An elastic address must be unbound and re-bound by hand | cross-zone | `summary` |
| `overseas-os-family-swap` | Some overseas regions are reported to reject a Windows-to-Linux swap; no official rule page is cited in this package | os-change | `summary` |
| `physical-address-manual` | The machine room address of a host is resolved by support staff; no public read query exists | platform-retirement | `dialogue` |

`design`: whether a scenario applies is derived from the flags plus the queried
region and zone values, never from the wording of the question alone.

## Customer-visible error wording

These are the wordings customers report. Each maps to a handling list. All four
are `summary` level: the wording is a paraphrase of what was seen, not a
verbatim machine code, because no error code was supplied for this tier.

### "instance type in the destination zone is out of stock"

The destination zone has no capacity for that instance type at that moment.

1. Re-check with the read-only capacity query against every candidate zone in the
   region.
2. Try another zone, or another type in the same family.
3. If this happens during a purchase, cancel the order and re-order in a zone that
   reports capacity. Capacity is not reserved by a failed order.

### "reverse dependencies or route dependencies on the private IP"

Something still references the private address of the instance, so the zone change
is refused. Shutting the instance down does not remove those references.

1. Look at custom route entries in the VPC route tables of that vSwitch.
2. Look at remote-session records and data-sync tasks that stored this address.
3. Remove or re-point each reference, then start the change again.

### "no visible progress after starting the zone change"

The relocation order exists and is unpaid, so nothing runs.

1. Open the order list and pay or cancel the pending relocation order.
2. Confirm the instance state afterwards with the read-only status query.

### "operating system type replacement is not supported"

The region or image combination rejects a cross-family replacement.

1. Confirm the target image family for this region in the console.
2. If it is genuinely unsupported, plan a rebuild plus a data restore instead of a
   replacement.

## Cost facts stated with each path

| Fact | Tag |
| --- | --- |
| A custom image costs nothing to build, but the snapshot it creates is billed | `dialogue` |
| The ownership transfer of an instance costs nothing and takes about half an hour; the target account pays the running cost from then on | `official` |
| Copying a snapshot is billed separately from the snapshot itself | `dialogue` |
| Cross-region replication keeps a second copy, so it carries its own storage charge | `summary` |
| Refunds, vouchers and residual-value decisions are never quoted by this skill | `dialogue` |

Pricing reference: [snapshot billing](https://help.aliyun.com/document_detail/56159.html).

## Statements this skill must never make

- A specific machine room address, or which zone is physically in which city.
- A retirement date, an extension, a refund amount, or a voucher amount.
- That a zone change is guaranteed to keep the public address.
- That the overseas operating-system-family rule is official: it is `summary`
  level here and must be confirmed in the console.
- Any figure about disk size, image size or capacity that was not returned by a
  query in this run.
