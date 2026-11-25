# Sibling-Area Handoff Map (capability K6 + boundary recognition)

Clone tickets routinely end as somebody else's problem. Recognize the shift
early, deliver the wording below (machine-readable copy:
`scripts/axes/instance_clone_guide/_constants.py` `HANDOFF_MAP`, served by
`scripts/axes/instance_clone_guide/clone_guidance.py --handoff "<customer sentence>"`), and attach the
evidence so the customer never has to repeat themselves. Route names are
the batch's WORKING labels for neighboring guidance areas; per the
requirements dossier they still need alignment against the final batch
skill list.

## Map

| Sibling symptom (customer wording) | Why it is not clone guidance | Route (working label) | Evidence to attach |
|---|---|---|---|
| "website broke after I switched to the cloned security group", rule priority questions | The dispute is rule content / precedence / enforcement, not the clone chain. Real tickets: rules reviewed as identical yet behavior differed - one stayed unresolved even after a live agent inspected guest memory. Say "cannot self-prove" verbatim; escalate rather than guess. | security-group guidance area | instance ID, old and new group IDs, switch timestamp, reproduced symptom |
| "can the clone keep my IP?", "transfer the IP" | IP allocation/migration is a network-product capability. No written retention answer existed in the source tickets - do not improvise one. | public IP / EIP guidance area | current public IP, instance IDs, business need, acceptable switch window |
| "monitoring data jumps between the two hosts" | Needs in-guest agent identity file changes; this skill never touches the guest. | Cloud Monitor guidance area (guest side) | both instance IDs, symptom window, plugin version screenshot |
| "copy my server down to the IDC / export the image" | Cloud-to-offline direction: check the export limits first (encrypted image, marketplace-derived custom image, Windows Server image are not exportable; quoted agent wording - verify against the official export document). SMC runs one way only: on-premises INTO the cloud. Alternative: back up data, rebuild locally, import data. | image export / offline rebuild guidance area | image ID and type, export attempt error screenshot |
| "can this family be upgraded later?", "resize instead of clone?" | Resize capability questions are independent of cloning; state read-only spec facts and refer onward. | instance resize / variation guidance area | instance ID, current type, target type |
| "clone 20 machines with host-name rules automatically" | Bulk provisioning with orchestration is an operations-orchestration (OOS) template concern; cloning one instance is only one step of it. Recognize, do not implement. OOS overview: https://help.aliyun.com/zh/ecs/user-guide/overview-3.md | OOS / batch scaling area | fleet size, naming rule, region |
| "refund me", "compensate the fees from the failed clone", "withdraw my balance" | Money actions are commercial processes; a read-only technical skill has no voucher or refund authority. Point to the Billing Management console or the human ticket channel. | commercial / human support channel | order/instance IDs, bill screenshots, timeline |
| "our Apsara Stack (dedicated cloud, enterprise edition 3.x) machine fails at clone installation / avs service" | Not the public-cloud product surface at all; public channels cannot process it. Both source tickets received no in-session solution. | dedicated-cloud support channel named in the customer's contract | product edition/version, failing component, error screenshots |
| "run this command inside my server for me" | Execution in-guest is outside this skill by design. Offer the read-only paste-back path (post-clone-checklist.md) or refer to the in-guest execution capability area. | remote connection / Cloud Assistant guidance area | the exact commands, the expected output |
| "OSS auto-converts my images to WebP" | Unrelated to ECS cloning. | OSS product documentation area | bucket name, style configuration screenshot |

## Handoff sentence skeleton

Deliver three parts, in this order:

1. what the issue really is and why it leaves clone scope;
2. the concrete facts already gathered (instance IDs, group IDs, times,
   screenshots) so the next channel needs no re-collection;
3. the exact channel or console area to go to, stated without promising an
   outcome.

Related: clone-solution-matrix.md, clone-scope-and-billing.md,
progress-triage.md, post-clone-checklist.md (relative to this directory).
