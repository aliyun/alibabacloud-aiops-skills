# Hand-off matrix: adjacent areas this skill must NOT claim

The scenario boundary is the product. Every row below was a live support thread
where the Cloud Assistant channel appeared in the story but the
substance belonged elsewhere; the skill's job is to recognise the pattern early,
carry the evidence it already gathered, and route it - the wrong-claim itself
costs the customer rounds of clarification.

Hand-off is a statement plus a package, not a shrug: emit the reason, the
evidence already collected (report attached), and the destination.

## Routes

| Recognise | Destination | Say (customer-facing shape) | Evidence this skill already has | Cases |
| --- | --- | --- | --- | --- |
| Disk resized/paid but partition or filesystem still old size; growpart / resize2fs / diskpart questions; the console one-click expansion entry | `area:disk-expand-diagnosis` | "Why the assistant task failed is classified above; the growth itself is the disk-expansion scenario. Snapshot before any expand step." | failed task Output and exit code; lifecycle state; guest OS; whitelisted `df_h` reading where consented | T-79753A0F, T-521F4C4C, T-478C2A19, T-99046C78, T-D6F80375 |
| Instance will not start, stuck in Stopping/Starting, VNC black screen, boot to repair environment | `area:instance-state-diagnosis` | "The agent verdict is unreliable while the OS is down; this belongs to the boot/lifecycle checks. Here is what is already confirmed: visibility, account, OS, last invocation results." | lifecycle status, ownership, last successful/failed history | T-DE98E694, T-E172703F, T-75912401 |
| Slow disk IO, IOPS/BPS at spec ceiling as the complaint itself | `area:resource-bottleneck` | "The command symptoms may share the same root - the IO performance question goes to its own scenario." | history timing, saturation candidates from this report (hypotheses, not measurements) | T-02E6175C, T-DE98E694 |
| Workbench CLI behavior: non-default SSH port handling, session-mode downgrades, tool-side transfer issues | `alibabacloud-workbench-cli` | "This is the Workbench CLI tool's own behavior, not a Cloud Assistant fault; interim path is a native SSH client." | nothing to carry; state the distinction | T-27821D2C |
| OS-internal deep troubleshooting, or third-party software compatibility while the channel works | `alibabacloud-ecs-linux-os-troubleshooting` (or manual for software compatibility) | "Commands are reaching the guest and failing inside it: package managers and vendor compatibility matrices are the next read." | the invocation Output, which already carries the installer error text | T-A9825E98 |
| Capacity/inode accounting as the ask itself (growth planning, cleanup execution) rather than a df reading that excludes an environment cause | the disk capacity and cleanup scenario (manual steps if no capacity skill is installed) | "The df readings above transfer with the report; the cleanup execution belongs to the capacity scenario." | `df_h` / `df_i` / `du_top` outputs | (scenario-boundary decision) |
| Leaked access key still producing commands; malware cleanup; incident response | manual - the security response flow | "Evidence list first (this report), then: disable the key in the RAM console, snapshot disks before touching anything, respond with a security team, restrict the new key." | `invocations` history per region; snapshot readiness via `snapshot-guard` | T-2A028B99, T-9BEAB951 |
| Anything destructive or state-changing: deleting files/snapshots, killing processes, starting/stopping services, reboots, re-initialisation, software install | manual only | Console path + risk statement + who owns the decision. Never a command run by this skill. | whatever narrowed the option space in the report | throughout |

## Anti-patterns the source cases produced

- **Adopting a timing claim.** "It broke right after I installed Cloud
  Assistant" (T-75912401): support proved registry damage independently. The
  correct move was what the human did - test the causation claim against
  evidence, then route - not opening an agent-repair branch.
- **Treating every failed task as an agent failure.** T-A9825E98 shows the
  opposite half: channel healthy, content incompatible. Classifying first
  prevents a useless agent-reinstall loop.
- **Answering the expansion ask through this skill.** Half the scenario's volume
  enters through expansion language (T-99046C78, T-79753A0F): the answer to
  "why did the task fail" belongs here; the answer to "how do I grow the
  partition" belongs to the disk-expand area, and saying so early is the fix.
- **Letting the ownership check come late.** T-D87E8F47 spent the whole thread
  discovering the instance was not even the customer's. The check is step one
  in `triage` for that reason.

## Hand-off wording rules

1. Name what was already ruled out, so the next skill does not repeat the
   prechecks (account, region, visibility, lifecycle, history summary).
2. Attach the report; a hand-off without the evidence package restarts the
   customer's story from zero.
3. Where the destination is a manual flow (security, OS repair), give the
   ordered human steps - never leave the impression the skill could have done
   it.
4. Do not invent console navigation for preview-stage features; the source
   case found the one-click expansion entry visible or not per account
   (T-79753A0F), and the honest answer was "where the entry is absent, the
   documented command path is the alternative".
