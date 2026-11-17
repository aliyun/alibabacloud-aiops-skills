# Scope Boundary and Handoff Phrases

This skill owns exactly one symptom area: the custom-image chain
(create -> progress/state -> size constraints -> use to create/replace ->
share/copy -> import/export guardrails). Everything else is recognized in
one sentence and handed off with the phrases below. Never pretend to
diagnose an out-of-scope area; never invent a target skill name that is not
listed here.

## Boundary table

| Recognize (customer words) | Verdict | Handoff target | Phrase to say |
|---|---|---|---|
| "replace-OS action itself fails / I need the OS-change risk checklist" | adjacent area | area:instance-state-diagnosis | "The OS-replacement action's own failure diagnosis belongs to the OS-replace skill; this skill only confirms image-side constraints (system-disk size floor, data-disk untouched rule), which we just did." |
| "no space left on device", "cannot create new file", "disk 100% full", "inode exhausted / file count limit" | in-disk capacity area | area:disk-expand-diagnosis | "Your disk filling up inside the OS is a capacity-cleanup case; pass my `df -h` / `df -i` output to the disk-capacity-cleanup skill." |
| "I expanded the disk but the OS still shows the old size" | partition/FS area | area:disk-expand-diagnosis | "Purchased capacity not visible inside the OS is the disk-expand area; the image side is already consistent (evidence above)." |
| "instance stuck at Starting/Stopping", "server won't boot" (not image-attributed) | instance state area | area:instance-state-diagnosis | "The boot-state diagnosis belongs to instance-state; if the state tooling finds an image-side cause (boot mode / drivers), the compatibility checklist in root-causes S3 is the follow-up." |
| "image/snapshot bills", "why charged", "unsubscribe refund", "delete blocked by usage" | billing & cleanup area | image billing & cleanup direction; console Billing and Cost | "I can explain the mechanism (an image depends on billed snapshots; overdue arrears release snapshots after the retention window and dependent images die with them), but bill attribution and unsubscription go to the billing flow." |
| "I want to delete this image/snapshot now" | irreversible | human process (manual console steps only) | "Deletion is never automated here. Impact if you delete: re-initialization from that image becomes impossible and the data is unrecoverable. Console path + risk notice provided." |
| "docker pull 401 from ghcr.io", "push to my image registry is slow" | container images | Container Registry (ACR) product line | "That is a container image / registry issue, a different product line from ECS custom images; ECS image tooling will not diagnose it." |
| "marketplace image vendor / third-party panel image problems" | vendor responsibility | the marketplace image provider | "Marketplace image quality and compatibility are the vendor's responsibility; contact the provider behind the listing (ticket-proven path)." |
| "Simple Application Server image" | different product | state the non-compatibility, stop | "ECS custom images and Simple Application Server are not interchangeable; data must be migrated manually." |
| "transfer my instance to another account" | commercial flow | console transfer flow | "Instance transfer has its own eligibility rules (campaign-priced instances may be ineligible); if transfer is denied, the in-scope alternative is the image chain: create image -> copy -> share -> create/replace on the target account." |

## Shared-word arbitration (overlap with the OS-replace skill)

"change system disk", "replace OS with an image" phrases overlap with
area:instance-state-diagnosis. Rule: if the complaint is about
the image itself (size, state, where it went, sharing), stay; if it is
about the replace-OS ORDER/action failing, hand off after contributing the
image-side facts (S2 rules) so the other skill starts with evidence.

## Degrade-to-manual triggers (no handoff skill exists)

- VNC also refuses login after credential resets -> evidence pack (what
  was tried, times, ids) -> human ticket; say plainly the skill cannot
  fix guest-internal auth.
- Region stock ("can I buy 2C2G in Zhangbei") -> buy-page link
  (console-guides) + DEGRADED (no in-scope stock API).
- "Exactly when will my image finish" -> dynamic facts only (snapshot
  progress), never an ETA promise.
