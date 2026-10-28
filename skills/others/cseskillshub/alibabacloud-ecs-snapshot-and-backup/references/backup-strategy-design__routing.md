# Boundary Recognition and Hand-off Routing

Knowledge module for capability "recognize + hand off". The SCOPE GATE is
this skill's only confirmation gate: when the main symptom belongs to another
channel, answer the backup sub-question only, state the boundary in one
sentence, and hand off with an exit path. Never expand into another channel's
diagnosis.

## Routing table

| Neighbor symptom axis (customer wording) | Hand-off target | This skill still answers |
|---|---|---|
| Operating / inspecting / deleting / rolling back specific snapshots or single-disk snapshot lifecycle | `alibabacloud-ebs-disk-snapshot-management` (the online dedup counterpart; trigger-word split pending owner confirmation) | whether the design (which mechanism, frequency, retention, off-site) is right |
| Ransomware / intrusion / "decrypt my data / who is responsible" | security-incident response channel / human ticket | pre-incident layered design; the shared-responsibility fact that recovery requires a pre-infection backup; which data today's plan cannot cover |
| Cannot connect / VNC / IO-hang / performance faults | instance diagnosis channel | the snapshot-first protective step as customer guidance before any restart/repair attempt, plus its billing model |
| Disk capacity expansion pricing / partition operations | disk-expansion channel | snapshot-before-operation advice and its cost model |
| Account billing mix-ups, arrears, renewal, plan purchase, pay-as-you-go to subscription conversion | billing/commercial channel or human support | the trailing "how do I back up before I release/convert" sub-question only |
| Account subject change / cancelled enterprise entity / renewal blocked | real-name/commercial process | nothing designable here -- full hand-off; also state the factual release-and-data-loss risk |
| Non-ECS products (Web Hosting class, lightweight products) asking for "the ECS backup plan" | that product's line | identify the product first; state that ECS image/snapshot capabilities do not exist there |

## Hand-off wording templates

- Snapshot-object operations: "Managing or rolling back this specific
  snapshot belongs to `alibabacloud-ebs-disk-snapshot-management`; this
  assistant covers backup plan and policy design."
- Security incident: "Your main problem is malware containment and data
  recovery; this assistant only designs backup plans and policies. Handing
  you to the security emergency channel. Fact per the official model:
  without a pre-infection backup, the provider side cannot recover the
  data. After containment, design the layered plan per this report."
- Connectivity/performance: "The unreachable/hung instance is an instance
  diagnosis problem. Before anyone restarts it, take manual snapshots of
  the disks (you perform it) so the attempt is reversible; billing model in
  our report."
- Billing/commercial: "Refunds, packages and account-entity changes are
  commercial processes; this assistant explains backup billing MODELS only.
  Please open a ticket / contact business support for amounts."
- Non-ECS product: "Your source is not an ECS instance, so ECS
  snapshot/image mechanisms do not apply; please use that product's own
  backup/export path."

## Exit paths to include with every hand-off

1. the matching skill/channel name above (or "submit a ticket" when no
   skill exists in this batch),
2. the relevant official doc from the evidence set when one applies
   (security: [enable host security](https://help.aliyun.com/zh/ecs/user-guide/enable-host-security.md),
   [application security](https://help.aliyun.com/zh/ecs/user-guide/application-security.md);
   conversion: [change pay-as-you-go to subscription](https://help.aliyun.com/document_detail/49884.html)),
3. for third-party data-recovery services: the marketplace entry cited in
   the evidence batch (mark it as a third-party option, not an official
   recovery guarantee).

## Anti-patterns (never do these)

- Diagnosing ransomware containment, port hardening, or intrusion paths here.
- Quoting final billed amounts, promising package sizes, or processing
  refunds (model + example only -- see [billing-models.md](billing-models.md)).
- Running or scripting anything inside the guest instance (self-check
  checklists are given as instructions for the customer instead).
- Silently answering the neighbor symptom "just briefly" beyond the backup
  sub-question; one boundary sentence, then hand off.
- Neighbor skill/tier names other than `alibabacloud-ebs-disk-snapshot-management`
  are pending alignment with this batch's skill list; when no matching skill
  is confirmed, hand off to the human ticket channel with the symptom text.
