# Migration Paths: SWAS <-> ECS and Cross-Region Moves

Decision support for `scripts/axes/swas_boundary_guide/swas_boundary_guide.py --migration-check`.
All wording is distilled from real support tickets; the rule cards and their
sources live in [references/swas-boundary-guide__boundary-rules.md](boundary-rules.md) (topic
`migration`). This skill only checks preconditions and prints the path --
every migration step is executed manually by the customer in the console.

## 1. First principles (state these before any path)

1. **Simple Application Server and ECS are different products.** There is no
   seamless conversion, no in-place product switch and no cross-product plan
   change. "Migration" always means creating a NEW resource in the target
   product/region and moving data to it.
2. **A SWAS instance cannot change its region.** Region moves go through the
   custom-image copy path (below).
3. **Image migration hard precondition: target system disk >= source system
   disk.** Ticket example: a SWAS server with a 50 GB system disk cannot be
   image-migrated onto the 99 CNY/year ECS plan because that plan ships a
   40 GB system disk.
4. **Money warnings, always stated up front:**
   - a larger target disk/plan must be paid for (price difference is not
     waived);
   - the promotional renewal price (for example 99 CNY/year) cannot be
     inherited by the migrated/new instance;
   - warn the customer BEFORE they refund anything -- refunding forfeits
     new-customer promo eligibility (see
     [references/swas-boundary-guide__commerce-rules.md](commerce-rules.md)).

## 2. Path matrix

| Source | Target | Path | Script inputs |
|---|---|---|---|
| SWAS | SWAS, another region | Custom-image copy: (1) create custom image of the source server; (2) copy the image to the target region; (3) create a new server from the copied image in the target region | `--source-product swas --target-product swas --source-region <r1> --target-region <r2> --source-disk-gb <N>` |
| SWAS | ECS (any region) | Custom-image share/export: (1) create custom image of the SWAS server; (2) share/export the image so ECS can use it (console image wizard); (3) launch the ECS instance from the image; (4) verify target disk >= source disk first | `--source-product swas --target-product ecs --source-disk-gb <N> --target-disk-gb <M>` (or `--target-plan`) |
| ECS | ECS, another region | Out of this skill's focus; use the general ECS migration guide linked below | n/a |
| Any | Physical machine | Not a migration: Elastic Bare Metal Server purchase via the sales channel; never quote prices | n/a |
| Precondition fails / cost-sensitive | -- | Manual migration fallback (section 4) | n/a |

## 3. Verdict logic implemented by `--migration-check`

1. **Capacity check** (when both disk sizes are known):
   `target >= source` -> `FEASIBLE_WITH_CONDITIONS`; otherwise -> `BLOCKED`
   with the manual-migration fallback. When a disk size is missing the
   check is skipped and reported as degraded -- the source disk size is
   read in the console (SWAS: server overview; ECS: disk list). This skill
   does not call any disk API (none is whitelisted).
2. **Path selection** from the source/target product and region pair
   (matrix above).
3. **Availability lookup** (only when `--target-region` is given):
   read-only `DescribeAvailableResource` (DestinationResource=InstanceType)
   reports purchasable zones; with `--target-instance-type` it returns a
   WithStock verdict for that exact type. On API failure the mode degrades
   to "check the console buy page" -- it never guesses stock.
4. **Standing warnings** (price difference, promo renewal, manual fallback,
   ICP filing when the target is a region in mainland China) are printed on
   every run.

## 4. Manual migration fallback (ticket-verified advice)

When image preconditions fail or the price difference is a concern:

1. Back up data on the source: database dumps, web files, application
   configs, crontabs, SSL certificates.
2. Provision the target server (SWAS or ECS) in the target region.
3. Restore data and reconfigure services on the target.
4. Repoint DNS / public access to the target IP.

Manual effort depends on the data volume -- no cloud API can assess that
for the customer, and this skill never performs any of these steps.

## 5. Known-plan shortcut

`--target-plan 99yuan-ecs-economy-e` fills the target disk (40 GiB ESSD
Entry) and conditions of the 99 CNY/year ECS activity plan (economy-type e
instance, 2 vCPU / 2 GiB / 3 Mbps, real-name verified, one per person;
activity page: <https://www.aliyun.com/daily-act/ecs/99program>). The
classic ticket outcome: source SWAS disk 50 GiB > target 40 GiB ->
`BLOCKED`, recommend manual migration or a larger target plan.

## 6. Instance-family price surprise (SWAS-image-created ECS)

An ECS instance created from a SWAS image may land on a default instance
family different from the one the customer compares prices with (a ticket
observed `ecs.sn1.medium` next to an `ecs.e-c1m2.2xlarge` comparison).
Advice: compare instance families and discount rules before purchase;
pricing detail pages and the shared-family doc explain the difference:
<https://help.aliyun.com/zh/ecs/user-guide/shared-instance-families.md>.

## 7. Official references (only verified links)

- Migration guide (general): <https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md>
- Shared/economy instance families: <https://help.aliyun.com/zh/ecs/user-guide/shared-instance-families.md>
- 99 CNY/year ECS activity terms: <https://www.aliyun.com/daily-act/ecs/99program>
- What is Simple Application Server: <https://help.aliyun.com/zh/simple-application-server/product-overview/what-is-simple-application-server>

Console-image-wizard steps (create/copy/share custom image) have no
verified help-center URL in this skill's evidence set; guide the customer
through the console wizard screens instead of citing an unverified link.
