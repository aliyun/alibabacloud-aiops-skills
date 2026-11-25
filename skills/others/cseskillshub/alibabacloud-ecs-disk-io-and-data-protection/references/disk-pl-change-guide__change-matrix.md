# Module M2 — Change matrix: directions, one-way rules, impact, manual steps

Knowledge module for `scripts/axes/disk_pl_change_guide/disk_pl_advisor.py` (assess / verify modes).
Every row carries its evidence ticket. This skill never performs any of the
changes below — it judges eligibility, states impact, and hands the
customer the console path, then re-verifies afterwards by query.

## 1. Allowed directions & one-way rules

| From → To | Verdict | Key facts |
|---|---|---|
| ESSD fixed PL → higher PL (PL0→PL1 etc.) | **ALLOWED, online** | no restart; brief IO fluctuation; snapshot first (ticket T-984F24BA) |
| ESSD fixed PL → lower PL (downgrade direction) | **VERIFY OFFICIAL** | upgrade path is confirmed; confirm the downgrade direction on the console change page / official ESSD page before promising it |
| ESSD fixed PL / Entry → ESSD AutoPL | **ALLOWED** | data preserved; snapshot first — and read the one-way rule below (tickets T-CB4F17DF / T-B525FD49) |
| **ESSD AutoPL → PL0 / PL1 / any fixed PL** | **DENIED — ONE-WAY** | verbatim (ticket T-B525FD49): "ESSD AutoPL disks do not support changing back to PL0 or PL1; once a disk was changed from PL0 to AutoPL it cannot be switched back to a fixed performance level" |
| **ESSD AutoPL → other category** | **DENIED / one-way boundary** | same boundary; verify on the console entry |
| Ultra disk / SSD disk → ESSD family (e.g. PL0) | **ALLOWED, online** | data is preserved; "will I lose data" was asked and answered snapshot-first in ticket T-584A7DD3 |
| Ultra/SSD → ESSD Entry, or ESSD → ultra/SSD (reverse) | **VERIFY OFFICIAL** | supported source/target pairs are listed on the console change page and the category-change doc |
| ESSD Entry → PL0/PL1 | **VERIFY OFFICIAL** | raising above the low Entry ceiling is the usual direction (40 GiB Entry = 2120 IOPS, ticket T-EE75C111); confirm the exact pair on the console |
| Regional ESSD (`cloud_regional_disk_auto`) | **OUT OF MATRIX** | own spec/limit page: <https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md> |
| Any capacity shrink (e.g. 700 GiB → 400 GiB) | **NOT THIS AREA** | hand off per handoff-boundaries.md (in alibabacloud-ecs-high-frequency-issues) (ticket T-E10A0001) |

**System disk vs data disk differ.** Which performance levels are
selectable can differ between a system disk and a data disk — the agent
in ticket T-E10A0001 pointed at exactly this difference
(<https://help.aliyun.com/zh/ecs/user-guide/change-the-category-of-a-disk#2c5e068047vd3>).
The console page shows the applicable set for the selected disk; read it
there, do not assert it from memory.

## 2. Impact & data-safety statements (relay verbatim in spirit)

From tickets T-984F24BA / T-584A7DD3:

1. Performance-level change is an **online operation — no instance
   restart is required**.
2. During the change window there may be **brief IO read/write
   fluctuation**: schedule it in an off-peak period.
3. Apart from that fluctuation, there is **no impact on the running
   instance, remote connections, or data integrity**.
4. Category changes keep existing data; still the mandatory order is
   **take a snapshot first, then change**. The snapshot itself is created
   by the customer (this skill only checks afterwards that one exists).
5. Changes are **asynchronous**: after submitting, watch the ECS task
   list for completion, then re-verify.
6. **Price difference / refunds are never quoted here** — estimate with
   the official pricing calculator or ask the sales manager
   (tickets T-8FCE8F40 / T-F7B7C8A6).

## 3. Preconditions checklist (before the customer clicks anything)

- [ ] Disk `Status` is `In_use` or `Available` (check via assess mode).
- [ ] A **recent accomplished snapshot** exists for the disk
      (assess mode's snapshot pre-check; if absent → create one first).
- [ ] Target pair exists in the change matrix above; a
      **VERIFY_OFFICIAL** verdict must be settled on the console page
      before instructing anyone.
- [ ] One-way direction understood (never move a disk onto AutoPL if the
      customer might later need a fixed PL).
- [ ] Off-peak window agreed (brief IO fluctuation).
- [ ] If the bottleneck analysis (assess/bottleneck modes) shows the
      instance side binds, warn that raising the PL will NOT raise
      throughput — the instance-type change is the real fix
      (ticket T-39B4EB79, performance-formulas.md (in alibabacloud-ecs-high-frequency-issues) §4).

## 4. Manual console steps (customer-performed; this skill performs none of them)

**A. Take a snapshot first**
1. ECS console → **Storage & Snapshots → Snapshots → Create Snapshot**.
2. Select the target disk (`d-xxxx`), name it recognizably.
3. Wait until the snapshot status shows `accomplished`.
Doc: <https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot>

**B. Change the performance level**
1. ECS console → **Storage & Snapshots → Disks** → find `d-xxxx`.
2. Open the change / performance-level entry in the Actions column.
3. Select the target PL; the page shows the resulting IOPS / throughput
   ceiling — read the target numbers from the page itself.
4. Confirm; the change runs online without a restart.
Doc: <https://help.aliyun.com/zh/ecs/user-guide/essds>

**C. Change the disk category**
1. Same disk list → the category-change entry.
2. Read the on-page constraints (they differ for system vs data disks).
Doc: <https://help.aliyun.com/zh/ecs/user-guide/change-the-category-of-a-disk.md>

**D. Watch the async task**
ECS console → task management shows the change task progress.
Doc: <https://help.aliyun.com/zh/ecs/user-guide/ecs-task-management.md>

**E. After the customer reports completion**
Run `python3 scripts/axes/disk_pl_change_guide/disk_pl_advisor.py --mode verify` with the expected
values; relay `OK` per field or point at the still-running task.

## 5. Refusal wording for in-skill change requests

If asked to perform the change (or take the snapshot, or run a guest
command) directly: state that this skill performs no cloud change by
design, show the console path from §4 instead, and offer the post-change
verify loop.
Never emit executable change commands — the console UI is the change path.
