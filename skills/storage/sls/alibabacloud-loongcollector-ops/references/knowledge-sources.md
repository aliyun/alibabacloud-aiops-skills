# Knowledge Sources — provenance & drift tracking
#
# Every reference in this skill is derived from the `loongcollector-oncall` knowledge base
# (knowledge base root: loongcollector-oncall/knowledge/).
# This file records, per reference, the source_path(s) it was translated from, the
# translation notes (what changed vs. the source), and the applicable collector versions.
#
# Drift rule: when a source file changes, re-verify the dependent reference(s) below.
# As of 2026-07-14, all `starops sls` commands in the data source have been replaced
# with `aliyun sls` equivalents; ToolService/JWT discovery replaced with `get-logging`;
# "abort on Lens discovery failure" replaced with capability degradation;
# "SSH strictly forbidden" replaced with controlled-direct policy (see §8.4 of design doc);
# send rate limit versioned (< 3.0: 20 MB/s, >= 3.0: 25 MB/s).

meta:
  knowledge_root: "loongcollector-oncall/knowledge/"
  build_verified_at: "CLI live-verified against aliyun 3.4.6 + aliyun-cli-sls 0.7.0"
  design_docs:
    - architecture/loongcollector-ops-skill-overview.md
    - architecture/loongcollector-ops-skill-design.md
  applicable_versions_default: "LoongCollector 1.x / 2.x / 3.x (version-gated per plugin-version-gates.yaml)"

references:
  navigation.md:
    source: [architecture/loongcollector-ops-skill-design.md "§5 capability router"]
    notes: "6-capability subset; install/lifecycle/Windows/ACK/CRD-controller excluded."

  prerequisites.md:
    source: [architecture/loongcollector-ops-skill-design.md "§ preflight"]
    notes: "aliyun CLI + SLS plugin + credential + scope gates; stop conditions."

  cli-installation-guide.md:
    source: []
    notes: "Authored (no source asset). Verified against setup.sh install of aliyun 3.4.6 + aliyun-cli-sls 0.7.0."

  cli-contracts.yaml:
    source: [related_apis.yaml, architecture/loongcollector-ops-skill-design.md]
    notes: "Live `aliyun sls <cmd> --help` verification. status=confirmed|cli_gap|product_gap."

  related-commands.md:
    source: [related_apis.yaml]
    notes: "Full aliyun sls command table."

  ram-policies.md:
    source: [related_apis.yaml, architecture/loongcollector-ops-skill-design.md "§ RAM"]
    notes: "Per-workflow RAM Actions (ReadOnly/Operator/Destructive) + permission failure handling."

  risk-and-approval.md:
    source: [architecture/loongcollector-ops-skill-design.md "§ risk R0-R4"]
    notes: "Approval / snapshot / rollback hard constraints."

  machine-group.md:
    source: [base/loongcollector/machine-group-and-heartbeat.md]
    notes: "starops→aliyun translation; CLI-003 member update uses get + full update-machine-group (standard method; update-machine-group-machine not used)."

  pipeline-config.md:
    source:
      - base/collection-config/config-model.md
      - base/collection-config/input-plugins.md
      - base/collection-config/processor-plugins.md
    notes: "Get-then-full-Update model; native-first; single input / single flusher_sls."

  plugin-version-gates.yaml:
    source:
      - base/loongcollector/versions-and-limits.md
      - base/collection-config/invalid-config-patterns.md
      - troubleshooting/user/collection-playbooks.md
    notes: "1.x/2.x/3.x chain gates, binary processor gates, send limits, VC-001/002/003."

  index-coupling.md:
    source:
      - base/collection-config/field-naming-and-index.md
      - base/collection-config/invalid-config-patterns.md
      - base/index/index.md
    notes: "Config/index same-batch diff; status code default long; JSON subfield/prefix rules; anti-patterns."

  field-conventions.md:
    source: [base/collection-config/field-naming-and-index.md]
    notes: "Field naming, standard fields, index type priority."

  task-model.yaml:
    source: [architecture/loongcollector-ops-skill-design.md "§5.5 task object"]
    notes: "Adapted from VibeOps collection_job schema; scope-lock, plan-no-write, check structure."

  scenario-matrix.yaml:
    source: [base/collection-config/recipes.md]
    notes: "host/docker/k8s signals + required inputs; k8s_crd is out of scope (detect double-write only)."

  sls-lens-contracts.md:
    source:
      - troubleshooting/user/data-access.md
      - repos/vibeops-registry/sls-loongcollector.md
    notes: "Entry discovery via get-logging (no starops/console-private); topic×version routing; field allowlist; query hard constraints. Source data-access.md migrated to aliyun sls + get-logging on 2026-07-14."

  monitoring-queries.yaml:
    source:
      - troubleshooting/user/monitoring-queries.md
      - base/loongcollector/self-monitoring-metrics.md
    notes: "Lens SQL library translated to get-logs-v2."

  troubleshooting.md:
    source:
      - troubleshooting/user/collection-playbooks.md
      - troubleshooting/user/data-access.md
    notes: "no-data / heartbeat playbooks with evidence loop + minimal fix. Source starops→aliyun translation completed 2026-07-14."

  alarm-catalog.yaml:
    source:
      - base/collection-config/invalid-config-patterns.md
      - troubleshooting/user/collection-playbooks.md
    notes: "alarm cards: MULTI_CONFIG_MATCH_ALARM / INVALID_PROCESSOR_TYPE / DROP_LOG_ALARM."

  acceptance-criteria.md:
    source: [architecture/loongcollector-ops-skill-design.md "§ acceptance U1-U6"]
    notes: "U1-U6 matrix + skill-creator CLI positive/negative patterns."

  verification-method.md:
    source: [architecture/loongcollector-ops-skill-design.md]
    notes: "Per-step verification commands."
