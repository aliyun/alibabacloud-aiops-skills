# Hand-off boundaries — what this skill recognizes but does not do

This skill owns two symptom areas: **using the BT panel and configuring its
sites**, and **the panel not opening**. Everything a thread grows into next
is routed with the evidence already collected, in the order the tree walked.
The neighbour list for this batch was never finalised, so the skill names
below are **candidate destinations to confirm against the live skill
catalogue before quoting them to a customer**. Where no receiving skill is
known, the destination is the plain console path, and the wording says so
rather than naming a skill that may not exist.

## The boundary in one table

| Growing symptom | Recognition signal | Destination | What travels with it |
| --- | --- | --- | --- |
| SSH (22) or RDP (3389) itself is dead and the panel question is downstream of that | remote login also fails; VNC-level breakage (T-169DAD1A) | area:remote-connection-entry, area:ssh-connection, area:windows-rdp | the cloud sweep results, agent status |
| Panel never installed, wrong image, "install version 7.9 for me" | `bt: command not found` echoes (T-1A92AC8C); version-pinning asks (T-9D4FCA66) | alibabacloud-ecs-install-extension (installation area); version choice itself stays the customer's | classification line, OS reading |
| Disk full / inode exhaustion needing cleanup or growth | `df` readings over threshold from probes or paste | area:disk-expand-diagnosis, then area:disk-expand-diagnosis | the watermark evidence |
| CPU/memory/load and OOM process-level analysis | pasted `top`/`free` (T-48B136B7, T-93C59065, T-E279891E) | area:resource-bottleneck; monitoring reads: the CloudMonitor console alert rules (no skill here reads alert history) | which layer proved resource causality |
| All public ports dead while the instance runs | blackhole signature (T-86E76038); cross-instance fear (T-C3DB3C57) | area:attack-blackhole-diagnosis | the full-status exclusion |
| Overdue account / bandwidth suspended | arrears signature (T-C9ABB457); no billing query verified | customer console: Billing -> Account overview (no skill yet) | layer states |
| ICP filing interception | page wording on domain access (T-36495FE9) | customer console: ICP filing status (no skill yet) | the exact response page |
| Malicious code, defacement, webshell at the application layer | injected content in sites (T-1A92AC8C) | area:host-intrusion-cleanup | server-layer evidence already gathered |
| OS corrupt, offline mount-and-repair needed | agent offline + SSH dead + lifecycle clean (T-169DAD1A) | area:instance-state-diagnosis (manual offline repair; never performed here) | every query result |
| Cloud Assistant agent itself missing/stopped | agent status false while instance runs | area:cloud-assistant-diagnosis | the agent-status row |
| A non-panel website slow or unreachable while the panel works | sites area, panel green | area:web-inaccessible-slow | layer table |
| Panel product dialogs, bugs, repair tools, plugin internals | after file probes show nothing missing (T-84281A4D's route) | the vendor's official support channel | probe evidence |

## The responsibility line, said in customer words

"The cloud side maintains server-layer reachability; the application layer
is maintained by you or the vendor" — the boundary support stated in
T-1A92AC8C. Panel credentials are guest-side secrets: nobody on the cloud
side holds or can hand them over; that is what `bt default` inside the
instance is for (§1 of [bt-site-config-guide.md](bt-panel-diagnosis__bt-site-config-guide.md)).
App deployments, code, DNS/CDN provider negotiations: guidance yes, work
done no — same as the human threads concluded.

## What never happens on the way out

Hand-off is recognition plus a written bridge, not remote execution elsewhere:

- no snapshot, restart, firewall change, credential reset or file edit is
  executed anywhere by this skill — every repair in every destination above
  is a manual customer step, ideally after the customer creates their own
  console snapshot first;
- the receiving area re-runs its own prechecks; this skill only ships its
  evidence list with the report (`handoff --area <n>` prints the wording);
- if the customer declines routing and asks this skill to "just fix it",
  the answer is the boundary statement plus the console path — and the
  read-only re-verification offer once they fix it themselves.
