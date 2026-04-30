# DDoS Pro Rule Operation Policy

## Warning: Rule Disabling Policy (Important!)

**When the user requests to disable a rule, the following constraints must be followed:**

### 1. Only Perform Disable Operations

Only call disable/switch APIs to turn off the rule. Never delete rules.

### 2. Never Delete Rules

Even if the disable operation fails, you **must not** call any delete API (e.g., `delete-web-cc-rule`, `delete-web-cc-rule-v2`, `delete-web-precise-access-rule`).

### 3. Never Modify Rule Content

Do not modify rule matching conditions, thresholds, or other configurations.

### 4. Failure Handling

- If the disable operation fails, inform the user of the failure reason
- **Do not** attempt to delete the rule or use other workarounds
- **Wait for the user's new instructions** before performing any other operations

### 5. Idempotent Check-Then-Act (Required)

Before executing any write operation, **always query the current state first** and skip the operation if the resource is already in the target state.

### 6. Pre-Operation Confirmation

```
Confirm operation: Disable rule {rule_name} (Domain: {domain})
- Operation type: Disable
- Will not delete the rule
- Will not modify rule content
- Can be re-enabled at any time

Continue? Reply "yes" to confirm
```

---

## Disable Commands by Rule Type

### CC Protection Rule

**Check current status**:
```bash
aliyun ddoscoo describe-web-cc-rules-v2 --domain '<domain>' --region <region-id>
```

**Disable CC custom rule**:
```bash
aliyun ddoscoo disable-web-cc-rule --domain '<domain>' --region <region-id>
```

**Re-enable CC custom rule**:
```bash
aliyun ddoscoo enable-web-cc-rule --domain '<domain>' --region <region-id>
```

### Precise Access Control

**Check current status**:
```bash
aliyun ddoscoo describe-web-precise-access-rule --domains '<domain>' --region <region-id>
```

**Toggle precise access control switch**:
```bash
aliyun ddoscoo modify-web-precise-access-switch --domain '<domain>' --config '{"PreciseRuleEnable": 0}' --region <region-id>
```

**Re-enable precise access control**:
```bash
aliyun ddoscoo modify-web-precise-access-switch --domain '<domain>' --config '{"PreciseRuleEnable": 1}' --region <region-id>
```

### Region Blocking

**Check current status**:
```bash
aliyun ddoscoo describe-web-area-block-configs --domains '<domain>' --region <region-id>
```

**Toggle region blocking switch**:
```bash
aliyun ddoscoo modify-web-area-block-switch --domain '<domain>' --config '{"RegionBlockSwitch": 0}' --region <region-id>
```

### Forbidden Operations

```bash
aliyun ddoscoo delete-web-cc-rule ...              # FORBIDDEN
aliyun ddoscoo delete-web-cc-rule-v2 ...           # FORBIDDEN
aliyun ddoscoo delete-web-precise-access-rule ...  # FORBIDDEN
```

---

## Operation Flowchart

```
User requests to disable/enable a rule
       |
Identify rule type (CC / Precise ACL / Region Block / etc.)
       |
Query current rule status (check-then-act)
       |
  +---------------------+
  | Already in target   |
  | state?              |
  +------+--------------+
     Yes | No
         |        |
   Inform user    Confirm operation with user
   (no action     (disable only, no deletion)
    needed)              |
                  Execute disable command
                         |
                    +-------------+
                    |   Success?  |
                    +------+------+
                       Yes | No
                           |        |
                           |   Report failure reason
                           |   Wait for user instructions
                           |   (Do NOT attempt to delete)
                           v
                      Operation complete
```
