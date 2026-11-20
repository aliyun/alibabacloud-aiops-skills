# M2: MLPS 2.0 (Dengbao) Control Areas vs. Platform Capabilities

Use this module for capability **S1**, that is, when the customer asks what a classified-protection (MLPS 2.0, also called "Dengbao") assessment looks at on ECS, or asks how platform capabilities map to the control areas the customer must prove.

## Evidence provenance (read first)

This skill ships WITHOUT verified support-ticket transcripts for this tier
(the tier's ticket corpus was not injected). The mapping below is therefore
built ONLY from (a) the tier trigger wording and (b) the official ECS help
documents that were verified as search hits for this skill (listed at the
bottom). Anything not covered here is **pending human verification**: say so
verbatim, and never invent clause numbers, document titles, or links.

## Responsibility split (the single most important customer misunderstanding)

- Having platform-level qualifications does NOT make the customer's business
  system compliant. MLPS 2.0 assessment targets the customer's INFORMATION
  SYSTEM (its application, hosts, network design, policies, and records);
  the assessment is performed by an accredited assessment body, not by the
  cloud provider.
- Platform side: the cloud infrastructure and platform services provide
  controls and capabilities customers can inherit or build on.
- Customer side: instance configuration, security-group design, OS hardening,
  account/permission design, log retention policy, backup policy, and the
  assessment process itself.
- The skill's role: map control areas to official capability documents, run
  the read-only inventory (S3), and be explicit about what stays manual.

## Control-area map (starting set)

"Level 1-5 / level 3 protection" refers to the protection levels of the
scheme; a level-3 system typically adds requirements such as two-factor
authentication for administrators, audit record retention, intrusion
prevention, and redundancy - always confirm the assessor's actual item list.

| Control area (customer wording) | What assessors typically examine | Platform-side capability / evidence | Official document (only citable link) |
|---|---|---|---|
| Operations and maintenance audit ("who logged into servers, can sessions be replayed") | Centralized O&M entry, identity binding, session recording and audit trail | Bastionhost (operations audit / session recording) integrated with ECS | https://help.aliyun.com/zh/ecs/user-guide/use-the-bastion-machine-for-operation-and-maintenance-to-meet-the-requirements-of-equal-protection-2-0.md |
| Security auditing and log retention ("are logs kept and tamper-evident") | Monitoring and audit data collection, retention handling | ECS monitoring and logging capability overview | https://help.aliyun.com/zh/ecs/user-guide/monitoring-and-logging.md |
| Shared responsibility baseline ("what does the platform already cover") | Where provider duties end and customer duties start | ECS security overview (shared-responsibility framing) | https://help.aliyun.com/zh/ecs/user-guide/security-overview.md |
| Secure computing environment - host layer ("OS baseline, patches, malicious code prevention") | Image provenance, OS security capability, patch cadence | Alibaba Cloud Linux (security-hardened OS baseline capabilities) | https://help.aliyun.com/zh/ecs/user-guide/alibaba-cloud-linux.md |
| Product capability scope ("which ECS features can support our design") | Network access control (security groups), disk redundancy/backup, image management | ECS product overview and function lists | https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md and https://help.aliyun.com/zh/ecs/user-guide/product-function-custom-node-ecs-normal.md |
| Console operation baseline (how the customer's staff operate instances manually) | Documented, repeatable operational procedures behind management-policy questions | Console quick-start guides (baseline operation reference only) | https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-a-windows-instance-and-build-an-iis-service.md and https://help.aliyun.com/zh/ecs/user-guide/use-the-ecs-instance-in-the-console.md |

Windows/Linux console guides above are weak-signal references kept ONLY as
operation baselines; do not present them as compliance evidence.

## Cryptographic assessment, covering the customer wording "MiPing" and cryptographic application security assessment

Cryptography-application assessment is a SEPARATE evaluation from MLPS 2.0
and has its own assessment process and criteria. The injected evidence for
this skill contains NO official document for it. Answer honestly: identify
which of the two evaluations the customer means, state that platform-side
cryptographic capability mapping for this skill is pending human
verification, and hand off to a human/support ticket for item-level advice.

## How the skill helps per control area (RO boundary)

1. S3 inventory (`--regions ...`) provides the factual asset list the
   assessor will sample from: instance IDs, status, zone, type, network,
   bound security-group IDs, public exposure flags.
2. This file supplies the "requirement <-> capability <-> document" table to
   paste into the customer's preparation notes.
3. Everything else - turning on bastionhost, adjusting security-group rules,
   enabling log delivery, key rotation - is a MANUAL customer action: give
   the console path and the risk note, never execute it (this skill is
   read-only and has no in-guest execution channel).

## Expansion discipline

The six rows are the complete citable set for this release. If the customer
raises another control area (e.g. physical/environmental requirements,
security-management policy documents), respond: outside this skill's
verified mapping; platform-side answers come from the shared-responsibility
document above; item-level interpretation belongs to the assessment body
and to human support.
