# Verification Methods

Success verification steps for AI Coaching Best Practice skill execution.

## Overview

This document provides step-by-step verification commands to confirm each stage of the AI Coaching system deployment was successful.

---

## Step 0: Verify NAT Gateway and SNAT Configuration

### Verification Command
```bash
# Check NAT Gateway exists
aliyun vpc describe-nat-gateways --profile adbpg \
  --biz-region-id cn-hangzhou --vpc-id vpc-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- `TotalCount` >= 1
- NAT Gateway `Status` is `Available`
- `NatType` is `Enhanced`
- `SnatTableIds` contains at least one entry
- Verify SNAT entry covers the VSwitch CIDR with a valid EIP

### Failure Indicators
- `TotalCount` is 0 — no NAT Gateway exists
- NAT Gateway `Status` is `Creating` or `Deleting`
- No SNAT entries configured — Supabase public access will fail
- EIP not bound to NAT Gateway

---

## Step 1: Verify Supabase Project Creation

### Verification Command
```bash
aliyun gpdb get-supabase-project --profile adbpg \
  --project-id sbp-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- `ProjectId` matches the created project (sbp-xxx format)
- `ProjectName` equals the specified name
- `Status` is `Running` or `Active`
- `PublicConnectUrl` is populated
- `ApiKeys` section contains `anon_key` and `service_role_key`

### Failure Indicators
- Error: `InvalidProjectId.NotFound`
- `Status` is `Creating` or `Failed`
- Missing connection URL or API keys

---

## Step 2: Verify ADBPG Instance Creation

### Verification Command
```bash
aliyun gpdb describe-db-instances --profile adbpg \
  --biz-region-id cn-hangzhou \
  --output cols="DBInstanceId,DBInstanceDescription,DBInstanceStatus,EngineVersion,VectorConfigurationStatus" rows="Items.DBInstance[]" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- Instance appears in the list with correct `DBInstanceId` (gp-xxx format)
- `DBInstanceStatus` is `Running`
- `EngineVersion` is `7.0`
- `VectorConfigurationStatus` is `enabled`
- `DBInstanceCategory` is `HighAvailability`

### Failure Indicators
- Instance not found in list
- `DBInstanceStatus` is `Creating`, `Modifying`, or `Failed`
- `VectorConfigurationStatus` is `disabled` or `null`

---

## Step 3: Verify Database Account

### Verification Command
```bash
aliyun gpdb describe-accounts --profile adbpg \
  --db-instance-id gp-xxxxx \
  --output cols="AccountName,AccountType,AccountStatus" rows="Accounts.DBInstanceAccount[]" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- Super account exists with specified name
- `AccountType` is `Super`
- `AccountStatus` is `Active`

### Failure Indicators
- No accounts listed
- Only `Normal` accounts exist
- Account status is `Locked` or `Creating`

---

## Step 4: Verify Vector Database Initialization

### Verification Command
```bash
aliyun gpdb describe-namespaces --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<ManagerAccountPassword>' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- Vector database is initialized
- No error about uninitialized vector DB

### Failure Indicators
- Error: `VectorDatabase.NotInitialized`
- Error: `ManagerAccount.PasswordMismatch`

---

## Step 5: Verify Namespace Creation

### Verification Command
```bash
aliyun gpdb describe-namespaces --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<ManagerAccountPassword>' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- Command succeeds without error
- Can create collection in the namespace

### Failure Indicators
- Error: `Namespace.NotExist`
- Error: `Namespace.AlreadyExists`
- Error: `ManagerAccount.PasswordMismatch`

---

## Step 6: Verify Document Collection Creation

### Verification Command
```bash
# Query collections (if available via API)
# Or verify by listing documents in collection
```

### Expected Success Indicators
- Collection exists with specified name
- Embedding model matches specification
- Dimension matches specification

### Failure Indicators
- Error: `Collection.NotExist`
- Embedding model mismatch

---

## Step 7: Verify Document Upload

### Verification Command
```bash
aliyun gpdb upload-document-async --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_coaching \
  --namespace-password '<NamespacePassword>' \
  --collection coaching_knowledge \
  --file-name "test_verify.pdf" \
  --file-url "https://example.com/test.pdf" \
  --document-loader-name ADBPGLoader \
  --chunk-size 500 \
  --chunk-overlap 50 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- Returns `TaskId` for async operation
- Document status becomes `Processed` after completion

### Check Upload Status
```bash
# Query document upload task status (if API available)
```

### Failure Indicators
- Error: `Collection.NotExist`
- Error: `InvalidFileUrl`
- Error: `UnsupportedFileType`
- Task status remains `Processing` indefinitely

---

## Step 8: Verify Knowledge Base Chat (AI Coaching)

### Verification Command
```bash
aliyun gpdb chat-with-knowledge-base --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --model-params '{
    "Model": "qwen-max",
    "Messages": [
      {"Role": "user", "Content": "Hello, I need coaching on my sales process."}
    ]
  }' \
  --knowledge-params '{
    "SourceCollection": [{
      "Collection": "coaching_knowledge",
      "Namespace": "ns_coaching",
      "NamespacePassword": "<NamespacePassword>",
      "QueryParams": {"TopK": 5}
    }]
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Expected Success Indicators
- Response contains meaningful coaching guidance
- Response includes retrieved knowledge context
- No authentication or permission errors

### Failure Indicators
- Error: `AccountOrPassword.VerificationError`
- Error: `Collection.NotExist`
- Error: `Namespace.NotExist`
- Empty or nonsensical response
- Model inference timeout

---

## Step 9: Verify Supabase Database Schema

### Verification Command
Connect to Supabase database using psql:

```bash
psql "postgres://<user>:<password>@<host>:<port>/postgres" -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE';
"
```

### Expected Success Indicators
Tables exist:
- `coaching_domains`
- `coaching_personas`
- `learners`
- `coaching_sessions`

### Verify Preset Coaching Domains
```sql
SELECT id, name, category, difficulty, is_active
FROM coaching_domains
ORDER BY category, difficulty;
```

Expected domains:
- `sales_workflow_coach` (workflow_coaching, intermediate)
- `architecture_advisor` (decision_support, advanced)
- `communication_coach` (skill_development, intermediate)
- `onboarding_mentor` (onboarding, beginner)

### Verify Coaching Personas
```sql
SELECT domain_id, LEFT(system_prompt, 50) as prompt_preview
FROM coaching_personas;
```

### Failure Indicators
- Tables don't exist
- Missing expected coaching domains
- Empty coaching_personas table

---

## Step 10: End-to-End Coaching Test

### Full Flow Test

1. **Query a coaching domain from Supabase:**
```sql
SELECT d.id, d.name, p.system_prompt
FROM coaching_domains d
LEFT JOIN coaching_personas p ON d.id = p.domain_id
WHERE d.id = 'sales_workflow_coach';
```

2. **Call ChatWithKnowledgeBase with coaching prompt:**
```bash
aliyun gpdb chat-with-knowledge-base --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --model-params '{
    "Model": "qwen-max",
    "Messages": [
      {"Role": "system", "Content": "<system_prompt from query>"},
      {"Role": "user", "Content": "I have a prospect who keeps delaying the decision. How should I handle this?"}
    ]
  }' \
  --knowledge-params '{
    "SourceCollection": [{
      "Collection": "coaching_knowledge",
      "Namespace": "ns_coaching",
      "NamespacePassword": "<NamespacePassword>",
      "QueryParams": {"TopK": 5}
    }]
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

3. **Verify response quality:**
- Response matches the coaching persona style
- Response incorporates knowledge from uploaded documents
- Response provides actionable coaching guidance
- Response uses Socratic questioning or appropriate coaching technique

### Failure Indicators
- Coaching domain not found in database
- Chat API returns errors
- Response doesn't match expected coaching style
- No knowledge retrieval in response

---

## Quick Health Check Script

Run this script to verify all components:

```bash
#!/bin/bash

# Configuration
PROFILE="adbpg"
REGION="cn-hangzhou"
DB_INSTANCE="gp-xxxxx"
MANAGER_ACCOUNT="admin_user"
MANAGER_PASSWORD="<ManagerAccountPassword>"   # Replace with actual password
NAMESPACE="ns_coaching"
NAMESPACE_PASSWORD="<NamespacePassword>"       # Replace with actual password
COLLECTION="coaching_knowledge"

echo "=== AI Coaching System Health Check ==="
echo ""

# 1. Check CLI version
echo "1. Checking Aliyun CLI version..."
aliyun version

# 2. Check credentials
echo ""
echo "2. Checking credentials..."
aliyun configure list

# 3. Check ADBPG instance
echo ""
echo "3. Checking ADBPG instance status..."
aliyun gpdb describe-db-instances --profile $PROFILE \
  --biz-region-id $REGION \
  --output cols="DBInstanceId,DBInstanceStatus,VectorConfigurationStatus" rows="Items.DBInstance[]" \
  --user-agent AlibabaCloud-Agent-Skills

# 4. Check accounts
echo ""
echo "4. Checking database accounts..."
aliyun gpdb describe-accounts --profile $PROFILE \
  --db-instance-id $DB_INSTANCE \
  --output cols="AccountName,AccountType,AccountStatus" rows="Accounts.DBInstanceAccount[]" \
  --user-agent AlibabaCloud-Agent-Skills

# 5. Test ChatWithKnowledgeBase
echo ""
echo "5. Testing ChatWithKnowledgeBase..."
aliyun gpdb chat-with-knowledge-base --profile $PROFILE \
  --biz-region-id $REGION \
  --db-instance-id $DB_INSTANCE \
  --model-params '{"Model": "qwen-max", "Messages": [{"Role": "user", "Content": "Hello"}]}' \
  --knowledge-params "{\"SourceCollection\": [{\"Collection\": \"$COLLECTION\", \"Namespace\": \"$NAMESPACE\", \"NamespacePassword\": \"$NAMESPACE_PASSWORD\", \"QueryParams\": {\"TopK\": 5}}]}" \
  --user-agent AlibabaCloud-Agent-Skills

echo ""
echo "=== Health Check Complete ==="
```

---

## Troubleshooting Common Issues

### Issue: `InvalidAccessKeyId.NotFound`
**Solution:** Re-verify credentials with `aliyun configure list`

### Issue: `Forbidden.RAM`
**Solution:** Check RAM policies - ensure user has required GPDB permissions

### Issue: `AccountOrPassword.VerificationError`
**Solution:** Verify manager account password is correct

### Issue: `Namespace.NotExist`
**Solution:** Create namespace first with `CreateNamespace`

### Issue: `VectorDatabase.NotInitialized`
**Solution:** Run `InitVectorDatabase` first

### Issue: Response quality is poor
**Solution:**
1. Verify documents were uploaded successfully
2. Increase `TopK` value (try 10)
3. Check document content quality
4. Verify embedding model compatibility
