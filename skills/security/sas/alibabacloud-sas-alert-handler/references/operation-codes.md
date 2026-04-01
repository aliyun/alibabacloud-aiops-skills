# Operation Codes Reference

This document contains detailed information about all available operation codes (operateCode) for alert handling.

---

## operateCode User Language Mapping

| operateCode | User-Friendly Description |
|-------------|---------------------------|
| block_ip | Block IP |
| kill_and_quara | Kill and Quarantine Virus |
| virus_quara | Quarantine File |
| virus_quara_bin | Quarantine File |
| advance_mark_mis_info | Advanced Whitelist |
| mark_mis_info | Add to Whitelist |
| ignore | Ignore |
| manual_handled | Mark as Handled |
| rm_mark_mis_info | Remove from Whitelist |
| quara | Quarantine |
| kill_process | Kill Process |
| cleanup | Cleanup |

---

## Default Handling Recommendation Rules

| Alert Type | Default Action | Reason |
|------------|----------------|--------|
| Unusual Login | Block IP | Unusual login behavior detected, recommend blocking source IP |
| Malware/Virus | Kill and Quarantine | Malware detected, recommend immediate quarantine and removal |
| Malicious File (process ended) | Quarantine File | Process no longer exists, recommend quarantining residual malicious files |
| Container Security | Ignore | Container-related alert, requires case-by-case evaluation |
| Reverse Shell | Kill Process / Quarantine | Serious threat, recommend immediate termination |
| Webshell | Quarantine | Backend file detected, recommend quarantine |
| Suspicious API Call | Ignore | Cloud product alert, requires case-by-case evaluation |

---

## Category 1: Threat Handling (Active Threat Response)

| operateCode | Operation Name | Description | Additional Parameters |
|-------------|----------------|-------------|----------------------|
| block_ip | Block IP | Block malicious IP address | expireTime |
| kill_and_quara | Kill and Quarantine | Terminate process and quarantine file | subOperation |
| virus_quara | Virus Quarantine | Quarantine malicious file | subOperation |
| virus_quara_bin | Quarantine File | Quarantine malicious file (process no longer exists) | subOperation |
| kill_process | Kill Process | Terminate malicious process | None |
| kill_virus | Deep Scan | Deep clean malicious files | None |
| cleanup | Cleanup | Clean malicious files | None |
| quara | Quarantine | Quarantine operation | None |
| stop_container | Stop Container | Stop container running | None |
| kill_container_process | Kill Container Process | Terminate malicious process in container | None |
| disable_malicious_defense | Disable Malicious Defense | Disable defense feature | None |
| client_problem_check | Problem Investigation | Trigger problem investigation | **CLI Not Supported** |

---

## Category 2: Whitelist Operations

| operateCode | Operation Name | Description | Additional Parameters |
|-------------|----------------|-------------|----------------------|
| advance_mark_mis_info | Advanced Whitelist | Whitelist this alert + Add whitelist rules | MarkMissParam |
| mark_mis_info | Add to Whitelist | Only whitelist this alert | None |
| defense_mark_mis_info | Precise Defense Whitelist | Precise defense whitelist | None |
| rm_mark_mis_info | Remove from Whitelist | Remove whitelist rules | None |

### Whitelist Operation Comparison

| Operation | Scope | Future Impact |
|-----------|-------|---------------|
| advance_mark_mis_info | This alert + Future matching rules | Future alerts matching rules will be auto-whitelisted |
| mark_mis_info | This alert only | Future similar alerts will still trigger |

---

## Category 3: Ignore Operations

| operateCode | Operation Name | Description |
|-------------|----------------|-------------|
| ignore | Ignore | Ignore this alert, take no action |

---

## Category 4: Manual Handling Operations

| operateCode | Operation Name | Description |
|-------------|----------------|-------------|
| manual_handled | Mark as Manually Handled | Mark as handled through other means |
| cancle_manual | Cancel Manual Handling | Cancel the manually handled status |

---

## Alert Status Code Reference

| EventStatus | Description |
|-------------|-------------|
| 1 | Pending (most common) |
| 2 | Ignored |
| 4 | Confirmed |
| 8 | Marked as false positive |
| 16 | Processing |
| 32 | Completed |

---

## DescribeSecurityEventOperations Response Fields

| Field | Description |
|-------|-------------|
| OperationCode | Handling operation code |
| UserCanOperate | Whether current version supports this operation (must be true to execute) |
| OperationParams | Sub-operation configuration parameters |
| MarkFieldsSource | Available whitelist field list (used for advanced whitelist) |
| MarkField | Existing whitelist rules |

**⚠️ Critical Check: Only execute operations where `UserCanOperate=true`**
