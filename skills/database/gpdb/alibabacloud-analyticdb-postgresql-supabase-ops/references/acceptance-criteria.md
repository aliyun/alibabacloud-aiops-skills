# Acceptance Criteria: ADBPG Supabase Management

**Scenario**: ADBPG Supabase Project Management
**Purpose**: Skill testing acceptance criteria

## Table of Contents

- [Correct CLI Command Patterns](#correct-cli-command-patterns)
  - [1. Product](#1-product--verify-product-name-exists)
  - [2. Command](#2-command--verify-action-exists-under-the-product)
  - [3. Parameters](#3-parameters--verify-each-parameter-name-exists)
  - [4. User-Agent](#4-user-agent--every-command-must-include)
  - [5. Complete Command Examples](#5-complete-command-examples)
- [Security Patterns](#security-patterns)
  - [1. Credential Handling](#1-credential-handling)
  - [2. Password Requirements](#2-password-requirements)
  - [3. Security IP List](#3-security-ip-list)
- [User confirmation](#user-confirmation)

---

## User confirmation

Per the main skill ([SKILL.md](../SKILL.md)):

- **No final “execute” confirmation** for read-only **list / get / describe** (e.g. `list-supabase-projects`, `get-supabase-project*`, `vpc describe-vpcs`, `vpc describe-vswitches`, `gpdb describe-regions`).
- **Explicit final user confirmation** before CLI for **create**, **pause**, **resume**, **reset-supabase-project-password**, **modify-supabase-project-security-ips**.

---

# Correct CLI Command Patterns

## 1. Product — verify product name exists

#### ✅ CORRECT
```bash
aliyun gpdb ...
```

#### ❌ INCORRECT
```bash
aliyun GPDB ...        # Error: product name must be lowercase
aliyun adbpg ...       # Error: product name is gpdb, not adbpg
```

## 2. Command — verify action exists under the product

#### ✅ CORRECT (Plugin Mode - lowercase with hyphens)
```bash
aliyun gpdb list-supabase-projects
aliyun gpdb get-supabase-project
aliyun gpdb create-supabase-project
aliyun gpdb pause-supabase-project
aliyun gpdb resume-supabase-project
aliyun gpdb reset-supabase-project-password
aliyun gpdb modify-supabase-project-security-ips
aliyun gpdb get-supabase-project-api-keys
aliyun gpdb get-supabase-project-dashboard-account
```

#### ❌ INCORRECT (Traditional API Mode)
```bash
aliyun gpdb ListSupabaseProjects       # Error: use list-supabase-projects
aliyun gpdb GetSupabaseProject         # Error: use get-supabase-project
aliyun gpdb CreateSupabaseProject      # Error: use create-supabase-project
```

## 3. Parameters — verify each parameter name exists

#### ✅ CORRECT (Plugin Mode - lowercase with hyphens)
```bash
--project-id spb-xxxxx
--biz-region-id cn-beijing
--project-name my_project
--zone-id cn-beijing-i
--account-password 'MyPass123!'
--security-ip-list "127.0.0.1"
--vpc-id vpc-xxxxx
--vswitch-id vsw-xxxxx
--project-spec 2C2G
--max-results 20
--user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT (Traditional API Mode)
```bash
--ProjectId spb-xxxxx        # Error: use --project-id
--RegionId cn-beijing       # Error: use --biz-region-id or --region
--ProjectName my_project     # Error: use --project-name
--ZoneId cn-beijing-i       # Error: use --zone-id
--AccountPassword 'xxx'      # Error: use --account-password
--SecurityIPList "xxx"       # Error: use --security-ip-list
--VpcId vpc-xxxxx            # Error: use --vpc-id
--VSwitchId vsw-xxxxx        # Error: use --vswitch-id
--MaxResults 20              # Error: use --max-results
```

## 4. User-Agent — every command must include

#### ✅ CORRECT
```bash
aliyun gpdb list-supabase-projects --user-agent AlibabaCloud-Agent-Skills
aliyun gpdb get-supabase-project --project-id spb-xxx --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun gpdb list-supabase-projects                    # Missing --user-agent
aliyun gpdb get-supabase-project --project-id spb-xxx # Missing --user-agent
```

## 5. Complete Command Examples

### List Projects
#### ✅ CORRECT
```bash
aliyun gpdb list-supabase-projects \
  --biz-region-id cn-beijing \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Get Project Details
#### ✅ CORRECT
```bash
aliyun gpdb get-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create Project
#### ✅ CORRECT
```bash
aliyun gpdb create-supabase-project \
  --biz-region-id cn-beijing \
  --zone-id cn-beijing-i \
  --project-name my_supabase \
  --account-password 'MyPass123!' \
  --security-ip-list "127.0.0.1" \
  --vpc-id vpc-xxxxx \
  --vswitch-id vsw-xxxxx \
  --project-spec 2C2G \
  --storage-size 20 \
  --disk-performance-level PL0 \
  --pay-type POSTPAY \
  --user-agent AlibabaCloud-Agent-Skills
```

### Pause Project
#### ✅ CORRECT
```bash
aliyun gpdb pause-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

### Resume Project
#### ✅ CORRECT
```bash
aliyun gpdb resume-supabase-project \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

### Reset Password
#### ✅ CORRECT
```bash
aliyun gpdb reset-supabase-project-password \
  --project-id spb-xxxxx \
  --account-password 'NewPass456!' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Modify Security IPs
#### ✅ CORRECT
```bash
aliyun gpdb modify-supabase-project-security-ips \
  --project-id spb-xxxxx \
  --security-ip-list "10.0.0.1,10.0.0.2/24" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Get API Keys
#### ✅ CORRECT
```bash
aliyun gpdb get-supabase-project-api-keys \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

### Get Dashboard Account
#### ✅ CORRECT
```bash
aliyun gpdb get-supabase-project-dashboard-account \
  --project-id spb-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

---

# Security Patterns

## 1. Credential Handling

#### ✅ CORRECT
```bash
# Only check credential status, do not output sensitive information
aliyun configure list
```

#### ❌ INCORRECT
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID           # FORBIDDEN: do not output AK
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET       # FORBIDDEN: do not output SK
aliyun configure set --access-key-id xxx    # FORBIDDEN: do not set credentials directly in session
```

## 2. Password Requirements

#### ✅ CORRECT
```
MyPass123!     # Uppercase + lowercase + numbers + special chars
Abc@12345      # At least 3 character types
Test_Pass1!    # 8-32 characters length
```

#### ❌ INCORRECT
```
password       # Only lowercase letters
12345678       # Only numbers
abc123         # Missing special chars or uppercase
Pass1!         # Less than 8 characters
```

## 3. Security IP List

#### ✅ CORRECT
```
127.0.0.1                    # No external access allowed
10.0.0.1                     # Single IP
10.0.0.1,10.0.0.2           # Multiple IPs
10.0.0.0/24                  # CIDR format
10.0.0.1,192.168.1.0/24     # Mixed format
```

#### ❌ INCORRECT (Security Risk)
```
0.0.0.0/0                    # Allows all IPs, serious security risk
```
