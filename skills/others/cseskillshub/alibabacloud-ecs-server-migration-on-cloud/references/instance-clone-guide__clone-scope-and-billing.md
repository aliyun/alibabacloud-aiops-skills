# Clone Scope and Billing (capabilities K2 + K6 scope half)

What a clone copies, what it does not, and what it costs. Wording distilled
from real tickets in this tier; agent-quoted figures are marked. The
machine-readable entries live in `scripts/axes/instance_clone_guide/_constants.py` (`FEE_ITEMS`,
`RISK_NOTICES`, `FAQ_TOPICS`), served by `scripts/axes/instance_clone_guide/clone_guidance.py
--topic <key>`.

## What the clone includes

| Question (customer wording) | Answer | Topic key |
|---|---|---|
| Does the data disk come along? | Only disks ticked when the custom image was created. A disk such as /dev/vdb1 is NOT copied unless selected. | data-disk-included |
| The image says 300 GB but my disk is 5 TB? | The list column shows the system disk only during creation; the image detail page lists every associated disk once the image reaches Available. | image-capacity-display |
| Must the source be stopped? | No. Running instances can be imaged; data written during the capture is not included, so pause writes / stop the service during capture if you need a consistent point in time. | shutdown-needed |
| Will the source server be affected? | Image/clone operations do not modify the source instance; recommend low-peak operation and a manual snapshot anyway. | source-impact |
| It says the image uploads to an OSS bucket I never opened? | That bucket is managed by the ECS service, invisible to users, needs no activation, and carries only the temporary image object. Expected behavior, not a fault. | managed-oss-bucket |
| Can you see my other account's server? | No: account-scoped reads only (this skill and human agents share the boundary). Other-account facts = customer self-check screenshots. | cross-account-visibility |

## Cost composition (state before the customer starts)

1. Creating a custom image: free, but it creates snapshots by default and
   snapshot storage bills continuously.
2. Cross-region image copy: inter-region traffic fee.
3. The new instance (clone wizard or purchase from image): normal instance
   billing in the account that buys it.
4. Leftover snapshots after verification: still billed until deleted
   (customer cleanup step, closes every checklist).

Illustration quoted inside a real support conversation: about 0.016 CNY per
100 GB snapshot-hour (about 0.4 CNY per day). This is a quoted example, not
a price promise; the official snapshot billing document is the authority:
https://help.aliyun.com/document_detail/56159.html

Snapshot deletion guidance (customer console action):
https://help.aliyun.com/document_detail/128131.html

## Platform limits that bind the scope

- Export of custom images is NOT supported for: encrypted images, custom
  images derived from a cloud marketplace image, and Windows Server
  operating-system images. This three-item list is the support-agent
  wording from one ticket in this tier; VERIFY it against the official
  export document before repeating it as a rule:
  https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image
- SMC (Server Migration Center) moves servers INTO Alibaba Cloud only;
  there is no cloud-to-on-premises direction.
- Whether an instance runs on a marketplace image is not derivable from
  this skill's read-only contract; it is a customer console self-check.
- Windows clone specifics: not in scope for this release -- no ticket
  evidence existed; the only Windows fact is the export limit above.

## What this skill will NOT judge

Whether a target spec (for example 2 vCPU / 4 GiB) can carry the
customer's business workload. Tickets closed such questions by phone with
no written conclusion, so this skill states read-only spec facts only and
suggests a load test on the clone before cut-over. Never improvise a
capacity verdict.

Related: clone-solution-matrix.md, progress-triage.md,
post-clone-checklist.md, handoff-map.md (relative to this directory).
