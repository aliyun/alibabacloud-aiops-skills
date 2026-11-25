# Clone Solution Matrix (capability K1)

Guidance for "copy this server", "make another machine with the same
configuration", "move the environment to my other account/region". The
customer performs every console step; this skill selects the path, narrates
entries / expected results / fallbacks, and verifies results read-only with
`scripts/axes/instance_clone_guide/clone_readiness_check.py`. The machine-readable version of this
matrix lives in `scripts/axes/instance_clone_guide/_constants.py` (`CLONE_PATHS`) and is served by
`scripts/axes/instance_clone_guide/clone_guidance.py --plan`.

## Quadrants

| Source to target | Console wizard | Custom-image chain |
|---|---|---|
| Same account, same region | yes - clone ECS instances feature | optional fallback |
| Same account, other region | no | yes: image -> copy image -> build there |
| Other account, same region | no | yes: image -> share image -> target builds |
| Other account, other region | no | yes, all four steps in order |

The clone wizard is documented at the help-center page "Clone ECS
instances" listed below. Everything beyond one account / one region rides
the image chain: create custom image -> copy image (cross-region) -> share
image (cross-account) -> land (new purchase from the image, or
replace-operating-system on an existing target instance).

## The four chain steps, with the traps seen in real tickets

1. **Create a custom image from the source instance.** Tick every data disk
   that must be copied. Trap: the image LIST shows only the system-disk
   capacity while creation runs; associated data disks appear on the image
   DETAIL page after completion (support-agent-verified wording).
2. **Copy the image to the destination region** (cross-region only). Trap:
   customers "lose" the copied image by leaving the console region selector
   on the source region. Cross-region copies incur traffic fees.
3. **Share the custom image with the target account UID** (cross-account
   only). Sharing is pushed from the source account; the target cannot pull.
   For cross-account AND cross-region, share the DESTINATION-REGION copy so
   the target account sees it where it will build.
4. **Land the clone in the target account.**
   - No target yet: buy a new instance selecting the custom/shared image.
   - Existing target instance: replace-operating-system with the image.
     HIGH RISK - this clears the target system disk: state the risk, tell
     the customer to take a manual snapshot of the target first, obtain an
     explicit acknowledgment, and only then continue guiding.

Mandatory up-front notices in every path: the source instance is not
modified by cloning; downtime on the source is not required (data written
during capture is not in the image); the fee composition is free image +
billable snapshots + cross-region copy traffic + the new instance;
completion time is never promised (see progress-triage.md).

## Cross-account visibility (hard boundary)

Read-only queries -- this skill's or a human agent's -- see only the account
behind the configured credential. Facts about the other account's instance
(its disks, its image visibility) are always customer self-check items:
"please log into that account and paste the console screenshot back".

## Console wording caveat

Console menu names change between versions. The exact click labels above
were distilled from support-ticket evidence, not from screenshots verified
this run. Quote the linked official guides as the authority, and have the
customer confirm each step's expected screen before proceeding.

## Official guides (verify before quoting; captured from tier research)

- Clone ECS instances:
  https://help.aliyun.com/zh/ecs/user-guide/clone-instances.md
- Create a custom image from an instance:
  https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance
- Copy a custom image:
  https://help.aliyun.com/zh/ecs/user-guide/copy-an-image
- Share a custom image:
  https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image
- Replace the operating system of an instance:
  https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance
- Create a snapshot (mandatory pre-step before any replace-operating-system
  guidance): https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot
  (also cited in tickets as https://help.aliyun.com/document_detail/25455.html)

Related: clone-scope-and-billing.md, progress-triage.md,
post-clone-checklist.md, handoff-map.md (relative to this directory).
