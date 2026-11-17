# Handoff matrix: what this skill recognizes and routes away

This tier is narrow on purpose: cloud-side **existence, displayed-status and
console-entry** questions. Everything that needs the guest OS, another
product's internals, a lifecycle decision, or a commercial outcome is
identified, explained with the evidence already in hand, and routed. The
routes below name only adjacent skills that verifiably exist in the same
ECS skill batch (or an explicitly human channel); never invent a skill name
mid-answer. `scripts/areas/console_resource_lookup/console_navigation.py --route "<symptom>"` prints the
matching row.

| Symptom recognized | What this skill still does | Route + sentence |
|---|---|---|
| Disk shows attached/"In Use" in console but the OS cannot see or use it; expanded capacity not visible in OS; partition vs disk confusion | Pin the cloud-side reading (sweep evidence, charge type); name the missing OS-layer step in plain words | to `area:disk-attach-os-visibility` / `area:disk-expand-diagnosis`. Sentence: "The cloud side is complete -- DescribeInstances evidence attached. What remains is inside the operating system (partition / file system / mount, or extending the partition), which this read-only lookup does not perform. Create a manual snapshot first in the console, then follow the init/expand guidance." |
| Instance exists but will not start, is stuck in Starting/Stopping, boot fails | Report only the control-plane state read and lock reasons | to `area:instance-state-diagnosis`. The state-machine fault is a different area than visibility. |
| Password / keypair cannot be set or reset; agent missing | Name the gating condition seen in Describe data | to `area:login-credential-repair`, with the reset-password doc from the entry map meanwhile |
| Policy authoring, permission tuning, `NoPermission.RAM` beyond naming the missing read action | Quote the failing action and the account the request id belongs to | to `area:ram-policy-diagnosis`; if the request id belongs to a third-party ecosystem platform, the answer is its own ticket channel (T-1D79BB54), and Alibaba Cloud side states it cannot act there |
| "How do I run this with the CLI / SDK?" | Nothing -- it is usage guidance | to `alibabacloud-cli-guidance` (the boundary named by the dedup scan) |
| Expired / released / "can my data come back" | Prove only whether the resource exists NOW | human lifecycle queue with a support ticket; entry map's billing pages. This skill never asserts a retention outcome |
| Refund / unsubscription / campaign and same-person benefit disputes / invoices / price differences | Navigation to the self-service entries + rule docs | human commercial channel. Sentence: "Refund and unsubscription decisions are commercial processes executed through the billing self-service entries (verified links in the entry map) or a support ticket. This skill does not and cannot execute them." (T-DF87AF28, T-B2672FDF, T-AB34E2B9 all closed this way) |
| Physical machine-room address | None possible -- console never displays it | reviewed human disclosure only. Sentence: "For security policy the console does not expose physical locations; the address is released via a manual channel after a purpose review (no stamped file exists). For ICP filing needs, the service contract in the billing console is the accepted document." (T-3F5A3E75, T-2000646E) |
| Security disposal banner lingering after appeal | Query the objective control-plane status as the anchor | the security management console / human security queue; ECS data cannot confirm or clear the banner (T-0ADBA324) |
| Simple Application Server, orders, DAS, Wanxiaozhi, DNS, OSS-file questions (T-E6CE8EA8) etc. | Identify the owning product with the concept map | entry map link for that product; inside another console, no diagnosis |
| Anything destructive: instance teardown, disk re-initialization, formatting, file deletion, OS changes | Detect and refuse to execute, every time | manual console steps ONLY, with the risk statement (stopped state required, data unrecoverable, take a snapshot first in the console yourself). This skill never emits an executable change path and never runs guest commands |

## Non-negotiable routing rules

1. Recognition beats execution: the deliverable of a routed case is the
   handoff sentence above plus the evidence collected so far, in the same
   report.
2. Snapshot-first reminder is mandatory wherever the next human step can
   destroy data (re-initialization, detach-and-release sequences, partition
   work). The reminder is guidance for the customer to act in the console --
   this skill never calls any snapshot API.
3. When even the route target is a human channel, say plainly what the skill
   cannot see (marketing eligibility, security-side records, another
   console's state, customer screen content), so expectations stay honest.
4. A customer pressing for direct execution of a destructive action gets the
   refusal sentence, never a workaround command.
