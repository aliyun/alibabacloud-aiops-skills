# Deployment paths for game and application servers on ECS

Four verified paths from "I want a server running" to a concrete, evidence-
backed next step. The entry script labels the chosen one in the report and
attaches only the documents listed here -- no remembered or invented links.
The actual installation, purchase submission and any configuration inside the
guest are human steps; this file is the guidance the skill outputs.

## Which path applies

| What the customer is doing | Path |
|---|---|
| Setting up a new game or app backend on one instance | Path 1: fresh install |
| Cloning an already-built environment to more instances or another account | Path 2: custom-image copy |
| Moving an existing server from elsewhere onto ECS | Path 3: migrate onto ECS |
| Deciding what to buy before deploying at all | Path 4: size and stock first |

A vague request stays vague on purpose: ask one clarifying question (new
build, copy, move, or not sure yet) before choosing.

## Path 1 -- fresh install

1. Instance readiness first: Running, correct region, correct bound security
   group (the entry script's evidence section).
2. Pre-deploy space gate: free space and free inodes on the target file
   system, via the confirmed `space` and `inodes` probes or the customer's own
   pasted `df -h` and `df -i` output. A failing gate goes to the capacity tier
   (see [handoff-boundaries.md](handoff-boundaries.md)) BEFORE any install
   attempt -- installing onto a full disk produces the confusing half-deployed
   state this tier then has to untangle.
3. Mount check when a data disk exists: the `mounts` probe proves whether the
   intended directory really sits on that disk; an install that silently
   filled the system disk is a classic outcome of skipping this.
4. Install inside the guest is the customer's own action (download, unpack,
   runtime prerequisites). Sizing references:
   * instance type selection best practices:
     https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-instance-type-selection.md
   * high clock speed (hf) families -- the family document itself; game
     servers are single-thread-sensitive, which is why they are the common
     fit:
     https://help.aliyun.com/zh/ecs/user-guide/instance-families-with-high-clock-speeds.md
5. Ports: open ONLY the ports the server actually serves, inbound, on the
   bound security group -- ECS console, Instances, select the instance,
   Security Groups tab, add one rule per port. This skill never edits rules
   and does not link a port-guide document, because no verified URL for one is
   part of this package.
6. Post-deploy verification: see the numbered human checks in
   [guest-inspection-commands.md](guest-inspection-commands.md) -- listener
   check inside, connect test from outside. Process and port commands are not
   dispatchable from this skill.

Honest scope note: game-specific installation tutorials (server binaries,
mods, versions) are not part of this skill's verified documents. Point the
customer to the software's own official install documentation and keep the
evidence work here.

## Path 2 -- custom-image copy

1. Build and verify ONE instance through Path 1 first.
2. The customer creates the custom image from that instance in the console
   (image operations belong to the image tier's execution, not to this skill).
3. Launch the remaining instances from that image; cross-account or regional
   sharing follows the verified sharing document:
   https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image.md
4. After launching, the skill verifies the deployment result at cloud level:
   the entry script's region scan lists how many instances matched and which
   are Running -- batch confirmation of counts and states, not of guest
   contents. Guest-level identity collisions (duplicate machine
   identifiers, licences) remain the customer's checklist item.

## Path 3 -- migrate onto ECS

1. The verified server-migration guide covers the tool path and prerequisites:
   https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md
2. The skill's part is the target-side readiness only: instance exists,
   Running, region and zone recorded, disk space gate passed.
3. Migration tool execution, data-consistency checks, and deep whole-site
   migration diagnosis belong to the site-migration tier -- recognised and
   handed off, not attempted (see
   [handoff-boundaries.md](handoff-boundaries.md)).

## Path 4 -- size and stock first

1. Sizing references, by workload:
   * general selection method:
     https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-instance-type-selection.md
   * CPU single-thread-sensitive (typical game backends): the hf family
     document above;
   * GPU-backed application servers:
     https://help.aliyun.com/zh/ecs/user-guide/gpu-accelerated-compute-optimized-and-vgpu-accelerated-instance-families-1.md
   * individual / try-before-you-buy scenario list:
     https://help.aliyun.com/zh/ecs/user-guide/usage-scenarios-for-the-ecs-free-trial.md
2. Stock check: the entry script's availability query returns per-zone status
   for the wanted type. Report the verdict verbatim, with the sentence that
   it reflects the query moment and is not a purchase guarantee. The
   customer-visible purchase-time error `OperationDenied.NoStock` means the
   same thing one step later in the console: sold out at that instant.
3. Buying, spec changes, and refunds are console/commercial flows: guidance
   and the console path, never a submitted order.

## Identifying the wrong product

If the region scan matches nothing and the customer's "server" came with a
fixed bundle, low price, or a different console entry, it is often a Simple
Application Server rather than an ECS instance. The distinguishing reference:
https://help.aliyun.com/zh/ecs/user-guide/use-alibaba-cloud-client-to-manage-simple-application-servers.md
Say which product was checked and where; do not continue ECS deployment
guidance against an instance that does not exist.
