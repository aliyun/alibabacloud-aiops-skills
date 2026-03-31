#!/bin/bash
# Full-region parallel AWS resource scanner
# Usage: ./aws-scan-region.sh [region]
#
# Runs 30+ service discovery commands in parallel (background jobs).
# Typical runtime: 30-60 seconds for a full region scan.
# Output: aws-scan-<region>-<timestamp>/inventory.md
#
# Environment:
#   AWS_SCAN_CMD_TIMEOUT  Per-scan command timeout in seconds (default: 120). Uses GNU `timeout` when available, perl fallback on macOS.
#   AWS_SCAN_REDACT       If 1 (default), redact IPs / instance ids in inventory.md.
#   AWS_SCAN_MAX_PARALLEL Max concurrent scan jobs (default: 20).
#   AWS_MAX_ATTEMPTS / AWS_RETRY_MODE — passed to AWS CLI to bound retries on slow APIs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_scan-common.sh
source "$SCRIPT_DIR/_scan-common.sh"

START_TIME=$(date +%s)

# ── Pre-flight: AWS CLI + credentials ────────────────────────────────────────
if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: AWS CLI is not installed. Install it first:" >&2
    echo "  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html" >&2
    exit 1
fi

REGION="${1:-$(aws configure get region 2>/dev/null || echo 'us-east-1')}"
validate_aws_region "$REGION"

AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text 2>&1)" || {
    echo "ERROR: AWS credentials are invalid or not configured." >&2
    echo "  aws sts get-caller-identity returned: $AWS_ACCOUNT_ID" >&2
    echo "" >&2
    echo "Fix: run 'aws configure' or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars." >&2
    echo "Do NOT proceed with mock or representative data." >&2
    exit 1
}
PREFIX_OWNER_ID="$AWS_ACCOUNT_ID"
[[ "$PREFIX_OWNER_ID" =~ ^[0-9]{12}$ ]] || {
    echo "ERROR: aws sts get-caller-identity returned unexpected Account ID: '$PREFIX_OWNER_ID'" >&2
    exit 1
}

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="aws-scan-${REGION}-${TIMESTAMP}"
OUTPUT_FILE="${OUTPUT_DIR}/inventory.md"
JOBS_DIR="${OUTPUT_DIR}/.jobs"

mkdir -p "$JOBS_DIR"

echo "Scanning region: $REGION"
echo "Output: $OUTPUT_FILE"
echo "Max parallel: $AWS_SCAN_MAX_PARALLEL"
echo ""

# ── helpers ───────────────────────────────────────────────────────────────────
HITS_DIR="${OUTPUT_DIR}/.hits"
mkdir -p "$HITS_DIR"

scan() {
    local name="$1"
    shift
    local safe
    safe="$(echo "$name" | tr ' /' '__')"
    local out="$JOBS_DIR/${safe}.txt"
    _wait_for_slot
    {
        echo "## $name"
        echo '```'
        local result
        if result=$(_run_scan_cmd env AWS_DEFAULT_REGION="$REGION" "$@" 2>/dev/null) && [[ -n "$result" ]]; then
            printf '%s\n' "$result"
            touch "$HITS_DIR/${safe}"
        else
            echo "(no resources, no access, or timeout)"
        fi
        echo '```'
        echo ""
    } > "$out" &
}

# ── Compute ───────────────────────────────────────────────────────────────────
scan "EC2 Instances" aws ec2 describe-instances --region "$REGION" \
    --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`].Value|[0],PublicIpAddress,PrivateIpAddress]' \
    --output table

scan "EBS Volumes" aws ec2 describe-volumes --region "$REGION" \
    --query 'Volumes[].[VolumeId,Size,VolumeType,State,Attachments[0].InstanceId]' \
    --output table

scan "ECS Clusters" aws ecs list-clusters --region "$REGION" --query 'clusterArns' --output table

scan "EKS Clusters" aws eks list-clusters --region "$REGION" --query 'clusters' --output table

scan "Elastic Beanstalk Environments" aws elasticbeanstalk describe-environments --region "$REGION" \
    --query 'Environments[].[EnvironmentName,ApplicationName,Status,EnvironmentUrl]' \
    --output table

# ── Serverless ────────────────────────────────────────────────────────────────
scan "Lambda Functions" aws lambda list-functions --region "$REGION" \
    --query 'Functions[].[FunctionName,Runtime,MemorySize,Timeout,Role]' \
    --output table

scan "API Gateway REST APIs" aws apigateway get-rest-apis --region "$REGION" \
    --query 'items[].[id,name,createdDate]' \
    --output table

scan "API Gateway HTTP APIs v2" aws apigatewayv2 get-apis --region "$REGION" \
    --query 'Items[].[ApiId,Name,ProtocolType]' \
    --output table

# ── EventBridge ───────────────────────────────────────────────────────────────
scan "EventBridge Event Buses" aws events list-event-buses --region "$REGION" \
    --query 'EventBuses[].[Name,Arn]' --output table

scan "EventBridge Rules (default bus)" aws events list-rules --region "$REGION" \
    --query 'Rules[].[Name,State,ScheduleExpression,EventPattern]' --output table

# ── Storage ───────────────────────────────────────────────────────────────────
scan "S3 Buckets (global)" aws s3api list-buckets --query 'Buckets[].[Name,CreationDate]' --output table

scan "EFS File Systems" aws efs describe-file-systems --region "$REGION" \
    --query 'FileSystems[].[FileSystemId,Name,LifeCycleState,SizeInBytes.Value]' \
    --output table

# ── Database ──────────────────────────────────────────────────────────────────
scan "RDS Instances" aws rds describe-db-instances --region "$REGION" \
    --query 'DBInstances[].[DBInstanceIdentifier,Engine,EngineVersion,DBInstanceClass,DBInstanceStatus]' \
    --output table

scan "RDS Clusters (Aurora)" aws rds describe-db-clusters --region "$REGION" \
    --query 'DBClusters[].[DBClusterIdentifier,Engine,EngineVersion,Status]' \
    --output table

scan "ElastiCache Clusters" aws elasticache describe-cache-clusters --region "$REGION" \
    --query 'CacheClusters[].[CacheClusterId,Engine,EngineVersion,CacheClusterStatus]' \
    --output table

scan "DynamoDB Tables" aws dynamodb list-tables --region "$REGION" --query 'TableNames' --output table

scan "Redshift Clusters" aws redshift describe-clusters --region "$REGION" \
    --query 'Clusters[].[ClusterIdentifier,NodeType,NumberOfNodes,ClusterStatus]' \
    --output table

# ── Messaging ─────────────────────────────────────────────────────────────────
scan "SQS Queues" aws sqs list-queues --region "$REGION" --query 'QueueUrls' --output table

scan "SNS Topics" aws sns list-topics --region "$REGION" --query 'Topics[].TopicArn' --output table

scan "MSK Clusters (Kafka)" aws kafka list-clusters --region "$REGION" \
    --query 'ClusterInfoList[].[ClusterName,State,NumberOfBrokerNodes]' \
    --output table

# ── Networking ────────────────────────────────────────────────────────────────
scan "VPCs (non-default, with IPv6)" aws ec2 describe-vpcs --region "$REGION" \
    --filters Name=is-default,Values=false \
    --query 'Vpcs[].[VpcId,CidrBlock,Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock,State,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "VPCs (default)" aws ec2 describe-vpcs --region "$REGION" \
    --filters Name=is-default,Values=true \
    --query 'Vpcs[].[VpcId,CidrBlock,State]' \
    --output table

scan "VPC Peering Connections" aws ec2 describe-vpc-peering-connections --region "$REGION" \
    --query 'VpcPeeringConnections[].[VpcPeeringConnectionId,Status.Code,RequesterVpcInfo.VpcId,AccepterVpcInfo.VpcId,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "Subnets (non-default VPC, with IPv6)" aws ec2 describe-subnets --region "$REGION" \
    --filters Name=default-for-az,Values=false \
    --query 'Subnets[].[SubnetId,VpcId,CidrBlock,Ipv6CidrBlockAssociationSet[0].Ipv6CidrBlock,AvailabilityZone,MapPublicIpOnLaunch,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "Internet Gateways" aws ec2 describe-internet-gateways --region "$REGION" \
    --query 'InternetGateways[].[InternetGatewayId,Attachments[0].VpcId,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "Egress-only Internet Gateways" aws ec2 describe-egress-only-internet-gateways --region "$REGION" \
    --query 'EgressOnlyInternetGateways[].[EgressOnlyInternetGatewayId,Attachments[0].VpcId,Attachments[0].State]' \
    --output table

scan "NAT Gateways" aws ec2 describe-nat-gateways --region "$REGION" \
    --query 'NatGateways[].[NatGatewayId,VpcId,State,NatGatewayAddresses[0].PublicIp,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "Route Tables (non-default, with routes)" aws ec2 describe-route-tables --region "$REGION" \
    --filters Name=association.main,Values=false \
    --query 'RouteTables[].[RouteTableId,VpcId,Tags[?Key==`Name`].Value|[0],Routes[*].[DestinationCidrBlock,DestinationIpv6CidrBlock,GatewayId,NatGatewayId,VpcPeeringConnectionId,State]]' \
    --output json

scan "Security Groups (with rules)" aws ec2 describe-security-groups --region "$REGION" \
    --query 'SecurityGroups[?GroupName!=`default`].[GroupId,GroupName,VpcId,IpPermissions[*].[IpProtocol,FromPort,ToPort,IpRanges[*].CidrIp,UserIdGroupPairs[*].GroupId],IpPermissionsEgress[*].[IpProtocol,FromPort,ToPort,IpRanges[*].CidrIp,UserIdGroupPairs[*].GroupId]]' \
    --output json

scan "Network ACLs (custom only, with rules)" aws ec2 describe-network-acls --region "$REGION" \
    --filters Name=default,Values=false \
    --query 'NetworkAcls[].[NetworkAclId,VpcId,Tags[?Key==`Name`].Value|[0],Entries[*].[RuleNumber,Protocol,RuleAction,Egress,CidrBlock,Ipv6CidrBlock,PortRange.From,PortRange.To]]' \
    --output json

scan "VPC Endpoints" aws ec2 describe-vpc-endpoints --region "$REGION" \
    --query 'VpcEndpoints[].[VpcEndpointId,VpcEndpointType,ServiceName,VpcId,State,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "Managed Prefix Lists (customer-owned)" aws ec2 describe-managed-prefix-lists --region "$REGION" \
    --filters "Name=owner-id,Values=$PREFIX_OWNER_ID" \
    --query 'PrefixLists[].[PrefixListId,PrefixListName,AddressFamily,MaxEntries]' \
    --output table

scan "DHCP Option Sets (with content)" aws ec2 describe-dhcp-options --region "$REGION" \
    --query 'DhcpOptions[].[DhcpOptionsId,Tags[?Key==`Name`].Value|[0],DhcpConfigurations[*].[Key,Values[*].Value]]' \
    --output json

scan "Elastic Load Balancers (v2)" aws elbv2 describe-load-balancers --region "$REGION" \
    --query 'LoadBalancers[].[LoadBalancerName,Type,State.Code,DNSName]' \
    --output table

scan "Elastic Load Balancers (classic)" aws elb describe-load-balancers --region "$REGION" \
    --query 'LoadBalancerDescriptions[].[LoadBalancerName,DNSName,VPCId]' \
    --output table

scan "Route53 Hosted Zones (global)" aws route53 list-hosted-zones \
    --query 'HostedZones[].[Name,Id,Config.PrivateZone,ResourceRecordSetCount]' \
    --output table

scan "CloudFront Distributions (global)" aws cloudfront list-distributions \
    --query 'DistributionList.Items[].[Id,DomainName,Status]' \
    --output table

# ── IAM (global) ──────────────────────────────────────────────────────────────
scan "IAM Users" aws iam list-users --query 'Users[].[UserName,CreateDate]' --output table

scan "IAM Roles" aws iam list-roles --no-paginate \
    --query 'Roles[].[RoleName,Arn]' --output table

# ── Monitoring / Other ────────────────────────────────────────────────────────
scan "CloudWatch Alarms" aws cloudwatch describe-alarms --region "$REGION" \
    --query 'MetricAlarms[].[AlarmName,StateValue,MetricName,Namespace]' \
    --output table

scan "Secrets Manager Secrets" aws secretsmanager list-secrets --region "$REGION" \
    --query 'SecretList[].[Name,LastChangedDate,RotationEnabled]' \
    --output table

scan "Systems Manager Parameters" aws ssm describe-parameters --region "$REGION" \
    --query 'Parameters[].[Name,Type,LastModifiedDate]' \
    --output table

scan "Step Functions State Machines" aws stepfunctions list-state-machines --region "$REGION" \
    --query 'stateMachines[].[name,stateMachineArn,type]' \
    --output table

scan "Cognito User Pools" aws cognito-idp list-user-pools --region "$REGION" --max-results 60 \
    --query 'UserPools[].[Id,Name,Status]' --output table

scan "ACM Certificates" aws acm list-certificates --region "$REGION" \
    --query 'CertificateSummaryList[].[CertificateArn,DomainName,Status]' \
    --output table

scan "CloudTrail Trails" aws cloudtrail describe-trails --region "$REGION" --include-shadow-trails false \
    --query 'trailList[].[Name,S3BucketName,CloudWatchLogsLogGroupArn,IsMultiRegionTrail,LogFileValidationEnabled]' \
    --output table

scan "CloudWatch Log Groups" aws logs describe-log-groups --region "$REGION" \
    --query 'logGroups[].[logGroupName,retentionInDays,storedBytes]' \
    --output table

scan "CloudWatch Metric Filters" aws logs describe-metric-filters --region "$REGION" \
    --query 'metricFilters[].[filterName,logGroupName,filterPattern,metricTransformations[0].metricName,metricTransformations[0].metricNamespace]' \
    --output table

# ── Container ────────────────────────────────────────────────────────────────
scan "ECR Repositories" aws ecr describe-repositories --region "$REGION" \
    --query 'repositories[].[repositoryName,repositoryUri,imageTagMutability,imageScanningConfiguration.scanOnPush]' \
    --output table

# ── Streaming ────────────────────────────────────────────────────────────────
scan "Kinesis Data Streams" aws kinesis list-streams --region "$REGION" \
    --query 'StreamNames' --output table

# ── Security (WAF) ──────────────────────────────────────────────────────────
scan "WAF Web ACLs (v2)" aws wafv2 list-web-acls --region "$REGION" --scope REGIONAL \
    --query 'WebACLs[].[Name,Id,ARN]' --output table

# ── Hybrid Networking ────────────────────────────────────────────────────────
scan "VPN Connections" aws ec2 describe-vpn-connections --region "$REGION" \
    --query 'VpnConnections[].[VpnConnectionId,State,CustomerGatewayId,VpnGatewayId,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "VPN Gateways" aws ec2 describe-vpn-gateways --region "$REGION" \
    --query 'VpnGateways[].[VpnGatewayId,State,Type,VpcAttachments[0].VpcId,Tags[?Key==`Name`].Value|[0]]' \
    --output table

scan "Direct Connect Connections" aws directconnect describe-connections --region "$REGION" \
    --query 'connections[].[connectionId,connectionName,connectionState,bandwidth,location]' \
    --output table

scan "Direct Connect Virtual Interfaces" aws directconnect describe-virtual-interfaces --region "$REGION" \
    --query 'virtualInterfaces[].[virtualInterfaceId,virtualInterfaceName,virtualInterfaceType,virtualInterfaceState,vlan,connectionId]' \
    --output table

# ── Big Data ─────────────────────────────────────────────────────────────────
scan "EMR Clusters" aws emr list-clusters --region "$REGION" --active \
    --query 'Clusters[].[Id,Name,Status.State,NormalizedInstanceHours]' \
    --output table

# ── Wait for all background jobs ──────────────────────────────────────────────
echo "Waiting for all scan jobs to complete..."
wait
echo "All scans done. Merging results..."

# ── Merge output (sorted by section name, empty sections filtered) ────────────
_merge_jobs "$JOBS_DIR" "AWS Resource Inventory — Region: $REGION" "$OUTPUT_FILE"

# ── Post-scan validation ─────────────────────────────────────────────────────
TOTAL_SECTIONS=$(find "$JOBS_DIR" -maxdepth 1 -name '*.txt' | wc -l | tr -d ' ')
HIT_COUNT=$(find "$HITS_DIR" -maxdepth 1 -type f | wc -l | tr -d ' ')
rm -rf "$HITS_DIR"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "Resource sections scanned: $TOTAL_SECTIONS total, $HIT_COUNT with data"
grep "^## " "$OUTPUT_FILE" | sed 's/^## /  - /' || true

if [[ "$HIT_COUNT" -eq 0 ]]; then
    echo "" >&2
    echo "WARNING: Every section returned empty — this almost certainly means" >&2
    echo "  the IAM user/role lacks permissions for all services in $REGION." >&2
    echo "  Verify: aws sts get-caller-identity && aws ec2 describe-instances --region $REGION" >&2
    echo "  Do NOT treat this as 'no resources exist'." >&2
    # Exit non-zero so the agent cannot silently continue
    echo ""
    echo "Full inventory: $OUTPUT_FILE"
    _print_elapsed "$START_TIME"
    exit 2
fi

echo ""
echo "Full inventory: $OUTPUT_FILE"
echo "Raw job outputs: $JOBS_DIR/"
echo "Note: AWS_SCAN_REDACT=${AWS_SCAN_REDACT} (set 0 for raw IDs/IPs in inventory)."
_print_elapsed "$START_TIME"
echo "Next: ./scripts/aws-scan-enrich.sh $REGION \"$(pwd)/$OUTPUT_DIR\" → per-resource deep scan → inventory-deep.md"
