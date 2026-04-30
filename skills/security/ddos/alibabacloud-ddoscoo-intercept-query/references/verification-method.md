# Success Verification Method

## Scenario Goal Verification

**Expected Outcome**: Given a Request ID from a DDoS Pro block/intercept event, the skill produces a complete analysis report identifying the blocking rule, its configuration, and actionable recommendations.

## Verification Steps

### 1. Instance Discovery Verification

**Command**:
```bash
aliyun ddoscoo describe-instances --page-number 1 --page-size 50 --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**Success Indicator**: Response contains `Instances` array with at least one valid DDoS Pro instance.

### 2. SLS and Log Store Status Verification

**Command**:
```bash
aliyun ddoscoo describe-sls-open-status --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
aliyun ddoscoo describe-log-store-exist-status --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**Success Indicator**: SLS is opened and log store exists.

### 3. SLS Logstore Info Verification

**Command**:
```bash
aliyun ddoscoo describe-sls-logstore-info --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**Success Indicator**: Response contains valid `LogStore`, `ProjectName` (or equivalent fields) with storage capacity and TTL info.

### 4. Domain Full Log Status Verification

**Command**:
```bash
aliyun ddoscoo describe-web-access-log-status --domain '<domain>' --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**Success Indicator**: Full log is enabled for the target domain.

### 5. Log Query Verification

**Command**:
```bash
python3 scripts/get_ddos_logs.py \
  --project <project-name> \
  --logstore <logstore-name> \
  --request-id <known-request-id> \
  --region <sls-region>
```

**Success Indicator**: Returns at least one log record containing `request_traceid`, block-related fields (`cc_action`, `final_action`, `final_plugin`, `final_rule_id`).

### 6. Rule Detail Verification

**CC Rules**:
```bash
aliyun ddoscoo describe-web-cc-rules-v2 --domain '<domain>' --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**Precise Access Control**:
```bash
aliyun ddoscoo describe-web-precise-access-rule --domains.1 '<domain>' --region cn-hangzhou --header User-Agent=AlibabaCloud-Agent-Skills/alibabacloud-ddoscoo-intercept-query
```

**Success Indicator**: Response contains rule details (Name, Action/Act, Conditions).

### 7. End-to-End Verification

**Process**: Run the complete workflow with a known Request ID.

**Success Indicator**: Output report contains all required fields:
- Request ID, Block Time, Client IP (masked)
- Rule ID / Rule Type, Block Action
- Recommendations based on block type
