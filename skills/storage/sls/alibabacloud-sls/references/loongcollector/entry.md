# Log collection

Install or upgrade LoongCollector/Logtail, manage collection pipelines and machine
groups, and diagnose missing data or abnormal heartbeat.

## Start here

- For cloud operations or host/cluster access, read the [execution guide](workflow.md)
  for preflight, scope, authorization, error recovery and verification. Then load
  the task reference below. [Capability routing](navigation.md) lists detailed
  required inputs and outcomes.
- For local-only rendering or validation, use the applicable configuration reference
  and bundled helpers; no cloud or cluster connection is needed.
- For installation-only requests, finish after collector readiness. Continue to
  collection setup and business-data verification only when requested.

## Scenarios

| Task | Reference |
| --- | --- |
| Install or upgrade on ECS, self-hosted Linux, ACK or self-built Kubernetes | [ECS](install/install-ecs.md), [self-hosted Linux](install/install-host.md), [ACK](install/install-ack.md), [self-built Kubernetes](install/install-k8s.md) |
| Create or modify collection pipelines | [Pipeline configuration](pipeline-config.md), [index coupling](index-coupling.md) |
| Manage machine groups, members and bindings | [Machine groups](machine-group.md) |
| Configure AgentSight / Agentloop collection | [AgentSight workflow](agentsight-agentloop.md), [input options](input-agentsight.md) |
| Manage a Pipeline through Kubernetes CRD | [CRD workflow](crd-pipeline.md) |
| Query collection alarms, status or pipeline metrics | [Lens queries](sls-lens-contracts.md), [query templates](monitoring-queries.yaml) |
| Diagnose missing data or abnormal heartbeat | [Troubleshooting](troubleshooting.md), [alarm catalog](alarm-catalog.yaml) |

## Essential boundaries

- Use the SLS Pipeline API by default for Kubernetes collection and reuse the
  official Project and machine group. CRD management is opt-in for explicit
  GitOps/CRD requests with reachable cluster access. Use one management plane per config.
- Keep account/profile, region and target resources within the authorized scope.
  Pass an explicitly selected profile to CLI calls and ACK helpers with `--profile`.
- Resource changes require user authorization; preserve current settings and
  snapshots, run the applicable dry-runs, and verify actual post-change state.
- Use configured CLI authentication and the [shared observability setup](../../SKILL.md#observability).
  Keep credentials, kubeconfig, certificates and private notification URLs out of output.
- Execute SLS cloud calls as individual direct commands with literal parameters;
  preserve returned errors and evidence. Permission recovery follows the
  [execution guide](workflow.md#2-ram-policy).

**Out of scope.** Windows; Sidecar; uninstall/rollback/restart-as-lifecycle; creating ECS; OOS/ChatOps; writing `AliyunLogConfig` / `NamespaceAliyunPipelineConfig`; advanced troubleshooting (delay, duplicate, parse failure, container filter, data loss/truncation). `kubectl exec` and `docker exec` are forbidden. If the user asks for an out-of-scope lifecycle action, say so and stop that branch.

## Verification and reporting

Use [acceptance criteria](acceptance-criteria.md) and [verification commands](verification-method.md)
for collector readiness or the applicable U1-U6 collection checks. Use the
[report template](workflow.md#11-report-template) to distinguish completed,
partial, blocked and unverified work. [Risk and rollback](risk-and-approval.md)
covers snapshots, restoration and cleanup.
