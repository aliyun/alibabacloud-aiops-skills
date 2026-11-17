# Load Balancer Selection and Capability Boundaries (Scenario D)

Scope: "which load balancer should I use", "does ALB support FTP", "must I
use a cloud load balancer with auto scaling", "should production span
multiple zones". Answers are RULE CALIBERS plus the cloud facts this skill
can verify (instance zone spread, instance-type ceilings).

> Source discipline: the capability boundaries below are distilled from real
> support tickets of this tier; official SLB/ALB/NLB product documentation
> URLs are PENDING verification (this batch's doc search returned none).
> State the caliber and its ticket provenance; never invent a URL. Only the
> verified ECS-document links at the bottom may be cited.

## Product capability boundaries (rule calibers)

| Need | Guidance | Rule ID |
|---|---|---|
| Layer-7 traffic (HTTP / HTTPS / gRPC), host/path routing | ALB. ALB serves layer-7 workloads only -- it does NOT load-balance FTP or other layer-4 protocols | `SEL-FTP` |
| FTP with a large passive data-port range (e.g. 50000-50501) | NLB with a port-range listener; ALB cannot do this. Health-check the CONTROL port; keep active/passive mode consistent with the client; if file listing still fails, packet capture is required -- that step belongs to a human engineer | `SEL-FTP` |
| Classic layer-4 / layer-7 with simple port forwarding | CLB remains the classic choice; pick per protocol needs | -- (no rule entry; caliber only) |
| HTTPS end-to-end (client->LB and LB->backend both encrypted) on ALB Basic | NOT supported: an ALB Basic HTTPS listener requires an HTTP/gRPC backend-protocol server group. Either terminate TLS at the LB (backend HTTP) or use an edition/server-group combination that supports HTTPS backends (caliber from a real ticket; official doc pending) | `ALB-BASIC-HTTPS-BACKEND` |

## Auto scaling integration (the "new instances get no traffic" mechanism)

- Auto Scaling only CREATES instances; a new instance receives traffic only
  after it is attached to the LB server group. In a scaling group, attach
  the server group in the scaling configuration so attachment is automatic
  (customer console action; steps are guidance only).
- Self-built Nginx as the "load balancer" does not integrate with Auto
  Scaling: the upstream server list must be maintained manually -- that is
  exactly why the cloud LB + scaling-group pattern is recommended.
- Application state: new instances must reach shared data stores through
  routable addresses (e.g. the source server's private IP or a managed
  database), never 127.0.0.1.
- Details and the standard architecture: `references/slb-backend-diagnosis__ess-lb-integration.md`.

## Cross-zone deployment (rule + verifiable fact)

- Caliber: choose based on the business's availability requirements -- if
  zone-level fault tolerance is needed, deploy backends across multiple
  zones; this is a business-side decision, not a platform default.
- Verifiable fact: the entry script computes the zone spread of the given
  backend instances from `ecs DescribeInstances` and reports `SINGLE ZONE`
  or `multi-zone` (rule `SEL-MULTI-ZONE`).
- Architecture background (verified doc):
  https://help.aliyun.com/zh/ecs/user-guide/hablog.md

## Instance-type ceilings (for "one backend is busier than the others")

When customers suspect unequal load with equal LB weights, the script reads
the instance-type ceilings (CPU, memory, bandwidth, PPS fields returned by
the API) via `ecs DescribeInstanceTypes` -- best-effort: without the
(unverified) permission point the call degrades with a `[WARN]` and the
section is marked degraded. Compare ceilings against the returned latest
metrics only as a CLUE; process-level attribution requires instance-side
inspection by the customer or the performance tier (candidate sibling -- see
`references/slb-backend-diagnosis__handoff-playbook.md`). Burstable instances have a
CPU-credit mechanism -- an unlimited-performance-mode instance can behave
differently from its peers. Family differences (verified docs):

- https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families.md
- https://help.aliyun.com/zh/ecs/user-guide/enhanced-instance-families.md

## Out-of-scope sub-requests seen in this scenario

- Instance spec-change restrictions (e.g. an e-family instance cannot be
  changed to certain newer families): belongs to the spec-change tier
  (candidate sibling -- see `references/slb-backend-diagnosis__handoff-playbook.md`); this skill
  only answers the load-balancer architecture sub-question of such tickets.
- Cost-optimization sizing for peak events: give the standard architecture
  (LB + multi-zone backends + Auto Scaling + managed database/cache), and
  route pricing questions to the billing tiers.

## Cited documents (verified links only)

- High-availability architecture: https://help.aliyun.com/zh/ecs/user-guide/hablog.md
- ECS overview (product relationships): https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md
- Instance family overview: https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families.md
- Enhanced instance families: https://help.aliyun.com/zh/ecs/user-guide/enhanced-instance-families.md
