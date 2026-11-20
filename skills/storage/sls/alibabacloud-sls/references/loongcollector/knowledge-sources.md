# Knowledge Sources — provenance & drift tracking
#
# Drift rule: when a source file changes, re-verify the dependent reference(s) below.

meta:
  applicable_versions_default: "LoongCollector 1.x / 2.x / 3.x (version-gated per plugin-version-gates.yaml)"

references:
  navigation.md:
    source: []
    notes: "7 capabilities including install.deploy; Windows/Sidecar/uninstall still excluded."

  prerequisites.md:
    source: []
    notes: "Credential, scope and install adapter gates; stop conditions."

  cli-contracts.yaml:
    source: [related_apis.yaml]
    notes: "Live `aliyun sls <cmd> --help` verification plus ACK cs addon loongcollector, host install script, and CRD kubectl contracts."

  related-commands.md:
    source: [related_apis.yaml]
    notes: "Full aliyun sls command table."

  ram-policies.md:
    source: [related_apis.yaml]
    notes: "Per-workflow RAM Actions (ReadOnly/Operator/Destructive) + permission failure handling."

  risk-and-approval.md:
    source: []
    notes: "Approval / snapshot / rollback hard constraints."

  machine-group.md:
    source: []
    notes: "CLI-003 member-only changes use machine-group add-members / machine-group remove-members."

  pipeline-config.md:
    source: []
    notes: "Get-then-full-Update model; native-first; single input / single flusher_sls."

  plugin-version-gates.yaml:
    source: []
    notes: "1.x/2.x/3.x chain gates, binary processor gates, send limits, VC-001/002/003."

  index-coupling.md:
    source: []
    notes: "Config/index same-batch diff; status code default long; JSON subfield/prefix rules; anti-patterns."

  field-conventions.md:
    source: []
    notes: "Field naming, standard fields, index type priority."

  task-model.yaml:
    source: []
    notes: "scope-lock, plan-no-write, check structure."

  scenario-matrix.yaml:
    source: []
    notes: "host/docker/k8s/host_agentsight signals; collection default SLS API; k8s_crd is opt-in when user asks and apiserver reachable."

  input-agentsight.md:
    source:
      - https://github.com/alibaba/loongcollector/blob/main/docs/cn/plugins/input/native/input_agentsight.md
      - https://help.aliyun.com/zh/sls/collect-ai-agent-observability-agentsight-logs (verified 2026-08-20)
    notes: "Cloud min 3.3.9 + kernel 5.10 (help)."

  agentsight-agentloop.md:
    source:
      - https://help.aliyun.com/zh/sls/collect-ai-agent-observability-agentsight-logs (verified 2026-08-20)
    notes: "Fixed names runtime-ebpf-agentsight-config / ebpf-event; empty ProbeConfig default; ConfigAlreadyExist = lock no overwrite; mask mode=buildin."

  sls-lens-contracts.md:
    source: []
    notes: "Entry discovery via logging get (no starops/console-private); topic×version routing; field allowlist; query hard constraints."

  monitoring-queries.yaml:
    source: []
    notes: "Lens SQL library."

  troubleshooting.md:
    source: []
    notes: "no-data / heartbeat playbooks with evidence loop + minimal fix."

  alarm-catalog.yaml:
    source: []
    notes: "alarm cards: MULTI_CONFIG_MATCH_ALARM / INVALID_PROCESSOR_TYPE / DROP_LOG_ALARM."

  acceptance-criteria.md:
    source: []
    notes: "U1-U6 matrix + skill-creator CLI positive/negative patterns."

  verification-method.md:
    source: []
    notes: "Per-step verification commands including CRD U1/U3."

  install/install-ecs.md:
    source: [https://help.aliyun.com/zh/sls/loongcollector-installation-linux]
    notes: "Cloud Assistant + official loongcollector.sh; no OOS."

  install/install-host.md:
    source: [https://help.aliyun.com/zh/sls/loongcollector-installation-linux]
    notes: "Same script via user SSH alias."

  install/install-ack.md:
    source: [https://help.aliyun.com/zh/sls/loongcollector-installation-kubernetes-1]
    notes: "aliyun cs addon name loongcollector; reuse k8s-log/k8s-group; collection default SLS API; temp public kubeconfig only for opt-in CRD."

  install/install-k8s.md:
    source: [https://help.aliyun.com/zh/sls/loongcollector-installation-kubernetes-1]
    notes: "kubectl custom package; AK/SK never in chat."

  crd-pipeline.md:
    source: []
    notes: "Writable ClusterAliyunPipelineConfig; opt-in when user asks and kube-apiserver reachable. Default collection is SLS API."
