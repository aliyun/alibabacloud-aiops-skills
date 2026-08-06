# Capability Router

Classify each request into exactly one capability, collect its required inputs, then load only its primary references. Never substitute example values for a missing real resource. If a scope-changing input (region, project, target group/config) is missing, STOP and ask.

## config.modify
- when_to_use: change an existing collection config, its parse chain, or its fields.
- out_of_scope: creating a brand-new config (use `config.create`); installing the collector.
- entry_signals: "change/modify parsing", "add field", "fix regex", "adjust filter".
- required_inputs: region, project, config_name.
- optional_inputs: sample_log, target fields, machine_group.
- allowed_adapters: aliyun_sls, local validator (render/validate/diff).
- risk_level: R2 (write after diff).
- primary_refs: pipeline-config.md, index-coupling.md, field-conventions.md, plugin-version-gates.yaml, acceptance-criteria.md.
- callbacks: from troubleshoot.basic when a config root cause is found.
- success_state: config + index + data verified (U1, U6, U5).
- blocked_state: version unknown, or double-write (API/CRD) detected.
- failure_state: update rejected or acceptance fails after bounded polling.

## config.create
- when_to_use: base resources (project/logstore/group) exist; only a new config is needed.
- out_of_scope: creating project/logstore/group from scratch (use `onboarding.cloud`).
- entry_signals: "create a config to collect /var/log/...", "collect this container stdout".
- required_inputs: region, project, logstore, machine_group, scenario.
- optional_inputs: parse_mode, sample_log, index_fields, multiline.
- allowed_adapters: aliyun_sls, local validator.
- risk_level: R2.
- primary_refs: scenario-matrix.yaml, pipeline-config.md, index-coupling.md, plugin-version-gates.yaml, acceptance-criteria.md.
- success_state: config exists, bound to group, has data (U1, U2, U3, U5).
- blocked_state: scenario or machine_group type undetermined.
- failure_state: create/apply fails or no data after polling with source logs present.

## onboarding.cloud
- when_to_use: collector already installed; wire the whole cloud side end to end.
- out_of_scope: installing/upgrading the collector.
- entry_signals: "onboard this app to SLS", "set up collection end to end".
- required_inputs: region, project, logstore, machine_group, source.
- allowed_adapters: aliyun_sls, local validator.
- risk_level: R2 (per write step).
- order: Project -> Logstore -> Index -> MachineGroup -> PipelineConfig -> Apply -> Heartbeat -> Data -> Fields.
- primary_refs: pipeline-config.md, machine-group.md, index-coupling.md, acceptance-criteria.md, scenario-matrix.yaml.
- success_state: U1-U6 pass.
- blocked_state: heartbeat missing (route to troubleshoot.basic) or double-write.
- failure_state: any U-check fails and cannot be resolved within scope.

## machine_group.manage
- when_to_use: create/modify a machine group, its members, or config bindings.
- entry_signals: "add machine to group", "create user-defined group", "bind config".
- required_inputs: region, project, group.
- optional_inputs: machine_identify_type, machine_list, config_name.
- allowed_adapters: aliyun_sls.
- risk_level: R2 create/apply; R3 remove/unbind; R4 delete group.
- primary_refs: machine-group.md, cli-contracts.yaml, risk-and-approval.md.
- note: member add/remove uses get + full update-machine-group (the standard method; update-machine-group-machine not used).
- success_state: object and relations match target (U2, U4).
- failure_state: heartbeat still absent after member/identity fix.

## lens.query
- when_to_use: query the user's own collection alarms/status/pipeline metrics from SLS Lens.
- out_of_scope: business SQL analytics, dashboards.
- entry_signals: "show collection alarms", "is the collector busy", "pipeline send errors".
- required_inputs: business project, time range; lens entry auto-discovered via `get-logging` (fallback: user-provided/console).
- allowed_adapters: aliyun_sls (get-logs-v2).
- risk_level: R0.
- primary_refs: sls-lens-contracts.md, monitoring-queries.yaml, plugin-version-gates.yaml.
- success_state: query complete (meta.progress Complete) with full context reported.
- blocked_state: Lens entry not resolvable -> report "Lens evidence missing", continue other evidence where relevant.

## troubleshoot.basic
- when_to_use: no data, or heartbeat abnormal.
- out_of_scope: delay/duplicate/parse-failure/container-filter/data-loss (advanced troubleshooting).
- entry_signals: "no logs collected", "machine group heartbeat failed".
- required_inputs: region, project. optional: logstore, config, group.
- allowed_adapters: aliyun_sls, Lens.
- risk_level: R0 for diagnosis; fixes route back to config.modify/machine_group.manage.
- primary_refs: troubleshooting.md, alarm-catalog.yaml, sls-lens-contracts.md, machine-group.md.
- success_state: evidence-backed root cause, or a single explicit blocking next step.
- failure_state: neither cloud nor Lens evidence resolves and no host access is available.
