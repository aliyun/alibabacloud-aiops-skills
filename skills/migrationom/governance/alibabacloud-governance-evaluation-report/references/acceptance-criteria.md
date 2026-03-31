# Acceptance Criteria: alicloud-it-gov-evaluation-report

**Scenario**: Alibaba Cloud Governance Center Maturity Evaluation Report
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Correct Product Pattern

#### ✅ CORRECT: governance product
```bash
aliyun governance list-evaluation-metadata
```

#### ❌ INCORRECT: Wrong product name
```bash
aliyun gov list-evaluation-metadata  # Wrong - 'gov' is not a valid product
aliyun cgc list-evaluation-metadata  # Wrong - 'cgc' is not a valid product
```

## 2. Correct Command Pattern

#### ✅ CORRECT: kebab-case subcommands
```bash
aliyun governance list-evaluation-metadata
aliyun governance list-evaluation-results
aliyun governance list-evaluation-metric-details
aliyun governance run-evaluation
```

#### ❌ INCORRECT: PascalCase or wrong command
```bash
aliyun governance ListEvaluationMetadata  # Wrong - should be kebab-case
aliyun governance get-evaluation-metadata  # Wrong - command is 'list-evaluation-metadata'
aliyun governance query-results  # Wrong - command is 'list-evaluation-results'
```

## 3. Correct Parameter Patterns

#### ✅ CORRECT: kebab-case parameters
```bash
aliyun governance list-evaluation-metadata --language zh
aliyun governance list-evaluation-results --account-id 123456789
aliyun governance list-evaluation-metric-details --id apbxftkv5c
```

#### ❌ INCORRECT: Wrong parameter names
```bash
aliyun governance list-evaluation-metadata --Language zh  # Wrong - should be --language
aliyun governance list-evaluation-results --accountId 123  # Wrong - should be --account-id
aliyun governance list-evaluation-metric-details --metric-id abc  # Wrong - should be --id
```

## 4. User-Agent Flag

#### ✅ CORRECT: Include user-agent
```bash
aliyun governance list-evaluation-results --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT: Missing user-agent
```bash
aliyun governance list-evaluation-results  # Missing --user-agent flag
```

## 5. Profile Parameter

#### ✅ CORRECT: Use --profile flag
```bash
aliyun governance list-evaluation-metadata --profile myprofile
```

#### ❌ INCORRECT: Wrong profile parameter
```bash
aliyun governance list-evaluation-metadata -p myprofile  # Wrong - should be --profile
```

# Correct Python Script Patterns

## 1. Script Invocation

#### ✅ CORRECT: Valid modes
```bash
python3 scripts/governance_query.py overview
python3 scripts/governance_query.py overview -r Error
python3 scripts/governance_query.py overview -r Error,Warning
python3 scripts/governance_query.py pillar -c Security --risky
python3 scripts/governance_query.py detail --id apbxftkv5c
python3 scripts/governance_query.py detail --keyword "MFA"
```

#### ❌ INCORRECT: Invalid modes or parameters
```bash
python3 scripts/governance_query.py summary  # Wrong - mode should be 'overview'
python3 scripts/governance_query.py pillar Security  # Wrong - need -c flag
python3 scripts/governance_query.py detail MFA  # Wrong - need --id or --keyword flag
```

## 2. Category Values

#### ✅ CORRECT: Valid category names
```bash
python3 scripts/governance_query.py pillar -c Security
python3 scripts/governance_query.py pillar -c Reliability
python3 scripts/governance_query.py pillar -c Performance
python3 scripts/governance_query.py pillar -c OperationalExcellence
python3 scripts/governance_query.py pillar -c CostOptimization
```

#### ❌ INCORRECT: Invalid category names
```bash
python3 scripts/governance_query.py pillar -c security  # Wrong - case sensitive
python3 scripts/governance_query.py pillar -c 安全  # Wrong - use English name
python3 scripts/governance_query.py pillar -c Cost  # Wrong - full name is CostOptimization
```

## 3. Filter Parameters

#### ✅ CORRECT: Valid filter values
```bash
python3 scripts/governance_query.py pillar -c Security -l Critical,High
python3 scripts/governance_query.py pillar -c Security -r Error,Warning
python3 scripts/governance_query.py pillar -c Security --risky
```

#### ❌ INCORRECT: Invalid filter values
```bash
python3 scripts/governance_query.py pillar -c Security -l critical  # Wrong - case sensitive
python3 scripts/governance_query.py pillar -c Security -r error  # Wrong - case sensitive
```

# Output Format Patterns

## 1. Overview Mode Output

Expected JSON structure:
```json
{
  "TotalScore": 0.85,
  "EvaluationTime": "2024-01-15T10:30:00Z",
  "TotalMetrics": 150,
  "PillarSummary": [...],
  "RiskDistribution": {...},
  "RiskyItems": [...]
}
```

## 2. Pillar Mode Output

Expected JSON structure:
```json
{
  "TotalScore": 0.85,
  "EvaluationTime": "2024-01-15T10:30:00Z",
  "Category": "Security",
  "CategoryCN": "安全",
  "MatchedCount": 10,
  "Items": [...]
}
```

## 3. Detail Mode Output

Expected JSON structure:
```json
{
  "Id": "apbxftkv5c",
  "DisplayName": "...",
  "Description": "...",
  "Category": "Security",
  "CategoryCN": "安全",
  "RecommendationLevel": "Critical",
  "Status": "Finished",
  "Risk": "Error",
  "Compliance": 0.5,
  "Remediation": [...]
}
```

## 4. Resources Mode Output

Expected JSON structure:
```json
{
  "MetricId": "apbxftkv5c",
  "TotalCount": 3,
  "Resources": [
    {
      "ResourceId": "user-001",
      "ResourceName": "test-user",
      "ResourceType": "ACS::RAM::User",
      "RegionId": "cn-hangzhou",
      "ResourceOwnerId": "123456789",
      "Classification": "NonCompliant",
      "Properties": {
        "MFAEnabled": "false"
      }
    }
  ]
}
```

## 5. Resources Mode Invocation

#### ✅ CORRECT: Valid resources query
```bash
python3 scripts/governance_query.py resources --id apbxftkv5c
python3 scripts/governance_query.py resources --id apbxftkv5c --max-results 100
```

#### ❌ INCORRECT: Missing required --id
```bash
python3 scripts/governance_query.py resources  # Wrong - --id is required
python3 scripts/governance_query.py resources --keyword "MFA"  # Wrong - resources mode only accepts --id
```
