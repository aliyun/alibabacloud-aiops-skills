# ECS Knowledge FAQ — Curated Quick Answers

A curated knowledge snapshot distilled from Alibaba Cloud ECS official documentation, meant to give quick, high-confidence answers to frequently asked ECS questions (instance families, billing, snapshots, disk resizing, security groups). Content may become stale — always verify with a live search using `scripts/aliyun_help.py` and cite the live URLs returned by that search rather than relying solely on the entries below.

## How are ECS instance specification families classified and named?

Alibaba Cloud groups instances into specification-family clusters by CPU architecture and workload type: x86 and ARM compute families, elastic bare metal servers, high-performance computing servers, supercomputing clusters, and GPU-based heterogeneous compute. Within each cluster, one-letter series encode the positioning — g for general purpose (vCPU:memory = 1:4), c for compute optimized (1:2), r for memory optimized (1:8), and ic for dense compute (1:1) — while trailing letters and numbers mark processor vendor and generation. Mastering this naming scheme lets you infer a family's balance of compute, memory, and network capability directly from its name.

Source: https://help.aliyun.com/document_detail/2849443.html

## What is the difference between general purpose and compute optimized families?

General purpose families (g series) keep a 1:4 vCPU-to-memory ratio and suit balanced workloads such as enterprise applications, mid-size databases, caches, and data processing. Compute optimized families (c series) use a 1:2 ratio and stronger sustained CPU performance for compute-bound workloads like batch processing, high-performance web servers, and scientific computation. Choosing between them is mainly a question of whether the workload is memory-balanced or CPU-bound.

Source: https://help.aliyun.com/document_detail/25378.html

## What are the specializations of memory-intensive and dense-compute families?

Memory-enhanced families such as re4 target high-performance and in-memory databases (for example SAP HANA, which certain sizes are certified for), memory-intensive applications, and big-data engines like Apache Spark or Presto, offering ratios up to 1:12 and very large memory ceilings. Dense compute families such as ic5 use a 1:1 ratio for workloads that need strong CPU with little memory: web front ends, batch processing, video encoding, and MMO game servers.

Source: https://help.aliyun.com/document_detail/25378.html

## How should I select the right instance specification?

Selection should combine performance requirements, price, and workload characteristics: first understand the family classification and naming rules, then match the workload's CPU, memory, network, and storage profile to a candidate family, and finally validate with real-world testing before committing. The official selection guide walks through this decision process step by step and is the recommended starting point for capacity planning.

Source: https://help.aliyun.com/document_detail/58291.html

## How do subscription, pay-as-you-go, and preemptible instances differ?

Subscription is a prepaid model best for steady 7x24 services such as persistent web servers: you pay upfront for a fixed term at a lower effective price. Pay-as-you-go bills by the second/hour with no commitment, ideal for elastic, bursty, or short-lived workloads. Preemptible instances offer steep discounts over pay-as-you-go but can be reclaimed automatically when market price exceeds your cap or supply runs short, so they only fit interruption-tolerant jobs such as batch computation, CI, and stateless scaling.

Source: https://help.aliyun.com/document_detail/25370.html

## What are savings plans and how do they reduce cost?

A savings plan is a discount benefit that offsets pay-as-you-go ECS/ECI instance bills (preemptible instances excluded) in exchange for an hourly spend commitment over a one-, three-, or five-year term. Unlike reserved instance coupons, it allows flexible changes across instance types, families, regions, and operating systems. It is purely a billing discount and does not provision resources, so it must be paired with actual pay-as-you-go instances; converting a subscription fleet to pay-as-you-go plus a savings plan can lower cost while improving flexibility.

Source: https://help.aliyun.com/document_detail/184083.html

## How can I control pay-as-you-go costs on idle instances?

A pay-as-you-go instance in a normal stop still accrues charges unless the economical (savings) stop mode is enabled, which suspends billing for compute resources while stopped. Release instances you no longer need — billing stops immediately, but remember that released data is permanently deleted, so create snapshots first. You can also switch billing methods when the business pattern changes.

Source: https://help.aliyun.com/document_detail/40653.html

## What are the key points when resizing a cloud disk?

Disk resizing is a two-step process: first extend the disk capacity in the console (buying more space), then extend the partition and file system inside the OS — payment alone does not make the new capacity usable. Disks can never be shrunk, so evaluate capacity needs carefully beforehand and take a snapshot before operating. Extended capacity is billed at the disk's existing billing method; note that a disk cannot be resized while a snapshot is being created.

Source: https://help.aliyun.com/document_detail/2949817.html

## How should I configure snapshot retention policies?

Snapshot storage is billed by capacity and duration, so keep only a reasonable number of snapshots and tune creation frequency and retention to the business need. Automatic snapshot policies create snapshots on a schedule with a defined retention period for routine protection against accidental deletion or corruption, and can replicate snapshots across regions for disaster recovery; retention of expiring snapshots can be extended before expiry, while permanently retained snapshots cannot be changed. Deleted snapshots are unrecoverable, so verify business and compliance impact before removal.

Source: https://help.aliyun.com/document_detail/25458.html

## Why can I not ping my ECS instance, and how do security groups factor in?

The security group must contain a rule allowing ICMP (ping) inbound; if that rule was removed, ping fails and you should restore it in the ECS console. Also check the VPC network ACL bound to the instance's vSwitch, because ACL rules restrict both inbound and outbound traffic and can override security-group allowances. Ping failures should be diagnosed layer by layer: security group rules, network ACLs, then OS-level firewall settings.

Source: https://help.aliyun.com/document_detail/40572.html

---

Curated date: 2026-08-18
