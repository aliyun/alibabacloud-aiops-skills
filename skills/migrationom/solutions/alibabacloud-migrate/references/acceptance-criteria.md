# Acceptance Criteria: alibabacloud-migrate

**Scenario**: AWS to Alibaba Cloud Migration
**Purpose**: Skill testing acceptance criteria for CLI commands and SDK usage patterns

---

# Correct CLI Command Patterns

## 1. SMC (Server Migration Center)

### Product Name
- ✅ CORRECT: `aliyun smc`
- ❌ INCORRECT: `aliyun SMC`, `aliyun server-migration-center`, `aliyun smc create-replication-job`

### Commands
SMC uses **RPC-style API** (PascalCase API names, not plugin mode lowercase).

- ✅ CORRECT: `aliyun smc CreateReplicationJob --RegionId cn-hangzhou --SourceId s-xxx --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun smc DescribeReplicationJobs --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun smc StartReplicationJob --RegionId cn-hangzhou --JobId j-xxx --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun smc create-replication-job` (wrong style - SMC uses RPC, not plugin mode)
- ❌ INCORRECT: Missing `--user-agent AlibabaCloud-Agent-Skills` flag

### Parameters
- ✅ CORRECT: `--RegionId cn-hangzhou` (PascalCase for RPC APIs)
- ❌ INCORRECT: `--region-id cn-hangzhou` (wrong case for RPC style)
- ✅ CORRECT: `--SourceId s-xxx` (valid source server ID format)
- ❌ INCORRECT: `--SourceServerId s-xxx` (wrong parameter name)
- ✅ CORRECT: `--TargetType Image` (valid enum: Image, ContainerImage, TargetInstance)
- ❌ INCORRECT: `--TargetType ECS` (invalid enum value)
- ✅ CORRECT: `--ImageName my-migrated-image` (custom image name)
- ❌ INCORRECT: `--ImageId` in CreateReplicationJob (ImageId is output, not input)

## 2. DTS (Data Transmission Service)

### Product Name
- ✅ CORRECT: `aliyun dts`
- ❌ INCORRECT: `aliyun DTS`, `aliyun data-transmission`

### Commands
DTS uses **RPC-style API** (PascalCase API names).

- ✅ CORRECT: `aliyun dts CreateMigrationJob --Region cn-hangzhou --MigrationJobClass medium --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun dts ConfigureMigrationJob --MigrationJobId dts-xxx --MigrationJobName my-migration --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun dts DescribeMigrationJobs --Region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun dts StartMigrationJob --MigrationJobId dts-xxx --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun dts create-migration-job` (wrong style - DTS uses RPC, not plugin mode)
- ❌ INCORRECT: `aliyun dts CreateMigrationJob --RegionId` (DTS uses `--Region` not `--RegionId` in CreateMigrationJob)

### Parameters
- ✅ CORRECT: `--Region cn-hangzhou` (DTS CreateMigrationJob uses `Region` not `RegionId`)
- ❌ INCORRECT: `--region cn-hangzhou` (wrong case)
- ✅ CORRECT: `--MigrationJobClass medium` (valid: small, medium, large, xlarge, 2xlarge)
- ❌ INCORRECT: `--MigrationJobClass Medium` (case-sensitive, must be lowercase)
- ✅ CORRECT: `--SourceEndpoint.InstanceType other` (for external databases like AWS RDS)
- ❌ INCORRECT: `--SourceEndpoint.InstanceType AWS` (invalid value)
- ✅ CORRECT: `--SourceEndpoint.InstanceType MySQL` (for MySQL databases)
- ✅ CORRECT: `--MigrationMode.StructureIntialization true` (note: "Intialization" not "Initialization" - official API typo)
- ❌ INCORRECT: `--MigrationMode.StructureInitialization true` (wrong spelling - API has typo)
- ✅ CORRECT: `--MigrationMode.DataIntialization true` (same typo pattern)
- ✅ CORRECT: `--MigrationMode.DataSynchronization true`
- ❌ INCORRECT: `--MigrationJobId` in CreateMigrationJob (JobId is returned, not input for creation)

## 3. VPC (Virtual Private Cloud)

### Product Name
- ✅ CORRECT: `aliyun vpc`
- ❌ INCORRECT: `aliyun VPC`, `aliyun virtual-private-cloud`

### Commands
VPC uses **RPC-style API** (PascalCase API names).

- ✅ CORRECT: `aliyun vpc CreateVpc --RegionId cn-hangzhou --CidrBlock 10.0.0.0/8 --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun vpc CreateVSwitch --RegionId cn-hangzhou --VpcId vpc-xxx --ZoneId cn-hangzhou-i --CidrBlock 10.0.0.0/24 --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun vpc DescribeVpcs --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun vpc DescribeVSwitches --RegionId cn-hangzhou --VpcId vpc-xxx --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun vpc create-vpc` (wrong style - VPC uses RPC, not plugin mode)
- ❌ INCORRECT: `aliyun vpc create-vswitch` (wrong style)

### Parameters
- ✅ CORRECT: `--RegionId cn-hangzhou` (PascalCase)
- ❌ INCORRECT: `--region-id cn-hangzhou` (wrong case)
- ✅ CORRECT: `--CidrBlock 10.0.0.0/8` (valid VPC CIDR: /8 to /28)
- ✅ CORRECT: `--CidrBlock 172.16.0.0/16` (valid private CIDR)
- ✅ CORRECT: `--CidrBlock 192.168.0.0/16` (valid private CIDR)
- ❌ INCORRECT: `--CidrBlock 100.64.0.0/10` (reserved CIDR, not allowed)
- ❌ INCORRECT: `--CidrBlock 224.0.0.0/4` (multicast range, not allowed)
- ✅ CORRECT: `--VpcId vpc-xxx` (valid VPC ID format)
- ✅ CORRECT: `--ZoneId cn-hangzhou-i` (valid zone ID format)
- ❌ INCORRECT: `--ZoneId hangzhou-i` (missing region prefix)
- ✅ CORRECT: `--VSwitchName my-vswitch` (optional descriptive name)
- ✅ CORRECT: `--VpcName my-vpc` (optional descriptive name)

## 4. ECS (Elastic Compute Service)

### Product Name
- ✅ CORRECT: `aliyun ecs`
- ❌ INCORRECT: `aliyun ECS`, `aliyun elastic-compute-service`

### Commands
ECS uses **RPC-style API** (PascalCase API names).

- ✅ CORRECT: `aliyun ecs RunInstances --RegionId cn-hangzhou --ImageId m-xxx --InstanceType ecs.g6.large --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun ecs CreateSecurityGroup --RegionId cn-hangzhou --VpcId vpc-xxx --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun ecs DescribeInstances --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun ecs DescribeSecurityGroups --RegionId cn-hangzhou --VpcId vpc-xxx --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun ecs DescribeImages --RegionId cn-hangzhou --ImageId m-xxx --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun ecs run-instances` (wrong style - ECS uses RPC, not plugin mode)
- ❌ INCORRECT: `aliyun ecs create-security-group` (wrong style)

### Parameters
- ✅ CORRECT: `--RegionId cn-hangzhou` (PascalCase)
- ❌ INCORRECT: `--region-id cn-hangzhou` (wrong case)
- ✅ CORRECT: `--ImageId m-xxx` (valid image ID format)
- ❌ INCORRECT: `--Image m-xxx` (wrong parameter name)
- ✅ CORRECT: `--InstanceType ecs.g6.large` (valid instance type format)
- ❌ INCORRECT: `--InstanceType g6.large` (missing ecs. prefix)
- ✅ CORRECT: `--SecurityGroupId sg-xxx` (valid security group ID)
- ✅ CORRECT: `--VpcId vpc-xxx` (valid VPC ID)
- ✅ CORRECT: `--VSwitchId vsw-xxx` (valid vSwitch ID)
- ✅ CORRECT: `--Amount 1` (number of instances, 1-100)
- ❌ INCORRECT: `--Count 1` (wrong parameter name)
- ✅ CORRECT: `--InstanceName my-ecs-instance` (optional descriptive name)
- ✅ CORRECT: `--InternetChargeType PayByTraffic` (valid: PayByBandwidth, PayByTraffic)
- ✅ CORRECT: `--InternetMaxBandwidthOut 5` (bandwidth in Mbps, 0-100)
- ✅ CORRECT: `--SystemDisk.Category cloud_essd` (valid: cloud, cloud_efficiency, cloud_ssd, cloud_essd)
- ❌ INCORRECT: `--SystemDisk.Category ssd` (wrong value format)
- ✅ CORRECT: `--SecurityGroupIds.1 sg-xxx` (for multiple security groups)

## 5. OSS (Object Storage Service)

### Product Name
- ✅ CORRECT: `aliyun oss` (ossutil-style subcommands)
- ❌ INCORRECT: `aliyun OSS`, `aliyun object-storage-service`

### Commands
OSS uses **ossutil-style subcommands** (lowercase, not RPC style).

- ✅ CORRECT: `aliyun oss mb oss://bucket-name --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun oss ls oss://bucket-name --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun oss cp localfile.txt oss://bucket-name/key --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun oss rm oss://bucket-name/key --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun oss stat oss://bucket-name/key --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun oss CreateBucket` (OSS uses ossutil subcommands, not RPC style)
- ❌ INCORRECT: `aliyun oss PutObject` (wrong style)
- ❌ INCORRECT: `aliyun oss MB oss://bucket` (subcommands must be lowercase)

### Parameters
- ✅ CORRECT: `--region cn-hangzhou` (lowercase for ossutil)
- ❌ INCORRECT: `--RegionId cn-hangzhou` (wrong parameter name for OSS)
- ✅ CORRECT: `oss://bucket-name/key` (valid OSS URI format)
- ❌ INCORRECT: `oss://bucket-name` without key for cp/rm operations (needs full path)
- ✅ CORRECT: `--recursive` (for recursive operations on directories)
- ✅ CORRECT: `--force` (for force delete operations)

## 6. FC (Function Compute 3.0)

### Product Name
- ✅ CORRECT: `aliyun fc` (Function Compute 3.0 API)
- ❌ INCORRECT: `aliyun fc-open` (deprecated), `aliyun FC`

### Commands
FC 3.0 uses **ROA-style API** (RESTful path patterns with HTTP methods).

- ✅ CORRECT: `aliyun fc create-function --function-name my-func --runtime nodejs20 --handler index.handler --code zipFile=base64encoded== --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun fc delete-function --function-name my-func --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun fc get-function --function-name my-func --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun fc create-trigger --function-name my-func --trigger-name my-trigger --trigger-type oss --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun fc CreateFunction` (FC 3.0 uses plugin mode lowercase, not RPC style)
- ❌ INCORRECT: `aliyun fc POST /2023-03-30/functions` (FC CLI uses subcommands, not raw HTTP)

### Parameters
- ✅ CORRECT: `--function-name my-func` (lowercase with hyphens)
- ❌ INCORRECT: `--FunctionName my-func` (wrong case)
- ❌ INCORRECT: `--functionName my-func` (wrong case)
- ✅ CORRECT: `--runtime nodejs20` (valid: nodejs8/10/12/14/16/18/20, python3/3.9/3.10, java8/11, go1, php7.2, dotnetcore3.1, custom)
- ❌ INCORRECT: `--runtime Node.js20` (wrong format)
- ✅ CORRECT: `--handler index.handler` (language-specific handler format)
- ✅ CORRECT: `--code zipFile=base64encoded==` (code as base64)
- ✅ CORRECT: `--code ossBucketName=my-bucket,ossObjectName=code.zip` (code from OSS)
- ❌ INCORRECT: `--Code` (wrong case)
- ✅ CORRECT: `--memory-size 128` (in MB, multiples of 64)
- ✅ CORRECT: `--timeout 60` (in seconds, 1-600)
- ✅ CORRECT: `--trigger-type oss` (valid: oss, timer, http, log, cdn_events)
- ❌ INCORRECT: `--triggerType oss` (wrong case)

## 7. Alibaba Cloud DNS (alidns)

### Product Name
- ✅ CORRECT: `aliyun alidns`
- ❌ INCORRECT: `aliyun dns`, `aliyun DNS`, `aliyun cloud-dns`

### Commands
Alidns uses **RPC-style API** (PascalCase API names).

- ✅ CORRECT: `aliyun alidns AddDomainRecord --DomainName example.com --RR www --Type A --Value 1.2.3.4 --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun alidns DescribeDomainRecords --DomainName example.com --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun alidns AddDomain --DomainName example.com --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `aliyun alidns DescribeDomains --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun alidns add-domain-record` (wrong style - alidns uses RPC, not plugin mode)
- ❌ INCORRECT: `aliyun dns AddDomainRecord` (product code is alidns, not dns)

### Parameters
- ✅ CORRECT: `--DomainName example.com` (full domain name)
- ❌ INCORRECT: `--Domain example.com` (wrong parameter name)
- ✅ CORRECT: `--RR www` (hostname part, e.g., www, @, mail)
- ✅ CORRECT: `--RR @` (for root domain)
- ❌ INCORRECT: `--RR` empty (cannot be empty)
- ✅ CORRECT: `--Type A` (valid: A, AAAA, CNAME, MX, TXT, NS, SRV, CAA, PTR)
- ❌ INCORRECT: `--TYPE A` (wrong case)
- ❌ INCORRECT: `--Type a` (type values are uppercase)
- ✅ CORRECT: `--Value 1.2.3.4` (record value, format depends on type)
- ❌ INCORRECT: `--value 1.2.3.4` (wrong case)
- ✅ CORRECT: `--TTL 600` (in seconds, default 600)
- ✅ CORRECT: `--Priority 10` (required for MX records, 1-50)
- ✅ CORRECT: `--Line default` (resolution line: default, telecom, unicom, mobile, etc.)

---

# Global Rules

## User-Agent Flag
- ✅ CORRECT: Every `aliyun` command includes `--user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: Any `aliyun` command missing `--user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT: `--user-agent AlibabaCloud-Agent-Skills` (exact string, case-sensitive)
- ❌ INCORRECT: `--user-agent alibabacloud-agent-skills` (wrong case)
- ❌ INCORRECT: `--UserAgent AlibabaCloud-Agent-Skills` (wrong parameter name)

## Credential Safety
- ✅ CORRECT: `aliyun configure list` (check credential status only)
- ❌ INCORRECT: `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` (never print credentials)
- ❌ INCORRECT: `echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET` (never print credentials)
- ❌ INCORRECT: `aliyun configure set --access-key-id LTAI5tXXX` (never hardcode AK in skill)
- ❌ INCORRECT: `aliyun configure set --access-key-secret xxx` (never hardcode SK in skill)
- ✅ CORRECT: Prompt user to configure credentials outside the session
- ✅ CORRECT: Check credential status and stop if invalid, directing user to configure

## Parameter Placeholders
- ✅ CORRECT: `--RegionId <region>` (placeholder indicates user must provide)
- ✅ CORRECT: `--VpcId <vpc-id>` (placeholder with description)
- ✅ CORRECT: `--ImageId <image-id-from-smc>` (placeholder with context)
- ❌ INCORRECT: `--RegionId cn-hangzhou` hardcoded without user confirmation prompt
- ❌ INCORRECT: `--VpcId vpc-12345` hardcoded example without clear placeholder notation
- ✅ CORRECT: Include parameter confirmation instruction before execution
- ❌ INCORRECT: Assume default values for RegionId, instance names, CIDR blocks, passwords

## API Style Recognition

### RPC-Style APIs (PascalCase API names, --ParameterName format)
- ✅ CORRECT for SMC: `aliyun smc CreateReplicationJob --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT for DTS: `aliyun dts CreateMigrationJob --Region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT for VPC: `aliyun vpc CreateVpc --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT for ECS: `aliyun ecs RunInstances --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT for Alidns: `aliyun alidns AddDomainRecord --DomainName example.com --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT: `aliyun smc create-replication-job` (plugin mode lowercase wrong for RPC)
- ❌ INCORRECT: `--region-id` (lowercase with hyphens wrong for RPC)

### Plugin Mode (lowercase with hyphens)
- ✅ CORRECT for FC: `aliyun fc create-function --function-name my-func --user-agent AlibabaCloud-Agent-Skills`
- ✅ CORRECT for OSS: `aliyun oss mb oss://bucket-name --user-agent AlibabaCloud-Agent-Skills`
- ❌ INCORRECT for FC: `aliyun fc CreateFunction` (RPC style wrong for FC 3.0)
- ❌ INCORRECT for OSS: `aliyun oss CreateBucket` (RPC style wrong for OSS)

### Parameter Case Sensitivity
- ✅ CORRECT for RPC APIs: `--RegionId`, `--ImageId`, `--VpcId` (PascalCase)
- ✅ CORRECT for FC: `--function-name`, `--runtime`, `--handler` (lowercase with hyphens)
- ✅ CORRECT for OSS: `--region` (lowercase)
- ❌ INCORRECT: Mixing styles (e.g., `--regionId` camelCase)

## Enum Value Validation

### SMC TargetType
- ✅ CORRECT: `Image`, `ContainerImage`, `TargetInstance`
- ❌ INCORRECT: `ECS`, `VM`, `ecs`

### DTS MigrationJobClass
- ✅ CORRECT: `small`, `medium`, `large`, `xlarge`, `2xlarge` (lowercase)
- ❌ INCORRECT: `Small`, `MEDIUM`, `Large`

### ECS InstanceType
- ✅ CORRECT: `ecs.g6.large`, `ecs.c6.xlarge`, `ecs.r6.2xlarge` (with ecs. prefix)
- ❌ INCORRECT: `g6.large`, `c6.xlarge` (missing prefix)

### ECS InternetChargeType
- ✅ CORRECT: `PayByBandwidth`, `PayByTraffic`
- ❌ INCORRECT: `pay-by-traffic`, `PAYBYBANDWIDTH`

### ECS SystemDisk.Category
- ✅ CORRECT: `cloud`, `cloud_efficiency`, `cloud_ssd`, `cloud_essd`, `cloud_auto`, `cloud_essd_entry`
- ❌ INCORRECT: `ssd`, `essd`, `hdd` (incomplete names)

### DNS Record Type
- ✅ CORRECT: `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `NS`, `SRV`, `CAA`, `PTR` (uppercase)
- ❌ INCORRECT: `a`, `cname`, `Mx`

### FC Runtime
- ✅ CORRECT: `nodejs20`, `python3.10`, `java11`, `go1`, `custom`
- ❌ INCORRECT: `Node.js20`, `Python3`, `Java`

---

# SDK Usage Patterns (Python Common SDK)

## Import Patterns
- ✅ CORRECT:
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_smc20190601 import models as smc_models
```
- ❌ INCORRECT:
```python
import aliyun  # Wrong SDK package
from alibabacloud import smc  # Wrong import path
```

## Authentication
- ✅ CORRECT:
```python
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
client = smc_models.Client(config)
```
- ❌ INCORRECT:
```python
# Never hardcode credentials
config = open_api_models.Config(
    access_key_id="LTAI5tXXX",
    access_key_secret="xxx"
)
```

## Client Initialization
- ✅ CORRECT:
```python
config = open_api_models.Config(
    region_id='cn-hangzhou',
    credential=credential
)
client = smc20190601.Client(config)
```
- ❌ INCORRECT:
```python
# Missing region_id or credential
client = smc20190601.Client()
```

## API Invocation
- ✅ CORRECT:
```python
request = smc_models.CreateReplicationJobRequest(
    region_id='cn-hangzhou',
    source_id='s-xxx',
    target_type='Image'
)
response = client.create_replication_job(request)
```
- ❌ INCORRECT:
```python
# Wrong method name (should be snake_case)
response = client.CreateReplicationJob(request)
# Wrong parameter case (should be snake_case)
request = smc_models.CreateReplicationJobRequest(
    RegionId='cn-hangzhou',  # Wrong
    SourceId='s-xxx'  # Wrong
)
```

## Error Handling
- ✅ CORRECT:
```python
from tea.exceptions import TeaException

try:
    response = client.create_replication_job(request)
except TeaException as e:
    print(f"Error code: {e.code}, message: {e.message}")
```
- ❌ INCORRECT:
```python
# No error handling
response = client.create_replication_job(request)

# Or catching generic Exception only
try:
    response = client.create_replication_job(request)
except Exception as e:
    pass  # Silent failure
```

---

# Common Anti-Patterns

## 1. Mixing API Styles
- ❌ INCORRECT: Using plugin mode for RPC APIs
```bash
aliyun smc create-replication-job --region-id cn-hangzhou  # WRONG
```
- ✅ CORRECT:
```bash
aliyun smc CreateReplicationJob --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills  # RIGHT
```

## 2. Wrong Product Codes
- ❌ INCORRECT: `aliyun dns` (should be `alidns`)
- ❌ INCORRECT: `aliyun server-migration` (should be `smc`)
- ❌ INCORRECT: `aliyun function-compute` (should be `fc`)

## 3. Hardcoded Values
- ❌ INCORRECT: Hardcoding region without user confirmation
```bash
aliyun vpc CreateVpc --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills  # Assumes region
```
- ✅ CORRECT: Use placeholder and confirm with user
```bash
aliyun vpc CreateVpc --RegionId <region> --user-agent AlibabaCloud-Agent-Skills  # Confirm with user first
```

## 4. Missing Required Parameters
- ❌ INCORRECT: `aliyun smc CreateReplicationJob` (missing SourceId, RegionId)
- ❌ INCORRECT: `aliyun ecs RunInstances` (missing ImageId, InstanceType, RegionId)

## 5. Wrong Parameter Names
- ❌ INCORRECT: `--source-server-id` (should be `--SourceId` for SMC)
- ❌ INCORRECT: `--migration-class` (should be `--MigrationJobClass` for DTS)
- ❌ INCORRECT: `--instance-type` in wrong context

## 6. Credential Exposure
- ❌ INCORRECT: Printing environment variables
```bash
echo "AK: $ALIBABA_CLOUD_ACCESS_KEY_ID"
```
- ❌ INCORRECT: Logging credentials
```python
print(f"Using AK: {credential.access_key_id}")
```

---

# Verification Checklist

Before considering any CLI command or SDK usage correct:

1. **Product Code**: Verify product code exists via `aliyun <product> --help`
2. **API Style**: Confirm RPC vs plugin mode based on product
3. **Parameter Names**: Verify exact parameter names via `--help`
4. **Parameter Case**: RPC uses PascalCase, plugin uses lowercase-hyphen
5. **Enum Values**: Verify enum values match `--help` output exactly
6. **User-Agent**: Every command includes `--user-agent AlibabaCloud-Agent-Skills`
7. **Credential Safety**: No credential values printed or hardcoded
8. **Parameter Confirmation**: All user-specific parameters confirmed before execution

---

# Terraform HCL Patterns

## 1. Terraform Online Runtime Usage
#### ✅ CORRECT
```bash
$TF apply main.tf
$TF apply main.tf --state-id $EXISTING_STATE_ID
$TF destroy "$STATE_ID"
```
#### ❌ INCORRECT
```bash
# Never use inline aliyun iacservice commands
aliyun iacservice execute-terraform-apply --code "..."
# Never run local terraform CLI (unless explicitly requested)
terraform apply
# Never start fresh apply when STATE_ID exists (causes duplicates)
$TF apply main.tf  # when $STATE_ID already exists
```

## 2. HCL File Consolidation
#### ✅ CORRECT — Single main.tf
```hcl
# main.tf contains ALL resources
resource "alicloud_vpc" "migration" { ... }
resource "alicloud_vswitch" "migration" { ... }
resource "alicloud_instance" "migrated" { ... }
```
#### ❌ INCORRECT — Split across files
```
# network.tf, compute.tf, database.tf — IaCService only accepts one file
```

## 3. State ID Management
#### ✅ CORRECT
```bash
STATE_ID=$($TF apply main.tf | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env
# Subsequent changes reuse STATE_ID:
$TF apply main.tf --state-id $STATE_ID
```
#### ❌ INCORRECT
```bash
# Not saving STATE_ID — cannot cleanup later
$TF apply main.tf
# Fresh apply when state exists — creates duplicate resources
$TF apply main.tf  # without --state-id when STATE_ID exists
```

## 4. Provider Configuration
#### ✅ CORRECT — Direct provider block only, no terraform{} wrapper
```hcl
provider "alicloud" {
  region               = var.region
  configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-migrate"
}
```
#### ❌ INCORRECT — `terraform {}` / `required_providers` block (causes plugin load failure)
```hcl
# DO NOT add this block — the provider is pre-initialized by the environment.
# Adding required_providers triggers plugin schema loading via the registry,
# which fails with "Unrecognized remote plugin message" in this setup.
terraform {
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.220"
    }
  }
}

provider "alicloud" {
  region = var.region
}
```
#### ❌ INCORRECT — Hardcoded credentials
```hcl
provider "alicloud" {
  access_key = "LTAI..."
  secret_key = "abc123..."
  region     = "cn-hangzhou"
}
```

## 5. Placeholder Values
#### ✅ CORRECT
```hcl
resource "alicloud_vpc" "migration" {
  vpc_name   = "migration-vpc"
  cidr_block = var.vpc_cidr  # or "<vpc-cidr>" in examples
}
```
#### ❌ INCORRECT
```hcl
resource "alicloud_vpc" "migration" {
  vpc_name   = "migration-vpc"
  cidr_block = "172.16.0.0/12"  # hardcoded user value
}
```
