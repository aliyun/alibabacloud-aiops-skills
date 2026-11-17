# Module M1 — Cloud disk performance formulas & ceilings

Knowledge module for `scripts/areas/disk_pl_change_guide/disk_pl_advisor.py` (assess / bottleneck /
faq modes). The script embeds the same numbers as constants; this file is
the human-readable source with provenance.

**Provenance discipline.** Values tagged **[ticket]** appear verbatim in a
real support-ticket reply (or a customer calculation confirmed there) for
this tier. Values tagged **[official]** come from the published block
storage specification pages cited below. Values tagged **[derived]** follow
the published pattern but were not seen verbatim — confirm them on the
official page before quoting. The live console display and the official
page are always the final authority: when the console shows a different
number, trust the console and cite the page, never argue.

## 1. The core misunderstanding this tier exists for

The big numbers in spec tables are **per-level ceilings reached only at
large capacity**. Per-disk IOPS and throughput grow **linearly with the
disk size** and then stop at the level cap. Customers reading "PL0 max
10,000 IOPS" expect 10,000 on a 100 GiB disk and "see 3,000 in the
console" — which is exactly right (ticket T-B525FD49), and ESSD Entry
100 GiB = 2,600 IOPS = `1800 + 8 × 100` (ticket T-DA6C3114).

## 2. IOPS ceilings, capacity c in GiB

| Disk level | IOPS formula | Cap | Provenance |
|---|---|---|---|
| Ultra disk (efficient cloud disk, `cloud_efficiency`) | `1800 + 8 × c` | 5,000 | cap **[ticket]** (800 GiB → 5000, T-DA6C3114); coefficient **[derived]** |
| SSD disk (`cloud_ssd`) | fixed maximum | 25,000 | **[official]** |
| ESSD Entry (`cloud_essd_entry`) | `1800 + 8 × c` | per Entry tier cap | **[ticket]**: 100 → 2600 (T-DA6C3114), 40 → 2120 (T-EE75C111) |
| ESSD PL0 (`cloud_essd` PL0) | `min(1800 + 12 × c, 10000)` | 10,000 | **[ticket]** T-B525FD49 (100 GiB → 3000; reaching 10,000 needs ≈ 684 GiB) |
| ESSD PL1 | `min(1800 + 50 × c, 50000)` | 50,000 | **[official]** |
| ESSD PL2 | `min(1800 + 50 × c, 100000)` | 100,000 | **[official]** |
| ESSD PL3 | `min(1800 + 50 × c, 1000000)` | 1,000,000 | **[official]** |
| ESSD AutoPL (`cloud_auto`) | baseline + purchased pre-provisioned IOPS; burst is an independent ceiling | read from the disk's console row | caliber rule **[ticket]** T-851CC73C |

AutoPL caliber (verbatim rule from ticket T-851CC73C): *if performance
burst is not enabled, the baseline ceiling counts; if burst is enabled,
the burst ceiling counts for short peaks.* Fixed-PL ESSD fits steady
workloads; AutoPL fits volatile ones. AutoPL billing behavior (burst is
on by default and can generate post-paid charges) belongs to the billing
area — see [handoff-boundaries.md](disk-pl-change-guide__handoff-boundaries.md).

## 3. Throughput ceilings (MB/s)

| Disk level | Throughput formula | Cap | Provenance |
|---|---|---|---|
| Ultra disk | `min(100 + 0.15 × c, 140)` | 140 | **[official]** |
| SSD disk | fixed maximum | 300 | **[official]** |
| ESSD Entry | `min(100 + 0.25 × c, 150)` | 150 | **[derived]** (PL0 curve shape applied to Entry) |
| ESSD PL0 | `min(100 + 0.25 × c, 180)` | 180 | **[ticket]** T-CC0FA37F (100 GiB → 125, 200 GiB → 150; measured 132.86 / 159.42 matched) |
| ESSD PL1 | `min(120 + 0.5 × c, 350)` | 350 | **[official]** |
| ESSD PL2 | `min(120 + 0.5 × c, 750)` | 750 | cap **[ticket]** (T-39B4EB79 discusses the 750 PL2 figure) |
| ESSD PL3 | `min(120 + 0.5 × c, 4000)` | 4,000 | **[official]** |
| ESSD AutoPL | baseline follows the PL1-shaped curve; burst ceiling above it | read from console | **[derived]** |

## 4. The smaller-of rule (instance side)

Usable bandwidth = **min(instance-type storage ceiling, disk ceiling)**.
Raising the disk level only helps while the disk is the smaller side.

Worked example (ticket T-39B4EB79): ESSD PL2 disk (750 MB/s) attached to
`ecs.u1-c1m2.4xlarge`, whose storage bandwidth baseline is 3 Gbit/s →
`3000 / 8 = 375 MB/s`. Every `EcsBaseBPS` alert came from the **instance**
side; the correct fix was changing the instance type, not a higher PL.

The per-instance-type storage ceiling lives in the official instance
family table (the queried APIs do not expose it — never guess it):
<https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families#u1>

## 5. Reading IO pressure (pasted iostat / monitoring)

- **High `%util` (97–99%) with LOW `await` (e.g. 0.47–0.53 ms)** = the
  disk is busy but answering fast: typical of random-read-heavy workloads
  (MongoDB, ticket T-4F5CBA0C). **Not** a performance bottleneck by itself.
- Treat the disk as the bottleneck only when readings sit **at** the
  capacity-derived ceiling from §2/§3, or `await` rises together with
  `util`.
- A long stretch of throughput pinned exactly at the §3 ceiling (e.g. a
  flat ~133 MB/s PL0 read rate) means saturation and the server can hang
  while saturated (ticket T-CC0FA37F) — raise the disk side AND find who
  issues the IO (see [guest-diagnostics.md](disk-pl-change-guide__guest-diagnostics.md)).
- Usage far below both ceilings → the source is the workload inside the
  guest, or the instance side binds: run the §4 cross-check first.

## 6. Official sources (re-verify reachability and numbers when citing)

- ESSD specs & formulas: <https://help.aliyun.com/zh/ecs/user-guide/essds>
- Block storage performance: <https://help.aliyun.com/zh/ecs/user-guide/block-storage-performance>
- ESSD AutoPL: <https://help.aliyun.com/zh/ecs/user-guide/essd-autopl-disks.md>
- Block storage overview: <https://help.aliyun.com/zh/ecs/user-guide/elastic-block-storage-devices.md>
- Regional ESSD (own limits, excluded from the ordinary matrix): <https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md>
