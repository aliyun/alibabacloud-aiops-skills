# Verification Method

## Phase 1 Verification: Environment & Credentials

```bash
# Verify CLI version >= 3.3.3
aliyun version

# Verify credentials are valid (returns JSON, not error)
aliyun antiddos-public describe-instance-ip-address \
  --ddos-region-id cn-hangzhou --instance-type ecs --current-page 1 --page-size 1
```

**Success criteria**: CLI version output >= 3.3.3, `aliyun configure list` shows a valid profile, API call returns normal JSON.

**Abort criteria**: If any pre-check command returns a non-zero exit code or fails 3 consecutive times, output a standardized error report and execute `aliyun configure ai-mode disable`, then terminate the workflow.

## Phase 2 Verification: RAM Permissions

```bash
# Basic Protection permission verification
aliyun antiddos-public describe-instance-ip-address \
  --ddos-region-id cn-hangzhou --instance-type ecs --current-page 1 --page-size 1

# Native Protection permission verification
aliyun ddosbgp describe-instance-list --page-no 1 --page-size 1 --region cn-hangzhou

# Anti-DDoS Pro permission verification (two Regions)
aliyun ddoscoo describe-instances --page-number 1 --page-size 1 --region cn-hangzhou
aliyun ddoscoo describe-instances --page-number 1 --page-size 1 --region ap-southeast-1
```

**Success criteria**: All commands return valid JSON responses, no `Forbidden.RAM` or `NoPermission` errors.

## Phase 3 Verification: Product Inventory (Mandatory Traversal)

**Success criteria**:
1. Instance list queries have been executed for every Region (even empty list returns count as successful execution)
2. All provisioned instances have been discovered and logged
3. No Regions were skipped due to empty lists or InvalidRegion errors

## Phase 5 Verification: Inspection Execution & Report

**Mandatory call verification**:
1. Native Protection's describe-ddos-event, describe-pack-ip-list, describe-traffic have all been called
2. Anti-DDoS Pro's describe-ddos-events, describe-domain-qps-list, describe-port-flow-list, describe-domain-status-code-list have all been called
3. Even if a product has no instances, the above APIs have been executed as probes

**Data consistency verification**:
1. Total instance count in report summary = sum of Region detail instance counts
2. Total protected IP count in report summary = sum of per-instance associated IP counts
3. No duplicate counting (same instance or IP deduplicated across multi-Region queries)
4. Empty values annotated as "0", not omitted

**Report format verification**:
1. Report strictly follows the prescribed template structure, no sections omitted
2. All assets grouped by Region
3. Both base period and compare period data have been retrieved
4. Period-over-period analysis calculations are correct
5. Anomaly indicators are flagged (+/-30% attention needed, +/-100% anomaly)

## Overall Verification

```bash
# Confirm AI-Mode is disabled (final step for ALL exit paths)
aliyun configure ai-mode disable
```

**Success criteria**: AI-Mode has been disabled before final exit, regardless of whether the workflow completed successfully or was terminated due to an exception.
