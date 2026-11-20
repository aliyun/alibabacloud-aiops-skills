# M5: Handoff Matrix - Recognize, Say the Sentence, Stop

This skill is a strictly read-only compliance-evidence guide. When the
conversation shows one of the symptom axes below, the request has left this
skill's scope. The required behavior is: **do not diagnose, do not attempt
any query beyond the whitelist, emit the matching handoff sentence (adjust
resource identifiers to what the customer actually said), and stop the
compliance workflow for that sub-request.**

| # | Symptom (customer wording) | Why it is out of scope | Handoff target | Handoff sentence to emit |
|---|---|---|---|---|
| 1 | "the disk is full", "cannot create new files", "inode exhausted", "file count limit", "need to free space" | Capacity/inode usage and cleanup is a separate capability (guest-side diagnostics and cleanup guidance), not compliance-evidence guidance | Disk space and inode governance capability (`alibabacloud-ecs-diagnose` family line) | "Disk usage and cleanup is handled by our disk-capacity diagnostics capability, not this compliance guide. I will hand you off to the instance disk-space diagnosis flow; nothing in this audit needs to change first." |
| 2 | "expanded the disk but the size did not take effect", "partition not grown" | Partition/resize propagation diagnosis is a dedicated flow | `alibabacloud-ecs-disk-expand-diagnosis` | "That looks like an expansion-not-applied issue, which has its own diagnosis skill (alibabacloud-ecs-disk-expand-diagnosis). This compliance guide stops here for that item." |
| 3 | "the instance will not start", "stuck between states after start/stop" | Instance lifecycle-state anomalies need their own evidence chain | `alibabacloud-ecs-instance-state-diagnosis` | "Instance start/stop anomalies belong to the instance-state diagnosis skill (alibabacloud-ecs-instance-state-diagnosis). Please run that first; we can resume the compliance inventory afterwards." |
| 4 | "disk IO is slow", "performance below spec" | Performance diagnosis is a separate axis | `alibabacloud-ecs-disk-io-diagnosis` | "Slow disk IO needs the disk-IO diagnosis skill (alibabacloud-ecs-disk-io-diagnosis); it is outside this compliance-evidence guide." |
| 5 | "actually turn on bastionhost / Security Center / WAF for me", "change my security group", "apply the fixes" | Remediation execution is a state change; this skill is read-only and never executes changes, including via "user-runnable" commands | Manual console steps (customer/administrator), each product's own documentation | "I can only guide you through the change - this skill never applies changes. Here are the console steps and risk notes; if you want execution help, use the human support channel or the product's own guidance." |
| 6 | "send the stamped original", "paper certificate", "sign an NDA", "custom attestation letter" | Legal-grade material handling is a commercial channel | Human / commercial support via a ticket | "Stamped, paper, or bespoke documents go through the commercial channel: please open a support ticket describing the exact document your auditor requires. I cannot promise content, seals, or timing from here." |
| 7 | "check the OS password policy / audit switch inside my Windows or Linux instance" | In-guest configuration requires in-instance execution, which this skill explicitly does not have | Customer's own administrators | "In-guest configuration checks are performed by your administrators inside the instance; this read-only guide lists them as manual checklist items but does not run anything in the guest." |

## Routing rules

- A single message can contain BOTH a compliance request and an out-of-scope
  symptom: serve the compliance part, and emit the exact handoff line(s) for
  the rest - never silently absorb a change request.
- Never "pre-fix" anything before a handoff: no changes, no guest commands,
  no document promises (SKILL.md Absolute Rules 1-3, 7).
- The four ECS diagnosis skills named above are routing pointers; if the
  customer's environment lacks them, hand the item to human support with the
  symptom wording instead.
