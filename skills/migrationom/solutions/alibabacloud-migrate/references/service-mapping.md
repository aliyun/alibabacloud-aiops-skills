# AWS to Alibaba Cloud Service Mapping

Comprehensive service mapping for AWS to Alibaba Cloud migration with migration complexity, recommended tools, and verified source citations.

## Mapping Methodology

This document provides AWS to Alibaba Cloud service mappings with source citations and confidence levels to ensure traceability and reliability.

### Sourcing Standard

Each mapping is verified against official Alibaba Cloud documentation and cross-referenced with multiple sources where available:

- **[Official]**: Alibaba Cloud Product Mapping Page (primary source)
- **[Terraform]**: Terraform alicloud Provider Registry
- **[CMH]**: Cloud Migration Hub - AWS Migration Guide
- **[Blog]**: Alibaba Cloud Product Comparison for AWS Professionals
- **[Doc:{service}]**: Service-specific documentation

### Confidence Scoring

- **High**: Confirmed by 2+ sources (Official + Terraform/CMH/Doc)
- **Medium**: Confirmed by 1 official source only, or community consensus
- **Low**: Inferred mapping, no direct official confirmation, or service significantly differs

### Last Verified

All mappings were last verified: **2026-03**

---

## Compute

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| EC2 | ECS (Elastic Compute Service) | SMC (Server Migration Center) | Medium | [Official], [CMH], [Terraform] | High | Use SMC for lift-and-shift; supports incremental migration |
| Lambda | Function Compute | Manual refactor + FC CLI | High | [Official], [Doc:fc] | High | Event sources and triggers need reconfiguration |
| ECS (Container Service) | ACK (Container Service for Kubernetes) | Velero + ACK One | Medium | [Official], [Terraform] | High | Kubernetes manifests mostly compatible |
| Fargate | ECI (Elastic Container Instance) | Terraform/ROS | Medium | [Official], [Terraform] | High | Serverless containers, pay-per-use |
| Elastic Beanstalk | SAE (Serverless App Engine) | Manual migration | High | [Official], [Blog] | High | Application code compatible, platform config differs |
| Lightsail | Simple Application Server | SMC | Low | [Official], [CMH] | High | Pre-configured VPS equivalent |
| Batch | Batch Compute | Manual refactor | High | [Official], [Doc:batchcompute] | High | Job definitions need rewriting |

## Storage

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| S3 | OSS (Object Storage Service) | ossutil, ossimport, Data Online Migration | Low | [Official], [CMH], [Terraform] | High | API compatible with some differences |
| EBS | Cloud Disk (System/Data Disk) | SMC, Snapshot | Low | [Official], [CMH] | High | Automatically migrated with ECS |
| EFS | NAS (Network Attached Storage) | rsync, rclone | Medium | [Official], [Terraform] | High | NFS protocol compatible |
| Glacier | OSS Archive/Cold Archive | ossutil lifecycle rules | Low | [Official], [Blog] | High | Configure lifecycle policies for auto-tiering |
| S3 Glacier Deep Archive | OSS Cold Archive | ossutil lifecycle rules | Low | [Official], [Blog] | High | Lowest cost, longest retrieval time |
| FSx | NAS/CPFS | Manual migration | High | [Official], [Doc:cpfs] | Medium | Choose based on workload type |
| Storage Gateway | Hybrid Cloud Storage Array | HCSA appliance | Medium | [Official], [Doc:hcsa] | Medium | Hybrid cloud file/nfs/iscsi gateway |

## Database

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| RDS MySQL | ApsaraDB RDS MySQL | DTS (Data Transmission Service) | Low | [Official], [CMH], [Terraform] | High | Native MySQL compatibility |
| RDS PostgreSQL | ApsaraDB RDS PostgreSQL | DTS | Low | [Official], [CMH], [Terraform] | High | Native PostgreSQL compatibility |
| RDS SQL Server | ApsaraDB RDS SQL Server | DTS | Low | [Official], [CMH], [Terraform] | High | Native SQL Server compatibility |
| RDS Oracle | ApsaraDB RDS Oracle | DTS | Medium | [Official], [CMH] | High | License management differs |
| Aurora MySQL | PolarDB MySQL | DTS | Medium | [Official], [Blog], [Doc:polar-db] | High | PolarDB offers better performance |
| Aurora PostgreSQL | PolarDB PostgreSQL | DTS | Medium | [Official], [Blog], [Doc:polar-db] | High | PolarDB compatible with Aurora features |
| DynamoDB | Tablestore | DTS, DataX | High | [Official], [Blog] | High | NoSQL but different API/SDK |
| ElastiCache Redis | Tair/Redis | DTS | Low | [Official], [CMH], [Terraform] | High | Redis protocol compatible |
| ElastiCache Memcached | ApsaraDB for Memcache | DTS | Low | [Official], [Terraform] | High | Memcached protocol compatible |
| DocumentDB | ApsaraDB for MongoDB | DTS | Medium | [Official], [Blog] | High | MongoDB compatible |
| Neptune | Graph Database (GDB) | Manual export/import | High | [Official], [Doc:gdb] | High | Different graph query languages |
| Redshift | MaxCompute, AnalyticDB | DTS, DataX | High | [Official], [Blog] | High | Data warehouse, different SQL dialect |
| Keyspaces | Lindorm | Manual migration | High | [Official], [Doc:lindorm] | Medium | Wide-column store, Cassandra compatible |

## Networking

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| VPC | VPC (Virtual Private Cloud) | Terraform, ROS, Console | Low | [Official], [CMH], [Terraform] | High | Similar concepts and architecture |
| Route 53 | Alibaba Cloud DNS | DNS import/export | Medium | [Official], [Terraform] | High | Zone file compatible, API differs |
| CloudFront | CDN (Content Delivery Network) | Console migration wizard | Medium | [Official], [CMH], [Terraform] | High | Certificate and origin config differs |
| Direct Connect | Express Connect | Physical circuit setup | High | [Official], [CMH], [Terraform] | High | Requires physical connection setup |
| ELB (Classic) | SLB (Server Load Balancer) | Manual config | Low | [Official], [Terraform] | High | Similar load balancing concepts |
| ALB (Application) | ALB (Application Load Balancer) | Manual config | Low | [Official], [Terraform] | High | Layer 7 load balancing |
| NLB (Network) | NLB (Network Load Balancer) | Manual config | Low | [Official], [Terraform] | High | Layer 4 load balancing |
| API Gateway | API Gateway | OpenAPI import/export | Medium | [Official], [Terraform] | High | OpenAPI 3.0 compatible |
| Cloud Map | PrivateZone | Manual config | Medium | [Official], [Doc:privatezone] | Medium | Service discovery |
| Transit Gateway | CEN (Cloud Enterprise Network) | Console/Terraform | Medium | [Official], [Terraform] | High | Multi-VPC and cross-region connectivity |
| VPC Peering | VPC Peering | Console/Terraform | Low | [Official], [Terraform] | High | Similar peering concepts |
| NAT Gateway | NAT Gateway | Console/Terraform | Low | [Official], [Terraform] | High | Similar NAT functionality |
| VPN Gateway | VPN Gateway | Console/Terraform | Low | [Official], [Terraform] | High | IPsec VPN compatible |

## Security & Identity

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| IAM | RAM (Resource Access Management) | Manual policy rewrite | Medium | [Official], [CMH], [Terraform] | High | Different policy syntax |
| IAM Identity Center | SSO (Single Sign-On) | Manual config | Medium | [Official], [Doc:sso] | High | SAML/OIDC compatible |
| KMS | KMS (Key Management Service) | Manual key import | Medium | [Official], [Terraform] | High | CMK concepts similar |
| Secrets Manager | Secrets Manager | Manual migration | Low | [Official], [Terraform] | High | Similar secret rotation |
| Parameter Store | ACM (Application Configuration Management) | Manual migration | Low | [Official], [Doc:acm] | Medium | Configuration management |
| WAF | WAF (Web Application Firewall) | Rule migration wizard | Medium | [Official], [Terraform] | High | OWASP rules compatible |
| Shield | Anti-DDoS Pro/Premium | Automatic | Low | [Official], [Blog] | High | DDoS protection built-in |
| ACM (Certificates) | SSL Certificates Service | Certificate import | Low | [Official], [Terraform] | High | Same certificate formats |
| Cognito | IDaaS (Identity as a Service) | Manual migration | High | [Official], [Blog] | High | User pool migration complex |
| GuardDuty | Security Center | Automatic enablement | Low | [Official], [CMH] | High | Threat detection |
| Inspector | Security Center | Automatic enablement | Low | [Official], [Blog] | Medium | Vulnerability scanning |
| Macie | Data Security Center | Manual config | Medium | [Official], [Doc:data-security] | Medium | Data classification and protection |
| CloudHSM | CloudHSM | Manual key migration | High | [Official], [Doc:cloudhsm] | High | Hardware security module |

## Monitoring & Management

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| CloudWatch | CloudMonitor | Metric migration scripts | Medium | [Official], [CMH], [Terraform] | High | Custom metrics need remapping |
| CloudWatch Logs | SLS (Simple Log Service) | Logstash, Fluent Bit | Medium | [Official], [Terraform] | High | Log collection agents differ |
| CloudTrail | ActionTrail | Console enablement | Low | [Official], [CMH], [Terraform] | High | API call logging |
| Config | Cloud Config | Manual rule migration | Medium | [Official], [Terraform] | High | Compliance rules differ |
| Systems Manager | OOS (Operation Orchestration Service) | Manual template rewrite | Medium | [Official], [Terraform] | High | Automation documents differ |
| OpsWorks | OOS | Manual migration | High | [Official], [Blog] | Medium | Chef/Puppet recipes need adaptation |
| Service Catalog | Resource Orchestration Service (ROS) | Template conversion | Medium | [Official], [Terraform] | High | CloudFormation-like |
| Trusted Advisor | Advisor | Automatic | Low | [Official], [Blog] | High | Best practice recommendations |
| X-Ray | ARMS (Application Real-Time Monitoring) | SDK changes | High | [Official], [Doc:arms] | High | Different tracing SDK |
| CloudWatch Events | EventBridge | Rule migration | Medium | [Official], [Terraform] | High | Event patterns compatible |

## Messaging & Integration

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| SQS | MNS (Message Notification Service) Queue | Manual code changes | Medium | [Official], [Terraform] | High | Different SDK, similar concepts |
| SNS | MNS Topic / EventBridge | Manual code changes | Medium | [Official], [Terraform] | High | Pub/sub compatible |
| EventBridge | EventBridge | Rule migration | Low | [Official], [Terraform] | High | Event patterns similar |
| Step Functions | Serverless Workflow | Flow definition rewrite | High | [Official], [Doc:serverless-workflow] | High | Different state language |
| Kinesis Data Streams | DataHub | DataX, Flink | High | [Official], [Blog] | High | Streaming platform differs |
| Kinesis Firehose | DataHub + DataWorks | Manual pipeline setup | High | [Official], [Doc:dataworks] | Medium | Data delivery service |
| Kinesis Analytics | Realtime Compute (Flink) | SQL/job migration | High | [Official], [Blog] | High | Stream processing |
| MQ (ActiveMQ) | MQ for Apache ActiveMQ | Broker migration | Low | [Official], [Terraform] | High | ActiveMQ compatible |
| MQ (RabbitMQ) | MQ for RabbitMQ | Broker migration | Low | [Official], [Terraform] | High | RabbitMQ compatible |
| AppSync | GraphQL Service | Schema migration | Medium | [Official], [Doc:graphql] | Medium | GraphQL compatible |
| Pinpoint | Mobile Analytics | SDK changes | High | [Official], [Blog] | Medium | Mobile engagement platform |

## Big Data & AI

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| EMR | E-MapReduce | Cluster migration | Medium | [Official], [CMH], [Terraform] | High | Hadoop/Spark compatible |
| Athena | Data Lake Analytics (DLA) | SQL migration | Medium | [Official], [Blog] | High | Serverless query service |
| Glue | DataWorks Data Integration | Job migration | High | [Official], [Terraform] | High | ETL service |
| Lake Formation | DataWorks Data Governance | Manual setup | High | [Official], [Doc:dataworks] | Medium | Data lake management |
| SageMaker | PAI (Platform of Artificial Intelligence) | Model migration | High | [Official], [Blog], [Doc:pai] | High | ML platform |
| Comprehend | NLP (Natural Language Processing) | API changes | High | [Official], [Doc:nlp] | High | NLP service |
| Rekognition | Image Search / VisionAI | API changes | High | [Official], [Blog] | High | Image/video analysis |
| Polly | Intelligent Speech Interaction | API changes | High | [Official], [Doc:speech] | High | Text-to-speech |
| Transcribe | Intelligent Speech Interaction | API changes | High | [Official], [Doc:speech] | High | Speech-to-text |
| Translate | Machine Translation | API changes | High | [Official], [Doc:translation] | High | Language translation |
| Lex | Intelligent Conversation | Bot migration | High | [Official], [Doc:conversation] | High | Chatbot service |
| Forecast | Time Series Forecasting | Model migration | High | [Official], [Doc:forecast] | Medium | Forecasting service |
| Personalize | Recommendation Engine | Model migration | High | [Official], [Doc:recommendation] | Medium | Recommendation service |
| Kendra | Open Search (with AI) | Index migration | High | [Official], [Doc:opensearch] | Medium | Enterprise search |

## Container & Serverless

| AWS Service | Alibaba Cloud Equivalent | Migration Tool | Complexity | Source | Confidence | Notes |
|-------------|-------------------------|----------------|------------|--------|------------|-------|
| EKS | ACK (Container Service for Kubernetes) | ACK One, Velero | Low | [Official], [CMH], [Terraform] | High | Kubernetes compatible |
| ECR | ACR (Container Registry) | cr-cli, docker push/pull | Low | [Official], [Terraform] | High | Docker registry compatible |
| ECS (Container) | ACK / ECI | Terraform, ROS | Low | [Official], [Terraform] | High | Container orchestration |
| Fargate | ECI (Elastic Container Instance) | Terraform, ROS | Medium | [Official], [Terraform] | High | Serverless containers |
| App Runner | SAE (Serverless App Engine) | Manual deployment | Medium | [Official], [Blog] | High | Serverless app platform |
| Copilot | ACK + DevOps | Manual setup | High | [Blog] | Medium | Container development tool |
| Proton | ROS + OOS | Manual setup | High | [Official], [Terraform] | Medium | Infrastructure templating |

---

## Migration Tools Comparison

| Migration Type | AWS Native | Alibaba Cloud Equivalent | Best For |
|----------------|------------|-------------------------|----------|
| Server Migration | SMS (Server Migration Service) | SMC (Server Migration Center) | EC2 → ECS lift-and-shift |
| Database Migration | DMS (Database Migration Service) | DTS (Data Transmission Service) | RDS → ApsaraDB migration |
| Data Transfer | Snowball | Lightning Cube | Large offline data transfer |
| Online Data Transfer | DataSync | Data Online Migration | S3 → OSS, NAS → NAS |
| Application Discovery | Application Discovery Service | Application Discovery Service | Migration planning |
| Migration Hub | Migration Hub | Migration Center | Migration tracking |

## Migration Complexity Legend

- **Low**: Direct replacement, minimal code changes, automated tools available
- **Medium**: Some refactoring needed, different APIs/SDKs, manual configuration
- **High**: Significant refactoring, architectural changes, custom development required

## Best Practices

1. **Start with assessment**: Use Alibaba Cloud Migration Center for discovery and planning
2. **Prioritize low-complexity services**: Begin with storage and networking
3. **Use managed services**: Leverage DTS for databases, SMC for servers
4. **Test incrementally**: Run migration drills before production cutover
5. **Plan for rollback**: Maintain AWS resources until migration is validated
6. **Update monitoring**: Migrate CloudWatch dashboards and alarms early
7. **Train teams**: Ensure operations team knows Alibaba Cloud console and tools
8. **Optimize post-migration**: Right-size resources after initial migration

---

## Sources

| Key | Source | URL | Last Accessed |
|-----|--------|-----|---------------|
| [Official] | Alibaba Cloud Product Mapping Page | https://www.alibabacloud.com/en/product/product-mapping | 2026-03 |
| [Terraform] | Terraform alicloud Provider Registry | https://registry.terraform.io/providers/aliyun/alicloud/latest/docs | 2026-03 |
| [CMH] | Cloud Migration Hub - AWS Migration Guide | https://www.alibabacloud.com/help/en/cmh/getting-started/migrate-resources-from-aws-to-alibaba-cloud | 2026-03 |
| [Blog] | Alibaba Cloud Product Comparison for AWS Professionals | https://www.alibabacloud.com/blog/Alibaba-Cloud-Product-Comparison-for-AWS-Professionals_444958 | 2026-03 |
| [Doc:fc] | Function Compute Documentation | https://www.alibabacloud.com/help/en/fc | 2026-03 |
| [Doc:batchcompute] | Batch Compute Documentation | https://www.alibabacloud.com/help/en/batchcompute | 2026-03 |
| [Doc:cpfs] | CPFS Documentation | https://www.alibabacloud.com/help/en/cpfs | 2026-03 |
| [Doc:hcsa] | Hybrid Cloud Storage Array Documentation | https://www.alibabacloud.com/help/en/hcsa | 2026-03 |
| [Doc:polar-db] | PolarDB Documentation | https://www.alibabacloud.com/help/en/polar-db | 2026-03 |
| [Doc:gdb] | Graph Database Documentation | https://www.alibabacloud.com/help/en/gdb | 2026-03 |
| [Doc:lindorm] | Lindorm Documentation | https://www.alibabacloud.com/help/en/lindorm | 2026-03 |
| [Doc:privatezone] | PrivateZone Documentation | https://www.alibabacloud.com/help/en/privatezone | 2026-03 |
| [Doc:sso] | SSO Documentation | https://www.alibabacloud.com/help/en/sso | 2026-03 |
| [Doc:acm] | ACM Documentation | https://www.alibabacloud.com/help/en/acm | 2026-03 |
| [Doc:data-security] | Data Security Center Documentation | https://www.alibabacloud.com/help/en/data-security-center | 2026-03 |
| [Doc:cloudhsm] | CloudHSM Documentation | https://www.alibabacloud.com/help/en/cloudhsm | 2026-03 |
| [Doc:arms] | ARMS Documentation | https://www.alibabacloud.com/help/en/arms | 2026-03 |
| [Doc:serverless-workflow] | Serverless Workflow Documentation | https://www.alibabacloud.com/help/en/serverless-workflow | 2026-03 |
| [Doc:dataworks] | DataWorks Documentation | https://www.alibabacloud.com/help/en/dataworks | 2026-03 |
| [Doc:graphql] | GraphQL Service Documentation | https://www.alibabacloud.com/help/en/graphql | 2026-03 |
| [Doc:pai] | PAI Documentation | https://www.alibabacloud.com/help/en/pai | 2026-03 |
| [Doc:nlp] | NLP Documentation | https://www.alibabacloud.com/help/en/nlp | 2026-03 |
| [Doc:speech] | Intelligent Speech Interaction Documentation | https://www.alibabacloud.com/help/en/speech | 2026-03 |
| [Doc:translation] | Machine Translation Documentation | https://www.alibabacloud.com/help/en/translation | 2026-03 |
| [Doc:conversation] | Intelligent Conversation Documentation | https://www.alibabacloud.com/help/en/conversation | 2026-03 |
| [Doc:forecast] | Time Series Forecasting Documentation | https://www.alibabacloud.com/help/en/forecast | 2026-03 |
| [Doc:recommendation] | Recommendation Engine Documentation | https://www.alibabacloud.com/help/en/recommendation | 2026-03 |
| [Doc:opensearch] | Open Search Documentation | https://www.alibabacloud.com/help/en/opensearch | 2026-03 |

## Changelog

> Versioning: Major (full re-verification) / Minor (new/changed mappings) / Patch (typos, URL fixes).

| Date | Version | Change | Category | Source | Author |
|------|---------|--------|----------|--------|--------|
| 2026-03-23 | 1.1 | Consolidated verification & maintenance into this file; removed standalone mapping-verification.md and mapping-maintenance.md | All | — | AI-assisted |
| 2026-03-22 | 1.0 | Initial citation-backed release — added Source, Confidence columns to all 100+ mappings; added Mapping Methodology section; added 28 source references | All | [Official], [Terraform], [CMH], [Blog], [Doc:*] | AI-assisted |

---

## Verification

How to verify that mappings in this table are accurate.

### Quick Verification (per mapping)

1. **Official source** — Check https://www.alibabacloud.com/en/product/product-mapping
2. **Terraform resource** — Search https://registry.terraform.io/providers/aliyun/alicloud/latest/docs for `alicloud_{resource}`
3. **Service documentation** — Verify https://www.alibabacloud.com/help/en/{service} returns HTTP 200 and is current

**Decision rule**: 3/3 sources → High confidence. 2/3 → Medium. 1/3 → Low. 0/3 → Do not include.

### CLI Product Existence Check

```bash
# Verify a product exists by calling a read-only describe/list command
aliyun <product> <DescribeAction> --RegionId <region> --user-agent AlibabaCloud-Agent-Skills
# Success (HTTP 200) = product exists
# Auth error (Forbidden/NoPermission) = product exists, credential issue
# Invalid product = product code wrong, check: aliyun --help
```

### Automated Verification

```bash
scripts/validate-source-mapping.sh --all                    # Validate all source mappings
scripts/validate-source-mapping.sh <source-file>            # Validate single source file
scripts/validate-source-mapping.sh --confirm <source-file>  # Validate + append new entries
```

### Confidence Scoring Rubric

| Criteria | Points |
|----------|--------|
| Listed on official product mapping page | +3 |
| Has Terraform resource in alicloud provider | +2 |
| Service doc page exists and current (<12 months) | +2 |
| Cloud Migration Hub supports migration | +1 |
| CLI product verification successful | +1 |
| Community/blog confirmation | +1 |

**Total → Confidence**: 7-9 = High, 4-6 = Medium, 1-3 = Low, 0 = Unverified (do not include).

---

## Maintenance

How to keep this mapping table accurate over time.

### When to Update

| Trigger | Priority | Timeline |
|---------|----------|----------|
| Migration discovers unmapped AWS service | **High** | Immediately (see below) |
| Alibaba Cloud launches/renames/merges service | High | Within 1 week |
| Customer reports mapping error | High | Within 48 hours |
| AWS launches new service | Medium | Within 2 weeks |
| Terraform provider adds new resource | Medium | Within 2 weeks |
| Quarterly scheduled review | Medium | End of quarter |

### Adding a New Mapping (During Migration)

When a migration discovers an AWS service not in this table:

1. Identify the AWS service and research the Alibaba Cloud equivalent
2. Find 2+ confirming sources: [Official], [Terraform], [CMH], [Doc:{service}]
3. Determine migration tool and complexity (Low/Medium/High)
4. Score confidence using the rubric above
5. Add row to the correct category table (alphabetical order)
6. Add source URL to the Sources table if new
7. Add changelog entry
8. Run `scripts/validate-source-mapping.sh` to validate

### Updating an Existing Mapping

1. Document reason for change
2. Update fields: equivalent, tool, complexity, notes (do NOT change the AWS service name)
3. Verify with 1+ official source
4. Adjust confidence if needed
5. Add changelog entry

### Deprecating a Mapping

1. Confirm deprecation from official source
2. Add `[DEPRECATED]` prefix in Notes: `[DEPRECATED] Old → New (since YYYY-MM)`
3. Do NOT delete the row (keep for traceability)
4. Add changelog entry

### Gap Detection (Quarterly)

1. Compare https://aws.amazon.com/products/ against this table by category
2. Classify gaps: **Mappable** (add it), **Partial** (add with Low confidence), **No Equivalent** (document as known gap), **Not Applicable** (skip)

### Quality Checklist (Before Any Change)

- [ ] At least 1 official source confirms the mapping
- [ ] Confidence level correctly scored per rubric
- [ ] Source citation in correct format: `[Source]`
- [ ] Changelog entry added
- [ ] No duplicate entries (search AWS service name first)
- [ ] Migration tool recommendation exists and is reasonable
- [ ] Service is in correct category

### Adding Mappings from Source Data

Use the validation script to extract, validate, and append mappings from raw source documents in `references/source-mappings/`:

```bash
# Preview: extract pairs, validate, show what would be appended
./scripts/validate-source-mapping.sh references/source-mappings/<file>.md

# Preview all source files at once
./scripts/validate-source-mapping.sh --all

# Dry-run: extract pairs only (no validation, no append)
./scripts/validate-source-mapping.sh --dry-run references/source-mappings/<file>.md

# Append confirmed entries to this table (adds changelog entry automatically)
./scripts/validate-source-mapping.sh --confirm references/source-mappings/<file>.md
```

The script will:
1. Extract product pairs from the source document (auto-detects format)
2. Validate each pair (CLI product check, documentation URL, Terraform resource)
3. Diff against this table — skip entries already present
4. Show a preview of new entries to append
5. On `--confirm`: append new rows to the correct section and add a changelog entry

### Change Sources to Monitor

| Source | URL | Frequency |
|--------|-----|-----------|
| Alibaba Cloud Release Notes | https://www.alibabacloud.com/notice | Monthly |
| Terraform Provider Releases | https://github.com/aliyun/terraform-provider-alicloud/releases | Monthly |
| Official Product Mapping | https://www.alibabacloud.com/en/product/product-mapping | Quarterly |
| AWS What's New | https://aws.amazon.com/new/ | Quarterly |
