# Security Rules - Complete Prohibitions

Complete list of forbidden and allowed actions for WAF Skill.

---

## ❌ Forbidden Actions (Zero Tolerance)

### 1. NO Write Operations

- ❌ NEVER call Create*/Update*/Delete* APIs
- ❌ NEVER modify WAF rules, templates, or protection objects
- ❌ NEVER deploy or push configurations to WAF instances

### 2. NO Script Generation

- ❌ NEVER generate configuration scripts (bash, python, etc.)
- ❌ NEVER output rule JSON examples
- ❌ NEVER write executable CLI commands for configuration
- ❌ NEVER save files to outputs directory or any location

### 3. NO Configuration Execution Offers

- ❌ NEVER ask for INSTANCE_ID to "help configure"
- ❌ NEVER ask for TEMPLATE_ID to "execute configuration"
- ❌ NEVER offer to configure on behalf of user
- ❌ NEVER say "configuration script saved" or "generate configuration plan"

### 4. NO Automated Deployment

- ❌ NEVER run write CLI commands (only Describe* queries allowed)
- ❌ NEVER execute API calls that change WAF state
- ❌ NEVER create, update, or delete any WAF resources

### 5. NO Credential Exposure (Evaluation system forbidden rule)

- ❌ NEVER use `--profile` parameter in any CLI command
- ❌ NEVER run `aliyun configure get` (exposes AK/SK)
- ❌ NEVER run `aliyun configure list` (scans profiles)
- ❌ NEVER output accessKeyId or accessKeySecret
- ❌ **NEVER read credential files** (`cat ~/.aliyun/config.json`, `cat ~/.aliyunlog/config`, etc.)
- ❌ **NEVER configure aliyunlog** (user must do this manually)
- ❌ **NEVER auto-install CLI tools** (pip3, brew install, etc.)
- ✅ ALWAYS rely on default profile configuration
- ✅ **If aliyunlog not configured, STOP and tell user to run `aliyunlog configure` first**
- ✅ **If CLI tools missing, STOP and guide user to install manually**

---

## ✅ Allowed Actions (Read-Only Only)

- ✅ Query rule configurations (Describe* APIs)
- ✅ Query traffic logs (aliyunlog get_log)
- ✅ Query instance information
- ✅ Diagnose rule effectiveness issues
- ✅ Provide TEXT-ONLY console guidance (what to click, what to fill)
- ✅ Check if CLI tools are installed (`which aliyun`, `which aliyunlog`)
- ✅ Guide users to install missing tools manually (provide instructions only)

---

## 📋 Output Verification Checklist

**BEFORE outputting any response, MUST verify ALL items:**

- [ ] No Create/Update/Delete API calls in output
- [ ] No configuration scripts or JSON examples
- [ ] No file save operations mentioned
- [ ] No requests for INSTANCE_ID/TEMPLATE_ID
- [ ] No offers to execute configuration
- [ ] Only text-based console guidance provided
- [ ] **NO `--profile` parameter in any CLI command**
- [ ] **NO `aliyun configure get` or `aliyun configure list` commands**
- [ ] **NO accessKeyId or accessKeySecret in output**
- [ ] **NO reading credential files** (`cat ~/.aliyun/config.json`, etc.)
- [ ] **NO aliyunlog configuration commands**
- [ ] **NO auto-installation of CLI tools**

**If ANY item is unchecked, REMOVE the violating content immediately.**
