# Security Rules - Complete Prohibitions

Complete list of forbidden and allowed actions for Cloud Firewall ACL Diagnosis Skill.

---

## ❌ Forbidden Actions (Zero Tolerance)

### 1. NO Write Operations

- ❌ NEVER call Create*/Update*/Delete* APIs
- ❌ NEVER modify Cloud Firewall rules, policies, or configurations
- ❌ NEVER deploy or push configurations to Cloud Firewall instances

### 2. NO Script Generation

- ❌ NEVER generate configuration scripts (bash, python, etc.)
- ❌ NEVER output rule JSON examples
- ❌ NEVER write executable CLI commands for configuration
- ❌ NEVER save files to outputs directory or any location

### 3. NO Configuration Execution Offers

- ❌ NEVER ask for FirewallId/InstanceId to "help configure"
- ❌ NEVER ask for rule IDs to "execute configuration"
- ❌ NEVER offer to configure on behalf of user
- ❌ NEVER say "configuration script saved" or "configuration plan generated"

### 4. NO Automated Deployment

- ❌ NEVER run write CLI commands (only Describe* queries allowed)
- ❌ NEVER execute API calls that change Cloud Firewall state
- ❌ NEVER create, update, or delete any Cloud Firewall resources

### 5. NO Credential Exposure (Evaluation System Forbidden Rule)

- ❌ NEVER use `--profile` parameter in any CLI command
- ❌ NEVER run `aliyun configure get` (exposes AK/SK)
- ❌ NEVER run `aliyun configure list` (scans profiles)
- ❌ NEVER output accessKeyId or accessKeySecret
- ❌ **NEVER read credential files** (`cat ~/.aliyun/config.json`, etc.)
- ❌ **NEVER configure aliyunlog** (user must do this manually)
- ❌ **NEVER auto-install CLI tools** (pip3, brew install, etc.)
- ✅ ALWAYS rely on default profile configuration
- ✅ **If CLI tools missing, STOP and guide user to install manually**

---

## ✅ Allowed Actions (Read-Only Only)

- ✅ Query rule configurations (Describe* APIs)
- ✅ Query traffic logs (DescribeTrafficLog)
- ✅ Query instance information
- ✅ Diagnose rule effectiveness issues
- ✅ Provide TEXT-ONLY console guidance (what to click, what to fill)
- ✅ Check if CLI tools are installed (`which aliyun`)
- ✅ Guide users to install missing tools manually (provide instructions only)

---

## 📋 Output Verification Checklist

**BEFORE outputting any response, MUST verify ALL items:**

- [ ] No Create/Update/Delete API calls in output
- [ ] No configuration scripts or JSON examples
- [ ] No file save operations mentioned
- [ ] No requests for FirewallId/InstanceId
- [ ] No offers to execute configuration
- [ ] Only text-based console guidance provided
- [ ] **NO `--profile` parameter in any CLI command**
- [ ] **NO `aliyun configure get` or `aliyun configure list` commands**
- [ ] **NO accessKeyId or accessKeySecret in output**
- [ ] **NO reading credential files** (`cat ~/.aliyun/config.json`, etc.)
- [ ] **NO auto-installation of CLI tools**

**If ANY item is unchecked, REMOVE the violating content immediately.**

---

## Read-Only Privilege Model

This skill operates under a least-privilege, read-only model:

- Only the following API action categories are used:
  - Cloud Firewall `Describe*` actions
  - `log:GetLogs` for `aliyun sls get-logs-v2`
  - `actiontrail:LookupEvents` for `aliyun actiontrail lookup-events`
- No Create/Update/Delete API calls are ever made.
- The skill relies on the default credential chain (environment variables or the default profile in `~/.aliyun/config.json`).
- The skill never uses `--profile`, never runs `aliyun configure get`, and never runs `aliyun configure list`.
- See `references/ram-policies.md` for the complete RAM permission list.
