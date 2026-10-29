# Configuration Drift Detection Reference

This document describes how to compare local configuration files (`ga-config.json`, `ga-listeners.json`) with the actual cloud state of GA resources, detect drift, and prompt the user to synchronize.

---

## 1. Drift Detection Scope

| Item | Local Source | Cloud API Source |
|---|---|---|
| Accelerator name/spec | `ga-config.json` | `describe-accelerator` / `get-basic-accelerator` |
| Acceleration regions | `ga-config.json` | `list-ip-sets` / `get-basic-ip-set` |
| Listeners | `ga-listeners.json` | `list-listeners` |
| Endpoint groups | `ga-listeners.json` | `list-endpoint-groups` + `describe-endpoint-group` |
| Endpoints | `ga-listeners.json` | `describe-endpoint-group` |
| Port overrides | `ga-listeners.json` | `describe-endpoint-group` |
| Basic accelerate IPs | `ga-config.json` | `list-basic-accelerate-ips` |
| Basic relations | `ga-config.json` | `list-basic-accelerate-ip-endpoint-relations` |

---

## 2. Standard Accelerator Drift Detection Script

```bash
source "${SKILL_ROOT}/scripts/init-session.sh"
bash "${SKILL_ROOT}/scripts/ga-detect-drift.sh"
```

For the standalone script source, see `scripts/ga-detect-drift.sh`.

---

## 3. Basic Accelerator Drift Detection Script

```bash
source "${SKILL_ROOT}/scripts/init-session.sh"
bash "${SKILL_ROOT}/scripts/ga-detect-drift-basic.sh"
```

For the standalone script source, see `scripts/ga-detect-drift-basic.sh`.

---

## 4. Drift Handling Strategies

### Strategy 1: Use Cloud State as Source of Truth

```bash
# Re-run the import script
bash import_standard_ga.sh $GA_ID
```

### Strategy 2: Use Local Config as Source of Truth

Use this strategy only when you are certain the local configuration is correct. Call the corresponding update APIs:
- `update-accelerator` / `update-basic-accelerator`
- `update-ip-set` / `update-basic-ip-set`
- `update-listener`
- `update-endpoint-group` / `update-basic-endpoint-group`

### Strategy 3: Report Only

Default recommendation. After detecting drift, display the difference list and let the user choose how to proceed.

---

## 5. Skill Integration Notes

Add a "Configuration drift detection" entry in the management section:

1. User triggers "Check GA configuration consistency" or "Sync configuration".
2. Read local `ga-config.json` and `ga-listeners.json`.
3. Call cloud APIs to fetch actual state.
4. Compare and output a drift report.
5. Ask the user:
   - Option 1: Use cloud state, update local files.
   - Option 2: Use local files, update cloud resources.
   - Option 3: View report only, take no action.

---

## 6. Notes

1. Skip runtime-only fields such as `create_time`, `expired_time`, and `state`.
2. Sort arrays before comparison to avoid false positives caused by ordering differences.
3. Exclude idempotent fields such as `ClientToken` and `RequestId`.
4. Exclude dynamic states such as `HealthStatus` from drift detection.
