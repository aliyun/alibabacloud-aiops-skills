# Verification Methods

## Step 1: Verify CLI Installation

```bash
aliyun version
# Expected: version >= 3.3.0
```

## Step 2: Verify Governance Plugin

```bash
aliyun governance --help
# Expected: Shows available governance commands
```

If plugin not installed:
```bash
aliyun plugin install --names governance
```

## Step 3: Verify Authentication

```bash
aliyun governance list-evaluation-results \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "Results.TotalScore"
```

**Success indicators:**
- Returns a numeric value (0.0-1.0)
- No error messages

**Common errors:**
- `InvalidAccessKeyId.NotFound` - Wrong Access Key ID
- `SignatureDoesNotMatch` - Wrong Access Key Secret
- `Forbidden.RAM` - Insufficient permissions (see [ram-policies.md](ram-policies.md))

## Step 4: Verify Metadata Query

```bash
aliyun governance list-evaluation-metadata \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "EvaluationMetadata | length(@)"
```

**Success indicators:**
- Returns a number > 0 (typically 5, one per pillar)

## Step 5: Verify Python Script

```bash
cd /path/to/alicloud-it-gov-evaluation-report
python3 scripts/governance_query.py overview
```

**Success indicators:**
- Returns JSON with `TotalScore`, `PillarSummary`, `RiskDistribution`
- No Python errors

## Step 6: Verify Specific Query Modes

### Overview Mode
```bash
python3 scripts/governance_query.py overview
```
Expected: JSON with overall maturity score and pillar summaries

### Pillar Mode
```bash
python3 scripts/governance_query.py pillar -c Security --risky
```
Expected: JSON with security-related risky items

### Detail Mode
```bash
python3 scripts/governance_query.py detail --keyword "MFA"
```
Expected: JSON with detailed check item information

## Troubleshooting

### Cache Issues
Force refresh cache:
```bash
python3 scripts/governance_query.py overview --refresh
```

### Profile Issues
Specify profile explicitly:
```bash
python3 scripts/governance_query.py overview --profile <your-profile>
```

### Permission Denied
Verify RAM policy is attached:
1. Go to RAM Console
2. Check user/role policies
3. Attach `AliyunGovernanceReadOnlyAccess` or custom policy
