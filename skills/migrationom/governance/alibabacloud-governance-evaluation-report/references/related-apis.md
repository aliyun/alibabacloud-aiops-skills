# Related APIs

## Governance Center CLI Commands

| Product | CLI Command | API Action | Description |
|---------|-------------|------------|-------------|
| governance | `aliyun governance list-evaluation-metadata` | ListEvaluationMetadata | Query all check items metadata including name, ID, description, stage, resource metadata, and remediation guide |
| governance | `aliyun governance list-evaluation-results` | ListEvaluationResults | Query governance check results and status |
| governance | `aliyun governance list-evaluation-metric-details` | ListEvaluationMetricDetails | Query non-compliant resource details for a specific check item |
| governance | `aliyun governance list-evaluation-score-history` | ListEvaluationScoreHistory | Query historical scores of governance maturity checks |
| governance | `aliyun governance run-evaluation` | RunEvaluation | Trigger a governance maturity check |
| governance | `aliyun governance generate-evaluation-report` | GenerateEvaluationReport | Generate governance evaluation report |

## Command Details

### list-evaluation-metadata

Query all check item metadata.

```bash
aliyun governance list-evaluation-metadata \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response fields:**
- `EvaluationMetadata[].Metadata[].Id` - Check item ID
- `EvaluationMetadata[].Metadata[].DisplayName` - Display name
- `EvaluationMetadata[].Metadata[].Description` - Description
- `EvaluationMetadata[].Metadata[].Category` - Category/Pillar (Security, Reliability, Performance, OperationalExcellence, CostOptimization)
- `EvaluationMetadata[].Metadata[].RecommendationLevel` - Recommendation level (Critical, High, Medium, Suggestion)
- `EvaluationMetadata[].Metadata[].RemediationMetadata` - Remediation guidance

### list-evaluation-results

Query governance check results.

```bash
aliyun governance list-evaluation-results \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response fields:**
- `Results.TotalScore` - Overall maturity score (0.0-1.0)
- `Results.EvaluationTime` - Evaluation timestamp
- `Results.MetricResults[].Id` - Check item ID
- `Results.MetricResults[].Status` - Status (Finished, NotApplicable, Failed)
- `Results.MetricResults[].Risk` - Risk level (Error, Warning, Suggestion, None)
- `Results.MetricResults[].Result` - Compliance rate (0.0-1.0)
- `Results.MetricResults[].ResourcesSummary.NonCompliant` - Non-compliant resource count

### list-evaluation-metric-details

Query non-compliant resources for a specific check item.

```bash
aliyun governance list-evaluation-metric-details \
  --id <metric-id> \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**
- `--id` (required) - Check item ID
- `--max-results` (optional) - Max results per page (default: 5)
- `--next-token` (optional) - Pagination token

**Response fields:**
- `Resources[].ResourceId` - Resource ID
- `Resources[].ResourceName` - Resource name
- `Resources[].ResourceType` - Resource type (e.g., `ACS::RAM::User`, `ACS::ECS::SecurityGroup`)
- `Resources[].RegionId` - Region ID
- `Resources[].ResourceOwnerId` - Owner account ID
- `Resources[].ResourceClassification` - Risk classification
- `Resources[].ResourceProperties[]` - Resource-specific attributes
- `NextToken` - Pagination token for next page

### run-evaluation

Trigger a new governance check.

```bash
aliyun governance run-evaluation \
  --user-agent AlibabaCloud-Agent-Skills
```

## References

- [Cloud Governance Center Documentation](https://help.aliyun.com/zh/governance/)
- [Governance API Reference](https://help.aliyun.com/zh/governance/developer-reference/api-governance-2021-01-20-overview)
