# WAF Configuration Guidance Details

> This file contains detailed configuration plans and examples.
> Referenced from SKILL.md Section 2.2.

---

## 1. Whitelist - Skip Specific Rule ID

When users need to skip a specific rule (e.g., rule 900904) while keeping other rules active:

- **Use whitelist**, NOT custom rule (custom rules cannot "pass" requests)
- Configuration path: `Protection Configuration` → `Whitelist`
- In the "Skip Modules" section:
  - Select **Custom**
  - Expand **Web Core Protection Rules**
  - Select **Specific Rule ID**
  - Enter the rule ID (e.g., `900904`) and press Enter
  - Maximum 50 rule IDs supported
- This allows the request to skip only the specified rule ID, other WAF rules continue to detect

### Example: Skip rule 900904 for scanner IP

- Rule name: `whitelist_scan_900904_20260412`
- Match condition: IP contains `116.62.56.98` AND URI Path equals `/assets/something/services/AppModule.class/`
- Skip module: Web Core Protection Rules → Specific Rule ID → `900904`

---

## 2. IP Access Control Configuration Plans

### Option 1: Custom Rule (Recommended)

- Use `custom_acl` DefenseScene
- Configuration condition: IP **does not belong to** specified network segment (use `ne` or `all-not-match` operator)
- Configuration action: **Block** (`block`)
- Advantage: Clear logic, can be implemented with one rule

**Example**: Only allow `123.2.0.0/24` to access
- Rule name: `block_non_123.2.0.0_24`
- Match condition: IP does not belong to `123.2.0.0/24`
- Disposal action: Block

### Option 2: Whitelist + Domain Block Rule (Requires TWO Rules)

⚠️ **CRITICAL**: This option requires configuring **TWO rules** to work correctly:

**Rule 1 - Whitelist** (allows specific IP):
- Use `whitelist` DefenseScene
- Configuration condition: IP **contains** specified network segment (use `contain` operator)
- Skip modules: waf, cc, customrule, blacklist, antiscan
- Example: Whitelist `123.2.0.0/24`
  - Rule name: `whitelist_123.2.0.0_24`
  - Match condition: IP contains `123.2.0.0/24`

**Rule 2 - Domain Block Rule** (blocks all other IPs) ⭐ MUST HAVE:
- Use `custom_acl` DefenseScene
- Configuration condition: **Domain equals** target domain (e.g., `example.com`)
- Configuration action: **Block** (`block`)
- Example: Block all access to domain
  - Rule name: `block_domain_example_com`
  - Match condition: Domain equals `example.com`
  - Disposal action: Block

**Rule Order**: Whitelist MUST be above Domain Block Rule in the list

⚠️ **Common Mistake**: Configuring ONLY the whitelist WITHOUT the domain block rule will NOT block other IPs

---

## 3. Security Risk Warnings

### Scanner IP Whitelist Risk

**When request User-Agent contains scanner identifiers (e.g., `ANCHASHI-SCAN`, `Nessus`, `AWVS`, `sqlmap`, etc.), whitelisting this IP poses serious security risks:**
- Scanner can bypass specified detection rules to continue probing for vulnerabilities
- If in production environment, may lead to real vulnerabilities being exploited

**Handling Suggestions**:
1. **Limit URL scope**: Add URL conditions, only effective for specific paths
2. **Set temporary validity**: Clearly inform user this is temporary whitelisting, recommend cleanup after 24 hours
3. **Require user confirmation**: Ask "Confirm this is an internal test IP?"

### Rule Naming Convention

Rule names should include the following information for traceability:
```
whitelist_<purpose>_<date>_<IP>_<ruleID>
# Example: whitelist_scan_test_20260331_101.201.33.171_113160
```

### Effective Delay Notice

Remind users that rules typically take effect within **10-30 seconds** after configuration, may be longer during peak hours:
> "After configuration completes, expected to take effect within 30 seconds. For immediate verification, please test later."

---

## 4. Common Diagnosis Scenarios

### Scenario 1: Template Not Bound to Protection Object

**Problem Manifestation**: Rule has been created and status is normal, but traffic is not being blocked or allowed.

**Diagnosis Steps**:
1. Query template containing rule: `DescribeDefenseRules` to get rule's `TemplateId`
2. Query templates bound to protection object: `DescribeDefenseResourceTemplates` to get list of bound templates
3. Compare the two, if rule's template is not in bound list, this is the issue

**Solution**:
- Method 1: Bind template containing rule to protection object
  - Console: `Protection Configuration` → `Protection Objects` → Find target protection object → `Bind Template` → Select corresponding template
- Method 2: Recreate rule in already bound template
  - Console: `Protection Configuration` → `Web Core Protection` → `Custom Rules` → Create in already bound template

### Scenario 2: Rule Match Conditions Don't Match Actual Request

**Problem Manifestation**: Rule configured with specific URI or IP conditions, but actual request doesn't meet these conditions.

**Diagnosis Steps**:
1. Query rule configuration: Check match conditions in `conditions` field
2. Query traffic logs: Check `request_path`, `real_client_ip` and other fields
3. Compare rule conditions with actual request to see if they match

**Example**:
- Rule configuration: URI **Contains** `/chenhang`
- Actual request: `request_path: "/"`
- Conclusion: Path doesn't match, rule will not take effect
